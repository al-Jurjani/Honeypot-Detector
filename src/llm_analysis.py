"""
llm_analysis.py — Pipeline 2: LLM-based semantic analysis using the Anthropic API.

Sends each contract's source code to Claude with a structured prompt that asks for
JSON output. The LLM acts as a semantic feature extractor, returning:

  - deception_risk_score          (int 0–10)
  - is_honeypot                   (bool)
  - withdrawal_possible_for_non_owner  (bool)
  - hidden_conditions             (list[str])  — trapping mechanisms found
  - suspicious_patterns           (list[str])  — suspicious code patterns
  - explanation                   (str)        — 2-3 sentence reasoning

All raw responses are saved to outputs/results/llm_raw_responses/ for reproducibility.
The parsed features are saved to outputs/results/llm_features.csv.

Uses temperature=0 for reproducibility. Includes rate limiting and robust JSON parsing.
"""

import time
from pathlib import Path
from typing import Optional

import anthropic
import pandas as pd
from tqdm import tqdm

from utils import (
    PROMPTS_DIR,
    RESULTS_DIR,
    get_logger,
    load_ground_truth,
    parse_json_response,
    read_contract,
    save_results,
)

logger = get_logger(__name__)

# Directory for storing raw LLM responses (one JSON file per contract)
RAW_RESPONSES_DIR = RESULTS_DIR / "llm_raw_responses"

# Anthropic model to use — claude-sonnet-4-6 is the default
DEFAULT_MODEL = "claude-sonnet-4-6"

# Expected keys in the JSON response
EXPECTED_KEYS = {
    "deception_risk_score",
    "is_honeypot",
    "withdrawal_possible_for_non_owner",
    "hidden_conditions",
    "suspicious_patterns",
    "explanation",
}


# ── Prompt loading ─────────────────────────────────────────────────────────────

def load_prompt(version: str = "v1") -> str:
    """
    Load a prompt template from prompts/<version>.txt.

    The template must contain a {source_code} placeholder that will be
    replaced with the contract source before sending to the API.

    Parameters
    ----------
    version : str
        Prompt version filename without extension (e.g. "v1", "v2").

    Returns
    -------
    str
        Prompt template string.
    """
    raise NotImplementedError("Load prompt template from prompts/ directory")


# ── Single contract analysis ───────────────────────────────────────────────────

def analyze_contract(
    sol_source: str,
    client: anthropic.Anthropic,
    prompt_template: str,
    model: str = DEFAULT_MODEL,
    rate_limit_sleep: float = 0.5,
) -> Optional[dict]:
    """
    Send a single contract to Claude and return parsed LLM features.

    Parameters
    ----------
    sol_source : str
        Raw Solidity source code.
    client : anthropic.Anthropic
        Authenticated Anthropic client.
    prompt_template : str
        Prompt string with a {source_code} placeholder.
    model : str
        Anthropic model ID.
    rate_limit_sleep : float
        Seconds to sleep after each API call to respect rate limits.

    Returns
    -------
    dict or None
        Parsed JSON feature dictionary, or None if the API call or JSON
        parsing fails.

    Notes
    -----
    - temperature=0 is used for reproducibility.
    - If JSON parsing fails on the first attempt, the raw response is
      logged and returned as None.
    """
    raise NotImplementedError("Implement single-contract LLM analysis")


# ── Batch processing ───────────────────────────────────────────────────────────

def run_batch(
    ground_truth_df: Optional[pd.DataFrame] = None,
    prompt_version: str = "v1",
    model: str = DEFAULT_MODEL,
    rate_limit_sleep: float = 0.5,
) -> pd.DataFrame:
    """
    Run LLM analysis on all contracts in the dataset.

    Parameters
    ----------
    ground_truth_df : pd.DataFrame, optional
        If provided, only process contracts listed here.
        Otherwise loads from ground_truth.csv.
    prompt_version : str
        Which prompt template to use (filename under prompts/).
    model : str
        Anthropic model ID.
    rate_limit_sleep : float
        Seconds to sleep between API calls.

    Returns
    -------
    pd.DataFrame
        One row per contract with columns:
        contract_id, deception_risk_score, is_honeypot,
        num_hidden_conditions, num_suspicious_patterns,
        withdrawal_possible, label.
        Saved automatically to outputs/results/llm_features.csv.

    Notes
    -----
    - Raw responses are saved to outputs/results/llm_raw_responses/<contract_id>.json
      so runs are reproducible and failed parses can be inspected manually.
    - Failed API calls and JSON parse errors are logged; the contract is
      skipped and can be retried later.
    """
    raise NotImplementedError("Implement batch LLM analysis loop")


# ── Evaluation helpers ─────────────────────────────────────────────────────────

def classify_by_threshold(
    llm_df: pd.DataFrame, threshold: int = 5
) -> pd.Series:
    """
    Method A: threshold-based classification.
    Returns a boolean Series: True if deception_risk_score >= threshold.
    """
    raise NotImplementedError


def classify_by_flag(llm_df: pd.DataFrame) -> pd.Series:
    """
    Method B: direct flag classification.
    Returns the is_honeypot boolean column as a Series.
    """
    raise NotImplementedError


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = run_batch()
    print(df.head())
