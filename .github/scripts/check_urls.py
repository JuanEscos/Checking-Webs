import os
import sys
import time
import requests

URLS_FILE = os.environ.get("URLS_FILE", "monitoring/urls_to_check.txt")
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

        # 429 = Too Many Requests → warning, no error crítico
        if status == 429:
            return True, "WARNING 429 Too Many Requests (servidor responde, tratado como OK)"

        if status >= 400:
            return False, f"ERROR HTTP {status}"

        body = resp.text

        patterns = [
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
    urls = load_urls(URLS_FILE)
    if not urls:
        print("No se han encontrado URLs en", URLS_FILE)
        sys.exit(1)

    failed = []
    warnings = []

    print("=== RESULTADO MONITORIZACIÓN WEBS ===")

    for url in urls:
        ok, info = check_url(url)
        line = f"{url} --> {info}"
        print(line)

        if "WARNING" in info:
            warnings.append(line)
        elif not ok:
            failed.append(line)

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    with open("monitoring_result.txt", "w", encoding="utf-8") as f:
        if failed:
            f.write("❌ ERRORES CRÍTICOS:\n")
            f.write("\n".join(failed))
            f.write("\n\n")
        if warnings:
            f.write("⚠️ ADVERTENCIAS:\n")
            f.write("\n".join(warnings))
            f.write("\n")

    if failed:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
