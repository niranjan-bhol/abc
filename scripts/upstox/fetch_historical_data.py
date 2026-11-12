import json
import shutil
import requests
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SYMBOLS_FILE = "mapped.json"
TOKEN_FILE = "access_token.txt"
SYMBOL_PATH = BASE_DIR / "data" / "upstox" / "symbols" / SYMBOLS_FILE
TOKEN_PATH = BASE_DIR / "data" / "upstox" / "authentication" / TOKEN_FILE

OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "historical" / "json"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

BASE_URL = "https://api.upstox.com/v3/historical-candle"

START_DATE = "2021-01-01"
END_DATE = "2026-11-10"

def load_symbols():
    with open(SYMBOL_PATH, "r") as f:
        return json.load(f)

def load_access_token():
    with open(TOKEN_PATH, "r") as f:
        return f.read().strip()

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

def fetch_historical_data(session, instrument_key):
    encoded_instrument = quote(instrument_key, safe="")
    url = f"{BASE_URL}/{encoded_instrument}/days/1/{END_DATE}/{START_DATE}"

    response = session.get(url, timeout=30)
    if not response.ok:
        raise RuntimeError()

    data = response.json()
    candles = data.get("data", {}).get("candles") if isinstance(data, dict) else None
    if data.get("status") != "success" or not candles:
        raise ValueError()
    return data

def save_data(symbol_name, data):
    output_file = OUTPUT_DIR / f"{symbol_name}.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

def download_historical_data(symbols, access_token):
    prepare_output_dir()
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    })

    success_count = 0
    total = len(symbols)
    print(f"\nDownloading data for {total} symbols ...\n")
    width = len(str(total))
    name_width = max(len(name) for name in symbols)

    for idx, (symbol_name, instrument_key) in enumerate(symbols.items(), 1):
        print(f"[{idx:0{width}d}/{total}]  {symbol_name:<{name_width}}  ->  ", end="", flush=True)
        try:
            data = fetch_historical_data(session, instrument_key)
            save_data(symbol_name, data)
            print(f"{len(data['data']['candles']):>4} candles")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nDownloaded data for {success_count}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        access_token = load_access_token()
        symbols = load_symbols()
        download_historical_data(symbols, access_token)
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
