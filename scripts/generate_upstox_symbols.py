import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SYMBOL_FILE = BASE_DIR / "data" / "symbol" / "symbol.txt"
INSTRUMENT_FILE = BASE_DIR / "data" / "upstox" / "instruments" / "NSE.json"
OUTPUT_FILE = BASE_DIR / "data" / "upstox" / "symbols" / "symbol.json"

def priority(instrument):
    return (
        instrument.get("segment") == "NSE_EQ",
        instrument.get("instrument_type") == "EQ",
    )

def build_symbols():
    symbols = [
        line.strip()
        for line in SYMBOL_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    
    with open(INSTRUMENT_FILE, "r", encoding="utf-8") as file:
        instruments = json.load(file)
    
    wanted = set(symbols)
    best = {}
    for instrument in instruments:
        trading_symbol = instrument.get("trading_symbol")
        if trading_symbol not in wanted:
            continue
        current = best.get(trading_symbol)
        if current is None or priority(instrument) > priority(current):
            best[trading_symbol] = instrument
    
    result = {}
    missing = []
    for symbol in symbols:
        instrument = best.get(symbol)
        if instrument is None:
            missing.append(symbol)
        else:
            result[symbol] = instrument["instrument_key"]
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
    
    relative_output = Path("/") / OUTPUT_FILE.relative_to(BASE_DIR.parent)
    print(f"Matched {len(result)}/{len(symbols)} symbols exported to {relative_output.as_posix()}")
    if missing:
        print(f"Not found ({len(missing)}): {', '.join(missing)}")

def main():
    build_symbols()

if __name__ == "__main__":
    main()
