import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

IN_DIR = BASE_DIR / "data" / "backtest" / "pnl"
OUT_FILE = BASE_DIR / "data" / "backtest" / "summary.csv"
OUT_FILE_DISPLAY = f"{BASE_DIR.name}/{OUT_FILE.relative_to(BASE_DIR)}"

INITIAL_CAPITAL = 100000
BUY_OFFSET = 1   # buy month = file month + 1
SELL_OFFSET = 3  # sell month = file month + 3
DECIMALS = 4
HEADER = ["category", "start", "end", "pnl_value", "pnl_percent", "cagr", "drawdown"]


def month_index(path):
    return int(path.stem[:4]) * 12 + int(path.stem[5:7]) - 1


def label(index):
    return f"{index // 12}-{index % 12 + 1:02}"


def period_return(path):
    """Equal-weight return of one rebalance, as a fraction. None if no trades."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        values = [float(row["pnl_percent"]) for row in csv.DictReader(f) if row["pnl_percent"] != ""]
    if not values:
        return None
    return sum(values) / len(values) / 100


def summarize(category):
    periods = []
    for path in sorted(category.glob("*.csv")):
        ret = period_return(path)
        if ret is not None:
            periods.append((month_index(path), ret))
    if not periods:
        return None

    equity = INITIAL_CAPITAL
    peak = equity
    drawdown = 0.0
    for _, ret in periods:
        equity = max(equity * (1 + ret), 0.0)
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1)

    start = periods[0][0] + BUY_OFFSET
    end = periods[-1][0] + SELL_OFFSET
    years = (end - start + 1) / 12
    growth = equity / INITIAL_CAPITAL
    cagr = growth ** (1 / years) - 1

    pnl = equity - INITIAL_CAPITAL
    return [
        category.name,
        label(start),
        label(end),
        round(pnl, DECIMALS),
        round(pnl / INITIAL_CAPITAL * 100, DECIMALS),
        round(cagr * 100, DECIMALS),
        round(drawdown * 100, DECIMALS),
    ]


def main():
    if not IN_DIR.exists():
        print(f"ERROR : input directory not found : {IN_DIR}")
        return
    categories = sorted(p for p in IN_DIR.iterdir() if p.is_dir())

    rows = []
    for category in categories:
        try:
            row = summarize(category)
        except (OSError, KeyError, ValueError, csv.Error) as exc:
            print(f"ERROR : {category.name} : {type(exc).__name__} : {exc}")
            continue
        if row is None:
            print(f"WARN : {category.name} has no trades")
            continue
        rows.append(row)

    if not rows:
        print("ERROR : nothing to export")
        return

    rows.sort(key=lambda row: row[5], reverse=True)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

    print(f"Summarized {len(rows)}/{len(categories)} categories")
    print(f"Saved to : {OUT_FILE_DISPLAY}")


if __name__ == "__main__":
    main()
