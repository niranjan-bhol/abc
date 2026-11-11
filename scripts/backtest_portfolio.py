import csv
from bisect import bisect_left
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO_DIR = ROOT / "data" / "portfolio"
PRICES_DIR = ROOT / "data" / "upstox" / "historical" / "csv"
OUT_DIR = ROOT / "data" / "backtest"

METRICS = ["number_of_shareholders", "shareholding_pct"]
SIGNAL_MONTHS = {1, 4, 7, 10}
BUY_OFFSET = 1  # buy in the month after the signal month
SELL_OFFSET = 3  # sell in the third month after the signal month
OUT_COLUMNS = ["symbol", "buy_price", "sell_price", "pnl_value", "pnl_percent"]

def add_months(year, month, offset):
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1

def load_prices():
    prices = {}
    for path in sorted(PRICES_DIR.glob("*.csv")):
        rows = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                try:
                    rows.append((row["date"], float(row["close"])))
                except (KeyError, TypeError, ValueError):
                    continue
        if rows:
            rows.sort()
            prices[path.stem] = ([d for d, _ in rows], [c for _, c in rows])
    return prices

def first_close_in_month(series, year, month):
    dates, closes = series
    prefix = f"{year:04d}-{month:02d}"
    i = bisect_left(dates, prefix)
    if i < len(dates) and dates[i].startswith(prefix):
        return dates[i], closes[i]
    return None

def last_close_in_month(series, year, month):
    dates, closes = series
    next_year, next_month = add_months(year, month, 1)
    i = bisect_left(dates, f"{next_year:04d}-{next_month:02d}") - 1
    if i >= 0 and dates[i].startswith(f"{year:04d}-{month:02d}"):
        return dates[i], closes[i]
    return None

def backtest_file(path, prices, year, month):
    buy_year, buy_month = add_months(year, month, BUY_OFFSET)
    sell_year, sell_month = add_months(year, month, SELL_OFFSET)

    out_rows = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            symbol = (row.get("symbol") or "").strip()
            series = prices.get(symbol)
            if not series:
                continue
            buy = first_close_in_month(series, buy_year, buy_month)
            sell = last_close_in_month(series, sell_year, sell_month)
            if not buy or not sell or sell[0] <= buy[0]:
                continue
            buy_price, sell_price = buy[1], sell[1]
            pnl_value = sell_price - buy_price
            pnl_percent = pnl_value / buy_price * 100 if buy_price else None
            out_rows.append(
                {
                    "symbol": symbol,
                    "buy_price": round(buy_price, 2),
                    "sell_price": round(sell_price, 2),
                    "pnl_value": round(pnl_value, 2),
                    "pnl_percent": "" if pnl_percent is None else round(pnl_percent, 2),
                }
            )
    return out_rows

def main():
    prices = load_prices()
    print(f"loaded prices for {len(prices)} symbols")

    written = skipped = 0
    for metric in METRICS:
        for folder in sorted(p for p in (PORTFOLIO_DIR / metric).iterdir() if p.is_dir()):
            for path in sorted(folder.glob("*.csv")):
                try:
                    year_str, month_str = path.stem.split("-")
                    year, month = int(year_str), int(month_str)
                except ValueError:
                    continue
                if month not in SIGNAL_MONTHS:
                    continue

                rows = backtest_file(path, prices, year, month)
                if not rows:
                    skipped += 1
                    continue

                out_path = OUT_DIR / metric / folder.name / path.name
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with out_path.open("w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
                    writer.writeheader()
                    writer.writerows(rows)
                written += 1

    print(f"wrote {written} files to {OUT_DIR.relative_to(ROOT)} (skipped {skipped} with no results)")

if __name__ == "__main__":
    main()
