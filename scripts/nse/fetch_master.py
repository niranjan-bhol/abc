import json
import time
import shutil
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SYMBOL_FILE = "symbol.txt"
SYMBOL_PATH = BASE_DIR / "data" / "nse" / "symbols" / SYMBOL_FILE
OUTPUT_DIR = BASE_DIR / "data" / "nse" / "master"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

RETRIES = 3
REQUEST_SLEEP = 0.5
SESSION_REFRESH_INTERVAL = 100

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
    return [
        s.strip()
        for s in SYMBOL_PATH.read_text(encoding="utf-8").splitlines()
        if s.strip()
    ]

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

def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    for attempt in range(RETRIES):
        try:
            session.get(BASE_URL, timeout=10).raise_for_status()
            time.sleep(1)
            return session
        except requests.RequestException:
            if attempt == RETRIES - 1:
                raise
            time.sleep(2**attempt)

def process_symbol(session, symbol, label):
    error = None
    for attempt in range(RETRIES):
        try:
            resp = session.get(
                API_URL, params={"index": "equities", "symbol": symbol}, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            (OUTPUT_DIR / f"{symbol}.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except (requests.RequestException, ValueError, OSError) as exc:
            error = exc
            if attempt < RETRIES - 1:
                time.sleep(2**attempt)
            continue
        suffix = "  (retry)" if attempt else ""
        print(f"{label}->  SUCCESS{suffix}")
        return True
    print(f"{label}->  ERROR : {type(error).__name__}")
    return False

def main():
    try:
        symbols = read_symbols()
        if not symbols:
            raise ValueError()
        session = create_session()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(symbols)
    width = len(str(total))
    print(f"\nDownloading data for {total} symbols ...\n")

    success = 0
    for index, symbol in enumerate(symbols, start=1):
        if index > 1 and (index - 1) % SESSION_REFRESH_INTERVAL == 0:
            try:
                session = create_session()
            except requests.RequestException as error:
                print(f"\nERROR : {type(error).__name__}")
                break
            print("\n--- SESSION REFRESHED ---\n")
        label = f"[{index:0{width}}/{total}]  {symbol:<12}"
        success += process_symbol(session, symbol, label)
        time.sleep(REQUEST_SLEEP)

    print(f"\nDownloaded data for {success}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
