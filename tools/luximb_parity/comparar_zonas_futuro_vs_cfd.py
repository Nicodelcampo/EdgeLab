"""¿Las zonas LUX-IMB (OG/VI) del futuro y del CFD nacen en el mismo lugar y momento? Target-free (sólo geometría y tiempo).

Período común; precio del CFD llevado al del futuro con la base estimada minuto a minuto (mediana móvil de close_fut - close_cfd).
Coincidencia: mismo tipo (OG/VI) y dirección, creación a <= `--min` minutos, y superposición de precio (tras la base).
Uso: python tools/luximb_parity/comparar_zonas_futuro_vs_cfd.py <bundle_futuro> <bundle_cfd> <desde> <hasta> <out.json> [--min 1]
"""
import json
import sys

import numpy as np
import pandas as pd


def cargar(p, a, b):
    B = json.load(open(p, encoding="utf-8"))
    c = pd.DataFrame(B["bar_series"]["time_1m"]["candles"]); c = c[(c.time >= a) & (c.time < b)]
    z = pd.DataFrame(B["runs"][0]["zones"]); z = z[(z.t0 >= a) & (z.t0 < b)].copy()
    z["dir"] = z.kind.str.split().str[1]; z["lo"] = z[["top", "bottom"]].min(1); z["hi"] = z[["top", "bottom"]].max(1)
    return c.set_index("time"), z.reset_index(drop=True)


def main():
    pf, pc, d0, d1, out = sys.argv[1:6]; tol = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 1
    a = int(pd.Timestamp(d0, tz="UTC").timestamp()); b = int((pd.Timestamp(d1, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    cf, zf = cargar(pf, a, b); cc, zc = cargar(pc, a, b)
    com = cf.index.intersection(cc.index)
    base = (cf.close.loc[com] - cc.close.loc[com]).rolling(240, min_periods=30, center=True).median()   # base suave (4 h)
    base = base.reindex(sorted(set(cf.index) | set(cc.index))).interpolate().ffill().bfill()
    zc["lo_f"] = zc.lo + base.reindex(zc.t0 - 60, method="nearest").to_numpy()
    zc["hi_f"] = zc.hi + base.reindex(zc.t0 - 60, method="nearest").to_numpy()
    usados = set(); pares = []
    for i, f in zf.iterrows():
        cand = zc[(zc.label == f.label) & (zc.dir == f.dir) & ((zc.t0 - f.t0).abs() <= tol * 60) & (zc.lo_f <= f.hi) & (zc.hi_f >= f.lo)]
        cand = cand[~cand.index.isin(usados)]
        if len(cand):
            j = (cand.t0 - f.t0).abs().idxmin(); usados.add(j); pares.append((i, j))
    res = dict(periodo=[d0, d1], tolerancia_min=tol, minutos_comunes=int(len(com)), base_mediana=float(np.nanmedian(base)),
               correlacion_retornos_1m=float(cf.close.loc[com].diff().corr(cc.close.loc[com].diff())))
    for lab in ("OG", "VI"):
        nf = int((zf.label == lab).sum()); nc = int((zc.label == lab).sum())
        m = sum(1 for i, j in pares if zf.label[i] == lab)
        res[lab] = dict(futuro=nf, cfd=nc, coinciden=m, pct_del_futuro=round(100 * m / nf, 1) if nf else None,
                        pct_del_cfd=round(100 * m / nc, 1) if nc else None)
    res["ejemplos_coincidencia"] = [dict(t=pd.Timestamp(zf.t0[i], unit="s", tz="UTC").isoformat(), tipo=zf.kind[i],
                                         futuro=[zf.lo[i], zf.hi[i]], cfd_en_precio_futuro=[round(zc.lo_f[j], 2), round(zc.hi_f[j], 2)],
                                         dt_min=int((zc.t0[j] - zf.t0[i]) / 60)) for i, j in pares[:15]]
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != "ejemplos_coincidencia"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
