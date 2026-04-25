# Step 11 Evaluation Report

**Prompt version used:** v1 (champion)
**Sample:** 10 honeypots + 10 legitimate contracts (seed=42)
**Note:** 4 parse failures were HTTP 413 errors (contracts exceeded the Groq context window). Truncation fix added post-run will resolve these in the full batch.

## Parse Success

| Metric | Value |
|--------|-------|
| Total contracts | 20 |
| Successfully parsed | 16 |
| Parse success rate | 80.0% |

## Classification Metrics (on parsed contracts)

| Metric | Value |
|--------|-------|
| Accuracy  | 0.812 |
| Precision | 0.818 |
| Recall    | 0.900 |
| F1 Score  | 0.857 |

## Confusion Matrix

| | Predicted Honeypot | Predicted Legitimate |
|---|---|---|
| **True Honeypot** | TP=9 | FN=1 |
| **True Legitimate** | FP=2 | TN=4 |

## Per Honeypot-Type Breakdown

| Type | Total | Correct | Accuracy |
|------|-------|---------|----------|
| balance_disorder | 1 | 1 | 100% |
| hidden_state | 4 | 4 | 100% |
| inheritance_disorder | 1 | 1 | 100% |
| legitimate | 6 | 4 | 67% |
| straw_man | 1 | 1 | 100% |
| uninitialised_struct | 3 | 2 | 67% |

## Prompt Comparison (10-contract pilot, seed=42)

| Version | F1 | Accuracy | Parse Rate | Notes |
|---------|-----|----------|------------|-------|
| v1 | 0.909 | 90.0% | 100.0% | Baseline: GPTScan scenario+property **CHAMPION** |
| v2 | 0.800 | 80.0% | 100.0% | v1 + strengthened uninitialised_struct Property |
| v3 | 0.000 | 40.0% | 100.0% | Chain-of-thought: per-type reasoning before JSON |
| v4 | 1.000 | 100.0% | 50.0% | Few-shot: worked examples (hit TPD rate limit in pilot) |

### Pilot observations

- **v1** (F1=0.909): 1 false positive — legitimate contract with complex owner-gated logic flagged as hidden_state.
- **v2** (F1=0.800): strengthening TYPE 8 Property introduced a new false negative on a hidden_state contract (over-sensitised to struct patterns, less attentive elsewhere).
- **v3** (F1=0.000): chain-of-thought format completely broke JSON output — the model spent all tokens on reasoning text and produced malformed or missing JSON for every honeypot.
- **v4** (F1=1.000 on 5/10 parsed): few-shot examples gave perfect results on the contracts that completed, but the larger prompt caused 5/10 calls to hit the tokens-per-minute rate limit, making the score unreliable.

**v1 selected** as champion: highest reliable F1 at full parse rate.

## Disagreements (LLM vs Ground Truth)

| filename | true_label | predicted | score | explanation |
|---|---|---|---|---|
| hp_252.sol | honeypot | legitimate | 2 | The contract appears to be a legitimate game of chance, where players can guess a secret number and win the contract bal |
| legit_223.sol | legitimate | honeypot | 8 | The contract has a high deception risk score due to hidden state variables and complex conditions restricting transfers. |
| legit_221.sol | legitimate | honeypot | 8 | The contract appears to be a honeypot due to hidden state variables and functions only accessible by the owner. The only |