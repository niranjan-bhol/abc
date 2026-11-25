import re
import csv
import math
import statistics
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SUMMARY_DIR = BASE_DIR / "data" / "launch" / "summary"
INPUT_PATH = SUMMARY_DIR / "simulation.csv"
OUTPUT_PATH = SUMMARY_DIR / "summary.csv"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_PATH.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_PATH.relative_to(BASE_DIR)}"

DECIMALS = 2
HEADER = ["label", "value"]
RISK_FREE_RATE = 0.05

PERIOD_PATTERN = re.compile(r"^(\d{4})_(0[1-9]|1[0-2])$")

def period_index(value):
    match = PERIOD_PATTERN.match(value or "")
    if not match:
        raise ValueError()
    return int(match[1]) * 12 + int(match[2]) - 1

def label(index):
    return f"{index // 12}-{index % 12 + 1:02d}"

def ratio(numerator, denominator, decimals=DECIMALS):
    return f"{numerator / denominator:.{decimals}f}" if denominator else "N/A"

def read_periods():
    periods = []
    previous_capital = None
    previous_end = None
    with open(INPUT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"start", "end", "capital_start", "capital_end"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError()

        for row in reader:
            try:
                capital_start = float(row["capital_start"])
                capital_end = float(row["capital_end"])
            except (TypeError, ValueError):
                raise ValueError() from None

            start = period_index(row["start"])
            end = period_index(row["end"])
            if (
                not math.isfinite(capital_start)
                or not math.isfinite(capital_end)
                or capital_start <= 0
                or capital_end < 0
                or end < start
                or (previous_end is not None and start <= previous_end)
            ):
                raise ValueError()
            if previous_capital is not None and not math.isclose(
                capital_start, previous_capital, abs_tol=0.01
            ):
                raise ValueError()

            periods.append((start, end, capital_start, capital_end))
            previous_capital = capital_end
            previous_end = end
    return periods

def run_equity_curve(periods):
    equity = periods[0][2]
    peak = equity
    quarter_returns = []
    drawdowns = []
    for _, _, capital_start, capital_end in periods:
        quarter_returns.append(capital_end / capital_start - 1)
        equity = capital_end
        peak = max(peak, equity)
        drawdowns.append(equity / peak - 1)
    return equity, quarter_returns, drawdowns

def summarize():
    periods = read_periods()
    if not periods:
        return None

    final_equity, quarter_returns, drawdowns = run_equity_curve(periods)
    initial_capital = periods[0][2]

    start = periods[0][0]
    end = periods[-1][1]
    years = (end - start + 1) / 12
    cagr = (final_equity / initial_capital) ** (1 / years) - 1

    pnl_value = final_equity - initial_capital
    pnl_percent = pnl_value / initial_capital * 100

    frequency = len(quarter_returns) / years
    mean_return = statistics.fmean(quarter_returns)
    avg_annual_return = (1 + mean_return) ** frequency - 1

    winning_quarters = sum(1 for r in quarter_returns if r > 0)
    losing_quarters = sum(1 for r in quarter_returns if r < 0)
    win_rate = winning_quarters / len(quarter_returns) * 100

    max_drawdown = min(drawdowns)
    avg_drawdown = statistics.fmean(drawdowns)

    risk_free_per_quarter = (1 + RISK_FREE_RATE) ** (1 / frequency) - 1
    excess_returns = [r - risk_free_per_quarter for r in quarter_returns]
    annual_excess_return = statistics.fmean(excess_returns) * frequency

    volatility = (statistics.stdev(quarter_returns) if len(quarter_returns) > 1 else 0.0) * math.sqrt(frequency)
    downside_deviation = math.sqrt(statistics.fmean(min(r, 0.0) ** 2 for r in excess_returns)) * math.sqrt(frequency)

    return [
        ("start_date", label(start)),
        ("end_date", label(end)),
        ("initial_capital", f"{initial_capital:.{DECIMALS}f}"),
        ("final_capital", f"{final_equity:.{DECIMALS}f}"),
        ("pnl_value", f"{pnl_value:.{DECIMALS}f}"),
        ("pnl_percent", f"{pnl_percent:.{DECIMALS}f}"),
        ("cagr", f"{cagr * 100:.{DECIMALS}f}"),
        ("avg_annual_return", f"{avg_annual_return * 100:.{DECIMALS}f}"),
        ("best_quarter", f"{max(quarter_returns) * 100:.{DECIMALS}f}"),
        ("worst_quarter", f"{min(quarter_returns) * 100:.{DECIMALS}f}"),
        ("winning_quarters", winning_quarters),
        ("losing_quarters", losing_quarters),
        ("win_rate", f"{win_rate:.{DECIMALS}f}"),
        ("max_drawdown", f"{max_drawdown * 100:.{DECIMALS}f}"),
        ("avg_drawdown", f"{avg_drawdown * 100:.{DECIMALS}f}"),
        ("volatility", f"{volatility * 100:.{DECIMALS}f}"),
        ("sharpe_ratio", ratio(annual_excess_return, volatility)),
        ("sortino_ratio", ratio(annual_excess_return, downside_deviation)),
        ("calmar_ratio", ratio(cagr, abs(max_drawdown))),
    ]

def export_summary(rows):
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

def generate_summary():
    if not INPUT_PATH.is_file():
        raise FileNotFoundError()

    rows = summarize()
    if rows is None:
        raise ValueError()

    export_summary(rows)

    print(f"Summary generated and saved to {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        generate_summary()
    except Exception as e:
        print(f"ERROR : {e}")

if __name__ == "__main__":
    main()
