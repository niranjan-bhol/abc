import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "nse" / "sh_processed" / "number_of_shareholders"
OUT_DIR = ROOT / "data" / "portfolio" / "number_of_shareholders"

N = 30
SYMBOL_COL = "Symbol"


def to_number(raw):
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def process_file(path):
    month = path.stem.replace("_", "-")  # 2021_01 -> 2021-01
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = [c for c in reader.fieldnames if c != SYMBOL_COL]
        rows = list(reader)

    for col in columns:
        values = []
        for row in rows:
            raw = (row.get(col) or "").strip()
            num = to_number(raw)
            if num is not None:
                values.append((row[SYMBOL_COL], raw, num))
        values.sort(key=lambda v: (-v[2], v[0]))

        col_dir = OUT_DIR / col
        col_dir.mkdir(parents=True, exist_ok=True)
        with (col_dir / f"{month}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["symbol", "value"])
            for symbol, raw, _ in values[:N]:
                writer.writerow([symbol, raw])
    return len(columns)


def main():
    files = sorted(IN_DIR.glob("*.csv"))
    for path in files:
        n_cols = process_file(path)
        print(f"{path.name}: {n_cols} columns")
    print(f"Done. {len(files)} files -> {Path(ROOT.name) / OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
