#!/usr/bin/env python3
"""Estima la curva de decaimiento de un cluster HFT. Target-free.

**No mira retornos.** Tres canales no direccionales: reentrada, cruce y permanencia.
Ningún resultado usa signo de retorno, P&L ni dirección esperada.

## Qué estima

Para cada cluster, en cada barra muestreada, se conoce la fracción de capacidad
consumida `c`. Se mide qué hace el precio en las `h` barras siguientes y se compara
contra un **placebo** de la misma geometría y distancia, del lado opuesto. El estimando
es el **contraste** por bin de `c`:

    contraste(c) = resultado(cluster con consumo c) - resultado(placebo emparejado)

Si el contraste cae con `c`, esa caída es la función de decaimiento. Si la curva cruda
cae pero el contraste no, la caída era del paso del tiempo y de la cercanía del precio,
no del consumo.

## Una decisión que hay que declarar

Con la invalidación dura activa, **el 99,4 % de los clusters muere perforado** antes de
consumirse (medido sobre el log real de NQ: 18.747 invalidados de 18.851 creados). Con
esa muerte no existe población con `c` alto y la curva no se puede estimar.

Por eso este runner **desactiva la invalidación por perforación**. Es un objeto distinto
del que dibuja el indicador, y se dice: se mide el cluster *sin muerte por perforación*,
para poder observar el decaimiento por consumo. La muerte se reintroduce después,
calibrada por lo que la curva diga — que es justamente el objetivo.

## Lo que este runner NO hace

No elige la mejor configuración de cluster ni el mejor predictor. Eso es optimizar
contra retornos y necesita el STOP del proyecto, manifiesto y holdout.
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
from edgelab.research import cluster_decay as cd  # noqa: E402

HOLDOUT_DESDE = pd.Timestamp("2026-07-01", tz="UTC")

# Sin muerte por perforacion: ver la nota del encabezado.
SIN_INVALIDACION = 10 ** 9


def una_sesion(path, t0, t1, tick_size, ticks_por_barra, p):
    tbl = pq.read_table(path, filters=[("ts_utc_ns", ">=", t0.value),
                                       ("ts_utc_ns", "<", t1.value)],
                        columns=["ts_utc_ns", "price_ticks", "volume"])
    if tbl.num_rows < 5000:
        return None
    ts = tbl.column("ts_utc_ns").to_numpy(zero_copy_only=False).astype("int64").tolist()
    px = tbl.column("price_ticks").to_numpy(zero_copy_only=False).astype("int64").tolist()
    vo = tbl.column("volume").to_numpy(zero_copy_only=False).astype("float64").tolist()

    zonas, _ = hz.accept_all(hz.detect_candidates(ts, px, vo),
                             hz.CAMPAIGN_FROZEN, tick_size)
    barras, perfiles = cd.barras_desde_ticks(ts, px, vo, ticks_por_barra)
    if len(barras) < p["horizonte_barras"] + p["ventana_sigma_barras"] + 10:
        return None

    cfg = dict(hc.CAMPAIGN_FROZEN, invalidation_ticks=SIN_INVALIDACION)
    eng = hc.ClusterEngine(tick_size, cfg)

    # zonas indexadas por la barra en que nacen
    por_barra = {}
    for z in zonas:
        por_barra.setdefault(z["idx_start"] // ticks_por_barra, []).append(z)

    acumuladas = []
    consumido = {}          # id -> volumen operado adentro
    muestras = []
    descartes = dict(sin_control=0, fuera_de_rango=0, sin_horizonte=0)

    for i, barra in enumerate(barras):
        for z in por_barra.get(i, []):
            acumuladas.append(dict(lower=z["sw_lo_tk"] * tick_size,
                                   upper=z["sw_hi_tk"] * tick_size,
                                   start_bar=i, total_vol=z["total_vol"],
                                   cvd=z["cvd"]))
            eng.on_zone_created(acumuladas, bar=i)

        vivos = [dict(id=c["id"],
                      lower_tk=int(round(c["lower"] / tick_size)),
                      upper_tk=int(round(c["upper"] / tick_size)),
                      poc_tk=int(round(c["poc"] / tick_size)),
                      capacidad=c["capacity_volume"], nacio=c["start_bar"])
                 for c in eng.clusters
                 if c["state"] in (hc.ACTIVE, hc.TOUCHED_POC)]
        if not vivos:
            continue

        for cid, v in cd.consumo_por_barra(vivos, perfiles[i]).items():
            consumido[cid] = consumido.get(cid, 0.0) + v

        if i % p["cada_n_barras"] or i < p["ventana_sigma_barras"]:
            continue

        precio = barra["close"]
        ocupados = [(c["lower_tk"], c["upper_tk"]) for c in vivos]
        sg = cd.sigma_local(barras, i, p["ventana_sigma_barras"])

        for c in vivos:
            d = (c["lower_tk"] - precio if c["lower_tk"] > precio
                 else precio - c["upper_tk"])
            if not (p["dist_min_ticks"] <= d <= p["dist_max_ticks"]):
                descartes["fuera_de_rango"] += 1
                continue
            real = cd.resultados(barras, i, c["lower_tk"], c["upper_tk"],
                                 p["horizonte_barras"])
            if real is None:
                descartes["sin_horizonte"] += 1
                continue
            ctrl_banda = cd.muestra_control(precio, c["lower_tk"], c["upper_tk"],
                                            ocupados)
            if ctrl_banda is None:
                descartes["sin_control"] += 1
                continue
            control = cd.resultados(barras, i, ctrl_banda[0], ctrl_banda[1],
                                    p["horizonte_barras"])
            muestras.append(dict(
                bar=i, cluster=c["id"],
                consumo=min(1.0, consumido.get(c["id"], 0.0) / max(1.0, c["capacidad"])),
                edad=i - c["nacio"], distancia=d, sigma=round(sg, 3),
                real=real, control=control))

    return dict(desde=str(t0), barras=len(barras), zonas=len(zonas),
                clusters=len(eng.clusters), muestras=len(muestras),
                descartes=descartes,
                muestras_detalle=muestras)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--desde", default="2026-05-12 21:00")
    ap.add_argument("--sesiones", type=int, default=3)
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--ticks-por-barra", type=int, default=25)
    ap.add_argument("--out", default="data/nt8_oracles/decaimiento_clusters_nq.json")
    a = ap.parse_args(argv)

    p = cd._p()
    d = pd.Timestamp(a.desde, tz="UTC")
    ventanas = []
    while len(ventanas) < a.sesiones:
        if d.dayofweek < 5:
            ventanas.append((d, d + pd.Timedelta(hours=23)))
        d += pd.Timedelta(days=1)
    if any(t1 >= HOLDOUT_DESDE for _, t1 in ventanas):
        print("FIREWALL: la ventana cruza el holdout. No se corre.")
        return 1

    todas = []
    resumen = []
    for t0, t1 in ventanas:
        r = una_sesion(REPO / a.parquet, t0, t1, a.tick_size, a.ticks_por_barra, p)
        if r is None:
            print("sesion sin datos suficientes:", t0.date())
            continue
        todas.extend(r.pop("muestras_detalle"))
        resumen.append(r)
        print(f"{t0.date()}  barras={r['barras']:,}  zonas={r['zonas']:,}  "
              f"clusters={r['clusters']:,}  muestras={r['muestras']:,}  "
              f"descartes={r['descartes']}")

    if not todas:
        print("sin muestras: nada que estimar")
        return 1

    curvas = {}
    for canal in ("reentra", "cruza", "barras_adentro"):
        curvas[canal] = cd.curva(todas, canal, p["bordes_consumo"])

    n = len(todas)
    mde = cd.mde_proporcion(n, celdas=len(p["bordes_consumo"]) - 1, deff=5.0)

    print(f"\nmuestras totales: {n:,}   MDE (5 bins, deff=5): {mde:.4f}")
    for canal, filas in curvas.items():
        print(f"\n--- {canal} ---")
        print(f"{'consumo':>12}{'n':>7}{'real':>8}{'placebo':>9}{'contraste':>11}")
        for f in filas:
            r = "  n/d" if f["real"] is None else f"{f['real']:>8.3f}"
            pl = "  n/d" if f["placebo"] is None else f"{f['placebo']:>9.3f}"
            ct = "  n/d" if f["contraste"] is None else f"{f['contraste']:>+11.3f}"
            marca = "" if f["suficiente"] else "  (bin flaco)"
            print(f"{f['desde']:>6}-{f['hasta']:<5}{f['n']:>7}{r}{pl}{ct}{marca}")

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(dict(config=hc.CAMPAIGN_FROZEN, muestreo=p, sesiones=resumen,
                   n_muestras=n, mde=mde, curvas=curvas,
                   nota="invalidacion por perforacion DESACTIVADA; ver encabezado"),
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nescrito:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
