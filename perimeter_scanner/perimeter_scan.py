from pathlib import Path
import csv
import json
import socket
import ssl
from datetime import datetime, UTC

INPUT_FILE = Path("inputs/store_assets.csv")
RAW_DIR = Path("outputs/raw")
REPORT_DIR = Path("outputs/reports")

RAW_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

COMMON_PORTS = [80, 443, 500, 4500, 8443]


def check_port(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def resolve_hostname(hostname):
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return ""


def get_tls_info(host, port=443):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                expiry = cert.get("notAfter", "")
                subject = cert.get("subject", "")
                return {
                    "tls_present": True,
                    "tls_expiry": expiry,
                    "tls_subject": str(subject),
                }
    except Exception as e:
        return {
            "tls_present": False,
            "tls_expiry": "",
            "tls_subject": "",
            "tls_error": str(e),
        }


def classify_result(result):
    if not any(result.get(f"port_{p}", False) for p in COMMON_PORTS):
        return "Host Unreachable"

    if result.get("port_443") and not result.get("tls_present"):
        return "TLS Review"

    return "Expected Exposure"


def scan_asset(asset):
    target = asset["hostname"] or asset["wan_ip"]

    result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "store_id": asset["store_id"],
        "store_name": asset["store_name"],
        "target": target,
        "hostname": asset["hostname"],
        "wan_ip": asset["wan_ip"],
        "firewall_vendor": asset["firewall_vendor"],
        "expected_public_services": asset["expected_public_services"],
    }

    if asset["hostname"]:
        result["resolved_ip"] = resolve_hostname(asset["hostname"])
    else:
        result["resolved_ip"] = ""

    for port in COMMON_PORTS:
        result[f"port_{port}"] = check_port(target, port)

    tls_info = {"tls_present": False, "tls_expiry": "", "tls_subject": ""}
    if result.get("port_443"):
        tls_info = get_tls_info(target, 443)
    elif result.get("port_8443"):
        tls_info = get_tls_info(target, 8443)

    result.update(tls_info)
    result["classification"] = classify_result(result)

    return result


def main():
    with open(INPUT_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assets = [row for row in reader if row["approval_status"].strip().lower() == "approved"]

    results = []
    for asset in assets:
        result = scan_asset(asset)
        results.append(result)

        raw_path = RAW_DIR / f'{asset["store_id"]}_{asset["store_name"].replace(" ", "_")}.json'
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    if results:
        import pandas as pd
        df = pd.DataFrame(results)
        df.to_csv(REPORT_DIR / "perimeter_summary.csv", index=False)
        df.to_excel(REPORT_DIR / "perimeter_summary.xlsx", index=False)

    print("Perimeter scan complete.")


if __name__ == "__main__":
    main()