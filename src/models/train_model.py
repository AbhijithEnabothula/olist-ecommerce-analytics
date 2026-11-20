"""Leakage-conscious chronological training with validation-only model selection."""
import json
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from src.features.build_features import (ALL_FEATURE_COLUMNS, CATEGORICAL_FEATURES,
                                         NUMERIC_FEATURES, get_feature_matrix_and_target)


def chronological_train_test_split(df: pd.DataFrame, test_fraction: float = 0.20) -> Tuple:
    ordered = df.sort_values('order_purchase_timestamp', kind='mergesort').reset_index(drop=True)
    cut = int(len(ordered) * (1 - test_fraction))
    train_df, test_df = ordered.iloc[:cut].copy(), ordered.iloc[cut:].copy()
    X_train, y_train = get_feature_matrix_and_target(train_df)
    X_test, y_test = get_feature_matrix_and_target(test_df)
    return X_train, X_test, y_train, y_test, train_df, test_df


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([('imputer', SimpleImputer(strategy='median')),
                        ('scaler', StandardScaler())])
    categorical = Pipeline([('imputer', SimpleImputer(strategy='constant', fill_value='unknown')),
                            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    return ColumnTransformer([('num', numeric, NUMERIC_FEATURES),
                              ('cat', categorical, CATEGORICAL_FEATURES)], remainder='drop')


def find_optimal_f1_threshold(y_true, y_prob) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
    if len(thresholds) == 0:
        return 0.5
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-9)
    return float(thresholds[int(np.argmax(f1))])


def evaluate_predictions(y_true, y_prob, threshold=0.5) -> Dict:
    preds = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, preds, labels=[0, 1]).ravel()
    return dict(threshold=round(float(threshold), 4),
                accuracy=round(float(accuracy_score(y_true, preds)), 4),
                precision=round(float(precision_score(y_true, preds, zero_division=0)), 4),
                recall=round(float(recall_score(y_true, preds, zero_division=0)), 4),
                f1_score=round(float(f1_score(y_true, preds, zero_division=0)), 4),
                roc_auc=round(float(roc_auc_score(y_true, y_prob)), 4),
                pr_auc=round(float(average_precision_score(y_true, y_prob)), 4),
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))


def train_and_compare_models(featured_df, models_dir='models/saved_models',
                             results_dir='reports/model_results') -> pd.DataFrame:
    # The time-based split is performed BEFORE fitting any scikit-learn transformers.
    X_train, X_test, y_train, y_test, train_df, test_df = chronological_train_test_split(featured_df)
    tscv = TimeSeriesSplit(n_splits=3)
    candidates = {
        'Logistic Regression (Balanced)': Pipeline([
            ('preprocessor', build_preprocessor()),
            ('classifier', LogisticRegression(C=0.5, max_iter=1000,
                                             class_weight='balanced', random_state=42))]),
        'Random Forest (Regularized)': Pipeline([
            ('preprocessor', build_preprocessor()),
            ('classifier', RandomForestClassifier(n_estimators=150, max_depth=8,
                       min_samples_leaf=50, max_features='sqrt', class_weight='balanced',
                       random_state=42, n_jobs=2))]),
        'HistGradientBoosting (Regularized)': Pipeline([
            ('preprocessor', build_preprocessor()),
            ('classifier', HistGradientBoostingClassifier(max_iter=120, learning_rate=0.04,
                       max_leaf_nodes=15, min_samples_leaf=80, l2_regularization=5.0,
                       class_weight='balanced', random_state=42))]),
    }
    records = []
    for name, pipeline in candidates.items():
        scores = cross_val_score(pipeline, X_train, y_train, cv=tscv,
                                 scoring='average_precision', n_jobs=1)
        records.append({'model': name, 'cv_pr_auc': round(float(scores.mean()), 4),
                        'cv_pr_auc_std': round(float(scores.std()), 4)})
    # No test probabilities are calculated during model selection.
    comparison = pd.DataFrame(records).sort_values('cv_pr_auc', ascending=False).reset_index(drop=True)
    best_name = str(comparison.iloc[0]['model'])
    chosen = candidates[best_name]

    # Tune the classification threshold on a chronological validation segment of TRAIN only.
    val_cut = int(len(X_train) * 0.85)
    val_model = clone(chosen)
    val_model.fit(X_train.iloc[:val_cut], y_train.iloc[:val_cut])
    val_probs = val_model.predict_proba(X_train.iloc[val_cut:])[:, 1]
    threshold = find_optimal_f1_threshold(y_train.iloc[val_cut:].to_numpy(), val_probs)

    # Refit chosen model on all TRAIN, then evaluate ONCE on held-out TEST.
    chosen.fit(X_train, y_train)
    test_probs = chosen.predict_proba(X_test)[:, 1]
    metrics = evaluate_predictions(y_test, test_probs, threshold)
    default_metrics = evaluate_predictions(y_test, test_probs, 0.5)
    comparison['selected'] = comparison['model'].eq(best_name)
    for col in ['test_roc_auc', 'test_pr_auc', 'default_thresh_f1',
                'optimal_threshold', 'test_precision', 'test_recall',
                'test_f1_score', 'test_accuracy', 'tn', 'fp', 'fn', 'tp']:
        comparison[col] = np.nan
    first = comparison.index[comparison['selected']][0]
    values = {'test_roc_auc': metrics['roc_auc'], 'test_pr_auc': metrics['pr_auc'],
              'default_thresh_f1': default_metrics['f1_score'], 'optimal_threshold': threshold,
              'test_precision': metrics['precision'], 'test_recall': metrics['recall'],
              'test_f1_score': metrics['f1_score'], 'test_accuracy': metrics['accuracy'],
              'tn': metrics['tn'], 'fp': metrics['fp'], 'fn': metrics['fn'], 'tp': metrics['tp']}
    for col, value in values.items():
        comparison.loc[first, col] = value

    # Post-evaluation explanatory analysis: test importance is not used for model selection.
    importance = permutation_importance(chosen, X_test, y_test, n_repeats=3,
                                        scoring='average_precision', random_state=42, n_jobs=1)
    fi = pd.DataFrame({'feature': ALL_FEATURE_COLUMNS,
                       'importance_mean': importance.importances_mean.round(5),
                       'importance_std': importance.importances_std.round(5)})
    fi = fi.sort_values('importance_mean', ascending=False).reset_index(drop=True)
    model_path, result_path = Path(models_dir), Path(results_dir)
    model_path.mkdir(parents=True, exist_ok=True)
    result_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(chosen, model_path / 'late_delivery_pipeline.joblib')
    comparison.to_csv(result_path / 'model_comparison.csv', index=False)
    fi.to_csv(result_path / 'feature_importance.csv', index=False)
    metadata = {
        'best_model_name': best_name, 'optimal_threshold': round(threshold, 4),
        'feature_columns': ALL_FEATURE_COLUMNS, 'numeric_features': NUMERIC_FEATURES,
        'categorical_features': CATEGORICAL_FEATURES,
        'train_rows': len(X_train), 'test_rows': len(X_test),
        'train_start': str(train_df['order_purchase_timestamp'].min()),
        'train_end': str(train_df['order_purchase_timestamp'].max()),
        'test_start': str(test_df['order_purchase_timestamp'].min()),
        'test_end': str(test_df['order_purchase_timestamp'].max()),
        'test_late_rate': round(float(y_test.mean()), 4),
        'scikit_learn_version': sklearn.__version__, 'selection_metric': 'training_cv_pr_auc',
        'threshold_source': 'chronological_training_validation',
        'test_evaluated_only_for_winner': True,
        'metrics': {'model': best_name, 'cv_pr_auc': float(comparison.iloc[0]['cv_pr_auc']),
                    'test_roc_auc': metrics['roc_auc'], 'test_pr_auc': metrics['pr_auc'],
                    'default_thresh_f1': default_metrics['f1_score'],
                    'optimal_threshold': round(threshold, 4),
                    'test_precision': metrics['precision'], 'test_recall': metrics['recall'],
                    'test_f1_score': metrics['f1_score'], 'test_accuracy': metrics['accuracy'],
                    'tn': metrics['tn'], 'fp': metrics['fp'], 'fn': metrics['fn'], 'tp': metrics['tp']}
    }
    (model_path / 'model_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return comparison
