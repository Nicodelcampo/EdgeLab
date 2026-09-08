#!/usr/bin/env python3
"""Escalón 3 del embudo — sensibilidad al parámetro de vigencia.

**Target-free.** No mira retornos.

## Por qué este escalón es crítico y no un detalle

El deep research (`docs/research/deep_research/DEEP_RESEARCH_HFT_CLUSTER_MAGNETISMO_2026-09-07.md`)
lo marca como el escalón que decide si el cluster es **estructura de mercado** o
**artefacto de una decisión de presentación**. Su condición de refutación es explícita:

> *Si el signo o el tamaño cambian materialmente con la vigencia, la membresía es
> decisión de presentación.*

En este indicador la vigencia ya **no** es cosmética —`max_age_bars` es un parámetro de
investigación, no la extensión del dibujo— y eso resuelve el defecto D1 que el documento
identificaba. Pero su **valor** sigue siendo arbitrario: todas las mediciones anteriores
de esta campaña usaron 500 barras sin haberlo barrido nunca. Eso es exactamente lo que
el documento prohíbe: tratar como dato un parámetro que nadie midió.

## Qué gobierna `max_age_bars`

Dos cosas a la vez, y conviene tenerlas separadas al leer los resultados:

1. **Qué zonas entran al campo** — el pool descarta las nacidas hace más de `max_age`.
2. **Cuánto vive un cluster** — pasa a `EXPIRED` al superar esa edad desde su
   nacimiento.

Así que subirlo agranda el pool *y* alarga la vida. Si el objeto sólo es estable en una
ventana angosta del parámetro, es un artefacto.

## Métrica y criterio

Para cada vigencia se reportan las mismas tres familias del test de estabilidad
(turnover ante ±1 de volumen, cobertura media as-of, cantidad de clusters), sobre la
configuración congelada de la campaña. El criterio de supervivencia es el mismo del
contrato del repo: **turnover < 5 %**, y que el objeto exista y no cubra todo.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.indicators import hftclusterzones as hc  # noqa: E402
from edgelab.bridge.indicators import hftzones_nq as hz  # noqa: E402
from tools.estabilidad_clusters_nq import (  # noqa: E402
    cobertura_media, clusters_de, perturbar, ticks_cubiertos, turnover)

HOLDOUT_DESDE = pd.Timestamp("2026-07-01", tz="UTC")

# Barrido pre-declarado. Se publica completo, pasen o no.
VIGENCIAS = [50, 100, 250, 500, 1000, 2000]


def una_sesion(path, t0, t1, tick_size, ticks_por_barra):
    tbl = pq.read_table(path, filters=[("ts_utc_ns", ">=", t0.value),
                                       ("ts_utc_ns", "<", t1.value)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    if tbl.num_rows < 1000:
        return None
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    c0 = hz.detect_candidates(ts, px, vo)
    c1 = hz.detect_candidates(ts, px, perturbar(vo))
    umbral = {"min_total_volume": hz.CAMPAIGN_FROZEN["min_total_volume"]}
    z0, _ = hz.accept_all(c0, umbral, tick_size)
    z1, _ = hz.accept_all(c1, umbral, tick_size)
    rango = max(px) - min(px) + 1
    barras = (len(ts) // ticks_por_barra) or 1

    celdas = []
    for vig in VIGENCIAS:
        p = dict(hc.CAMPAIGN_FROZEN, max_age_bars=vig)
        e0 = clusters_de(z0, tick_size, ticks_por_barra, p)
        e1 = clusters_de(z1, tick_size, ticks_por_barra, p)
        celdas.append(dict(
            max_age_bars=vig,
            vigencia_vs_sesion=round(vig / barras, 3),
            clusters=len(e0.clusters),
            turnover=round(turnover(ticks_cubiertos(e0, tick_size),
                                    ticks_cubiertos(e1, tick_size)), 4),
            cobertura_media_pct=round(
                cobertura_media(e0, tick_size, rango, vig), 2),
        ))
    return dict(desde=str(t0), ticks=len(ts), barras=barras, zonas=len(z0),
                rango_ticks=rango, celdas=celdas)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--desde", default="2026-05-12 21:00")
    ap.add_argument("--sesiones", type=int, default=3)
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--ticks-por-barra", type=int, default=25)
    ap.add_argument("--out", default="data/nt8_oracles/vigencia_clusters_nq.json")
    a = ap.parse_args(argv)

    d = pd.Timestamp(a.desde, tz="UTC")
    ventanas = []
    while len(ventanas) < a.sesiones:
        if d.dayofweek < 5:
            ventanas.append((d, d + pd.Timedelta(hours=23)))
        d += pd.Timedelta(days=1)
    if any(t1 >= HOLDOUT_DESDE for _, t1 in ventanas):
        print("FIREWALL: la ventana cruza el holdout. No se corre.")
        return 1

    salida = dict(escalon="3 - sensibilidad a la vigencia",
                  config=hc.CAMPAIGN_FROZEN, vigencias=VIGENCIAS,
                  criterio="turnover < 5% en TODAS las vigencias razonables",
                  sesiones=[])
    for t0, t1 in ventanas:
        r = una_sesion(REPO / a.parquet, t0, t1, a.tick_size, a.ticks_por_barra)
        if r is None:
            continue
        salida["sesiones"].append(r)
        print(f"{t0.date()}  barras={r['barras']:,}  zonas={r['zonas']:,}")
        for c in r["celdas"]:
            print(f"   vigencia={c['max_age_bars']:>5} "
                  f"({c['vigencia_vs_sesion']:>5.2f}x sesion)  "
                  f"clusters={c['clusters']:>4}  "
                  f"turnover={100*c['turnover']:>5.1f}%  "
                  f"cobertura={c['cobertura_media_pct']:>5.1f}%")

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(salida, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nescrito:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
