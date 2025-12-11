import os
import sys
import requests

URLS_FILE = os.environ.get("URLS_FILE", "monitoring/urls_to_check.txt")

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
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code >= 400:
            return False, f"ERROR HTTP {resp.status_code}"
        return True, f"OK {resp.status_code}"
    except Exception as e:
        return False, f"EXCEPCIÓN: {type(e).__name__}: {e}"

def main():
    urls = load_urls(URLS_FILE)
    if not urls:
        print("No se han encontrado URLs en el fichero. Revisa:", URLS_FILE)
        sys.exit(1)

    print("=== RESULTADO MONITORIZACIÓN WEBS ===")
    failed = []
    for url in urls:
        ok, info = check_url(url)
        line = f"{url} --> {info}"
        print(line)
        if not ok:
            failed.append(line)

    if failed:
        # Guardamos un pequeño resumen en un archivo para adjuntarlo al correo
        with open("monitoring_result.txt", "w", encoding="utf-8") as f:
            f.write("Se han detectado errores en las siguientes URLs:\n\n")
            f.write("\n".join(failed))
            f.write("\n\nResultado completo:\n\n")
            # (podríamos volver a escribir todo, pero con el resumen vale)

        # Salimos con código 1 para que el job cuente como fallo
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
