import csv
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "json"
OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "csv"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

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
        data = json.load(f)

    candles = data.get("data", {}).get("candles") if isinstance(data, dict) else None
    if not candles:
        raise ValueError()

    csv_file = OUTPUT_DIR / f"{json_file.stem}.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume", "oi"])
        for candle in sorted(candles, key=lambda c: c[0]):
            writer.writerow([str(candle[0])[:10], *candle[1:]])

    return len(candles)

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
            print(f"{row_count:>4} rows")
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
