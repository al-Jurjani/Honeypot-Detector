"""
loto_ensemble.py — Step 16: LOTO evaluation of the ensemble pipeline.

Merges static + LLM features into a 15-feature set and evaluates 4 classifiers
using the same leave-one-type-out protocol as the static and LLM evaluations,
so all three pipelines are directly comparable.

Feature set (15 total)
----------------------
Static (10): uses_tx_origin, has_fallback, fallback_reverts_non_owner,
             require_count, has_selfdestruct, has_withdrawal_function,
             withdrawal_owner_only, uses_inline_assembly,
             state_changes_before_external_calls, payable_to_withdraw_ratio

LLM (5):     deception_risk_score, is_honeypot_llm, withdrawal_possible_llm,
             num_hidden_conditions, num_suspicious_patterns

Outputs
-------
outputs/results/loto_ensemble_results.csv   per-type metrics, all 4 models
outputs/results/loto_ensemble_summary.csv   mean +/- std across types
outputs/results/loto_comparison.csv         updated: static vs LLM vs ensemble
"""

import ast
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

from src.utils import LABELS_PATH, RESULTS_DIR, get_logger

log = get_logger("loto_ensemble")

STATIC_CSV = RESULTS_DIR / "static_features.csv"
LLM_CSV = RESULTS_DIR / "llm_features.csv"
LOTO_RF_CSV = RESULTS_DIR / "loto_results.csv"
LOTO_LLM_CSV = RESULTS_DIR / "loto_llm_results.csv"
ENSEMBLE_RESULTS_CSV = RESULTS_DIR / "loto_ensemble_results.csv"
ENSEMBLE_SUMMARY_CSV = RESULTS_DIR / "loto_ensemble_summary.csv"
COMPARISON_CSV = RESULTS_DIR / "loto_comparison.csv"

STATIC_FEATURES = [
    "uses_tx_origin", "has_fallback", "fallback_reverts_non_owner",
    "require_count", "has_selfdestruct", "has_withdrawal_function",
    "withdrawal_owner_only", "uses_inline_assembly",
    "state_changes_before_external_calls", "payable_to_withdraw_ratio",
]
LLM_FEATURES = [
    "deception_risk_score", "is_honeypot_llm", "withdrawal_possible_llm",
    "num_hidden_conditions", "num_suspicious_patterns",
]
ALL_FEATURES = STATIC_FEATURES + LLM_FEATURES

RANDOM_STATE = 42


def _count_list_field(series: pd.Series) -> pd.Series:
    """Count items in a stringified list field, e.g. \"['a', 'b']\" -> 2."""
    def _count(val):
        if pd.isna(val) or val == "" or val == "[]":
            return 0
        try:
            parsed = ast.literal_eval(str(val))
            return len(parsed) if isinstance(parsed, list) else 0
        except Exception:
            return 0
    return series.apply(_count)


def _bool_field(series: pd.Series) -> pd.Series:
    return (series.astype(str).str.lower() == "true").astype(int)


def _build_dataset() -> pd.DataFrame:
    static = pd.read_csv(STATIC_CSV)
    llm = pd.read_csv(LLM_CSV)
    gt = pd.read_csv(LABELS_PATH)[["contract_id", "honeypot_type"]]

    # Engineer LLM features
    llm["is_honeypot_llm"] = _bool_field(llm["is_honeypot"])
    llm["withdrawal_possible_llm"] = _bool_field(
        llm["withdrawal_possible_for_non_owner"]
    )
    llm["num_hidden_conditions"] = _count_list_field(llm["hidden_conditions"])
    llm["num_suspicious_patterns"] = _count_list_field(
        llm["suspicious_patterns"]
    )
    llm["deception_risk_score"] = pd.to_numeric(
        llm["deception_risk_score"], errors="coerce"
    ).fillna(0)

    llm_cols = ["contract_id"] + LLM_FEATURES
    df = static.merge(llm[llm_cols], on="contract_id", how="inner")
    df = df.merge(gt, on="contract_id", how="left")
    df["label_bin"] = (df["label"] == "honeypot").astype(int)
    return df


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
    df = _build_dataset()
    log.info(
        "Dataset: %d contracts, %d features",
        len(df), len(ALL_FEATURES)
    )

    honeypot_types = sorted(
        df.loc[df["label"] == "honeypot", "honeypot_type"].dropna().unique()
    )
    legitimate = df[df["label"] == "legitimate"]
    legit_train = legitimate.sample(frac=0.8, random_state=RANDOM_STATE)
    legit_test = legitimate.drop(legit_train.index)

    log.info(
        "Legitimate: %d train / %d test",
        len(legit_train), len(legit_test)
    )

    records = []

    for held_out_type in honeypot_types:
        held_out = df[df["honeypot_type"] == held_out_type]
        other_hp = df[
            (df["label"] == "honeypot") &
            (df["honeypot_type"] != held_out_type)
        ]
        train_df = pd.concat([other_hp, legit_train])
        test_df = pd.concat([held_out, legit_test])

        X_train = train_df[ALL_FEATURES].astype(float).values
        y_train = train_df["label_bin"].values
        X_test = test_df[ALL_FEATURES].astype(float).values
        y_test = test_df["label_bin"].values

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

        rf_f1 = next(
            r["f1"] for r in records
            if r["held_out_type"] == held_out_type
            and r["model"] == "RandomForest"
        )
        log.info(
            "%-30s  n=%3d  ensemble-RF F1=%.3f",
            held_out_type, len(held_out), rf_f1
        )

    results_df = pd.DataFrame(records)
    results_df.to_csv(ENSEMBLE_RESULTS_CSV, index=False)
    log.info("Saved per-type results to %s", ENSEMBLE_RESULTS_CSV)

    # Summary
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
    summary_df.to_csv(ENSEMBLE_SUMMARY_CSV, index=False)

    # Updated comparison: static RF vs LLM-B vs ensemble RF
    rf_static = (
        pd.read_csv(LOTO_RF_CSV)
        .query("model == 'RandomForest'")
        .set_index("held_out_type")
    )
    llm_b = (
        pd.read_csv(LOTO_LLM_CSV)
        .set_index("held_out_type")
    )
    ens_rf = (
        results_df.query("model == 'RandomForest'")
        .set_index("held_out_type")
    )

    comp_rows = []
    for t in honeypot_types:
        comp_rows.append({
            "held_out_type": t,
            "n_held_out": int(ens_rf.loc[t, "n_held_out"]),
            "static_RF_f1": round(float(rf_static.loc[t, "f1"]), 3),
            "LLM_B_f1": round(float(llm_b.loc[t, "B_f1"]), 3),
            "ensemble_RF_f1": round(float(ens_rf.loc[t, "f1"]), 3),
            "static_RF_recall": round(float(rf_static.loc[t, "recall"]), 3),
            "LLM_B_recall": round(float(llm_b.loc[t, "B_recall"]), 3),
            "ensemble_RF_recall": round(float(ens_rf.loc[t, "recall"]), 3),
        })

    comp_df = pd.DataFrame(comp_rows)
    mean_row = {
        "held_out_type": "MEAN",
        "n_held_out": "",
        **{c: round(comp_df[c].mean(), 3)
           for c in comp_df.columns if c not in ("held_out_type", "n_held_out")},
    }
    comp_df = pd.concat(
        [comp_df, pd.DataFrame([mean_row])], ignore_index=True
    )
    comp_df.to_csv(COMPARISON_CSV, index=False)

    # Print tables
    print("\n-- LOTO Ensemble Results: RandomForest -------------------------")
    print(f"  {'Type':<30}  {'N':>4}  {'Static':>7}  {'LLM-B':>6}  {'Ensemble':>9}")
    print(f"  {'-'*30}  {'-'*4}  {'-'*7}  {'-'*6}  {'-'*9}")
    for _, row in comp_df.iterrows():
        n = str(int(row["n_held_out"])) if row["n_held_out"] != "" else "--"
        print(
            f"  {str(row['held_out_type']):<30}  {n:>4}"
            f"  {row['static_RF_f1']:>7.3f}"
            f"  {row['LLM_B_f1']:>6.3f}"
            f"  {row['ensemble_RF_f1']:>9.3f}"
        )
    print()

    print("-- Ensemble Summary (all 4 models, mean across types) ----------")
    print(f"  {'Model':<22}  {'F1':>6}  {'Recall':>7}  {'Precision':>10}  {'AUC':>6}")
    print(f"  {'-'*22}  {'-'*6}  {'-'*7}  {'-'*10}  {'-'*6}")
    for _, row in summary_df.iterrows():
        print(
            f"  {row['model']:<22}"
            f"  {row['f1_mean']:.3f}+-{row['f1_std']:.3f}"
            f"  {row['recall_mean']:.3f}"
            f"  {row['precision_mean']:.3f}"
            f"  {row['auc_roc_mean']:.3f}"
        )
    print()


if __name__ == "__main__":
    run()
