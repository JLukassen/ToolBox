from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


REQUIRED_OUTPUT_COLUMNS = [
    "Email",
    "FirstName",
    "SurName",
    "Department",
    "Country",
    "Language",
    "Phone",
    "Office",
    "Group",
]


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def clean_text(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() == "nan" else text


def split_name(display_name: str) -> tuple[str, str]:
    parts = [p for p in clean_text(display_name).split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def derive_group(office: str, department: str, email: str) -> str:
    office_clean = clean_text(office)
    department_clean = clean_text(department)
    domain = email.split("@", 1)[1] if "@" in email else ""

    if office_clean and department_clean:
        return f"{office_clean}-{department_clean}"
    if office_clean:
        return office_clean
    if department_clean:
        return department_clean
    return domain


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def load_and_map_input(input_file: Path) -> pd.DataFrame:
    df = pd.read_csv(input_file, dtype=str).fillna("")

    email_col = find_column(df, [
        "Email", "PrimarySmtpAddress", "mail", "userPrincipalName", "email address"
    ])
    first_col = find_column(df, ["FirstName", "GivenName", "givenName"])
    last_col = find_column(df, ["SurName", "Surname", "LastName", "sn"])
    display_col = find_column(df, ["DisplayName", "displayName", "Name"])
    department_col = find_column(df, ["Department", "department"])
    country_col = find_column(df, ["Country", "country", "CountryOrRegion"])
    language_col = find_column(df, ["Language", "PreferredLanguage", "preferredLanguage"])
    phone_col = find_column(df, ["Phone", "MobilePhone", "telephoneNumber", "mobilePhone"])
    office_col = find_column(df, ["Office", "physicalDeliveryOfficeName", "OfficeLocation", "officeLocation"])
    group_col = find_column(df, ["Group", "group"])

    if not email_col:
        raise ValueError("Could not find an email column in the input file.")

    out = pd.DataFrame()
    out["Email"] = df[email_col].apply(normalize_email)

    if first_col:
        out["FirstName"] = df[first_col].apply(clean_text)
    else:
        out["FirstName"] = ""

    if last_col:
        out["SurName"] = df[last_col].apply(clean_text)
    else:
        out["SurName"] = ""

    if display_col:
        display_series = df[display_col].apply(clean_text)
    else:
        display_series = pd.Series([""] * len(df))

    for idx in out.index:
        if not out.at[idx, "FirstName"] or not out.at[idx, "SurName"]:
            derived_first, derived_last = split_name(display_series.iloc[idx])
            if not out.at[idx, "FirstName"]:
                out.at[idx, "FirstName"] = derived_first
            if not out.at[idx, "SurName"]:
                out.at[idx, "SurName"] = derived_last

    out["Department"] = df[department_col].apply(clean_text) if department_col else ""
    out["Country"] = df[country_col].apply(clean_text) if country_col else ""
    out["Language"] = df[language_col].apply(clean_text) if language_col else ""
    out["Phone"] = df[phone_col].apply(clean_text) if phone_col else ""
    out["Office"] = df[office_col].apply(clean_text) if office_col else ""

    if group_col:
        out["Group"] = df[group_col].apply(clean_text)
    else:
        out["Group"] = ""

    return out


def finalize_for_titanhq(
    df: pd.DataFrame,
    default_country: str,
    default_language: str,
    drop_blank_names: bool = False,
) -> pd.DataFrame:
    work = df.copy()

    work["Email"] = work["Email"].apply(normalize_email)
    work = work[work["Email"] != ""].copy()

    work["Country"] = work["Country"].replace("", default_country)
    work["Language"] = work["Language"].replace("", default_language)

    for idx in work.index:
        if not clean_text(work.at[idx, "Group"]):
            work.at[idx, "Group"] = derive_group(
                office=work.at[idx, "Office"],
                department=work.at[idx, "Department"],
                email=work.at[idx, "Email"],
            )

    if drop_blank_names:
        work = work[(work["FirstName"] != "") & (work["SurName"] != "")].copy()

    work = work.drop_duplicates(subset=["Email"]).sort_values("Email")
    work = work[REQUIRED_OUTPUT_COLUMNS]

    return work


def main() -> None:
    parser = argparse.ArgumentParser(description="Format a CSV into TitanHQ bulk user import format.")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", default="titanhq_bulk_users.csv", help="Path to output CSV")
    parser.add_argument("--default-country", default="US", help="Default country if missing")
    parser.add_argument("--default-language", default="en", help="Default language if missing")
    parser.add_argument(
        "--drop-blank-names",
        action="store_true",
        help="Drop rows where first and surname cannot be determined",
    )

    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output)

    mapped = load_and_map_input(input_file)
    final_df = finalize_for_titanhq(
        mapped,
        default_country=args.default_country,
        default_language=args.default_language,
        drop_blank_names=args.drop_blank_names,
    )

    final_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(final_df)} rows to {output_file}")


if __name__ == "__main__":
    main()