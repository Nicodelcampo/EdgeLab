"""M9: distancia y tiempo de la vuelta + zonas tomadas / restantes -> ¿llega a A antes que a X?
Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M9_DISTANCIA_TIEMPO_ZONAS_TOMADAS_20261020.md (no cambiar sin enmienda).
Uso: python tools/luximb_parity/luximb_m9.py <out.json> <INSTR>:<bundle.json>:<impulsos.json> [...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from luximb_outcomes import GAP_S, REP_START, TICK, TOPE_MIN  # noqa: E402

DS = (0.25, 0.50); RAPIDO_S = 900; VIDA = 500; NB = 10000
COMM = {"NQ": 0.225, "ES": 0.09}


def eventos(inst, bpath, ipath):
    B = json.load(open(bpath, encoding="utf-8")); I = json.load(open(ipath, encoding="utf-8"))
    cd = B["bar_series"]["time_1m"]["candles"]; tm = np.array([c["time"] for c in cd])
    idx = {int(x): i for i, x in enumerate(tm)}
    Z = B["runs"][0]["zones"]
    zi = np.array([idx[z["available_ts"] - 60] for z in Z]); zav = np.array([z["available_ts"] for z in Z])
    zmid = np.array([(z["top"] + z["bottom"]) / 2 for z in Z]); ztop = np.array([z["top"] for z in Z]); zbot = np.array([z["bottom"] for z in Z])
    T = B["bar_series"]["tick_25"]["candles"]
    t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
    del B, T, cd
    rows = []
    for ev in I["impulsos"]:
        if ev["tc"] >= REP_START: raise SystemExit("evento fuera de descubrimiento")
        s = 1 if ev["dir"] == "up" else -1; A, X = ev["p0"], ev["p1"]; R = abs(X - A); kb = ev["ic"]
        if R <= 0: continue
        a = int(np.searchsorted(t25, ev["tc"], "left")); b = a
        while b < len(t25) and t25[b] <= ev["tc"] + TOPE_MIN * 60 and (b == a or t25[b] - t25[b - 1] <= GAP_S):
            b += 1
        if b <= a: continue
        hh, ll, cc = h25[a:b], l25[a:b], c25[a:b]
        p25 = int(np.searchsorted(t25, ev["tc"] - 3600, "left"))
        vol_pre = float(h25[p25:a].max() - l25[p25:a].min()) if a > p25 else np.nan
        sup = np.flatnonzero((hh > X) if s > 0 else (ll < X)); k_sup = sup[0] if len(sup) else 10**9   # supera X
        viva_marca = (zi <= kb) & (kb - zi <= VIDA)
        pos = s * (zmid - X) / R                                       # 0 = X, -1 = A, -2 = un R detras de A
        ny = pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York")
        for d in DS:
            L = X - d * R * s
            tq = np.flatnonzero((ll <= L) if s > 0 else (hh >= L))
            if not len(tq) or tq[0] >= k_sup: continue                  # toca d antes de superar X
            k = int(tq[0]); t_tq = t25[a + k]
            # zonas tomadas: interiores, vivas en la marca, atravesadas enteras por la vuelta hasta el toque
            ext = ll[:k + 1].min() if s > 0 else hh[:k + 1].max()
            interior = viva_marca & (pos <= 0) & (pos >= -1)
            tomadas = interior & ((ext <= zbot) if s > 0 else (ext >= ztop))
            # zonas restantes: vivas en el toque, entre el precio y A (sin tomar) + franja detras de A
            kt = int(np.searchsorted(tm, t_tq, "right")) - 1
            viva_tq = (zav <= t_tq) & (kt - zi <= VIDA)
            rest = viva_tq & (((pos < -d) & (pos >= -1) & ~tomadas) | ((pos < -1) & (pos >= -2)))
            # desenlace desde la vela siguiente al toque
            k0 = k + 1
            hA = np.flatnonzero((ll[k0:] <= A) if s > 0 else (hh[k0:] >= A)); hX = np.flatnonzero((hh[k0:] >= X) if s > 0 else (ll[k0:] <= X))
            kA = hA[0] if len(hA) else 10**9; kX = hX[0] if len(hX) else 10**9
            if kA == kX == 10**9: res, px = "tiempo", cc[-1] + s * TICK
            elif kX <= kA: res, px = "X", X + s * TICK
            else: res, px = "A", A
            rows.append(dict(inst=inst, contrato=I["bundle"], dia=str(ny.date()), d=d, rapido=bool(t_tq - ev["tc"] <= RAPIDO_S),
                             t_min=(t_tq - ev["tc"]) / 60, k_tomadas=int(tomadas.sum()), m_restantes=int(rest.sum()), R=R, vol_pre=vol_pre,
                             res=res, yA=int(res == "A"), pnl=-s * (px - L) - COMM[inst]))
    return rows


def contraste(d, grupo_col, rng):
    """P(A) grupo 1 - grupo 0, ponderado por estratos (vol_pre x R terciles); bootstrap por dia."""
    d = d[d[grupo_col].isin([0, 1])]

    def fn(x):
        tot = acc = 0.0
        for _, g in x.groupby("estr"):
            g1, g0 = g[g[grupo_col] == 1], g[g[grupo_col] == 0]
            if len(g1) and len(g0):
                w = len(g1) + len(g0); acc += w * (g1.yA.mean() - g0.yA.mean()); tot += w
        return acc / tot if tot else np.nan
    days = d.dia.unique(); ix = {k: np.flatnonzero(d.dia.values == k) for k in days}
    full = fn(d); bs = np.array([fn(d.iloc[np.concatenate([ix[k] for k in rng.choice(days, len(days))])]) for _ in range(NB)])
    return dict(est=round(float(full), 4), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                p_bilateral=float(min(1, 2 * min(np.nanmean(bs <= 0), np.nanmean(bs >= 0)))), se=float(np.nanstd(bs)),
                n1=int((d[grupo_col] == 1).sum()), n0=int((d[grupo_col] == 0).sum()),
                pnl_g1=round(float(d.loc[d[grupo_col] == 1, "pnl"].mean()), 3), pnl_g0=round(float(d.loc[d[grupo_col] == 0, "pnl"].mean()), 3))


def grupos(d, cortes):
    km, m33, m67 = cortes
    d = d.copy()
    d["gk"] = np.where((d.k_tomadas >= km) & (d.k_tomadas > 0), 1, 0)
    d["gm"] = np.where(d.m_restantes <= m33, 1, np.where(d.m_restantes >= m67, 0, -1))
    return d


def main():
    out = sys.argv[1]; rows = []
    for trip in sys.argv[2:]:
        inst, bp, ip = trip.split(":", 2); rows += eventos(inst, bp, ip); print(inst, ip, len(rows), flush=True)
    df = pd.DataFrame(rows); df = df[df.vol_pre.notna()].reset_index(drop=True)
    df.to_csv(out.replace(".json", "_eventos.csv"), index=False)
    rng = np.random.default_rng(20261027); res = {"NQ": {}, "ES_confirmacion": {}}
    for inst in ("NQ", "ES"):
        x = df[df.inst == inst]
        cv, cr = np.quantile(x.vol_pre, [1 / 3, 2 / 3]), np.quantile(x.R, [1 / 3, 2 / 3])
        df.loc[x.index, "estr"] = [f"{u}{v}" for u, v in zip(np.digitize(x.vol_pre, cv), np.digitize(x.R, cr))]
    nq = df[df.inst == "NQ"]; cortes = {}; fam = {}
    for d_ in DS:
        for rap in (True, False):
            celda = f"d{d_}_{'rapido' if rap else 'lento'}"; c = nq[(nq.d == d_) & (nq.rapido == rap)]
            ct = (float(c.k_tomadas[c.k_tomadas > 0].median()) if (c.k_tomadas > 0).any() else 1.0,
                  float(np.quantile(c.m_restantes, 1 / 3)), float(np.quantile(c.m_restantes, 2 / 3)))
            if ct[2] <= ct[1]: ct = (ct[0], ct[1], ct[1] + 1)
            cortes[celda] = ct; g = grupos(c, ct)
            res["NQ"][celda] = dict(n=len(c), dias=c.dia.nunique(), P_A=round(c.yA.mean(), 4), pnl_medio=round(c.pnl.mean(), 3), cortes_k_m33_m67=ct,
                                    H_k=contraste(g, "gk", rng), H_m=contraste(g, "gm", rng))
            fam[f"{celda}_H_k"] = res["NQ"][celda]["H_k"]["p_bilateral"]; fam[f"{celda}_H_m"] = res["NQ"][celda]["H_m"]["p_bilateral"]
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, n in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[n])); holm[n] = round(run, 4)
    es = df[df.inst == "ES"]
    for n, p in holm.items():
        if p < 0.05:                                                     # confirmacion unica en ES con cortes y signo de NQ
            celda, h = n.rsplit("_H_", 1); d_ = float(celda.split("_")[0][1:]); rap = celda.endswith("rapido")
            c = grupos(es[(es.d == d_) & (es.rapido == rap)], cortes[celda]); r = contraste(c, "g" + h, rng)
            signo_nq = np.sign(res["NQ"][celda]["H_" + h]["est"])
            r["confirma"] = bool((r["ic95"][0] > 0) if signo_nq > 0 else (r["ic95"][1] < 0)); res["ES_confirmacion"][n] = r
    out_d = dict(manifiesto="MANIFIESTO_M9_DISTANCIA_TIEMPO_ZONAS_TOMADAS_20261020.md", n_eventos=dict(df.inst.value_counts()), resultados=res, p_holm_NQ=holm,
                 MDE80_pp={f"{c}_{h}": round(280 * res['NQ'][c][h]['se'], 1) for c in res["NQ"] for h in ("H_k", "H_m")})
    json.dump(out_d, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out_d, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
