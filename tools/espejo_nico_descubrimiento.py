#!/usr/bin/env python3
r"""ESPEJO-NICO-100T — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md

ES, research-v2 (Lucid), sesiones de descubrimiento (≤ 2026-03-31). Velas de 25t de la caché de trades
(artifacts/tbzx/bars) y de midquote (artifacts/ipc_rob/mid), agrupadas de a 4 dentro de la sesión = **100t**.

- Impulsos: kernel congelado `espejo_impulsos` con min_w 34 t, max_bars 20, e_min 0,3, retr 0,3, sin e_max (precio de trade).
- Evento: primer CIERRE de vela 100t en que la vuelta recorrió x ∈ {0,50; 0,75} de W sin extremo nuevo más allá de B.
- Resultado: completa (toca A por mecha) antes de un extremo nuevo (≥ 1 tick más allá de B); horizonte 3 × duración de
  la ida en velas 100t o fin de sesión. Primario sobre midquote; trade como descriptivo.
- Nulo N1: `edgelab.research.espejo_nulo.simulate_null` con velas 25t previas al evento (semilla por evento).
- Semejanza: modelo congelado (score menor = más parecido) sobre cierres de trade hasta la vela del evento.
- Terciles del score fijados sobre todo el descubrimiento, por x, sin mirar resultados.
- 8 pruebas primarias: P1 (exceso sobre p0 en el tercil más parecido) y P2 (más − menos parecido), x × estrato.
  Bootstrap por sesión (1.000), p unilateral, BH q = 0,10, MDE 80 % (2,49 × EE).

    .venv\Scripts\python tools\espejo_nico_descubrimiento.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402
from edgelab.bridge.indicators import espejo_impulsos as K  # noqa: E402
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402
from espejo_semejanza_nico import features  # noqa: E402

OUT = REPO / "artifacts" / "espejo" / "nico_100t"
FROZEN = REPO / "docs" / "research" / "ESPEJO_SEMEJANZA_NICO_CONGELADA_20260928.json"
MID = REPO / "artifacts" / "ipc_rob" / "mid" / "ES"
KPARAMS = dict(e_max=1.01, atr_k=None, min_w=34.0, max_bars=20)
XS = (0.5, 0.75)
MULT = 4
N_NULL, N_BOOT, SEED = 2000, 1000, 20260928
TICK = 1.0                                   # las cachés de velas (trade y midquote) están en ticks


def agg100(h, l, c):
    n = len(c) // MULT * MULT                     # la cola incompleta de la sesión no forma vela de 100t
    H = h[:n].reshape(-1, MULT).max(1); L = l[:n].reshape(-1, MULT).min(1); C = c[:n].reshape(-1, MULT)[:, -1]
    return H, L, C


def score(it, fr):
    f = features(it)
    return float(sum(fr["pesos"][k] * f[k] / fr["escala_diferencias"][k] for k in fr["feats"])), f


def outcome(H, L, k, A, beyond, d, horizon_end):
    """Desde la vela k+1 hasta horizon_end (inclusive): completa / falla / ambigua / censurada, y excursión máx en W."""
    for j in range(k + 1, horizon_end + 1):
        hit_a = (L[j] <= A) if d == 1 else (H[j] >= A)
        hit_b = (H[j] >= beyond) if d == 1 else (L[j] <= beyond)
        if hit_a and hit_b:
            return "ambigua", j
        if hit_a:
            return "completa", j
        if hit_b:
            return "falla", j
    return "censurada", horizon_end


def session_events(s, prev_triples, fr):
    z = np.load(T2.bars_dir("ES") / f"{s}.npz"); m = np.load(MID / f"{s}.npz")
    h, l, c, v = (z[k].astype(float) for k in ("h", "l", "c", "v")); t = z["t"].astype(float)
    mh, ml, mc = (m[k].astype(float) for k in ("h", "l", "c"))
    H, L, C = agg100(h, l, c); MH, ML, MC = agg100(mh, ml, mc)
    n = len(C)
    if n < 30:
        return [], None
    T = t[:n * MULT].reshape(-1, MULT)[:, -1]; V = v[:n * MULT].reshape(-1, MULT).sum(1)
    O = np.r_[C[0], C[:-1]]
    res = K.run(T, O, H / TICK * TICK, L, C, V, np.zeros(n, int), params=KPARAMS)
    mo = np.r_[mc[0], mc[:-1]]
    trip = np.column_stack([mc - mo, mh - mo, ml - mo]) / TICK                      # ternas 25t de midquote, en ticks
    rows = []
    for im in res["impulses"]:
        d, A, B, i0, iB = im["dir"], im["A"], im["B"], im["bar_A"], im["bar_B"]
        W = abs(B - A)
        if not W or im["bar_conf"] >= n - 1:
            continue
        dur = iB - i0 + 1
        eff = im["eff"]
        if eff < 0.3:
            continue
        estr = "TBZ" if eff >= 0.6 else "otros"
        done = set()
        start = max(iB + 1, im["bar_conf"])
        for k in range(start, n):
            if (d == 1 and H[k] > B) or (d == -1 and L[k] < B):
                break
            f_close = d * (B - C[k]) / W
            for x in XS:
                if x in done or f_close < x:
                    continue
                done.add(x)
                it = dict(candles=[dict(close=float(cc)) for cc in C[:k + 1]], A=A, B=B, iA=i0, iB=iB, dir=d)
                sc, feats = score(it, fr)
                hz = min(k + 3 * dur, n - 1)
                beyond = B + d * TICK
                r = {"session": s, "x": x, "estrato": estr, "dir": d, "A": A, "B": B, "W_t": W / TICK, "dur": dur,
                     "bar_B": iB, "bar_evt": k, "t_evt": float(T[k]), "score": sc, **feats, "horizonte_velas": hz - k}
                # trade (descriptivo)
                r["res_trade"], _ = outcome(H, L, k, A, beyond, d, hz)
                # midquote (primario): cierre de midquote del evento y nulo desde ahí
                r["res_mid"], jm = outcome(MH, ML, k, A, beyond, d, hz)
                seg = slice(k + 1, (jm if r["res_mid"] != "censurada" else hz) + 1)
                exc_a = (d * (B - (ML[seg] if d == 1 else MH[seg]))).max() if seg.stop > seg.start else 0.0
                r["exc_max_W"] = float(max(exc_a, 0) / W)
                pre = trip[:(k + 1) * MULT]
                if len(pre) < 50 and prev_triples is not None:
                    pre = np.vstack([prev_triples[-(200 - len(pre)):], pre])
                if len(pre) < 50:
                    r["p0"] = None
                else:
                    seed = int(hashlib.sha256(f"{s}|{k}|{x}|{iB}".encode()).hexdigest()[:8], 16)
                    r["p0"] = simulate_null(MC[k] / TICK, A / TICK, beyond / TICK, -d, pre, hz - k, n=N_NULL, seed=seed)
                r["f_close_mid"] = float(d * (B - MC[k]) / W)
                rows.append(r)
            if len(done) == len(XS):
                break
    return rows, trip


def boot_session(vals, ses, rng, n):
    u = np.unique(ses); idx = {s: np.flatnonzero(ses == s) for s in u}
    out = np.empty(n)
    for b in range(n):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[s] for s in pick])
        out[b] = vals[ii].mean() if len(ii) else np.nan
    return out


def bh(p, q=0.10):
    p = np.asarray(p); o = np.argsort(p); m = len(p)
    ok = p[o] <= q * (np.arange(1, m + 1) / m)
    k = np.max(np.flatnonzero(ok)) + 1 if ok.any() else 0
    rej = np.zeros(m, bool); rej[o[:k]] = True
    return rej


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO,
                                capture_output=True, text=True).stdout.strip())
    fr = json.loads(FROZEN.read_text(encoding="utf-8"))
    ss = [s["trade_date"] for s in T2.canonical_sessions("ES") if s["trade_date"] <= TB.EXP_END
          and (MID / f"{s['trade_date']}.npz").exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    rows, prev = [], None
    for i, s in enumerate(ss):
        r, prev = session_events(s, prev, fr)
        rows += r
        if i % 20 == 0:
            print(s, i + 1, "/", len(ss), "eventos", len(rows), flush=True)
    (OUT / "eventos.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    ev = [r for r in rows if r["p0"] is not None]
    rng = np.random.default_rng(SEED)
    cells, pvals = [], []
    for x in XS:
        sx = np.array([r["score"] for r in ev if r["x"] == x])
        q1, q2 = np.quantile(sx, [1 / 3, 2 / 3])                     # terciles sin mirar resultados
        for r in ev:
            if r["x"] == x:
                r["tercil"] = "mas" if r["score"] <= q1 else ("menos" if r["score"] > q2 else "medio")
        for estr in ("TBZ", "otros"):
            E = [r for r in ev if r["x"] == x and r["estrato"] == estr]
            exc = np.array([(r["res_mid"] == "completa") - r["p0"]["completa"] for r in E], float)
            ses = np.array([r["session"] for r in E]); ter = np.array([r["tercil"] for r in E])
            top, bot = ter == "mas", ter == "menos"
            b_top = boot_session(exc[top], ses[top], rng, N_BOOT)
            # P2: diferencia por sesión remuestreada conjuntamente
            u = np.unique(ses); idx = {s: np.flatnonzero(ses == s) for s in u}; b_d = np.empty(N_BOOT)
            for b in range(N_BOOT):
                ii = np.concatenate([idx[s] for s in rng.choice(u, len(u))])
                tt, bb = ii[top[ii]], ii[bot[ii]]
                b_d[b] = (exc[tt].mean() if len(tt) else np.nan) - (exc[bb].mean() if len(bb) else np.nan)
            for name, est, bs in (("P1", exc[top].mean(), b_top), ("P2", exc[top].mean() - exc[bot].mean(), b_d)):
                se = float(np.nanstd(bs)); p = float(np.mean(bs <= 0))
                cells.append(dict(prueba=name, x=x, estrato=estr, n_mas=int(top.sum()), n_menos=int(bot.sum()),
                                  estimado=float(est), ic90=[float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))],
                                  ee=se, p_unilateral=p, mde80=2.49 * se))
                pvals.append(p)
    rej = bh(pvals)
    for c, r in zip(cells, rej):
        c["bh_q10"] = bool(r)
    desc = {}
    for x in XS:
        for estr in ("TBZ", "otros"):
            E = [r for r in ev if r["x"] == x and r["estrato"] == estr]
            for ter in ("mas", "medio", "menos"):
                F = [r for r in E if r["tercil"] == ter]
                if not F:
                    continue
                cnt = lambda key, v: float(np.mean([r[key] == v for r in F]))
                desc[f"x{x}_{estr}_{ter}"] = dict(
                    n=len(F), completa_mid=cnt("res_mid", "completa"), falla_mid=cnt("res_mid", "falla"),
                    ambigua_mid=cnt("res_mid", "ambigua"), censurada_mid=cnt("res_mid", "censurada"),
                    p0_completa=float(np.mean([r["p0"]["completa"] for r in F])),
                    p0_censurada=float(np.mean([r["p0"]["censurada"] for r in F])),
                    f_close_mid=float(np.mean([r["f_close_mid"] for r in F])),
                    completa_trade=cnt("res_trade", "completa"),
                    exc_max_W_mediana=float(np.median([r["exc_max_W"] for r in F])))
    rep = dict(manifiesto="docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md", code_commit=head,
               tree_dirty=dirty, sesiones=len(ss), eventos=len(rows), eventos_sin_nulo=len(rows) - len(ev),
               pruebas=cells, sobreviven=[f"{c['prueba']} x={c['x']} {c['estrato']}" for c in cells if c["bh_q10"]],
               descriptivo=desc, costo_ES_puntos_exceso=0.064)
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(eventos=len(rows), sin_nulo=len(rows) - len(ev), sobreviven=rep["sobreviven"],
                          pruebas=[(c["prueba"], c["x"], c["estrato"], c["n_mas"], round(c["estimado"], 3),
                                    [round(v, 3) for v in c["ic90"]], round(c["mde80"], 3)) for c in cells]),
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
