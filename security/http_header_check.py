from urllib.parse import urlparse
import requests

def check_headers(url: str) -> dict:
    result = {
        "url": url,
        "status_code": "",
        "server": "",
        "title": "",
        "x_frame_options": "",
        "content_security_policy": "",
        "strict_transport_security": "",
        "error": "",
    }

    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["server"] = resp.headers.get("Server", "")
        result["x_frame_options"] = resp.headers.get("X-Frame-Options", "")
        result["content_security_policy"] = resp.headers.get("Content-Security-Policy", "")
        result["strict_transport_security"] = resp.headers.get("Strict-Transport-Security", "")

        text = resp.text or ""
        title_start = text.lower().find("<title>")
        title_end = text.lower().find("</title>")
        if title_start != -1 and title_end != -1:
            result["title"] = text[title_start + 7:title_end].strip()

    except Exception as e:
        result["error"] = str(e)

    return result