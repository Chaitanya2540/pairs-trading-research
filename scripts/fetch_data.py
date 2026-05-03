"""
Fetch daily close prices for every symbol referenced by PAIR_REGISTRY.

Run from the repo root:

    python scripts/fetch_data.py
    python scripts/fetch_data.py --start 2024-04-01 --end 2026-03-30

Yahoo Finance is the data source (free, reliable, gives NSE prices via the
".NS" suffix). The fetched closes match Zerodha Kite's daily closes within
rounding noise — I checked HDFCBANK in the original notebook against Yahoo
and the first 7 days are identical.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Make src/ importable so we can read PAIR_REGISTRY
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pairs.data import PAIR_REGISTRY, DATA_DIR  # noqa: E402


# Mapping from internal symbol → Yahoo ticker. Yahoo uses ".NS" for NSE-listed
# Indian stocks. Keep this list aligned with PAIR_REGISTRY.
YF_TICKER = {
    "HDFCBANK":  "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY":      "INFY.NS",
    "TCS":       "TCS.NS",
    "AXISBANK":  "AXISBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
}


def fetch_one(symbol: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    ticker = YF_TICKER.get(symbol)
    if ticker is None:
        raise KeyError(
            f"No Yahoo ticker mapped for {symbol!r}. "
            f"Add it to YF_TICKER in scripts/fetch_data.py."
        )
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"Yahoo returned no data for {ticker}")
    # yfinance can return a multi-level columns frame for single tickers
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df[["Close"]].rename(columns={"Close": "close"}).reset_index()
    out = out.rename(columns={"Date": "date"})
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2024-04-01")
    p.add_argument("--end",   default="2026-03-31")  # yfinance end is exclusive-ish
    args = p.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Collect every symbol referenced by any pair
    symbols = sorted({
        sym
        for pair in PAIR_REGISTRY.values()
        for sym in (pair.leg1, pair.leg2)
    })

    if not symbols:
        print("No pairs in PAIR_REGISTRY — nothing to fetch.")
        return 0

    print(f"Fetching {len(symbols)} symbols from Yahoo Finance "
          f"({args.start} → {args.end})")
    for sym in symbols:
        try:
            df = fetch_one(sym, args.start, args.end)
        except Exception as e:
            print(f"  [SKIP] {sym}: {e}")
            continue
        path = DATA_DIR / f"{sym}.csv"
        df.to_csv(path, index=False)
        print(f"  [OK]   {sym} -> {path.name}  ({len(df)} rows, "
              f"{df.iloc[0]['date']} → {df.iloc[-1]['date']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
