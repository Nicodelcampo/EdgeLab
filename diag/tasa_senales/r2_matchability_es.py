"""R2 - auditoria de matchability del control casi-zona. TARGET-FREE, SIN OUTCOMES.

QUE AUDITA
==========
H-ES-CRUCE-1 comparo 7.542 pares zona/casi-zona y concluyo delta pareada ~ 0. Pero el
18,3 % de las zonas (1.692) nunca consiguio control, y nadie miro quienes son. Si ese
grupo se concentra en una fase, un ancho o un regimen, el nulo agregado no representa a
esa subpoblacion y el estimando hay que redefinirlo o limitarlo.

R2 no mira que paso despues. Audita el EMPAREJAMIENTO.

EL EMPAREJAMIENTO REAL, TAL COMO CORRIO
=======================================
Reproducido de `velocidad_cruce_es.py`, sin idealizarlo:

  pool        casi-zonas de la misma sesion, agrupadas por ancho EXACTO en ticks
  orden       greedy, zonas en orden cronologico de creacion
  criterio    el candidato mas cercano en |delta t| -- valor ABSOLUTO, asi que el
              control puede ser POSTERIOR a la zona
  reemplazo   sin reemplazo: un control se usa una sola vez
  tope        |delta t| <= 30 min
  descarte    ademas se descarta si quedan < 200 ticks tras el fin del control

Las tres propiedades que mas pueden sesgar -- greedy, sin reemplazo, y control futuro
permitido -- se miden explicitamente en vez de asumirse inocuas.

EPISODIO Y SOLAPE: SOLO HISTORIA CAUSAL
=======================================
El censo de contextos conto solape con `abs(t_i - t_j) <= 30 min`, o sea que incluia
zonas creadas DESPUES. Para R2 eso seria una feature POST disfrazada. Aca `n_previas`,
`es_primera` y `solape_causal` usan unicamente eventos anteriores a t0.

SIN OUTCOMES. SIN HOLDOUT. Cero excursion, retorno, cruce o P&L.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import run_con_casi  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "r2_matchability_es_v1"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
CANONICAL_OUT = REPO / "docs" / "research" / "r2_matchability_es.json"
NY = ZoneInfo("America/New_York")

# Parametros del emparejamiento auditado. Son los de velocidad_cruce_es.py, no valores
# nuevos: si cambian alla, este audit deja de describir lo que corrio.
MAX_SEPARACION_MS = 30 * 60 * 1000
MIN_TICKS_POST = 200
VENTANA_PREV_MS = 5 * 60 * 1000
SEMILLA = 20260821

FASES = [("asia", 18, 3), ("europa", 3, 8), ("premarket", 8, 9.5),
         ("rth_am", 9.5, 12), ("rth_pm", 12, 16), ("cierre", 16, 18)]

# |SMD| < 0,10 es la REFERENCIA convencional de MatchIt, no un umbral de verdad.
SMD_REFERENCIA = 0.10


def fase_de(h):
    for nombre, ini, fin in FASES:
        if ini <= fin:
            if ini <= h < fin:
                return nombre
        elif h >= ini or h < fin:
            return nombre
    return "otro"


def hora_ny(ts_ns):
    d = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).astimezone(NY)
    return d.hour + d.minute / 60.0 + d.second / 3600.0


def make_run_id(head, claves, max_ses, snapshot_name=None):
    snapshot_name = snapshot_name or SNAPSHOT.name
    partes = [SCHEMA_VERSION, head, CONTRATO, snapshot_name, str(MAX_SEPARACION_MS),
              str(MIN_TICKS_POST), str(SEMILLA), str(max_ses),
              ",".join(str(t) for t in claves)]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def clasificar_run(max_ses, out_path):
    if not max_ses:
        return "full", True, None
    if pathlib.Path(out_path).resolve() == CANONICAL_OUT.resolve():
        return ("truncated_probe", False,
                "corrida truncada no puede sobrescribir %s" % CANONICAL_OUT)
    return "truncated_probe", False, None


# --------------------------------------------------------------------------
# Diagnosticos de balance
# --------------------------------------------------------------------------

def smd(a, b):
    """Standardized mean difference. Denominador: sd agrupada, como MatchIt."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return None
    s = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    if s == 0:
        return 0.0 if a.mean() == b.mean() else None
    return float((a.mean() - b.mean()) / s)


def ratio_varianza(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2 or b.var(ddof=1) == 0:
        return None
    return float(a.var(ddof=1) / b.var(ddof=1))


def ks_max(a, b):
    """Maxima diferencia eCDF (estadistico KS), sin scipy."""
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    if not len(a) or not len(b):
        return None
    todos = np.concatenate([a, b])
    ca = np.searchsorted(a, todos, side="right") / len(a)
    cb = np.searchsorted(b, todos, side="right") / len(b)
    return float(np.abs(ca - cb).max())


def balance(grupo_a, grupo_b, campos):
    out = {}
    for c in campos:
        va = [x[c] for x in grupo_a if x.get(c) is not None]
        vb = [x[c] for x in grupo_b if x.get(c) is not None]
        if not va or not vb:
            out[c] = {}
            continue
        out[c] = dict(
            n_a=len(va), n_b=len(vb),
            media_a=round(float(np.mean(va)), 4), media_b=round(float(np.mean(vb)), 4),
            smd=None if smd(va, vb) is None else round(smd(va, vb), 4),
            ratio_var=None if ratio_varianza(va, vb) is None
            else round(ratio_varianza(va, vb), 4),
            ks_max=None if ks_max(va, vb) is None else round(ks_max(va, vb), 4))
    return out


def frac_por(grupo, campo):
    if not grupo:
        return {}
    tot = len(grupo)
    g = {}
    for x in grupo:
        g[str(x[campo])] = g.get(str(x[campo]), 0) + 1
    return {k: round(v / tot, 4) for k, v in sorted(g.items())}


# --------------------------------------------------------------------------
# Emparejamiento: la MISMA logica que velocidad_cruce_es.py, parametrizada
# --------------------------------------------------------------------------

def emparejar(zonas, pool_por_ancho, con_reemplazo=False, orden=None,
              max_sep=MAX_SEPARACION_MS):
    """Greedy por ancho exacto. Devuelve {indice_zona: (indice_casi, delta_ms)}.

    `orden` permite reordenar las zonas para medir dependencia del orden (item 9).
    `con_reemplazo` permite medir cuanto del descarte lo causa el sin-reemplazo (item 7).
    """
    idx = list(range(len(zonas))) if orden is None else list(orden)
    usadas = set()
    res = {}
    for i in idx:
        z = zonas[i]
        cand = pool_por_ancho.get(z["ancho_ticks"], [])
        mejor, mejor_d, mejor_j = None, None, None
        for j, c in enumerate(cand):
            if (not con_reemplazo) and (z["ancho_ticks"], j) in usadas:
                continue
            d = abs(c["start_ts"] - z["start_ts"])      # ABSOLUTO: admite futuro
            if mejor_d is None or d < mejor_d:
                mejor, mejor_d, mejor_j = c, d, j
        if mejor is None or mejor_d > max_sep:
            res[i] = None
            continue
        if not con_reemplazo:
            usadas.add((z["ancho_ticks"], mejor_j))
        res[i] = (mejor_j, int(mejor["start_ts"] - z["start_ts"]))   # CON signo
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    # Rutas de datos por argumento: una corrida desde worktree apunta al arbol
    # principal SIN enlazar nada. El 2026-08-21 una junction de directorio dentro
    # de una worktree hizo que `git worktree remove --force` borrara 4 GB del
    # destino. Ver docs/incidents/INCIDENTE_JUNCTION_WORKTREE_2026-08-21.md
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--parquet", default=str(PARQUET))
    a = ap.parse_args()

    run_scope, publishable, err = clasificar_run(a.max_sesiones, a.out)
    if err:
        sys.exit("ABORTA: " + err)

    snapshot = pathlib.Path(a.snapshot)
    parquet = pathlib.Path(a.parquet)
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    zs = {}
    for f in con.execute(
            "SELECT id, start_ts, end_ts, bucket, dir, price_upper, price_lower, "
            "pasos, valid_steps, avg_ms, total_ms, total_vol, vol_rate "
            "FROM hft_zones WHERE instrument=? AND start_ts<? ORDER BY start_ts",
            (CONTRATO, CUTOFF_MS)):
        td = int(trade_date_ymd(np.array([f[1] * 1_000_000], dtype=np.int64))[0])
        zs.setdefault(td, []).append(f)
    con.close()

    universo = sorted(zs)
    claves = universo[:a.max_sesiones] if a.max_sesiones else list(universo)
    print("R2 matchability  -  %s" % SCHEMA_VERSION)
    print("  universo %d -> seleccionadas %d  (%s, publishable=%s)"
          % (len(universo), len(claves), run_scope, publishable))

    zonas_all, casi_all = [], []
    faltantes, excluidas_h0 = [], []
    por_sesion = []

    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(parquet, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError as e:
            faltantes.append(dict(trade_date=td, etapa="load", motivo=str(e)[:120]))
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        if len(ts) == 0:
            faltantes.append(dict(trade_date=td, etapa="ventana_vacia", motivo="0 ticks"))
            continue

        def covar(start_ts, end_ts, lo, hi, previos_ts, previos_lohi):
            """Covariables PRE/AT_EVENT. `previos_*` son SOLO eventos anteriores."""
            j = int(np.searchsorted(ts, start_ts * 1_000_000, side="left"))
            j0 = int(np.searchsorted(ts, start_ts * 1_000_000
                                     - VENTANA_PREV_MS * 1_000_000))
            prev = pxt[j0:j]
            hasta = pxt[:max(j, 1)]
            d_lo, d_hi = int(hasta.min()), int(hasta.max())
            rango_prev = float(prev.max() - prev.min()) if len(prev) else 0.0
            ret_prev = float(prev[-1] - prev[0]) if len(prev) > 1 else 0.0
            # episodio CAUSAL: solo lo anterior
            n_prev = len(previos_ts)
            t_desde = (start_ts - previos_ts[-1]) if n_prev else None
            solape = sum(1 for (a_, b_) in previos_lohi if lo <= b_ and a_ <= hi)
            return dict(
                ancho_ticks=hi - lo,
                fase=fase_de(hora_ny(start_ts * 1_000_000)),
                minuto_sesion=round((start_ts * 1_000_000 - ini) / 6e10, 1),
                ticks_prev_5min=int(j - j0),
                rango_prev_5min=round(rango_prev, 1),
                ret_prev_5min_abs=round(abs(ret_prev), 1),
                ret_prev_5min_signed=round(ret_prev, 1),
                rango_dia_hasta_t0=int(d_hi - d_lo),
                pos_en_rango=round(float(((hi + lo) / 2.0 - d_lo)
                                         / max(d_hi - d_lo, 1)), 4),
                n_previas_causal=n_prev,
                es_primera=bool(n_prev == 0),
                t_desde_previa_ms=t_desde,
                solape_causal=solape,
                ticks_post=int(len(ts) - int(np.searchsorted(
                    ts, (end_ts or start_ts) * 1_000_000, side="right"))))

        # --- zonas del oraculo ------------------------------------------------
        zl, prev_ts, prev_lohi = [], [], []
        for (zid, st, en, bucket, dr, pu, pl, pas, vst, ams, tms, tvol, vr) in zs[td]:
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            if hi - lo <= 0:
                excluidas_h0.append(dict(trade_date=td, id=zid, motivo="altura 0"))
                continue
            c = covar(st, en, lo, hi, prev_ts, prev_lohi)
            c.update(trade_date=td, id=zid, start_ts=st, end_ts=en, dir=int(dr),
                     tipo=bucket, es_sweep=bool(bucket != "Absorb"),
                     pasos=pas, valid_steps=vst, avg_ms=ams, total_ms=tms,
                     total_vol=tvol, vol_rate=vr, grupo="zona")
            zl.append(c)
            prev_ts.append(st)
            prev_lohi.append((lo, hi))

        # --- casi-zonas del puerto -------------------------------------------
        _z, casi = run_con_casi(ts, pxt * tsz, vol, tsz)
        cl, cprev_ts, cprev_lohi = [], [], []
        for c0 in casi:
            hi = int(round(c0["price_upper"] / tsz))
            lo = int(round(c0["price_lower"] / tsz))
            if hi - lo <= 0:
                continue
            c = covar(c0["start_ts"], c0["end_ts"], lo, hi, cprev_ts, cprev_lohi)
            c.update(trade_date=td, start_ts=c0["start_ts"], end_ts=c0["end_ts"],
                     dir=int(c0["dir"]), tipo="casi", es_sweep=None,
                     pasos=c0["pasos"], valid_steps=c0["valid_steps"],
                     avg_ms=c0["avg_ms"], total_ms=c0["total_ms"],
                     total_vol=c0["total_vol"], vol_rate=c0["vol_rate"],
                     motivo=c0["motivo"], grupo="casi")
            cl.append(c)
            cprev_ts.append(c0["start_ts"])
            cprev_lohi.append((lo, hi))

        # --- emparejamiento base, identico al que corrio ----------------------
        pool = {}
        for j, c in enumerate(cl):
            pool.setdefault(c["ancho_ticks"], []).append(c)
        m_base = emparejar(zl, pool)

        # item 4: candidatos por zona (soporte comun por ancho)
        for i, z in enumerate(zl):
            cand = pool.get(z["ancho_ticks"], [])
            z["n_candidatos_ancho"] = len(cand)
            r = m_base[i]
            z["matched"] = r is not None
            z["delta_control_ms"] = r[1] if r else None
            z["control_es_futuro"] = (r[1] > 0) if r else None
            z["sin_soporte_ancho"] = len(cand) == 0

        # item 7/8: con reemplazo y reutilizacion
        m_rep = emparejar(zl, pool, con_reemplazo=True)
        uso = {}
        for i, r in m_rep.items():
            if r:
                uso[(zl[i]["ancho_ticks"], r[0])] = uso.get(
                    (zl[i]["ancho_ticks"], r[0]), 0) + 1

        # item 9: dependencia del orden
        rng = np.random.default_rng(SEMILLA + td)
        m_rev = emparejar(zl, pool, orden=list(range(len(zl)))[::-1])
        m_rnd = emparejar(zl, pool, orden=rng.permutation(len(zl)).tolist())
        difiere_rev = sum(1 for i in m_base
                          if (m_base[i] is None) != (m_rev[i] is None)
                          or (m_base[i] and m_rev[i] and m_base[i][0] != m_rev[i][0]))
        difiere_rnd = sum(1 for i in m_base
                          if (m_base[i] is None) != (m_rnd[i] is None)
                          or (m_base[i] and m_rnd[i] and m_base[i][0] != m_rnd[i][0]))

        por_sesion.append(dict(
            trade_date=td, n_zonas=len(zl), n_casi=len(cl),
            n_matched=sum(1 for i in m_base if m_base[i]),
            n_matched_con_reemplazo=sum(1 for i in m_rep if m_rep[i]),
            max_reutilizacion=max(uso.values()) if uso else 0,
            difiere_orden_inverso=difiere_rev,
            difiere_orden_aleatorio=difiere_rnd))
        zonas_all.extend(zl)
        casi_all.extend(cl)
        if (k + 1) % 10 == 0:
            print("    %d/%d  zonas %d  casi %d" % (k + 1, len(claves),
                                                    len(zonas_all), len(casi_all)))

    print("  %d zonas, %d casi-zonas, %d sesiones"
          % (len(zonas_all), len(casi_all), len(por_sesion)))

    # ---------------------------------------------------------------- agregados
    matched = [z for z in zonas_all if z["matched"]]
    unmatched = [z for z in zonas_all if not z["matched"]]
    CAMPOS = ["ancho_ticks", "pasos", "valid_steps", "avg_ms", "total_ms", "total_vol",
              "vol_rate", "ticks_prev_5min", "rango_prev_5min", "ret_prev_5min_abs",
              "ret_prev_5min_signed", "rango_dia_hasta_t0", "pos_en_rango",
              "n_previas_causal", "solape_causal", "minuto_sesion", "n_candidatos_ancho"]

    controles = [c for c in casi_all]
    campos_par = [c for c in CAMPOS if c != "n_candidatos_ancho"]

    sep = [abs(z["delta_control_ms"]) for z in matched]
    futuros = [z for z in matched if z["control_es_futuro"]]
    reut = [s["max_reutilizacion"] for s in por_sesion]

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]

    out = dict(
        schema_version=SCHEMA_VERSION,
        run_id=make_run_id(head, claves, a.max_sesiones, snapshot.name),
        run_scope=run_scope, publishable=publishable, max_sesiones_arg=a.max_sesiones,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        proposito=("auditar el emparejamiento zona/casi-zona de H-ES-CRUCE-1. No mira "
                   "que paso despues de ninguno de los dos"),
        emparejamiento_auditado=dict(
            pool="casi-zonas de la misma sesion agrupadas por ancho EXACTO",
            orden="greedy, zonas en orden cronologico",
            criterio="candidato mas cercano en |delta t| (ABSOLUTO: admite control futuro)",
            reemplazo="sin reemplazo",
            tope_ms=MAX_SEPARACION_MS, min_ticks_post=MIN_TICKS_POST,
            nota_fuente="reproducido de diag/tasa_senales/velocidad_cruce_es.py"),
        conteos=dict(
            n_universe_discovered=len(universo), n_selected=len(claves),
            n_available=len(claves) - len(faltantes), n_processed=len(por_sesion),
            n_zonas=len(zonas_all), n_zonas_altura0_excluidas=len(excluidas_h0),
            n_casi=len(casi_all),
            n_matched=len(matched), n_unmatched=len(unmatched),
            match_rate=round(len(matched) / len(zonas_all), 4) if zonas_all else None),
        missing_items=faltantes,
        excluded_items=excluidas_h0[:50],
        n_excluded_total=len(excluidas_h0),
        montecarlo=dict(seed=SEMILLA, method="sin remuestreo; auditoria determinista"),

        # --- 1-2: matched vs unmatched ---------------------------------------
        matched_vs_unmatched=dict(
            population_id="P_ZONAS", numerator="zonas con control",
            denominator="zonas con ancho > 0",
            fase=dict(matched=frac_por(matched, "fase"),
                      unmatched=frac_por(unmatched, "fase")),
            tipo=dict(matched=frac_por(matched, "tipo"),
                      unmatched=frac_por(unmatched, "tipo")),
            direccion=dict(matched=frac_por(matched, "dir"),
                           unmatched=frac_por(unmatched, "dir")),
            balance=balance(matched, unmatched, CAMPOS),
            smd_referencia=SMD_REFERENCIA,
            campos_fuera_de_referencia=sorted(
                c for c, v in balance(matched, unmatched, CAMPOS).items()
                if v.get("smd") is not None and abs(v["smd"]) >= SMD_REFERENCIA)),

        # --- 3: soporte comun -------------------------------------------------
        soporte_comun=dict(
            zonas_sin_candidato_de_su_ancho=sum(1 for z in zonas_all
                                                if z["sin_soporte_ancho"]),
            frac=round(sum(1 for z in zonas_all if z["sin_soporte_ancho"])
                       / len(zonas_all), 4) if zonas_all else None,
            candidatos_por_zona=dict(
                p05=int(np.percentile([z["n_candidatos_ancho"] for z in zonas_all], 5)),
                p50=int(np.median([z["n_candidatos_ancho"] for z in zonas_all])),
                p95=int(np.percentile([z["n_candidatos_ancho"] for z in zonas_all], 95)))
            if zonas_all else {}),

        # --- 4-5: balance del par y separacion temporal ------------------------
        balance_par=dict(
            antes=balance(zonas_all, casi_all, campos_par),
            despues=balance(matched, controles, campos_par),
            nota=("'antes' compara TODAS las zonas contra TODAS las casi-zonas; "
                  "'despues' compara las emparejadas contra el pool de controles")),
        separacion_temporal=dict(
            p05=int(np.percentile(sep, 5)), p50=int(np.median(sep)),
            p95=int(np.percentile(sep, 95)), maximo=int(max(sep)),
            frac_control_futuro=round(len(futuros) / len(matched), 4),
            nota=("el criterio usa |delta t|, asi que admite controles POSTERIORES a la "
                  "zona. Target-free no lo invalida -- cada banda se mide hacia adelante "
                  "desde SU creacion -- pero hay que declararlo")) if matched else {},

        # --- 6-8: reemplazo, reutilizacion, orden ------------------------------
        reemplazo=dict(
            n_matched_sin_reemplazo=len(matched),
            n_matched_con_reemplazo=sum(s["n_matched_con_reemplazo"]
                                        for s in por_sesion),
            ganancia_por_reemplazo=sum(s["n_matched_con_reemplazo"]
                                       for s in por_sesion) - len(matched),
            max_reutilizacion_p50=int(np.median(reut)) if reut else None,
            max_reutilizacion_max=int(max(reut)) if reut else None),
        dependencia_del_orden=dict(
            difiere_orden_inverso=sum(s["difiere_orden_inverso"] for s in por_sesion),
            difiere_orden_aleatorio=sum(s["difiere_orden_aleatorio"]
                                        for s in por_sesion),
            frac_inverso=round(sum(s["difiere_orden_inverso"] for s in por_sesion)
                               / len(zonas_all), 4) if zonas_all else None,
            frac_aleatorio=round(sum(s["difiere_orden_aleatorio"] for s in por_sesion)
                                 / len(zonas_all), 4) if zonas_all else None,
            nota="greedy: un orden distinto puede asignar controles distintos"),

        # --- 9-10: cobertura --------------------------------------------------
        cobertura=dict(
            por_sesion=dict(
                p05=round(float(np.percentile([s["n_matched"] / max(s["n_zonas"], 1)
                                               for s in por_sesion], 5)), 4),
                p50=round(float(np.median([s["n_matched"] / max(s["n_zonas"], 1)
                                           for s in por_sesion])), 4),
                p95=round(float(np.percentile([s["n_matched"] / max(s["n_zonas"], 1)
                                               for s in por_sesion], 95)), 4)),
            por_fase={f: round(sum(1 for z in zonas_all
                                   if z["fase"] == f and z["matched"])
                               / max(sum(1 for z in zonas_all if z["fase"] == f), 1), 4)
                      for f in sorted({z["fase"] for z in zonas_all})},
            por_ancho={str(w): round(sum(1 for z in zonas_all
                                         if z["ancho_ticks"] == w and z["matched"])
                                     / max(sum(1 for z in zonas_all
                                               if z["ancho_ticks"] == w), 1), 4)
                       for w in sorted({z["ancho_ticks"] for z in zonas_all})[:20]}),
        procedencia=dict(head_commit=head, arbol_limpio=not bool(sucios),
                         archivos_sucios=sorted(sucios), snapshot=str(snapshot),
                         parquet=str(parquet), contrato=CONTRATO,
                         comando=" ".join(sys.argv)),
        sesiones=por_sesion)

    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    c = out["conteos"]
    print("\n  match rate %.4f   (%d de %d)   sin soporte de ancho: %d"
          % (c["match_rate"], c["n_matched"], c["n_zonas"],
             out["soporte_comun"]["zonas_sin_candidato_de_su_ancho"]))
    print("  fuera de |SMD| < %.2f : %s" % (SMD_REFERENCIA,
                                            out["matched_vs_unmatched"]
                                            ["campos_fuera_de_referencia"] or "ninguno"))
    if matched:
        st = out["separacion_temporal"]
        print("  separacion |dt| ms  p50 %d  p95 %d   control futuro %.3f"
              % (st["p50"], st["p95"], st["frac_control_futuro"]))
    print("  orden: difiere inverso %.4f  aleatorio %.4f"
          % (out["dependencia_del_orden"]["frac_inverso"],
             out["dependencia_del_orden"]["frac_aleatorio"]))
    print("  cobertura por fase: %s" % out["cobertura"]["por_fase"])
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
