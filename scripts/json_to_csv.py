import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "json"
OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "csv"

def display_path(path):
    return f"{BASE_DIR.name}/{path.relative_to(BASE_DIR).as_posix()}"

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*.csv"):
            file.unlink()
        print(f"Output directory exists : {display_path(OUTPUT_DIR)}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory : {display_path(OUTPUT_DIR)}")

def convert_json_to_csv():
    json_files = sorted(INPUT_DIR.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {display_path(INPUT_DIR)}")
        return
    
    prepare_output_dir()
    print()
    
    success_count = 0
    total = len(json_files)
    width = len(str(total))
    name_width = max(len(f.stem) for f in json_files)
    
    for idx, json_file in enumerate(json_files, 1):
        print(f"[{idx:0{width}d}/{total}]  {json_file.stem:<{name_width}}  ->  ", end="", flush=True)
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            candles = data.get("data", {}).get("candles", [])
            
            if not candles:
                print("ERROR (No candle data found)")
                continue
            
            csv_filename = json_file.stem + ".csv"
            csv_file = OUTPUT_DIR / csv_filename
            
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "oi"
                ])
                
                for candle in sorted(candles, key=lambda c: c[0]):
                    # "2026-11-09T00:00:00+05:30" -> "2026-11-09"
                    writer.writerow([str(candle[0])[:10], *candle[1:]])
            
            print(f"{len(candles):>4} rows")
            success_count += 1
        
        except Exception as e:
            print(f"ERROR ({e})")
    
    print(f"\nDownloaded data for {success_count}/{total} symbols")
    print(f"Saved to : {display_path(OUTPUT_DIR)}")

def main():
    convert_json_to_csv()

if __name__ == "__main__":
    main()
