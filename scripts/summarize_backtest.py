import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKTEST_DIR = ROOT / "data" / "backtest"
OUTPUT_DIR = ROOT / "data" / "results"

METRICS = ["number_of_shareholders", "shareholding_pct"]
OUT_COLUMNS = ["category", "pnl_value", "pnl_percent"]

def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def summarize_folder(folder):
    pnl_value = pnl_percent = 0.0
    for path in sorted(folder.glob("*.csv")):
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                pnl_value += to_float(row.get("pnl_value"))
                pnl_percent += to_float(row.get("pnl_percent"))
    return pnl_value, pnl_percent

def main():
    for metric in METRICS:
        in_dir = BACKTEST_DIR / metric
        rows = []
        for folder in sorted(p for p in in_dir.iterdir() if p.is_dir()):
            pnl_value, pnl_percent = summarize_folder(folder)
            rows.append(
                {
                    "category": folder.name,
                    "pnl_value": round(pnl_value, 2),
                    "pnl_percent": round(pnl_percent, 2),
                }
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{metric}.csv"
        with out_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
