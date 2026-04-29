"""
loto_evaluation.py — Leave-One-Type-Out (LOTO) evaluation on static features.

For each of the 8 honeypot types, trains RF/LR/GBT/SVM on all contracts
EXCEPT that type, then tests on the held-out type + all legitimate contracts.

This answers: can the model detect a honeypot type it has never seen before?

Output
------
outputs/results/loto_results.csv    per-type metrics for all 4 models
outputs/results/loto_summary.csv    mean metrics across types per model
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from src.utils import RESULTS_DIR, LABELS_PATH, get_logger

log = get_logger("loto_evaluation")

STATIC_CSV = RESULTS_DIR / "static_features.csv"
LOTO_RESULTS_CSV = RESULTS_DIR / "loto_results.csv"
LOTO_SUMMARY_CSV = RESULTS_DIR / "loto_summary.csv"

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
    # Guard: roc_auc undefined if only one class in test set
    try:
        auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        auc = float("nan")
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "auc_roc": auc,
    }


def run() -> None:
    df = pd.read_csv(STATIC_CSV)
    gt = pd.read_csv(LABELS_PATH)[["contract_id", "honeypot_type"]]
    df = df.merge(gt, on="contract_id", how="left")
    df["label_bin"] = (df["label"] == "honeypot").astype(int)

    honeypot_types = sorted(
        df[df["label"] == "honeypot"]["honeypot_type"].dropna().unique()
    )
    legitimate = df[df["label"] == "legitimate"]

    log.info(
        "Honeypot types found: %s", honeypot_types
    )
    log.info("Legitimate contracts: %d", len(legitimate))

    records = []

    for held_out_type in honeypot_types:
        held_out = df[df["honeypot_type"] == held_out_type]
        other_hp = df[
            (df["label"] == "honeypot") &
            (df["honeypot_type"] != held_out_type)
        ]

        train_df = pd.concat([other_hp, legitimate])
        test_df = pd.concat([held_out, legitimate])

        X_train = train_df[FEATURE_COLS].astype(float).values
        y_train = train_df["label_bin"].values
        X_test = test_df[FEATURE_COLS].astype(float).values
        y_test = test_df["label_bin"].values

        log.info(
            "Held-out: %-30s  train=%d  test=%d (HP=%d, legit=%d)",
            held_out_type,
            len(train_df),
            len(test_df),
            len(held_out),
            len(legitimate),
        )

        for model_name, model in _make_models().items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            m = _metrics(y_test, y_pred, y_prob)
            records.append({
                "held_out_type": held_out_type,
                "n_held_out": len(held_out),
                "model": model_name,
                **m,
            })

    results_df = pd.DataFrame(records)
    results_df.to_csv(LOTO_RESULTS_CSV, index=False)
    log.info("Saved per-type results to %s", LOTO_RESULTS_CSV)

    # Summary: mean across held-out types per model
    metric_cols = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    summary_rows = []
    for model_name, grp in results_df.groupby("model"):
        row = {"model": model_name}
        for col in metric_cols:
            row[f"{col}_mean"] = grp[col].mean()
            row[f"{col}_std"] = grp[col].std()
        summary_rows.append(row)

    summary_df = (
        pd.DataFrame(summary_rows)
        .sort_values("f1_mean", ascending=False)
    )
    summary_df.to_csv(LOTO_SUMMARY_CSV, index=False)

    # Print per-type breakdown (RF only for readability)
    print("\n-- LOTO Results: RandomForest (per held-out type) --------------")
    rf = results_df[results_df["model"] == "RandomForest"].copy()
    print(f"  {'Type':<30}  {'N':>4}  {'F1':>6}  {'Recall':>7}  {'Precision':>9}")
    print(f"  {'-'*30}  {'-'*4}  {'-'*6}  {'-'*7}  {'-'*9}")
    for _, row in rf.sort_values("f1").iterrows():
        print(
            f"  {row['held_out_type']:<30}"
            f"  {int(row['n_held_out']):>4}"
            f"  {row['f1']:.3f}"
            f"  {row['recall']:.3f}"
            f"  {row['precision']:.3f}"
        )
    print()

    # Print model summary
    print("-- LOTO Summary (mean across all held-out types) ---------------")
    print(f"  {'Model':<22}  {'F1':>6}  {'Recall':>7}  {'AUC':>6}")
    print(f"  {'-'*22}  {'-'*6}  {'-'*7}  {'-'*6}")
    for _, row in summary_df.iterrows():
        print(
            f"  {row['model']:<22}"
            f"  {row['f1_mean']:.3f}+-{row['f1_std']:.3f}"
            f"  {row['recall_mean']:.3f}"
            f"  {row['auc_roc_mean']:.3f}"
        )
    print()


if __name__ == "__main__":
    run()
