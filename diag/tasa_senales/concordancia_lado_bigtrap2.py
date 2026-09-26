"""Concordancia entre el lado atrapado de `BigTrap2` y el lado de la excursion.

## Por que existe este modulo

`recuento_kT.py` mide el evento **agnostico de direccion**: `k = min(ku, kd)`,
o sea el precio se aleja `T` ticks **hacia cualquier lado**, el que ocurra
primero. Verificado: ese modulo no menciona `kind`, `is_bull` ni `trapped`.

Pero `BigTrap2` tiene direccion nativa, y v0.3 §5.3 exige que su **traduccion
concreta** quede congelada en E-R1. Si esa traduccion resulta ser «solo cuenta
la excursion del lado que el atrapamiento predice», entonces el evento que H1
operaria **no es el que se conto**, y `f` hay que recalcularla.

Este modulo mide exactamente eso, **sin tocar outcomes**: la excursion y su lado
son geometria del setup, no resultado economico.

## La semantica de BigTrap2, leida del kernel

`bigtrap2.py:266` — *«Trapped buyers: agresion compradora que quedo por ENCIMA
del close»*: compraron caro y la barra cerro debajo. Son largos bajo el agua; la
zona queda **arriba** del precio y funciona como **resistencia**.

`bigtrap2.py:274` — *«Trapped sellers: agresion vendedora que quedo por DEBAJO
del close»*: vendieron barato y la barra cerro arriba. Son cortos bajo el agua;
la zona queda **abajo** y funciona como **soporte**.

    TRAMPA DE NOMENCLATURA, que hay que declarar en E-R1:
    `is_bull=True` -> `trapped_buyers` -> zona ARRIBA -> senal BAJISTA.
    El flag nombra QUIEN quedo atrapado, no la direccion de la operacion.

## Que se cuenta como concordante

    trapped_buyers  (resistencia arriba) -> excursion HACIA ARRIBA (ku)
    trapped_sellers (soporte abajo)      -> excursion HACIA ABAJO  (kd)

Es la lectura en la que el atrapamiento aporta informacion: el precio atraviesa
la zona por el lado donde estan los atrapados, y el retorno a la banda es la
operacion. **Es una lectura, no una derivacion** — el modulo la mide, no la
adopta.

## Lo que este modulo NO hace

No elige la traduccion. No adopta un `T`. No mira outcomes ni holdout. Emite los
conteos para que E-R1 se redacte con el numero delante en vez de con una
estimacion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, CLASE_KERNEL, LEAD_DAYS, MAX_FECHA, REGISTRY, T_DESIGN,
    TZ_CHART, bars_mod, corte_del_sello, dias_research, git_head,
    huella_del_codigo, pd, ticks_mod,
)

SCHEMA_VERSION = "concordancia_lado_v1"
SALIDA = Path(__file__).resolve().parent / "concordancia_lado_bigtrap2.json"
INDICADOR = "BigTrap2"


def lados_kT(px, lo_t, hi_t, i0, i1, umbrales):
    """Por umbral: `(k, lado, j)`.

    `lado` es `+1` si la primera excursion fue hacia ARRIBA (`px >= hi + T`),
    `-1` si fue hacia ABAJO (`px <= lo - T`). Empate exacto -mismo indice- se
    reporta como `0` y se cuenta aparte: no se rompe a favor de nadie.
    """
    if i1 <= i0:
        return None
    p = px[i0:i1]
    if not len(p):
        return None
    rmax = np.maximum.accumulate(p)
    rmin = np.minimum.accumulate(p)
    dentro = np.flatnonzero((p >= lo_t) & (p <= hi_t))

    out = {}
    for T in umbrales:
        ku = int(np.searchsorted(rmax, hi_t + T, side="left"))
        kd = int(np.searchsorted(-rmin, -(lo_t - T), side="left"))
        vu, vd = ku < len(p), kd < len(p)
        if not vu and not vd:
            out[T] = (None, None, None)
            continue
        if vu and vd:
            k, lado = (ku, 1) if ku < kd else ((kd, -1) if kd < ku else (ku, 0))
        elif vu:
            k, lado = ku, 1
        else:
            k, lado = kd, -1
        j = None
        if k > 0 and len(dentro):
            q = int(np.searchsorted(dentro, k, side="right"))
            if q < len(dentro):
                j = int(dentro[q])
        out[T] = (k, lado, j)
    return out


def medir(archivo, fechas, umbrales):
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
        return dict(estado="ABSTAIN",
                    motivo="`sequence` no es orden total: el orden intrabar no "
                           "es demostrable")

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None \
        else mod.run(tk, b, chart_tz=TZ_CHART)

    por_kind = Counter()
    # (T) -> Counter de categorias
    cat = {T: Counter() for T in umbrales}
    ret = {T: Counter() for T in umbrales}
    n_zonas = n_sin_kind = 0

    for z in r.get("zones") or []:
        if z.get("created_ms") is None or z.get("top") is None:
            continue
        cb = z.get("created_bar")
        if cb is None or not isinstance(cb, (int, np.integer)) \
                or cb < 0 or cb >= len(bar_end):
            continue
        kind = z.get("kind")
        if kind not in ("trapped_buyers", "trapped_sellers"):
            n_sin_kind += 1
            continue
        lo_t, hi_t = z["bottom"] / tk.tick_size, z["top"] / tk.tick_size
        disp = int(bar_end[int(cb)])          # BigTrap2 es bar_close
        i0 = int(np.searchsorted(ts, disp, side="right"))
        fin_ms = z.get("ended_ms")
        i1 = (int(np.searchsorted(ts, int(fin_ms) * 1_000_000, side="right"))
              if fin_ms else len(ts))
        res = lados_kT(px, lo_t, hi_t, i0, min(i1, len(ts)), umbrales)
        if res is None:
            continue
        n_zonas += 1
        por_kind[kind] += 1
        esperado = 1 if kind == "trapped_buyers" else -1
        for T in umbrales:
            k, lado, j = res[T]
            if k is None:
                cat[T]["nunca_se_aleja"] += 1
            elif k == 0:
                cat[T]["k_cero"] += 1
            elif lado == 0:
                cat[T]["empate_de_lado"] += 1
            elif lado == esperado:
                cat[T]["concordante"] += 1
                if j is not None:
                    ret[T]["concordante_con_retorno"] += 1
            else:
                cat[T]["discordante"] += 1
                if j is not None:
                    ret[T]["discordante_con_retorno"] += 1
    return dict(estado="OK", zonas=n_zonas, sin_kind=n_sin_kind,
                por_kind=dict(por_kind),
                categorias={str(T): dict(v) for T, v in cat.items()},
                retornos={str(T): dict(v) for T, v in ret.items()})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SALIDA))
    a = ap.parse_args(argv)

    dias, info = dias_research()
    # mismo armado que `recuento_kT.main()`: agrupar por contrato y ordenar.
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(arch, sorted(f)) for arch, f in sorted(por_arch.items())]
    peor = max(f for _a, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _a, fs in plan)
    print(f"universo: {ns} sesiones | max {peor} <= {MAX_FECHA} | {INDICADOR}")

    crudo, tot_cat, tot_ret, tot_kind = {}, Counter(), Counter(), Counter()
    n_zonas = 0
    for arch, fechas in plan:
        print(f"== {arch} : {len(fechas)} sesiones", flush=True)
        res = medir(arch, fechas, T_DESIGN)
        crudo[arch] = res
        if res.get("estado") != "OK":
            print(f"   {res.get('estado')}: {res.get('motivo')}")
            continue
        n_zonas += res["zonas"]
        tot_kind.update(res["por_kind"])
        for T, d in res["categorias"].items():
            for k, v in d.items():
                tot_cat[(T, k)] += v
        for T, d in res["retornos"].items():
            for k, v in d.items():
                tot_ret[(T, k)] += v
        print(f"   zonas={res['zonas']}  {dict(res['por_kind'])}")

    print(f"\nzonas totales: {n_zonas}   por lado: {dict(tot_kind)}")
    print("\nEXCURSIONES por T -- concordante = el precio sale por el lado del "
          "atrapamiento")
    hdr = "  T     concordante  discordante  empate   k_T==0  nunca_aleja"
    print(hdr)
    curva = {}
    for T in T_DESIGN:
        s = str(T)
        c = tot_cat[(s, "concordante")]
        d = tot_cat[(s, "discordante")]
        e = tot_cat[(s, "empate_de_lado")]
        z = tot_cat[(s, "k_cero")]
        n = tot_cat[(s, "nunca_se_aleja")]
        print(f"  {T:<4}{c:>12}{d:>13}{e:>8}{z:>9}{n:>13}")
        curva[s] = dict(concordante=c, discordante=d, empate=e, k_cero=z,
                        nunca_se_aleja=n,
                        concordante_con_retorno=tot_ret[(s, "concordante_con_retorno")],
                        discordante_con_retorno=tot_ret[(s, "discordante_con_retorno")],
                        f_agnostico_por_sesion=round((c + d + e) / ns, 3),
                        f_concordante_por_sesion=round(c / ns, 3))
    print("\n`f` POR SESION -- lo que cambia si E-R1 adopta la lectura concordante")
    print("  T      agnostico   concordante   cociente")
    for T in T_DESIGN:
        s = str(T)
        fa, fc = curva[s]["f_agnostico_por_sesion"], curva[s]["f_concordante_por_sesion"]
        q = f"{fc / fa:.3f}" if fa else "-"
        print(f"  {T:<5}{fa:>11}{fc:>14}{q:>11}")

    payload = dict(
        schema_version=SCHEMA_VERSION,
        que_es="concordancia lado atrapado vs lado de la excursion -- insumo de "
               "la traduccion direccional de v0.3 §5.3, NO la adopta",
        indicador=INDICADOR, umbrales=list(T_DESIGN),
        clase_kernel=CLASE_KERNEL.get(INDICADOR),
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        universe_filter_report=info,
        outcomes_accessed=False,
        zonas_totales=n_zonas, por_lado=dict(tot_kind),
        curva=curva, por_contrato=crudo)
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(payload, indent=2, default=str),
                           encoding="utf-8")
    print(f"\n-> {a.out}")
    print("EXIT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
