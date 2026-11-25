import re
import csv
import math
import shutil
from calendar import month_abbr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "launch" / "portfolio"
PRICE_DIR = BASE_DIR / "data" / "upstox" / "historical" / "csv"
OUTPUT_DIR = BASE_DIR / "data" / "launch" / "pnl"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

DECIMALS = 2
HEADER = ["symbol", "buy_price", "sell_price", "pnl_value", "pnl_percent"]

FILE_PATTERN = re.compile(r"^(\d{4})_(0[1-9]|1[0-2])_to_(\d{4})_(0[1-9]|1[0-2])\.csv$")
DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-\d{2}")

price_cache = {}

def period_label(path):
    match = FILE_PATTERN.match(path.name)
    if not match:
        raise ValueError()
    start_year, start_month, end_year, end_month = match.groups()
    return (
        f"{month_abbr[int(start_month)].upper()} {start_year} to "
        f"{month_abbr[int(end_month)].upper()} {end_year}"
    )

def read_closes(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            match = DATE_PATTERN.match(row.get("date") or "")
            try:
                close = float(row.get("close"))
            except (TypeError, ValueError):
                continue
            if match and math.isfinite(close) and close > 0:
                rows.append((row["date"], close, (int(match[1]), int(match[2]))))
    rows.sort(key=lambda item: item[0])
    return rows

def month_closes(symbol):
    if symbol not in price_cache:
        result = {}
        path = PRICE_DIR / f"{symbol}.csv"
        if path.parent == PRICE_DIR and path.is_file():
            for _, close, key in read_closes(path):
                if key in result:
                    result[key][1] = close
                else:
                    result[key] = [close, close]
        price_cache[symbol] = result
    return price_cache[symbol]

def compute_trade(symbol, buy_key, sell_key):
    closes = month_closes(symbol)
    if buy_key not in closes or sell_key not in closes:
        return None
    buy = closes[buy_key][0]
    sell = closes[sell_key][1]
    pnl = sell - buy
    return [
        symbol,
        f"{buy:.{DECIMALS}f}",
        f"{sell:.{DECIMALS}f}",
        f"{pnl:.{DECIMALS}f}",
        f"{pnl / buy * 100:.{DECIMALS}f}",
    ]

def read_symbols(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "symbol" not in (reader.fieldnames or []):
            raise ValueError()
        symbols = [(row["symbol"] or "").strip() for row in reader]
    return list(dict.fromkeys(s for s in symbols if s))

def process_file(path, output_path):
    match = FILE_PATTERN.match(path.name)
    buy_key = (int(match[1]), int(match[2]))
    sell_key = (int(match[3]), int(match[4]))

    symbols = read_symbols(path)
    trades = [t for t in (compute_trade(s, buy_key, sell_key) for s in symbols) if t]
    if symbols and not trades:
        return False

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(trades)
    return True

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"\nOutput directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUTPUT_PATH_DISPLAY}")

def calculate_pnl():
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError()

    files = sorted(
        path
        for path in INPUT_DIR.glob("*.csv")
        if FILE_PATTERN.match(path.name)
    )
    if not files:
        raise ValueError()

    prepare_output_dir()

    written_files = skipped_files = 0
    total = len(files)
    print(f"\nCalculating portfolio PnL across {total} holding periods ...\n")

    for path in files:
        try:
            if process_file(path, OUTPUT_DIR / path.name):
                written_files += 1
                print(f"{period_label(path)}  ->  SUCCESS")
            else:
                skipped_files += 1
                print(f"{period_label(path)}  ->  SKIPPED")
        except Exception as e:
            print(f"{period_label(path)}  ->  ERROR : {type(e).__name__}")

    print(f"\nWRITTEN : {written_files} files")
    print(f"SKIPPED : {skipped_files} files (no price data for sell month)")
    print(f"\nPnL calculation completed for {written_files}/{total} holding periods")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        calculate_pnl()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
