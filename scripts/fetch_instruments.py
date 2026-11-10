import json
import gzip
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "instruments"

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

def download_instruments():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    relative_output = Path("/") / OUTPUT_DIR.relative_to(BASE_DIR.parent)
    print(f"Output directory: {relative_output}")
    print(f"\nDownloading {len(INSTRUMENTS)} instrument files")
    
    success_count = 0
    failed_files = []
    
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
            
            print(f"✓ {filename}")
            success_count += 1
            
        except Exception as e:
            print(f"✕ {filename} - {str(e)}")
            failed_files.append(filename)
    
    print(f"\nSuccessfully downloaded {success_count}/{len(INSTRUMENTS)} files")

def main():
    download_instruments()

if __name__ == "__main__":
    main()
