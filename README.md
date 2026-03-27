# Detecting Honeypot Smart Contracts on Ethereum

**LLM-Based Semantic Analysis vs. Traditional Static Feature Extraction**

Course: Information Security and Ethics | Team Size: 3 | Duration: ~7 Weeks

---

## Overview

This project compares three approaches to detecting honeypot smart contracts on Ethereum:

1. **Pipeline 1 — Static Feature Extraction**: AST-based hand-crafted features fed into a Random Forest classifier.
2. **Pipeline 2 — LLM Semantic Analysis**: Claude (Anthropic API) reads the source code and returns structured JSON risk assessments.
3. **Pipeline 3 — Hybrid Ensemble**: Combined static + LLM features in a single Random Forest.

---

## Repository Structure

```
honeypot-detector/
├── data/
│   ├── contracts/
│   │   ├── honeypots/        # Honeypot .sol files (hp_001.sol, ...)
│   │   └── legitimate/       # Legitimate .sol files (legit_001.sol, ...)
│   └── labels/
│       └── ground_truth.csv  # Master label file
├── src/
│   ├── static_analysis.py    # Pipeline 1: AST feature extraction
│   ├── llm_analysis.py       # Pipeline 2: Anthropic API analysis
│   ├── ensemble.py           # Pipeline 3: Ensemble + evaluation + figures
│   └── utils.py              # Shared utilities (paths, logging, I/O)
├── outputs/
│   ├── figures/              # Generated paper figures (PNG, 300 dpi)
│   └── results/              # CSV outputs and raw LLM responses
├── paper/                    # LaTeX / paper drafts
├── prompts/                  # Prompt versions (v1.txt, v2.txt, ...)
├── .env.example              # API key template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Create and activate virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Solidity compiler

```bash
solc-select install 0.8.0
solc-select use 0.8.0
```

### 4. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and ETHERSCAN_API_KEY
```

### 5. Verify environment

```bash
python verify_env.py
# Should print: Environment OK
```

---

## Running the Pipelines

```bash
# Step 1: Download contract source code (requires Etherscan API key)
# python src/fetch_contracts.py   # (to be implemented)

# Step 2: Extract static features
python src/static_analysis.py

# Step 3: Run LLM analysis (requires Anthropic API key, ~$5-15 for 400 contracts)
python src/llm_analysis.py

# Step 4: Train ensemble + generate all results and figures
python src/ensemble.py
```

---

## Dataset

- **HoneyBadger dataset** (Torres et al.): labeled honeypot and legitimate contract addresses
- Source code fetched from Etherscan verified contracts API
- Target: 200+ honeypots + 200+ legitimate contracts

Honeypot types covered: balance disorder, hidden state variable, hidden transfer, straw man contract, inheritance disorder, skip empty string literal, type deduction overflow, uninitialised struct.

---

## ground_truth.csv Schema

| Column | Type | Description |
|---|---|---|
| `contract_id` | str | Unique identifier (e.g. `hp_001`) |
| `filename` | str | Filename (e.g. `hp_001.sol`) |
| `label` | str | `honeypot` or `legitimate` |
| `honeypot_type` | str | HoneyBadger category (honeypots only) |
| `source` | str | Data source (e.g. `honeybadger`, `etherscan`) |

---

## Tools & Budget

| Tool | Cost | Purpose |
|---|---|---|
| Python 3.12 | Free | All scripting and ML |
| solidity-parser-antlr | Free | AST parsing for static features |
| Slither | Free | Optional additional static analysis |
| scikit-learn | Free | Random Forest, metrics |
| Anthropic API (Claude) | ~$5–15 | LLM pipeline |
| Matplotlib / Seaborn | Free | Visualization |

---

## Paper

Target: 7–8 pages (IEEE/ACM format), 5-fold stratified cross-validation, McNemar's test for statistical significance.

**Research Question**: Can LLM-based semantic analysis detect honeypot smart contracts more effectively than traditional static feature extraction?
