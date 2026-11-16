import json
import gzip
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent

OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "instruments"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

BASE_URL = "https://assets.upstox.com/market-quote/instruments/exchange/"

INSTRUMENTS = [
    "complete.json.gz",
    "NSE.json.gz",
    "BSE.json.gz",
    "MCX.json.gz",
    "NSE_MIS.json.gz",
    "BSE_MIS.json.gz",
    "MTF.json.gz",
    "suspended-instrument.json.gz",
    "mf-instruments.json.gz",
    "global.json.gz"
]

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*.csv"):
                file.unlink()
        print(f"\nOutput directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUTPUT_PATH_DISPLAY}")

def download_instruments():
    prepare_output_dir()
    print(f"\nDownloading {len(INSTRUMENTS)} instrument files ...")

    success_count = 0

    for instrument_file in INSTRUMENTS:
        filename = instrument_file.replace(".gz", "")
        url = BASE_URL + instrument_file
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = gzip.decompress(response.content)
            instruments = json.loads(data.decode("utf-8"))
            output_file = OUTPUT_DIR / filename
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(instruments, file, indent=2)
            print(f"‣ {filename}")
            success_count += 1
        except Exception as e:
            print(f"‣ {filename} -> {type(e).__name__}")

    print(f"\nDownloaded {success_count}/{len(INSTRUMENTS)} instrument files")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    download_instruments()

if __name__ == "__main__":
    main()
