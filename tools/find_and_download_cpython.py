# -*- coding: utf-8 -*-
import urllib.request
import json
import time
from pathlib import Path

def main():
    target_dir = Path("E:/DatosNT8/subir_a_notion_menor_200mb")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    url = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    print(f"Buscando release en {url}...")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        
    tag = data.get("tag_name")
    print(f"Tag encontrado: {tag}")
    
    matched_asset = None
    for a in data.get("assets", []):
        name = a.get("name", "")
        # Prefer install_only tar.gz for x86_64 linux gnu
        if "cpython-3.12" in name and "x86_64-unknown-linux-gnu-install_only" in name and name.endswith(".tar.gz"):
            matched_asset = a
            break
            
    if not matched_asset:
        # Fallback to any 3.12 install_only
        for a in data.get("assets", []):
            name = a.get("name", "")
            if "cpython-3.12" in name and "x86_64" in name and "install_only" in name:
                matched_asset = a
                break
                
    if not matched_asset:
        print("No se encontró asset exacto. Listando assets disponibles de Python 3.12:")
        for a in data.get("assets", []):
            name = a.get("name", "")
            if "3.12" in name and "x86_64" in name:
                print("  -", name)
        return
        
    name = matched_asset["name"]
    download_url = matched_asset["browser_download_url"]
    size_mb = matched_asset["size"] / (1024 * 1024)
    print(f"\nDescargando {name} ({size_mb:.2f} MB)...")
    print(f"URL: {download_url}")
    
    dest_path = target_dir / name
    t0 = time.time()
    
    req_dl = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_dl) as src, open(dest_path, "wb") as dst:
        total_dl = 0
        while chunk := src.read(8 * 1024 * 1024):
            dst.write(chunk)
            total_dl += len(chunk)
            print(f"  Descargados {total_dl / (1024*1024):.1f} MB...", end="\r", flush=True)
            
    print(f"\n[+] Descarga completada en {time.time() - t0:.1f}s.")
    print(f"Archivo guardado en: {dest_path}")
    print(f"Tamaño final: {dest_path.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
