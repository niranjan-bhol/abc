import re
import csv
import math
import shutil
from calendar import month_abbr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INPUT_DIR = BASE_DIR / "data" / "launch" / "change"
OUTPUT_DIR = BASE_DIR / "data" / "launch" / "portfolio"

INPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{INPUT_DIR.relative_to(BASE_DIR)}"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

TOP_N = 15

KEY_COLUMN = "Symbol"
DATE_COLUMN = "SubmissionDate"
CATEGORIES = ("InstitutionsDomestic", "InstitutionsForeign")
HEADER = ["symbol", "submission_date", "change", "source"]

FILE_PATTERN = re.compile(r"^(\d{4})_(0[1-9]|1[0-2])\.csv$")
PORTFOLIO_INPUT_MONTHS = {1, 4, 7, 10}
FIRST_INPUT_NAME = "2021_10.csv"

def to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None

def add_months(year, month, months):
    year, month_index = divmod(year * 12 + month - 1 + months, 12)
    return year, month_index + 1

def portfolio_window(path):
    year, month = map(int, FILE_PATTERN.match(path.name).groups())
    start = add_months(year, month, 1)
    end = add_months(*start, 2)
    return start, end

def list_input_files():
    files = []
    for path in INPUT_DIR.glob("*.csv"):
        match = FILE_PATTERN.match(path.name)
        if (
            match
            and int(match.group(2)) in PORTFOLIO_INPUT_MONTHS
            and path.name >= FIRST_INPUT_NAME
        ):
            files.append(path)
    return sorted(files)

def portfolio_window_label(path):
    (start_year, start_month), (end_year, end_month) = portfolio_window(path)
    return (
        f"{month_abbr[start_month].upper()} {start_year} to "
        f"{month_abbr[end_month].upper()} {end_year}"
    )

def portfolio_window_name(path):
    (start_year, start_month), (end_year, end_month) = portfolio_window(path)
    return (
        f"{start_year}_{start_month:02}_to_"
        f"{end_year}_{end_month:02}.csv"
    )

def read_month(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        missing = [c for c in (KEY_COLUMN, DATE_COLUMN, *CATEGORIES) if c not in columns]
        if missing:
            raise ValueError()
        rows = list(reader)
    if not rows:
        raise ValueError()
    return rows

def rank_rows(rows, column):
    best = {}
    for row in rows:
        change = to_float(row.get(column))
        symbol = (row.get(KEY_COLUMN) or "").strip()
        if change is None or change <= 0 or not symbol:
            continue
        if symbol not in best or change > best[symbol]["change"]:
            best[symbol] = {
                "symbol": symbol,
                "submission_date": row.get(DATE_COLUMN) or "",
                "change": change,
            }
    return sorted(best.values(), key=lambda item: (-item["change"], item["symbol"]))

def add_replacement(selected, ranked, source, selected_symbols):
    for item in ranked[TOP_N:]:
        if item["symbol"] in selected_symbols:
            continue
        selected.append({**item, "source": source})
        selected_symbols.add(item["symbol"])
        return True
    return False

def select_top_rows(rows):
    ranked = {category: rank_rows(rows, category) for category in CATEGORIES}
    domestic = ranked["InstitutionsDomestic"][:TOP_N]
    foreign = ranked["InstitutionsForeign"][:TOP_N]
    domestic_by_symbol = {item["symbol"]: item for item in domestic}
    foreign_by_symbol = {item["symbol"]: item for item in foreign}
    overlap = domestic_by_symbol.keys() & foreign_by_symbol.keys()

    selected = []
    for item in foreign:
        symbol = item["symbol"]
        if symbol in overlap:
            domestic_item = domestic_by_symbol[symbol]
            selected.append({
                **item,
                "change": max(item["change"], domestic_item["change"]),
                "source": "Both",
            })
        else:
            selected.append({**item, "source": "InstitutionsForeign"})

    for item in domestic:
        if item["symbol"] not in overlap:
            selected.append({**item, "source": "InstitutionsDomestic"})

    selected_symbols = {item["symbol"] for item in selected}
    available = {item["symbol"] for items in ranked.values() for item in items}
    target = min(TOP_N * 2, len(available))
    replacement_order = ("InstitutionsForeign", "InstitutionsDomestic")
    replacement_index = 0
    while len(selected) < target:
        source = replacement_order[replacement_index % len(replacement_order)]
        if not add_replacement(
            selected,
            ranked[source],
            source,
            selected_symbols,
        ):
            other_source = replacement_order[
                (replacement_index + 1) % len(replacement_order)
            ]
            if not add_replacement(
                selected,
                ranked[other_source],
                other_source,
                selected_symbols,
            ):
                break
        replacement_index += 1

    selected.sort(key=lambda item: (-item["change"], item["symbol"]))
    return [
        (
            item["symbol"],
            item["submission_date"],
            item["change"],
            item["source"],
        )
        for item in selected
    ]

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"\nOutput directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUTPUT_PATH_DISPLAY}")

def save_portfolio(path):
    rows = read_month(path)
    selected = select_top_rows(rows)
    output_path = OUTPUT_DIR / portfolio_window_name(path)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(selected)

def select_stock():
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError()

    files = list_input_files()
    if not files:
        raise ValueError()

    prepare_output_dir()

    success_count = 0
    total = len(files)
    print(f"\nSelecting top stocks for {total} quarterly portfolios ...\n")

    for path in files:
        print(f"{portfolio_window_label(path)}  ->  ", end="", flush=True)
        try:
            save_portfolio(path)
            print("SUCCESS")
            success_count += 1
        except Exception as e:
            print(f"ERROR : {type(e).__name__}")

    print(f"\nPortfolio construction completed successfully for {success_count}/{total} quarters")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

def main():
    try:
        select_stock()
    except Exception as e:
        print(f"ERROR : {type(e).__name__}")

if __name__ == "__main__":
    main()
