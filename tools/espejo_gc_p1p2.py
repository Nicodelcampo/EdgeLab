#!/usr/bin/env python3
r"""Candidato GC (reversión tras el espejo) — controles P1 y P2 pedidos por el auditor (062/063), OK de Nico 29/09.
Sólo descubrimiento (≤ 2026-03-31, feb-2026 excluido). Nada de abr–jun ni holdout.

COHORTE: exactamente los eventos de `espejo_rev_100t.py` versión que produjo 2.103 trades (GC, W ≥ 100 t, 30 velas 100t;
recorrido cronológico; se llena si la vela de completación pasó A ≥ 1 tick; pool previo ≥ 50). Cada exclusión posterior
se cuenta por regla, nada se descarta en silencio.

P1 — control emparejado: por cada evento, 3 velas de OTRAS sesiones de descubrimiento con la misma franja horaria
(±30 min, reloj UTC del día) y el mismo tercil de volatilidad previa (desvío de los cambios de cierre de las 20 velas
100t anteriores; cortes globales). Misma operación: dirección, W, TP/SL y desplazamiento cierre→entrada. Diferencia
pareada R_evento − media(R_controles); bootstrap por sesión del evento; máximo estadístico (max-T) sobre 30 celdas
(15 TP/SL × {todos, no lista + ineficiente}). Eventos sin 3 controles comparables: «sin soporte», informados.

P2 — llenado tick a tick (piloto 200 trades, elegidos con semilla por estratos de sesión ANTES de mirar resultados):
orden límite en A colocada al cierre de la vela 100t en que la vuelta cruzó el 75 % (antes del toque); llenado si
opera un trade ≥ 1 tick del otro lado de A (trade-through: sin libro no se demuestra prioridad en cola, se usa el
criterio conservador). TP límite (se llena con trade-through de 1 tick); SL stop, ejecutado al bid/ask del primer
tick que lo dispara (deslizamiento medido). Horizonte 150 velas (15.000 ticks) o fin de sesión, liquidación al bid/ask.
Fricción congelada ANTES de ver resultados: comisión + tasas US$ 2,50 por lado (supuesto declarado), tick GC US$ 10;
spread y deslizamiento medidos de los ticks. Se reporta R por regla de velas vs R tick a tick, tasa de llenado y R neto.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402

M, HZ, SEED, MW, MB = 4, 150, 20260929, 100.0, 30
TPS = (0.25, 0.5, 1.0, 1.5, 2.0); SLS = (0.25, 0.5, 1.0)
KEYS = [f"{tp}_{sl}" for tp in TPS for sl in SLS]
TOD_WIN, N_CTRL, N_BOOT, N_P2 = 1800, 3, 2000, 200
COMISION_USD_LADO, TICK_USD = 2.50, 10.0


def agg(h, l, c, v, t):
    n = len(c) // M * M
    return (h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1],
            v[:n].reshape(-1, M).sum(1), t[:n].reshape(-1, M)[:, -1])


def trade(H, L, C, k, fill, c, tp, sl, end):
    T = fill + c * tp; S = fill - c * sl
    for j in range(k + 1, end + 1):
        if (L[j] <= S) if c == 1 else (H[j] >= S):
            return S
        if (H[j] >= T) if c == 1 else (L[j] <= T):
            return T
    return C[end]


def vol_prev(C):
    d = np.abs(np.diff(C, prepend=C[0])); out = np.full(len(C), np.nan)
    cs = np.cumsum(d); cs2 = np.cumsum(d * d)
    for i in range(20, len(C)):
        a = cs[i - 1] - cs[i - 21]; b = cs2[i - 1] - cs2[i - 21]
        out[i] = np.sqrt(max(b / 20 - (a / 20) ** 2, 0))
    return out


def load_sessions(bars_dir):
    files = [f for f in sorted(Path(bars_dir).glob("*.npz")) if not f.stem.startswith("202602")]
    S = {}
    for f in files:
        z = np.load(f); h, l, c, v = (z[q].astype(float) for q in ("h", "l", "c", "v")); t = z["t"].astype(float)
        H, L, C, V, T = agg(h, l, c, v, t)
        S[f.stem] = dict(H=H, L=L, C=C, V=V, T=T, n=len(C), vol=vol_prev(C) if len(C) > 20 else np.full(len(C), np.nan))
    return files, S


def cohort(files, S, excl):
    """Réplica exacta de espejo_rev_100t (versión cronológica que dio 2.103 trades)."""
    ev, prev_ok = [], False
    for f in files:
        s = f.stem; D = S[s]; n = D["n"]
        if n < 60:
            prev_ok = False; continue
        H, L, C, V, T = D["H"], D["L"], D["C"], D["V"], D["T"]
        res = K.run(T, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int), params=dict(e_max=1.01, atr_k=None, min_w=MW, max_bars=MB))
        prog = {}
        for e in res["events"]:
            if e["kind"] in ("MIRROR_CANDIDATE", "MIRROR_PROGRESS") and abs(e.get("x", 0) - 0.75) < 1e-9:
                prog[e["imp_id"]] = e["bar"]
        comp = {e["imp_id"]: e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"}
        for im in res["impulses"]:
            e = comp.get(im["imp_id"])
            if e is None or not im["W"]:
                continue
            k = e["bar"]; d = im["dir"]; A = im["A"]
            if k >= n - 2:
                excl["k_fin_sesion"] += 1; continue
            if d * (A - (L[k] if d == 1 else H[k])) < 1:
                excl["no_paso_A_1tick"] += 1; continue
            end = min(k + HZ, n - 1)
            if not (k * M >= 50 or prev_ok) or end <= k:
                excl["sin_pool_o_horizonte"] += 1; continue
            ev.append(dict(session=s, k=int(k), d=int(d), A=float(A), W=float(im["W"]), end=int(end), k75=prog.get(im["imp_id"]),
                           filt=bool(im["no_lista_lo"] is not None and im["ineficiente"]), tod=float(T[k] % 86400), vol=float(D["vol"][k])))
        prev_ok = True
    return ev


def cells_R(D, k, fill, c, W, end):
    return np.array([c * (trade(D["H"], D["L"], D["C"], k, fill, c, tp * W, sl * W, end) - fill) / W for tp in TPS for sl in SLS])


def p1(bars_dir, out):
    files, S = load_sessions(bars_dir)
    excl = {"k_fin_sesion": 0, "no_paso_A_1tick": 0, "sin_pool_o_horizonte": 0}
    ev = cohort(files, S, excl)
    allvol = np.concatenate([D["vol"][~np.isnan(D["vol"])] for D in S.values()]); cut = np.quantile(allvol, [1 / 3, 2 / 3])
    ter = lambda v: -1 if np.isnan(v) else (0 if v <= cut[0] else (2 if v > cut[1] else 1))
    cand = []                                            # (sesion, q, tod, tercil)
    for s, D in S.items():
        for q in range(20, D["n"] - 2):
            cand.append((s, q, D["T"][q] % 86400, ter(D["vol"][q])))
    cs = np.array([x[0] for x in cand]); cq = np.array([x[1] for x in cand]); ctod = np.array([x[2] for x in cand]); cter = np.array([x[3] for x in cand])
    rng = np.random.default_rng(SEED)
    rows, sin_soporte = [], 0
    for e in ev:
        D = S[e["session"]]; k = e["k"]
        Rr = cells_R(D, k, e["A"], e["d"], e["W"], e["end"])
        dt = np.abs(ctod - e["tod"]); dt = np.minimum(dt, 86400 - dt)
        m = (cs != e["session"]) & (dt <= TOD_WIN) & (cter == ter(e["vol"]))
        idx = np.flatnonzero(m)
        if len(idx) < N_CTRL:
            sin_soporte += 1; rows.append(dict(**{k2: e[k2] for k2 in ("session", "k", "filt")}, R=Rr.tolist(), ctrl=None)); continue
        Rc = []
        for i in rng.choice(idx, N_CTRL, replace=False):
            Dc = S[cs[i]]; q = int(cq[i]); off = e["A"] - D["C"][k]
            Rc.append(cells_R(Dc, q, Dc["C"][q] + off, e["d"], e["W"], min(q + (e["end"] - k), Dc["n"] - 1)))
        rows.append(dict(**{k2: e[k2] for k2 in ("session", "k", "filt")}, R=Rr.tolist(), ctrl=np.mean(Rc, 0).tolist()))
    sup = [r for r in rows if r["ctrl"] is not None]
    res = {}
    blocks = [("todos", sup), ("no_lista+inef", [r for r in sup if r["filt"]])]
    tobs, tnull, cellsout = [], [], []
    for fname, X in blocks:
        if len(X) < 30:
            continue
        Dm = np.array([np.array(r["R"]) - np.array(r["ctrl"]) for r in X]); ses = np.array([r["session"] for r in X])
        u = np.unique(ses); ix = {x: i for i, x in enumerate(u)}; si = np.array([ix[x] for x in ses])
        Ssum = np.zeros((len(u), len(KEYS))); N = np.zeros(len(u)); np.add.at(Ssum, si, Dm); np.add.at(N, si, 1)
        Wb = np.random.default_rng(SEED + 1).multinomial(len(u), np.ones(len(u)) / len(u), size=N_BOOT).astype(float)
        bm = (Wb @ Ssum) / np.maximum(Wb @ N, 1e-9)[:, None]; obs = Dm.mean(0); se = bm.std(0)
        tobs.append(obs / se); tnull.append(np.abs((bm - obs) / se))
        for j, key in enumerate(KEYS):
            cellsout.append(dict(filtro=fname, celda=key, n=len(X), R_evento=float(np.mean([r["R"][j] for r in X])),
                                 R_control=float(np.mean([r["ctrl"][j] for r in X])), dif_pareada=float(obs[j]),
                                 ic90=[float(np.quantile(bm[:, j], .05)), float(np.quantile(bm[:, j], .95))], t=float(obs[j] / se[j])))
    crit = float(np.quantile(np.max(np.hstack(tnull), 1), .95))
    for c in cellsout:
        c["sobrevive_maxT"] = abs(c["t"]) >= crit
    res = dict(cohorte=len(ev), exclusiones_antes_de_cohorte=excl, sin_soporte_control=sin_soporte, con_control=len(sup),
               cortes_volatilidad=cut.tolist(), t_critico_maxT_30_celdas=crit, celdas=cellsout)
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "p1_control_emparejado.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    (Path(out) / "p1_cohorte.json").write_text(json.dumps(ev, default=float), encoding="utf-8")
    print("P1 cohorte", len(ev), "exclusiones", excl, "sin soporte", sin_soporte, "t crit", round(crit, 2), flush=True)
    for c in cellsout:
        if c["celda"] in ("2.0_1.0", "1.5_1.0", "1.0_1.0"):
            print(" ", c["filtro"], c["celda"], c["n"], "R ev", round(c["R_evento"], 3), "R ctrl", round(c["R_control"], 3),
                  "dif", round(c["dif_pareada"], 3), [round(x, 3) for x in c["ic90"]], "t", round(c["t"], 2), c["sobrevive_maxT"], flush=True)


def p2(bars_dir, sessions_json, ticks_dir, out):
    """Piloto de llenado tick a tick sobre 200 trades de la cohorte (TP 2 W / SL 1 W, todos)."""
    from edgelab.bridge.ticks import load_canonical_parquet
    files, S = load_sessions(bars_dir)
    excl = {"k_fin_sesion": 0, "no_paso_A_1tick": 0, "sin_pool_o_horizonte": 0}
    ev = cohort(files, S, excl)
    rng = np.random.default_rng(SEED + 2)
    by = {}
    for i, e in enumerate(ev):
        by.setdefault(e["session"], []).append(i)
    order = rng.permutation(sorted(by))                   # estratificado por sesión: 1 por sesión en ronda, hasta 200
    pick = []
    while len(pick) < min(N_P2, len(ev)):
        for s in order:
            if by[s] and len(pick) < N_P2:
                pick.append(by[s].pop(int(rng.integers(len(by[s])))))
        if not any(by.values()):
            break
    meta = {x["trade_date"]: x for x in json.loads(Path(sessions_json).read_text(encoding="utf-8"))["sessions"]}
    files_t = {p.name: p for p in Path(ticks_dir).rglob("*.parquet")}
    rows, cache = [], {}
    for i in sorted(pick):
        e = ev[i]; s = e["session"]; m = meta[s]
        if s not in cache:
            cache.clear()
            tk = load_canonical_parquet(str(files_t[m["file"]]), contract=m["contract"], start_utc_ns=m["start"], end_utc_ns=m["end"])
            cache[s] = tk
        tk = cache[s]; px = tk.price_ticks.astype(float); bid = tk.bid_ticks.astype(float); ask = tk.ask_ticks.astype(float)
        d, A, W, k = e["d"], e["A"], e["W"], e["k"]
        place = (e["k75"] + 1) * 100 if e["k75"] is not None else (k) * 100    # tick al cierre de la vela del 75 %
        last_fill = min(len(px) - 1, (k + 30) * 100)
        # compra (d=1) límite en A: trade-through si opera ≤ A − 1; venta (d=−1): ≥ A + 1
        seg = px[place:last_fill + 1]
        thr = np.flatnonzero(seg <= A - 1) if d == 1 else np.flatnonzero(seg >= A + 1)
        touch = np.flatnonzero(seg <= A) if d == 1 else np.flatnonzero(seg >= A)
        r = dict(session=s, k=k, W=W, lleno_tick=bool(len(thr)), toco_sin_atravesar=bool(len(touch) and not len(thr)))
        if len(thr):
            fi = place + int(thr[0]); T = A + d * 2 * W; SL = A - d * 1 * W; end = min(len(px) - 1, fi + HZ * 100)
            exitp, why, slip = None, "cierre", 0.0
            for j in range(fi + 1, end + 1):
                if (px[j] <= SL) if d == 1 else (px[j] >= SL):
                    exitp = bid[j] if d == 1 else ask[j]; slip = d * (exitp - SL); why = "sl"; break
                if (px[j] >= T + 1) if d == 1 else (px[j] <= T - 1):
                    exitp = T; why = "tp"; break
            if exitp is None:
                exitp = bid[end] if d == 1 else ask[end]
            gross_t = d * (exitp - A)
            spread_fill = float(ask[fi] - bid[fi])
            net_t = gross_t - 2 * COMISION_USD_LADO / TICK_USD
            r.update(salida=why, bruto_ticks=float(gross_t), neto_ticks=float(net_t), R_bruto_W=float(gross_t / W),
                     R_neto_W=float(net_t / W), desliz_sl_ticks=float(slip), spread_llenado=spread_fill)
        D = S[s]
        r["R_regla_velas_W"] = float(d * (trade(D["H"], D["L"], D["C"], k, A, d, 2 * W, 1 * W, e["end"]) - A) / W)
        rows.append(r)
    filled = [r for r in rows if r["lleno_tick"]]
    res = dict(piloto=len(rows), llenados_tick=len(filled), toca_sin_atravesar=sum(r["toco_sin_atravesar"] for r in rows),
               comision_usd_lado=COMISION_USD_LADO,
               R_regla_velas_W_todos=float(np.mean([r["R_regla_velas_W"] for r in rows])),
               R_regla_velas_W_llenados=float(np.mean([r["R_regla_velas_W"] for r in filled])) if filled else None,
               R_tick_bruto_W=float(np.mean([r["R_bruto_W"] for r in filled])) if filled else None,
               R_tick_neto_W=float(np.mean([r["R_neto_W"] for r in filled])) if filled else None,
               neto_ticks_medio=float(np.mean([r["neto_ticks"] for r in filled])) if filled else None,
               desliz_sl_medio=float(np.mean([r["desliz_sl_ticks"] for r in filled if r["salida"] == "sl"])) if any(r.get("salida") == "sl" for r in filled) else None,
               spread_medio=float(np.mean([r["spread_llenado"] for r in filled])) if filled else None, trades=rows)
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "p2_llenado_tick.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("P2", {k2: v for k2, v in res.items() if k2 != "trades"}, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("step", choices=["p1", "p2"]); ap.add_argument("--bars", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--sessions"); ap.add_argument("--ticks"); a = ap.parse_args()
    p1(a.bars, a.out) if a.step == "p1" else p2(a.bars, a.sessions, a.ticks, a.out)
