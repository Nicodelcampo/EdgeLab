#!/usr/bin/env python3
"""U1-CRUZADO: régimen de rango como explicación del nulo 2023-25 (PREREGISTRO_REGIMEN_RANGO_U1.md). Sólo datos ya en el repo."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).resolve().parents[2] / "docs/research/areas_expansion_20261022/u1"


def regimen():
    d = pd.read_csv(D / "topes/U1_DENSIDAD_20230101_20260930_dias.csv").sort_values("ses").reset_index(drop=True)
    d["rango_20"] = d.rango.shift(1).rolling(20).mean()                          # sólo sesiones anteriores
    med = d.rango_20.expanding().median().shift(1)                                # mediana de los rango_20 anteriores
    d["alto"] = (d.rango_20 > med).astype(object)
    d.loc[d.rango_20.isna() | med.isna(), "alto"] = np.nan
    return d.set_index("ses")["alto"]


def boot(x, s, B=20000, seed=20261024):
    g = pd.DataFrame({"x": x, "s": s}).groupby("s").x.agg(["sum", "count"])
    rng = np.random.default_rng(seed); k = len(g); ii = rng.integers(0, k, (B, k))
    m = g["sum"].to_numpy()[ii].sum(1) / g["count"].to_numpy()[ii].sum(1)
    return [float(np.percentile(m, 5)), float(np.percentile(m, 95))], m


def main():
    reg = regimen(); out = {}
    oos = pd.concat([pd.read_csv(f) for f in sorted((D / "integridad_oos").glob("U1_OOS_US_FIX27_*_operaciones.csv"))])
    oos["alto"] = oos.ses.map(reg)
    for ej in ("E1A/T3/S3", "E1A/T1/S3"):
        x = oos[(oos.ejecucion == ej) & oos.alto.notna()]
        a, b = x[x.alto == True], x[x.alto == False]
        ica, ma = boot(a.neto.values, a.ses.values); icb, mb = boot(b.neto.values, b.ses.values)
        dif = ma - mb
        out[ej] = dict(n_alto=len(a), n_bajo=len(b), media_alto=round(a.neto.mean(), 2), ic90_alto=[round(v, 2) for v in ica],
                       media_bajo=round(b.neto.mean(), 2), ic90_bajo=[round(v, 2) for v in icb],
                       dif=round(a.neto.mean() - b.neto.mean(), 2), ic90_dif=[round(float(np.percentile(dif, 5)), 2), round(float(np.percentile(dif, 95)), 2)],
                       p_dif=round(float((dif <= 0).mean()), 4), mde_alto=round(2.5 * (ica[1] - ica[0]) / 3.29, 1))
    dev = pd.concat([pd.read_csv(f) for f in sorted((D / "topes").glob("U1_TOPES_NQ_*_operaciones.csv"))])
    dev = dev[(dev.ejecucion == "E1A/T3/S3") & (dev.tope == "mult:3") & dev.motivo.isna()]
    dev["alto"] = dev.ses.map(reg)
    out["desarrollo_frac_alto"] = round(float((dev.alto == True).mean()), 3)
    out["desarrollo_media_alto_bajo"] = [round(dev.neto[dev.alto == True].mean(), 2), round(dev.neto[dev.alto == False].mean(), 2),
                                         int((dev.alto == True).sum()), int((dev.alto == False).sum())]
    print(json.dumps(out, indent=1))
    (D / "RESULTADO_REGIMEN_RANGO_U1.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
