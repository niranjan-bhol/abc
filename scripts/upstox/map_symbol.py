import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

NSE_SYMBOL_FILE = "symbol.txt"
UPSTOX_INSTRUMENT_FILE = "NSE.json"
SYMBOL_PATH = BASE_DIR / "data" / "nse" / "symbols" / NSE_SYMBOL_FILE
INSTRUMENT_PATH = BASE_DIR / "data" / "upstox" / "instruments" / UPSTOX_INSTRUMENT_FILE

OUTPUT_FILE = "mapped.json"
OUTPUT_DIR = BASE_DIR / "data" / "upstox" / "symbols"
OUTPUT_PATH = OUTPUT_DIR / OUTPUT_FILE
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

def read_symbols():
    lines = SYMBOL_PATH.read_text(encoding="utf-8").splitlines()
    symbols = list(dict.fromkeys(line.strip() for line in lines if line.strip()))
    if not symbols:
        raise ValueError()
    return symbols

def read_instruments():
    with open(INSTRUMENT_PATH, "r", encoding="utf-8") as file:
        instruments = json.load(file)
    if not isinstance(instruments, list):
        raise ValueError()
    return instruments

def build_mapping(symbols, instruments):
    wanted = set(symbols)
    best = {}
    for instrument in instruments:
        if not isinstance(instrument, dict) or instrument.get("segment") != "NSE_EQ":
            continue
        trading_symbol = instrument.get("trading_symbol")
        if trading_symbol not in wanted or not instrument.get("instrument_key"):
            continue
        current = best.get(trading_symbol)
        if current is None or (
            instrument.get("instrument_type") == "EQ"
            and current.get("instrument_type") != "EQ"
        ):
            best[trading_symbol] = instrument
    return {s: best[s]["instrument_key"] for s in symbols if s in best}

def export_mapping(mapping):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(mapping, file, indent=2)

def main():
    try:
        symbols = read_symbols()
        mapping = build_mapping(symbols, read_instruments())
        if not mapping:
            raise ValueError()
        export_mapping(mapping)
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    print(f"{len(mapping)}/{len(symbols)} symbols successfully mapped and exported to {OUTPUT_PATH_DISPLAY}/{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
