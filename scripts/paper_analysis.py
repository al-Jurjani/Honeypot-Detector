"""
paper_analysis.py — Steps 17 & 18: master comparison table + significance tests.

Step 17: Master comparison table
  Rows: Static-best, LLM-A, LLM-B, Ensemble-best
  Columns: Precision, Recall, F1, Accuracy, ROC-AUC (mean +/- std)
  Saved to: outputs/results/master_comparison_table.csv

Step 18: McNemar's test
  Compares per-contract predictions across all pipeline pairs on a shared
  test set (282 honeypot contracts from their held-out LOTO folds +
  48 held-out legitimate contracts).
  Saved to: outputs/results/mcnemar_results.csv
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from statsmodels.stats.contingency_tables import mcnemar

from src.utils import LABELS_PATH, RESULTS_DIR, get_logger

log = get_logger("paper_analysis")

STATIC_CSV    = RESULTS_DIR / "static_features.csv"
LLM_CSV       = RESULTS_DIR / "llm_features.csv"
MASTER_CSV    = RESULTS_DIR / "master_comparison_table.csv"
MCNEMAR_CSV   = RESULTS_DIR / "mcnemar_results.csv"

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
THRESHOLDS = [4, 5, 6, 7]


# ── Feature engineering ───────────────────────────────────────────────────────

def _count_list_field(series):
    def _count(val):
        if pd.isna(val) or val in ("", "[]"):
            return 0
        try:
            parsed = ast.literal_eval(str(val))
            return len(parsed) if isinstance(parsed, list) else 0
        except Exception:
            return 0
    return series.apply(_count)


def _bool_field(series):
    return (series.astype(str).str.lower() == "true").astype(int)


def _build_combined() -> pd.DataFrame:
    static = pd.read_csv(STATIC_CSV)
    llm = pd.read_csv(LLM_CSV)
    gt = pd.read_csv(LABELS_PATH)[["contract_id", "honeypot_type"]]

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

    llm_keep = ["contract_id", "true_honeypot_type",
                "deception_risk_score", "is_honeypot",
                "is_honeypot_llm", "withdrawal_possible_llm",
                "num_hidden_conditions", "num_suspicious_patterns"]
    df = static.merge(llm[llm_keep], on="contract_id", how="inner")
    df = df.merge(gt, on="contract_id", how="left")
    df["label_bin"] = (df["label"] == "honeypot").astype(int)
    return df


# ── Model factories ───────────────────────────────────────────────────────────

def _make_lr():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def _make_rf():
    return RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)


# ── LOTO helpers ──────────────────────────────────────────────────────────────

def _loto_metrics(df, feature_cols, model_factory, label_col="label_bin",
                  type_col="honeypot_type", legit_label="legitimate"):
    legitimate = df[df["label"] == legit_label]
    legit_train = legitimate.sample(frac=0.8, random_state=RANDOM_STATE)
    legit_test = legitimate.drop(legit_train.index)
    honeypot_types = sorted(
        df.loc[df["label"] == "honeypot", type_col].dropna().unique()
    )

    fold_metrics = []
    per_contract = []  # (contract_id, y_true, y_pred, y_prob)

    for htype in honeypot_types:
        held_out = df[df[type_col] == htype]
        other_hp = df[(df["label"] == "honeypot") & (df[type_col] != htype)]
        train_df = pd.concat([other_hp, legit_train])
        test_df  = pd.concat([held_out, legit_test])

        X_tr = train_df[feature_cols].astype(float).values
        y_tr = train_df[label_col].values
        X_te = test_df[feature_cols].astype(float).values
        y_te = test_df[label_col].values

        model = model_factory()
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)
        y_prob = model.predict_proba(X_te)[:, 1]

        try:
            auc = roc_auc_score(y_te, y_prob)
        except ValueError:
            auc = float("nan")

        fold_metrics.append({
            "held_out_type": htype,
            "accuracy":  accuracy_score(y_te, y_pred),
            "precision": precision_score(y_te, y_pred, zero_division=0),
            "recall":    recall_score(y_te, y_pred, zero_division=0),
            "f1":        f1_score(y_te, y_pred, zero_division=0),
            "auc_roc":   auc,
        })

        for i, cid in enumerate(test_df["contract_id"].values):
            per_contract.append((cid, y_te[i], y_pred[i], y_prob[i]))

    return pd.DataFrame(fold_metrics), per_contract


def _summary_row(label, fold_df):
    row = {"pipeline": label}
    for col in ["accuracy", "precision", "recall", "f1", "auc_roc"]:
        row[f"{col}_mean"] = fold_df[col].mean()
        row[f"{col}_std"]  = fold_df[col].std()
    return row


# ── Step 17 ───────────────────────────────────────────────────────────────────

def build_master_table(df):
    log.info("Step 17 — building master comparison table ...")

    rows = []

    # Static best (LR)
    fold_df, static_preds = _loto_metrics(
        df, STATIC_FEATURES, _make_lr
    )
    rows.append(_summary_row("Static (LogisticRegression)", fold_df))

    # Static RF (for McNemar reference)
    fold_rf, static_rf_preds = _loto_metrics(
        df, STATIC_FEATURES, _make_rf
    )
    rows.append(_summary_row("Static (RandomForest)", fold_rf))

    # Ensemble best (LR)
    fold_ens, ens_preds = _loto_metrics(
        df, ALL_FEATURES, _make_lr
    )
    rows.append(_summary_row("Ensemble (LogisticRegression)", fold_ens))

    # Ensemble RF
    fold_ens_rf, ens_rf_preds = _loto_metrics(
        df, ALL_FEATURES, _make_rf
    )
    rows.append(_summary_row("Ensemble (RandomForest)", fold_ens_rf))

    # LLM Method B — direct boolean (no training loop needed)
    legitimate = df[df["label"] == "legitimate"]
    legit_test = legitimate.sample(frac=0.2, random_state=RANDOM_STATE)
    honeypot_types = sorted(
        df.loc[df["label"] == "honeypot", "honeypot_type"].dropna().unique()
    )

    llm_fold_metrics = []
    llm_preds = []
    for htype in honeypot_types:
        held_out = df[df["honeypot_type"] == htype]
        test_df  = pd.concat([held_out, legit_test])
        y_te     = test_df["label_bin"].values
        y_pred   = test_df["is_honeypot_llm"].values
        y_prob   = pd.to_numeric(
            test_df["deception_risk_score"], errors="coerce"
        ).fillna(0).values
        try:
            auc = roc_auc_score(y_te, y_prob)
        except ValueError:
            auc = float("nan")
        llm_fold_metrics.append({
            "held_out_type": htype,
            "accuracy":  accuracy_score(y_te, y_pred),
            "precision": precision_score(y_te, y_pred, zero_division=0),
            "recall":    recall_score(y_te, y_pred, zero_division=0),
            "f1":        f1_score(y_te, y_pred, zero_division=0),
            "auc_roc":   auc,
        })
        for i, cid in enumerate(test_df["contract_id"].values):
            llm_preds.append((cid, y_te[i], y_pred[i], y_prob[i]))

    llm_fold_df = pd.DataFrame(llm_fold_metrics)
    rows.append(_summary_row("LLM (Method B — boolean)", llm_fold_df))

    # LLM Method A — threshold (select on val set)
    legit_train_full = legitimate.drop(legit_test.index)
    llm_a_fold_metrics = []
    llm_a_preds = []
    for htype in honeypot_types:
        held_out = df[df["honeypot_type"] == htype]
        other_hp = df[(df["label"] == "honeypot") & (df["honeypot_type"] != htype)]
        val_df   = pd.concat([other_hp, legit_train_full])
        test_df  = pd.concat([held_out, legit_test])

        val_true   = val_df["label_bin"].values
        val_scores = pd.to_numeric(val_df["deception_risk_score"], errors="coerce").fillna(0).values
        best_t = max(THRESHOLDS, key=lambda t: f1_score(
            val_true, (val_scores >= t).astype(int), zero_division=0
        ))
        y_te   = test_df["label_bin"].values
        y_prob = pd.to_numeric(test_df["deception_risk_score"], errors="coerce").fillna(0).values
        y_pred = (y_prob >= best_t).astype(int)
        try:
            auc = roc_auc_score(y_te, y_prob)
        except ValueError:
            auc = float("nan")
        llm_a_fold_metrics.append({
            "held_out_type": htype,
            "accuracy":  accuracy_score(y_te, y_pred),
            "precision": precision_score(y_te, y_pred, zero_division=0),
            "recall":    recall_score(y_te, y_pred, zero_division=0),
            "f1":        f1_score(y_te, y_pred, zero_division=0),
            "auc_roc":   auc,
        })
        for i, cid in enumerate(test_df["contract_id"].values):
            llm_a_preds.append((cid, y_te[i], y_pred[i], y_prob[i]))

    llm_a_fold_df = pd.DataFrame(llm_a_fold_metrics)
    rows.append(_summary_row("LLM (Method A — threshold)", llm_a_fold_df))

    table = pd.DataFrame(rows)
    table.to_csv(MASTER_CSV, index=False)

    # Pretty print
    cols = ["accuracy", "precision", "recall", "f1", "auc_roc"]
    print("\n-- Master Comparison Table (LOTO, mean +/- std) ----------------")
    header = f"  {'Pipeline':<35}"
    for c in cols:
        header += f"  {c.upper()[:7]:>14}"
    print(header)
    print("  " + "-" * 35 + ("  " + "-" * 14) * len(cols))
    for _, row in table.iterrows():
        line = f"  {row['pipeline']:<35}"
        for c in cols:
            line += f"  {row[f'{c}_mean']:.3f}+-{row[f'{c}_std']:.3f}"
        print(line)
    print()

    return table, static_preds, static_rf_preds, llm_preds, llm_a_preds, ens_preds, ens_rf_preds


# ── Step 18 ───────────────────────────────────────────────────────────────────

def _preds_to_series(preds_list):
    """Deduplicate per-contract predictions (honeypots appear once,
    legitimate appear multiple times — take first occurrence)."""
    seen = {}
    for cid, y_true, y_pred, y_prob in preds_list:
        if cid not in seen:
            seen[cid] = (y_true, y_pred, y_prob)
    df = pd.DataFrame(
        [(k, v[0], v[1], v[2]) for k, v in seen.items()],
        columns=["contract_id", "y_true", "y_pred", "y_prob"],
    )
    return df.set_index("contract_id")


def run_mcnemar(pred_a, pred_b, label_a, label_b):
    common = pred_a.index.intersection(pred_b.index)
    pa = pred_a.loc[common, "y_pred"].values
    pb = pred_b.loc[common, "y_pred"].values
    yt = pred_a.loc[common, "y_true"].values

    correct_a = (pa == yt)
    correct_b = (pb == yt)
    n01 = ((correct_a) & (~correct_b)).sum()   # A right, B wrong
    n10 = ((~correct_a) & (correct_b)).sum()   # A wrong, B right

    table = [[0, n01], [n10, 0]]
    try:
        result = mcnemar(table, exact=True)
        pval = result.pvalue
    except Exception:
        pval = float("nan")

    return {
        "pair": f"{label_a} vs {label_b}",
        "n_contracts": len(common),
        f"{label_a}_only_correct": int(n01),
        f"{label_b}_only_correct": int(n10),
        "p_value": round(pval, 4),
        "significant": pval < 0.05 if not np.isnan(pval) else False,
    }


def build_mcnemar(static_preds, llm_preds, ens_preds):
    log.info("Step 18 — running McNemar's tests ...")

    s  = _preds_to_series(static_preds)
    l  = _preds_to_series(llm_preds)
    e  = _preds_to_series(ens_preds)

    results = [
        run_mcnemar(s, l, "Static-LR", "LLM-B"),
        run_mcnemar(s, e, "Static-LR", "Ensemble-LR"),
        run_mcnemar(l, e, "LLM-B",     "Ensemble-LR"),
    ]

    df = pd.DataFrame(results)
    df.to_csv(MCNEMAR_CSV, index=False)

    print("-- McNemar's Test Results ---------------------------------------")
    print(f"  {'Pair':<30}  {'N':>5}  {'A-only':>7}  {'B-only':>7}  {'p-value':>8}  {'Sig?':>5}")
    print(f"  {'-'*30}  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*5}")
    for _, row in df.iterrows():
        sig = "YES" if row["significant"] else "no"
        only_cols = [c for c in row.index if c.endswith("_only_correct") and pd.notna(row[c])]
        a_val = int(row[only_cols[0]]) if only_cols else 0
        b_val = int(row[only_cols[1]]) if len(only_cols) > 1 else 0
        print(
            f"  {row['pair']:<30}"
            f"  {int(row['n_contracts']):>5}"
            f"  {a_val:>7}"
            f"  {b_val:>7}"
            f"  {row['p_value']:>8.4f}"
            f"  {sig:>5}"
        )
    print()
    return df


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = _build_combined()
    log.info("Combined dataset: %d contracts, %d features", len(df), len(ALL_FEATURES))

    table, static_preds, static_rf_preds, llm_b_preds, llm_a_preds, ens_preds, ens_rf_preds = \
        build_master_table(df)

    build_mcnemar(static_preds, llm_b_preds, ens_preds)

    log.info("Saved: %s", MASTER_CSV)
    log.info("Saved: %s", MCNEMAR_CSV)
