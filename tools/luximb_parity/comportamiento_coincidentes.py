"""¿El precio del futuro se comporta distinto en las zonas LUX-IMB que también nacen en el índice (CFD) que en las que no?

Registro: TRIAL_REGISTRY_GLOBAL `luximb_20261022/coincidentes_fut_vs_cfd` (6 pruebas, antes de mirar). EF2 exploratorio.
Medidas sobre M1 del futuro, desde el cierre de la vela creadora hasta el fin de la vida (t1):
  toque    = el precio vuelve a la zona (alcista: low <= top; bajista: high >= bottom)
  relleno  = la atraviesa entera (alcista: low <= bottom; bajista: high >= top)
  reac30   = desde el cierre de la vela del primer toque, cierre 30 min después menos ese cierre, a favor de la zona (puntos)
Contraste: coincidentes − no coincidentes, por tipo (OG, VI); IC 95 % y p bilateral por bootstrap por días; Holm sobre 6.
Uso: python tools/luximb_parity/comportamiento_coincidentes.py <bundle_fut> <bundle_cfd> <desde> <hasta> <out.json>
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").path.dirname(__file__))
import comparar_zonas_futuro_vs_cfd as C  # noqa: E402


def emparejar(zf, zc, base):
    bb = base.reindex(zc.t0 - 60, method="nearest").to_numpy(); lo_f, hi_f = zc.lo.to_numpy() + bb, zc.hi.to_numpy() + bb
    usados, co = set(), np.zeros(len(zf), bool)
    for i, f in zf.iterrows():
        k = np.flatnonzero((zc.label.to_numpy() == f.label) & (zc.dir.to_numpy() == f.dir) & (np.abs(zc.t0.to_numpy() - f.t0) <= 60)
                           & (lo_f <= f.hi) & (hi_f >= f.lo))
        k = [j for j in k if j not in usados]
        if k: usados.add(k[0]); co[i] = True
    return co


def medir(zf, cf):
    t = cf.index.to_numpy(); h, l, c = cf.high.to_numpy(), cf.low.to_numpy(), cf.close.to_numpy(); out = []
    for z in zf.itertuples():
        a = np.searchsorted(t, z.t0, "left"); b = np.searchsorted(t, z.t1, "right")       # vela que abre en t0 = primera posterior
        hh, ll = h[a:b], l[a:b]; bull = z.dir == "BULL"
        tq = np.flatnonzero(ll <= z.hi) if bull else np.flatnonzero(hh >= z.lo)
        rel = bool(((ll <= z.lo) if bull else (hh >= z.hi)).any())
        r30 = np.nan
        if len(tq):
            k = a + tq[0]; j = np.searchsorted(t, t[k] + 1800, "left")
            if j < len(t) and t[j] - t[k] <= 3600: r30 = (c[j] - c[k]) * (1 if bull else -1)
        out.append(dict(toque=float(len(tq) > 0), relleno=float(rel), reac30=r30, dia=int((z.t0 + 6 * 3600) // 86400)))
    return pd.DataFrame(out)


def contraste(x, g, dia, B=4000, seed=7):
    m = np.isfinite(x); x, g, dia = x[m], g[m], dia[m]
    obs = x[g].mean() - x[~g].mean(); d = np.unique(dia); rng = np.random.default_rng(seed); bs = []
    idx = {k: np.flatnonzero(dia == k) for k in d}
    for _ in range(B):
        s = np.concatenate([idx[k] for k in rng.choice(d, len(d))]); gs = g[s]
        if gs.any() and (~gs).any(): bs.append(x[s][gs].mean() - x[s][~gs].mean())
    bs = np.array(bs); p = float(min(1, 2 * min((bs <= 0).mean(), (bs >= 0).mean())))
    return dict(coinciden=float(x[g].mean()), no_coinciden=float(x[~g].mean()), dif=float(obs), ic95=[float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                p=p, n=[int(g.sum()), int((~g).sum())], dias=int(len(d)))


def main():
    pf, pc, d0, d1, out = sys.argv[1:6]
    a = int(pd.Timestamp(d0, tz="UTC").timestamp()); b = int((pd.Timestamp(d1, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    cf, zf = C.cargar(pf, a, b); cc, zc = C.cargar(pc, a, b)
    cf_full = pd.DataFrame(json.load(open(pf, encoding="utf-8"))["bar_series"]["time_1m"]["candles"]).set_index("time")   # vida más allá del período
    com = cf.index.intersection(cc.index)
    base = (cf.close.loc[com] - cc.close.loc[com]).rolling(240, min_periods=30, center=True).median()
    base = base.reindex(sorted(set(cf.index) | set(cc.index))).interpolate().ffill().bfill()
    co = emparejar(zf, zc, base); M = medir(zf, cf_full)
    res = dict(periodo=[d0, d1], registro="luximb_20261022/coincidentes_fut_vs_cfd", pruebas={})
    for lab in ("OG", "VI"):
        s = (zf.label == lab).to_numpy()
        for k in ("toque", "relleno", "reac30"):
            res["pruebas"][f"{lab}/{k}"] = contraste(M[k].to_numpy()[s], co[s], M.dia.to_numpy()[s])
    ps = sorted(res["pruebas"].items(), key=lambda kv: kv[1]["p"]); m = len(ps); mx = 0
    for r, (k, v) in enumerate(ps):
        mx = max(mx, min(1, (m - r) * v["p"])); v["p_holm"] = mx
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k, v in res["pruebas"].items():
        print(f"{k:12} coinciden={v['coinciden']:.3f} no={v['no_coinciden']:.3f} dif={v['dif']:+.3f} IC[{v['ic95'][0]:+.3f},{v['ic95'][1]:+.3f}] p={v['p']:.3f} holm={v['p_holm']:.3f} n={v['n']}")


if __name__ == "__main__":
    main()
