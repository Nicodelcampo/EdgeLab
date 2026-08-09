"""`f` con LOS DOS filtros: `sep_min` **y** excursion valida. Cierra E-R1 §9.

## El problema que resuelve

Nadie aplico los dos filtros juntos:

    censo_primeros_toques.py   sep_min SI   excursion NO   1.825 ev  9,08/ses
    recuento_kT.py             sep_min NO   excursion SI   1.655 ev  8,23/ses
    lo que E-R1 necesita       SI           SI             ESTE MODULO

`recuento_kT.py` no menciona `sep_min` en ninguna linea -verificado-. Y v0.3
§6.3 publica `f ~= 8,3` para `BigTrap2` a `T=34`, que coincide con 8,23 y por lo
tanto viene de la poblacion SIN `sep_min`. Es coincidencia entre dos filtros
distintos, no confirmacion.

## Como se compone la condicion

La poblacion autoritativa es el **primer toque** (`first_touch_ms`). La condicion
de excursion de v0.3 §3.2 es `k_T > 0` y retorno posterior. Sobre la poblacion de
primeros toques eso se vuelve exacto y simple:

    el primer toque es valido  <=>  k_T > 0  Y  i_toque > k_T

o sea: **el precio se alejo `T` ticks ANTES de tocar por primera vez**. Es la
misma semantica de §3.1 -«el precio se aleja al menos T ticks y luego produce el
desenlace»- leida sobre la entrada primaria que fija la enmienda.

## Los dos ordenes, y por que se reportan los dos

    ORDEN A   decongestionar primero, exigir excursion a los supervivientes
    ORDEN B   filtrar por excursion primero, decongestionar ese subconjunto

**No dan lo mismo.** El greedy de `sep_min` conserva el PRIMERO de cada ventana
de 120 min, y ese primero puede ser justamente uno sin excursion valida,
suprimiendo a otro que si la tenia. El modulo no elige: emite los dos.

## Lo que este modulo NO hace

No adopta un orden. No adjudica H1. No recalcula el MDE. No mira outcomes ni
holdout. Prediccion registrada de antemano en
`docs/predictions/PRED-008_f_con_ambos_filtros.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, T_DESIGN,
    TZ_CHART, bars_mod, corte_del_sello, dias_research, git_head,
    huella_del_codigo, pd, ticks_mod,
)
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402
from edgelab.research.first_touch_decongestion import (  # noqa: E402
    FIRST_TOUCH_SEP_MINUTES, decongest_first_touch_events,
)
from edgelab.research.first_touch_population import (  # noqa: E402
    extract_first_touch_events,
)

SCHEMA_VERSION = "f_ambos_filtros_v1"
SALIDA = Path(__file__).resolve().parent / "f_ambos_filtros.json"
INDICADOR = "BigTrap2"


def k_excursion(px, lo_t, hi_t, i0, i1, T):
    """Indice relativo de la primera excursion de `T` ticks, bidireccional.

    `min(k_arriba, k_abajo)`, igual que `recuento_kT.eventos_kT`. `None` si el
    precio nunca se aleja `T` dentro del tramo.
    """
    if i1 <= i0:
        return None
    p = px[i0:i1]
    if not len(p):
        return None
    ku = int(np.searchsorted(np.maximum.accumulate(p), hi_t + T, side="left"))
    kd = int(np.searchsorted(-np.minimum.accumulate(p), -(lo_t - T), side="left"))
    cand = [k for k in (ku, kd) if k < len(p)]
    return min(cand) if cand else None


def medir(archivo, fechas, T):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())

    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / archivo),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    ts = np.asarray(tk.ts_ns)
    px = np.asarray(tk.price_ticks).astype(np.float64)
    sq = np.asarray(tk.sequence)
    if not bool((np.diff(sq) > 0).all()):
        return dict(estado="ABSTAIN", motivo="`sequence` no es orden total")

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    # Poblacion autoritativa: primeros toques, con la maquinaria que ya tiene
    # tests propios. No se reimplementa.
    eventos = extract_first_touch_events(r)
    setf = set(fechas)
    eventos = [e for e in eventos if session_date_ct(e["first_touch_ms"]) in setf]

    geo = {}
    for z in r.get("zones") or []:
        zid = z.get("id")
        if isinstance(zid, str) and zid and z.get("top") is not None:
            geo[zid] = z

    # Marcar cada evento con su condicion de excursion. NO se filtra todavia:
    # los dos ordenes necesitan el conjunto completo etiquetado.
    n_sin_geo = n_sin_tramo = 0
    for e in eventos:
        e["excursion_ok"] = False
        z = geo.get(e["zone_id"])
        if z is None:
            n_sin_geo += 1
            continue
        cb = e["created_bar"]
        if not (0 <= cb < len(bar_end)):
            n_sin_tramo += 1
            continue
        lo_t, hi_t = z["bottom"] / tk.tick_size, z["top"] / tk.tick_size
        disp = int(bar_end[int(cb)])          # BigTrap2 es bar_close
        i0 = int(np.searchsorted(ts, disp, side="right"))
        fin_ms = z.get("ended_ms")
        i1 = (int(np.searchsorted(ts, int(fin_ms) * 1_000_000, side="right"))
              if fin_ms else len(ts))
        i1 = min(i1, len(ts))
        k = k_excursion(px, lo_t, hi_t, i0, i1, T)
        if k is None or k == 0:
            continue
        # indice del primer toque, relativo al mismo origen `i0`
        i_toque = int(np.searchsorted(ts, int(e["first_touch_ms"]) * 1_000_000,
                                      side="left")) - i0
        # EL RETORNO TIENE QUE SER POSTERIOR A LA EXCURSION.
        e["excursion_ok"] = bool(i_toque > k)

    # ORDEN A: decongestionar todo, despues exigir excursion.
    dA = decongest_first_touch_events(eventos, session_date_of_ms=session_date_ct,
                                      sep_minutes=FIRST_TOUCH_SEP_MINUTES)
    a_sup = len(dA["events"])
    a_ambos = sum(1 for e in dA["events"] if e.get("excursion_ok"))

    # ORDEN B: exigir excursion, despues decongestionar ese subconjunto.
    con_exc = [e for e in eventos if e["excursion_ok"]]
    dB = decongest_first_touch_events(con_exc, session_date_of_ms=session_date_ct,
                                      sep_minutes=FIRST_TOUCH_SEP_MINUTES)
    b_ambos = len(dB["events"])

    # P4: orden temporal. `extract_first_touch_events` ya falla cerrado si
    # touch_bar <= created_bar; se recuenta para dejarlo publicado.
    viol = sum(1 for e in eventos
               if e["first_touch_bar"] <= e["created_bar"]
               or e["first_touch_ms"] <= e["created_ms"])

    return dict(estado="OK", sesiones=len(fechas),
                primeros_toques=len(eventos),
                con_excursion=len(con_exc),
                sep_supervivientes=a_sup,
                orden_A=a_ambos, orden_B=b_ambos,
                sin_geometria=n_sin_geo, sin_tramo=n_sin_tramo,
                violaciones_orden_temporal=viol)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=int, default=34)
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)
    print(f"universo: {ns} sesiones | max {peor} <= {MAX_FECHA} | {INDICADOR} "
          f"| T={a.T} | sep_min={FIRST_TOUCH_SEP_MINUTES}")

    crudo, tot = {}, dict(primeros_toques=0, con_excursion=0,
                          sep_supervivientes=0, orden_A=0, orden_B=0,
                          violaciones_orden_temporal=0)
    for arch, fechas in plan:
        print(f"== {arch} : {len(fechas)} sesiones", flush=True)
        res = medir(arch, fechas, a.T)
        crudo[arch] = res
        if res.get("estado") != "OK":
            print(f"   {res.get('estado')}: {res.get('motivo')}")
            continue
        for k in tot:
            tot[k] += res[k]
        print(f"   toques={res['primeros_toques']:>5}  c/excursion="
              f"{res['con_excursion']:>5}  post-sep={res['sep_supervivientes']:>4}"
              f"  A={res['orden_A']:>4}  B={res['orden_B']:>4}")

    fA, fB = tot["orden_A"] / ns, tot["orden_B"] / ns
    print(f"\n{'':<34}{'eventos':>9}{'/sesion':>10}")
    print(f"  {'primeros toques (crudo)':<32}{tot['primeros_toques']:>9}"
          f"{tot['primeros_toques'] / ns:>10.2f}")
    print(f"  {'solo sep_min':<32}{tot['sep_supervivientes']:>9}"
          f"{tot['sep_supervivientes'] / ns:>10.2f}")
    print(f"  {'solo excursion T=%d' % a.T:<32}{tot['con_excursion']:>9}"
          f"{tot['con_excursion'] / ns:>10.2f}")
    print(f"  {'AMBOS -- orden A':<32}{tot['orden_A']:>9}{fA:>10.2f}")
    print(f"  {'AMBOS -- orden B':<32}{tot['orden_B']:>9}{fB:>10.2f}")
    print(f"\n  violaciones de orden temporal: {tot['violaciones_orden_temporal']}"
          f"   (P4 exige 0)")

    payload = dict(
        schema_version=SCHEMA_VERSION,
        que_es="f con sep_min Y excursion valida -- cierra E-R1 v0.3 §9",
        prediccion_registrada="PRED-008: f_ambos < 3,0 ev/sesion, punto 1,2; "
                              "refutada si >= 3,0",
        indicador=INDICADOR, T=a.T, sep_minutes=FIRST_TOUCH_SEP_MINUTES,
        clase_kernel=CLASE_KERNEL.get(INDICADOR),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        universe_filter_report=info,
        outcomes_accessed=False,
        totales=tot,
        f_orden_A_por_sesion=round(fA, 4),
        f_orden_B_por_sesion=round(fB, 4),
        por_contrato=crudo)
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=2, default=str),
                           encoding="utf-8")
    print(f"\n-> {a.out}")
    print("EXIT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
