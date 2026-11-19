#!/usr/bin/env python3
"""T-REGIMEN: meseta de parámetros y PBO del T de FundedSync en NQ (pre-registro docs/research/t_regimen_20261118/PREREGISTRO.md).

Reusa el kernel de `tools/m1_largo.py` (`cargar`, `_kernel_fs`), `fundedsyncstack.correr_modulo("T", ms, **cfg)`, la fricción canónica
(`embudo_runners.friccion`), `g2.pbo_cscv` y `g2.parameter_sensitivity`.

  python tools/t_regimen.py grilla     # 81 variantes 2008 → 2026-09 -> GRILLA_OPS.csv.gz (reanudable por variante)
  python tools/t_regimen.py decidir    # meseta + PBO en 2021-02-10 → 2026-09-29 -> RESULTADO.json
"""
import itertools, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/t_regimen_20261118"
PARCIAL = ROOT / "data/t_regimen"
QUIEBRE, FIN = "2021-02-10", "2026-09-29"
GRILLA = dict(orb_bars=[10, 15, 20], knn_k=[10, 15, 25], knn_flip_probability_threshold=[0.60, 0.65, 0.70],
              admission_min_close_location=[0.50, 0.60, 0.70])
FABRICA = (15, 15, 0.65, 0.60)


def variantes():
    return list(itertools.product(*GRILLA.values()))


def _nombre(v):
    return "orb%d_k%d_th%.2f_cl%.2f" % v


def grilla():
    from registro_global import exigir_contada
    exigir_contada("docs/research/t_regimen_20261118/PREREGISTRO.md")
    from datos import ruta
    from m1_largo import cargar, _kernel_fs
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    D = cargar("NQ", ruta("M1NT8")); D = D[D.index >= "2008-01-01"]
    ms = F.build_multi_series(F.load_m1_data(_kernel_fs(0.0)["a_utc"](D), end="2026-10-01"), tz_input="UTC"); fr = float(friccion("NQ")[0])
    mm = D.index.hour * 60 + D.index.minute; PARCIAL.mkdir(parents=True, exist_ok=True)
    for v in variantes():
        f = PARCIAL / f"{_nombre(v)}.csv"
        if f.exists(): continue
        ob, k, th, cl = v
        x = F.correr_modulo("T", ms, orb_bars=ob, orb_end_minute_et=570 + ob, knn_k=k, knn_flip_probability_threshold=th,
                            admission_min_close_location=cl)
        tt = pd.to_datetime(x.entry_time_utc, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        orb = D[(mm >= 570) & (mm < 570 + ob)]; dd = orb.index.normalize()
        rg = ((orb.h.groupby(dd).max() - orb.l.groupby(dd).min()) * 1.25).clip(2.0, 100.0)
        o = pd.DataFrame(dict(dia=tt.dt.normalize(), neto=pd.to_numeric(x.pnl_pts, errors="coerce").values - fr))
        o["riesgo"] = rg.reindex(o.dia).to_numpy(float); o["R"] = o.neto / o.riesgo; o["variante"] = _nombre(v)
        o.to_csv(f, index=False); print(_nombre(v), len(o), round(o[o.dia >= QUIEBRE].R.mean(), 3), flush=True)
    G = pd.concat([pd.read_csv(PARCIAL / f"{_nombre(v)}.csv") for v in variantes()])
    G.to_csv(DIR / "GRILLA_OPS.csv.gz", index=False)


def decidir():
    from edgelab.research import g2
    G = pd.read_csv(DIR / "GRILLA_OPS.csv.gz", parse_dates=["dia"]); G = G[np.isfinite(G.R)]
    nombres = [_nombre(v) for v in variantes()]; fab = _nombre(FABRICA)
    W = G[(G.dia >= QUIEBRE) & (G.dia <= FIN)]; A = G[G.dia < QUIEBRE]
    r_w = W.groupby("variante").R.mean().reindex(nombres); r_a = A.groupby("variante").R.mean().reindex(nombres)
    M = W.assign(mes=W.dia.dt.to_period("M")).pivot_table(index="mes", columns="variante", values="R", aggfunc="sum").reindex(columns=nombres).fillna(0.0)
    pbo = g2.pbo_cscv(M.to_numpy().tolist(), s=16)
    pbo = pbo if isinstance(pbo, (int, float)) else (pbo.get("pbo") if isinstance(pbo, dict) else pbo[0])
    vecinos = []
    for i, (a, b) in enumerate(zip(variantes()[nombres.index(fab)], FABRICA)):
        vals = list(GRILLA.values())[i]; j = vals.index(b)
        for jj in (j - 1, j + 1):
            if 0 <= jj < len(vals): v = list(FABRICA); v[i] = vals[jj]; vecinos.append(_nombre(tuple(v)))
    med_vec, pos_vec, n_vec = g2.parameter_sensitivity(r_w.to_dict(), fab, vecinos)
    frac_pos = float((r_w > 0).mean()); med = float(r_w.median()); rf = float(r_w[fab])
    meseta = frac_pos >= 0.70 and med >= 0.5 * rf and (med_vec or 0) > 0
    ver = "SOBREAJUSTE_PROBABLE" if (pbo > 0.5 or frac_pos < 0.5) else ("REGIMEN_ROBUSTO" if (meseta and pbo < 0.3) else "INTERMEDIO")
    out = dict(preregistro="docs/research/t_regimen_20261118/PREREGISTRO.md", ventana=[QUIEBRE, FIN], fabrica=fab, R_fabrica=rf,
               frac_variantes_positivas=frac_pos, mediana_grilla=med, vecinos=dict(mediana=med_vec, positivos=pos_vec, n=n_vec),
               meseta=bool(meseta), pbo=float(pbo), veredicto=ver, meses=int(len(M)),
               R_por_variante_2021=r_w.round(4).to_dict(), R_por_variante_antes=r_a.round(4).to_dict(),
               antes_frac_positivas=float((r_a > 0).mean()), antes_R_fabrica=float(r_a[fab]))
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("R_fabrica", "frac_variantes_positivas", "mediana_grilla", "vecinos", "meseta", "pbo", "veredicto",
                                          "antes_frac_positivas", "antes_R_fabrica")}, default=float))


if __name__ == "__main__":
    {"grilla": grilla, "decidir": decidir}[sys.argv[1]]()
