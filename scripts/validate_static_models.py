"""
validate_static_models.py — Diagnostic validation for static feature results.

Runs two checks to confirm the Step 14 CV results are genuine:

  1. Permutation test  — shuffles labels 100 times and retrains RF each time.
     If real accuracy >> permuted accuracy, features are genuinely predictive.
     Output: outputs/results/static_permutation_test.csv

  2. Single-feature baselines — trains RF on each feature in isolation.
     Reveals which features drive performance and whether any one feature
     alone explains the result.
     Output: outputs/results/static_single_feature_baselines.csv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score

from src.utils import RESULTS_DIR, get_logger

log = get_logger("validate_static_models")

STATIC_CSV = RESULTS_DIR / "static_features.csv"
PERMUTATION_CSV = RESULTS_DIR / "static_permutation_test.csv"
SINGLE_FEATURE_CSV = RESULTS_DIR / "static_single_feature_baselines.csv"

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
N_PERMUTATIONS = 100


def _cv_f1(X, y, seed=RANDOM_STATE) -> float:
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed)
    rf = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
    scores = cross_val_score(rf, X, y, cv=skf, scoring="f1")
    return scores.mean()


def run_permutation_test(X, y) -> pd.DataFrame:
    log.info("Running permutation test (%d permutations) ...", N_PERMUTATIONS)

    real_f1 = _cv_f1(X, y)
    log.info("Real F1: %.4f", real_f1)

    rng = np.random.default_rng(RANDOM_STATE)
    perm_f1s = []
    for i in range(N_PERMUTATIONS):
        y_shuffled = rng.permutation(y)
        perm_f1s.append(_cv_f1(X, y_shuffled, seed=i))
        if (i + 1) % 20 == 0:
            log.info("  %d/%d done (mean permuted F1 so far: %.4f)",
                     i + 1, N_PERMUTATIONS, np.mean(perm_f1s))

    perm_f1s = np.array(perm_f1s)
    p_value = (perm_f1s >= real_f1).mean()

    summary = pd.DataFrame([{
        "real_f1": real_f1,
        "permuted_f1_mean": perm_f1s.mean(),
        "permuted_f1_std": perm_f1s.std(),
        "permuted_f1_max": perm_f1s.max(),
        "p_value": p_value,
        "n_permutations": N_PERMUTATIONS,
    }])
    detail = pd.DataFrame({
        "permutation": range(1, N_PERMUTATIONS + 1),
        "f1": perm_f1s,
    })
    full = pd.concat([summary.assign(type="summary"),
                      detail.assign(type="permutation")], ignore_index=True)
    full.to_csv(PERMUTATION_CSV, index=False)

    print("\n-- Permutation Test ---------------------------------------------")
    print(f"  Real F1:              {real_f1:.4f}")
    print(f"  Permuted F1 (mean):   {perm_f1s.mean():.4f} +/- {perm_f1s.std():.4f}")
    print(f"  Permuted F1 (max):    {perm_f1s.max():.4f}")
    print(f"  p-value:              {p_value:.4f}")
    if p_value < 0.05:
        print("  RESULT: features are GENUINELY predictive (p < 0.05)")
    else:
        print("  RESULT: WARNING — cannot rule out chance (p >= 0.05)")
    print()

    return summary


def run_single_feature_baselines(X, y, feature_names) -> pd.DataFrame:
    log.info("Running single-feature baselines ...")
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    rows = []
    for i, feat in enumerate(feature_names):
        X_single = X[:, i].reshape(-1, 1)
        rf = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
        f1_scores = cross_val_score(rf, X_single, y, cv=skf, scoring="f1")
        acc_scores = cross_val_score(rf, X_single, y, cv=skf, scoring="accuracy")
        rows.append({
            "feature": feat,
            "f1_mean": f1_scores.mean(),
            "f1_std": f1_scores.std(),
            "accuracy_mean": acc_scores.mean(),
            "accuracy_std": acc_scores.std(),
        })

    df = (pd.DataFrame(rows)
          .sort_values("f1_mean", ascending=False)
          .reset_index(drop=True))
    df.to_csv(SINGLE_FEATURE_CSV, index=False)

    print("-- Single-Feature Baselines (RF, 5-fold CV) --------------------")
    print(f"  {'Feature':<42}  {'F1':>6}  {'Accuracy':>9}")
    print(f"  {'-'*42}  {'-'*6}  {'-'*9}")
    for _, row in df.iterrows():
        print(
            f"  {row['feature']:<42}"
            f"  {row['f1_mean']:.3f}"
            f"+-{row['f1_std']:.3f}"
            f"  {row['accuracy_mean']:.3f}"
            f"+-{row['accuracy_std']:.3f}"
        )
    print()

    return df


if __name__ == "__main__":
    df = pd.read_csv(STATIC_CSV)
    df["label_bin"] = (df["label"] == "honeypot").astype(int)
    X = df[FEATURE_COLS].astype(float).values
    y = df["label_bin"].values

    run_permutation_test(X, y)
    run_single_feature_baselines(X, y, FEATURE_COLS)

    log.info("Saved: %s", PERMUTATION_CSV)
    log.info("Saved: %s", SINGLE_FEATURE_CSV)
