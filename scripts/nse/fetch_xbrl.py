import json
import time
import shutil
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SYMBOL_FILE = "symbol.txt"
IN_DIR = BASE_DIR / "data" / "nse" / "master"
OUT_DIR = BASE_DIR / "data" / "nse" / "xbrl"
OUT_DIR_DISPLAY = f"{BASE_DIR.name}/{OUT_DIR.relative_to(BASE_DIR)}"

RETRIES = 3
REQUEST_SLEEP = 0.2
SESSION_REFRESH_INTERVAL = 50

BASE_URL = "https://www.nseindia.com"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.7",
    "referer": f"{BASE_URL}/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
}

def prepare_output_dir():
    if OUT_DIR.exists():
        for child in OUT_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"\nOutput directory exists : {OUT_DIR_DISPLAY}")
        print("Cleared output directory")
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUT_DIR_DISPLAY}")

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

def download(session, url, out):
    error = None
    for attempt in range(RETRIES):
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            out.write_bytes(resp.content)
            return True, None
        except (requests.RequestException, OSError) as exc:
            error = exc
            if attempt < RETRIES - 1:
                time.sleep(2**attempt)
    return False, error

def process_symbol(session, file, label):
    out_dir = OUT_DIR / file.stem
    saved = failed = 0

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError()
    except (OSError, ValueError) as exc:
        print(f"{label}->  ERROR : {type(exc).__name__}")
        return saved, failed

    error_types = set()
    for row in rows:
        try:
            url, submission = row.get("xbrl"), row.get("submissionDate")
            if not url or not submission:
                continue
            submission_str = datetime.strptime(submission, "%d-%b-%Y").strftime("%Y%m%d")
        except (AttributeError, ValueError) as exc:
            failed += 1
            error_types.add(type(exc).__name__)
            continue

        out = out_dir / f"{submission_str}.xml"
        if out.exists():
            continue

        ok, error = download(session, url, out)
        if ok:
            saved += 1
        else:
            failed += 1
            error_types.add(type(error).__name__ if error else "Unknown")
        time.sleep(REQUEST_SLEEP)

    suffix = f"  ({', '.join(sorted(error_types))})" if error_types else ""
    print(f"{label}->  {saved:02} SAVED | {failed:02} FAILED{suffix}")
    return saved, failed

def main():
    try:
        if not IN_DIR.exists():
            raise FileNotFoundError()
        files = sorted(IN_DIR.glob("*.json"))
        if not files:
            raise ValueError()
        session = create_session()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(files)
    width = len(str(total))
    print(f"\nDownloading data for {total} symbols ...\n")

    saved = failed = processed = 0
    for index, file in enumerate(files, start=1):
        if index > 1 and (index - 1) % SESSION_REFRESH_INTERVAL == 0:
            try:
                session = create_session()
            except requests.RequestException as error:
                print(f"\nERROR : {type(error).__name__}")
                break
            print("\n--- SESSION REFRESHED ---\n")
        label = f"[{index:0{width}}/{total}]  {file.stem:<12}"
        try:
            s, f = process_symbol(session, file, label)
        except (OSError, ValueError, AttributeError) as error:
            print(f"{label}->  ERROR : {type(error).__name__}")
            processed += 1
            continue
        saved += s
        failed += f
        processed += 1

    print(f"\nSUCCESS : {saved}")
    print(f"FAILED  : {failed}")
    print(f"\nProcessed {processed}/{total} symbols")
    print(f"Saved to : {OUT_DIR_DISPLAY}")

if __name__ == "__main__":
    main()
