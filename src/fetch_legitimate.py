"""
fetch_legitimate.py — Download ~200 additional verified legitimate contracts
from Etherscan to balance the honeypot/legitimate class ratio.

Strategy:
  1. Collect candidate addresses from ERC-20 token transfers of major wallets.
  2. Supplement with a seed list of well-known DeFi/infrastructure contracts.
  3. Download verified source code via Etherscan v2 API.
  4. Save as data/contracts/legitimate/legit_NNN.sol (continuing numbering).

Usage:
    python -m src.fetch_legitimate
"""

import json
import os
import time

import pandas as pd
import requests
from tqdm import tqdm
from dotenv import load_dotenv

from src.utils import (
    LEGIT_DIR,
    RESULTS_DIR,
    get_logger,
    load_ground_truth,
    save_ground_truth,
)

load_dotenv()
log = get_logger("fetch_legitimate")

API_KEY = os.getenv("ETHERSCAN_API_KEY")
BASE_URL = "https://api.etherscan.io/v2/api"
RATE_LIMIT = 0.25
TARGET = 200

# Major wallets whose token transfers yield diverse legitimate contracts
WHALE_WALLETS = [
    "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe",  # Ethereum Foundation
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance 14
    "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",  # Binance 7
    "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503",  # Binance
    "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549",  # Binance 15
    "0xF977814e90dA44bFA03b6295A0616a897441aceC",  # Binance 8
]

# Well-known DeFi / infrastructure / token contracts (definitely legitimate)
SEED_CONTRACTS = [
    # -- DEX routers & factories --
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # Uniswap V2 Router
    "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # Uniswap V2 Factory
    "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # Uniswap V3 SwapRouter
    "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # Uniswap V3 Factory
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",  # Uniswap V3 Router02
    "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD",  # Uniswap Universal Router
    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",  # SushiSwap Router
    "0xDef1C0ded9bec7F1a1670819833240f027b25EfF",  # 0x Exchange Proxy
    "0x1111111254EEB25477B68fb85Ed929f73A960582",  # 1inch V5 Router
    # -- Lending --
    "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",  # Aave V2 LendingPool
    "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",  # Aave V3 Pool
    "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",  # Compound Comptroller
    "0xc3d688B66703497DAA19211EEdff47f25384cdc3",  # Compound V3 cUSDCv3
    # -- Curve --
    "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # Curve 3pool
    "0xD51a44d3FaE010294C616388b506AcdA1bfAAE46",  # Curve Tricrypto2
    # -- Stablecoins --
    "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    "0x4Fabb145d64652a948d72533023f6E7A623C7C53",  # BUSD
    "0x853d955aCEf822Db058eb8505911ED77F175b99e",  # FRAX
    "0x8E870D67F660D95d5be530380D0eC0bd388289E1",  # USDP
    # -- Wrapped assets --
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
    # -- Governance / utility tokens --
    "0x514910771AF9Ca656af840dff83E8264EcF986CA",  # LINK
    "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",  # UNI
    "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",  # AAVE
    "0xc00e94Cb662C3520282E6f5717214004A7f26888",  # COMP
    "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",  # MKR
    "0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",  # SNX
    "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",  # YFI
    "0xD533a949740bb3306d119CC777fa900bA034cd52",  # CRV
    "0xba100000625a3754423978a60c9317c58a424e3D",  # BAL
    "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2",  # SUSHI
    "0x111111111117dC0aa78b770fA6A738034120C302",  # 1INCH
    "0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B",  # CVX
    "0x0D8775F648430679A709E98d2b0Cb6250d2887EF",  # BAT
    "0xE41d2489571d322189246DaFA5ebDe1F4699F498",  # ZRX
    "0x0F5D2fB29fb7d3CFeE444a200298f468908cC942",  # MANA
    "0x3845badAde8e6dFF049820680d1F14bD3903a5d0",  # SAND
    "0x4d224452801ACEd8B2F0aebE155379bb5D594381",  # APE
    "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",  # MATIC
    "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # stETH
    "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",  # SHIB
    "0xae78736Cd615f374D3085123A210448E74Fc6393",  # rETH
    "0xBe9895146f7AF43049ca1c1AE358B0541Ea49704",  # cbETH
    "0x15D4c048F83bd7e37d49eA4C83a07267Ec4203dA",  # GALA
    "0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b",  # AXS
    "0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b",  # CRO
    "0x2b591e99afE9f32eAA6214f7B7629768c40Eeb39",  # HEX
    "0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1",  # TON
    "0x75231F58b43240C9718Dd58B4967c5114342a86c",  # OKB
    "0x50D1c9771902476076eCFc8B2A83Ad6b9355a4c9",  # FTT
    "0x3506424F91fD33084466F402d5D97f05F8e3b4AF",  # CHZ
    "0x6982508145454Ce325dDbE47a25d4ec3d2311933",  # PEPE
    "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",  # LDO
    "0xfAbA6f8e4a5E8Ab82F62fe7C39859FA577269BE3",  # ONDO
    "0x163f8C2467924be0ae7B5347228CABF260318753",  # WLD
    "0xb131f4A55907B10d1F0A50d8ab8FA09EC342cd74",  # MEME
    "0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72",  # ENS
    "0xFe2e637202056d30016725477c5da089Ab0A043A",  # sETH2
]


def etherscan_call(params: dict) -> dict | None:
    """Rate-limited Etherscan v2 API call."""
    params["chainid"] = "1"
    params["apikey"] = API_KEY
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.debug("API error: %s", exc)
        return None


def collect_token_addresses(wallet: str) -> set[str]:
    """Extract unique token contract addresses from a wallet's
    recent ERC-20 transfers."""
    data = etherscan_call({
        "module": "account",
        "action": "tokentx",
        "address": wallet,
        "page": "1",
        "offset": "1000",
        "sort": "desc",
    })
    time.sleep(RATE_LIMIT)
    if not data or data.get("status") != "1":
        return set()
    results = data.get("result", [])
    if isinstance(results, str):
        return set()
    return {
        tx["contractAddress"].lower()
        for tx in results
        if tx.get("contractAddress")
    }


def fetch_source(address: str) -> str | None:
    """Download verified source code via Etherscan v2."""
    data = etherscan_call({
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
    })
    time.sleep(RATE_LIMIT)
    if not data or data.get("status") != "1":
        return None
    result = data.get("result")
    if isinstance(result, str) or not result:
        return None
    source = result[0].get("SourceCode", "")
    if not source:
        return None

    # Flatten multi-file JSON wrapper
    if source.startswith("{"):
        try:
            raw = source[1:-1] if source.startswith("{{") else source
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and any(
                k in parsed for k in ("sources", "Sources")
            ):
                srcs = parsed.get("sources", parsed.get("Sources", parsed))
                parts = []
                for fname, obj in srcs.items():
                    c = (
                        obj.get("content", "")
                        if isinstance(obj, dict)
                        else str(obj)
                    )
                    parts.append(f"// ---- {fname} ----\n{c}")
                return "\n\n".join(parts)
        except (json.JSONDecodeError, AttributeError):
            pass

    return source


def main() -> None:
    if not API_KEY:
        log.error("ETHERSCAN_API_KEY not set in .env")
        return

    df = load_ground_truth()
    df["filename"] = df["filename"].astype(object)
    existing = set(df["contract_id"].str.lower())
    legit_count = int(
        df.loc[df["label"] == "legitimate", "filename"]
        .dropna()
        .str.extract(r"(\d+)", expand=False)
        .astype(int)
        .max()
    ) if len(df[df["label"] == "legitimate"]) > 0 else 0
    log.info(
        "Existing dataset: %d honeypots, %d legitimate (last legit_%03d)",
        len(df[df["label"] == "honeypot"]),
        len(df[df["label"] == "legitimate"]),
        legit_count,
    )

    # ── Phase 1: collect candidate addresses ──────────────────────
    candidates: set[str] = set()
    log.info("Collecting token contract addresses from whale wallets...")
    for wallet in WHALE_WALLETS:
        addrs = collect_token_addresses(wallet)
        candidates |= addrs
        log.info("  %s... → %d tokens", wallet[:12], len(addrs))

    for addr in SEED_CONTRACTS:
        candidates.add(addr.lower())

    candidates -= existing
    candidates_list = sorted(candidates)
    log.info(
        "Candidates: %d (excluded %d already in dataset)",
        len(candidates_list),
        len(candidates & existing),
    )

    # ── Phase 2: download verified source code ────────────────────
    LEGIT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    new_rows = []

    for addr in tqdm(candidates_list, desc="Downloading contracts"):
        if downloaded >= TARGET:
            break
        source = fetch_source(addr)
        if not source:
            skipped += 1
            continue

        legit_count += 1
        downloaded += 1
        filename = f"legit_{legit_count:03d}.sol"
        (LEGIT_DIR / filename).write_text(source, encoding="utf-8")
        new_rows.append({
            "contract_id": addr,
            "filename": filename,
            "label": "legitimate",
            "honeypot_type": "",
            "source": "etherscan",
        })

        if downloaded % 25 == 0:
            log.info("  ... %d / %d downloaded", downloaded, TARGET)

    # ── Phase 3: update ground_truth.csv ──────────────────────────
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        save_ground_truth(df)

    log.info(
        "Done. Downloaded %d new legitimate contracts (%d skipped).",
        downloaded, skipped,
    )
    log.info(
        "Dataset totals: %d honeypots, %d legitimate",
        len(df[df["label"] == "honeypot"]),
        len(df[df["label"] == "legitimate"]),
    )


if __name__ == "__main__":
    main()
