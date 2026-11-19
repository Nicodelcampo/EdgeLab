#!/usr/bin/env python3
"""AUDITORIA-EXCLUSIONES (pre-registro docs/research/auditoria_exclusiones_fs_20261119/PREREGISTRO.md): T y R de FundedSync en NQ con las
listas fijas de fechas del vendedor desactivadas; R de los días excluidos contra días al azar. Reusa m1_largo (T con T_FECHAS, el kernel
`operaciones`), neto_pistas (_ms, _ops, _cfg, FABRICA) y la fricción canónica.

  python tools/auditoria_exclusiones_fs.py      # → docs/research/auditoria_exclusiones_fs_20261119/RESULTADO.json y OPS.csv.gz
"""
import json, sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/auditoria_exclusiones_fs_20261119"; PRE = "docs/research/auditoria_exclusiones_fs_20261119/PREREGISTRO.md"
FERIADOS_R = {20240704, 20241224, 20250120, 20250703, 20250829}          # feriados / medias jornadas (regla aplicable en vivo)


def _t_sin_exclusiones(D):
    from edgelab.research import fundedsyncstack as F
    from edgelab.research.embudo_runners import friccion
    from m1_largo import _kernel_fs, T_FECHAS
    ns = _kernel_fs(friccion("NQ")[0])
    ns["F"] = SimpleNamespace(MODULOS={"T": F.MODULOS["T"]}, build_multi_series=F.build_multi_series, load_m1_data=F.load_m1_data,
                              correr_modulo=lambda k, ms, **kw: F.correr_modulo(k, ms, **{**T_FECHAS, **kw, "use_exclusion_calendars": False}))
    return ns["operaciones"](D)["T"]


def _perm(r_dias, r_exc, k=10000, seed=7):
    rng = np.random.default_rng(seed); x = np.asarray(r_dias, float); obs = float(np.sum(r_exc))
    sims = np.array([x[rng.choice(len(x), len(r_exc), replace=False)].sum() for _ in range(k)])
    return obs, float((sims <= obs).mean())


def main():
    from registro_global import exigir_contada
    from edgelab.research.fundedsyncstack import modulos_w_n_t as M, modulos_r_z_e_q as Q
    from edgelab.research.embudo_runners import friccion
    from datos import ruta
    from m1_largo import cargar
    import neto_pistas as NP
    exigir_contada(PRE)
    fr = float(friccion("NQ")[0]); res = {}
    # T
    exc_t = set(M.FTM_DEGRADED_DATA_EXCLUSION_DATE_KEYS) | set(M.FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS)
    D = cargar("NQ", ruta("M1NT8")); T = _t_sin_exclusiones(D); T = T[T.riesgo >= 2].copy()
    T["ses"] = pd.to_datetime(T.dia).dt.strftime("%Y%m%d").astype(int); T["R"] = T.neto / T.riesgo
    T["excluida"] = T.ses.isin(exc_t); T["tipo"] = np.where(T.ses.isin(M.FTM_CONTRACT_ROLL_EXCLUSION_DATE_KEYS), "vencimiento", np.where(T.excluida, "degradado", ""))
    v = T[(T.ses >= 20200101)]; d = v.groupby("ses").R.sum(); e = d[d.index.isin(exc_t)]
    obs, pct = _perm(d[~d.index.isin(exc_t)], e)
    r21 = v[v.ses >= 20210210]; con, sin = float(r21.R.mean()), float(r21[~r21.excluida].R.mean())
    res["T"] = dict(dias_excluidos_con_operacion=int(len(e)), R_dias_excluidos=obs, R_medio_dia_excluido=float(e.mean()) if len(e) else None,
                    percentil=pct, por_tipo=v[v.excluida].groupby("tipo").R.agg(["size", "mean"]).round(4).to_dict("index"),
                    R_2021_con=con, R_2021_sin=sin, cambio=con - sin)
    # R (fábrica, stop 0,25 × ATR20)
    F, D2, ms = NP._ms("NQ"); cfg = NP._cfg("R", NP.FABRICA["R"])
    o = NP._ops(F, "R", ms, D2, {**cfg, "blocked_sessions": ()}); s = 0.25 * o.atr20
    o["R"] = (np.where(o.mae_pts >= s, -s, o.pnl_pts) - fr) / s; o["ses_i"] = pd.to_datetime(o.ses).dt.strftime("%Y%m%d").astype(int)
    blq = set(Q.ATR_PHASE_BLOCKED_SESSIONS); o["bloqueada"] = o.ses_i.isin(blq); o["feriado"] = o.ses_i.isin(FERIADOS_R)
    v = o[o.ses_i >= 20200101]; d = v.groupby("ses_i").R.sum(); e = d[d.index.isin(blq)]
    obs, pct = _perm(d[~d.index.isin(blq)], e)
    w = v[v.ses_i >= 20210210]
    res["R"] = dict(dias_bloqueados_con_operacion=int(len(e)), R_dias_bloqueados=obs, detalle={int(k): round(float(x), 3) for k, x in e.items()},
                    percentil=pct, R_2021_con=float(w.R.mean()), R_2021_sin=float(w[~w.bloqueada].R.mean()), cambio=float(w.R.mean() - w[~w.bloqueada].R.mean()))
    for k in ("T", "R"):
        r = res[k]; r["veredicto"] = "SESGO_VENDEDOR" if (r["percentil"] < 0.10 or r["cambio"] < -0.02) else "INOCUA"
    pd.concat([T.assign(modulo="T")[["ses", "R", "excluida", "modulo"]],
               o.assign(modulo="R", ses=o.ses_i, excluida=o.bloqueada)[["ses", "R", "excluida", "modulo"]]]).to_csv(DIR / "OPS.csv.gz", index=False)
    (DIR / "RESULTADO.json").write_text(json.dumps(dict(preregistro=PRE, resultados=res), indent=1, default=float)); print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
