import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).parent
SYMBOLS_FILE = "symbols.json"
ACCESS_TOKEN_FILE = "access_token.txt"
TOKEN_PATH = BASE_DIR / "data" / "auth" / ACCESS_TOKEN_FILE
OUTPUT_DIR = BASE_DIR / "data" / "historical" / "json"

API_BASE_URL = "https://api.upstox.com/v3/historical-candle"

DATE_RANGES = {
    "minutes": {"start": "2022-01-01"},
    "hours": {"start": "2022-01-01"},
    "days": {"start": "2000-01-01"},
    "weeks": {"start": "2000-01-01"},
    "months": {"start": "2000-01-01"}
}

CHUNK_RULES = {
    "minutes_1_to_15": relativedelta(months=1),
    "minutes_gt_15": relativedelta(months=3),
    "hours": relativedelta(months=3),
    "days": relativedelta(years=10),
    "weeks": None,
    "months": None
}

def load_access_token():
    with open(TOKEN_PATH, "r") as f:
        return f.read().strip()

def load_symbols():
    with open(SCRIPTS_DIR / SYMBOLS_FILE, "r") as f:
        return json.load(f)

def setup_output_directory():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for file in OUTPUT_DIR.glob("*.json"):
        file.unlink()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Fetch historical data from Upstox API')
    parser.add_argument('--unit', type=str, required=True,
                        choices=['minutes', 'hours', 'days', 'weeks', 'months'],
                        help='Time unit for candles')
    parser.add_argument('--interval', type=int, required=True,
                        help='Interval value (1-300 for minutes, 1-5 for hours, 1 for others)')
    
    args = parser.parse_args()
    
    interval_ranges = {
        "minutes": (1, 300),
        "hours": (1, 5),
        "days": (1, 1),
        "weeks": (1, 1),
        "months": (1, 1)
    }
    
    min_int, max_int = interval_ranges[args.unit]
    if not (min_int <= args.interval <= max_int):
        parser.error(f"Interval must be between {min_int} and {max_int} for {args.unit}")
    
    return args.unit, args.interval

def determine_chunk_rule(unit, interval):
    if unit == "minutes":
        if 1 <= interval <= 15:
            return CHUNK_RULES["minutes_1_to_15"]
        else:
            return CHUNK_RULES["minutes_gt_15"]
    elif unit == "hours":
        return CHUNK_RULES["hours"]
    elif unit == "days":
        return CHUNK_RULES["days"]
    elif unit in ["weeks", "months"]:
        return CHUNK_RULES[unit]

def generate_date_chunks(start_date_str, end_date_str, chunk_delta):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    if chunk_delta is None:
        return [(start_date_str, end_date_str)]
    
    chunks = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = current_start + chunk_delta - timedelta(days=1)
        if current_end > end_date:
            current_end = end_date
        
        chunks.append((
            current_start.strftime("%Y-%m-%d"),
            current_end.strftime("%Y-%m-%d")
        ))
        
        current_start = current_end + timedelta(days=1)
    
    return chunks

def fetch_historical_data(instrument_key, unit, interval, to_date, from_date, access_token):
    encoded_instrument = requests.utils.quote(instrument_key, safe='')
    
    url = f"{API_BASE_URL}/{encoded_instrument}/{unit}/{interval}/{to_date}/{from_date}"
    
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

def merge_candle_data(chunks_data):
    all_candles = []
    
    for chunk_data in chunks_data:
        if chunk_data and chunk_data.get("status") == "success":
            candles = chunk_data.get("data", {}).get("candles", [])
            all_candles.extend(candles)
    
    unique_candles = {}
    for candle in all_candles:
        timestamp = candle[0]
        unique_candles[timestamp] = candle
    
    sorted_candles = sorted(unique_candles.values(), key=lambda x: x[0])
    
    return {
        "status": "success",
        "data": {
            "candles": sorted_candles
        }
    }

def process_symbol(symbol_name, instrument_key, unit, interval, access_token, idx, total):
    print(f"\n[{idx}/{total}] {symbol_name}")
    print(f"  Instrument : {instrument_key}")
    
    start_date = DATE_RANGES[unit]["start"]
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"  Date range : {start_date} to {end_date}")
    
    chunk_delta = determine_chunk_rule(unit, interval)
    date_chunks = generate_date_chunks(start_date, end_date, chunk_delta)
    
    print(f"  Fetching data in {len(date_chunks)} chunks")
    
    chunks_data = []
    for chunk_idx, (from_date, to_date) in enumerate(date_chunks, 1):
        print(f"    Chunk {chunk_idx}/{len(date_chunks)}: {from_date} to {to_date}", end=" ")
        
        data = fetch_historical_data(
            instrument_key, unit, interval, to_date, from_date, access_token
        )
        
        if data:
            candle_count = len(data.get("data", {}).get("candles", []))
            print(f"({candle_count:,} candles)")
            chunks_data.append(data)
        else:
            pass
    
    if len(chunks_data) > 1:
        print("  Merging chunks")
        final_data = merge_candle_data(chunks_data)
    elif len(chunks_data) == 1:
        final_data = chunks_data[0]
    else:
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
        
        unit, interval = parse_arguments()
        
        setup_output_directory()
        
        relative_output = Path("/") / OUTPUT_DIR.relative_to(BASE_DIR.parent)
        print(f"Output directory: {relative_output}")
        
        success_count = 0
        total_symbols = len(symbols)
        
        for idx, (symbol_name, instrument_key) in enumerate(symbols.items(), 1):
            if process_symbol(symbol_name, instrument_key, unit, interval, access_token, idx, total_symbols):
                success_count += 1
        
        print(f"\nSuccessfully downloaded data for {success_count}/{total_symbols} symbols")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
