#!/usr/bin/env python3
"""Piloto de SOPORTE de etiquetas para EXP-REV-GRID (sin modelo, sin indicador, sin entrenar).

Pregunta: con barreras (X, Y) en ticks y horizonte T, ¿que fraccion de las decisiones resuelve (R/C) y cual vence (timeout) o queda
censurada por fin de sesion? Solo usa el camino de precios de ticks (release v4, ES) en el tramo de DESCUBRIMIENTO (2025-07-18..2026-03-31).
No calcula retornos de una estrategia ni ajusta nada. Sirve para fijar etiqueta/horizonte y el MDE de las particiones ANTES de entrenar.

Reloj de decision: cada DECISION_STEP_S segundos dentro de RTH (08:30-15:30 hora de Chicago real). Entrada: primer tick posterior a la decision.
R = la barrera X en la direccion de reversion se alcanza primero; C = la barrera Y en contra; empate en el mismo timestamp = AMBIGUOUS;
TIMEOUT = ninguna en T con datos completos; CENSORED = la sesion termina antes de T. Se promedian las dos direcciones (sin indicador de expansion
no hay direccion privilegiada): este piloto mide RESOLUCION, no predictibilidad.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow.parquet as pq
from numba import njit

DISC_START, DISC_END = 20250718, 20260331
HOLDOUT_TRADE_DATE = 20261001
HOLDOUT_UTC_NS = 1790812800000000000
CHI = ZoneInfo("America/Chicago")
DECISION_STEP_S = int(os.environ.get("PILOT_STEP", "60"))
RTH_MIN = (510, 930)                      # 08:30 - 15:30 CT en minutos
# Configuracion por defecto = piloto de horizontes largos; PILOT_PAIRS="8:8,12:12" y PILOT_H="15,30,60" dan el piloto de horizontes cortos (pista L2)
PAIRS = [tuple(int(v) for v in s.split(":")) for s in os.environ.get("PILOT_PAIRS", "24:24,32:32,48:32,48:48,64:32,64:64,96:48").split(",")]   # (X objetivo, Y parada)
HORIZONS_S = [int(v) for v in os.environ.get("PILOT_H", "300,600,900,1800,3600").split(",")]
LEVELS = np.array(sorted({v for p in PAIRS for v in p}), dtype=np.int64)      # ticks
FRICTION_ES = 3.546
OUT = ["R", "C", "AMBIGUOUS", "TIMEOUT", "CENSORED"]


def locate_es_parquet() -> Path:
    env = os.environ.get("ES_TICKS_PARQUET")
    if env:
        return Path(env)
    root = Path("/kaggle/input")
    if root.exists():
        import json as _j
        for m in root.rglob("release_manifest.json"):
            try:
                info = _j.loads(m.read_text(encoding="utf-8")).get("assets", {}).get("ES")
                if info and "file" in info and (m.parent / info["file"]).exists():
                    return m.parent / info["file"]
            except Exception:
                pass
        for c in list(root.rglob("ES_ticks.parquet")) + list(root.rglob("ES.parquet")):
            return c
    raise FileNotFoundError("no se encontro el parquet de ES")


def load_sessions(pfile: Path):
    pf = pq.ParquetFile(pfile)
    ci = {pf.metadata.row_group(0).column(i).path_in_schema: i for i in range(pf.metadata.row_group(0).num_columns)}
    td_col, c_col, sel_col = ci["trade_date"], ci.get("contract", -1), ci.get("session_selected", -1)
    by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st = md.column(td_col).statistics
        if st is not None and st.has_min_max and int(st.min) >= HOLDOUT_TRADE_DATE:
            continue
        key = int(st.min) if (st is not None and st.has_min_max and st.min == st.max) else -1
        by_td[key].append(rg)
    out = []
    for td in sorted(k for k in by_td if DISC_START <= k <= DISC_END):
        rgs = by_td[td]
        if len(rgs) > 1 and c_col >= 0:
            rows, per = defaultdict(int), defaultdict(list)
            for r in rgs:
                md = pf.metadata.row_group(r)
                if sel_col >= 0:
                    s = md.column(sel_col).statistics
                    if s is not None and s.has_min_max and s.max is False:
                        continue
                sc = md.column(c_col).statistics
                name = str(sc.min) if (sc is not None and sc.has_min_max) else "UNK"
                rows[name] += md.num_rows
                per[name].append(r)
            if not rows:
                continue
            rgs = per[max(rows.items(), key=lambda x: x[1])[0]]
        else:
            md0 = pf.metadata.row_group(rgs[0])
            if sel_col >= 0:
                s = md0.column(sel_col).statistics
                if s is not None and s.has_min_max and s.max is False:
                    continue
        t = pf.read_row_groups(rgs, columns=["ts_utc_ns", "price_ticks"])
        ts = np.array(t["ts_utc_ns"].to_numpy(), dtype=np.int64)
        px = np.array(t["price_ticks"].to_numpy(), dtype=np.int64)
        if len(ts) < 1000:
            continue
        if ts[-1] >= HOLDOUT_UTC_NS:
            m = ts < HOLDOUT_UTC_NS
            ts, px = ts[m], px[m]
        if (np.diff(ts) < 0).any():
            o = np.argsort(ts, kind="mergesort")
            ts, px = ts[o], px[o]
        off = int(datetime.fromtimestamp(int(ts[len(ts) // 2]) / 1e9, CHI).utcoffset().total_seconds())
        out.append((td, ts, px, off))
    return out


@njit(cache=True)
def scan_session(ts, px, dec_ts, levels, tmax_ns):
    """Para cada decision: tiempos (ns desde la entrada) de primer cruce de cada nivel arriba/abajo, y datos para censura/timeout."""
    nd, nl = len(dec_ts), len(levels)
    tu = np.full((nd, nl), -1, np.int64)
    td = np.full((nd, nl), -1, np.int64)
    ok = np.zeros(nd, np.bool_)
    covered = np.zeros(nd, np.int64)      # ns de camino observado desde la entrada (hasta fin de sesion o tmax)
    n = len(ts)
    j = 0
    for k in range(nd):
        while j < n and ts[j] <= dec_ts[k]:
            j += 1
        if j >= n - 1:
            continue
        e = j
        ok[k] = True
        p0 = px[e]
        t0 = ts[e]
        mx = 0
        mn = 0
        iu = 0
        idn = 0
        i = e + 1
        while i < n and ts[i] - t0 <= tmax_ns:
            d = px[i] - p0
            if d > mx:
                mx = d
                while iu < nl and mx >= levels[iu]:
                    tu[k, iu] = ts[i] - t0
                    iu += 1
            if d < mn:
                mn = d
                while idn < nl and -mn >= levels[idn]:
                    td[k, idn] = ts[i] - t0
                    idn += 1
            i += 1
        covered[k] = ts[n - 1] - t0 if ts[n - 1] - t0 < tmax_ns else tmax_ns
    return tu, td, ok, covered


def level_index(v):
    return int(np.where(LEVELS == v)[0][0])


def classify(tu, td, covered, x, y, T_ns):
    """Cuenta R/C/AMBIGUOUS/TIMEOUT/CENSORED para la direccion 'reversion hacia arriba' y su espejo, devolviendo [dir, outcome]."""
    ix, iy = level_index(x), level_index(y)
    res = np.zeros((2, 5), np.int64)
    for d in range(2):
        up_t = tu[:, ix] if d == 0 else td[:, ix]     # objetivo X en la direccion de la reversion
        dn_t = td[:, iy] if d == 0 else tu[:, iy]     # parada Y en contra
        a = (up_t >= 0) & (up_t <= T_ns)
        b = (dn_t >= 0) & (dn_t <= T_ns)
        r = a & (~b | (up_t < dn_t))
        c = b & (~a | (dn_t < up_t))
        amb = a & b & (up_t == dn_t)
        res[d, 0] = int(r.sum())
        res[d, 1] = int(c.sum())
        res[d, 2] = int(amb.sum())
        neither = ~a & ~b
        cens = neither & (covered < T_ns)
        res[d, 3] = int((neither & ~cens).sum())
        res[d, 4] = int(cens.sum())
    return res


def main():
    t0 = time.time()
    pfile = locate_es_parquet()
    sessions = load_sessions(pfile)
    print(f"sesiones de descubrimiento: {len(sessions)} ({sessions[0][0]}..{sessions[-1][0]})", flush=True)
    tmax_ns = max(HORIZONS_S) * 1_000_000_000
    per_session = {}      # (pair, T) -> lista de vectores [R,C,AMB,TO,CENS] por sesion (suma de las 2 direcciones)
    decisions = []
    for td, ts, px, off in sessions:
        # decisiones RTH cada DECISION_STEP_S
        sec = (ts // 1_000_000_000 + off)
        mins = (sec % 86400) // 60
        in_rth = (mins >= RTH_MIN[0]) & (mins <= RTH_MIN[1])
        if not in_rth.any():
            continue
        first, last = int(ts[in_rth][0]), int(ts[in_rth][-1])
        dec = np.arange(first, last, DECISION_STEP_S * 1_000_000_000, dtype=np.int64)
        m = ((dec // 1_000_000_000 + off) % 86400) // 60
        dec = dec[(m >= RTH_MIN[0]) & (m <= RTH_MIN[1])]
        tu, tdn, ok, cov = scan_session(ts, px, dec, LEVELS, tmax_ns)
        tu, tdn, cov = tu[ok], tdn[ok], cov[ok]
        decisions.append((td, int(ok.sum())))
        for pair in PAIRS:
            for T in HORIZONS_S:
                r = classify(tu, tdn, cov, pair[0], pair[1], T * 1_000_000_000)
                per_session.setdefault((pair, T), []).append(r.sum(axis=0))
    summary = []
    for (pair, T), lst in per_session.items():
        arr = np.array(lst, dtype=np.float64)          # [sesion, 5]
        tot = arr.sum(axis=0)
        n = tot.sum()
        resolved_den = tot[0] + tot[1]
        p_R, p_C, p_TO, p_CENS, p_AMB = tot[0] / n, tot[1] / n, tot[3] / n, tot[4] / n, tot[2] / n
        x, y = pair
        p_eq = (y + FRICTION_ES) / (x + y)
        # SE por sesion de la tasa de reversion entre resueltos y MDE80 (clusterizado por sesion)
        rr = np.where(arr[:, 0] + arr[:, 1] > 0, arr[:, 0] / np.maximum(arr[:, 0] + arr[:, 1], 1), np.nan)
        w = arr[:, 0] + arr[:, 1]
        mu = np.nansum(rr * w) / max(w.sum(), 1)
        se = np.sqrt(np.nansum((w * (rr - mu)) ** 2)) / max(w.sum(), 1) * np.sqrt(len(w) / max(len(w) - 1, 1))
        summary.append(dict(X=x, Y=y, T_s=T, decisiones=int(n / 2), p_R=round(p_R, 4), p_C=round(p_C, 4), p_timeout=round(p_TO, 4),
                            p_censurado=round(p_CENS, 4), p_ambiguo=round(p_AMB, 5),
                            resueltos_por_sesion=round(resolved_den / 2 / len(arr), 1), R_entre_resueltos=round(float(tot[0] / max(resolved_den, 1)), 4),
                            p_eq_con_friccion=round(p_eq, 4), p_nulo_primer_paso=round(y / (x + y), 4), se_sesion_R_entre_resueltos=round(float(se), 4),
                            mde80_pp=round(float(2.8 * se * 100), 2), sesiones=int(len(arr)),
                            episodios_independientes_aprox=int(len(arr) * (RTH_MIN[1] - RTH_MIN[0]) * 60 / T)))
    out = dict(spec="EXP-REV-GRID support pilot v1", discovery=[DISC_START, DISC_END], sesiones=len(sessions), decision_step_s=DECISION_STEP_S,
               friccion_es_ticks=FRICTION_ES, nota="mide resolucion, no predictibilidad; sin indicador ni modelo; sin retornos de estrategia",
               decisiones_por_sesion_media=round(float(np.mean([d[1] for d in decisions])), 1), tabla=summary, segundos=round(time.time() - t0, 1))
    Path(os.environ.get("PILOT_OUT", "/kaggle/working")).mkdir(parents=True, exist_ok=True)
    Path(os.environ.get("PILOT_OUT", "/kaggle/working"), "GRID_SUPPORT_PILOT.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("=== GRID_SUPPORT_PILOT_START ===", flush=True)
    print(json.dumps(out, indent=1), flush=True)
    print("=== GRID_SUPPORT_PILOT_END ===", flush=True)


if __name__ == "__main__":
    main()
