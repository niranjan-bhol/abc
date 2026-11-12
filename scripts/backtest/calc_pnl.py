import csv
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TOP_N = 30

IN_DIR = BASE_DIR / "data" / "backtest" / f"top{TOP_N}"
PRICE_DIR = BASE_DIR / "data" / "upstox" / "historical" / "csv"
OUT_DIR = BASE_DIR / "data" / "backtest" / "pnl"
OUT_DIR_DISPLAY = f"{BASE_DIR.name}/{OUT_DIR.relative_to(BASE_DIR)}"

REBALANCE_MONTHS = {1, 4, 7, 10}
BUY_OFFSET = 1   # buy at first close of the month after the file's month
SELL_OFFSET = 3  # sell at last close of the 3rd month after the file's month
HEADER = ["symbol", "buy_price", "sell_price", "pnl_value", "pnl_percent"]
DECIMALS = 4

_price_cache = {}


def add_months(year, month, offset):
    index = year * 12 + (month - 1) + offset
    return index // 12, index % 12 + 1


def month_closes(symbol):
    """Return {(year, month): (first_close, last_close)} for a symbol."""
    if symbol in _price_cache:
        return _price_cache[symbol]
    result = {}
    path = PRICE_DIR / f"{symbol}.csv"
    if path.exists():
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = []
            for row in csv.DictReader(f):
                try:
                    rows.append((row["date"], float(row["close"])))
                except (KeyError, TypeError, ValueError):
                    continue
        rows.sort(key=lambda item: item[0])
        for date, close in rows:
            key = (int(date[:4]), int(date[5:7]))
            if key in result:
                result[key][1] = close
            else:
                result[key] = [close, close]
    _price_cache[symbol] = result
    return result


def compute_trade(symbol, buy_key, sell_key):
    closes = month_closes(symbol)
    if buy_key not in closes or sell_key not in closes:
        return None
    buy = closes[buy_key][0]
    sell = closes[sell_key][1]
    if buy <= 0:
        return None
    pnl = sell - buy
    return [
        symbol,
        round(buy, DECIMALS),
        round(sell, DECIMALS),
        round(pnl, DECIMALS),
        round(pnl / buy * 100, DECIMALS),
    ]


def process_file(path, out_path):
    year, month = int(path.stem[:4]), int(path.stem[5:7])
    buy_key = add_months(year, month, BUY_OFFSET)
    sell_key = add_months(year, month, SELL_OFFSET)

    with path.open(newline="", encoding="utf-8-sig") as f:
        symbols = [row["symbol"] for row in csv.DictReader(f)]

    trades = [t for t in (compute_trade(s, buy_key, sell_key) for s in symbols) if t]
    skipped = len(symbols) - len(trades)
    # sell month not covered by price data at all, nothing to export
    if symbols and not trades:
        return None, skipped

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(trades)
    return len(trades), skipped


def main():
    if not IN_DIR.exists():
        print(f"ERROR : input directory not found : {IN_DIR}")
        return
    categories = sorted(p for p in IN_DIR.iterdir() if p.is_dir())
    if not categories:
        print(f"ERROR : no category folders in {IN_DIR}")
        return

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
        print(f"Cleared output directory : {OUT_DIR_DISPLAY}")
    OUT_DIR.mkdir(parents=True)

    written = skipped_files = 0
    for category in categories:
        out_dir = OUT_DIR / category.name
        out_dir.mkdir()
        for path in sorted(category.glob("*.csv")):
            try:
                if int(path.stem[5:7]) not in REBALANCE_MONTHS:
                    continue
                count, _ = process_file(path, out_dir / path.name)
            except (OSError, KeyError, ValueError, csv.Error) as exc:
                print(f"ERROR : {category.name}/{path.name} : {type(exc).__name__} : {exc}")
                continue
            if count is None:
                skipped_files += 1
            else:
                written += 1
        print(f"{category.name}")

    print(f"\nWritten {written} files, skipped {skipped_files} (no price data for sell month)")
    print(f"Saved to : {OUT_DIR_DISPLAY}")


if __name__ == "__main__":
    main()
