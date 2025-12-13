import os
import sys
import time
import requests

URLS_FILE = os.environ.get("URLS_FILE", "monitoring/urls_to_check.txt")

# segundos entre peticiones para no disparar tanto el WAF
SLEEP_BETWEEN_REQUESTS = float(os.environ.get("SLEEP_BETWEEN_REQUESTS", "1.0"))

def load_urls(path):
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls

def check_url(url, timeout=15):
    headers = {
        "User-Agent": "AgilityDivertidog-Healthcheck/1.0 (+https://agilitydivertidog.com)"
    }
    try:
        resp = requests.get(url, timeout=timeout, headers=headers)
        status = resp.status_code

        # 429 = Too Many Requests → lo tratamos como "warning"
        if status == 429:
            return True, "WARNING 429 Too Many Requests (servidor responde, tratado como OK)"

        # Si el código HTTP es 4xx/5xx (distinto de 429) → error real
        if status >= 400:
            return False, f"ERROR HTTP {status}"

        # --- AQUÍ VIENE LA DETECCIÓN DE "WARNINGS" EN EL HTML ---
        body_snippet = resp.text[:4000]  # miramos solo los primeros 4000 caracteres

        error_patterns = [
            "Warning: include(",
            "Warning: include_once(",
            "Warning: require(",
            "Warning: require_once(",
            "Fatal error",
            "Parse error",
            "Uncaught Exception",
        ]

        for pattern in error_patterns:
            if pattern in body_snippet:
                return False, f"ERROR CONTENIDO HTML: se ha encontrado '{pattern}'"

        # Si todo OK
        return True, f"OK {status}"

    except Exception as e:
        return False, f"EXCEPCIÓN: {type(e).__name__}: {e}"

def main():
    urls = load_urls(URLS_FILE)
    if not urls:
        print("No se han encontrado URLs en el fichero. Revisa:", URLS_FILE)
        sys.exit(1)

    print("=== RESULTADO MONITORIZACIÓN WEBS ===")
    failed = []
    warnings = []

    for url in urls:
        ok, info = check_url(url)
        line = f"{url} --> {info}"
        print(line)

        if "WARNING 429" in info:
            warnings.append(line)
        elif not ok:
            failed.append(line)

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    # generamos un resumen para adjuntar en el correo SI hay errores de verdad
    if failed or warnings:
        with open("monitoring_result.txt", "w", encoding="utf-8") as f:
            if failed:
                f.write("❌ ERRORES CRÍTICOS:\n\n")
                f.write("\n".join(failed))
                f.write("\n\n")
            if warnings:
                f.write("⚠️ ADVERTENCIAS (no rompen el healthcheck):\n\n")
                f.write("\n".join(warnings))
                f.write("\n")

    # solo marcamos fallo si hay errores críticos de verdad (404, 500, timeout, etc.)
    if failed:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
