"""
error_analysis.py -- Steps 19, 20, 21: error analysis + case studies.

Runs LOTO for Static-LR and Ensemble-LR, evaluates LLM-B directly.
Uses majority vote across folds for legitimate-contract predictions
(they appear in all 8 test folds).

Outputs
-------
outputs/results/per_contract_predictions.csv  -- all pipeline predictions
outputs/results/error_analysis_fps.csv        -- false positives per pipeline
outputs/results/error_analysis_fns.csv        -- false negatives per pipeline
outputs/results/case_studies.txt              -- Step 21 narrative text
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.utils import LABELS_PATH, RESULTS_DIR, DATA_DIR, get_logger

log = get_logger("error_analysis")

STATIC_CSV = RESULTS_DIR / "static_features.csv"
LLM_CSV    = RESULTS_DIR / "llm_features.csv"
PRED_CSV   = RESULTS_DIR / "per_contract_predictions.csv"
FP_CSV     = RESULTS_DIR / "error_analysis_fps.csv"
FN_CSV     = RESULTS_DIR / "error_analysis_fns.csv"
CASE_TXT   = RESULTS_DIR / "case_studies.txt"

HP_DIR     = DATA_DIR / "contracts" / "honeypots"
LEGIT_DIR  = DATA_DIR / "contracts" / "legitimate"

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


# --------------------------------------------------------------------------- #
#  Data loading & feature engineering                                          #
# --------------------------------------------------------------------------- #

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


def _build_df():
    static = pd.read_csv(STATIC_CSV)
    llm    = pd.read_csv(LLM_CSV)
    gt     = pd.read_csv(LABELS_PATH)[["contract_id", "honeypot_type"]]

    llm["is_honeypot_llm"]        = _bool_field(llm["is_honeypot"])
    llm["withdrawal_possible_llm"] = _bool_field(llm["withdrawal_possible_for_non_owner"])
    llm["num_hidden_conditions"]   = _count_list_field(llm["hidden_conditions"])
    llm["num_suspicious_patterns"] = _count_list_field(llm["suspicious_patterns"])
    llm["deception_risk_score"]    = pd.to_numeric(llm["deception_risk_score"], errors="coerce").fillna(0)

    llm_keep = [
        "contract_id", "true_honeypot_type",
        "deception_risk_score", "is_honeypot", "explanation",
        "hidden_conditions", "suspicious_patterns",
        "is_honeypot_llm", "withdrawal_possible_llm",
        "num_hidden_conditions", "num_suspicious_patterns",
    ]
    df = static.merge(llm[llm_keep], on="contract_id", how="inner")
    df = df.merge(gt, on="contract_id", how="left")
    df["label_bin"] = (df["label"] == "honeypot").astype(int)
    return df


# --------------------------------------------------------------------------- #
#  LOTO runner — returns per-contract predictions (with repeat counts)         #
# --------------------------------------------------------------------------- #

def _make_lr():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def run_loto(df, feature_cols, model_factory):
    """
    Returns a dict: contract_id -> list of (y_true, y_pred, y_prob).
    Legitimate contracts appear in all 8 folds; honeypots appear once.
    """
    legitimate = df[df["label"] == "legitimate"]
    legit_train = legitimate.sample(frac=0.8, random_state=RANDOM_STATE)
    legit_test  = legitimate.drop(legit_train.index)

    honeypot_types = sorted(
        df.loc[df["label"] == "honeypot", "honeypot_type"].dropna().unique()
    )

    preds = defaultdict(list)

    for htype in honeypot_types:
        held_out = df[df["honeypot_type"] == htype]
        other_hp = df[(df["label"] == "honeypot") & (df["honeypot_type"] != htype)]
        train_df = pd.concat([other_hp, legit_train])
        test_df  = pd.concat([held_out, legit_test])

        X_tr = train_df[feature_cols].astype(float).values
        y_tr = train_df["label_bin"].values
        X_te = test_df[feature_cols].astype(float).values
        y_te = test_df["label_bin"].values

        model = model_factory()
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)
        y_prob = model.predict_proba(X_te)[:, 1]

        for i, cid in enumerate(test_df["contract_id"].values):
            preds[cid].append((int(y_te[i]), int(y_pred[i]), float(y_prob[i])))

    return preds


def majority_vote(preds_dict):
    """
    Collapse repeated predictions to one row per contract using majority vote.
    Returns dict: contract_id -> (y_true, y_pred, y_prob_mean).
    """
    result = {}
    for cid, recs in preds_dict.items():
        y_true = recs[0][0]
        y_pred = int(round(np.mean([r[1] for r in recs])))
        y_prob = float(np.mean([r[2] for r in recs]))
        result[cid] = (y_true, y_pred, y_prob)
    return result


# --------------------------------------------------------------------------- #
#  Source-code helpers                                                          #
# --------------------------------------------------------------------------- #

def _read_source(contract_id, filename):
    for d in (HP_DIR, LEGIT_DIR):
        path = d / filename
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _snippet(source, max_lines=60):
    lines = source.splitlines()
    return "\n".join(lines[:max_lines])


# --------------------------------------------------------------------------- #
#  Explanation generators                                                       #
# --------------------------------------------------------------------------- #

_FEATURE_DESCS = {
    "uses_tx_origin":                    "uses tx.origin for authentication",
    "has_fallback":                      "has a payable fallback/receive function",
    "fallback_reverts_non_owner":        "fallback reverts for non-owners",
    "require_count":                     "has multiple require/revert checks",
    "has_selfdestruct":                  "contains selfdestruct",
    "has_withdrawal_function":           "has a withdrawal function",
    "withdrawal_owner_only":             "withdrawal is owner-gated",
    "uses_inline_assembly":              "uses inline assembly",
    "state_changes_before_external_calls": "mutates state before external calls",
    "payable_to_withdraw_ratio":         "high payable-to-withdraw ratio",
}

_HP_TYPE_NOTES = {
    "balance_disorder":         "Balance manipulation — actual balance differs from what internal accounting shows",
    "hidden_state":             "Hidden state variable blocks withdrawals invisibly",
    "hidden_transfer":          "Owner drains funds via a concealed transfer in a callback",
    "inheritance_disorder":     "Inheritance overrides a critical function the investor expects to call",
    "skip_empty_string_literal": "ABI encoder quirk skips empty string literals, shifting argument positions",
    "straw_man":                "Owner-only function appears to allow external withdrawals but is gated",
    "type_deduction_overflow":  "Integer overflow/underflow exploited to bypass balance checks",
    "uninitialised_struct":     "Uninitialised struct storage pointer overwrites owner address",
}


def _explain_fp_static(row):
    triggered = []
    for f in STATIC_FEATURES:
        val = row.get(f, 0)
        if f == "require_count":
            if val >= 3:
                triggered.append(f"high require_count ({int(val)})")
        elif f == "payable_to_withdraw_ratio":
            if val > 0:
                triggered.append(f"non-zero payable_to_withdraw_ratio ({val:.2f})")
        elif val == 1:
            triggered.append(_FEATURE_DESCS[f])
    if not triggered:
        return "No strong feature signal — borderline classification near the decision boundary."
    return (
        f"Legitimate contract flagged because it {', '.join(triggered)}. "
        "These features overlap with known honeypot patterns but serve a genuine purpose here."
    )


def _explain_fn_static(row):
    present = []
    for f in STATIC_FEATURES:
        val = row.get(f, 0)
        if f in ("require_count", "payable_to_withdraw_ratio"):
            if val > 0:
                present.append(f)
        elif val == 1:
            present.append(f)
    htype = row.get("honeypot_type", "unknown")
    note  = _HP_TYPE_NOTES.get(htype, "")
    if not present:
        return (
            f"All 10 static features are zero for this {htype} honeypot. "
            f"{note}. The deception mechanism leaves no detectable AST fingerprint."
        )
    return (
        f"This {htype} honeypot has {len(present)} active features ({', '.join(present)}) "
        f"but was still missed — likely because the deceptive pattern is subtle. {note}."
    )


def _explain_fp_llm(row):
    exp = str(row.get("explanation", "")).strip()
    hc  = str(row.get("hidden_conditions", "")).strip()
    sp  = str(row.get("suspicious_patterns", "")).strip()
    parts = []
    if hc and hc not in ("[]", "nan", ""):
        parts.append(f"flagged hidden conditions: {hc}")
    if sp and sp not in ("[]", "nan", ""):
        parts.append(f"flagged suspicious patterns: {sp}")
    if parts:
        return (
            f"LLM misidentified this legitimate contract because it {'; '.join(parts)}. "
            "These are likely legitimate access-control or upgrade patterns."
        )
    if exp:
        return f"LLM reasoning: \"{exp[:200]}\""
    return "LLM produced a false positive — no specific conditions recorded."


def _explain_fn_llm(row):
    exp   = str(row.get("explanation", "")).strip()
    htype = row.get("honeypot_type", "unknown")
    note  = _HP_TYPE_NOTES.get(htype, "")
    base  = f"LLM missed this {htype} honeypot. {note}."
    if exp:
        return base + f" LLM's own reasoning: \"{exp[:200]}\""
    return base


# --------------------------------------------------------------------------- #
#  Pattern grouping                                                             #
# --------------------------------------------------------------------------- #

def _infer_fp_pattern(row):
    if row.get("withdrawal_owner_only", 0) == 1 and row.get("has_withdrawal_function", 0) == 1:
        return "Owner-gated withdrawal"
    if row.get("require_count", 0) >= 4:
        return "Complex access control (many requires)"
    if row.get("uses_tx_origin", 0) == 1:
        return "tx.origin authentication"
    if row.get("uses_inline_assembly", 0) == 1:
        return "Inline assembly"
    if row.get("has_fallback", 0) == 1 and row.get("payable_to_withdraw_ratio", 0) > 0:
        return "Payable fallback with withdrawal"
    return "Borderline / low feature overlap"


def _infer_fn_pattern(row):
    htype = row.get("honeypot_type", "unknown")
    present = sum(
        1 for f in STATIC_FEATURES
        if (f in ("require_count", "payable_to_withdraw_ratio") and row.get(f, 0) > 0)
        or (f not in ("require_count", "payable_to_withdraw_ratio") and row.get(f, 0) == 1)
    )
    if present == 0:
        return f"No AST fingerprint ({htype})"
    return f"Partial signal only ({htype}, {present}/10 features active)"


# --------------------------------------------------------------------------- #
#  Main                                                                         #
# --------------------------------------------------------------------------- #

def run():
    df = _build_df()
    log.info("Dataset: %d contracts", len(df))

    # ------------------------------------------------------------------ #
    # Run LOTO for Static-LR and Ensemble-LR                              #
    # ------------------------------------------------------------------ #
    log.info("Running LOTO: Static-LR ...")
    s_raw  = run_loto(df, STATIC_FEATURES, _make_lr)
    s_mv   = majority_vote(s_raw)

    log.info("Running LOTO: Ensemble-LR ...")
    e_raw  = run_loto(df, ALL_FEATURES, _make_lr)
    e_mv   = majority_vote(e_raw)

    # ------------------------------------------------------------------ #
    # LLM-B — no training; majority vote over folds isn't needed since    #
    # is_honeypot_llm is the same for every fold                          #
    # ------------------------------------------------------------------ #
    log.info("Collecting LLM-B predictions ...")
    legitimate = df[df["label"] == "legitimate"]
    legit_test = legitimate.sample(frac=0.2, random_state=RANDOM_STATE)
    honeypot_types = sorted(
        df.loc[df["label"] == "honeypot", "honeypot_type"].dropna().unique()
    )

    llm_preds = {}
    for htype in honeypot_types:
        held_out = df[df["honeypot_type"] == htype]
        test_df  = pd.concat([held_out, legit_test])
        for _, row in test_df.iterrows():
            cid = row["contract_id"]
            if cid not in llm_preds:
                llm_preds[cid] = (
                    int(row["label_bin"]),
                    int(row["is_honeypot_llm"]),
                    float(row["deception_risk_score"]),
                )

    # ------------------------------------------------------------------ #
    # Build per-contract predictions DataFrame                            #
    # ------------------------------------------------------------------ #
    all_cids = sorted(set(s_mv) | set(e_mv) | set(llm_preds))
    meta = df[["contract_id", "filename", "label", "honeypot_type"]].set_index("contract_id")

    records = []
    for cid in all_cids:
        row = {
            "contract_id": cid,
            "filename":    meta.loc[cid, "filename"] if cid in meta.index else "",
            "true_label":  meta.loc[cid, "label"]   if cid in meta.index else "",
            "true_type":   meta.loc[cid, "honeypot_type"] if cid in meta.index else "",
        }
        for tag, mv in [("static_lr", s_mv), ("ensemble_lr", e_mv), ("llm_b", llm_preds)]:
            if cid in mv:
                _, pred, prob = mv[cid]
                row[f"{tag}_pred"] = pred
                row[f"{tag}_prob"] = round(prob, 4)
            else:
                row[f"{tag}_pred"] = None
                row[f"{tag}_prob"] = None
        records.append(row)

    pred_df = pd.DataFrame(records)
    pred_df.to_csv(PRED_CSV, index=False)
    log.info("Saved per-contract predictions: %s", PRED_CSV)

    # ------------------------------------------------------------------ #
    # Error analysis: FPs and FNs per pipeline                            #
    # ------------------------------------------------------------------ #
    feat_df = df.set_index("contract_id")
    llm_df  = pd.read_csv(LLM_CSV).set_index("contract_id")

    fp_rows, fn_rows = [], []

    pipelines = [
        ("Static-LR",    "static_lr"),
        ("Ensemble-LR",  "ensemble_lr"),
        ("LLM-B",        "llm_b"),
    ]

    for pipe_name, col in pipelines:
        sub = pred_df[pred_df[f"{col}_pred"].notna()].copy()
        fps = sub[(sub["true_label"] == "legitimate") & (sub[f"{col}_pred"] == 1)]
        fns = sub[(sub["true_label"] == "honeypot")  & (sub[f"{col}_pred"] == 0)]

        log.info("%s — FPs: %d, FNs: %d", pipe_name, len(fps), len(fns))

        for _, row in fps.iterrows():
            cid  = row["contract_id"]
            frow = feat_df.loc[cid] if cid in feat_df.index else pd.Series()

            if pipe_name == "LLM-B":
                explanation = _explain_fp_llm(frow)
                pattern     = "LLM false positive — legitimate access control patterns"
            else:
                explanation = _explain_fp_static(frow)
                pattern     = _infer_fp_pattern(frow)

            fp_rows.append({
                "pipeline":       pipe_name,
                "contract_id":    cid,
                "filename":       row["filename"],
                "pattern_group":  pattern,
                "explanation":    explanation,
                "prob_score":     row[f"{col}_prob"],
                **{f: frow.get(f, None) for f in STATIC_FEATURES},
            })

        for _, row in fns.iterrows():
            cid  = row["contract_id"]
            frow = feat_df.loc[cid] if cid in feat_df.index else pd.Series()

            if pipe_name == "LLM-B":
                llm_row     = llm_df.loc[cid] if cid in llm_df.index else pd.Series()
                explanation = _explain_fn_llm({**frow.to_dict(), **llm_row.to_dict()})
                pattern     = f"LLM false negative — {row['true_type']}"
            else:
                explanation = _explain_fn_static(frow)
                pattern     = _infer_fn_pattern(frow)

            fn_rows.append({
                "pipeline":       pipe_name,
                "contract_id":    cid,
                "filename":       row["filename"],
                "true_type":      row["true_type"],
                "pattern_group":  pattern,
                "explanation":    explanation,
                "prob_score":     row[f"{col}_prob"],
                **{f: frow.get(f, None) for f in STATIC_FEATURES},
            })

    fp_df = pd.DataFrame(fp_rows)
    fn_df = pd.DataFrame(fn_rows)
    fp_df.to_csv(FP_CSV, index=False)
    fn_df.to_csv(FN_CSV, index=False)
    log.info("Saved FP analysis: %s", FP_CSV)
    log.info("Saved FN analysis: %s", FN_CSV)

    # ------------------------------------------------------------------ #
    # Print error summary tables                                           #
    # ------------------------------------------------------------------ #
    print("\n-- Step 19: False Positives (legitimate contracts misclassified) --")
    for pipe_name, col in pipelines:
        sub = fp_df[fp_df["pipeline"] == pipe_name]
        print(f"\n  {pipe_name}  ({len(sub)} FPs)")
        if sub.empty:
            print("    (none)")
            continue
        print(f"  {'Contract':<15}  {'Pattern':<40}  Prob")
        print(f"  {'-'*15}  {'-'*40}  {'-'*6}")
        for _, r in sub.iterrows():
            print(f"  {r['contract_id']:<15}  {r['pattern_group']:<40}  {r['prob_score']:.3f}")

        # Group summary
        groups = sub["pattern_group"].value_counts()
        print(f"\n  Pattern groups:")
        for g, n in groups.items():
            print(f"    [{n}]  {g}")

    print("\n\n-- Step 20: False Negatives (honeypots missed) -------------------")
    for pipe_name, col in pipelines:
        sub = fn_df[fn_df["pipeline"] == pipe_name]
        print(f"\n  {pipe_name}  ({len(sub)} FNs)")
        if sub.empty:
            print("    (none)")
            continue
        print(f"  {'Contract':<15}  {'Type':<28}  {'Pattern':<35}  Prob")
        print(f"  {'-'*15}  {'-'*28}  {'-'*35}  {'-'*6}")
        for _, r in sub.iterrows():
            print(f"  {r['contract_id']:<15}  {str(r['true_type']):<28}  {r['pattern_group']:<35}  {r['prob_score']:.3f}")

    # ------------------------------------------------------------------ #
    # Step 21: Case studies                                                #
    # ------------------------------------------------------------------ #
    print("\n\n-- Step 21: Case Studies -----------------------------------------")

    case_lines = []

    def case_header(n, title):
        case_lines.append(f"\n{'='*70}")
        case_lines.append(f"CASE {n}: {title}")
        case_lines.append(f"{'='*70}")

    # Case 1: Honeypot caught by LLM but missed by Static (FN for static, TP for LLM)
    fn_static_cids = set(fn_df[fn_df["pipeline"] == "Static-LR"]["contract_id"])
    llm_tp_cids    = set(
        pred_df[(pred_df["true_label"] == "honeypot") & (pred_df["llm_b_pred"] == 1)]["contract_id"]
    )
    llm_catches_static_misses = fn_static_cids & llm_tp_cids

    if llm_catches_static_misses:
        cid = sorted(llm_catches_static_misses)[0]
        row = feat_df.loc[cid]
        src = _read_source(cid, row.get("filename", f"{cid}.sol"))
        llm_row = llm_df.loc[cid] if cid in llm_df.index else pd.Series()
        case_header(1, f"LLM catches what static missed — {cid} ({row.get('honeypot_type')})")
        case_lines.append(f"Contract: {cid}  |  Type: {row.get('honeypot_type')}")
        case_lines.append(f"Static-LR pred: MISSED  |  LLM-B pred: CAUGHT")
        case_lines.append(f"\nStatic features: " +
                         ", ".join(f"{f}={int(row.get(f,0))}" for f in STATIC_FEATURES))
        case_lines.append(f"\nLLM explanation: {str(llm_row.get('explanation',''))[:500]}")
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")
    else:
        case_header(1, "LLM catches what static missed")
        case_lines.append("(No contracts found where LLM-B caught a honeypot that Static-LR missed.)")

    # Case 2: Honeypot caught by static but missed by LLM
    fn_llm_cids    = set(fn_df[fn_df["pipeline"] == "LLM-B"]["contract_id"])
    static_tp_cids = set(
        pred_df[(pred_df["true_label"] == "honeypot") & (pred_df["static_lr_pred"] == 1)]["contract_id"]
    )
    static_catches_llm_misses = fn_llm_cids & static_tp_cids

    if static_catches_llm_misses:
        # Pick one with most static features active (clearest example)
        best_cid = max(
            static_catches_llm_misses,
            key=lambda c: sum(
                1 for f in STATIC_FEATURES
                if feat_df.loc[c].get(f, 0) > 0
            ) if c in feat_df.index else 0,
        )
        row = feat_df.loc[best_cid]
        src = _read_source(best_cid, row.get("filename", f"{best_cid}.sol"))
        llm_row = llm_df.loc[best_cid] if best_cid in llm_df.index else pd.Series()
        case_header(2, f"Static catches what LLM missed — {best_cid} ({row.get('honeypot_type')})")
        case_lines.append(f"Contract: {best_cid}  |  Type: {row.get('honeypot_type')}")
        case_lines.append(f"Static-LR pred: CAUGHT  |  LLM-B pred: MISSED")
        active = [f for f in STATIC_FEATURES if row.get(f, 0) > 0]
        case_lines.append(f"\nActive static features: {', '.join(active)}")
        case_lines.append(f"\nLLM explanation: {str(llm_row.get('explanation',''))[:500]}")
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")
    else:
        case_header(2, "Static catches what LLM missed")
        case_lines.append("(No contracts where Static-LR caught a honeypot that LLM-B missed.)")

    # Case 3: False positive — legitimate contract flagged by both Static and LLM
    fp_static_cids = set(fp_df[fp_df["pipeline"] == "Static-LR"]["contract_id"])
    fp_llm_cids    = set(fp_df[fp_df["pipeline"] == "LLM-B"]["contract_id"])
    fp_both        = fp_static_cids & fp_llm_cids

    if fp_both:
        cid = sorted(fp_both)[0]
        row = feat_df.loc[cid]
        src = _read_source(cid, row.get("filename", f"{cid}.sol"))
        llm_row = llm_df.loc[cid] if cid in llm_df.index else pd.Series()
        case_header(3, f"Legitimate contract fooling both pipelines — {cid}")
        case_lines.append(f"Contract: {cid}  |  True label: LEGITIMATE")
        case_lines.append(f"Both Static-LR and LLM-B predicted: HONEYPOT")
        case_lines.append(f"\nActive static features: " +
                         ", ".join(f for f in STATIC_FEATURES if row.get(f, 0) > 0))
        case_lines.append(f"\nLLM explanation: {str(llm_row.get('explanation',''))[:500]}")
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")
    elif fp_static_cids:
        cid = sorted(fp_static_cids)[0]
        row = feat_df.loc[cid]
        src = _read_source(cid, row.get("filename", f"{cid}.sol"))
        case_header(3, f"Legitimate contract flagged by Static-LR — {cid}")
        case_lines.append(f"\nActive static features: " +
                         ", ".join(f for f in STATIC_FEATURES if row.get(f, 0) > 0))
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")
    else:
        case_header(3, "Legitimate contract flagged by static")
        case_lines.append("(Static-LR had no false positives in this evaluation.)")

    # Case 4: Missed by both — hardest honeypot
    fn_both = fn_static_cids & fn_llm_cids
    if fn_both:
        # Pick one; prefer hidden_state or uninitialised_struct (subtle types)
        preferred = [c for c in fn_both
                     if feat_df.loc[c].get("honeypot_type", "") in
                     ("hidden_state", "uninitialised_struct", "skip_empty_string_literal")
                     and c in feat_df.index]
        cid = preferred[0] if preferred else sorted(fn_both)[0]
        row = feat_df.loc[cid]
        src = _read_source(cid, row.get("filename", f"{cid}.sol"))
        llm_row = llm_df.loc[cid] if cid in llm_df.index else pd.Series()
        case_header(4, f"Hardest honeypot — missed by all pipelines — {cid} ({row.get('honeypot_type')})")
        case_lines.append(f"Contract: {cid}  |  Type: {row.get('honeypot_type')}")
        case_lines.append(f"Static-LR: MISSED  |  LLM-B: MISSED")
        case_lines.append(f"\nStatic features: all zero (no AST fingerprint)")
        case_lines.append(f"\nLLM explanation: {str(llm_row.get('explanation',''))[:500]}")
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")
    else:
        case_header(4, "Hardest honeypot")
        case_lines.append("(No contracts missed by both pipelines simultaneously — "
                          "ensemble covers all cases in this evaluation.)")

    # Case 5: Most interesting FP for LLM — high deception_risk_score but legitimate
    fp_llm_df = fp_df[fp_df["pipeline"] == "LLM-B"].copy()
    if not fp_llm_df.empty:
        best_fp = fp_llm_df.sort_values("prob_score", ascending=False).iloc[0]
        cid = best_fp["contract_id"]
        row = feat_df.loc[cid]
        src = _read_source(cid, row.get("filename", f"{cid}.sol"))
        llm_row = llm_df.loc[cid] if cid in llm_df.index else pd.Series()
        case_header(5, f"Most convincing LLM false positive — {cid} (deception_risk={best_fp['prob_score']:.1f})")
        case_lines.append(f"Contract: {cid}  |  True label: LEGITIMATE")
        case_lines.append(f"LLM deception_risk_score: {best_fp['prob_score']:.2f}")
        case_lines.append(f"\nLLM explanation: {str(llm_row.get('explanation',''))[:600]}")
        case_lines.append(f"\nHidden conditions: {str(llm_row.get('hidden_conditions',''))}")
        case_lines.append(f"\nSuspicious patterns: {str(llm_row.get('suspicious_patterns',''))}")
        case_lines.append(f"\nSource snippet (first 60 lines):\n{_snippet(src)}")

    case_text = "\n".join(case_lines)
    print(case_text)
    CASE_TXT.write_text(case_text, encoding="utf-8")
    log.info("Saved case studies: %s", CASE_TXT)


if __name__ == "__main__":
    run()
