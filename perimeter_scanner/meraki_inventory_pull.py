from pathlib import Path
import csv
import os
import sys
import time
import requests

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "inputs"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = INPUT_DIR / "store_assets.csv"
API_BASE = "https://api.meraki.com/api/v1"


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def meraki_get(path: str, api_key: str, params: dict | None = None) -> list[dict]:
    """
    Handles Meraki pagination via RFC5988 Link headers.
    """
    headers = {
        "X-Cisco-Meraki-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    url = f"{API_BASE}{path}"
    results: list[dict] = []

    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        params = None  # only send params on the first request

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            time.sleep(retry_after)
            continue

        resp.raise_for_status()

        data = resp.json()
        if isinstance(data, list):
            results.extend(data)
        else:
            # Some endpoints return an object; normalize as a single-item list.
            results.append(data)

        next_link = None
        link_header = resp.headers.get("Link", "")
        if link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    next_link = part.split(";")[0].strip().strip("<>").strip()
                    break

        url = next_link

    return results


def normalize_store_name(name: str) -> str:
    return str(name or "").strip()


def derive_store_id(name: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in normalize_store_name(name).upper() if ch.isalnum())
    return cleaned[:12] if cleaned else fallback


def build_rows(uplinks: list[dict], device_statuses: list[dict]) -> list[dict]:
    """
    Expected appliance uplink statuses payload includes keys such as:
    - serial
    - name
    - model
    - networkId
    - lastReportedAt
    - uplinks: [...]
    Official API docs describe organization-wide appliance uplink status listing. :contentReference[oaicite:1]{index=1}
    """
    status_by_serial = {
        str(row.get("serial", "")).strip(): row
        for row in device_statuses
    }

    rows: list[dict] = []

    for item in uplinks:
        serial = str(item.get("serial", "")).strip()
        device_name = normalize_store_name(item.get("name", ""))
        model = str(item.get("model", "")).strip()
        network_id = str(item.get("networkId", "")).strip()
        status = status_by_serial.get(serial, {})

        # Try to find the first public IP-like uplink.
        public_ip = ""
        uplink_list = item.get("uplinks", []) or []
        for uplink in uplink_list:
            candidate = str(
                uplink.get("publicIp")
                or uplink.get("ip")
                or ""
            ).strip()
            if candidate:
                public_ip = candidate
                break

        store_name = device_name or serial or "UNKNOWN"
        store_id = derive_store_id(store_name, serial[:12] or "UNKNOWN")

        # Meraki MX/Z appliances commonly expose VPN-related services; public management
        # behavior varies by config. Keeping expected ports conservative is reasonable. :contentReference[oaicite:2]{index=2}
        rows.append({
            "store_id": store_id,
            "store_name": store_name,
            "city": "",
            "state": "",
            "asset_name": device_name or "Main Firewall",
            "asset_type": "Firewall",
            "wan_ip": public_ip,
            "hostname": "",
            "firewall_vendor": "Meraki",
            "expected_public_services": "443;500;4500",
            "scan_profile": "standard",
            "approval_status": "approved",
            "scan_enabled": "yes" if public_ip else "no",
            "notes": f"serial={serial}; model={model}; networkId={network_id}; device_status={status.get('status', '')}",
        })

    # Deduplicate by serial-derived notes / WAN IP / store name combination
    seen = set()
    deduped: list[dict] = []
    for row in rows:
        key = (row["store_name"], row["wan_ip"], row["notes"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    return deduped


def write_store_assets(rows: list[dict], output_file: Path) -> None:
    fieldnames = [
        "store_id",
        "store_name",
        "city",
        "state",
        "asset_name",
        "asset_type",
        "wan_ip",
        "hostname",
        "firewall_vendor",
        "expected_public_services",
        "scan_profile",
        "approval_status",
        "scan_enabled",
        "notes",
    ]

    with output_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    api_key = get_env("MERAKI_API_KEY")
    organization_id = get_env("MERAKI_ORG_ID")

    print("Pulling Meraki appliance uplink statuses...")
    uplinks = meraki_get(
        f"/organizations/{organization_id}/appliance/uplink/statuses",
        api_key,
        params={"perPage": 1000},
    )

    print("Pulling Meraki device statuses...")
    device_statuses = meraki_get(
        f"/organizations/{organization_id}/devices/statuses",
        api_key,
        params={"perPage": 1000},
    )

    rows = build_rows(uplinks, device_statuses)

    # Keep only rows with at least a device name or WAN IP
    rows = [r for r in rows if r["store_name"] or r["wan_ip"]]

    write_store_assets(rows, OUTPUT_FILE)

    print(f"Wrote {len(rows)} rows to: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise