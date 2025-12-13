import os
import sys
import time
import requests

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
    if not USERNAME or not PASSWORD:
        return False, "Faltan MONITOR_USER / MONITOR_PASS en los secrets"

    payload = {
        "email": USERNAME,     # <-- campos típicos de tu login
        "password": PASSWORD,
    }

    try:
        resp = session.post(LOGIN_URL, data=payload, timeout=15)

        # Comprobaciones básicas de login
        if resp.status_code != 200:
            return False, f"Error HTTP tras login: {resp.status_code}"

        text_lower = resp.text.lower()
        # Ajusta estas cadenas si tu login muestra otros mensajes de error
        if "incorrecto" in text_lower or "error" in text_lower:
            return False, "Credenciales incorrectas o login fallido"

        # Si no vemos mensajes de error obvios, asumimos que el login ha ido bien
        return True, "Login OK"

    except Exception as e:
        return False, f"EXCEPCIÓN en login: {type(e).__name__}: {e}"


def check_url(session, url):
    """Comprueba una URL ya autenticado."""
    try:
        resp = session.get(url, timeout=15)
        status = resp.status_code

        # 429 = Too Many Requests → lo tratamos como "warning"
        if status == 429:
            return True, "WARNING 429 Too Many Requests"

        if status >= 400:
            return False, f"ERROR HTTP {status}"

        body = resp.text

        # Detectar errores PHP en el contenido
        patterns = [
            "Warning:",
            "Fatal error",
            "Parse error",
            "Uncaught Exception",
            "Uncaught Error",
        ]

        found = [p for p in patterns if p in body]

        if found:
            return False, "ERROR CONTENIDO HTML: " + ", ".join(found)

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

    # --- LOGIN ---
    ok, info = login(session)
    print("LOGIN:", info)
    if not ok:
        # Si el login falla, dejamos monitoring_result.txt con el motivo
        with open("monitoring_result.txt", "w", encoding="utf-8") as f:
            f.write("❌ ERROR EN LOGIN:\n")
            f.write(info + "\n")
        sys.exit(1)

    urls = load_urls(URLS_FILE)
    if not urls:
        print("No se han encontrado URLs en", URLS_FILE)
        sys.exit(1)

    failed = []
    warnings = []

    print("=== RESULTADO MONITORIZACIÓN WEBS ===")

    for url in urls:
        ok, info = check_url(session, url)
        line = f"{url} --> {info}"
        print(line)

        if "WARNING" in info:
            warnings.append(line)
        elif not ok:
            failed.append(line)

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    # Escribir resumen
    with open("monitoring_result.txt", "w", encoding="utf-8") as f:
        if failed:
            f.write("❌ ERRORES CRÍTICOS:\n")
            f.write("\n".join(failed))
            f.write("\n\n")
        if warnings:
            f.write("⚠️ ADVERTENCIAS:\n")
            f.write("\n".join(warnings))
            f.write("\n")

    # Solo fallar si hay errores críticos
    if failed:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
