import re
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "launch" / "pnl"
OUTPUT_PATH = BASE_DIR / "data" / "launch" / "summary" / "simulation.csv"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_PATH.relative_to(BASE_DIR)}"

INITIAL_CAPITAL = Decimal("100000")
DECIMALS = 2
CAPITAL_QUANTUM = Decimal("0.01")
HEADER = ["start", "end", "capital_start", "capital_end", "pnl_value", "pnl_percent"]

FILE_PATTERN = re.compile(r"^(\d{4})_(0[1-9]|1[0-2])_to_(\d{4})_(0[1-9]|1[0-2])\.csv$")

def period_from_filename(path):
    match = FILE_PATTERN.match(path.name)
    if not match:
        raise ValueError()
    start_year, start_month, end_year, end_month = match.groups()
    return f"{start_year}_{start_month}", f"{end_year}_{end_month}"

def read_trades(path):
    trades = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"buy_price", "sell_price"}.issubset(reader.fieldnames or []):
            raise ValueError()

        for row in reader:
            try:
                buy_price = Decimal(row["buy_price"])
                sell_price = Decimal(row["sell_price"])
            except (InvalidOperation, TypeError):
                raise ValueError() from None
            if (
                not buy_price.is_finite()
                or not sell_price.is_finite()
                or buy_price <= 0
                or sell_price < 0
            ):
                raise ValueError()
            trades.append((buy_price, sell_price))
    return trades

def simulate(path, capital_start):
    start, end = period_from_filename(path)
    trades = read_trades(path)
    if trades:
        allocation = capital_start / len(trades)
        final_capital = sum(
            (allocation / buy_price) * sell_price
            for buy_price, sell_price in trades
        ).quantize(CAPITAL_QUANTUM)
    else:
        final_capital = capital_start
    pnl_value = final_capital - capital_start
    pnl_percent = pnl_value / capital_start * 100

    return [
        start,
        end,
        f"{capital_start:.{DECIMALS}f}",
        f"{final_capital:.{DECIMALS}f}",
        f"{pnl_value:.{DECIMALS}f}",
        f"{pnl_percent:.{DECIMALS}f}",
    ], final_capital

def simulate_strategy():
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError()

    input_files = sorted(
        path
        for path in INPUT_DIR.glob("*.csv")
        if FILE_PATTERN.match(path.name)
    )
    if not input_files:
        raise ValueError()

    capital = INITIAL_CAPITAL
    rows = []
    for path in input_files:
        row, capital = simulate(path, capital)
        rows.append(row)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

    print(f"Strategy simulation completed for {len(rows)} periods and saved to {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        simulate_strategy()
    except Exception as e:
        print(f"ERROR : {e}")

if __name__ == "__main__":
    main()
