import csv
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "nse" / "historical" / "json"
OUTPUT_DIR = BASE_DIR / "data" / "nse" / "historical" / "csv"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

COLUMNS = [
    "CH_SYMBOL",
    "CH_SERIES",
    "mTIMESTAMP",
    "CH_PREVIOUS_CLS_PRICE",
    "CH_OPENING_PRICE",
    "CH_TRADE_HIGH_PRICE",
    "CH_TRADE_LOW_PRICE",
    "CH_LAST_TRADED_PRICE",
    "CH_CLOSING_PRICE",
    "VWAP",
    "CH_TOT_TRADED_QTY",
    "CH_TOT_TRADED_VAL",
    "CH_TOTAL_TRADES",
    "CH_TIMESTAMP",
    "COP_DELIV_QTY",
    "COP_DELIV_PERC",
]

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

def convert_file(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list) or not records:
        raise ValueError()

    csv_file = OUTPUT_DIR / f"{json_file.stem}.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    return len(records)

def convert_json_to_csv():
    json_files = sorted(INPUT_DIR.glob("*.json"))

    if not json_files:
        raise ValueError()

    prepare_output_dir()

    success_count = 0
    total = len(json_files)
    print(f"\nConverting {total} JSON files ...\n")
    width = len(str(total))
    name_width = max(len(f.stem) for f in json_files)

    for idx, json_file in enumerate(json_files, 1):
        print(f"[{idx:0{width}d}/{total}]  {json_file.stem:<{name_width}}  ->  ", end="", flush=True)
        try:
            row_count = convert_file(json_file)
            print(f"{row_count:>5} rows")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nConverted {success_count}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        convert_json_to_csv()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
