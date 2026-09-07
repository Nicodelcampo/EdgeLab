#!/usr/bin/env python3
"""Censo target-free de zonas HFT sobre NQ, con barrido de umbrales gratis.

**No mira retornos.** Cuenta candidatos, zonas aceptadas y por qué mueren los
rechazados. No hay P&L, no hay dirección esperada, no hay selección por resultado.

## Para qué existe

Nico planteó el orden correcto: *exportar todas las zonas posibles y recién después,
en base a datos, decidir cómo definir un cluster*. Este script produce ese dato.

La clave es la separación de `hftzones_nq`: una pasada por tick emite **todos** los
candidatos con sus estadísticos suficientes, y después los diez umbrales de aceptación
se aplican por aritmética. Un barrido que en NinjaTrader exigiría re-correr el chart
entero acá cuesta un `for`.

## Firewall

El corte del holdout es 2026-07-01. El script **rechaza** cualquier ventana que lo
cruce: un censo target-free no justifica abrir la ventana sellada.

    .venv\\Scripts\\python tools\\censo_zonas_nq.py --contrato "NQ 06-26" --sesiones 3
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402

HOLDOUT_DESDE = pd.Timestamp("2026-07-01", tz="UTC")

# Barridos que se publican SIEMPRE, completos. No se elige el mejor: el objetivo es
# medir la sensibilidad de la poblacion, no encontrar el umbral que mas gusta.
BARRIDOS = {
    "min_total_volume": [0, 10, 25, 50, 100, 200],
    "min_volume_rate": [0, 25, 50, 100, 200, 400],
    "min_pasos": [4, 6, 8, 12, 20, 40],
    "min_sweep_ticks": [1, 2, 4, 8, 16],
    "max_avg_ms": [5, 10, 25, 50, 100],
    "min_absorb_pasos": [3, 6, 12],
}


def sesiones_cme(inicio, n):
    """Ventanas de sesion CME: 17:00 CT a 16:00 CT del dia siguiente.

    Se usa el offset fijo CDT (UTC-5) del periodo mayo-junio 2026 a proposito y se
    declara: construir un calendario DST-aware es otro trabajo, y una ventana mal
    corrida se veria como un cambio de poblacion.
    """
    out = []
    d = pd.Timestamp(inicio, tz="UTC")
    while len(out) < n:
        if d.dayofweek < 5:
            out.append((d, d + pd.Timedelta(hours=23)))
        d += pd.Timedelta(days=1)
    return out


def censo_sesion(path, t0, t1):
    tbl = pq.read_table(path,
                        filters=[("ts_utc_ns", ">=", t0.value),
                                 ("ts_utc_ns", "<", t1.value)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    if tbl.num_rows < 1000:
        return None
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    t = time.time()
    cands = hz.detect_candidates(ts, px, vo)
    segundos = time.time() - t

    zonas, motivos = hz.accept_all(cands)
    med = lambda v: sorted(v)[len(v) // 2] if v else None

    barridos = {}
    for nombre, valores in BARRIDOS.items():
        barridos[nombre] = {str(v): len(hz.accept_all(cands, {nombre: v})[0])
                            for v in valores}
    barridos["detect_absorb=False"] = len(
        hz.accept_all(cands, {"detect_absorb": False})[0])

    return dict(
        desde=str(t0), hasta=str(t1),
        ticks=len(ts), candidatos=len(cands), segundos=round(segundos, 2),
        zonas_defaults=len(zonas),
        muertes=dict(sorted(motivos.items(), key=lambda kv: -kv[1])),
        buckets=dict(collections.Counter(z["bucket"] for z in zonas)),
        altura_mediana_ticks=med([z["height_ticks"] for z in zonas]),
        pasos_mediano=med([z["valid_steps"] for z in zonas]),
        vol_mediano=med([z["total_vol"] for z in zonas]),
        avg_ms_mediano=med([z["avg_ms"] for z in zonas]),
        barridos=barridos,
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--contrato", default="NQ 06-26")
    ap.add_argument("--desde", default="2026-05-12 21:00")
    ap.add_argument("--sesiones", type=int, default=3)
    ap.add_argument("--out", default="data/nt8_oracles/censo_zonas_nq.json")
    a = ap.parse_args(argv)

    path = REPO / "data" / "nt8" / "NQ_parquet" / (a.contrato.replace(" ", "_") + "_ticks.parquet")
    if not path.exists():
        print("no existe:", path)
        return 2

    ventanas = sesiones_cme(a.desde, a.sesiones)
    if any(t1 >= HOLDOUT_DESDE for _, t1 in ventanas):
        print("FIREWALL: la ventana pedida cruza el holdout (%s). No se corre."
              % HOLDOUT_DESDE.date())
        return 1

    salida = dict(contrato=a.contrato, sesiones=[],
                  defaults_aceptacion=hz.ACCEPT_DEFAULTS,
                  defaults_estructurales=hz.STRUCTURAL_DEFAULTS,
                  nota="target-free: censo de geometria y ciclo de vida, sin retornos")
    for t0, t1 in ventanas:
        r = censo_sesion(path, t0, t1)
        if r is None:
            print("sesion vacia:", t0)
            continue
        salida["sesiones"].append(r)
        print(f"{t0.date()}  ticks={r['ticks']:>9,}  cand={r['candidatos']:>7,}  "
              f"zonas={r['zonas_defaults']:>5}  {r['segundos']}s")

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(salida, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nescrito:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
