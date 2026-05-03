"""
Data loading and pair registry.

Daily close prices live as CSVs in data/raw/<SYMBOL>.csv with columns (date, close).
Pairs are registered in PAIR_REGISTRY — add a pair here to make it available to
every downstream module (signals, backtest, the Streamlit app).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# ── Pair registry ────────────────────────────────────────────────────────────
# leg1 is the "dependent" side in the OLS hedge: spread = leg1 - β * leg2.
# label is what gets shown in the UI / reports.

@dataclass(frozen=True)
class Pair:
    id: str
    leg1: str
    leg2: str
    label: str
    rationale: str  # why we expect cointegration — shown in app / README


PAIR_REGISTRY: dict[str, Pair] = {
    "HDFC_ICICI": Pair(
        id="HDFC_ICICI",
        leg1="HDFCBANK",
        leg2="ICICIBANK",
        label="HDFC Bank / ICICI Bank",
        rationale=(
            "Two of the largest private-sector Indian banks. Similar deposit base, "
            "loan mix and regulatory exposure — the classic domestic-banking pair."
        ),
    ),
    "INFY_TCS": Pair(
        id="INFY_TCS",
        leg1="INFY",
        leg2="TCS",
        label="Infosys / TCS",
        rationale=(
            "Largest two Indian IT services companies. Both export-driven, similar "
            "client mix (BFSI, retail, healthcare), almost identical USD-INR exposure. "
            "Cointegration is the textbook expectation."
        ),
    ),
    "AXIS_KOTAK": Pair(
        id="AXIS_KOTAK",
        leg1="AXISBANK",
        leg2="KOTAKBANK",
        label="Axis Bank / Kotak Mahindra Bank",
        rationale=(
            "Two private-sector banks at different scale points. Same regulatory "
            "regime but Axis is corporate-tilted and Kotak is retail/private-banking "
            "tilted. Useful contrast to the HDFC/ICICI pair which is more homogeneous."
        ),
    ),
}


# ── Resolve data directory relative to this package ──────────────────────────
_PKG_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent  # src/pairs -> src -> repo root
DATA_DIR = _REPO_ROOT / "data" / "raw"


def load_symbol(symbol: str) -> pd.Series:
    """Load a single symbol's daily close series, indexed by date."""
    path = DATA_DIR / f"{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Price data not found for {symbol!r} at {path}. "
            f"Drop a CSV with columns (date, close) there."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").drop_duplicates(subset="date")
    s = df.set_index("date")["close"].astype(float)
    s.name = symbol
    return s


def load_pair(pair_id: str) -> tuple[pd.Series, pd.Series, Pair]:
    """Load both legs of a registered pair, date-aligned on their intersection."""
    if pair_id not in PAIR_REGISTRY:
        raise KeyError(
            f"Unknown pair {pair_id!r}. Registered pairs: {list(PAIR_REGISTRY)}"
        )
    p = PAIR_REGISTRY[pair_id]
    s1 = load_symbol(p.leg1)
    s2 = load_symbol(p.leg2)
    common = s1.index.intersection(s2.index)
    return s1.loc[common], s2.loc[common], p


def available_pairs() -> list[Pair]:
    """List every registered pair (for the Streamlit dropdown)."""
    return list(PAIR_REGISTRY.values())
