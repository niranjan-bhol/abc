import json
import time
import shutil
from datetime import datetime
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "nse" / "sh_master"
OUT_DIR = ROOT / "data" / "nse" / "sh_xbrl"
OUT_DIR_DISPLAY = f"{ROOT.name}/{OUT_DIR.relative_to(ROOT)}"

RETRIES = 3
REQUEST_SLEEP = 0.3
SESSION_REFRESH_INTERVAL = 10

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
        print(f"Output directory exists : {OUT_DIR_DISPLAY}")
        print("Cleared output directory")
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory : {OUT_DIR_DISPLAY}")

def create_session():
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

def download(session, url, out):
    for attempt in range(RETRIES):
        try:
            resp = session.get(url, timeout=60)
            resp.raise_for_status()
            out.write_bytes(resp.content)
            return True
        except (requests.RequestException, OSError):
            time.sleep(2**attempt)
    return False

def process_symbol(session, file, label):
    out_dir = OUT_DIR / file.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = failed = 0

    for row in json.loads(file.read_text()):
        url, date = row.get("xbrl"), row.get("date")
        submission = row.get("submissionDate")
        if not url or not date or not submission:
            continue
        date_str = datetime.strptime(date, "%d-%b-%Y").strftime("%Y%m%d")
        submission_str = datetime.strptime(submission, "%d-%b-%Y").strftime("%Y%m%d")
        out = out_dir / f"{date_str}_{submission_str}.xml"
        if out.exists():
            continue
        if download(session, url, out):
            saved += 1
        else:
            failed += 1
        time.sleep(REQUEST_SLEEP)

    print(f"{label}->  {saved:02} SAVED | {failed:02} FAILED")
    return saved, failed

def main():
    if not IN_DIR.exists():
        print("ERROR : Master directory not found")
        return

    files = sorted(IN_DIR.glob("*.json"))
    if not files:
        print("ERROR : No master files found")
        return

    total = len(files)
    width = len(str(total))

    prepare_output_dir()
    print(f"\nDownloading data for {total} symbols\n")

    session = create_session()
    if session is None:
        print("ERROR : Unable to create NSE session")
        return

    saved = failed = 0
    for index, file in enumerate(files, start=1):
        if index > 1 and (index - 1) % SESSION_REFRESH_INTERVAL == 0:
            session = create_session()
            if session is None:
                print("\nERROR : Unable to refresh NSE session")
                break
            print("\n--- SESSION REFRESHED ---\n")
        label = f"[{index:0{width}}/{total}]  {file.stem:<12}"
        try:
            s, f = process_symbol(session, file, label)
        except (OSError, ValueError, AttributeError):
            print(f"{label}->  ERROR")
            continue
        saved += s
        failed += f

    print(f"\nSUCCESS : {saved}")
    print(f"FAILED  : {failed}")

if __name__ == "__main__":
    main()
