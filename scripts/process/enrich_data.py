import csv
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

NSE_DIR = BASE_DIR / "data" / "nse" / "historical" / "csv_transformed"
UPSTOX_DIR = BASE_DIR / "data" / "upstox" / "historical" / "csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "enriched"

OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}/"

COLUMNS = [
    "series", 
    "date", "open", "high", "low", "close",
    "nse_upstox_ratio",
    "vwap", "traded_quantity", "traded_value",
    "delivery_percent", "delivered_quantity", "delivered_value",
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

def read_nse(nse_file):
    with open(nse_file, "r", encoding="utf-8", newline="") as f:
        return {row["date"]: row for row in csv.DictReader(f)}

def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def fmt(value, digits):
    return "" if value is None else f"{value:.{digits}f}"

def enrich_row(upstox_row, nse_row):
    volume = to_float(upstox_row["volume"])
    nse_row = nse_row or {}
    nse_qty = to_float(nse_row.get("total_traded_qty"))
    nse_vwap = to_float(nse_row.get("vwap"))
    series = nse_row.get("series", "")
    delivery_percent = 100.0 if series in ("BE", "BZ") else to_float(nse_row.get("delivery_pct"))

    ratio = nse_qty / volume if nse_qty is not None and volume else None
    if ratio is None:
        nse_close = to_float(nse_row.get("close"))
        upstox_close = to_float(upstox_row["close"])
        if nse_close and upstox_close is not None:
            ratio = upstox_close / nse_close
    vwap = nse_vwap * ratio if nse_vwap is not None and ratio is not None else None
    traded_quantity = volume
    traded_value = volume * vwap if volume is not None and vwap is not None else None
    delivered_quantity = (
        traded_quantity * (delivery_percent / 100)
        if traded_quantity is not None and delivery_percent is not None
        else None
    )
    delivered_value = (
        delivered_quantity * vwap
        if delivered_quantity is not None and vwap is not None
        else None
    )

    return [
        nse_row["series"],
        upstox_row["date"],
        upstox_row["open"],
        upstox_row["high"],
        upstox_row["low"],
        upstox_row["close"],
        fmt(ratio, 2),
        fmt(vwap, 2),
        fmt(traded_quantity, 0),
        fmt(traded_value, 2),
        fmt(delivery_percent, 2),
        fmt(delivered_quantity, 0),
        fmt(delivered_value, 2),
    ]

def enrich_file(upstox_file):
    nse_rows = read_nse(NSE_DIR / upstox_file.name)

    rows = []
    blanks = 0
    with open(upstox_file, "r", encoding="utf-8", newline="") as f:
        for upstox_row in csv.DictReader(f):
            row = enrich_row(upstox_row, nse_rows.get(upstox_row["date"]))
            if "" in row:
                blanks += 1
            rows.append(row)

    if not rows:
        raise ValueError()

    output_file = OUTPUT_DIR / upstox_file.name
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    return len(rows), blanks

def enrich_data():
    nse_names = {f.name for f in NSE_DIR.glob("*.csv")}
    common_files = sorted(f for f in UPSTOX_DIR.glob("*.csv") if f.name in nse_names)

    if not common_files:
        raise ValueError()

    prepare_output_dir()

    success_count = 0
    total = len(common_files)
    print(f"\nEnriching {total} common files ...\n")
    width = len(str(total))
    name_width = max(len(f.stem) for f in common_files)

    for idx, upstox_file in enumerate(common_files, 1):
        print(f"[{idx:0{width}d}/{total}]  {upstox_file.stem:<{name_width}}  ->  ", end="", flush=True)
        try:
            row_count, blanks = enrich_file(upstox_file)
            suffix = f"  (blank {blanks} rows)" if blanks else ""
            print(f"{row_count:>4} rows{suffix}")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nEnriched {success_count}/{total} symbols")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        enrich_data()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
