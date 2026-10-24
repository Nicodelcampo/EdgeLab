"""M4: penetracion de vuelta dentro del impulso. Reglas en
`docs/research/luximb_parity_20261020/PREREGISTRO_M4_PENETRACION_LUXIMB_NQ_20261020.md` (no cambiar sin enmienda).

Uso: python tools/luximb_parity/luximb_m4_penetracion.py <out.json> <bundle.json>:<impulsos.json> [...]
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from luximb_outcomes import REP_START, TOPE_MIN, GAP_S, TICK, COMM, boot  # noqa: E402

ALTURAS = (0.25, 0.382, 0.5, 0.618, 0.75)


def eventos(ev, t25, h25, l25, c25):
    s = 1 if ev["dir"] == "up" else -1
    A, X = ev["p0"], ev["p1"]; R = abs(X - A)
    a = int(np.searchsorted(t25, ev["tc"], "left")); b = a
    while b < len(t25) and t25[b] <= ev["tc"] + TOPE_MIN * 60 and (b == a or t25[b] - t25[b - 1] <= GAP_S):
        b += 1
    hh, ll = h25[a:b], l25[a:b]
    out = {}
    for p in ALTURAS:
        L = X - p * R * s
        tq = np.flatnonzero((ll <= L) if s > 0 else (hh >= L))
        if not len(tq):
            out[p] = None; continue
        k0 = tq[0] + 1
        hA = np.flatnonzero((ll[k0:] <= A) if s > 0 else (hh[k0:] >= A)); hX = np.flatnonzero((hh[k0:] >= X) if s > 0 else (ll[k0:] <= X))
        kA = hA[0] if len(hA) else 10**9; kX = hX[0] if len(hX) else 10**9
        if kA == kX == 10**9:
            res = "tiempo"; px = (c25[b - 1] if b > a else L) + s * TICK
        elif kX <= kA:
            res = "X"; px = X + s * TICK
        else:
            res = "A"; px = A
        out[p] = dict(res=res, pnl=-s * (px - L) - COMM)
    return out


def main():
    out_path = sys.argv[1]; rows = []
    for pair in sys.argv[2:]:
        bpath, ipath = pair.rsplit(":", 1)
        B = json.load(open(bpath, encoding="utf-8")); I = json.load(open(ipath, encoding="utf-8"))
        T = B["bar_series"]["tick_25"]["candles"]
        t25 = np.array([c["time"] for c in T]); h25 = np.array([c["high"] for c in T]); l25 = np.array([c["low"] for c in T]); c25 = np.array([c["close"] for c in T])
        for grupo, evs in (("T", I["impulsos"]), ("C", I["control"])):
            for ev in evs:
                if ev["tc"] >= REP_START: raise SystemExit("evento fuera de descubrimiento")
                dia = str(pd.Timestamp(ev["tc"], unit="s", tz="UTC").tz_convert("America/New_York").date())
                for p, r in eventos(ev, t25, h25, l25, c25).items():
                    if r: rows.append(dict(contrato=B["meta"]["contract"], grupo=grupo, esT=grupo == "T", dia=dia, altura=p, dir=ev["dir"], **r))
        del B, T
    df = pd.DataFrame(rows); df["a"] = (df.res == "A").astype(float)
    rng = np.random.default_rng(20261021)
    res, fam = {}, {}
    for p in ALTURAS:
        d = df[df.altura == p]; t = d[d.esT]; c = d[~d.esT]
        ha = boot(d, "a", "esT", rng); hb = boot(t, "pnl", None, rng)
        res[str(p)] = dict(n_T=len(t), n_C=len(c), dias_T=t.dia.nunique(), P_A_T=round(t.a.mean(), 4), P_A_C=round(c.a.mean(), 4),
                           P_X_T=round((t.res == "X").mean(), 4), P_X_C=round((c.res == "X").mean(), 4),
                           pnl_T_media=round(t.pnl.mean(), 3), pnl_C_media=round(c.pnl.mean(), 3),
                           Ha_PA_T_menos_C=ha, Hb_pnl_T=hb, MDE80_pp=round(2.8 * ha["se"] * 100, 1))
        fam[f"{p}_a"] = ha["p"]; fam[f"{p}_b"] = hb["p"]
    order = sorted(fam, key=fam.get); holm = {}; run = 0.0
    for k, name in enumerate(order):
        run = max(run, min(1.0, (len(order) - k) * fam[name])); holm[name] = round(run, 4)
    out = dict(preregistro="PREREGISTRO_M4_PENETRACION_LUXIMB_NQ_20261020.md", alturas=res, p_holm=holm)
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    df.to_csv(out_path.replace(".json", "_eventos.csv"), index=False)
    for p in ALTURAS:
        r = res[str(p)]
        print(f"{p:5}: nT={r['n_T']:3} nC={r['n_C']:4} P(A) T={r['P_A_T']:.3f} C={r['P_A_C']:.3f} dif={r['Ha_PA_T_menos_C']['est']:+.3f} "
              f"IC{r['Ha_PA_T_menos_C']['ic95']} MDE={r['MDE80_pp']}pp | pnl T={r['pnl_T_media']:+.2f} IC{r['Hb_pnl_T']['ic95']} C={r['pnl_C_media']:+.2f} "
              f"| holm a={holm[f'{p}_a']} b={holm[f'{p}_b']}")


if __name__ == "__main__":
    main()
