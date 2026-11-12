import csv
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TOP_N = 30

IN_DIR = BASE_DIR / "data" / "backtest" / "new"
OUT_DIR = BASE_DIR / "data" / "backtest" / f"top{TOP_N}"
OUT_DIR_DISPLAY = f"{BASE_DIR.name}/{OUT_DIR.relative_to(BASE_DIR)}"

SKIP_COLUMNS = {"Symbol", "SubmissionDate"}
HEADER = ["symbol", "submission_date", "change"]


def read_month(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = [c for c in (reader.fieldnames or []) if c not in SKIP_COLUMNS]
        rows = list(reader)
    return columns, rows


def top_rows(rows, column):
    ranked = []
    for row in rows:
        try:
            change = float(row[column])
        except (TypeError, ValueError):
            continue
        ranked.append((row["Symbol"], row["SubmissionDate"], change))
    # highest change first, symbol as a stable tie-breaker
    ranked.sort(key=lambda item: (-item[2], item[0]))
    return ranked[:TOP_N]


def prepare_output_dir():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
        print(f"Cleared output directory : {OUT_DIR_DISPLAY}")
    OUT_DIR.mkdir(parents=True)


def main():
    files = sorted(IN_DIR.glob("*.csv")) if IN_DIR.exists() else []
    if not files:
        print(f"ERROR : no input files in {IN_DIR}")
        return
    prepare_output_dir()

    for path in files:
        try:
            columns, rows = read_month(path)
            for column in columns:
                column_dir = OUT_DIR / column
                column_dir.mkdir(exist_ok=True)
                with (column_dir / path.name).open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADER)
                    writer.writerows(top_rows(rows, column))
        except (OSError, KeyError, csv.Error) as exc:
            print(f"ERROR : {path.name} : {type(exc).__name__} : {exc}")
            continue
        print(f"{path.name} -> {len(columns)} categories")

    print(f"\nSaved to : {OUT_DIR_DISPLAY}")


if __name__ == "__main__":
    main()
