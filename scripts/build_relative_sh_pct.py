import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "nse" / "sh_processed" / "shareholding_pct"
OUT_DIR = ROOT / "data" / "realtive_sh_pct"

SYMBOL_COL = "Symbol"

def to_number(raw):
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None

def month_index(path):
    year, month = path.stem.split("_")
    return int(year) * 12 + int(month) - 1

def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = [c for c in reader.fieldnames if c != SYMBOL_COL]
        data = {row[SYMBOL_COL]: row for row in reader}
    return columns, data

def relative_change(cur, prev):
    # (cur - prev) / prev as a fraction; blank when either value is missing or prev is 0
    cur, prev = to_number(cur), to_number(prev)
    if cur is None or prev is None or prev == 0:
        return ""
    # + 0.0 turns a rounded "-0.0000" into "0.0000"
    return f"{round((cur - prev) / prev, 4) + 0.0:.4f}"

def main():
    files = sorted(IN_DIR.glob("*.csv"), key=month_index)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prev_path, prev_data = None, None
    for path in files:
        columns, data = load(path)
        # The first month, or a month following a gap, has no previous month to compare with
        if prev_path is not None and month_index(path) - month_index(prev_path) == 1:
            with (OUT_DIR / path.name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([SYMBOL_COL] + columns)
                for symbol, row in data.items():
                    prev_row = prev_data.get(symbol)
                    writer.writerow(
                        [symbol]
                        + [
                            relative_change(row.get(c), prev_row.get(c)) if prev_row else ""
                            for c in columns
                        ]
                    )
            print(f"{path.name}: {len(data)} symbols")
        else:
            print(f"{path.name}: skipped (no previous month)")
        prev_path, prev_data = path, data

    print(f"Done -> {Path(ROOT.name) / OUT_DIR.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
