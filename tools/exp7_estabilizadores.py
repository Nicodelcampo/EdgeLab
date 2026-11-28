"""EXP-7 (pre-registro `docs/research/caida_2026_20261125/PREREGISTRO_EXP7_ESTABILIZADORES.md`, contado: 12 pruebas).

Estabilizadoras de la canasta de la mañana (T_NQ, RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ) y entrada en retroceso para T_NQ,
RQ5_NQ y RQ5_ES. Todo en R neto (fricción canónica base de `edgelab/costos.py`), mensual, partición A5 (DESC / REP; HOLDOUT
de A5 y 2026 sólo descriptivos).

  python tools/exp7_estabilizadores.py --out docs/research/caida_2026_20261125/exp7 [--corrida 1|2]
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab import costos  # noqa: E402
from edgelab.holdout import a5_bloque  # noqa: E402

CAND = ROOT / "docs" / "research" / "candidatas_nt8_20261125"
NUEVAS = CAND / "corridas_nt8_nuevas"
M1 = ROOT / "data" / "m1nt8"
NY = "America/New_York"
CANASTA = {"T_NQ": (CAND / "T" / "NT8_T_NQ_fijo1.csv", "NQ"), "RQ5_NQ": (NUEVAS / "NT8_RQ5_NQ.csv", "NQ"),
           "RQ5_ES": (NUEVAS / "NT8_RQ5_ES.csv", "ES"), "ES5N_ES": (NUEVAS / "NT8_ES5N_ES.csv", "ES"),
           "Franklin_NQ": (NUEVAS / "NT8_Franklin_NQ.csv", "NQ")}
ESTAB_NT8 = {"SOMSF_NQ": (CAND / "SOM_sin_finde" / "NT8_SOM_sin_finde_NQ_fijo1.csv", "NQ"),
             "C2VZ_NQ": (NUEVAS / "NT8_C2_VZ_NQ.csv", "NQ"), "C2VZ_ES": (NUEVAS / "NT8_C2_VZ_ES.csv", "ES")}
ESTAB_GRILLA = {"OVN_NQ": ("edgelab.research.overnight_inventario", "NQ", "docs/research/programa_r_20261103/embudo/OVERNIGHT-INV-NQ-R/estado.json"),
                "OVN_ES": ("edgelab.research.overnight_inventario", "ES", "docs/research/programa_r_20261103/embudo/OVERNIGHT-INV-ES-R/estado.json"),
                "KAL_NQ": ("edgelab.research.kalman_fade", "NQ", "docs/research/paquete_20261031/embudo/KALMAN-FADE-NQ/estado.json")}
RETROCESO = {"T_NQ": "T_NQ", "RQ5_NQ": "RQ5_NQ", "RQ5_ES": "RQ5_ES"}
KS = (0.25, 0.50)
MESES = pd.period_range("2020-01", "2026-09", freq="M")


def fric(inst: str) -> float:
    return costos.friccion_rt_puntos(inst, "base")


def ops_nt8(path: Path, inst: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    d = d[d.riesgo_pts > 0].copy()
    d["R"] = (d.pnl_pts - fric(inst)) / d.riesgo_pts
    d["ses"] = d.fecha_int.astype(int)
    return d


def ops_grilla(mod: str, inst: str, estado: str) -> pd.DataFrame:
    import externas_estructurales_a5 as X
    from edgelab.research import grilla_generica as GG
    from edgelab.research.embudo_runners import friccion
    st = json.loads((ROOT / estado).read_text(encoding="utf-8"))["params"]
    ctx = X.cargar_ctx_m1nt8_rapido(inst, 20190102, 20260930, carpeta_datos=M1)
    fr, ex = friccion(inst)
    _, cx = GG.correr(importlib.import_module(mod), ctx, modo="REP", friccion=fr, extra_adverso=ex, cortes=st["cortes"],
                      celdas=st["celdas"], log=lambda s: None)
    o = GG.operaciones_de(cx, st["celdas"], sim=ctx)
    o = o[np.isfinite(o.neto) & (o.riesgo > 0)].copy()
    o["R"] = o.neto / o.riesgo                         # `neto` ya descuenta la fricción canónica (grilla_generica)
    o["ses"] = o.ses.astype(int)
    o["n_celdas"] = len(st["celdas"])
    return o


def mensual(o: pd.DataFrame, n_celdas: int = 1) -> pd.Series:
    m = pd.to_datetime(o.ses.astype(str)).dt.to_period("M")
    s = o.groupby(m).R.sum() / n_celdas                # varias celdas: media de las reglas (cada una 1 R)
    return s.reindex(MESES, fill_value=0.0)


def bloque_mes() -> pd.Series:
    out = {}
    for p in MESES:
        dias = pd.bdate_range(p.start_time, p.end_time)
        b = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in dias])
        b = b[b != "EMBARGO"]
        out[p] = b.mode().iloc[0] if len(b) else "EMBARGO"
    s = pd.Series(out)
    s[[p.year == 2026 for p in s.index]] = "2026"
    return s


def retroceso(o: pd.DataFrame, inst: str, k: float) -> pd.DataFrame:
    """Orden límite a entrada − lado·k·riesgo, 30 min desde la entrada y antes de la salida original; mismo stop; salida original."""
    d = pd.read_parquet(M1 / f"{inst}_M1_nonadj_utc.parquet", columns=["high", "low"],
                        filters=[("datetime", ">=", pd.Timestamp("2019-01-01")), ("datetime", "<", pd.Timestamp("2026-10-01"))])
    idx = pd.DatetimeIndex(d.index).tz_localize("UTC").as_unit("ns").asi8
    hi, lo = d.high.to_numpy(float), d.low.to_numpy(float)
    en = pd.to_datetime(o.en_ny).dt.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()
    ex = pd.to_datetime(o.ex_ny).dt.tz_localize(NY, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()
    side = o.side.to_numpy(int); e0 = o.entry_price.to_numpy(float); rk = o.riesgo_pts.to_numpy(float); xp = o.exit_price.to_numpy(float)
    lim = e0 - side * k * rk
    be = (o.exit_name.astype(str).str.upper() == "BE_STOP").to_numpy()
    R = np.zeros(len(o)); lleno = np.zeros(len(o), bool)
    for i in range(len(o)):
        # la vela de la entrada original ya pasó (la entrada se llenó en su apertura): se busca desde la vela siguiente
        a = np.searchsorted(idx, en[i], side="right")
        b = np.searchsorted(idx, min(en[i] + 30 * 60 * 10**9, ex[i]), side="left")
        if b <= a: continue
        seg = lo[a:b] <= lim[i] if side[i] > 0 else hi[a:b] >= lim[i]
        if not seg.any(): continue
        lleno[i] = True
        # corrida 2 (auditoría): el break-even de la variante está en SU entrada, no en la original
        sal = lim[i] if be[i] else xp[i]
        R[i] = (side[i] * (sal - lim[i]) - fric(inst)) / (rk[i] * (1 - k))
    out = o.copy(); out["R"] = np.where(lleno, R, 0.0); out["lleno"] = lleno
    return out


def _betacf(a: float, b: float, x: float) -> float:
    """Fracción continua de la beta incompleta (Lentz; Numerical Recipes 6.4). Sin scipy (no está en el entorno de CLAUDE.md)."""
    tiny = 1e-300; qab = a + b; qap = a + 1.0; qam = a - 1.0
    c = 1.0; d = 1.0 - qab * x / qap; d = tiny if abs(d) < tiny else d; d = 1.0 / d; h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = tiny if abs(d) < tiny else d; c = 1.0 + aa / c; c = tiny if abs(c) < tiny else c; d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = tiny if abs(d) < tiny else d; c = 1.0 + aa / c; c = tiny if abs(c) < tiny else c; d = 1.0 / d
        de = d * c; h *= de
        if abs(de - 1.0) < 1e-14: break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2): return math.exp(lb) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lb) * _betacf(b, a, 1 - x) / b


def t_sf(t: float, df: float) -> float:
    """P(T > t) de la t de Student con df grados de libertad."""
    if not np.isfinite(t) or df <= 0: return float("nan")
    p = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return p if t > 0 else 1.0 - p


def t_uni(x) -> tuple:
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 3 or x.std(ddof=1) == 0: return float("nan"), float("nan")
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    return float(t), float(t_sf(t, len(x) - 1))


def mde(x) -> float:
    x = np.asarray(x, float)
    return float(2.49 * x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else float("nan")   # 80 % de potencia, α 0,05 unilateral


def bh(p: dict, q=0.10) -> dict:
    ks = sorted(p, key=lambda k: (np.inf if not np.isfinite(p[k]) else p[k])); m = len(ks); ok = set(); last = 0
    for i, k in enumerate(ks, 1):
        if np.isfinite(p[k]) and p[k] <= q * i / m: last = i
    for i, k in enumerate(ks, 1):
        if i <= last: ok.add(k)
    return {k: k in ok for k in p}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--corrida", type=int, default=1)
    a = ap.parse_args(argv); a.out.mkdir(parents=True, exist_ok=True)
    blo = bloque_mes()
    can_ops = {n: ops_nt8(p, i) for n, (p, i) in CANASTA.items()}
    can = pd.DataFrame({n: mensual(o) for n, o in can_ops.items()})
    cesta = can.mean(axis=1)
    malo = cesta < 0
    series = {n: mensual(ops_nt8(p, i)) for n, (p, i) in ESTAB_NT8.items()}
    for n, (mod, inst, est) in ESTAB_GRILLA.items():
        o = ops_grilla(mod, inst, est); series[n] = mensual(o, int(o.n_celdas.iloc[0]))
    res = dict(corrida=a.corrida, meses_por_bloque=blo.value_counts().to_dict(), estabilizadoras={}, retroceso={})
    for bloque in ("DESC", "REP", "HOLDOUT", "2026"):
        sel = blo == bloque
        res.setdefault("canasta", {})[bloque] = dict(meses=int(sel.sum()), malos=int((malo & sel).sum()),
                                                     R_mes=round(float(cesta[sel].mean()), 3))
    p_desc = {}
    for n, s in series.items():
        r = {}
        for bloque in ("DESC", "REP", "HOLDOUT", "2026"):
            sel = blo == bloque
            xm, xb = s[sel & malo], s[sel & ~malo]
            t, p = t_uni(xm)
            r[bloque] = dict(R_mes=round(float(s[sel].mean()), 3), R_malos=round(float(xm.mean()), 3), R_buenos=round(float(xb.mean()), 3),
                             dif=round(float(xm.mean() - xb.mean()), 3), corr=round(float(np.corrcoef(s[sel], cesta[sel])[0, 1]), 3),
                             t_malos=round(t, 2), p_malos=round(p, 4), mde_malos=round(mde(xm), 3), n_malos=int(len(xm)))
        res["estabilizadoras"][n] = r; p_desc[n] = r["DESC"]["p_malos"]
    pas = bh(p_desc)
    for n in res["estabilizadoras"]:
        d = res["estabilizadoras"][n]
        d["pasa_BH_DESC"] = pas[n]
        d["confirma_REP"] = bool(pas[n] and d["REP"]["R_malos"] > 0 and d["REP"]["p_malos"] <= 0.10)
    p_desc = {}
    for n, base in RETROCESO.items():
        o = can_ops[base]; inst = CANASTA[base][1]; mb = mensual(o)
        for k in KS:
            v = retroceso(o, inst, k); mv = mensual(v); dif = mv - mb
            r = dict(llenado=round(float(v.lleno.mean()), 3), R_op_original=round(float(o.R.mean()), 4),
                     R_op_llenadas=round(float(v.R[v.lleno].mean()), 4), R_op_originales_de_las_llenadas=round(float(o.R[v.lleno.values].mean()), 4))
            for bloque in ("DESC", "REP", "HOLDOUT", "2026"):
                sel = blo == bloque; t, p = t_uni(dif[sel])
                r[bloque] = dict(R_mes_original=round(float(mb[sel].mean()), 3), R_mes_variante=round(float(mv[sel].mean()), 3),
                                 dif_mes=round(float(dif[sel].mean()), 3), t=round(t, 2), p=round(p, 4), mde=round(mde(dif[sel]), 3))
            nom = f"{n}_PB{int(k * 100)}"; res["retroceso"][nom] = r; p_desc[nom] = r["DESC"]["p"]
    pas = bh(p_desc)
    for n in res["retroceso"]:
        d = res["retroceso"][n]; d["pasa_BH_DESC"] = pas[n]
        d["confirma_REP"] = bool(pas[n] and d["REP"]["dif_mes"] > 0 and d["REP"]["p"] <= 0.10)
    pd.DataFrame(series).assign(canasta=cesta, bloque=blo).to_csv(a.out / f"SERIES_MENSUALES_corrida{a.corrida}.csv")
    (a.out / f"EXP7_corrida{a.corrida}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
