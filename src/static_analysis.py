"""
static_analysis.py — Pipeline 1: Static feature extraction from Solidity source code.

Uses a Solidity AST parser to extract hand-crafted features that are indicative of
honeypot behavior. Each feature is documented with the honeypot pattern it targets.

Features extracted (10 core features):
  1.  uses_tx_origin                   — references tx.origin (phishing / access control trick)
  2.  has_fallback                      — contract has a fallback or receive function
  3.  fallback_reverts_non_owner        — fallback reverts for addresses other than the owner
  4.  num_require_statements            — total count of require() calls
  5.  has_selfdestruct                  — contract uses selfdestruct
  6.  withdrawal_exists                 — at least one function that sends Ether out
  7.  withdrawal_owner_only             — withdrawal gated by an owner/access check
  8.  uses_inline_assembly              — contract contains inline assembly blocks
  9.  state_changes_before_ext_calls    — count of state writes before external calls
  10. payable_to_withdraw_ratio         — payable functions / withdraw-like functions
"""

from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from utils import (
    HONEYPOT_DIR,
    LEGIT_DIR,
    get_logger,
    load_ground_truth,
    read_contract,
    save_results,
)

logger = get_logger(__name__)


# ── Feature extraction ─────────────────────────────────────────────────────────

def extract_features(sol_source: str) -> Optional[dict]:
    """
    Extract all static features from a Solidity source string.

    Parameters
    ----------
    sol_source : str
        Raw Solidity source code.

    Returns
    -------
    dict or None
        Dictionary mapping feature names to values, or None if parsing fails.
    """
    raise NotImplementedError("Implement AST-based feature extraction")


def _uses_tx_origin(source: str) -> bool:
    """Return True if the source code references tx.origin."""
    raise NotImplementedError


def _has_fallback(source: str) -> bool:
    """Return True if a fallback() or receive() function is defined."""
    raise NotImplementedError


def _fallback_reverts_non_owner(source: str) -> bool:
    """
    Return True if the fallback reverts (revert/require) for callers
    other than the owner — a common honeypot access-control trap.
    """
    raise NotImplementedError


def _num_require_statements(source: str) -> int:
    """Count the total number of require() calls in the source."""
    raise NotImplementedError


def _has_selfdestruct(source: str) -> bool:
    """Return True if selfdestruct or suicide is used."""
    raise NotImplementedError


def _withdrawal_exists(source: str) -> bool:
    """
    Return True if at least one function sends Ether out via
    transfer(), send(), or a low-level call with value.
    """
    raise NotImplementedError


def _withdrawal_owner_only(source: str) -> bool:
    """
    Return True if the withdrawal function is gated by an ownership check
    (e.g., require(msg.sender == owner)).
    """
    raise NotImplementedError


def _uses_inline_assembly(source: str) -> bool:
    """Return True if the contract contains inline assembly blocks."""
    raise NotImplementedError


def _state_changes_before_ext_calls(source: str) -> int:
    """
    Count how many state-variable writes occur before external calls
    in each function. High counts suggest reentrancy guards or hidden state.
    """
    raise NotImplementedError


def _payable_to_withdraw_ratio(source: str) -> float:
    """
    Return the ratio of payable functions to withdraw-like functions.
    A ratio >> 1 (many ways in, few ways out) is a honeypot signal.
    Returns 0.0 if there are no withdraw functions.
    """
    raise NotImplementedError


# ── Batch processing ───────────────────────────────────────────────────────────

def run_batch(ground_truth_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Run static feature extraction on all contracts in the dataset.

    Parameters
    ----------
    ground_truth_df : pd.DataFrame, optional
        If provided, only process contracts listed in this DataFrame.
        Otherwise loads from ground_truth.csv.

    Returns
    -------
    pd.DataFrame
        One row per contract: all features + contract_id + label.
        Saved automatically to outputs/results/static_features.csv.
    """
    raise NotImplementedError("Implement batch extraction loop")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = run_batch()
    print(df.head())
