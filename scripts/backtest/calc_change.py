import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

IN_DIR = BASE_DIR / "data" / "nse" / "processed"
OUT_DIR = BASE_DIR / "data" / "backtest" / "new"
OUT_DIR_DISPLAY = f"{BASE_DIR.name}/{OUT_DIR.relative_to(BASE_DIR)}"

START_YEAR, START_MONTH = 2021, 1
# first month is only the baseline; output starts from the next one
FIRST_OUTPUT = (2021, 2)
END_YEAR, END_MONTH = 2026, 11

KEY_COLUMN = "Symbol"
SKIP_COLUMNS = {"Symbol", "SubmissionDate"}
DECIMALS = 4


def month_range():
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (END_YEAR, END_MONTH):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def read_month(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = {row[KEY_COLUMN]: row for row in reader}
    return columns, rows


def pct_change(current, previous):
    cur, prev = to_float(current), to_float(previous)
    if cur is None or prev is None:
        return ""
    if prev == 0:
        return 0.0 if cur == 0 else ""
    return round((cur - prev) / abs(prev) * 100, DECIMALS)


def main():
    if not IN_DIR.exists():
        print(f"ERROR : input directory not found : {IN_DIR}")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prev_rows = {}
    for year, month in month_range():
        name = f"{year}_{month:02}.csv"
        path = IN_DIR / name
        if not path.exists():
            print(f"WARN : {name} missing")
            prev_rows = {}
            continue

        try:
            columns, rows = read_month(path)
            if (year, month) < FIRST_OUTPUT:
                prev_rows = rows
                print(f"{name} -> baseline")
                continue
            value_columns = [c for c in columns if c not in SKIP_COLUMNS]
            out_rows = []
            for symbol, row in rows.items():
                prev = prev_rows.get(symbol, {})
                out = [symbol, row.get("SubmissionDate", "")]
                out += [pct_change(row.get(c), prev.get(c)) for c in value_columns]
                out_rows.append(out)

            with (OUT_DIR / name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([KEY_COLUMN, "SubmissionDate", *value_columns])
                writer.writerows(out_rows)
        except (OSError, KeyError, csv.Error) as exc:
            print(f"ERROR : {name} : {type(exc).__name__} : {exc}")
            prev_rows = {}
            continue

        prev_rows = rows
        print(f"{name} -> {len(out_rows)} symbols")

    print(f"\nSaved to : {OUT_DIR_DISPLAY}")


if __name__ == "__main__":
    main()