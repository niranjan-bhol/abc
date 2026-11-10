import json
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
SYMBOL_FILE = ROOT / "data" / "symbol" / "symbol.txt"
OUT_DIR = ROOT / "data" / "nse" / "sh_master"
OUT_DIR_DISPLAY = f"{ROOT.name}/{OUT_DIR.relative_to(ROOT)}"

RETRIES = 3
REQUEST_SLEEP = 0.5

BASE_URL = "https://www.nseindia.com"
API_URL = f"{BASE_URL}/api/corporate-share-holdings-master"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.7",
    "referer": f"{BASE_URL}/companies-listing/corporate-filings-shareholding-pattern",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
}

def read_symbols():
    return [s.strip() for s in SYMBOL_FILE.read_text().splitlines() if s.strip()]

def prepare_output_dir():
    if OUT_DIR.exists():
        for file in OUT_DIR.glob("*.json"):
            file.unlink()
        print(f"Output directory exists : {OUT_DIR_DISPLAY}")
        print("Cleared output directory")
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory : {OUT_DIR_DISPLAY}")

def new_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    for attempt in range(RETRIES):
        try:
            session.get(BASE_URL, timeout=10).raise_for_status()
            time.sleep(1)
            return session
        except requests.RequestException:
            time.sleep(2**attempt)
    return None

def process_symbol(session, symbol, label):
    for attempt in range(RETRIES):
        try:
            resp = session.get(
                API_URL, params={"index": "equities", "symbol": symbol}, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            (OUT_DIR / f"{symbol}.json").write_text(json.dumps(data, indent=2))
        except (requests.RequestException, ValueError, OSError):
            time.sleep(2**attempt)
            continue
        suffix = "  (retry)" if attempt else ""
        print(f"{label}->  SUCCESS{suffix}")
        return True
    print(f"{label}->  ERROR")
    return False

def main():
    if not SYMBOL_FILE.exists():
        print("ERROR : Symbol file not found")
        return

    try:
        symbols = read_symbols()
    except OSError:
        print("ERROR : Unable to process symbol file")
        return
    if not symbols:
        print("ERROR : No symbols found in symbol file")
        return

    total = len(symbols)
    width = len(str(total))

    prepare_output_dir()
    print(f"\nDownloading data for {total} symbols\n")

    session = new_session()
    if session is None:
        print("ERROR : Unable to create NSE session")
        return

    success = 0
    for index, symbol in enumerate(symbols, start=1):
        label = f"[{index:0{width}}/{total}]  {symbol:<12}"
        success += process_symbol(session, symbol, label)
        time.sleep(REQUEST_SLEEP)

    print(f"\nDownloaded data for {success}/{total} symbols")
    print(f"Saved to : {OUT_DIR_DISPLAY}")

if __name__ == "__main__":
    main()
