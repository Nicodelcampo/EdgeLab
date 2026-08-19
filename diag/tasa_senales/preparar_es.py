"""Deja ES en las mismas condiciones que 6E, y extrae el oráculo de HFTZonesESPureV2.

QUÉ TIENE 6E Y ES NO TENÍA
==========================
6E vive en `censo_hz2a_superficie.py` como **serie formal**: 4 contratos encadenados
con su `sha256` canónico verificado y su firewall aplicado. ES no tenía nada de eso.

Este script produce el equivalente para ES:

  - `sha256` de cada parquet, **declarado** (no hay canon previo contra el cual
    verificar; decir «canónico» sin canon sería la etiqueta escrita en vez de computada)
  - **cobertura temporal real de cada contrato**, para armar la cadena sin solapes
  - inventario de sesiones (`trade_date_ymd`) y ticks por contrato, **antes** del
    firewall
  - el **oráculo** de `HFTZonesESPureV2` extraído de su SQLite, recortado al firewall

EL TECHO DE MEMORIA ERA AUTOINFLIGIDO
=====================================
`P-25` dice que `load_canonical_parquet` «lee el archivo completo antes de recortar por
`--dias`». **Eso es falso y lo escribí sin leer la función.** Su firma es

    load_canonical_parquet(path, contract=None, start_utc_ns=None, end_utc_ns=None, ...)

y empuja el filtro a `pyarrow.read_table(filters=…)`, o sea a nivel de row-group. Lo que
leía el archivo entero eran **mis llamadas**, que nunca pasaban la ventana.

Medido sobre `ES_06-26` (73.268.494 filas): una sesión sale en **1,38 M ticks (66 MB)
en 1,1 s**, 53 veces menos. Por eso ES —cuyos archivos individuales pasan los 2 GB en el
modelo de 48 B/tick— es perfectamente trabajable.

EL ORÁCULO
==========
`HFTZonesESPureV2` no escribe CSV: escribe SQLite en `C:\\LoggerHFT\\data\\`. El
contrato de paridad del proyecto usa CSV, así que se convierte **sin tocar el `.cs`** —
modificar el indicador cambiaría el objeto que se quiere validar.

Target-free: geometría y procedencia. Sin outcomes, sin P&L. Holdout excluido.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys

import numpy as np
import pyarrow.parquet as pq

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.kaggle.sessions_cme import session_bounds_utc_ns, trade_date_ymd  # noqa: E402

SCHEMA_VERSION = "preparar_es_v1"
HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]
SQLITE_ORACULO = pathlib.Path(r"C:\LoggerHFT\data\hft_logger.sqlite")

# Columnas de `hft_zones` que definen la GEOMETRIA de la zona. El resto son features
# (cvd, delta_slope, no_move_*) y se exportan aparte: la paridad se juzga primero sobre
# geometria y ciclo de vida, no sobre features derivados.
GEOMETRIA = ("id", "instrument", "start_ts", "end_ts", "bucket", "dir",
             "price_upper", "price_lower", "height_ticks", "pasos", "valid_steps",
             "tick_res")
FEATURES = ("avg_ms", "total_ms", "vol_rate", "total_vol", "max_tick_vol", "cvd_sweep",
            "buy_vol", "sell_vol", "delta_slope", "delta_first", "delta_second",
            "no_move_ticks", "no_move_vol", "max_level_ticks", "max_retro")


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inventario_contratos(d_in):
    """Cobertura temporal y sesiones de cada parquet, SIN cargar los ticks.

    Se usa la metadata de row-groups para el rango, y una sola pasada por la columna de
    tiempo para las sesiones. Nunca se materializan las seis columnas.
    """
    out = []
    for f in sorted(d_in.glob("ES_*ticks*.parquet")):
        pf = pq.ParquetFile(f)
        n = pf.metadata.num_rows
        ts_min, ts_max, sesiones, n_fw = None, None, set(), 0
        for lote in pf.iter_batches(batch_size=1 << 21, columns=["ts_utc_ns"]):
            t = lote.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype(np.int64)
            ts_min = int(t[0]) if ts_min is None else min(ts_min, int(t.min()))
            ts_max = int(t.max()) if ts_max is None else max(ts_max, int(t.max()))
            pre = t[t < FIREWALL_CUTOFF_NS]
            n_fw += len(pre)
            if len(pre):
                sesiones.update(int(x) for x in np.unique(trade_date_ymd(pre)))
        out.append(dict(
            archivo=f.name, sha256=sha256_archivo(f), canon_disponible=False,
            filas=n, filas_pre_firewall=n_fw,
            gb_arrays_sin_ventana=round(n * 48 / 2 ** 30, 3),
            ts_min=ts_min, ts_max=ts_max,
            n_sesiones_pre_firewall=len(sesiones),
            primera_sesion=min(sesiones) if sesiones else None,
            ultima_sesion=max(sesiones) if sesiones else None))
        s = out[-1]
        print("  %-26s %11d filas  %5.2f GB  %3d sesiones  %s -> %s"
              % (f.name, n, s["gb_arrays_sin_ventana"], s["n_sesiones_pre_firewall"],
                 s["primera_sesion"], s["ultima_sesion"]))
    return out


def solapes(inv):
    """Detecta contratos que se pisan en el tiempo. Encadenarlos sin mirar esto
    duplicaria ticks, que es lo que el censo de 6E evita por construccion."""
    ord_ = sorted([x for x in inv if x["ts_min"] is not None], key=lambda x: x["ts_min"])
    pares = []
    for a, b in zip(ord_, ord_[1:]):
        if b["ts_min"] <= a["ts_max"]:
            pares.append(dict(a=a["archivo"], b=b["archivo"],
                              solape_ns=int(a["ts_max"] - b["ts_min"])))
    return ord_, pares


def extraer_oraculo(destino, contrato):
    if not SQLITE_ORACULO.exists():
        return dict(disponible=False, motivo="no existe %s" % SQLITE_ORACULO)
    con = sqlite3.connect("file:%s?mode=ro" % SQLITE_ORACULO.as_posix(), uri=True)
    cur = con.cursor()
    cols = GEOMETRIA + FEATURES
    q = ("SELECT %s FROM hft_zones WHERE instrument = ? AND start_ts < ? ORDER BY start_ts, id"
         % ",".join(cols))
    corte_ms = FIREWALL_CUTOFF_NS // 1_000_000
    filas = cur.execute(q, (contrato, corte_ms)).fetchall()
    total = cur.execute("SELECT COUNT(*) FROM hft_zones WHERE instrument = ?",
                        (contrato,)).fetchone()[0]
    con.close()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + "\n")
        for r in filas:
            f.write(",".join("" if v is None else str(v) for v in r) + "\n")
    return dict(disponible=True, contrato=contrato, archivo=str(destino),
                zonas_exportadas=len(filas), zonas_totales_del_contrato=total,
                zonas_descartadas_por_firewall=total - len(filas),
                corte_utc_ms=int(corte_ms),
                sha256=sha256_archivo(destino),
                nota=("el .cs escribe SQLite, no CSV; se convierte SIN tocarlo -- "
                      "modificar el indicador cambiaria el objeto que se valida"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--contrato-oraculo", default="ES 06-26",
                    help="contrato con cobertura integra pre-firewall")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "es_preparacion.json"))
    a = ap.parse_args()

    d_in = pathlib.Path(a.dir) if a.dir else (REPO / "data" / "nt8" / "ES_parquet")
    print("preparacion de ES  ·  %s" % SCHEMA_VERSION)
    print("  firewall: trade date %d  ->  corte %d ns" % (HOLDOUT_FIRST_TRADE_DATE,
                                                          FIREWALL_CUTOFF_NS))
    inv = inventario_contratos(d_in)
    ordenados, pares = solapes(inv)
    print()
    if pares:
        print("  SOLAPES detectados (encadenar sin resolverlos duplicaria ticks):")
        for p in pares:
            print("    %s  y  %s  se pisan %.1f h" % (p["a"], p["b"], p["solape_ns"] / 3.6e12))
    else:
        print("  sin solapes: los contratos se pueden encadenar en orden temporal")

    orac = extraer_oraculo(REPO / "data" / "nt8_oracles" /
                           "hftzonesespurev2_ES_0626_pre_firewall.csv", a.contrato_oraculo)
    print()
    if orac["disponible"]:
        print("  oraculo %s: %d zonas exportadas de %d (%d descartadas por firewall)"
              % (orac["contrato"], orac["zonas_exportadas"], orac["zonas_totales_del_contrato"],
                 orac["zonas_descartadas_por_firewall"]))
    else:
        print("  oraculo NO disponible: %s" % orac["motivo"])

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]
    out = dict(
        schema_version=SCHEMA_VERSION, instrumento="ES",
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        firewall=dict(holdout_first_trade_date=HOLDOUT_FIRST_TRADE_DATE,
                      cutoff_ns=int(FIREWALL_CUTOFF_NS)),
        nota_memoria=("`load_canonical_parquet` YA acepta start_utc_ns/end_utc_ns y "
                      "empuja el filtro a pyarrow. P-25 afirmaba que lee el archivo "
                      "completo: es falso, lo hacian las llamadas. Una sesion de "
                      "ES_06-26 sale en 1,38 M ticks (66 MB) contra 73,3 M del archivo."),
        contratos=inv,
        cadena_temporal=[x["archivo"] for x in ordenados],
        solapes=pares,
        oraculo=orac,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios),
            alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
