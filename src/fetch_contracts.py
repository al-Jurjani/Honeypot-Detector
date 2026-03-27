"""
fetch_contracts.py — Collect Solidity source code for all contracts in
data/labels/ground_truth.csv.

Strategy:
  1. Look for the .sol file in the local HoneyBadger dataset first.
  2. Fall back to the Etherscan v2 API if not found locally.
  3. Skip and log any contract that cannot be resolved.

Usage:
    python -m src.fetch_contracts
"""

import json
import shutil
import time
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from src.utils import (
    HONEYPOT_DIR,
    LEGIT_DIR,
    RESULTS_DIR,
    ROOT,
    get_logger,
    load_ground_truth,
    save_ground_truth,
)
from dotenv import load_dotenv
import os

load_dotenv()

log = get_logger("fetch_contracts")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"
RATE_LIMIT = 0.25  # seconds between Etherscan requests

# HoneyBadger local dataset (sibling repo)
HONEYBADGER_SRC = ROOT.parent / "HoneyBadger" / "datasets" / "source_code"

# Map our honeypot_type labels to HoneyBadger folder names
TYPE_TO_FOLDER = {
    "balance_disorder": "balance_disorder",
    "hidden_state": "hidden_state_update",
    "hidden_transfer": "hidden_transfer",
    "inheritance_disorder": "inheritance_disorder",
    "skip_empty_string_literal": "skip_empty_string_literal",
    "straw_man": "straw_man_contract",
    "type_deduction_overflow": "type_deduction_overflow",
    "uninitialised_struct": "uninitialised_struct",
}


def find_local_source(address: str, honeypot_type: str) -> Path | None:
    """Find a .sol file in the HoneyBadger dataset."""
    folder = TYPE_TO_FOLDER.get(honeypot_type, "")
    if folder:
        candidate = HONEYBADGER_SRC / folder / f"{address}.sol"
        if candidate.exists():
            return candidate
    # Brute-force search across all type folders
    for subdir in HONEYBADGER_SRC.iterdir():
        if subdir.is_dir():
            candidate = subdir / f"{address}.sol"
            if candidate.exists():
                return candidate
    return None


def fetch_etherscan_v2(address: str) -> str | None:
    """Call Etherscan v2 API. Return source code or None."""
    if not ETHERSCAN_API_KEY:
        return None
    params = {
        "chainid": "1",
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": ETHERSCAN_API_KEY,
    }
    try:
        resp = requests.get(
            ETHERSCAN_V2_URL, params=params, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.debug("Etherscan error for %s: %s", address, exc)
        return None

    if data.get("status") != "1" or not data.get("result"):
        return None
    result = data["result"]
    if isinstance(result, str):
        return None
    source = result[0].get("SourceCode", "")
    if not source:
        return None

    # Multi-file JSON wrapper → flatten
    if source.startswith("{") and "sources" in source.lower():
        try:
            raw = source[1:-1] if source.startswith("{{") else source
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                srcs = parsed.get("sources", parsed)
                parts = []
                for fname, obj in srcs.items():
                    c = obj.get("content", "") if isinstance(obj, dict) else str(obj)
                    parts.append(f"// ---- {fname} ----\n{c}")
                return "\n\n".join(parts)
        except (json.JSONDecodeError, AttributeError):
            pass
    return source


def main() -> None:
    df = load_ground_truth()
    df["filename"] = df["filename"].astype(object)
    log.info("Loaded %d contracts from ground_truth.csv", len(df))
    log.info(
        "HoneyBadger local source: %s (exists=%s)",
        HONEYBADGER_SRC, HONEYBADGER_SRC.exists(),
    )

    HONEYPOT_DIR.mkdir(parents=True, exist_ok=True)
    LEGIT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    skipped_path = RESULTS_DIR / "skipped_contracts.txt"
    skipped = []
    hp_count = 0
    legit_count = 0
    local_hits = 0
    api_hits = 0

    for idx, row in tqdm(
        df.iterrows(), total=len(df), desc="Collecting contracts"
    ):
        address = row["contract_id"]
        label = row["label"]
        hp_type = row.get("honeypot_type", "")
        if pd.isna(hp_type):
            hp_type = ""

        # Skip if already downloaded
        existing = row.get("filename")
        if pd.notna(existing) and existing:
            parent = HONEYPOT_DIR if label == "honeypot" else LEGIT_DIR
            if (parent / existing).exists():
                if label == "honeypot":
                    hp_count += 1
                else:
                    legit_count += 1
                continue

        # 1) Try local HoneyBadger dataset
        local_path = find_local_source(address, hp_type)
        if local_path:
            source = local_path.read_text(encoding="utf-8")
            local_hits += 1
        else:
            # 2) Fall back to Etherscan v2
            source = fetch_etherscan_v2(address)
            if source:
                api_hits += 1
            time.sleep(RATE_LIMIT)

        if not source:
            skipped.append(address)
            continue

        # Assign filename and save
        if label == "honeypot":
            hp_count += 1
            filename = f"hp_{hp_count:03d}.sol"
            out_path = HONEYPOT_DIR / filename
        else:
            legit_count += 1
            filename = f"legit_{legit_count:03d}.sol"
            out_path = LEGIT_DIR / filename

        out_path.write_text(source, encoding="utf-8")
        df.at[idx, "filename"] = filename

    # Update ground_truth.csv with filenames
    save_ground_truth(df)

    # Write skipped list
    if skipped:
        skipped_path.write_text(
            "\n".join(skipped) + "\n", encoding="utf-8"
        )

    log.info(
        "Done. %d honeypots, %d legitimate, %d skipped "
        "(local: %d, etherscan: %d)",
        hp_count, legit_count, len(skipped),
        local_hits, api_hits,
    )


if __name__ == "__main__":
    main()
