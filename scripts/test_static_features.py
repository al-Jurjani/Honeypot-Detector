"""
test_static_features.py — Smoke-test static feature extraction on 20 sample
contracts (10 honeypots + 10 legitimate), print a formatted table, and run
heuristic sanity checks.

Usage (from project root):
    python -m scripts.test_static_features
"""

import sys

import pandas as pd

from src.static_features import extract_features
from src.utils import HONEYPOT_DIR, LEGIT_DIR, RESULTS_DIR, load_ground_truth

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

SHORT = {
    "uses_tx_origin": "tx_orig",
    "has_fallback": "fallbk",
    "fallback_reverts_non_owner": "fb_rev",
    "require_count": "req_n",
    "has_selfdestruct": "slfdes",
    "has_withdrawal_function": "wdraw",
    "withdrawal_owner_only": "wd_own",
    "uses_inline_assembly": "asm",
    "state_changes_before_external_calls": "st_ext",
    "payable_to_withdraw_ratio": "p/w",
}


def main() -> None:
    hp_files = sorted(HONEYPOT_DIR.glob("*.sol"))[:10]
    legit_files = sorted(LEGIT_DIR.glob("*.sol"))[:10]

    if len(hp_files) < 10 or len(legit_files) < 10:
        print(
            f"Need at least 10 files in each folder. "
            f"Found {len(hp_files)} honeypots, {len(legit_files)} legitimate."
        )
        sys.exit(1)

    # Load ground truth for label lookup by filename
    gt = load_ground_truth()
    gt_labels = dict(zip(gt["filename"], gt["label"]))

    rows = []
    success = 0
    failed = 0

    for fpath, folder_label in [
        *[(f, "honeypot") for f in hp_files],
        *[(f, "legitimate") for f in legit_files],
    ]:
        feats = extract_features(fpath)
        if feats is None:
            print(f"  SKIP (unreadable): {fpath.name}")
            failed += 1
            continue
        success += 1
        # Use ground truth label if available, else folder label
        label = gt_labels.get(fpath.name, folder_label)
        feats["filename"] = fpath.name
        feats["label"] = label
        rows.append(feats)

    df = pd.DataFrame(rows)
    col_order = ["filename", "label"] + FEATURE_COLS
    df = df[col_order]

    # ── Print formatted table ─────────────────────────────────────
    short_heads = ["filename", "label"] + [SHORT[c] for c in FEATURE_COLS]
    widths = []
    for i, col in enumerate(col_order):
        header_w = len(short_heads[i])
        data_w = df[col].astype(str).str.len().max()
        widths.append(max(header_w, data_w))

    header_line = "  ".join(h.rjust(w) for h, w in zip(short_heads, widths))
    sep = "  ".join("-" * w for w in widths)

    print()
    print(header_line)
    print(sep)
    for _, row in df.iterrows():
        vals = []
        for col, w in zip(col_order, widths):
            v = row[col]
            if isinstance(v, bool):
                s = "T" if v else "."
            elif isinstance(v, float):
                s = f"{v:.1f}"
            else:
                s = str(v)
            vals.append(s.rjust(w))
        print("  ".join(vals))

    # ── Summary ───────────────────────────────────────────────────
    print()
    print(f"Processed: {success} OK, {failed} failed")

    # ── Save CSV ──────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "static_features_test20.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

    # ── Sanity Check Flags ────────────────────────────────────────
    flags = []

    for _, row in df.iterrows():
        name = row["filename"]
        label = row["label"]
        tag = f"  {name} ({label})"

        if row["uses_tx_origin"]:
            flags.append(f"{tag} -- uses tx.origin")

        if row["has_withdrawal_function"] and not row["withdrawal_owner_only"]:
            flags.append(
                f"{tag} -- has withdraw but NOT owner-only"
            )

        if row["payable_to_withdraw_ratio"] > 3.0:
            flags.append(
                f"{tag} -- suspicious payable/withdraw ratio "
                f"({row['payable_to_withdraw_ratio']:.1f})"
            )

        if row["require_count"] == 0:
            flags.append(f"{tag} -- zero require() calls")

        if row["has_fallback"] and row["fallback_reverts_non_owner"]:
            flags.append(
                f"{tag} -- fallback reverts non-owner (strong honeypot signal)"
            )

    print()
    print("=" * 60)
    print("SANITY CHECK FLAGS")
    print("=" * 60)
    if flags:
        for f in flags:
            print(f)
        print(f"\nTotal flags: {len(flags)}")
    else:
        print("  No flags raised.")


if __name__ == "__main__":
    main()
