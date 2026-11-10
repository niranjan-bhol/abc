import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_FILE = "symbols.json"
ACCESS_TOKEN_FILE = "access_token.txt"
SYMBOL_PATH = BASE_DIR / "data" / "upstox" / "symbols" / SYMBOLS_FILE
TOKEN_PATH = BASE_DIR / "data" / "upstox" / "auth" / ACCESS_TOKEN_FILE
OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "json"

API_BASE_URL = "https://api.upstox.com/v3/historical-candle"

START_DATE = "2021-01-01"
END_DATE = "2026-11-10"

def load_access_token():
    with open(TOKEN_PATH, "r") as f:
        return f.read().strip()

def load_symbols():
    with open(SYMBOL_PATH, "r") as f:
        return json.load(f)

def setup_output_directory():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for file in OUTPUT_DIR.glob("*.json"):
        file.unlink()

def fetch_historical_data(instrument_key, access_token):
    encoded_instrument = requests.utils.quote(instrument_key, safe='')
    
    url = f"{API_BASE_URL}/{encoded_instrument}/days/1/{END_DATE}/{START_DATE}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_symbol(symbol_name, instrument_key, access_token, idx, total):
    print(f"\n[{idx}/{total}] {symbol_name}")
    print(f"  Instrument : {instrument_key}")
    
    print(f"  Date range : {START_DATE} to {END_DATE}")
    
    final_data = fetch_historical_data(instrument_key, access_token)
    
    if not final_data:
        print("  No data fetched")
        return False
    
    output_file = OUTPUT_DIR / f"{symbol_name}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)
    
    total_candles = len(final_data.get("data", {}).get("candles", []))
    print(f"  Saved : {total_candles:,} total candles to {symbol_name}.json")
    
    return True

def main():
    try:
        access_token = load_access_token()
        symbols = load_symbols()
        
        setup_output_directory()
        
        relative_output = Path("/") / OUTPUT_DIR.relative_to(BASE_DIR.parent)
        print(f"Output directory: {relative_output}")
        
        success_count = 0
        total_symbols = len(symbols)
        
        for idx, (symbol_name, instrument_key) in enumerate(symbols.items(), 1):
            if process_symbol(symbol_name, instrument_key, access_token, idx, total_symbols):
                success_count += 1
        
        print(f"\nSuccessfully downloaded data for {success_count}/{total_symbols} symbols")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
