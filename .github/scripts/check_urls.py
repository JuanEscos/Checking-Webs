import os
import sys
import time
import requests
from bs4 import BeautifulSoup

URLS_FILE = os.environ.get("URLS_FILE", "monitoring/urls_to_check.txt")
SLEEP_BETWEEN_REQUESTS = float(os.environ.get("SLEEP_BETWEEN_REQUESTS", "1.0"))

LOGIN_URL = "https://agilitydivertidog.com/NewWeb/login.php"
USERNAME = os.environ.get("MONITOR_USER")
PASSWORD = os.environ.get("MONITOR_PASS")

def load_urls(path):
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def login(session):
    """Realiza login en tu panel privado."""
    payload = {
        "email": USERNAME,
        "password": PASSWORD
    }

    resp = session.post(LOGIN_URL, data=payload, timeout=15)

    if "Incorrecto" in resp.text or "error" in resp.text.lower():
        return False, "Credenciales incorrectas o login fallido"
    if resp.status_code != 200:
        return False, f"Error HTTP tras login: {resp.status_code}"

    return True, "Login OK"


def check_url(session, url):
    """Comprueba una URL ya autenticado."""
    try:
        resp = session.get(url, timeout=15)
        status = resp.status_code

        if status == 429:
            return True, "WARNING 429 Too Many Requests"

        if status >= 400:
            return False, f"ERROR HTTP {status}"

        body = resp.text

        # Detectar errores PHP en contenido
        patterns = [
            "Warning:",
            "Fatal error",
            "Parse error",
            "Uncaught Exception",
            "Uncaught Error",
        ]

        found = [p for p in patterns if p in body]

        if found:
            return False, f"ERROR CONTENIDO HTML: {', '.join(found)}"

        return True, f"OK {status}"

    except Exception as e:
        return False, f"EXCEPCIÓN: {type(e).__name__}: {e}"


def main():
    if not USERNAME or not PASSWORD:
        print("Faltan credenciales MONITOR_USER / MONITOR_PASS")
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "AgilityDivertidog-Healthcheck/1.0 (+https://agilitydivertidog.com)"
    })

    # LOGIN
    ok, info = login(session)
    print("LOGIN:", info)
    if not ok:
        sys.exit(1)

    urls = load_urls(URLS_FILE)

    failed = []
    warnings = []

    for url in urls:
        ok, info = check_url(session, url)
        print(url, "-->", info)

        if "WARNING" in info:
            warnings.append(f"{url} --> {info}")
        elif not ok:
            failed.append(f"{url} --> {info}")

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    # Escribir resumen
    with open("monitoring_result.txt", "w", encoding="utf-8") as f:
        if failed:
            f.write("❌ ERRORES CRÍTICOS:\n" + "\n".join(failed) + "\n\n")
        if warnings:
            f.write("⚠️ ADVERTENCIAS:\n" + "\n".join(warnings) + "\n")

    # Solo fallar si hay errores críticos
    if failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
