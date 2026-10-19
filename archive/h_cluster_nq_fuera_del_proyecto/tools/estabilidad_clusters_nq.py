#!/usr/bin/env python3
"""Estabilidad target-free de zonas y clusters HFT.

**No mira retornos.** Mide si el objeto sobrevive a una perturbación mínima de los
datos y si no es degenerado. Nada de esto requiere el STOP del proyecto.

## El criterio es el que el proyecto ya fijó

`docs/research/PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`: perturbar el volumen por
tick en **±1 sobre dos tercios de los ticks** y exigir **turnover de zonas < 5 %**.
`aVolClusterPOI` da 66 % y no pasa. Ese es el número a batir.

## Una simplificación que vale la pena entender

La máquina de estados que segmenta las rachas depende **sólo de precios y tiempos**: el
volumen no interviene en dónde empieza ni termina una racha. Por lo tanto el conjunto
de **candidatos es invariante** a esta perturbación, y todo el turnover que aparezca
viene de las compuertas de volumen (`min_total_volume`, `min_volume_rate`).

Eso hace el test barato —se detecta una vez y se acepta dos— y también más informativo:
el turnover mide exactamente cuántas zonas viven pegadas a su umbral.

## Qué se reporta

El **landscape completo**, todas las celdas. No se elige la mejor: elegir por resultado
es precisamente lo que el proyecto prohíbe, y acá ni siquiera hay un resultado que
optimizar — hay una superficie de sensibilidad.

Tres familias de métrica:

1. **Turnover** ante la perturbación, de zonas y de clusters.
2. **Degeneración**: qué fracción del rango de precio de la sesión queda cubierta por
   algún cluster. Cerca de 0 % o de 100 % el objeto no discrimina nada.
3. **Consistencia entre sesiones**: si el conteo varía por un factor grande entre
   sesiones contiguas, la definición no describe una propiedad estable del mercado.
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

HOLDOUT_DESDE = pd.Timestamp("2026-07-01", tz="UTC")

# Ejes del barrido. Se publican completos.
VOL_UMBRAL = [10, 25, 50, 100]          # min_total_volume: gobierna cuantas zonas hay
SIGMA = [1.0, 3.0, 6.0]                 # ancho del halo, en ticks
DENSIDAD = [2.0, 3.0, 5.0]              # densidad acumulada que dispara un cluster


def perturbar(volumen):
    """±1 sobre dos tercios de los ticks, determinista.

    Determinista a propósito: un test de estabilidad con ruido aleatorio no es
    reproducible, y entonces no se puede sellar como gate. El patrón alterna signo por
    paridad del índice y se salta uno de cada tres.
    """
    out = list(volumen)
    for i in range(len(out)):
        if i % 3 == 0:
            continue
        out[i] = max(1.0, out[i] + (1.0 if i % 2 else -1.0))
    return out


def clusters_de(zonas, tick_size, ticks_por_barra, params):
    """Construye los clusters recorriendo los nacimientos de zona, en orden.

    Sólo geometría: no se alimentan ticks, así que no hay consumo ni muerte por
    volumen. Es deliberado — esta herramienta mide estabilidad de la **definición**,
    no del ciclo de vida.
    """
    eng = hc.ClusterEngine(tick_size, params)
    acumuladas = []
    for z in sorted(zonas, key=lambda x: x["idx_start"]):
        acumuladas.append(dict(lower=z["sw_lo_tk"] * tick_size,
                               upper=z["sw_hi_tk"] * tick_size,
                               start_bar=z["idx_start"] // ticks_por_barra,
                               total_vol=z["total_vol"], cvd=z["cvd"]))
        eng.on_zone_created(acumuladas, bar=z["idx_start"] // ticks_por_barra)
    return eng


def ticks_cubiertos(eng, tick_size):
    """Union de todo lo que algun cluster llego a cubrir en la sesion.

    Sirve para el turnover —comparar dos corridas sobre el mismo eje— pero **no** para
    medir degeneracion: unir clusters que nunca coexistieron infla la cobertura.
    Para eso esta `cobertura_media`.
    """
    out = set()
    for c in eng.clusters:
        lo = int(round(c["lower"] / tick_size))
        hi = int(round(c["upper"] / tick_size))
        out.update(range(lo, hi + 1))
    return out


def cobertura_media(eng, tick_size, rango_ticks, max_age, n_muestras=200):
    """Fraccion del rango cubierta por clusters VIVOS, promediada sobre la sesion.

    As-of: en cada barra muestreada cuentan solo los clusters nacidos antes y que
    todavia no expiraron por edad. Es la metrica honesta de degeneracion -- si da
    ~100 %, estar dentro de un cluster no informa nada; si da ~0 %, el objeto no
    existe.
    """
    if not eng.clusters or rango_ticks <= 0:
        return 0.0
    b0 = min(c["start_bar"] for c in eng.clusters)
    b1 = max(c["start_bar"] for c in eng.clusters)
    if b1 <= b0:
        return 0.0
    paso = max(1, (b1 - b0) // n_muestras)
    total = 0.0
    n = 0
    for bar in range(b0, b1 + 1, paso):
        vivos = set()
        for c in eng.clusters:
            if c["start_bar"] <= bar <= c["start_bar"] + max_age:
                lo = int(round(c["lower"] / tick_size))
                hi = int(round(c["upper"] / tick_size))
                vivos.update(range(lo, hi + 1))
        total += len(vivos) / rango_ticks
        n += 1
    return 100.0 * total / max(1, n)


def jaccard(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def turnover(a, b):
    """Fracción de la unión que NO está en los dos. 0 = idénticos."""
    if not a and not b:
        return 0.0
    return 1.0 - jaccard(a, b)


def una_sesion(path, t0, t1, tick_size, ticks_por_barra):
    tbl = pq.read_table(path, filters=[("ts_utc_ns", ">=", t0.value),
                                       ("ts_utc_ns", "<", t1.value)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    if tbl.num_rows < 1000:
        return None
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    # el candidato NO depende del volumen: una sola deteccion sirve para las dos ramas
    cands = hz.detect_candidates(ts, px, vo)
    cands_pert = hz.detect_candidates(ts, px, perturbar(vo))
    rango_ticks = max(px) - min(px) + 1

    celdas = []
    for mtv in VOL_UMBRAL:
        z0, _ = hz.accept_all(cands, {"min_total_volume": mtv}, tick_size)
        z1, _ = hz.accept_all(cands_pert, {"min_total_volume": mtv}, tick_size)
        id_z = lambda zs: {(z["ts_start"], z["ts_end"], z["direction"]) for z in zs}
        tz = turnover(id_z(z0), id_z(z1))

        for sg in SIGMA:
            for de in DENSIDAD:
                p = dict(halo_sigma_ticks=sg, min_density=de,
                         max_age_bars=500, min_capacity_volume=100.0)
                e0 = clusters_de(z0, tick_size, ticks_por_barra, p)
                e1 = clusters_de(z1, tick_size, ticks_por_barra, p)
                c0 = ticks_cubiertos(e0, tick_size)
                c1 = ticks_cubiertos(e1, tick_size)
                celdas.append(dict(
                    min_total_volume=mtv, sigma=sg, min_density=de,
                    zonas=len(z0), turnover_zonas=round(tz, 4),
                    clusters=len(e0.clusters),
                    turnover_clusters=round(turnover(c0, c1), 4),
                    cobertura_union_pct=round(100.0 * len(c0) / rango_ticks, 2),
                    cobertura_media_pct=round(
                        cobertura_media(e0, tick_size, rango_ticks, 500), 2),
                    ancho_mediano_ticks=(sorted(
                        (c["upper"] - c["lower"]) / tick_size for c in e0.clusters
                    )[len(e0.clusters) // 2] if e0.clusters else 0.0),
                ))
    return dict(desde=str(t0), ticks=len(ts), candidatos=len(cands),
                rango_ticks=rango_ticks, celdas=celdas)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--desde", default="2026-05-12 21:00")
    ap.add_argument("--sesiones", type=int, default=3)
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--ticks-por-barra", type=int, default=25)
    ap.add_argument("--out", default="data/nt8_oracles/estabilidad_clusters_nq.json")
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

    salida = dict(parquet=a.parquet, criterio="turnover de zonas < 5% (contrato del repo)",
                  perturbacion="volumen +-1 en dos tercios de los ticks, determinista",
                  ejes=dict(min_total_volume=VOL_UMBRAL, sigma=SIGMA, min_density=DENSIDAD),
                  sesiones=[])
    for t0, t1 in ventanas:
        r = una_sesion(REPO / a.parquet, t0, t1, a.tick_size, a.ticks_por_barra)
        if r is None:
            continue
        salida["sesiones"].append(r)
        print(f"{t0.date()}  ticks={r['ticks']:>9,}  celdas={len(r['celdas'])}")

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(salida, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("escrito:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
