from __future__ import annotations

import argparse
import csv
import ssl
import socket
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Iterable


@dataclass
class TLSReviewResult:
    target: str
    port: int
    tls_present: bool
    status: str
    common_name: str
    issuer: str
    not_before: str
    not_after: str
    days_remaining: str
    error: str


def parse_cert_name(name_tuples) -> str:
    try:
        parts = []
        for rdn in name_tuples:
            for key, value in rdn:
                parts.append(f"{key}={value}")
        return ", ".join(parts)
    except Exception:
        return ""


def classify_days_remaining(days_remaining: int) -> str:
    if days_remaining < 0:
        return "Expired"
    if days_remaining <= 14:
        return "Critical"
    if days_remaining <= 30:
        return "Warning"
    return "OK"


def review_tls(target: str, port: int = 443, timeout: int = 5) -> TLSReviewResult:
    try:
        context = ssl.create_default_context()

        with socket.create_connection((target, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=target) as tls_sock:
                cert = tls_sock.getpeercert()

        subject = cert.get("subject", ())
        issuer = cert.get("issuer", ())
        not_before = cert.get("notBefore", "")
        not_after = cert.get("notAfter", "")

        common_name = ""
        for rdn in subject:
            for key, value in rdn:
                if key == "commonName":
                    common_name = value
                    break
            if common_name:
                break

        days_remaining = ""
        status = "OK"

        if not_after:
            expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
            days = (expiry_dt - datetime.now(UTC)).days
            days_remaining = str(days)
            status = classify_days_remaining(days)

        return TLSReviewResult(
            target=target,
            port=port,
            tls_present=True,
            status=status,
            common_name=common_name,
            issuer=parse_cert_name(issuer),
            not_before=not_before,
            not_after=not_after,
            days_remaining=days_remaining,
            error="",
        )

    except Exception as exc:
        return TLSReviewResult(
            target=target,
            port=port,
            tls_present=False,
            status="No TLS / Error",
            common_name="",
            issuer="",
            not_before="",
            not_after="",
            days_remaining="",
            error=str(exc),
        )


def read_targets_from_csv(path: Path) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            target = str(row.get("target", "")).strip()
            port_text = str(row.get("port", "443")).strip()
            if not target:
                continue
            port = int(port_text) if port_text.isdigit() else 443
            targets.append((target, port))

    return targets


def write_results_csv(results: Iterable[TLSReviewResult], output_file: Path) -> None:
    rows = [asdict(r) for r in results]
    if not rows:
        return

    with output_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review TLS certificates for one or more targets.")
    parser.add_argument("--target", help="Single hostname or IP to review")
    parser.add_argument("--port", type=int, default=443, help="Port to review for a single target")
    parser.add_argument("--input", help="CSV with columns: target,port")
    parser.add_argument("--output", default="tls_review_results.csv", help="Output CSV path")

    args = parser.parse_args()

    targets: list[tuple[str, int]] = []

    if args.target:
        targets.append((args.target.strip(), args.port))

    if args.input:
        targets.extend(read_targets_from_csv(Path(args.input)))

    if not targets:
        raise SystemExit("Provide --target or --input")

    results = [review_tls(target, port) for target, port in targets]
    output_file = Path(args.output)
    write_results_csv(results, output_file)

    print(f"Wrote {len(results)} results to {output_file}")
    for result in results:
        print(
            f"{result.target}:{result.port} | "
            f"{result.status} | "
            f"TLS={result.tls_present} | "
            f"CN={result.common_name} | "
            f"Days Remaining={result.days_remaining or 'N/A'}"
        )


if __name__ == "__main__":
    main()