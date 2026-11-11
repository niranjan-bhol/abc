import json
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_FILE = "symbol.json"
ACCESS_TOKEN_FILE = "access_token.txt"
SYMBOL_PATH = BASE_DIR / "data" / "upstox" / "symbols" / SYMBOLS_FILE
TOKEN_PATH = BASE_DIR / "data" / "upstox" / "auth" / ACCESS_TOKEN_FILE
OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "json"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

API_BASE_URL = "https://api.upstox.com/v3/historical-candle"

START_DATE = "2021-01-01"
END_DATE = "2026-11-10"

def load_access_token():
    with open(TOKEN_PATH, "r") as f:
        return f.read().strip()

def load_symbols():
    with open(SYMBOL_PATH, "r") as f:
        return json.load(f)

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for file in OUTPUT_DIR.glob("*.json"):
            file.unlink()
        print(f"Output directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory : {OUTPUT_PATH_DISPLAY}")

def fetch_historical_data(instrument_key, access_token):
    encoded_instrument = requests.utils.quote(instrument_key, safe='')
    
    url = f"{API_BASE_URL}/{encoded_instrument}/days/1/{END_DATE}/{START_DATE}"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def process_symbol(symbol_name, instrument_key, access_token, idx, total, name_width, key_width):
    width = len(str(total))
    print(f"[{idx:0{width}d}/{total}]  {symbol_name:<{name_width}}  ->  ", end="", flush=True)
    
    try:
        data = fetch_historical_data(instrument_key, access_token)
        
        output_file = OUTPUT_DIR / f"{symbol_name}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        total_candles = len(data["data"]["candles"])
    
    except Exception as e:
        print(f"ERROR ({e})")
        return False
    
    print(f"{total_candles:>4} candles")
    return True

def main():
    try:
        access_token = load_access_token()
        symbols = load_symbols()
        
        prepare_output_dir()
        print()
        
        success_count = 0
        total_symbols = len(symbols)
        name_width = max(len(name) for name in symbols)
        key_width = max(len(key) for key in symbols.values())
        
        for idx, (symbol_name, instrument_key) in enumerate(symbols.items(), 1):
            if process_symbol(symbol_name, instrument_key, access_token, idx, total_symbols, name_width, key_width):
                success_count += 1
        
        print(f"\nDownloaded data for {success_count}/{total_symbols} symbols")
        print(f"Saved to : {OUTPUT_PATH_DISPLAY}")
    
    except Exception as e:
        print(f"ERROR : {e}")

if __name__ == "__main__":
    main()
