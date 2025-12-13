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

        # Errores HTTP "serios"
        if status >= 400:
            return False, f"ERROR HTTP {status}"

        # --- DETECCIÓN DE WARNINGS / ERRORES EN EL CONTENIDO HTML ---
        body = resp.text  # analizamos todo el HTML

        error_patterns = [
            "Warning:",            # cualquier Warning de PHP
            "Fatal error",         # errores fatales
            "Parse error",         # errores de parseo
            "Uncaught Exception",  # excepciones no capturadas
            "Uncaught Error",
        ]

        patterns_encontrados = [p for p in error_patterns if p in body]

        if patterns_encontrados:
            return False, "ERROR CONTENIDO HTML: se han encontrado patrones de error: " + ", ".join(patterns_encontrados)

        # Si todo bien
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
