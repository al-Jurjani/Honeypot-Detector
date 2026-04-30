"""
loto_llm_evaluation.py — Step 15: LOTO evaluation of the LLM pipeline.

For each of the 8 honeypot types, evaluates LLM predictions on the held-out
type + all legitimate contracts — mirroring the static LOTO exactly so results
are directly comparable.

Two methods:
  Method A — threshold on deception_risk_score (threshold selected on the
              other-7-types set, applied to the held-out set)
  Method B — direct is_honeypot boolean from the LLM response

Outputs
-------
outputs/results/loto_llm_results.csv    per-type metrics, both methods
outputs/results/loto_llm_summary.csv    mean +/- std across types, both methods
outputs/results/loto_comparison.csv     side-by-side: RF vs LLM-A vs LLM-B
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.utils import LABELS_PATH, RESULTS_DIR, get_logger

log = get_logger("loto_llm_evaluation")

LLM_CSV = RESULTS_DIR / "llm_features.csv"
LOTO_RF_CSV = RESULTS_DIR / "loto_results.csv"
LOTO_LLM_RESULTS_CSV = RESULTS_DIR / "loto_llm_results.csv"
LOTO_LLM_SUMMARY_CSV = RESULTS_DIR / "loto_llm_summary.csv"
LOTO_COMPARISON_CSV = RESULTS_DIR / "loto_comparison.csv"

THRESHOLDS = [4, 5, 6, 7]


def _metrics(y_true, y_pred, y_score=None) -> dict:
    try:
        auc = roc_auc_score(y_true, y_score) if y_score is not None else float("nan")
    except ValueError:
        auc = float("nan")
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "auc_roc": auc,
    }


def _best_threshold(y_true, scores) -> int:
    """Pick threshold with highest F1 on validation set."""
    best_t, best_f1 = THRESHOLDS[0], -1.0
    for t in THRESHOLDS:
        preds = (scores >= t).astype(int)
        f = f1_score(y_true, preds, zero_division=0)
        if f > best_f1:
            best_f1, best_t = f, t
    return best_t


def run() -> None:
    # Load LLM predictions — true_honeypot_type is the ground truth type
    df = pd.read_csv(LLM_CSV)
    df["label_bin"] = (df["true_label"] == "honeypot").astype(int)
    TYPE_COL = "true_honeypot_type"

    # Coerce is_honeypot to binary (handles True/False strings)
    df["is_honeypot_bin"] = (
        df["is_honeypot"].astype(str).str.lower() == "true"
    ).astype(int)

    # Fill missing scores with 0 (parse failures — none expected after 100% parse rate)
    df["deception_risk_score"] = pd.to_numeric(
        df["deception_risk_score"], errors="coerce"
    ).fillna(0)

    honeypot_types = sorted(
        df.loc[df["true_label"] == "honeypot", TYPE_COL].dropna().unique()
    )
    legitimate = df[df["true_label"] == "legitimate"]
    legit_train = legitimate.sample(frac=0.8, random_state=42)
    legit_test = legitimate.drop(legit_train.index)

    log.info(
        "Evaluating %d honeypot types, %d train legit / %d test legit",
        len(honeypot_types), len(legit_train), len(legit_test)
    )

    records = []

    for held_out_type in honeypot_types:
        held_out = df[df[TYPE_COL] == held_out_type]
        other_hp = df[
            (df["true_label"] == "honeypot") &
            (df[TYPE_COL] != held_out_type)
        ]

        # Validation set (other types) — used only for threshold selection
        val_df = pd.concat([other_hp, legit_train])
        val_true = val_df["label_bin"].values
        val_scores = val_df["deception_risk_score"].values
        best_t = _best_threshold(val_true, val_scores)

        # Test set (held-out type + held-out legitimate)
        test_df = pd.concat([held_out, legit_test])
        y_true = test_df["label_bin"].values
        scores = test_df["deception_risk_score"].values
        bool_preds = test_df["is_honeypot_bin"].values

        # Method A — threshold
        preds_a = (scores >= best_t).astype(int)
        m_a = _metrics(y_true, preds_a, scores)

        # Method B — direct boolean
        m_b = _metrics(y_true, bool_preds, scores)

        log.info(
            "%-30s  n=%3d  threshold=%d  F1-A=%.3f  F1-B=%.3f",
            held_out_type, len(held_out), best_t,
            m_a["f1"], m_b["f1"],
        )

        records.append({
            "held_out_type": held_out_type,
            "n_held_out": len(held_out),
            "best_threshold": best_t,
            **{f"A_{k}": v for k, v in m_a.items()},
            **{f"B_{k}": v for k, v in m_b.items()},
        })

    results_df = pd.DataFrame(records)
    results_df.to_csv(LOTO_LLM_RESULTS_CSV, index=False)
    log.info("Saved per-type results to %s", LOTO_LLM_RESULTS_CSV)

    # Summary: mean +/- std across types
    metric_keys = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    summary_rows = []
    for method, prefix in [("Method A (threshold)", "A_"), ("Method B (boolean)", "B_")]:
        row = {"method": method}
        for k in metric_keys:
            col = f"{prefix}{k}"
            row[f"{k}_mean"] = results_df[col].mean()
            row[f"{k}_std"] = results_df[col].std()
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(LOTO_LLM_SUMMARY_CSV, index=False)

    # Comparison table: RF vs LLM-A vs LLM-B per type
    rf = pd.read_csv(LOTO_RF_CSV)
    rf_f1 = (rf[rf["model"] == "RandomForest"]
             .set_index("held_out_type")["f1"])

    comp_rows = []
    for _, row in results_df.iterrows():
        t = row["held_out_type"]
        comp_rows.append({
            "held_out_type": t,
            "n_held_out": int(row["n_held_out"]),
            "RF_f1": round(rf_f1.get(t, float("nan")), 3),
            "LLM_A_f1": round(row["A_f1"], 3),
            "LLM_B_f1": round(row["B_f1"], 3),
            "RF_recall": round(
                rf[rf["model"] == "RandomForest"]
                .set_index("held_out_type")["recall"].get(t, float("nan")), 3),
            "LLM_A_recall": round(row["A_recall"], 3),
            "LLM_B_recall": round(row["B_recall"], 3),
        })

    comp_df = pd.DataFrame(comp_rows)

    # Add mean row
    mean_row = {
        "held_out_type": "MEAN",
        "n_held_out": "",
        "RF_f1": round(comp_df["RF_f1"].mean(), 3),
        "LLM_A_f1": round(comp_df["LLM_A_f1"].mean(), 3),
        "LLM_B_f1": round(comp_df["LLM_B_f1"].mean(), 3),
        "RF_recall": round(comp_df["RF_recall"].mean(), 3),
        "LLM_A_recall": round(comp_df["LLM_A_recall"].mean(), 3),
        "LLM_B_recall": round(comp_df["LLM_B_recall"].mean(), 3),
    }
    comp_df = pd.concat(
        [comp_df, pd.DataFrame([mean_row])], ignore_index=True
    )
    comp_df.to_csv(LOTO_COMPARISON_CSV, index=False)

    # Print full comparison table
    print("\n-- LOTO Comparison: RF vs LLM-A vs LLM-B ----------------------")
    print(f"  {'Type':<30}  {'N':>4}  {'RF':>6}  {'LLM-A':>6}  {'LLM-B':>6}  "
          f"{'RF-R':>6}  {'A-R':>6}  {'B-R':>6}")
    print(f"  {'-'*30}  {'-'*4}  {'-'*6}  {'-'*6}  {'-'*6}  "
          f"{'-'*6}  {'-'*6}  {'-'*6}")
    for _, row in comp_df.iterrows():
        n = str(row["n_held_out"]) if row["n_held_out"] != "" else "  --"
        print(
            f"  {str(row['held_out_type']):<30}  {n:>4}"
            f"  {row['RF_f1']:>6.3f}  {row['LLM_A_f1']:>6.3f}"
            f"  {row['LLM_B_f1']:>6.3f}"
            f"  {row['RF_recall']:>6.3f}  {row['LLM_A_recall']:>6.3f}"
            f"  {row['LLM_B_recall']:>6.3f}"
        )
    print()

    print("-- LLM Summary (mean across held-out types) --------------------")
    for _, row in summary_df.iterrows():
        print(
            f"  {row['method']:<25}"
            f"  F1={row['f1_mean']:.3f}+-{row['f1_std']:.3f}"
            f"  Recall={row['recall_mean']:.3f}"
            f"  Precision={row['precision_mean']:.3f}"
            f"  AUC={row['auc_roc_mean']:.3f}"
        )
    print()


if __name__ == "__main__":
    run()
