"""
llm_analyzer.py — Pipeline 2: LLM-based honeypot detection using Groq API.

Sends Solidity source code to llama-3.3-70b-versatile with a structured prompt
and parses the JSON response into feature fields for downstream classification.

Key functions:
  analyze_contract(contract_id, sol_path, prompt_template) -> dict
  batch_analyze(ground_truth_csv, contracts_dir, prompt_path, output_dir,
                sample_ids=None) -> DataFrame
"""

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from tqdm import tqdm

load_dotenv()

# Paths relative to this file's location
_SRC = Path(__file__).resolve().parent
ROOT = _SRC.parent
CONTRACTS_DIR = ROOT / "data" / "contracts"
LABELS_PATH = ROOT / "data" / "labels" / "ground_truth.csv"
RESULTS_DIR = ROOT / "outputs" / "results"
RAW_RESPONSES_DIR = RESULTS_DIR / "llm_raw_responses"

MODEL = "llama-3.3-70b-versatile"
MAX_CHARS = 12000
RATE_LIMIT_SLEEP = 2.5

EXPECTED_KEYS = {
    "deception_risk_score",
    "is_honeypot",
    "honeypot_type",
    "withdrawal_possible_for_non_owner",
    "hidden_conditions",
    "suspicious_patterns",
    "explanation",
}


# ── JSON parsing ───────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict | None:
    """Try direct JSON parse, then strip markdown fences as fallback."""
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find any JSON object in the response
    match2 = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if match2:
        try:
            return json.loads(match2.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ── Single contract analysis ───────────────────────────────────────────────────

def analyze_contract(
    contract_id: str,
    sol_path: str | Path,
    prompt_template: str,
    client: Groq | None = None,
) -> dict:
    """
    Analyze one contract with the LLM and return parsed feature dict.

    Parameters
    ----------
    contract_id : str
        Ethereum address or unique ID for this contract.
    sol_path : path-like
        Path to the .sol source file.
    prompt_template : str
        Prompt string containing a {source_code} placeholder.
    client : Groq, optional
        Reuse an existing Groq client; creates a new one if None.

    Returns
    -------
    dict
        Keys: contract_id, parse_success, raw_response, plus all EXPECTED_KEYS.
        On parse failure, JSON fields are None except parse_success=False.
    """
    if client is None:
        client = Groq()

    result: dict = {
        "contract_id": contract_id,
        "parse_success": False,
        "raw_response": None,
    }
    for k in EXPECTED_KEYS:
        result[k] = None

    try:
        source = Path(sol_path).read_text(encoding="utf-8")
    except Exception as e:
        result["raw_response"] = f"FILE_READ_ERROR: {e}"
        return result

    if len(source) > MAX_CHARS:
        source = source[:MAX_CHARS] + "\n\n// [TRUNCATED — contract exceeded context limit]"

    prompt = prompt_template.replace("{source_code}", source)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        result["raw_response"] = f"API_ERROR: {e}"
        time.sleep(RATE_LIMIT_SLEEP)
        return result

    result["raw_response"] = raw
    parsed = _parse_json(raw)

    if parsed is not None:
        result["parse_success"] = True
        for k in EXPECTED_KEYS:
            result[k] = parsed.get(k)

    time.sleep(RATE_LIMIT_SLEEP)
    return result


# ── Batch processing ───────────────────────────────────────────────────────────

def batch_analyze(
    ground_truth_csv: str | Path,
    contracts_dir: str | Path,
    prompt_path: str | Path,
    output_dir: str | Path,
    sample_ids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Run LLM analysis on all contracts (or a subset) and persist results.

    Parameters
    ----------
    ground_truth_csv : path-like
        CSV with columns: contract_id, filename, label, honeypot_type, source.
    contracts_dir : path-like
        Root directory containing honeypots/ and legitimate/ subdirs.
    prompt_path : path-like
        Path to the prompt template .txt file.
    output_dir : path-like
        Directory where llm_raw_responses/ will be written.
    sample_ids : list of str, optional
        If provided, only process these contract_ids.

    Returns
    -------
    pd.DataFrame
        One row per contract with all feature fields.
        Also saves raw JSON responses under output_dir/llm_raw_responses/.
    """
    gt = pd.read_csv(ground_truth_csv)
    if sample_ids is not None:
        gt = gt[gt["contract_id"].isin(sample_ids)].copy()

    prompt_template = Path(prompt_path).read_text(encoding="utf-8")
    raw_dir = Path(output_dir) / "llm_raw_responses"
    raw_dir.mkdir(parents=True, exist_ok=True)

    client = Groq()
    records = []

    for _, row in tqdm(gt.iterrows(), total=len(gt), desc="LLM analysis"):
        cid = row["contract_id"]
        label = row["label"]
        subdir = "honeypots" if label == "honeypot" else "legitimate"
        sol_path = Path(contracts_dir) / subdir / row["filename"]

        res = analyze_contract(cid, sol_path, prompt_template, client=client)
        res["true_label"] = label
        res["true_honeypot_type"] = row.get("honeypot_type", "")
        res["filename"] = row["filename"]
        records.append(res)

        # Persist raw response per contract
        raw_file = raw_dir / f"{cid}.json"
        raw_file.write_text(
            json.dumps({"contract_id": cid, "raw_response": res["raw_response"],
                        "parse_success": res["parse_success"]}, indent=2),
            encoding="utf-8",
        )

    return pd.DataFrame(records)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = batch_analyze(
        ground_truth_csv=LABELS_PATH,
        contracts_dir=CONTRACTS_DIR,
        prompt_path=ROOT / "prompts" / "v1.txt",
        output_dir=RESULTS_DIR,
    )
    out = RESULTS_DIR / "llm_features.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")
