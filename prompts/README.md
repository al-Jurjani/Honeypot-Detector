# Prompt Version Log

| Version | F1 | Accuracy | Parse Rate | Selected | Notes |
|---------|-----|----------|------------|----------|-------|
| v1 | 0.909 | 90.0% | 100.0% | YES | Baseline: GPTScan scenario+property |
| v2 | 0.800 | 80.0% | 100.0% |  | v1 + strengthened uninitialised_struct Property |
| v3 | 0.000 | 40.0% | 100.0% |  | Chain-of-thought: per-type reasoning before JSON |
| v4 | 1.000 | 100.0% | 50.0% |  | Few-shot: worked examples (hit TPD rate limit in pilot) |