# -*- coding: utf-8 -*-
"""F1.2 + F1.3 — supervivencia de la zona con riesgos competitivos, y depleción
por índice de toque. **Todo target-free.**

## Por qué las dos juntas

Las dos salen del **mismo paso del kernel** y de las mismas dos fuentes: el dict
de zonas y las filas de eventos. Correrlas por separado significaría dos caminos
que computan lo mismo y que después divergen — que es exactamente cómo nació el
sesgo que este plan repara.

## F1.3 — depleción por índice de toque

El censo F0.2 encontró que de **48.768 eventos de toque**, H1 midió sólo los
primeros (**32 %**). Los otros 33.160 nunca se miraron.

El kernel emite `ZONE_TOUCHED` con su **ordinal** (`touch_count`) y su barra, y
`ZONE_INVALIDATED` con su razón y su barra. Cruzándolos por `(zone_id, barra)` se
obtiene, para cada ordinal `k`, **qué fracción de los toques nº k rompió el nivel
en esa misma barra**. Eso es la tasa ruptura-vs-rebote por índice de toque, sin
leer un solo precio y sin ninguna regla de trade.

La literatura predice que la probabilidad de rebote **sube con los toques
previos** y **decae con el tiempo**. H1 midió exclusivamente el toque nº 1 — el
caso virgen, el más propenso a romper. Acá se ve si eso es cierto en estos datos.

## F1.2 — supervivencia con riesgos competitivos

La vida de una zona **es** un problema de supervivencia: nace y muere por
`close_through`, `close_through_gap`, `max_age` o `max_touches`, o queda
**censurada** por seguir activa al final de los datos. Tratar una sola causa como
evento y censurar el resto **sesga el hazard** — por eso se estima la **función
de incidencia acumulada** (Aalen-Johansen) por causa, no un Kaplan-Meier por
causa.

### Sustitución declarada: estratificación en vez de Cox

El plan v2 pedía un Cox. `lifelines` **no está en el lock**, y CLAUDE.md prohíbe
dependencias pesadas nuevas. En vez de traer una dependencia se estima el hazard
**estratificado por cuantil de covariable**, que además es más transparente: se
ve la curva completa de cada estrato en vez de un coeficiente. Se declara como
desviación del plan, no se disimula.

**Y ya se sabe que la covariable estrella del plan no tiene rango:** F0.2 midió
altura mediana **1 tick**, p90 **2 ticks**. Se estratifica igual para dejarlo
medido en vez de argumentado.

## Lo que NO hace

No lee un precio posterior a ningún evento para juzgarlo económicamente. No
calcula P&L. No adjudica ninguna hipótesis. No toca el holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.censo_zonas_completo import resumen, vol_por_zona  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F1_supervivencia_depletion_v1"
INDICADOR = "BigTrap2"

#: Ordinales de toque que se publican uno por uno. Más allá, agregado.
ORDINALES = 10
#: Horizonte en barras de las curvas de supervivencia publicadas.
HORIZONTE = 120


def aalen_johansen(tiempos, causas, censura, horizonte):
    """Supervivencia global e incidencia acumulada por causa.

    `tiempos`: duración en barras. `causas`: etiqueta de causa por sujeto.
    `censura`: booleano, True = censurado (sin evento observado).

    Con riesgos competitivos, `1 - KM` de una causa **sobreestima** su incidencia
    porque trata las otras causas como censura informativa. La CIF es el objeto
    correcto: CIF_c(t) = sum_{s<=t} S(s-) * h_c(s).
    """
    t = np.asarray(tiempos, dtype=np.int64)
    cen = np.asarray(censura, dtype=bool)
    causas = np.asarray(causas, dtype=object)
    etiquetas = sorted({str(c) for c, k in zip(causas, cen) if not k})

    orden = np.argsort(t, kind="stable")
    t, cen, causas = t[orden], cen[orden], causas[orden]
    n = len(t)

    S = 1.0
    cif = {c: 0.0 for c in etiquetas}
    curva_S, curva_cif = {}, {c: {} for c in etiquetas}
    i = 0
    en_riesgo = n
    while i < n:
        ti = int(t[i])
        j = i
        while j < n and int(t[j]) == ti:
            j += 1
        eventos = ~cen[i:j]
        d_total = int(eventos.sum())
        if d_total and en_riesgo > 0:
            S_previo = S
            for c in etiquetas:
                d_c = int(((causas[i:j] == c) & eventos).sum())
                if d_c:
                    cif[c] += S_previo * (d_c / en_riesgo)
            S = S * (1.0 - d_total / en_riesgo)
        if ti <= horizonte:
            curva_S[ti] = round(S, 6)
            for c in etiquetas:
                curva_cif[c][ti] = round(cif[c], 6)
        en_riesgo -= (j - i)
        i = j
    return dict(supervivencia=curva_S, incidencia_acumulada=curva_cif,
                cif_final={c: round(v, 6) for c, v in cif.items()},
                n=n, censurados=int(cen.sum()))


def estratificar(filas, campo, n_estratos=3):
    """Hazard estratificado por cuantil de una covariable. Sustituye al Cox."""
    v = np.array([f[campo] for f in filas if f[campo] is not None], dtype=np.float64)
    if v.size < n_estratos * 10 or len(np.unique(v)) < 2:
        return dict(estado="SIN_RANGO", motivo="la covariable no tiene variacion "
                    "suficiente para estratificar", valores_unicos=int(len(np.unique(v))),
                    resumen=resumen(v.tolist()))
    cortes = [float(np.percentile(v, q)) for q in
              [100 * k / n_estratos for k in range(1, n_estratos)]]
    out = {}
    for k in range(n_estratos):
        lo = -np.inf if k == 0 else cortes[k - 1]
        hi = np.inf if k == n_estratos - 1 else cortes[k]
        sub = [f for f in filas if f[campo] is not None
               and (f[campo] > lo or k == 0) and f[campo] <= hi]
        if not sub:
            continue
        vidas = [f["vida_barras"] for f in sub if f["vida_barras"] is not None]
        rotas = sum(1 for f in sub if f["causa"] in ("close_through", "close_through_gap"))
        out["q%d" % (k + 1)] = dict(
            rango=[None if lo == -np.inf else round(lo, 4),
                   None if hi == np.inf else round(hi, 4)],
            n=len(sub), frac_rota=round(rotas / len(sub), 4),
            vida_barras=resumen(vidas),
            toques=resumen([f["toques"] for f in sub]))
    return dict(estado="OK", cortes=[round(c, 4) for c in cortes], estratos=out)


def medir(arch, fechas, params):
    ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
           - pd.Timedelta(days=LEAD_DAYS))
    fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                    + pd.Timedelta(days=1))
    fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
    tk = ticks_mod.load_canonical_parquet(
        str(REPO_PATH / "data" / "nt8" / "6E" / arch),
        start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
    if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
        return dict(estado="ABSTAIN", motivo="`sequence` no es orden total")

    b = bars_mod.build_time_bars(tk, 1)
    bar_end = np.asarray(b.end_ns)
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = (mod.run(tk, b, fp, params=params, chart_tz=TZ_CHART) if fp is not None
         else mod.run(tk, b, params=params, chart_tz=TZ_CHART))

    vols = vol_por_zona(r.get("csv_lines") or [])
    setf = set(fechas)

    # --- filas por zona (F1.2) -------------------------------------------
    filas, en_calendario = [], set()
    for z in r.get("zones") or []:
        if z.get("top") is None or z.get("created_ms") is None:
            continue
        if session_date_ct(int(z["created_ms"])) not in setf:
            continue           # nacio en el lead-in
        zid = z["id"]
        en_calendario.add(zid)
        cb = int(z["created_bar"])
        fin_ms = z.get("ended_ms")
        vida = None
        if fin_ms is not None and 0 <= cb < len(bar_end):
            bf = int(np.searchsorted(bar_end, int(fin_ms) * 1_000_000, side="left"))
            if bf >= cb:
                vida = bf - cb
        filas.append(dict(
            zone_id=zid, causa=str(z.get("end_reason")),
            censurado=(z.get("end_reason") is None),
            vida_barras=vida, toques=int(z.get("touches") or 0),
            altura_ticks=(float(z["top"]) - float(z["bottom"])) / tk.tick_size,
            volumen=vols.get(zid), created_bar=cb))

    # --- F1.3: toques con su ordinal, y si rompieron en esa misma barra ---
    # El kernel evalua touched y adverse_close en la MISMA iteracion de barra:
    # un toque que rompe emite ZONE_TOUCHED y ZONE_INVALIDATED con el mismo
    # bar_index. Cruzar por (zone_id, barra) es exacto, no una aproximacion.
    muerte_en_barra = {}
    for ev in r.get("events") or []:
        if ev.get("type") == "ZONE_INVALIDATED":
            muerte_en_barra[(ev.get("zone_id"), int(ev["bar_index"]))] = \
                ev.get("reason") or "?"

    por_ordinal = defaultdict(lambda: dict(n=0, rompio=0))
    for ev in r.get("events") or []:
        if ev.get("type") != "ZONE_TOUCHED":
            continue
        zid = ev.get("zone_id")
        if zid not in en_calendario:
            continue
        k = int(ev.get("touch_count") or 0)
        d = por_ordinal[k]
        d["n"] += 1
        if (zid, int(ev["bar_index"])) in muerte_en_barra:
            d["rompio"] += 1

    return dict(estado="OK", sesiones=len(fechas), filas=filas,
                por_ordinal={str(k): dict(v) for k, v in sorted(por_ordinal.items())},
                tick_size=tk.tick_size)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", default="{}", help="JSON de overrides del kernel")
    ap.add_argument("--nombre", default="defaults")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2
    params = json.loads(a.params)

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns = sum(len(fs) for _x, fs in plan)

    print("F1.2 SUPERVIVENCIA (riesgos competitivos) + F1.3 DEPLECION POR TOQUE")
    print("  universo %d sesiones | celda %s | params %s"
          % (ns, a.nombre, json.dumps(params, sort_keys=True)))

    filas, ordinales, crudo = [], Counter(), {}
    rompio = Counter()
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        res = medir(arch, fechas, params)
        if res.get("estado") != "OK":
            crudo[arch] = res
            print("   %s: %s" % (res["estado"], res.get("motivo")))
            continue
        filas.extend(res["filas"])
        for k, v in res["por_ordinal"].items():
            ordinales[int(k)] += v["n"]
            rompio[int(k)] += v["rompio"]
        crudo[arch] = dict(estado="OK", sesiones=res["sesiones"],
                           zonas=len(res["filas"]))
        print("   zonas=%d  toques=%d" % (len(res["filas"]),
                                          sum(v["n"] for v in res["por_ordinal"].values())))

    # ---------------- F1.3 ----------------
    print("\n" + "=" * 70)
    print("F1.3  DEPLECION POR INDICE DE TOQUE")
    print("  la literatura predice que la ruptura BAJA con los toques previos")
    print("\n  %-9s %9s %9s %9s" % ("ordinal", "toques", "rompio", "tasa"))
    dep = {}
    for k in sorted(ordinales):
        if k > ORDINALES:
            break
        n, rr = ordinales[k], rompio[k]
        dep[str(k)] = dict(n=n, rompio=rr, tasa=round(rr / n, 4) if n else None)
        print("  %-9d %9d %9d %8.1f%%" % (k, n, rr, 100 * rr / n if n else 0))
    cola_n = sum(v for k, v in ordinales.items() if k > ORDINALES)
    cola_r = sum(v for k, v in rompio.items() if k > ORDINALES)
    if cola_n:
        dep[">%d" % ORDINALES] = dict(n=cola_n, rompio=cola_r,
                                      tasa=round(cola_r / cola_n, 4))
        print("  %-9s %9d %9d %8.1f%%" % (">%d" % ORDINALES, cola_n, cola_r,
                                          100 * cola_r / cola_n))
    tot_n, tot_r = sum(ordinales.values()), sum(rompio.values())
    print("  %-9s %9d %9d %8.1f%%" % ("TOTAL", tot_n, tot_r,
                                      100 * tot_r / tot_n if tot_n else 0))

    # ---------------- F1.2 ----------------
    obs = [f for f in filas if f["vida_barras"] is not None or f["censurado"]]
    tiempos = [(f["vida_barras"] if f["vida_barras"] is not None else HORIZONTE)
               for f in obs]
    aj = aalen_johansen(tiempos, [f["causa"] for f in obs],
                        [f["censurado"] for f in obs], HORIZONTE)

    print("\n" + "=" * 70)
    print("F1.2  SUPERVIVENCIA CON RIESGOS COMPETITIVOS")
    print("  zonas %d   censuradas %d" % (aj["n"], aj["censurados"]))
    print("\n  incidencia acumulada por causa (final):")
    for c, v in sorted(aj["cif_final"].items(), key=lambda kv: -kv[1]):
        print("    %-20s %.4f" % (c, v))
    print("\n  supervivencia de la zona (fraccion viva a las N barras):")
    for t in (1, 2, 5, 10, 20, 60, 120):
        s = aj["supervivencia"].get(t)
        if s is None:
            ks = [k for k in aj["supervivencia"] if k <= t]
            s = aj["supervivencia"][max(ks)] if ks else 1.0
        print("    %4d barras   %.4f" % (t, s))

    estratos = {}
    for campo in ("altura_ticks", "volumen", "toques"):
        estratos[campo] = estratificar(filas, campo)
        e = estratos[campo]
        print("\n  estratificado por %s: %s" % (campo, e["estado"]))
        if e["estado"] != "OK":
            print("    %s (valores unicos: %d)" % (e["motivo"], e["valores_unicos"]))
            continue
        for q, d in sorted(e["estratos"].items()):
            print("    %-4s rango %-22s n=%5d  rota %.3f  vida med %6.1f"
                  % (q, str(d["rango"]), d["n"], d["frac_rota"],
                     (d["vida_barras"] or {}).get("p50", float("nan"))))

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.2+F1.3",
        plan="docs/PLAN_ANALISIS_v2_2026-08-10.md",
        celda=a.nombre, params=params,
        desviacion_declarada="el plan pedia un Cox; `lifelines` no esta en el "
                             "lock y CLAUDE.md prohibe dependencias pesadas "
                             "nuevas. Se estratifica por cuantil de covariable, "
                             "que ademas publica la curva completa de cada "
                             "estrato en vez de un coeficiente.",
        session_count=ns, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()),
        universe_filter_report=info, outcomes_accessed=False,
        depletion_por_ordinal=dep,
        depletion_total=dict(n=tot_n, rompio=tot_r,
                             tasa=round(tot_r / tot_n, 4) if tot_n else None),
        supervivencia=aj, estratificacion=estratos,
        horizonte_barras=HORIZONTE, por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        .encode()).hexdigest()
    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1_superv_depletion__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str)
                      + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
