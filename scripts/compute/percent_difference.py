import csv
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "processed" / "enriched_manual"
OUTPUT_ROOT = BASE_DIR / "data" / "computed"

OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_ROOT.relative_to(BASE_DIR)}/"

DATE_COLUMN = "date"
LABELS = ["close", "vwap", "traded_quantity", "traded_value", "delivered_quantity", "delivered_value"]
MAX_LAG = 252
LAG_COLUMNS = [f"prev_{n}" for n in range(1, MAX_LAG + 1)]
DIGITS = 4

def prepare_output_dirs():
    print()
    for label in LABELS:
        out_dir = OUTPUT_ROOT / label
        display = f"{OUTPUT_PATH_DISPLAY}{label}"
        if out_dir.exists():
            for child in out_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            print(f"Output directory exists & cleared output directory : {display}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created output directory : {display}")

def compute_rows(dates, values):
    rows = []
    for i in range(1, len(values)):
        today = values[i]
        previous_values = values[max(0, i - MAX_LAG):i][::-1]
        row = [dates[i]]
        row.extend(
            f"{(today - p) / p * 100:.{DIGITS}f}" if p else ""
            for p in previous_values
        )
        row.extend([""] * (MAX_LAG - len(previous_values)))
        rows.append(row)
    return rows

def compute_file(csv_file):
    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {DATE_COLUMN, *LABELS}.issubset(reader.fieldnames):
            raise ValueError()
        data = list(reader)

    if len(data) < 2:
        raise ValueError()

    dates = [row[DATE_COLUMN] for row in data]

    for label in LABELS:
        values = [float(row[label]) for row in data]
        rows = compute_rows(dates, values)

        output_file = OUTPUT_ROOT / label / csv_file.name
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([DATE_COLUMN, *LAG_COLUMNS])
            writer.writerows(rows)

    return len(data) - 1

def compute_percent_diff():
    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:
        raise ValueError()

    prepare_output_dirs()

    success_count = 0
    total = len(csv_files)
    print(f"\nComputing percent difference for {total} CSV files ...\n")
    width = len(str(total))
    name_width = max(len(f.stem) for f in csv_files)

    for idx, csv_file in enumerate(csv_files, 1):
        print(f"[{idx:0{width}d}/{total}]  {csv_file.stem:<{name_width}}  ->  ", end="", flush=True)
        try:
            row_count = compute_file(csv_file)
            print(f"{row_count:>4} rows")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nComputed {success_count}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}<{' | '.join(LABELS)}>")

def main():
    try:
        compute_percent_diff()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
