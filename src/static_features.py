"""
static_features.py — Extract 10 hand-crafted static features from Solidity
source files for honeypot detection (Pipeline 1).

Uses solidity-parser for AST analysis where possible, with regex fallbacks
for older Solidity syntax or unparseable files.

Usage:
    python -m src.static_features                        # batch: all contracts
    python -m src.static_features data/contracts/honeypots/hp_001.sol  # single
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from src.utils import (
    HONEYPOT_DIR,
    LEGIT_DIR,
    RESULTS_DIR,
    get_logger,
    load_ground_truth,
    read_contract,
    save_results,
)

log = get_logger("static_features")

# Patterns for withdrawal-like function names
_WITHDRAW_NAMES = re.compile(
    r"\b(withdraw|claim|cashout|getfunds|retrieve)\b", re.IGNORECASE
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_comments(source: str) -> str:
    """Remove single-line and multi-line comments from Solidity source."""
    source = re.sub(r"//[^\n]*", "", source)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return source


def _try_parse_ast(source: str) -> Optional[dict]:
    """Attempt to parse source into an AST. Returns None on failure."""
    try:
        from solidity_parser import parser
        return parser.parse(source, loc=False)
    except Exception:
        return None


def _get_contract_nodes(ast: dict) -> list[dict]:
    """Extract ContractDefinition nodes from the AST."""
    return [
        c for c in ast.get("children", [])
        if c.get("type") == "ContractDefinition"
    ]


def _get_functions(ast: dict) -> list[dict]:
    """Extract all FunctionDefinition nodes across all contracts."""
    funcs = []
    for contract in _get_contract_nodes(ast):
        for node in contract.get("subNodes", []):
            if node.get("type") == "FunctionDefinition":
                funcs.append(node)
    return funcs


def _ast_to_text(node) -> str:
    """Recursively stringify an AST node for text-matching inside it."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (list, tuple)):
        return " ".join(_ast_to_text(n) for n in node)
    if isinstance(node, dict):
        return " ".join(_ast_to_text(v) for v in node.values())
    return str(node)


# ── Individual feature extractors ─────────────────────────────────────────────

def _uses_tx_origin(source: str, ast: Optional[dict]) -> bool:
    return bool(re.search(r"\btx\.origin\b", source))


def _has_fallback(source: str, ast: Optional[dict]) -> bool:
    # Old-style: function () or function() — unnamed function
    # New-style: fallback() or receive()
    clean = _strip_comments(source)
    # receive() external payable
    if re.search(r"\breceive\s*\(\s*\)\s*(external|public)", clean):
        return True
    # fallback() external
    if re.search(r"\bfallback\s*\(\s*\)\s*(external|public)", clean):
        return True
    # Old-style unnamed fallback: "function" followed by "()" with no name
    # Match: function() or function () — but NOT function someName()
    if re.search(
        r"\bfunction\s*\(\s*\)\s*(public|external|payable|internal|\{)",
        clean,
    ):
        return True
    return False


def _fallback_reverts_non_owner(source: str, ast: Optional[dict]) -> bool:
    """Check if fallback body contains a require/revert/throw with
    an owner or sender comparison."""
    clean = _strip_comments(source)

    # Try to extract fallback body
    fallback_body = None

    # New-style fallback/receive
    m = re.search(
        r"\b(?:fallback|receive)\s*\(\s*\)\s*(?:external|public)?"
        r"\s*(?:payable)?\s*\{",
        clean,
    )
    if not m:
        # Old-style: function() with no name
        m = re.search(
            r"\bfunction\s*\(\s*\)\s*(?:public|external)?\s*(?:payable)?\s*\{",
            clean,
        )
    if m:
        # Extract brace-delimited body
        start = m.end() - 1  # position of '{'
        depth = 0
        end = start
        for i in range(start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        fallback_body = clean[start:end]

    if not fallback_body:
        return False

    has_guard = bool(
        re.search(r"\b(require|revert|throw)\b", fallback_body)
    )
    has_owner_check = bool(
        re.search(
            r"(msg\.sender\s*[!=]=\s*\w*owner|"
            r"\w*owner\s*[!=]=\s*msg\.sender|"
            r"msg\.sender\s*[!=]=\s*creator|"
            r"onlyOwner)",
            fallback_body,
            re.IGNORECASE,
        )
    )
    return has_guard and has_owner_check


def _require_count(source: str, ast: Optional[dict]) -> int:
    clean = _strip_comments(source)
    return len(re.findall(r"\brequire\s*\(", clean))


def _has_selfdestruct(source: str, ast: Optional[dict]) -> bool:
    clean = _strip_comments(source)
    return bool(re.search(r"\b(selfdestruct|suicide)\s*\(", clean))


def _has_withdrawal_function(source: str, ast: Optional[dict]) -> bool:
    clean = _strip_comments(source)
    return bool(
        re.search(
            r"\bfunction\s+(withdraw|claim|cashout|getfunds|retrieve)\b",
            clean,
            re.IGNORECASE,
        )
    )


def _withdrawal_owner_only(source: str, ast: Optional[dict]) -> bool:
    """Check if any withdrawal function has an owner-only guard."""
    clean = _strip_comments(source)

    # Find each withdrawal function body
    pattern = re.compile(
        r"\bfunction\s+(withdraw|claim|cashout|getfunds|retrieve)"
        r"\b[^{]*\{",
        re.IGNORECASE,
    )
    for m in pattern.finditer(clean):
        # Check for onlyOwner modifier on the function signature
        sig = clean[m.start(): m.end()]
        if re.search(r"\bonlyOwner\b", sig):
            return True

        # Extract function body
        start = m.end() - 1
        depth = 0
        end = start
        for i in range(start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = clean[start:end]

        if re.search(
            r"require\s*\(\s*msg\.sender\s*==\s*\w*owner",
            body,
            re.IGNORECASE,
        ):
            return True
        if re.search(
            r"require\s*\(\s*\w*owner\s*==\s*msg\.sender",
            body,
            re.IGNORECASE,
        ):
            return True
    return False


def _uses_inline_assembly(source: str, ast: Optional[dict]) -> bool:
    clean = _strip_comments(source)
    return bool(re.search(r"\bassembly\s*\{", clean))


def _extract_function_bodies(source: str) -> list[str]:
    """Return a list of function-body strings from raw source."""
    clean = _strip_comments(source)
    bodies = []
    for m in re.finditer(r"\bfunction\b[^{]*\{", clean):
        start = m.end() - 1
        depth = 0
        end = start
        for i in range(start, len(clean)):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        bodies.append(clean[start:end])
    return bodies


def _state_changes_before_external_calls(
    source: str, ast: Optional[dict]
) -> int:
    """Count state variable assignments that appear before external calls
    (.transfer, .send, .call) within the same function body."""
    # Heuristic: a state change is an assignment to a non-local variable
    # (no "memory" / "storage" keyword, and the LHS doesn't start with
    # common local patterns like uint/bool/address declarations).
    assignment_re = re.compile(
        r"(?<!\w)"                        # not preceded by word char
        r"[a-zA-Z_]\w*"                   # identifier (potential state var)
        r"(?:\[[^\]]*\])?"                # optional mapping/array index
        r"\s*(?:\+|-|\*|/)?="             # assignment operator
        r"(?!=)",                          # not == comparison
    )
    external_call_re = re.compile(
        r"\.(transfer|send|call)\s*[\({]"
    )

    total = 0
    for body in _extract_function_bodies(source):
        # Find position of first external call
        ext_match = external_call_re.search(body)
        if not ext_match:
            continue
        # Count assignments before that position
        before = body[: ext_match.start()]
        assignments = assignment_re.findall(before)
        total += len(assignments)
    return total


def _payable_to_withdraw_ratio(
    source: str, ast: Optional[dict]
) -> float:
    clean = _strip_comments(source)

    # Count payable functions
    payable_count = len(
        re.findall(r"\bfunction\b[^{]*\bpayable\b[^{]*\{", clean)
    )
    # Also count old-style unnamed fallback with payable
    if re.search(
        r"\bfunction\s*\(\s*\)\s*(?:public\s+)?payable\s*\{", clean
    ):
        payable_count = max(payable_count, 1)

    # Count withdraw-like functions
    withdraw_count = len(
        re.findall(
            r"\bfunction\s+(withdraw|claim|cashout|getfunds|retrieve)\b",
            clean,
            re.IGNORECASE,
        )
    )
    return payable_count / max(withdraw_count, 1)


# ── Main extraction ──────────────────────────────────────────────────────────

def extract_features(filepath: str | Path) -> Optional[dict]:
    """
    Extract all 10 static features from a .sol file.

    Returns a dict with the feature values, or None if the file
    cannot be read.
    """
    source = read_contract(filepath)
    if source is None:
        log.warning("Cannot read %s", filepath)
        return None

    ast = _try_parse_ast(source)
    if ast is None:
        log.debug("AST parse failed for %s, using regex only", filepath)

    return {
        "uses_tx_origin": _uses_tx_origin(source, ast),
        "has_fallback": _has_fallback(source, ast),
        "fallback_reverts_non_owner": _fallback_reverts_non_owner(
            source, ast
        ),
        "require_count": _require_count(source, ast),
        "has_selfdestruct": _has_selfdestruct(source, ast),
        "has_withdrawal_function": _has_withdrawal_function(source, ast),
        "withdrawal_owner_only": _withdrawal_owner_only(source, ast),
        "uses_inline_assembly": _uses_inline_assembly(source, ast),
        "state_changes_before_external_calls": (
            _state_changes_before_external_calls(source, ast)
        ),
        "payable_to_withdraw_ratio": _payable_to_withdraw_ratio(
            source, ast
        ),
    }


# ── Batch processing ─────────────────────────────────────────────────────────

def extract_all(contracts_dir: Path) -> list[dict]:
    """
    Extract features from all .sol files in a directory.

    Returns a list of dicts, each with 'contract_id' + 10 features.
    """
    results = []
    sol_files = sorted(contracts_dir.glob("*.sol"))
    for fpath in tqdm(sol_files, desc=f"Extracting [{contracts_dir.name}]"):
        feats = extract_features(fpath)
        if feats is None:
            continue
        feats["contract_id"] = fpath.stem
        results.append(feats)
    return results


def run_batch() -> pd.DataFrame:
    """
    Run static feature extraction on all honeypot + legitimate contracts.
    Merges with ground_truth labels and saves to static_features.csv.
    """
    gt = load_ground_truth()

    rows = []
    for _, entry in tqdm(
        gt.iterrows(), total=len(gt), desc="Static features"
    ):
        label = entry["label"]
        filename = entry["filename"]
        contract_id = entry["contract_id"]
        folder = HONEYPOT_DIR if label == "honeypot" else LEGIT_DIR
        fpath = folder / filename

        feats = extract_features(fpath)
        if feats is None:
            continue
        feats["contract_id"] = contract_id
        feats["filename"] = filename
        feats["label"] = label
        rows.append(feats)

    df = pd.DataFrame(rows)
    out = save_results(df, "static_features.csv")
    log.info("Saved %d rows to %s", len(df), out)
    return df


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single file mode
        path = Path(sys.argv[1])
        feats = extract_features(path)
        if feats is None:
            print(f"ERROR: could not extract features from {path}")
            sys.exit(1)
        print(json.dumps(feats, indent=2))
    else:
        # Batch mode
        df = run_batch()
        print(f"\n{len(df)} contracts processed.")
        print(df.head(10).to_string())
