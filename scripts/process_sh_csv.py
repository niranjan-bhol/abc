import csv
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "nse" / "sh_csv"
OUT_DIR = ROOT / "data" / "nse" / "sh_processed"
OUT_DIR_DISPLAY = f"{ROOT.name}/{OUT_DIR.relative_to(ROOT)}"

START_YEAR, START_MONTH = 2021, 1

METRICS = ["number_of_shareholders", "number_of_shares", "shareholding_pct"]

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

COLUMNS = ["Symbol", *CATEGORIES]

def prepare_output_dir():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for metric in METRICS:
        (OUT_DIR / metric).mkdir(parents=True, exist_ok=True)

def read_filing(path):
    data = {metric: {} for metric in METRICS}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            category = (row.get("category") or "").strip()
            for metric in METRICS:
                data[metric][category] = (row.get(metric) or "").strip()
    return data

def load_filings():
    filings = {}
    for folder in sorted(p for p in IN_DIR.iterdir() if p.is_dir()):
        items = []
        for path in folder.glob("*.csv"):
            try:
                items.append((datetime.strptime(path.stem, "%Y%m%d").date(), path))
            except ValueError:
                print(f"WARN : skipping {path.relative_to(ROOT)} (bad file name)")
        if items:
            filings[folder.name] = sorted(items)
    return filings

def month_range(last_year, last_month):
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (last_year, last_month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)

def month_end_key(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)

def main():
    if not IN_DIR.exists():
        print("ERROR : Input directory not found")
        return

    filings = load_filings()
    if not filings:
        print("ERROR : No input files found")
        return

    last_date = max(items[-1][0] for items in filings.values())
    cache = {}

    def get(path):
        if path not in cache:
            cache[path] = read_filing(path)
        return cache[path]

    prepare_output_dir()
    print(f"\nProcessing {len(filings)} symbols\n")

    for year, month in month_range(last_date.year, last_date.month):
        limit = datetime(*month_end_key(year, month), 1).date()
        rows = {metric: [] for metric in METRICS}
        for symbol, items in filings.items():
            latest = next((p for d, p in reversed(items) if d < limit), None)
            if latest is None:
                continue
            data = get(latest)
            for metric in METRICS:
                values = data[metric]
                rows[metric].append([symbol, *(values.get(c, "") for c in CATEGORIES)])

        name = f"{year}_{month:02}.csv"
        for metric in METRICS:
            with (OUT_DIR / metric / name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)
                writer.writerows(rows[metric])
        print(f"{name} -> {len(rows[METRICS[0]])} symbols")

    print(f"\nSUCCESS : output written to {OUT_DIR_DISPLAY}")

if __name__ == "__main__":
    main()
