import requests

COMMON_PATHS = [
    "/admin",
    "/login",
    "/dashboard",
    "/manage",
    "/administrator",
]

def check_admin_paths(base_url: str) -> list[dict]:
    findings = []

    for path in COMMON_PATHS:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(url, timeout=8, allow_redirects=True)
            findings.append({
                "url": url,
                "status_code": resp.status_code,
                "final_url": resp.url,
            })
        except Exception as e:
            findings.append({
                "url": url,
                "status_code": "",
                "final_url": "",
                "error": str(e),
            })

    return findings