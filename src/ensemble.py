"""
ensemble.py — Pipeline 3: Hybrid ensemble classifier (static + LLM features).

Merges static_features.csv and llm_features.csv by contract_id into a single
feature matrix and trains a Random Forest classifier. Also handles evaluation
for all three pipelines (static-only, LLM-only, ensemble) using 5-fold
stratified cross-validation on the same splits for a fair comparison.

Outputs
-------
- outputs/results/ensemble_features.csv   — merged feature matrix
- outputs/results/cv_results.csv          — per-fold metrics for all approaches
- outputs/results/comparison_table.csv    — mean ± std summary table
- outputs/figures/                        — all paper figures (generated here)
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    roc_auc_score,
    confusion_matrix,
)

from utils import FIGURES_DIR, RESULTS_DIR, get_logger, save_results

logger = get_logger(__name__)

N_FOLDS = 5
RANDOM_STATE = 42


# ── Data loading and merging ───────────────────────────────────────────────────

def load_static_features() -> pd.DataFrame:
    """Load outputs/results/static_features.csv."""
    raise NotImplementedError


def load_llm_features() -> pd.DataFrame:
    """Load outputs/results/llm_features.csv."""
    raise NotImplementedError


def merge_features(
    static_df: pd.DataFrame, llm_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge static and LLM feature DataFrames on contract_id.

    Parameters
    ----------
    static_df : pd.DataFrame
    llm_df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        Combined feature matrix (inner join on contract_id).
        Only contracts present in both DataFrames are included.
    """
    raise NotImplementedError


# ── Cross-validation ───────────────────────────────────────────────────────────

def get_cv_splits(
    df: pd.DataFrame, label_col: str = "label"
) -> list[tuple]:
    """
    Generate 5-fold stratified cross-validation splits.

    Returns a list of (train_idx, test_idx) tuples so the exact same
    splits can be reused across all three pipelines.

    Parameters
    ----------
    df : pd.DataFrame
        Full feature DataFrame (must contain label_col).
    label_col : str
        Column name for binary labels.

    Returns
    -------
    list of (np.ndarray, np.ndarray)
    """
    raise NotImplementedError


def evaluate_fold(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    clf: RandomForestClassifier,
) -> dict:
    """
    Train clf on the training fold and evaluate on the test fold.

    Returns
    -------
    dict with keys: precision, recall, f1, accuracy, roc_auc
    """
    raise NotImplementedError


# ── Pipeline evaluations ───────────────────────────────────────────────────────

def evaluate_static_pipeline(
    static_df: pd.DataFrame, splits: list[tuple]
) -> pd.DataFrame:
    """
    Evaluate Pipeline 1 (static-only Random Forest) on the given CV splits.

    Returns
    -------
    pd.DataFrame
        One row per fold with metric columns.
    """
    raise NotImplementedError


def evaluate_llm_pipeline(
    llm_df: pd.DataFrame,
    splits: list[tuple],
    method: str = "flag",
    threshold: int = 5,
) -> pd.DataFrame:
    """
    Evaluate Pipeline 2 (LLM-only) on the given CV splits.

    Parameters
    ----------
    method : str
        "flag"      — use is_honeypot boolean directly
        "threshold" — use deception_risk_score >= threshold

    Returns
    -------
    pd.DataFrame
        One row per fold with metric columns.
    """
    raise NotImplementedError


def evaluate_ensemble_pipeline(
    merged_df: pd.DataFrame, splits: list[tuple]
) -> pd.DataFrame:
    """
    Evaluate Pipeline 3 (ensemble Random Forest) on the given CV splits.

    Returns
    -------
    pd.DataFrame
        One row per fold with metric columns.
    """
    raise NotImplementedError


# ── Summary table ──────────────────────────────────────────────────────────────

def build_comparison_table(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build the master comparison table (mean ± std across folds).

    Parameters
    ----------
    results : dict
        Keys are approach names (e.g. "Static-Only", "LLM-Only (flag)"),
        values are per-fold metric DataFrames from the evaluate_* functions.

    Returns
    -------
    pd.DataFrame
        Rows = approaches, columns = "Precision", "Recall", "F1",
        "Accuracy", "ROC-AUC" (each formatted as "mean ± std").
    """
    raise NotImplementedError


# ── Statistical significance ───────────────────────────────────────────────────

def mcnemar_test(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
) -> float:
    """
    Run McNemar's test to compare two classifiers.

    Parameters
    ----------
    y_true : np.ndarray
        Ground-truth binary labels.
    y_pred_a, y_pred_b : np.ndarray
        Predictions from classifier A and B respectively.

    Returns
    -------
    float
        p-value. p < 0.05 indicates a statistically significant difference.
    """
    raise NotImplementedError


# ── Visualization ──────────────────────────────────────────────────────────────

def plot_f1_comparison(results: dict[str, pd.DataFrame]) -> None:
    """Figure 1: Bar chart of mean F1 scores across all approaches."""
    raise NotImplementedError


def plot_precision_recall(results: dict[str, pd.DataFrame]) -> None:
    """Figure 2: Grouped bar chart of precision vs recall per approach."""
    raise NotImplementedError


def plot_roc_curves(
    roc_data: dict[str, tuple[np.ndarray, np.ndarray, float]]
) -> None:
    """Figure 3: Overlaid ROC curves with AUC values in the legend."""
    raise NotImplementedError


def plot_confusion_matrices(
    cms: dict[str, np.ndarray]
) -> None:
    """Figure 4: 2×2 confusion matrix heatmaps (one per approach)."""
    raise NotImplementedError


def plot_feature_importance(
    clf: RandomForestClassifier, feature_names: list[str]
) -> None:
    """Figure 5: Feature importance bar chart from the static Random Forest."""
    raise NotImplementedError


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    static_df = load_static_features()
    llm_df = load_llm_features()
    merged_df = merge_features(static_df, llm_df)

    splits = get_cv_splits(merged_df)

    results = {
        "Static-Only": evaluate_static_pipeline(static_df, splits),
        "LLM-Only (flag)": evaluate_llm_pipeline(llm_df, splits, method="flag"),
        "LLM-Only (threshold)": evaluate_llm_pipeline(
            llm_df, splits, method="threshold"
        ),
        "Ensemble": evaluate_ensemble_pipeline(merged_df, splits),
    }

    table = build_comparison_table(results)
    print(table.to_string())
    save_results(table, "comparison_table.csv")
