import csv
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "nse" / "historical" / "csv"
OUTPUT_DIR = BASE_DIR / "data" / "nse" / "historical" / "csv_transformed"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

DATE_COLUMN = "mTIMESTAMP"
SERIES_PRIORITY = ["EQ", "RR", "BE", "BZ"]
COLUMN_MAP = {
    DATE_COLUMN: "date",
    "CH_SERIES": "series",
    "CH_OPENING_PRICE": "open",
    "CH_TRADE_HIGH_PRICE": "high",
    "CH_TRADE_LOW_PRICE": "low",
    "CH_CLOSING_PRICE": "close",
    "CH_LAST_TRADED_PRICE": "last_traded_price",
    "CH_PREVIOUS_CLS_PRICE": "prev_close",
    "VWAP": "vwap",
    "CH_TOTAL_TRADES": "total_trades",
    "CH_TOT_TRADED_QTY": "total_traded_qty",
    "CH_TOT_TRADED_VAL": "total_traded_val",
    "COP_DELIV_QTY": "delivered_qty",
    "COP_DELIV_PERC": "delivery_pct",
}

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"\nOutput directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUTPUT_PATH_DISPLAY}")

def series_rank(row):
    series = row["series"]
    if series in SERIES_PRIORITY:
        return SERIES_PRIORITY.index(series)
    return len(SERIES_PRIORITY)

def transform_file(csv_file):
    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not set(COLUMN_MAP).issubset(reader.fieldnames):
            raise ValueError()
        rows_by_date = {}
        for row in reader:
            new_row = {new: row[old] for old, new in COLUMN_MAP.items()}
            new_row["date"] = (
                datetime.strptime(row[DATE_COLUMN], "%d-%b-%Y").date().isoformat()
            )
            existing = rows_by_date.get(new_row["date"])
            if existing is None or series_rank(new_row) < series_rank(existing):
                rows_by_date[new_row["date"]] = new_row
        rows = list(rows_by_date.values())

    if not rows:
        raise ValueError()

    rows.sort(key=lambda r: r["date"])

    output_file = OUTPUT_DIR / csv_file.name
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(COLUMN_MAP.values()))
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

def transform_csv():
    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:
        raise ValueError()

    prepare_output_dir()

    success_count = 0
    total = len(csv_files)
    print(f"\nTransforming {total} CSV files ...\n")
    width = len(str(total))
    name_width = max(len(f.stem) for f in csv_files)

    for idx, csv_file in enumerate(csv_files, 1):
        print(f"[{idx:0{width}d}/{total}]  {csv_file.stem:<{name_width}}  ->  ", end="", flush=True)
        try:
            row_count = transform_file(csv_file)
            print(f"{row_count:>4} rows")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nTransformed {success_count}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        transform_csv()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
