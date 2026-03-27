"""
verify_env.py — Smoke-test that all required packages import correctly.
Run with: python verify_env.py
"""

import sys

failures = []

checks = [
    ("anthropic", "Anthropic SDK"),
    ("sklearn", "scikit-learn"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    ("web3", "web3"),
    ("tqdm", "tqdm"),
    ("dotenv", "python-dotenv"),
    ("statsmodels", "statsmodels"),
    ("solcx", "py-solc-x"),
]

for module, label in checks:
    try:
        __import__(module)
        print(f"  [OK] {label}")
    except ImportError as e:
        failures.append((label, str(e)))
        print(f"  [FAIL] {label}: {e}")

# slither has a different import path
try:
    import slither  # noqa: F401
    print("  [OK] Slither")
except ImportError:
    try:
        from slither.slither import Slither  # noqa: F401
        print("  [OK] Slither (slither.slither)")
    except ImportError as e:
        failures.append(("Slither", str(e)))
        print(f"  [FAIL] Slither: {e}")

print()
if failures:
    print(f"Environment INCOMPLETE — {len(failures)} package(s) missing:")
    for label, err in failures:
        print(f"  - {label}: {err}")
    sys.exit(1)
else:
    print("Environment OK")
