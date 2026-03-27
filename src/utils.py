"""
utils.py — Shared utility functions for the honeypot detection project.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTRACTS_DIR = DATA_DIR / "contracts"
HONEYPOT_DIR = CONTRACTS_DIR / "honeypots"
LEGIT_DIR = CONTRACTS_DIR / "legitimate"
LABELS_PATH = DATA_DIR / "labels" / "ground_truth.csv"
OUTPUTS_DIR = ROOT / "outputs"
RESULTS_DIR = OUTPUTS_DIR / "results"
FIGURES_DIR = OUTPUTS_DIR / "figures"
PROMPTS_DIR = ROOT / "prompts"


# ── Logging ────────────────────────────────────────────────────────────────────

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a consistently configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ── Ground truth ───────────────────────────────────────────────────────────────

def load_ground_truth() -> pd.DataFrame:
    """
    Load ground_truth.csv and return as a DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: contract_id, filename, label, honeypot_type, source
    """
    return pd.read_csv(LABELS_PATH)


def save_ground_truth(df: pd.DataFrame) -> None:
    """Overwrite ground_truth.csv with an updated DataFrame."""
    df.to_csv(LABELS_PATH, index=False)


# ── Contract I/O ───────────────────────────────────────────────────────────────

def read_contract(filepath: Path | str) -> Optional[str]:
    """
    Read a Solidity source file and return its contents.

    Parameters
    ----------
    filepath : Path or str
        Absolute or relative path to the .sol file.

    Returns
    -------
    str or None
        Source code string, or None if the file cannot be read.
    """
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except Exception:
        return None


# ── JSON helpers ───────────────────────────────────────────────────────────────

def parse_json_response(raw: str) -> Optional[dict]:
    """
    Try to parse a JSON object from a raw LLM response string.

    Handles both bare JSON and responses wrapped in ```json ... ``` blocks.

    Parameters
    ----------
    raw : str
        Raw text returned by the LLM.

    Returns
    -------
    dict or None
        Parsed dictionary, or None if parsing fails.
    """
    import re
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


# ── Results I/O ────────────────────────────────────────────────────────────────

def save_results(df: pd.DataFrame, filename: str) -> Path:
    """
    Save a results DataFrame as CSV under outputs/results/.

    Parameters
    ----------
    df : pd.DataFrame
    filename : str
        e.g. "static_features.csv"

    Returns
    -------
    Path
        Full path where the file was saved.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / filename
    df.to_csv(out, index=False)
    return out
