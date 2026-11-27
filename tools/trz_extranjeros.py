#!/usr/bin/env python3
"""TRZ-EXTRANJEROS (pre-registro docs/research/trz_extranjeros_20261127/PREREGISTRO.md): T, R y Z de la cartera NT8, sin cambios, en
índices extranjeros con M1 de HistData.

  python tools/trz_extranjeros.py bajar      # zips anuales/mensuales de HistData → data/trz_extranjeros/raw/ (sólo hasta 2026-09)
"""
import http.cookiejar, re, sys, time, urllib.parse, urllib.request, zipfile, io, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "data/trz_extranjeros/raw"
INDICES = {"GRXEUR": "DAX", "UKXGBP": "FTSE", "ETXEUR": "EuroStoxx", "FRXEUR": "CAC", "JPXJPY": "Nikkei", "AUXAUD": "ASX200"}
ANIOS = range(2010, 2026)


def _op():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())); op.addheaders = [("User-Agent", "Mozilla/5.0")]
    return op


def _bajar(sym: str, anio: int, mes: int | None) -> bytes | None:
    op = _op(); ruta = f"{sym.lower()}/{anio}" + (f"/{mes}" if mes else "")
    u = f"https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{ruta}"
    h = op.open(u, timeout=60).read().decode("latin1")
    campos = dict(re.findall(r'<input type="hidden" name="(\w+)" id="\w+" value="([^"]*)"', h))
    if "tk" not in campos: return None
    req = urllib.request.Request("https://www.histdata.com/get.php", data=urllib.parse.urlencode(campos).encode(), headers={"Referer": u})
    b = op.open(req, timeout=180).read()
    return b if b[:2] == b"PK" else None


def bajar() -> int:
    RAW.mkdir(parents=True, exist_ok=True); proc = {}
    for sym in INDICES:
        piezas = [(a, None) for a in ANIOS] + [(2026, m) for m in range(1, 10)]
        for anio, mes in piezas:
            f = RAW / f"{sym}_{anio}{'' if mes is None else f'_{mes:02d}'}.zip"
            if not f.exists():
                b = None
                for intento in range(4):
                    try: b = _bajar(sym, anio, mes); break
                    except Exception as e: print("reintento", sym, anio, mes, repr(e)[:80], flush=True); time.sleep(10)
                if b is None: print("sin datos", sym, anio, mes, flush=True); continue
                f.write_bytes(b); time.sleep(2)
            proc[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        print(sym, "listo", flush=True)
    (RAW.parent / "PROCEDENCIA.json").write_text(json.dumps(dict(fuente="histdata.com ASCII M1 (EST fijo, UTC−5)", archivos=proc), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit({"bajar": bajar}[sys.argv[1]]())
