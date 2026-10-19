"""Atlas target-free de eventos HFT sobre ES — F1 del embudo. SIN OUTCOMES.

QUE ES
======
Una tabla inmutable y reutilizable, una fila por evento, con las features de la whitelist
del registry (`hft_es_context_feature_registry_2026-08-20.json`). Se construye UNA vez y
sirve para muchas preguntas posteriores (ATJ: atlas target-free construido una sola vez).

LAS TRES POBLACIONES, CON LAS MISMAS COLUMNAS
=============================================
Precision 4 del auditor: si el atlas sólo tuviera filas HFT, los controles entrarian
DESPUES de ver outcomes -- justo el error que todo el diseno intenta evitar.

  ZONA        zona real del oraculo Flat
  CASI        casi-zona: racha que fallo EXACTAMENTE UNO de los cuatro filtros
  S1_1MIN     barra extrema generica, SIN exigir que sea zona ni casi-zona

Las tres reciben identicas columnas de regimen y geometria, ahora, antes de que exista
ningun outcome.

S1 NO SE TRANSPORTA DE F2.9
===========================
F2.9 midio S1 sobre 6E con su propia especificacion de barra. Aca se define sobre barras
de 1 MINUTO y se llama `S1_1MIN` para no confundirlos. Criterio declarado:
rango >= 3 ticks, mecha superior o inferior >= 30% del rango, volumen >= mediana de la
sesion. Es una definicion nueva sobre ES, no un resultado heredado.

NORMALIZACION EXPANSIVA, NUNCA FULL-SAMPLE
==========================================
El registry lo exige: los percentiles no pueden usar observaciones futuras. Cada
percentil se calcula contra el historial ACUMULADO de su mismo bucket horario hasta el
evento, procesando las sesiones en orden cronologico. Un percentil full-sample seria
comodo y no seria live-compatible.

DISPONIBILIDAD CAUSAL
=====================
Cada columna lleva PRE o AT_EVENT. No hay columnas POST: no hay excursion, retorno,
cruce, MAE/MFE ni P&L. `scheduled_news` (F06) NO se implementa: hace falta calendario
oficial y todavia no existe en el repo. Se declara NOT_AVAILABLE en vez de inventarse.

SALIDA
======
Parquet por evento en `data/atlas/` (gitignorado, es dato) + JSON agregado versionado con
esquema, conteos, denominadores y sha256 del parquet.
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

from diag.tasa_senales.r2_matchability_es import fase_de  # noqa: E402
from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import run_con_casi  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "atlas_hft_es_v1_target_free"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CONTRATO = "ES 03-26"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
CANONICAL_OUT = REPO / "docs" / "research" / "atlas_hft_es.json"
DIR_ATLAS = REPO / "data" / "atlas"
NY = ZoneInfo("America/New_York")

VENTANA_PREV_MS = 5 * 60 * 1000
BUCKET_MIN = 15                  # bucket horario para la normalizacion expansiva
S1_MIN_RANGO_TICKS = 3
S1_MECHA_FRAC = 0.30
SEED = 20260821

# Columnas y su disponibilidad causal (D-HFT-CTX-02). Ninguna es POST.
DISPONIBILIDAD = {
    "session_phase": "PRE", "minuto_sesion": "PRE", "bucket_15m": "PRE",
    "tick_rate_5m": "PRE", "vol_rate_5m": "PRE", "intertick_mediano_ms": "PRE",
    "cambios_precio_5m": "PRE", "rango_prev_5m": "PRE", "path_prev_5m": "PRE",
    "rv_prev_5m": "PRE", "ret_prev_5m_signed": "PRE", "ret_prev_5m_abs": "PRE",
    "trend_score": "PRE", "illiq_amihud_proxy": "PRE",
    "rango_dia_hasta_t0": "PRE", "pos_en_rango_dia": "PRE",
    "dist_vwap_ticks": "PRE", "dist_vwap_abs": "PRE",
    "pct_tick_rate": "PRE", "pct_vol_rate": "PRE", "pct_rv": "PRE",
    "pct_rango_prev": "PRE", "pct_illiq": "PRE",
    "n_previas_causal": "PRE", "es_primera": "PRE", "t_desde_previa_ms": "PRE",
    "repeticiones_nivel_causal": "PRE", "solape_causal": "PRE",
    "ancho_ticks": "AT_EVENT", "dir": "AT_EVENT", "tipo": "AT_EVENT",
    "pasos": "AT_EVENT", "valid_steps": "AT_EVENT", "avg_ms": "AT_EVENT",
    "total_ms": "AT_EVENT", "total_vol": "AT_EVENT", "vol_rate_evento": "AT_EVENT",
    "esfuerzo_vol_por_tick": "AT_EVENT", "desplazamiento_sobre_path": "AT_EVENT",
    "motivo_filtro_fallado": "AT_EVENT",
}
NO_IMPLEMENTADAS = {
    "scheduled_news": "NOT_AVAILABLE: requiere calendario oficial, no existe en el repo",
    "spread_depth_ofi": "DEFERRED: requiere BBO/L2 sincronizado (L01)",
    "queue_imbalance": "DEFERRED: requiere colas reales (L02)",
    "bigtrap_columns": "BLOCKED: paridad de BigTrap2 sobre ES no existe",
}


class PercentilExpansivo:
    """Percentil contra el historial ACUMULADO del mismo bucket, nunca full-sample."""

    def __init__(self):
        self.hist = {}

    def pct(self, bucket, valor):
        h = self.hist.setdefault(bucket, [])
        p = None if len(h) < 20 else float(np.mean(np.asarray(h) <= valor))
        h.append(valor)
        return None if p is None else round(p, 4)


def sha256_de(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def make_run_id(head, claves, max_ses):
    partes = [SCHEMA_VERSION, head, CONTRATO, str(BUCKET_MIN), str(SEED),
              str(max_ses), ",".join(str(t) for t in claves)]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def clasificar_run(max_ses, out_path):
    if not max_ses:
        return "full", True, None
    if pathlib.Path(out_path).resolve() == CANONICAL_OUT.resolve():
        return "truncated_probe", False, "truncada no sobrescribe %s" % CANONICAL_OUT
    return "truncated_probe", False, None


def barras_1min(ts, px, vol, ini):
    m = ((ts - ini) // 60_000_000_000).astype(np.int64)
    corte = np.flatnonzero(np.diff(m)) + 1
    tr = np.split(np.arange(len(m)), corte)
    return [dict(i0=int(t[0]), i1=int(t[-1]), ts=int(ts[t[-1]]),
                 o=float(px[t[0]]), h=float(px[t].max()), l=float(px[t].min()),
                 c=float(px[t[-1]]), v=float(vol[t].sum())) for t in tr]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--parquet", default=str(PARQUET))
    ap.add_argument("--atlas-dir", default=str(DIR_ATLAS))
    a = ap.parse_args()

    run_scope, publishable, err = clasificar_run(a.max_sesiones, a.out)
    if err:
        sys.exit("ABORTA: " + err)

    snapshot, parquet = pathlib.Path(a.snapshot), pathlib.Path(a.parquet)
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
    print("atlas HFT  -  %s" % SCHEMA_VERSION)
    print("  universo %d -> seleccionadas %d  (%s)  SIN OUTCOMES"
          % (len(universo), len(claves), run_scope))

    pct = {k: PercentilExpansivo() for k in
           ("tick_rate", "vol_rate", "rv", "rango_prev", "illiq")}
    filas, faltantes = [], []

    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(parquet, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError as e:
            faltantes.append(dict(trade_date=td, motivo=str(e)[:100]))
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        if len(ts) < 1000:
            faltantes.append(dict(trade_date=td, motivo="menos de 1000 ticks"))
            continue

        barras = barras_1min(ts, pxt.astype(np.float64), vol, ini)
        b_ts = np.array([b["ts"] for b in barras], dtype=np.int64)
        pv = np.cumsum([b["c"] * b["v"] for b in barras])
        vv = np.cumsum([b["v"] for b in barras])
        vwap = pv / np.maximum(vv, 1e-9)
        med_vol_sesion = float(np.median([b["v"] for b in barras]))

        # --- eventos de las tres poblaciones, con historia causal propia -------
        eventos = []
        for (zid, st, en, bucket, dr, pu, pl, pas, vst, ams, tms, tvol, vr) in zs[td]:
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            if hi - lo <= 0:
                continue
            eventos.append(dict(grupo="ZONA", start_ts=st, end_ts=en, lo=lo, hi=hi,
                                dir=int(dr), tipo=bucket, pasos=pas, valid_steps=vst,
                                avg_ms=ams, total_ms=tms, total_vol=tvol,
                                vol_rate_evento=vr, motivo_filtro_fallado=None))
        _z, casi = run_con_casi(ts, pxt * tsz, vol, tsz)
        for c0 in casi:
            hi = int(round(c0["price_upper"] / tsz))
            lo = int(round(c0["price_lower"] / tsz))
            if hi - lo <= 0:
                continue
            eventos.append(dict(grupo="CASI", start_ts=c0["start_ts"],
                                end_ts=c0["end_ts"], lo=lo, hi=hi, dir=int(c0["dir"]),
                                tipo="casi", pasos=c0["pasos"],
                                valid_steps=c0["valid_steps"], avg_ms=c0["avg_ms"],
                                total_ms=c0["total_ms"], total_vol=c0["total_vol"],
                                vol_rate_evento=c0["vol_rate"],
                                motivo_filtro_fallado=c0["motivo"]))
        for b in barras:
            rango = b["h"] - b["l"]
            if rango < S1_MIN_RANGO_TICKS or b["v"] < med_vol_sesion:
                continue
            mecha_sup = b["h"] - max(b["o"], b["c"])
            mecha_inf = min(b["o"], b["c"]) - b["l"]
            if max(mecha_sup, mecha_inf) < S1_MECHA_FRAC * rango:
                continue
            eventos.append(dict(
                grupo="S1_1MIN", start_ts=b["ts"] // 1_000_000,
                end_ts=b["ts"] // 1_000_000, lo=int(b["l"]), hi=int(b["h"]),
                dir=1 if b["c"] >= b["o"] else -1, tipo="s1",
                pasos=None, valid_steps=None, avg_ms=None, total_ms=None,
                total_vol=b["v"], vol_rate_evento=None, motivo_filtro_fallado=None))

        eventos.sort(key=lambda e: e["start_ts"])
        prev = {g: dict(ts=[], niveles=[]) for g in ("ZONA", "CASI", "S1_1MIN")}

        for ev in eventos:
            st = ev["start_ts"]
            j = int(np.searchsorted(ts, st * 1_000_000, side="left"))
            j0 = int(np.searchsorted(ts, st * 1_000_000 - VENTANA_PREV_MS * 1_000_000))
            pr = pxt[j0:j]
            if len(pr) < 2:
                continue
            dur_s = max((ts[j - 1] - ts[j0]) / 1e9, 1e-6) if j > j0 else 1e-6
            d = datetime.fromtimestamp(st / 1e3, tz=timezone.utc).astimezone(NY)
            h_ny = d.hour + d.minute / 60.0
            bucket15 = int(h_ny * 60 // BUCKET_MIN)

            dif = np.diff(pr.astype(np.float64))
            rango_prev = float(pr.max() - pr.min())
            path = float(np.abs(dif).sum())
            rv = float(np.sqrt((dif ** 2).sum()))
            ret = float(pr[-1] - pr[0])
            v5 = float(vol[j0:j].sum())
            tick_rate = (j - j0) / dur_s
            vol_rate5 = v5 / dur_s
            illiq = abs(ret) / max(v5, 1.0)
            hasta = pxt[:max(j, 1)]
            d_lo, d_hi = int(hasta.min()), int(hasta.max())
            ib = int(np.searchsorted(b_ts, st * 1_000_000, side="left")) - 1
            vw = float(vwap[ib]) if 0 <= ib < len(vwap) else None
            mid = (ev["hi"] + ev["lo"]) / 2.0

            g = prev[ev["grupo"]]
            n_prev = len(g["ts"])
            rep = sum(1 for n in g["niveles"] if abs(n - mid) <= 1.0)
            solape = sum(1 for (a_, b_) in g["niveles_lohi"]
                         if ev["lo"] <= b_ and a_ <= ev["hi"]) \
                if "niveles_lohi" in g else 0

            filas.append(dict(
                trade_date=td, grupo=ev["grupo"], start_ts=st,
                session_phase=fase_de(h_ny), minuto_sesion=round((st * 1_000_000 - ini)
                                                                 / 6e10, 1),
                bucket_15m=bucket15,
                tick_rate_5m=round(tick_rate, 3), vol_rate_5m=round(vol_rate5, 3),
                intertick_mediano_ms=round(float(np.median(np.diff(ts[j0:j]))) / 1e6, 3)
                if j - j0 > 1 else None,
                cambios_precio_5m=int((dif != 0).sum()),
                rango_prev_5m=round(rango_prev, 2), path_prev_5m=round(path, 2),
                rv_prev_5m=round(rv, 4), ret_prev_5m_signed=round(ret, 2),
                ret_prev_5m_abs=round(abs(ret), 2),
                trend_score=round(ret / rv, 4) if rv > 0 else None,
                illiq_amihud_proxy=round(illiq, 8),
                rango_dia_hasta_t0=d_hi - d_lo,
                pos_en_rango_dia=round((mid - d_lo) / max(d_hi - d_lo, 1), 4),
                dist_vwap_ticks=round(mid - vw, 2) if vw is not None else None,
                dist_vwap_abs=round(abs(mid - vw), 2) if vw is not None else None,
                pct_tick_rate=pct["tick_rate"].pct(bucket15, tick_rate),
                pct_vol_rate=pct["vol_rate"].pct(bucket15, vol_rate5),
                pct_rv=pct["rv"].pct(bucket15, rv),
                pct_rango_prev=pct["rango_prev"].pct(bucket15, rango_prev),
                pct_illiq=pct["illiq"].pct(bucket15, illiq),
                n_previas_causal=n_prev, es_primera=bool(n_prev == 0),
                t_desde_previa_ms=int(st - g["ts"][-1]) if n_prev else None,
                repeticiones_nivel_causal=rep, solape_causal=solape,
                ancho_ticks=ev["hi"] - ev["lo"], dir=ev["dir"], tipo=ev["tipo"],
                pasos=ev["pasos"], valid_steps=ev["valid_steps"], avg_ms=ev["avg_ms"],
                total_ms=ev["total_ms"], total_vol=ev["total_vol"],
                vol_rate_evento=ev["vol_rate_evento"],
                esfuerzo_vol_por_tick=round(ev["total_vol"] / max(ev["hi"] - ev["lo"], 1),
                                            3),
                desplazamiento_sobre_path=round((ev["hi"] - ev["lo"]) / path, 4)
                if path > 0 else None,
                motivo_filtro_fallado=ev["motivo_filtro_fallado"]))
            g["ts"].append(st)
            g["niveles"].append(mid)
            g.setdefault("niveles_lohi", []).append((ev["lo"], ev["hi"]))

        if (k + 1) % 10 == 0:
            print("    %d/%d  filas %d" % (k + 1, len(claves), len(filas)))

    print("  %d filas totales" % len(filas))

    # --------------------------------------------------------------- salida
    import pyarrow as pa
    import pyarrow.parquet as pq
    dir_atlas = pathlib.Path(a.atlas_dir)
    dir_atlas.mkdir(parents=True, exist_ok=True)
    ruta = dir_atlas / ("atlas_hft_es_%s.parquet"
                        % ("full" if not a.max_sesiones else "probe"))
    pq.write_table(pa.Table.from_pylist(filas), ruta, compression="zstd")
    sha = sha256_de(ruta)

    def resumen_grupo(g):
        sub = [f for f in filas if f["grupo"] == g]
        if not sub:
            return {}
        def q(c):
            v = [x[c] for x in sub if x.get(c) is not None]
            return round(float(np.median(v)), 4) if v else None
        return dict(
            n=len(sub),
            frac_pct_disponible=round(float(np.mean(
                [x["pct_rv"] is not None for x in sub])), 4),
            ancho_mediano=q("ancho_ticks"), rv_mediano=q("rv_prev_5m"),
            tick_rate_mediano=q("tick_rate_5m"), trend_score_mediano=q("trend_score"),
            dist_vwap_abs_mediana=q("dist_vwap_abs"),
            pos_en_rango_mediana=q("pos_en_rango_dia"),
            solape_causal_mediano=q("solape_causal"),
            frac_primera=round(float(np.mean([x["es_primera"] for x in sub])), 4),
            por_fase={f: round(sum(1 for x in sub if x["session_phase"] == f)
                               / len(sub), 4)
                      for f in sorted({x["session_phase"] for x in sub})})

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION,
        run_id=make_run_id(head, claves, a.max_sesiones),
        run_scope=run_scope, publishable=publishable, max_sesiones_arg=a.max_sesiones,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        proposito=("atlas target-free F1: una fila por evento, tres poblaciones con las "
                   "MISMAS columnas, construido antes de que exista ningun outcome"),
        poblaciones=dict(
            ZONA="zona real del oraculo Flat",
            CASI="racha que fallo exactamente uno de los cuatro filtros de calidad",
            S1_1MIN=("barra extrema de 1 minuto: rango >= %d ticks, mecha >= %d%% del "
                     "rango, volumen >= mediana de sesion. NO es el S1 de F2.9 (otra "
                     "especificacion de barra, otro instrumento); por eso el nombre "
                     "distinto" % (S1_MIN_RANGO_TICKS, int(S1_MECHA_FRAC * 100)))),
        disponibilidad_causal=DISPONIBILIDAD,
        no_implementadas=NO_IMPLEMENTADAS,
        normalizacion=("percentil EXPANSIVO contra el historial acumulado del mismo "
                       "bucket de %d min, procesando sesiones en orden cronologico. "
                       "Nunca full-sample: seria comodo y no seria live-compatible. "
                       "None hasta acumular 20 observaciones en el bucket" % BUCKET_MIN),
        conteos=dict(n_universe_discovered=len(universo), n_selected=len(claves),
                     n_available=len(claves) - len(faltantes),
                     n_filas=len(filas),
                     por_grupo={g: sum(1 for f in filas if f["grupo"] == g)
                                for g in ("ZONA", "CASI", "S1_1MIN")}),
        missing_items=faltantes,
        artefacto=dict(ruta=(str(ruta.relative_to(REPO))
                             if REPO in ruta.parents else str(ruta)), sha256=sha,
                       bytes=ruta.stat().st_size,
                       nota="gitignorado: es dato, no codigo. El sha256 lo hace trazable"),
        resumen={g: resumen_grupo(g) for g in ("ZONA", "CASI", "S1_1MIN")},
        procedencia=dict(head_commit=head, arbol_limpio=not bool(sucios),
                         archivos_sucios=sorted(sucios), snapshot=str(snapshot),
                         parquet=str(parquet), comando=" ".join(sys.argv)))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    print("\n  por grupo: %s" % out["conteos"]["por_grupo"])
    for g, r in out["resumen"].items():
        if r:
            print("  %-8s n=%6d  ancho %5s  rv %8s  trend %7s  vwap %7s  1a %.3f"
                  % (g, r["n"], r["ancho_mediano"], r["rv_mediano"],
                     r["trend_score_mediano"], r["dist_vwap_abs_mediana"],
                     r["frac_primera"]))
    print("  parquet %s  (%.1f MB)  sha256 %s..."
          % (ruta.name, ruta.stat().st_size / 1e6, sha[:16]))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
