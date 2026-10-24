#!/usr/bin/env python3
"""Recorta un dataset SPOT de Dukascopy en la frontera del holdout (HOLDOUT-A4) y deja la carpeta lista para subirla como
NUEVA VERSIÓN privada. Auditoría 2026-10-24, P-96 P4 (OK de Nico): los seis `edgelab-dukascopy-*` se subieron con corte en la
fecha UTC 2026-09-30 y tienen 120 velas M1 (y sus ticks) de 22:00 a 23:59 UTC, que ya son holdout.

  python tools/recortar_spot_holdout.py --slug nicolasbuttaro/edgelab-dukascopy-nq-usatech --trabajo /data/recorte/usatech
  python tools/recortar_spot_holdout.py ... --subir        # además sube la versión con tools/kaggle_dataset.py

Sólo QUITA filas: todo parquet con `time_utc_ns` se reescribe con las filas < HOLDOUT_APERTURA_UTC_NS y se verifica que lo
conservado sea exactamente el prefijo anterior a la frontera (orden ascendente, conteos, ninguna fila >= frontera).
`calidad.json` pierde lo que describe al holdout (huecos que lo tocan, ticks del 30-sep después de las 22:00) y el README
declara el recorte. `RECORTE_HOLDOUT.json` queda en la carpeta (sube con la versión) con conteos y sha256 de entrada y salida.
La versión 1 de Kaggle sigue en el historial del dataset: borrarla es una decisión aparte (ver el acta)."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.holdout import HOLDOUT_APERTURA_UTC_ISO, HOLDOUT_APERTURA_UTC_NS  # noqa: E402

COL = "time_utc_ns"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def recortar_parquet(origen: Path, destino: Path, frontera: int = HOLDOUT_APERTURA_UTC_NS) -> dict:
    """Reescribe `origen` sin las filas >= frontera, por row group (no carga el archivo entero). Falla si no es ascendente."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(origen); w = None; previo = None; n_in = n_out = n_fuera = 0; ts_max = None
    try:
        for i in range(pf.metadata.num_row_groups):
            t = pf.read_row_group(i); ts = t[COL]; n_in += len(t)
            if len(t) == 0: continue
            if previo is not None and pc.min(ts).as_py() < previo: raise SystemExit(f"{origen.name}: no ascendente entre row groups")
            if len(t) > 1 and not pc.all(pc.greater_equal(ts.slice(1), ts.slice(0, len(t) - 1))).as_py():
                raise SystemExit(f"{origen.name}: no ascendente en el row group {i}")
            previo = pc.max(ts).as_py(); m = pc.less(ts, frontera); k = pc.sum(m).as_py() or 0
            n_fuera += len(t) - k
            if k == 0: continue
            t = t.filter(m) if k < len(t) else t
            if w is None: w = pq.ParquetWriter(destino, pf.schema_arrow, compression="zstd")
            w.write_table(t, row_group_size=len(t)); n_out += k; ts_max = pc.max(t[COL]).as_py()
    finally:
        if w is not None: w.close()
    if n_in != n_out + n_fuera: raise SystemExit(f"{origen.name}: conteo inconsistente")
    if n_out:                                                   # verificación de la salida, leída de nuevo
        v = pq.read_table(destino, columns=[COL])[COL]
        assert len(v) == n_out and pc.max(v).as_py() < frontera, origen.name
    return dict(archivo=origen.name, filas_entrada=n_in, filas_salida=n_out, filas_quitadas=n_fuera, ts_max_salida=ts_max)


def recortar_calidad(c: dict, ticks_30sep: int | None, frontera_ns: int = HOLDOUT_APERTURA_UTC_NS) -> dict:
    """Saca de calidad.json lo que describe al holdout: huecos que lo tocan y el conteo de ticks del 30-sep después de las 22:00."""
    ms = frontera_ns // 1_000_000; c = json.loads(json.dumps(c)); dia = HOLDOUT_APERTURA_UTC_ISO[:10]
    c["huecos_5min"] = [h for h in c.get("huecos_5min", []) if h.get("hasta_ms", 0) < ms]
    if ticks_30sep is not None and dia in c.get("dias", {}):
        c["dias"][dia]["ticks"] = ticks_30sep
    return c


def ticks_del_dia(p: Path, dia_iso: str, frontera: int = HOLDOUT_APERTURA_UTC_NS) -> int:
    import datetime as dt
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    d0 = int(dt.datetime.fromisoformat(dia_iso).replace(tzinfo=dt.timezone.utc).timestamp()) * 1_000_000_000
    ts = pq.read_table(p, columns=[COL], filters=[(COL, ">=", d0), (COL, "<", frontera)])[COL]
    return len(ts)


def bajar(slug: str, dest: Path, version: int | None):
    from kaggle_auth import curl_auth
    owner, name = slug.split("/"); lst = f"https://www.kaggle.com/api/v1/datasets/list/{owner}/{name}"
    files = json.loads(subprocess.check_output(["curl", "-sS", "--fail-with-body"] + curl_auth(lst) + [lst]))["datasetFiles"]
    for f in files:
        u = f"https://www.kaggle.com/api/v1/datasets/download/{owner}/{name}/{f['name']}" + (f"?datasetVersionNumber={version}" if version else "")
        for intento in range(5):                                         # descargas de GB se cortan: se retoma (-C -) hasta el tamaño listado
            subprocess.run(["curl", "-sSL", "--fail", "-C", "-", "-o", str(dest / f["name"])] + curl_auth(u) + [u])
            if (dest / f["name"]).exists() and (dest / f["name"]).stat().st_size == f["totalBytes"]: break
        if (dest / f["name"]).stat().st_size != f["totalBytes"]: raise SystemExit(f"{f['name']}: tamaño distinto al listado")


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--slug", required=True); ap.add_argument("--trabajo", required=True)
    ap.add_argument("--origen", help="carpeta ya bajada (si no, se baja la versión indicada)"); ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--subir", action="store_true"); a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    w = Path(a.trabajo); ori = Path(a.origen) if a.origen else w / "origen"; out = w / "recortado"
    ori.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    if not a.origen: bajar(a.slug, ori, a.version)
    reg = dict(slug=a.slug, version_origen=a.version, frontera_utc=HOLDOUT_APERTURA_UTC_ISO + "Z", frontera_ns=HOLDOUT_APERTURA_UTC_NS,
               motivo="HOLDOUT-A4: el corte por fecha UTC dejaba 22:00-23:59 UTC del 2026-09-30 (P-96 P4, auditoría 2026-10-24)", archivos=[])
    tick_file = None
    for p in sorted(ori.iterdir()):
        if p.suffix == ".parquet":
            r = recortar_parquet(p, out / p.name); r["sha256_entrada"] = sha256(p); r["sha256_salida"] = sha256(out / p.name)
            reg["archivos"].append(r); print(json.dumps(r), flush=True)
            if p.stem.endswith("_ticks"): tick_file = out / p.name
    for p in sorted(ori.iterdir()):
        if p.name == "calidad.json":
            n = ticks_del_dia(tick_file, HOLDOUT_APERTURA_UTC_ISO[:10]) if tick_file else None
            c = recortar_calidad(json.loads(p.read_text(encoding="utf-8")), n)
            c["recorte_holdout_A4"] = {"frontera_utc": reg["frontera_utc"], "quitadas": {r["archivo"]: r["filas_quitadas"] for r in reg["archivos"]}}
            (out / p.name).write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        elif p.name == "README.md":
            (out / p.name).write_text(p.read_text(encoding="utf-8").rstrip() + f"\n\nRECORTE 2026-10-24 (HOLDOUT-A4): sin filas desde {reg['frontera_utc']}"
                                      " (apertura de la sesión CME del 2026-10-01). La versión 1 cortaba por fecha UTC y traía 22:00-23:59 del 30-sep."
                                      " Detalle: RECORTE_HOLDOUT.json.\n", encoding="utf-8")
        elif p.suffix != ".parquet":
            raise SystemExit(f"archivo no previsto: {p.name}")
    if any(r["filas_quitadas"] == 0 for r in reg["archivos"]): print("aviso: algún parquet no tenía filas del holdout", flush=True)
    (out / "RECORTE_HOLDOUT.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.subir:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "kaggle_dataset.py"), "version", "--slug", a.slug, "--dir", str(out),
                        "--notes", f"Recorte HOLDOUT-A4: sin filas desde {reg['frontera_utc']} (P-96 P4)"], check=True)
    return reg


if __name__ == "__main__":
    main()
