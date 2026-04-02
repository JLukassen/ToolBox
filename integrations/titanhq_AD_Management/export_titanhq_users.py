from pathlib import Path
import os
import sys
import requests
import pandas as pd
from msal import ConfidentialClientApplication
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TENANT_ID = os.getenv("TENANT_ID", "").strip()
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "").strip()

if not TENANT_ID or not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing Graph API credentials in .env file")

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DOMAINS = [
    "olshanfoundation.com",
    "brownfoundationrepair.com",
    "olshanservices.com",
    "cablelock.com",
]

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]


def get_token() -> str:
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" not in result:
        raise RuntimeError(f"Failed to get token: {result}")

    return result["access_token"]


def graph_get_all(url: str, headers: dict) -> list[dict]:
    items = []
    next_url = url

    while next_url:
        resp = requests.get(next_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")

    return items


def fetch_users(token: str) -> pd.DataFrame:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    url = (
        f"{GRAPH_BASE}/users"
        f"?$select=displayName,mail,userPrincipalName,proxyAddresses,accountEnabled"
        f"&$top=999"
    )

    users = graph_get_all(url, headers)
    df = pd.DataFrame(users)

    for col in ["displayName", "mail", "userPrincipalName", "proxyAddresses", "accountEnabled"]:
        if col not in df.columns:
            df[col] = ""

    return df


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def extract_proxy_addresses(value) -> list[str]:
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = []

    emails = []
    for item in raw_values:
        text = str(item or "").strip()
        if not text:
            continue

        # Exchange-style values often look like:
        # SMTP:primary@domain.com
        # smtp:alias@domain.com
        if ":" in text:
            prefix, addr = text.split(":", 1)
            if prefix.lower() == "smtp":
                addr = normalize_email(addr)
                if addr:
                    emails.append(addr)
        else:
            addr = normalize_email(text)
            if addr:
                emails.append(addr)

    return emails


def collect_identity_rows(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, record in df.iterrows():
        display_name = str(record.get("displayName", "") or "").strip()
        account_enabled = record.get("accountEnabled", "")

        candidates = set()

        mail = normalize_email(record.get("mail", ""))
        upn = normalize_email(record.get("userPrincipalName", ""))
        proxy_addresses = extract_proxy_addresses(record.get("proxyAddresses", []))

        if mail:
            candidates.add(mail)
        if upn:
            candidates.add(upn)

        for addr in proxy_addresses:
            candidates.add(addr)

        for email in sorted(candidates):
            rows.append({
                "email": email,
                "display_name": display_name,
                "account_enabled": account_enabled,
            })

    out = pd.DataFrame(rows)

    if out.empty:
        return pd.DataFrame(columns=["email", "display_name", "account_enabled"])

    out["email"] = out["email"].astype(str).str.strip().str.lower()
    out["display_name"] = out["display_name"].astype(str).str.strip()

    out = out[out["email"] != ""].copy()
    out = out.drop_duplicates(subset=["email"]).sort_values("email")

    return out


def build_domain_export(identity_df: pd.DataFrame, domain: str) -> pd.DataFrame:
    work = identity_df.copy()

    work = work[work["email"].str.endswith(f"@{domain}", na=False)].copy()

    out = pd.DataFrame({
        "email": work["email"].astype(str).str.strip(),
        "display_name": work["display_name"].astype(str).str.strip(),
        "domain": domain,
    })

    out = out[out["email"] != ""].copy()
    out = out.drop_duplicates(subset=["email"]).sort_values("email")

    return out


def main():
    token = get_token()
    users_df = fetch_users(token)

    print(f"Total user objects pulled from Graph: {len(users_df)}")

    identity_df = collect_identity_rows(users_df)
    print(f"Total email identities collected: {len(identity_df)}")

    all_outputs = []

    for domain in DOMAINS:
        out = build_domain_export(identity_df, domain)
        out_file = OUTPUT_DIR / f"{domain.replace('.', '_')}_antispoof.csv"
        out.to_csv(out_file, index=False)
        print(f"Wrote {len(out)} rows to {out_file}")
        all_outputs.append(out)

    combined = (
        pd.concat(all_outputs, ignore_index=True)
        if all_outputs
        else pd.DataFrame(columns=["email", "display_name", "domain"])
    )

    review_file = OUTPUT_DIR / "titanhq_antispoof_review.xlsx"
    combined.to_excel(review_file, index=False)
    print(f"Wrote combined review workbook: {review_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise