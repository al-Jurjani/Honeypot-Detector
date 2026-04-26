"""
run_step13.py — Resumable LLM batch analysis on all 523 contracts.

Skips contracts that already have a raw response file, so re-running after
a quota cutoff picks up exactly where it left off.

Usage:
    python scripts/run_step13.py            # full run / resume
    python scripts/run_step13.py --retry    # retry parse failures only
    python scripts/run_step13.py --assemble # rebuild llm_features.csv from
                                            # existing raw files, no API calls
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.llm_analyzer import analyze_contract, EXPECTED_KEYS
from src.utils import LABELS_PATH, HONEYPOT_DIR, LEGIT_DIR, RESULTS_DIR, get_logger
from groq import Groq

log = get_logger("step13")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "v1.txt"
RAW_DIR = RESULTS_DIR / "llm_raw_responses"
OUT_CSV = RESULTS_DIR / "llm_features.csv"


def _raw_path(contract_id: str) -> Path:
    return RAW_DIR / f"{contract_id}.json"


def _load_raw(contract_id: str) -> dict | None:
    p = _raw_path(contract_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _assemble(gt: pd.DataFrame) -> pd.DataFrame:
    """Build llm_features.csv from all existing raw response files."""
    from src.llm_analyzer import _parse_json

    records = []
    for _, row in gt.iterrows():
        cid = row["contract_id"]
        raw_data = _load_raw(cid)
        if raw_data is None:
            continue

        rec = {
            "contract_id": cid,
            "filename": row["filename"],
            "true_label": row["label"],
            "true_honeypot_type": row.get("honeypot_type", ""),
            "parse_success": raw_data.get("parse_success", False),
            "raw_response": raw_data.get("raw_response", ""),
        }
        for k in EXPECTED_KEYS:
            rec[k] = None

        if rec["parse_success"]:
            parsed = _parse_json(rec["raw_response"])
            if parsed:
                for k in EXPECTED_KEYS:
                    rec[k] = parsed.get(k)

        records.append(rec)

    return pd.DataFrame(records)


def run(retry_failures: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    gt = pd.read_csv(LABELS_PATH)
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    client = Groq()

    # Determine which contracts still need processing
    if retry_failures:
        # Only contracts with existing raw file where parse_success=False
        pending = []
        for _, row in gt.iterrows():
            raw = _load_raw(row["contract_id"])
            if raw is not None and not raw.get("parse_success", False):
                pending.append(row)
        log.info("Retrying %d parse failures", len(pending))
    else:
        # Skip contracts that already have a raw response file
        pending = []
        skipped = 0
        for _, row in gt.iterrows():
            if _raw_path(row["contract_id"]).exists():
                skipped += 1
            else:
                pending.append(row)
        log.info(
            "Skipping %d already-processed contracts. %d remaining.",
            skipped,
            len(pending),
        )

    if not pending:
        log.info("Nothing to process.")
    else:
        quota_hit = False
        for row in tqdm(pending, desc="LLM analysis"):
            cid = row["contract_id"]
            subdir = "honeypots" if row["label"] == "honeypot" else "legitimate"
            sol_path = (HONEYPOT_DIR if row["label"] == "honeypot" else LEGIT_DIR) / row["filename"]

            res = analyze_contract(cid, sol_path, prompt_template, client=client)

            # Detect quota exhaustion — stop early and preserve progress
            raw_resp = res.get("raw_response", "") or ""
            if "rate_limit_exceeded" in raw_resp.lower() or "413" in raw_resp:
                log.warning("Quota/rate-limit hit at contract %s — stopping.", cid)
                quota_hit = True
                break

            raw_file = _raw_path(cid)
            raw_file.write_text(
                json.dumps({
                    "contract_id": cid,
                    "raw_response": res["raw_response"],
                    "parse_success": res["parse_success"],
                }, indent=2),
                encoding="utf-8",
            )

        done = len(list(RAW_DIR.glob("*.json")))
        total = len(gt)
        log.info("Raw files on disk: %d / %d", done, total)
        if quota_hit:
            log.warning(
                "Quota exhausted. Re-run tomorrow — script will resume from where it stopped."
            )

    # Always rebuild the CSV from whatever raw files exist
    df = _assemble(gt)
    if len(df) > 0:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_CSV, index=False)

        parsed = df["parse_success"].sum()
        total = len(df)
        log.info(
            "llm_features.csv: %d contracts, %d parsed (%.1f%%), %d failed",
            total,
            parsed,
            100 * parsed / total,
            total - parsed,
        )
    else:
        log.info("No raw responses found yet — CSV not written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry", action="store_true", help="Retry parse failures only")
    parser.add_argument("--assemble", action="store_true", help="Rebuild CSV only, no API calls")
    args = parser.parse_args()

    if args.assemble:
        gt = pd.read_csv(LABELS_PATH)
        df = _assemble(gt)
        df.to_csv(OUT_CSV, index=False)
        parsed = df["parse_success"].sum()
        print(f"Assembled {len(df)} rows, {parsed} parsed ({100*parsed/len(df):.1f}%)")
    else:
        run(retry_failures=args.retry)
