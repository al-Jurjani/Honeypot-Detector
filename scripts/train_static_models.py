"""
train_static_models.py — Step 14: 5-fold stratified CV on static features.

Trains 4 classifiers on outputs/results/static_features.csv using identical
fold splits so results are comparable across pipelines.

Outputs
-------
outputs/results/cv_splits.json         fold indices (reused in steps 15-16)
outputs/results/static_cv_results.csv  per-fold metrics for all 4 models
outputs/results/static_summary.csv     mean +/- std per model
outputs/results/static_feature_importance.csv  RF feature importances
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from src.utils import RESULTS_DIR, get_logger

log = get_logger("train_static_models")

STATIC_CSV = RESULTS_DIR / "static_features.csv"
CV_SPLITS_JSON = RESULTS_DIR / "cv_splits.json"
CV_RESULTS_CSV = RESULTS_DIR / "static_cv_results.csv"
SUMMARY_CSV = RESULTS_DIR / "static_summary.csv"
IMPORTANCES_CSV = RESULTS_DIR / "static_feature_importance.csv"

FEATURE_COLS = [
    "uses_tx_origin",
    "has_fallback",
    "fallback_reverts_non_owner",
    "require_count",
    "has_selfdestruct",
    "has_withdrawal_function",
    "withdrawal_owner_only",
    "uses_inline_assembly",
    "state_changes_before_external_calls",
    "payable_to_withdraw_ratio",
]

N_SPLITS = 5
RANDOM_STATE = 42


def _make_models() -> dict:
    return {
        "RandomForest": RandomForestClassifier(
            n_estimators=100, random_state=RANDOM_STATE
        ),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=1000, random_state=RANDOM_STATE
            )),
        ]),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=100, random_state=RANDOM_STATE
        ),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(probability=True, random_state=RANDOM_STATE)),
        ]),
    }


def _metrics(y_true, y_pred, y_prob) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_true, y_prob),
    }


def run() -> None:
    df = pd.read_csv(STATIC_CSV)
    df["label_bin"] = (df["label"] == "honeypot").astype(int)

    X = df[FEATURE_COLS].astype(float).values
    y = df["label_bin"].values

    # Generate and save fold splits
    skf = StratifiedKFold(
        n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
    )
    splits = [
        {"train": train.tolist(), "test": test.tolist()}
        for train, test in skf.split(X, y)
    ]
    CV_SPLITS_JSON.write_text(
        json.dumps(splits, indent=2), encoding="utf-8"
    )
    log.info("Saved %d fold splits to %s", N_SPLITS, CV_SPLITS_JSON)

    # Cross-validate each model
    fold_records = []
    rf_importances = []

    for model_name in _make_models():
        log.info("Training %s ...", model_name)
        for fold_idx, split in enumerate(splits):
            train_idx = np.array(split["train"])
            test_idx = np.array(split["test"])

            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = _make_models()[model_name]
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]

            m = _metrics(y_test, y_pred, y_prob)
            fold_records.append({
                "model": model_name,
                "fold": fold_idx + 1,
                **m,
            })

            if model_name == "RandomForest":
                rf_importances.append(model.feature_importances_)

    # Save per-fold results
    cv_df = pd.DataFrame(fold_records)
    cv_df.to_csv(CV_RESULTS_CSV, index=False)
    log.info("Saved per-fold results to %s", CV_RESULTS_CSV)

    # Save summary (mean +/- std per model)
    metric_cols = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    summary_rows = []
    for model_name, grp in cv_df.groupby("model"):
        row = {"model": model_name}
        for col in metric_cols:
            row[f"{col}_mean"] = grp[col].mean()
            row[f"{col}_std"] = grp[col].std()
        summary_rows.append(row)

    summary_df = (
        pd.DataFrame(summary_rows)
        .sort_values("f1_mean", ascending=False)
    )
    summary_df.to_csv(SUMMARY_CSV, index=False)

    # Print summary table
    print("\n-- Static Features CV Summary ----------------------------------")
    for _, row in summary_df.iterrows():
        print(
            f"  {row['model']:<22}"
            f"  Acc={row['accuracy_mean']:.3f}"
            f"+-{row['accuracy_std']:.3f}"
            f"  F1={row['f1_mean']:.3f}"
            f"+-{row['f1_std']:.3f}"
            f"  AUC={row['auc_roc_mean']:.3f}"
            f"+-{row['auc_roc_std']:.3f}"
        )
    print()

    # Save RF feature importances
    mean_imp = np.mean(rf_importances, axis=0)
    imp_df = (
        pd.DataFrame({"feature": FEATURE_COLS, "importance": mean_imp})
        .sort_values("importance", ascending=False)
    )
    imp_df.to_csv(IMPORTANCES_CSV, index=False)
    log.info("Saved RF feature importances to %s", IMPORTANCES_CSV)

    print("-- RF Feature Importances (mean over folds) --------------------")
    for _, row in imp_df.iterrows():
        bar = "#" * int(row["importance"] * 40)
        print(
            f"  {row['feature']:<42}"
            f"  {row['importance']:.4f}  {bar}"
        )
    print()


if __name__ == "__main__":
    run()
