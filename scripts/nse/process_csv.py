import csv
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

IN_DIR = BASE_DIR / "data" / "nse" / "csv"
OUT_DIR = BASE_DIR / "data" / "nse" / "processed"
OUT_DIR_DISPLAY = f"{BASE_DIR.name}/{OUT_DIR.relative_to(BASE_DIR)}"

START_YEAR, START_MONTH = 2021, 1

METRIC = "shareholding_pct"

CATEGORIES = [
    "MutualFundsOrUTI",
    "VentureCapitalFunds",
    "AlternativeInvestmentFunds",
    "Banks",
    "InsuranceCompanies",
    "ProvidentFundsOrPensionFunds",
    "AssetReconstructionCompanies",
    "SovereignWealthFundsDomestic",
    "NBFCsRegisteredWithRBI",
    "OtherFinancialInstitutions",
    "OtherInstitutionsDomestic",
    "InstitutionsDomestic",
    "ForeignDirectInvestment",
    "ForeignVentureCapitalInvestors",
    "SovereignWealthFundsForeign",
    "InstitutionsForeignPortfolioInvestorCategoryOne",
    "InstitutionsForeignPortfolioInvestorCategoryTwo",
    "OverseasDepositories",
    "OtherInstitutionsForeign",
    "InstitutionsForeign",
    "CentralGovernmentOrPresidentOfIndia",
    "StateGovernmentsOrGovernors",
    "ShareholdingByCompaniesOrBodiesCorporateWhereCentralOrStateGovernmentIsPromoter",
    "Governments",
    "AssociateCompaniesOrSubsidiaries",
    "DirectorsAndDirectorsRelatives",
    "KeyManagerialPersonnel",
    "RelativesOfPromotersOtherThanPromoterGroup",
    "TrustsWhereAnyPersonBelongingToPromoterAndPromoterGroupIsTrusteeOrBeneficiaryOrAuthorOfTrust",
    "InvestorEducationAndProtectionFund",
    "ResidentIndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakh",
    "ResidentIndividualShareholdersHoldingNominalShareCapitalInExcessOfRsTwoLakh",
    "NonResidentIndians",
    "ForeignNationals",
    "ForeignCompanies",
    "BodiesCorporate",
    "OtherNonInstitutions",
    "Clearing Members",
    "HUF",
    "LLP",
    "Trusts",
    "NonInstitutions",
    "PublicShareholding",
]

COLUMNS = ["Symbol", "SubmissionDate", *CATEGORIES]

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

def read_filing(path):
    data = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            category = (row.get("category") or "").strip()
            if category:
                data[category] = (row.get(METRIC) or "").strip()
    if not data:
        raise ValueError()
    return data

def load_filings(folders):
    filings = {}
    for folder in folders:
        items = []
        for path in sorted(folder.glob("*.csv")):
            try:
                filing_date = datetime.strptime(path.stem, "%Y%m%d").date()
                data = read_filing(path)
            except (OSError, ValueError, csv.Error) as exc:
                print(f"WARN : {type(exc).__name__}")
                continue
            items.append((filing_date, data))
        if items:
            items.sort(key=lambda item: item[0])
            filings[folder.name] = items
    return filings

def month_range(last_year, last_month):
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (last_year, last_month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

def month_end_key(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)

def main():
    try:
        if not IN_DIR.exists():
            raise FileNotFoundError()
        folders = sorted(p for p in IN_DIR.iterdir() if p.is_dir())
        if not folders:
            raise ValueError()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(folders)
    width = len(str(total)) + 2
    print(f"\nProcessing {total} symbols ...\n")

    try:
        filings = load_filings(folders)
        if not filings:
            raise ValueError()
    except ValueError as error:
        print(f"ERROR : {type(error).__name__}")
        return

    last_date = max(items[-1][0] for items in filings.values())
    pointers = {symbol: -1 for symbol in filings}

    for year, month in month_range(last_date.year, last_date.month):
        limit = datetime(*month_end_key(year, month), 1).date()
        rows = []
        for symbol, items in filings.items():
            idx = pointers[symbol]
            while idx + 1 < len(items) and items[idx + 1][0] < limit:
                idx += 1
            pointers[symbol] = idx
            if idx < 0:
                continue
            filing_date, data = items[idx]
            rows.append([symbol, filing_date.isoformat(), *(data.get(c, "") for c in CATEGORIES)])

        name = f"{year}_{month:02}.csv"
        try:
            with (OUT_DIR / name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)
                writer.writerows(rows)
        except OSError as exc:
            print(f"ERROR : {type(exc).__name__}")
            continue

        label = datetime(year, month, 1).strftime("%b %Y").upper()
        print(f"{label:<10}->{len(rows):>{width}} symbols")

    print(f"\nDownloaded data for {len(filings)}/{total} symbols")
    print(f"Saved to : {OUT_DIR_DISPLAY}")

if __name__ == "__main__":
    main()
