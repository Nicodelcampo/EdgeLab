#!/usr/bin/env python3
"""Graba cada día la planilla pública «Arbitraje Ratios» de Martín Masella (Google Sheets), que guarda SÓLO la rueda en curso.

La hoja «Intraday» trae GD30/AL30 en 24hs cada 10 segundos (10:30 → 17:00), con el último precio y los dos ratios operables con
puntas: «GD>AL» = bid GD30 / ask AL30 − 1 (rotar de GD a AL) y «AL>GD» = ask GD30 / bid AL30 − 1 (volver). «D-C» trae lo mismo para
AL30D/AL30C, y «MD» una foto de puntas con cantidades de AL29, AL30, GD29 y GD30 (pesos, MEP y cable; CI y 24hs). Los precios en vivo
de la planilla salen de la API de Primary vía Veta; los diarios, de IOL. Al día siguiente la hoja se reescribe: si no se graba
entre las 17:05 y las 10:30 del día hábil siguiente, esa rueda se pierde.

  python tools/bonos_masella_grabar.py grabar      # baja y guarda la rueda que muestra la planilla (no pisa una ya grabada)
  python tools/bonos_masella_grabar.py resumen     # ruedas grabadas, filas y cobertura

Destino: data/bonos_ar/intradia_masella/<AAAA-MM-DD>/ (gitignorado): los CSV crudos, parquets limpios y PROCEDENCIA.json con sha256.
Los datos son de un tercero: no se publican ni se suben a GitHub (a un dataset privado de Kaggle, sólo si Nico lo decide). Sólo usa la biblioteca estándar y pandas (sin openpyxl).
Se buscó antes con `tools/existente.py buscar` («descargar planilla google sheets grabar intradía bonos»): no hay un grabador de
planillas ni de intradía de bonos; `bonos_ratios.py` y `bonos_rotacion.py` leen sólo diarios de data912.
"""
import hashlib, io, json, sys, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/bonos_ar/intradia_masella"
SHEET_ID = "1W2kTK4n10-fKWYRJmoffOnxdaibkL-7I5wduSHVlGvI"
HOJAS = {"intraday": "Intraday", "dc": "D-C", "md": "MD", "ratio": "Ratio GD30AL30"}
BA = ZoneInfo("America/Argentina/Buenos_Aires")


def _bajar(hoja: str) -> bytes:
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=" + urllib.parse.quote(hoja))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _fecha_rueda(raw_ratio: bytes, ahora: datetime) -> str:
    """La primera fila de datos de «Ratio GD30AL30» es la rueda en curso, como «dd/mm»; el año se toma de la fecha local."""
    df = pd.read_csv(io.BytesIO(raw_ratio), header=None, dtype=str)
    dm = df.iloc[1, 1]
    d, m = (int(x) for x in dm.split("/"))
    y = ahora.year - (1 if m > ahora.month else 0)
    return f"{y:04d}-{m:02d}-{d:02d}"


def _bloque_10s(raw: bytes, cols: list[str]) -> pd.DataFrame:
    """Bloque izquierdo (columnas A–F): hora y precios cada 10 s, de la última a la primera; se devuelve en orden ascendente."""
    df = pd.read_csv(io.BytesIO(raw), dtype=str).iloc[:, :6]
    df.columns = cols
    df = df[df["hora"].fillna("").str.match(r"^\d{1,2}:\d{2}:\d{2}$")].copy()
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce")
    return df.iloc[::-1].reset_index(drop=True)


def _md(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), dtype=str).iloc[:, 1:8]
    df.columns = ["ticker", "bidsize", "bid", "last", "ask", "asksize", "stamp"]
    df = df[df["ticker"].notna() & df["stamp"].notna()].copy()
    for c in ["bidsize", "bid", "last", "ask", "asksize"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.reset_index(drop=True)


def grabar() -> int:
    ahora = datetime.now(BA)
    raw = {k: _bajar(v) for k, v in HOJAS.items()}
    fecha = _fecha_rueda(raw["ratio"], ahora)
    out = DEST / fecha
    if (out / "PROCEDENCIA.json").exists():
        print(f"{fecha}: ya grabada en {out}; no se pisa.")
        return 0
    intr = _bloque_10s(raw["intraday"], ["hora", "GD30", "AL30", "ratio_pct", "GD_a_AL_pct", "AL_a_GD_pct"])
    dc = _bloque_10s(raw["dc"], ["hora", "AL30D", "AL30C", "ratio_pct", "D_a_C_pct", "C_a_D_pct"])
    md = _md(raw["md"])
    if len(intr) < 100:
        print(f"{fecha}: la hoja Intraday tiene {len(intr)} filas; parece vacía o a medio cargar. No se graba.")
        return 1
    if ahora.date().isoformat() == fecha and ahora.hour < 17:
        print(f"{fecha}: la rueda todavía no terminó ({ahora:%H:%M} en Buenos Aires). Correr después de las 17:05.")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    proc = {"fuente": f"https://docs.google.com/spreadsheets/d/{SHEET_ID} (Martín Masella, «Arbitraje Ratios»; precios vía Primary/Veta)",
            "bajado_en": ahora.isoformat(timespec="seconds"), "rueda": fecha, "archivos": {}}
    for k, b in raw.items():
        (out / f"crudo_{k}.csv").write_bytes(b)
        proc["archivos"][f"crudo_{k}.csv"] = hashlib.sha256(b).hexdigest()
    for nom, df in [("intraday_gd30_al30.parquet", intr), ("intraday_al30d_al30c.parquet", dc), ("md_puntas.parquet", md)]:
        df.insert(0, "fecha", fecha)
        df.to_parquet(out / nom, index=False)
        proc["archivos"][nom] = {"filas": len(df)}
    proc["cobertura"] = {"desde": intr.hora.iloc[0], "hasta": intr.hora.iloc[-1], "filas_10s": len(intr)}
    (out / "PROCEDENCIA.json").write_text(json.dumps(proc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(proc["cobertura"] | {"rueda": fecha, "destino": str(out)}, ensure_ascii=False))
    return 0


def resumen() -> int:
    filas = []
    for p in sorted(DEST.glob("*/PROCEDENCIA.json")):
        j = json.loads(p.read_text(encoding="utf-8"))
        filas.append({"rueda": j["rueda"], **j.get("cobertura", {}), "bajado_en": j["bajado_en"]})
    print(pd.DataFrame(filas).to_string(index=False) if filas else "Sin ruedas grabadas.")
    return 0


if __name__ == "__main__":
    sys.exit({"grabar": grabar, "resumen": resumen}[sys.argv[1] if len(sys.argv) > 1 else "grabar"]())
