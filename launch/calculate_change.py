import csv
import math
import shutil
from calendar import month_abbr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "nse" / "processed"
OUTPUT_DIR = BASE_DIR / "data" / "launch" / "change"

OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"
INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"

START_YEAR, START_MONTH = 2021, 1
END_YEAR, END_MONTH = 2026, 11

KEY_COLUMN = "Symbol"
DATE_COLUMN = "SubmissionDate"
VALUE_COLUMNS = ("InstitutionsDomestic", "InstitutionsForeign")
DECIMALS = 2

def to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None

def month_range():
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (END_YEAR, END_MONTH):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

def read_month(path):
    if not path.is_file():
        raise FileNotFoundError()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        missing = [c for c in (KEY_COLUMN, DATE_COLUMN, *VALUE_COLUMNS) if c not in columns]
        if missing:
            raise ValueError()
        rows = {}
        for row in reader:
            symbol = (row.get(KEY_COLUMN) or "").strip()
            if symbol:
                rows[symbol] = row
    if not rows:
        raise ValueError()
    return rows

def pct_change(current, previous):
    cur, prev = to_float(current), to_float(previous)
    if cur is None or prev is None:
        return ""
    if prev == 0:
        return f"{0:.{DECIMALS}f}" if cur == 0 else ""
    return f"{(cur - prev) / abs(prev) * 100:.{DECIMALS}f}"

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

def save_change(name, rows, prev_rows):
    out_rows = []
    for symbol, row in rows.items():
        prev = prev_rows.get(symbol, {})
        out_rows.append([
            symbol,
            row.get(DATE_COLUMN) or "",
            *(pct_change(row.get(c), prev.get(c)) for c in VALUE_COLUMNS),
        ])

    with open(OUTPUT_DIR / name, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([KEY_COLUMN, DATE_COLUMN, *VALUE_COLUMNS])
        writer.writerows(out_rows)

    return len(out_rows)

def calculate_change():
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError()

    months = list(month_range())
    if not any((INPUT_DIR / f"{y}_{m:02}.csv").exists() for y, m in months):
        raise ValueError()

    prepare_output_dir()

    success_count = 0
    total = len(months)
    print(f"\nCalculating monthly changes in shareholding percentages across {total} months ...\n")
    prev_rows = {}

    for year, month in months:
        name = f"{year}_{month:02}.csv"
        label = f"{month_abbr[month].upper()} {year}"
        print(f"{label}  -> ", end="", flush=True)
        try:
            rows = read_month(INPUT_DIR / name)
            if prev_rows:
                result = f"{save_change(name, rows, prev_rows)} symbols"
            else:
                result = "baseline"
            print(f"{result:>12}")
            prev_rows = rows
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")
            prev_rows = {}

    print(f"\nCompleted monthly shareholding change calculations for {success_count}/{total} months")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        calculate_change()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
