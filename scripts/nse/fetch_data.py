import json
import time
import shutil
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SYMBOL_FILE = "symbol.txt"
SYMBOL_PATH = BASE_DIR / "data" / "nse" / "symbols" / SYMBOL_FILE
OUTPUT_DIR = BASE_DIR / "data" / "nse" / "historical" / "json"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

START_DATE = date(2021, 1, 1)
END_DATE = date(2026, 10, 31)
CHUNK_MONTHS = 3

API_ROW_CAP = 70
RETRIES = 3
CHUNK_SLEEP = 0.5
SYMBOL_SLEEP = 1
SESSION_REFRESH_RANGE = (15, 35)
SYMBOL_RETRY_BACKOFF = 15
MAX_WORKERS = 10

BASE_URL = "https://www.nseindia.in"
API_URL = f"{BASE_URL}/api/historicalOR/generateSecurityWiseHistoricalData"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.7",
    "referer": f"{BASE_URL}/report-detail/eq_security",
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

def build_chunks():
    chunks = []
    start = START_DATE
    while start <= END_DATE:
        month_index = start.year * 12 + start.month - 1 + CHUNK_MONTHS
        next_start = date(month_index // 12, month_index % 12 + 1, 1)
        chunks.append((start, min(next_start - timedelta(days=1), END_DATE)))
        start = next_start
    return chunks

CHUNKS = build_chunks()

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

def fetch_chunk(session, symbol, start, end):
    params = {
        "from": start.strftime("%d-%m-%Y"),
        "to": end.strftime("%d-%m-%Y"),
        "symbol": symbol,
        "type": "priceVolumeDeliverable",
        "series": "ALL",
    }
    for attempt in range(RETRIES):
        try:
            resp = session.get(API_URL, params=params, timeout=15)
            resp.raise_for_status()
            records = resp.json()["data"]
            if not isinstance(records, list):
                raise ValueError()
            return records, attempt > 0
        except (requests.RequestException, ValueError, KeyError, TypeError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2**attempt)

def row_date(record):
    return datetime.strptime(record["mTIMESTAMP"], "%d-%b-%Y").date()

def fetch_range(session, symbol, start, end):
    # The API caps a response at API_ROW_CAP rows, dropping the earliest dates, so a full
    # response is incomplete: drop its (maybe partial) earliest date and refetch up to it
    records, retried = fetch_chunk(session, symbol, start, end)
    if len(records) < API_ROW_CAP or start >= end:
        return records, retried, False
    earliest = min(row_date(r) for r in records)
    if earliest >= end:
        return records, retried, False
    kept = [r for r in records if row_date(r) > earliest]
    time.sleep(CHUNK_SLEEP)
    older, older_retried, _ = fetch_range(session, symbol, start, earliest)
    return kept + older, retried or older_retried, True

_local = threading.local()
_session_lock = threading.Lock()

def get_session(force_new=False):
    # One session per worker thread (requests.Session is not guaranteed thread-safe)
    if force_new or getattr(_local, "session", None) is None or _local.count >= _local.limit:
        _local.session = None
        # Serialize session creation to avoid bursts against the homepage
        with _session_lock:
            _local.session = create_session()
        _local.count = 0
        # Random limit per thread so workers don't all refresh at the same symbol
        _local.limit = random.randint(*SESSION_REFRESH_RANGE)
    _local.count += 1
    return _local.session

def fetch_symbol(symbol, session):
    rows = []
    retried = False
    rechunked = False
    for index, (start, end) in enumerate(CHUNKS):
        if index:
            time.sleep(CHUNK_SLEEP)
        chunk, chunk_retried, chunk_rechunked = fetch_range(session, symbol, start, end)
        retried = retried or chunk_retried
        rechunked = rechunked or chunk_rechunked
        rows.extend(chunk)
    return rows, retried, rechunked

def process_symbol(symbol, label):
    try:
        # On failure, back off and retry the whole symbol with a brand new session,
        # since the server may be throttling or have invalidated the old one
        for attempt in range(RETRIES):
            try:
                rows, retried, rechunked = fetch_symbol(symbol, get_session(force_new=attempt > 0))
                break
            except (requests.RequestException, ValueError, KeyError, TypeError):
                if attempt == RETRIES - 1:
                    raise
                time.sleep(SYMBOL_RETRY_BACKOFF * (attempt + 1))
        (OUTPUT_DIR / f"{symbol}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        retried = retried or attempt > 0
    except (requests.RequestException, ValueError, KeyError, TypeError, OSError) as error:
        return False, f"{label}->   ERROR : {type(error).__name__}"
    finally:
        time.sleep(SYMBOL_SLEEP)
    tags = [tag for tag, used in (("rechunked", rechunked), ("retry", retried)) if used]
    suffix = f"  ({' & '.join(tags)})" if tags else ""
    return True, f"{label}->  {len(rows):>5} records{suffix}"

def main():
    try:
        symbols = read_symbols()
        if not symbols:
            raise ValueError()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(symbols)
    width = len(str(total))
    workers = min(MAX_WORKERS, total)
    print(f"\nDownloading data for {total} symbols using {workers} workers ...\n")

    labels = [
        f"[{index:0{width}}/{total}]  {symbol:<12}"
        for index, symbol in enumerate(symbols, start=1)
    ]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(process_symbol, symbol, label)
            for symbol, label in zip(symbols, labels)
        ]
        success = 0
        for future in futures:
            ok, message = future.result()
            print(message, flush=True)
            success += ok

    print(f"\nDownloaded data for {success}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
