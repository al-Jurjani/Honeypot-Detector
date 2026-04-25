"""
run_llm_pipeline.py — Steps 9, 10, 11 of the LLM analysis pipeline.

Tests all 4 prompt versions on a 10-contract pilot (Step 9), selects the
champion by F1 score, then runs it on 20 contracts for the final evaluation
report (Step 11).
"""

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402
from groq import Groq  # noqa: E402

from llm_analyzer import analyze_contract  # noqa: E402

load_dotenv()

CONTRACTS_DIR = ROOT / "data" / "contracts"
LABELS_PATH = ROOT / "data" / "labels" / "ground_truth.csv"
PROMPTS_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "outputs" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
PROMPT_VERSIONS = ["v1", "v2", "v3", "v4"]

NOTES = {
    "v1": "Baseline: GPTScan scenario+property pairs for all 8 types",
    "v2": "v1 + strengthened uninitialised_struct Property description",
    "v3": "Chain-of-thought: per-type reasoning before JSON output",
    "v4": "Few-shot: one honeypot + one legitimate worked example inline",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_gt():
    return pd.read_csv(LABELS_PATH)


def sample_contracts(gt, n_honeypot, n_legit, seed):
    hp = gt[gt["label"] == "honeypot"].sample(
        n=n_honeypot, random_state=seed
    )
    leg = gt[gt["label"] == "legitimate"].sample(
        n=n_legit, random_state=seed
    )
    return pd.concat([hp, leg]).reset_index(drop=True)


def run_on_sample(sample, prompt_template, client):
    results = []
    for _, row in sample.iterrows():
        cid = row["contract_id"]
        subdir = (
            "honeypots" if row["label"] == "honeypot" else "legitimate"
        )
        sol_path = CONTRACTS_DIR / subdir / row["filename"]
        res = analyze_contract(
            cid, sol_path, prompt_template, client=client
        )
        res["true_label"] = row["label"]
        res["true_honeypot_type"] = row.get("honeypot_type", "")
        res["filename"] = row["filename"]
        results.append(res)
    return results


def compute_metrics(results):
    total = len(results)
    parsed = [r for r in results if r["parse_success"]]
    parse_rate = len(parsed) / total if total else 0

    if not parsed:
        return {
            "accuracy": 0, "precision": 0, "recall": 0, "f1": 0,
            "parse_rate": 0, "n_parsed": 0, "n_total": total,
        }

    y_true = [
        1 if r["true_label"] == "honeypot" else 0 for r in parsed
    ]
    y_pred = [1 if bool(r["is_honeypot"]) else 0 for r in parsed]

    return {
        "accuracy":   accuracy_score(y_true, y_pred),
        "precision":  precision_score(y_true, y_pred, zero_division=0),
        "recall":     recall_score(y_true, y_pred, zero_division=0),
        "f1":         f1_score(y_true, y_pred, zero_division=0),
        "parse_rate": parse_rate,
        "n_parsed":   len(parsed),
        "n_total":    total,
    }


def print_metrics(version, m):
    print(
        f"  {version}: parse={m['parse_rate']:.0%} "
        f"acc={m['accuracy']:.0%} "
        f"prec={m['precision']:.0%} "
        f"rec={m['recall']:.0%} "
        f"F1={m['f1']:.3f} "
        f"({m['n_parsed']}/{m['n_total']} parsed)"
    )


def detail_rows(results):
    rows = []
    for r in results:
        correct = (
            bool(r["is_honeypot"]) == (r["true_label"] == "honeypot")
            if r["parse_success"] else None
        )
        rows.append({
            "contract_id":             r["contract_id"],
            "true_label":              r["true_label"],
            "true_honeypot_type":      r["true_honeypot_type"],
            "is_honeypot_predicted":   r["is_honeypot"],
            "deception_risk_score":    r["deception_risk_score"],
            "honeypot_type_predicted": r["honeypot_type"],
            "parse_success":           r["parse_success"],
            "correct":                 correct,
            "explanation":             r["explanation"],
        })
    return rows


# ── Step 9: pilot all 4 versions ──────────────────────────────────────────────

def step9_pilot():
    print("\n=== STEP 9: PROMPT COMPARISON (10-contract pilot) ===")
    gt = load_gt()
    pilot = sample_contracts(gt, n_honeypot=5, n_legit=5, seed=SEED)
    print(f"Pilot: {pilot['label'].value_counts().to_dict()}")

    client = Groq()
    iteration_log = []
    scores = {}

    for version in PROMPT_VERSIONS:
        prompt_path = PROMPTS_DIR / f"{version}.txt"
        if not prompt_path.exists():
            print(f"  SKIP {version} — file not found")
            continue

        prompt_template = prompt_path.read_text(encoding="utf-8")
        print(f"\nRunning {version}...")
        results = run_on_sample(pilot, prompt_template, client)
        m = compute_metrics(results)
        print_metrics(version, m)

        for r in results:
            is_hp = bool(r["is_honeypot"])
            true_hp = r["true_label"] == "honeypot"
            if r["parse_success"] and is_hp != true_hp:
                pred = "honeypot" if is_hp else "legitimate"
                print(
                    f"    WRONG {r['contract_id'][:16]} "
                    f"true={r['true_label']} pred={pred} "
                    f"score={r['deception_risk_score']} "
                    f"type={r['true_honeypot_type']}"
                )
            elif not r["parse_success"]:
                snippet = (
                    (r["raw_response"] or "")[:80].replace("\n", " ")
                )
                print(
                    f"    PARSE_FAIL {r['contract_id'][:16]}: {snippet}"
                )

        iteration_log.append({
            "version": version,
            "metrics": m,
            "results": detail_rows(results),
        })
        scores[version] = m

    log_path = RESULTS_DIR / "prompt_iterations.json"
    log_path.write_text(
        json.dumps(iteration_log, indent=2), encoding="utf-8"
    )
    print(f"\nIteration log saved to {log_path}")

    eligible = {
        v: s for v, s in scores.items() if s["parse_rate"] >= 0.80
    }
    pool = eligible if eligible else scores
    champion = max(pool, key=lambda v: pool[v]["f1"])

    print("\nPilot results summary:")
    print(f"  {'version':<6}  {'F1':>6}  {'acc':>6}  {'parse':>6}")
    for v in PROMPT_VERSIONS:
        if v in scores:
            s = scores[v]
            marker = " <-- CHAMPION" if v == champion else ""
            print(
                f"  {v:<6}  {s['f1']:>6.3f}  "
                f"{s['accuracy']:>6.0%}  "
                f"{s['parse_rate']:>6.0%}{marker}"
            )

    return champion, iteration_log, scores


# ── Step 11: run champion on 20 contracts ─────────────────────────────────────

def step11_test20(champion, scores):
    print(f"\n=== STEP 11: 20-CONTRACT TEST (champion={champion}) ===")
    gt = load_gt()
    sample20 = sample_contracts(gt, n_honeypot=10, n_legit=10, seed=SEED)
    print(f"Sample: {sample20['label'].value_counts().to_dict()}")

    prompt_template = (
        PROMPTS_DIR / f"{champion}.txt"
    ).read_text(encoding="utf-8")
    client = Groq()
    results = run_on_sample(sample20, prompt_template, client)

    raw_dir = RESULTS_DIR / "llm_raw_responses"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        p = raw_dir / f"{r['contract_id']}.json"
        p.write_text(
            json.dumps({
                "contract_id":  r["contract_id"],
                "raw_response": r["raw_response"],
                "parse_success": r["parse_success"],
            }, indent=2),
            encoding="utf-8",
        )

    rows = []
    for r in results:
        rows.append({
            "contract_id":                       r["contract_id"],
            "filename":                          r["filename"],
            "true_label":                        r["true_label"],
            "true_honeypot_type":                r["true_honeypot_type"],
            "is_honeypot":                       r["is_honeypot"],
            "honeypot_type_predicted":           r["honeypot_type"],
            "deception_risk_score":              r["deception_risk_score"],
            "withdrawal_possible_for_non_owner": (
                r["withdrawal_possible_for_non_owner"]
            ),
            "parse_success":                     r["parse_success"],
            "explanation":                       r["explanation"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / "llm_test_20.csv", index=False)

    m = compute_metrics(results)
    parsed = [r for r in results if r["parse_success"]]
    y_true = [
        1 if r["true_label"] == "honeypot" else 0 for r in parsed
    ]
    y_pred = [1 if bool(r["is_honeypot"]) else 0 for r in parsed]
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    type_stats: dict = {}
    for r in parsed:
        if r["true_label"] == "honeypot":
            t = r["true_honeypot_type"]
            if not isinstance(t, str) or t != t:
                t = "unknown"
        else:
            t = "legitimate"
        type_stats.setdefault(t, {"total": 0, "correct": 0})
        type_stats[t]["total"] += 1
        if bool(r["is_honeypot"]) == (r["true_label"] == "honeypot"):
            type_stats[t]["correct"] += 1

    disagreements = [
        r for r in parsed
        if bool(r["is_honeypot"]) != (r["true_label"] == "honeypot")
    ]

    report_lines = [
        "# Step 11 Evaluation Report",
        "",
        f"**Prompt version used:** {champion}",
        "**Sample:** 10 honeypots + 10 legitimate contracts (seed=42)",
        "",
        "## Parse Success",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total contracts | {m['n_total']} |",
        f"| Successfully parsed | {m['n_parsed']} |",
        f"| Parse success rate | {m['parse_rate']:.1%} |",
        "",
        "## Classification Metrics (on parsed contracts)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Accuracy  | {m['accuracy']:.3f} |",
        f"| Precision | {m['precision']:.3f} |",
        f"| Recall    | {m['recall']:.3f} |",
        f"| F1 Score  | {m['f1']:.3f} |",
        "",
        "## Confusion Matrix",
        "",
        "| | Predicted Honeypot | Predicted Legitimate |",
        "|---|---|---|",
        f"| **True Honeypot** | TP={tp} | FN={fn} |",
        f"| **True Legitimate** | FP={fp} | TN={tn} |",
        "",
        "## Per Honeypot-Type Breakdown",
        "",
        "| Type | Total | Correct | Accuracy |",
        "|------|-------|---------|----------|",
    ]
    for t, v in sorted(type_stats.items()):
        pct = v["correct"] / v["total"] if v["total"] else 0
        report_lines.append(
            f"| {t} | {v['total']} | {v['correct']} | {pct:.0%} |"
        )

    report_lines += [
        "",
        "## Prompt Comparison (pilot results)",
        "",
        "| Version | F1 | Accuracy | Parse Rate | Notes |",
        "|---------|-----|----------|------------|-------|",
    ]
    for v in PROMPT_VERSIONS:
        if v in scores:
            s = scores[v]
            marker = " **CHAMPION**" if v == champion else ""
            report_lines.append(
                f"| {v} | {s['f1']:.3f} | {s['accuracy']:.1%} | "
                f"{s['parse_rate']:.1%} | "
                f"{NOTES.get(v, '')}{marker} |"
            )

    report_lines += ["", "## Disagreements (LLM vs Ground Truth)", ""]
    if disagreements:
        report_lines += [
            "| contract_id | true_label | predicted | score"
            " | explanation |",
            "|---|---|---|---|---|",
        ]
        for r in disagreements:
            pred = "honeypot" if r["is_honeypot"] else "legitimate"
            expl = (r["explanation"] or "").replace("|", "/")[:120]
            report_lines.append(
                f"| {r['contract_id'][:20]} | {r['true_label']}"
                f" | {pred} | {r['deception_risk_score']} | {expl} |"
            )
    else:
        report_lines.append(
            "No disagreements — all parsed contracts correct."
        )

    (RESULTS_DIR / "step11_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    print("\n--- STEP 11 SUMMARY ---")
    print(
        f"Parse:  {m['n_parsed']}/{m['n_total']} ({m['parse_rate']:.1%})"
    )
    print(
        f"Acc={m['accuracy']:.3f}  Prec={m['precision']:.3f}  "
        f"Rec={m['recall']:.3f}  F1={m['f1']:.3f}"
    )
    print(f"TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    if disagreements:
        print(f"Disagreements ({len(disagreements)}):")
        for r in disagreements:
            pred = "honeypot" if r["is_honeypot"] else "legitimate"
            print(
                f"  {r['filename']} true={r['true_label']} "
                f"pred={pred} type={r['true_honeypot_type']} "
                f"score={r['deception_risk_score']}"
            )

    return df, m


# ── README ─────────────────────────────────────────────────────────────────────

def write_prompts_readme(champion, scores):
    lines = [
        "# Prompt Version Log",
        "",
        "| Version | F1 | Accuracy | Parse Rate | Selected | Notes |",
        "|---------|-----|----------|------------|----------|-------|",
    ]
    for v in PROMPT_VERSIONS:
        if v in scores:
            s = scores[v]
            selected = "YES" if v == champion else ""
            lines.append(
                f"| {v} | {s['f1']:.3f} | {s['accuracy']:.1%} | "
                f"{s['parse_rate']:.1%} | {selected} | "
                f"{NOTES.get(v, '')} |"
            )
        else:
            lines.append(
                f"| {v} | TBD | TBD | TBD | | {NOTES.get(v, '')} |"
            )

    (PROMPTS_DIR / "README.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"README saved to {PROMPTS_DIR / 'README.md'}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    champion, iteration_log, scores = step9_pilot()
    write_prompts_readme(champion, scores)
    df, final_metrics = step11_test20(champion, scores)

    print("\n=== DELIVERABLES CHECK ===")
    check_files = [
        PROMPTS_DIR / "v1.txt",
        PROMPTS_DIR / "v2.txt",
        PROMPTS_DIR / "v3.txt",
        PROMPTS_DIR / "v4.txt",
        PROMPTS_DIR / "README.md",
        ROOT / "src" / "llm_analyzer.py",
        RESULTS_DIR / "prompt_iterations.json",
        RESULTS_DIR / "llm_test_20.csv",
        RESULTS_DIR / "step11_report.md",
    ]
    for f in check_files:
        status = "OK" if f.exists() else "MISSING"
        print(f"  [{status}] {f.relative_to(ROOT)}")
    raw_count = len(
        list((RESULTS_DIR / "llm_raw_responses").glob("*.json"))
    )
    print(
        f"  [OK] outputs/results/llm_raw_responses/ ({raw_count} files)"
    )
    print(
        f"\nChampion: {champion}  |  F1={final_metrics['f1']:.3f}  "
        f"Acc={final_metrics['accuracy']:.3f}  "
        f"Parse={final_metrics['parse_rate']:.1%}"
    )
