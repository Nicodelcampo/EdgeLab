#!/usr/bin/env python3
"""Canal direccional (H2): ¿el precio rechaza los extremos de un cluster?

**Target-free.** No hay P&L, ni entrada, ni salida, ni costo. Sólo la geometría del
recorrido posterior a un contacto.

## La pregunta

Hipótesis de Nico: *«el precio rechaza los extremos de un cluster»*. Es el complemento
direccional de H1 (atracción, que mide `decaimiento_clusters_nq.py`).

## El control

Se enumeran **todos** los contactos de primera vez con un nivel de precio en la sesión
—haya cluster o no— y se contrasta la tasa de rechazo entre los que caen sobre un borde
vivo y los que no. Es decir: el cluster no se compara contra nada, se compara contra
*un nivel cualquiera al que el precio llegó igual*.

El contraste se lee **estratificado** por distancia de aproximación y volatilidad local.
Sin estratificar mediría que el precio llega a los bordes de cluster de otra manera, no
que reaccione distinto una vez que llegó. El agregado se publica al lado, nunca en su
lugar: con exposición dependiente de la distancia, la inversión de Simpson es un riesgo
real y hay un test que lo demuestra.

## Diferencia con el módulo de decaimiento

Aquel mide **si el precio llega** (canal no direccional, con placebo geométrico del lado
opuesto). Éste mide **qué hace cuando llegó** (canal direccional, con control por nivel
sin cluster). Los dos hacen falta: un efecto bidireccional promedia cero si sólo se mira
uno.
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
from edgelab.research import cluster_rejection as cr  # noqa: E402

HOLDOUT_DESDE = pd.Timestamp("2026-07-01", tz="UTC")


def una_sesion(path, t0, t1, tick_size, ticks_por_barra, p, vivos_solamente=True):
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
    barras, _ = cd.barras_desde_ticks(ts, px, vo, ticks_por_barra)
    if len(barras) < p["horizonte"] + 60:
        return None

    eng = hc.ClusterEngine(tick_size, hc.CAMPAIGN_FROZEN)
    por_barra = {}
    for z in zonas:
        por_barra.setdefault(z["idx_start"] // ticks_por_barra, []).append(z)

    acumuladas = []
    muestras = []
    nacimientos = []          # barra de cada nacimiento de zona, para la intensidad
    for i, barra in enumerate(barras):
        for z in por_barra.get(i, []):
            nacimientos.append(i)
            acumuladas.append(dict(lower=z["sw_lo_tk"] * tick_size,
                                   upper=z["sw_hi_tk"] * tick_size,
                                   start_bar=i, total_vol=z["total_vol"],
                                   cvd=z["cvd"]))
            eng.on_zone_created(acumuladas, bar=i)
        eng.on_bar(i)

        if i < 60:
            continue
        estados = (hc.ACTIVE, hc.TOUCHED_POC) if vivos_solamente else None
        vivos = [dict(lower_tk=int(round(c["lower"] / tick_size)),
                      upper_tk=int(round(c["upper"] / tick_size)),
                      ultima=c["end_bar"])
                 for c in eng.clusters
                 if estados is None or c["state"] in estados]

        # intensidad: nacimientos de zona en la ventana previa. Es la covariable del
        # escalon 5 -- el cluster nace donde ya habia actividad.
        w0 = i - p["ventana_intensidad"]
        intensidad = sum(1 for b in nacimientos if w0 <= b <= i)

        sg = cd.sigma_local(barras, i, 50)
        for nivel, lado in cr.contactos(barras, i, p):
            des = cr.desenlace(barras, i, nivel, lado, p)
            if des is None:
                continue
            c_borde = cr.borde_de(nivel, vivos)
            muestras.append(dict(
                bar=i, nivel=nivel, lado=lado, sigma=round(sg, 3),
                distancia=nivel - barras[i - 1]["close"],
                intensidad=intensidad,
                # hold-out: hace cuanto que el objeto no se actualiza. Si el cluster se
                # acaba de mover, su definicion usa el mismo tramo de precio que despues
                # se mide.
                lag=(i - c_borde["ultima"]) if c_borde else None,
                borde=c_borde is not None,
                categoria=cr.categoria(nivel, vivos),
                desenlace=des))
    return dict(desde=str(t0), barras=len(barras), zonas=len(zonas),
                clusters=len(eng.clusters), muestras=muestras)


def _volcar_muestras(todas, out_json):
    """Guarda las muestras crudas en un parquet ignorado por git.

    La corrida cuesta ~90 minutos y el runner las descartaba al agregar. Cada pregunta
    nueva sobre el mismo dato -estratificar el hold-out, otro umbral de lag, bootstrap
    por sesion- obligaba a repetirla entera. Con esto se responde en segundos.
    """
    destino = REPO / "data/research_cache" / (out_json.stem + "_muestras.parquet")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(todas).to_parquet(destino, index=False)
        print(f"muestras crudas: {destino}  ({len(todas):,} filas)")
    except Exception as e:
        print(f"WARN al volcar muestras: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="data/nt8/NQ_parquet/NQ_06-26_ticks.parquet")
    ap.add_argument("--desde", default="2026-04-01 22:00")
    ap.add_argument("--sesiones", type=int, default=10)
    ap.add_argument("--tick-size", type=float, default=0.25)
    ap.add_argument("--ticks-por-barra", type=int, default=25)
    ap.add_argument("--out", default="data/nt8_oracles/rechazo_clusters_nq.json")
    a = ap.parse_args(argv)

    p = cr._p()
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
            continue
        ms = r.pop("muestras")
        todas.extend(ms)
        r["n_muestras"] = len(ms)
        r["n_borde"] = sum(1 for m in ms if m["borde"])
        resumen.append(r)
        # Guardado parcial por sesión (checkpointing para no perder progreso)
        parcial_out = (REPO / a.out).with_name(Path(a.out).stem + "_parcial.json")
        try:
            t_p = cr.tabla(todas, p) if todas else []
            ag_p = cr.agregado(todas) if todas else {}
            n_b_p = ag_p.get("borde", {}).get("n", 0)
            mde_p = cd.mde_proporcion(n_b_p, celdas=max(1, len(t_p)), deff=5.0) if n_b_p else None
            parcial_out.parent.mkdir(parents=True, exist_ok=True)
            with open(parcial_out, "w", encoding="utf-8") as fp:
                json.dump(dict(config=hc.CAMPAIGN_FROZEN, muestreo=p, sesiones=resumen,
                               sesiones_completadas=len(resumen), sesiones_pedidas=len(ventanas),
                               n=len(todas), mde=mde_p, agregado=ag_p, tabla=t_p),
                          fp, ensure_ascii=False, indent=1)
        except Exception as e:
            print(f"WARN al escribir parcial: {e}")

    if not todas:
        print("sin muestras")
        return 1

    t = cr.tabla(todas, p)
    ag = cr.agregado(todas)
    n_b = ag["borde"]["n"]
    mde = cd.mde_proporcion(n_b, celdas=max(1, len(t)), deff=5.0) if n_b else None

    print(f"\ncontactos: {len(todas):,}   resueltos en borde: {n_b:,}   "
          f"MDE({len(t)} celdas, deff=5): {mde:.4f}" if mde else "")
    print("\n--- agregado (NO leer solo: ver la tabla) ---")
    print(f"   borde     n={ag['borde']['n']:>6,}  rechazo={ag['borde']['rechazo']}")
    print(f"   sin borde n={ag['sin_borde']['n']:>6,}  rechazo={ag['sin_borde']['rechazo']}")
    print(f"   contraste = {ag['contraste']}")
    print("\n--- estratificado por distancia x sigma ---")
    print(f"{'binD':>5}{'binS':>5}{'n_borde':>9}{'n_libre':>9}{'n_dentro':>9}"
          f"{'rech_b':>9}{'rech_libre':>11}{'contr':>9}")
    for f in t:
        rb = "  n/d" if f["rechazo_borde"] is None else f"{f['rechazo_borde']:>9.3f}"
        rs = "  n/d" if f["rechazo_sin_borde"] is None else f"{f['rechazo_sin_borde']:>9.3f}"
        ct = "  n/d" if f["contraste"] is None else f"{f['contraste']:>+9.3f}"
        marca = "" if f["suficiente"] else "  (flaco)"
        print(f"{f['bin_distancia']:>5}{f['bin_sigma']:>5}{f['n_borde']:>9,}"
              f"{f['n_sin_borde']:>9,}{f.get('n_dentro',0):>9,}{rb}{rs:>11}{ct}{marca}")

    # --- escalon 5 ---
    print("\n--- escalon 5a: estratificado por INTENSIDAD (nacimientos/100 barras) ---")
    t_int = cr.tabla_por(todas, "intensidad", p["bordes_intensidad"])
    print(f"{'bin':>4}{'n_borde':>9}{'n_libre':>9}{'rech_b':>9}{'rech_l':>9}{'contr':>9}")
    for f in t_int:
        rb = "  n/d" if f["rechazo_borde"] is None else f"{f['rechazo_borde']:>9.3f}"
        rl = "  n/d" if f["rechazo_libre"] is None else f"{f['rechazo_libre']:>9.3f}"
        ct = "  n/d" if f["contraste"] is None else f"{f['contraste']:>+9.3f}"
        print(f"{f['bin']:>4}{f['n_borde']:>9,}{f['n_libre']:>9,}{rb}{rl}{ct}"
              + ("" if f["suficiente"] else "  (flaco)"))

    lag = p["lag_holdout"]
    ho = [m for m in todas if m.get("categoria") == "libre"
          or (m.get("lag") is not None and m["lag"] >= lag)]
    ag_ho = cr.agregado(ho)
    print(f"\n--- escalon 5b: objeto HOLD-OUT (cluster sin tocar hace >= {lag} barras) ---")
    print(f"   borde n={ag_ho['borde']['n']:>7,}  rechazo={ag_ho['borde']['rechazo']}")
    print(f"   libre n={ag_ho['sin_borde']['n']:>7,}  rechazo={ag_ho['sin_borde']['rechazo']}")
    print(f"   contraste = {ag_ho['contraste']}")

    # 5b no se puede leer con un solo numero: el mismo -0,01 es compatible con "el
    # efecto desaparece al aislar el objeto" y con "el subconjunto rancio no tiene
    # potencia". Se publica la descomposicion completa y su diferencia.
    lagd = cr.contraste_lag(todas, lag, deff=5.0)
    print(f"   fresco (lag<{lag})  n={lagd['fresco']['n']:>7,}  "
          f"rechazo={lagd['fresco']['rechazo']:.4f}  vs libre {lagd['fresco']['contraste']:+.4f}"
          f"  z={lagd['fresco']['z']:+.2f}")
    print(f"   rancio (lag>={lag}) n={lagd['rancio']['n']:>7,}  "
          f"rechazo={lagd['rancio']['rechazo']:.4f}  vs libre {lagd['rancio']['contraste']:+.4f}"
          f"  z={lagd['rancio']['z']:+.2f}")
    print(f"   diferencia fresco-rancio = {lagd['diferencia']['valor']:+.4f}  "
          f"z={lagd['diferencia']['z']:+.2f}  p={lagd['diferencia']['p_valor']:.2e}")

    # y estratificado: la rancidez no es aleatoria -- un cluster lleva 30 barras sin
    # tocarse porque el precio estuvo lejos, y el rechazo cae con la distancia. Sin
    # estratificar, la particion puede ser composicion y no objeto.
    t_ho = cr.tabla(ho, p)
    frescos = [m for m in todas if m.get("categoria") == "libre"
               or (m.get("lag") is not None and m["lag"] < lag)]
    t_fr = cr.tabla(frescos, p)
    print("\n--- 5b estratificado: contraste por estrato, rancio | fresco ---")
    print(f"{'binD':>5}{'binS':>5}{'n_ranc':>9}{'contr_r':>10}{'n_fresco':>10}{'contr_f':>10}")
    idx = {(f["bin_distancia"], f["bin_sigma"]): f for f in t_fr}
    for f in t_ho:
        g = idx.get((f["bin_distancia"], f["bin_sigma"]), {})
        c_r = "       n/d" if f["contraste"] is None else f"{f['contraste']:>+10.3f}"
        c_f = "       n/d" if g.get("contraste") is None else f"{g['contraste']:>+10.3f}"
        print(f"{f['bin_distancia']:>5}{f['bin_sigma']:>5}{f['n_borde']:>9,}{c_r}"
              f"{g.get('n_borde', 0):>10,}{c_f}")

    ag_limpio = cr.agregado_limpio(todas)
    print("\n--- agregado con control LIMPIO (borde vs libre, sin el interior) ---")
    print(f"   borde  n={ag_limpio['borde']['n']:>7,}  rechazo={ag_limpio['borde']['rechazo']:.4f}")
    print(f"   libre  n={ag_limpio['libre']['n']:>7,}  rechazo={ag_limpio['libre']['rechazo']:.4f}")
    print(f"   dentro n={ag_limpio['dentro']['n']:>7,}  rechazo={ag_limpio['dentro']['rechazo']:.4f}")
    print(f"   contraste limpio = {ag_limpio['contraste']:+.4f}   "
          f"(el de `agregado` mezcla libre con dentro: {ag['contraste']:+.4f})")

    _volcar_muestras(todas, REPO / a.out)

    out = REPO / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(dict(config=hc.CAMPAIGN_FROZEN, muestreo=p, sesiones=resumen,
                   n=len(todas), mde=mde, agregado=ag, tabla=t,
                   escalon5_intensidad=t_int, escalon5_holdout=ag_ho,
                   agregado_limpio=ag_limpio, escalon5_lag=lagd,
                   escalon5_tabla_rancio=t_ho, escalon5_tabla_fresco=t_fr),
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nescrito:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
