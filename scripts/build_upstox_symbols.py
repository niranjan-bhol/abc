import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

SYMBOL_FILE = DATA_DIR / "symbol" / "symbol.txt"
OUTPUT_FILE = DATA_DIR / "upstox" / "symbols" / "symbol.json"

# NSE.json is downloaded to either location depending on the fetch script used
INSTRUMENT_CANDIDATES = [
    DATA_DIR / "upstox" / "instruments" / "NSE.json",
    BASE_DIR / "upstox" / "instruments" / "NSE.json",
]


def find_instruments_file():
    for path in INSTRUMENT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "NSE.json not found in: " + ", ".join(str(p) for p in INSTRUMENT_CANDIDATES)
    )


def priority(instrument):
    # Prefer plain NSE equity over bonds/other series sharing a trading symbol
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

    instruments_file = find_instruments_file()
    with open(instruments_file, "r", encoding="utf-8") as file:
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
