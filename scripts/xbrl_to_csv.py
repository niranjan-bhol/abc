import csv
import shutil
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "nse" / "sh_xbrl"
OUT_DIR = ROOT / "data" / "nse" / "sh_csv"
OUT_DIR_DISPLAY = f"{ROOT.name}/{OUT_DIR.relative_to(ROOT)}"

CATEGORY_AXIS = "CategoryOfShareholdersAxis"
OTHER_NON_INST_AXIS = "OtherNonInstitutions"
OTHER_NON_INST_LABEL_FACT = "CategoryOfOtherNonInstitutions"

FACT_TO_COLUMN = {
    "NumberOfShareholders": "number_of_shareholders",
    "NumberOfShares": "number_of_shares",
    "ShareholdingAsAPercentageOfTotalNumberOfShares": "shareholding_pct",
}
NUMERIC_COLUMNS = tuple(FACT_TO_COLUMN.values())
COLUMNS = ["category", *NUMERIC_COLUMNS]

# Template of the public shareholding table, in order.
# Labels are the XBRL names. Several aliases cover spelling/schema differences
# between filing years; the first alias is the name used when a filing has no
# such row (the row is then left blank).
# Section = (items, other_rows, subtotal_aliases)
SECTIONS = [
    (  # Institutions (Domestic)
        [
            ("MutualFundsOrUTI", "MutualFundsOrUti"),
            ("VentureCapitalFunds",),
            ("AlternativeInvestmentFunds",),
            ("Banks", "FinancialInstitutionOrBanks"),
            ("InsuranceCompanies",),
            ("ProvidentFundsOrPensionFunds",),
            ("AssetReconstructionCompanies",),
            ("SovereignWealthFundsDomestic",),
            ("NBFCsRegisteredWithRBI", "NBFCsRegisteredWithRbi"),
            ("OtherFinancialInstitutions",),
            ("OtherInstitutionsDomestic", "OtherInstitutions"),
        ],
        [],
        ("InstitutionsDomestic",),
    ),
    (  # Institutions (Foreign)
        [
            ("ForeignDirectInvestment",),
            ("ForeignVentureCapitalInvestors",),
            ("SovereignWealthFundsForeign",),
            (
                "InstitutionsForeignPortfolioInvestorCategoryOne",
                "InstitutionsForeignPortfolioInvestorCatergoryOne",
                "InstitutionsForeignPortfolioInvestor",
            ),
            (
                "InstitutionsForeignPortfolioInvestorCategoryTwo",
                "InstitutionsForeignPortfolioInvestorCatergoryTwo",
            ),
            ("OverseasDepositories",),
            ("OtherInstitutionsForeign",),
        ],
        [],
        ("InstitutionsForeign",),
    ),
    (  # Central Government / State Government(s)
        [
            ("CentralGovernmentOrPresidentOfIndia", "CentralGovernmentOrStateGovernmentSOrPresidentOfIndia"),
            ("StateGovernmentsOrGovernors",),
            (
                "ShareholdingByCompaniesOrBodiesCorporateWhereCentralOrStateGovernmentIsPromoter",
                "ShareholdingByCompaniesOrBodiesCorporatewhereCentralOrStateGovernmentIsPromoter",
            ),
        ],
        [],
        ("Governments", "Goverments"),
    ),
    (  # Non-institutions
        [
            ("AssociateCompaniesOrSubsidiaries",),
            ("DirectorsAndDirectorsRelatives",),
            ("KeyManagerialPersonnel",),
            ("RelativesOfPromotersOtherThanPromoterGroup",),
            (
                "TrustsWhereAnyPersonBelongingToPromoterAndPromoterGroupIsTrusteeOrBeneficiaryOrAuthorOfTrust",
                "TrustsWhereAnyPersonBelongingToPromoterAndPromoterGroupIsisTrusteeOrBeneficiaryOrAuthorOfTrust",
            ),
            ("InvestorEducationAndProtectionFund",),
            (
                "ResidentIndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakh",
                "IndividualShareholdersHoldingNominalShareCapitalUpToRsTwoLakh",
            ),
            (
                "ResidentIndividualShareholdersHoldingNominalShareCapitalInExcessOfRsTwoLakh",
                "IndividualShareholdersHoldingNominalShareCapitalInExcessOfRsTwoLakh",
            ),
            ("NonResidentIndians",),
            ("ForeignNationals",),
            ("ForeignCompanies",),
            ("BodiesCorporate",),
            ("OtherNonInstitutions",),
        ],
        # Breakdown rows under OtherNonInstitutions: aliases are the labels used in XBRL
        [
            ("Clearing Members", "Clearing Member"),
            ("HUF",),
            ("LLP",),
            ("Trusts",),
        ],
        ("NonInstitutions",),
    ),
]
TOTAL_ALIASES = ("PublicShareholding",)

def local(tag):
    return tag.rsplit("}", 1)[-1]

def parse_contexts(root):
    contexts = {}
    for ctx in root.iter():
        if local(ctx.tag) != "context":
            continue
        members = [el for el in ctx.iter() if local(el.tag) in ("explicitMember", "typedMember")]
        if len(members) != 1:
            continue
        member = members[0]
        axis = member.get("dimension").split(":")[-1]
        if local(member.tag) == "explicitMember":
            if axis == CATEGORY_AXIS:
                name = (member.text or "").strip().split(":")[-1].removesuffix("Member")
                contexts[ctx.get("id")] = ("category", name.lower(), name)
        elif OTHER_NON_INST_AXIS in axis:
            child = next(iter(member), None)
            if child is not None:
                contexts[ctx.get("id")] = ("detail", (child.text or "").strip(), "")
    return contexts

def sum_values(rows):
    """Sum the numeric columns of several rows; {} if none has data."""
    total = {}
    for row in rows:
        for col in NUMERIC_COLUMNS:
            try:
                value = Decimal(row.get(col, ""))
            except InvalidOperation:
                continue
            total[col] = total.get(col, Decimal(0)) + value
    return {col: str(value) for col, value in total.items()}

def find(entries, aliases):
    """First entry matching one of the aliases (case-insensitive), else None."""
    for alias in aliases:
        if alias.lower() in entries:
            return entries[alias.lower()]
    return None

def make_row(entry, aliases):
    """Row labelled with the XBRL name found in the file, or the canonical name if absent."""
    if entry is None:
        return {"category": aliases[0]}
    return {"category": entry["name"], **{c: entry[c] for c in NUMERIC_COLUMNS if c in entry}}

def build_rows(facts, details):
    rows = []
    subtotals = []
    for items, others, subtotal_aliases in SECTIONS:
        item_entries = []
        for aliases in items:
            entry = find(facts, aliases)
            item_entries.append(entry or {})
            rows.append(make_row(entry, aliases))
        for aliases in others:
            rows.append(make_row(find(details, aliases), aliases))
        # Older schemas have no sub-total fact; fall back to summing the items.
        entry = find(facts, subtotal_aliases)
        if entry is None:
            summed = sum_values(item_entries)
            entry = {"name": subtotal_aliases[0], **summed} if summed else None
        subtotals.append(entry or {})
        rows.append(make_row(entry, subtotal_aliases))

    entry = find(facts, TOTAL_ALIASES)
    if entry is None:
        summed = sum_values(subtotals)
        entry = {"name": TOTAL_ALIASES[0], **summed} if summed else None
    rows.append(make_row(entry, TOTAL_ALIASES))
    return rows

def to_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None

def is_fraction_scale(facts):
    """True if the file stores shareholding % as a fraction of 1 (e.g. 0.6734) instead of 67.34.

    The grand-total row (ShareholdingPattern) is 100% in a percentage-style file
    and 1 in a fraction-style file, so it decides the scale.
    """
    total = to_decimal(facts.get("shareholdingpattern", {}).get("shareholding_pct"))
    if total is not None:
        return total <= 1
    values = [to_decimal(f.get("shareholding_pct")) for f in facts.values()]
    values = [v for v in values if v is not None]
    return bool(values) and max(values) <= 1

def scale_pct(row):
    value = to_decimal(row.get("shareholding_pct"))
    if value is not None:
        row["shareholding_pct"] = format((value * 100).normalize(), "f")

def extract_public_rows(xml_path):
    root = ET.parse(xml_path).getroot()
    contexts = parse_contexts(root)

    facts = {}
    typed = {}
    for el in root.iter():
        ref = el.get("contextRef")
        if ref not in contexts:
            continue
        kind, key, name = contexts[ref]
        fact = local(el.tag)
        value = (el.text or "").strip()
        column = FACT_TO_COLUMN.get(fact)
        if kind == "category":
            if column:
                facts.setdefault(key, {"name": name})[column] = value
        elif column:
            typed.setdefault(key, {})[column] = value
        elif fact == OTHER_NON_INST_LABEL_FACT:
            typed.setdefault(key, {})["label"] = value

    if not facts:
        raise ValueError("no public shareholding data")

    if is_fraction_scale(facts):
        for row in [*facts.values(), *typed.values()]:
            scale_pct(row)

    by_label = {}
    for row in typed.values():
        if row.get("label"):
            by_label.setdefault(row["label"].lower(), []).append(row)
    details = {
        key: {"name": rows[0]["label"], **sum_values(rows)} for key, rows in by_label.items()
    }

    return build_rows(facts, details)

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

def process_symbol(folder, label):
    out_dir = OUT_DIR / folder.name
    saved = failed = 0
    for xml_path in sorted(folder.glob("*.xml")):
        try:
            rows = extract_public_rows(xml_path)
            if not rows:
                raise ValueError("no public shareholding data")
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / f"{xml_path.stem}.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            saved += 1
        except (ET.ParseError, OSError, ValueError):
            failed += 1
    print(f"{label}->  {saved:02} SAVED | {failed:02} FAILED")
    return saved, failed

def main():
    if not IN_DIR.exists():
        print("ERROR : XBRL directory not found")
        return

    folders = sorted(p for p in IN_DIR.iterdir() if p.is_dir())
    if not folders:
        print("ERROR : No symbol folders found")
        return

    total = len(folders)
    width = len(str(total))

    prepare_output_dir()
    print(f"\nConverting data for {total} symbols\n")

    saved = failed = 0
    for index, folder in enumerate(folders, start=1):
        label = f"[{index:0{width}}/{total}]  {folder.name:<12}"
        s, f = process_symbol(folder, label)
        saved += s
        failed += f

    print(f"\nSUCCESS : {saved}")
    print(f"FAILED  : {failed}")

if __name__ == "__main__":
    main()
