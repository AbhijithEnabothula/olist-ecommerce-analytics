"""Model evaluation charts (ROC, Precision-Recall, Confusion Matrix, Feature Importance)."""

from pathlib import Path
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    PrecisionRecallDisplay,
    RocCurveDisplay,
    confusion_matrix,
)
from src.models.train_model import chronological_train_test_split


def generate_evaluation_figures(
    featured_df: pd.DataFrame,
    pipeline_path: str | Path = "models/saved_models/late_delivery_pipeline.joblib",
    fi_csv_path: str | Path = "reports/model_results/feature_importance.csv",
    figures_dir: str | Path = "reports/figures",
    threshold: float = 0.5755,
) -> None:
    """Export ROC curve, PR curve, Confusion Matrix, and Feature Importance charts."""
    fig_path = Path(figures_dir)
    fig_path.mkdir(parents=True, exist_ok=True)

    _, X_test, _, y_test, _, _ = chronological_train_test_split(featured_df, test_fraction=0.20)
    pipeline = joblib.load(pipeline_path)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    sns.set_theme(style="whitegrid")

    # 1. ROC & Precision-Recall Curves side-by-side
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    RocCurveDisplay.from_predictions(y_test, y_prob, ax=axes[0], name="Logistic Regression (Balanced)")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1, label="Random Baseline (0.50)")
    axes[0].set_title("Chronological Test ROC Curve")
    axes[0].legend(loc="lower right")

    PrecisionRecallDisplay.from_predictions(
        y_test, y_prob, ax=axes[1], name="Logistic Regression (Balanced)"
    )
    baseline_pr = float(y_test.mean())
    axes[1].axhline(baseline_pr, color="gray", linestyle="--", label=f"Baseline Late Rate ({baseline_pr:.2%})")
    axes[1].set_title("Chronological Test Precision-Recall Curve")
    axes[1].legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(fig_path / "07_roc_pr_curves.png", dpi=200)
    plt.close(fig)

    # 2. Confusion Matrix at Optimal Threshold
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["On-Time (0)", "Late (1)"])
    disp.plot(ax=ax, cmap="Blues", values_format=",d", colorbar=False)
    ax.set_title(f"Confusion Matrix (Threshold = {threshold:.4f})")
    plt.tight_layout()
    plt.savefig(fig_path / "08_confusion_matrix.png", dpi=200)
    plt.close(fig)

    # 3. Top 12 Permutation Feature Importance
    fi_df = pd.read_csv(fi_csv_path).head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(fi_df["feature"], fi_df["importance_mean"], xerr=fi_df["importance_std"], color="#2b5c8f")
    ax.set_xlabel("Mean Decrease in Test PR-AUC (Permutation Importance)")
    ax.set_title("Top 12 Pre-Shipment Predictors of Late Delivery")
    plt.tight_layout()
    plt.savefig(fig_path / "09_feature_importance.png", dpi=200)
    plt.close(fig)
