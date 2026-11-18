"""Campañas con la partición HOLDOUT-A5 (2026-11-18): lo común a toda familia que descubre y confirma sobre M1 largo.

Enmienda `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`; primer uso `tools/luximb_a5.py` (de ahí se extrajo).
  bloques(ses)            DESC / REP / HOLDOUT / EMBARGO / TERMINAL de cada sesión (`holdout.a5_bloque`)
  con_desenlace(E)        máscara de eventos cuyos desenlaces se pueden calcular sin acta: sólo DESC y REP
  cluster(ses, r)         media por operación, error estándar agrupado por sesión y p unilateral (H1: media > 0)
  diferencia(...)         celda − control con bootstrap por sesión (comparten sesiones y a veces eventos)
  calibrar_por_sesion     criterio de M1 contra ticks (`papel_m1_20261115/VALIDACION.md`, el de `atras_m1`)
  bh(ps, q)               Benjamini–Hochberg
Los eventos (sin retornos) se calculan de corrido en toda la ventana; los desenlaces de HOLDOUT/EMBARGO sólo con la apertura
registrada (`holdout_ventanas.registrar_apertura`) y la reserva de LORD++.
"""
from __future__ import annotations

from math import erfc, sqrt

import numpy as np
import pandas as pd

VISIBLES = ("DESC", "REP")
MIN_CORR, MIN_SES_COMUNES = 0.5, 30


def bloques(ses) -> np.ndarray:
    from edgelab.holdout import a5_bloque
    ses = np.asarray(ses); u = np.unique(ses); m = {int(s): a5_bloque(int(s)) for s in u}
    return np.array([m[int(s)] for s in ses])


def con_desenlace(E: pd.DataFrame, col: str = "bloque") -> np.ndarray:
    return E[col].isin(VISIBLES).to_numpy()


def sf(z: float) -> float:
    """Cola superior de la normal estándar (sin scipy)."""
    return float(0.5 * erfc(z / sqrt(2)))


def cluster(ses, r):
    """(media por operación, error estándar agrupado por sesión, p unilateral de media > 0)."""
    df = pd.DataFrame(dict(s=np.asarray(ses), r=np.asarray(r, float))); g = df.groupby("s").r.agg(["sum", "count"]); n = g["count"].sum()
    if n == 0: return float("nan"), float("nan"), 1.0
    m = g["sum"].sum() / n; se = float(np.sqrt(((g["sum"] - m * g["count"]) ** 2).sum()) / n)
    return float(m), se, sf(m / se) if se > 0 else 1.0


def diferencia(ses_a, r_a, ses_b, r_b, B: int = 2000, seed: int = 7):
    """(a − b, error estándar, p unilateral de a − b > 0) con bootstrap por sesión."""
    a = pd.DataFrame(dict(s=ses_a, r=r_a)).groupby("s").r.agg(["sum", "count"])
    b = pd.DataFrame(dict(s=ses_b, r=r_b)).groupby("s").r.agg(["sum", "count"])
    S = np.array(sorted(set(a.index) | set(b.index))); a = a.reindex(S, fill_value=0); b = b.reindex(S, fill_value=0)
    obs = a["sum"].sum() / a["count"].sum() - b["sum"].sum() / b["count"].sum()
    rng = np.random.default_rng(seed); A = a.to_numpy(float); Bm = b.to_numpy(float); bs = np.empty(B)
    for i in range(B):
        ix = rng.integers(0, len(S), len(S)); sa, sb = A[ix].sum(0), Bm[ix].sum(0); bs[i] = sa[0] / sa[1] - sb[0] / sb[1]
    se = float(bs.std(ddof=1))
    return float(obs), se, sf(obs / se) if se > 0 else 1.0


def bh(ps, q: float):
    from edgelab.research.banco_eventos import bh as _bh
    return _bh(list(ps), q)


def calibrar_por_sesion(t: dict, m: dict) -> dict:
    """M1 contra ticks por sesión ({sesión: R sumado}): mismo signo, diferencia ≤ 1 EE combinado y correlación > 0,5 en ≥ 30 sesiones."""
    ses = sorted(set(t) | set(m)); x = np.array([t.get(s, 0.0) for s in ses]); y = np.array([m.get(s, 0.0) for s in ses])
    com = sorted(set(t) & set(m))
    ee = float(np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))) if len(ses) > 2 else float("nan")
    corr = float(np.corrcoef([t[s] for s in com], [m[s] for s in com])[0, 1]) if len(com) > 2 else float("nan")
    out = dict(sesiones=len(ses), comunes=len(com), ticks_media=float(x.mean()), m1_media=float(y.mean()), ee=ee, corr=corr)
    out["calibra"] = bool(len(com) >= MIN_SES_COMUNES and np.sign(x.mean()) == np.sign(y.mean()) and abs(x.mean() - y.mean()) <= ee
                          and corr > MIN_CORR)
    return out


def frac_anios_positivos(ses, r) -> float:
    s = pd.Series(np.asarray(r, float)).groupby(np.asarray(ses) // 10000).sum()
    return float((s > 0).mean()) if len(s) else float("nan")


# ------------------------------------------------------------------------------------- evaluación de celdas (DESC / REP)
FRIC_R_MAX = 0.08                                       # subconjunto operable (fricción / riesgo inicial)


def evaluar(T: pd.DataFrame, bloque: str, defs, ejecs, fric_pts: float, control: dict | None = None, limpios=None, pares=None) -> dict:
    """Por (definición, ejecución): n, R bruto (EE por sesión, p unilateral), años positivos, neto, fricción en R media, neto del
    subconjunto operable; y por (definición − su control, ejecución): diferencia con bootstrap por sesión. `T` trae `ses`, `bloque`,
    una columna booleana por definición y `r_<ejec>`/`k_<ejec>` del motor (`ejecucion.desenlaces`). Con varios instrumentos, la
    fricción en R de cada fila va en `f_<ejec>` (si no, `fric_pts / k_<ejec>`). `pares` [(definición, ejecución)] limita las pruebas a
    esos pares (cada variante con su propia salida); los controles se evalúan con la ejecución de su definición."""
    T = T[T.bloque == bloque]; out = {}; control = control or {}
    for e in ejecs:
        base = {}
        for d in list(defs) + sorted(set(control.values()) - set(defs)):          # los controles se evalúan siempre (son la base)
            if pares and (d, e) not in pares and not any((dd, e) in pares for dd, cc in control.items() if cc == d): continue
            g = T[T[d].astype(bool) & T[f"r_{e}"].notna() & (T[f"k_{e}"] > 0)]
            r = g[f"r_{e}"].to_numpy(float); ses = g.ses.to_numpy(np.int64)
            fr = g[f"f_{e}"].to_numpy(float) if f"f_{e}" in g else fric_pts / g[f"k_{e}"].to_numpy(float)   # f_: fricción en R por fila
            m, se, p = cluster(ses, r); op = fr <= FRIC_R_MAX
            v = dict(n=int(len(r)), R_bruto=m, se=se, p=p, frac_anios_pos=frac_anios_positivos(ses, r),
                     R_neto=float((r - fr).mean()) if len(r) else None, fric_R_media=float(fr.mean()) if len(r) else None,
                     n_operable=int(op.sum()), R_neto_operable=float((r - fr)[op].mean()) if op.any() else None)
            if limpios: v["R_bruto_limpios"] = float(r[(ses >= limpios[0]) & (ses <= limpios[1])].mean()) if ((ses >= limpios[0]) & (ses <= limpios[1])).any() else None
            if d in defs and (not pares or (d, e) in pares): out[f"{d}|{e}"] = v
            base[d] = (ses, r)
        for d, c in control.items():
            if pares and (d, e) not in pares: continue
            if d in base and c in base and len(base[d][1]) and len(base[c][1]):
                dif, se, p = diferencia(*base[d], *base[c]); out[f"{d}-{c}|{e}"] = dict(dif_bruto=dif, se=se, p=p)
    return out


def nominar(res: dict, q: float = 0.10, calibra=None, min_frac_anios: float = 0.6) -> list:
    """BH q sobre todas las pruebas; nominada = BH + media > 0 + (absolutas) ≥ 60 % de años positivos + calibra (si se da)."""
    nombres = list(res); rech = bh([res[k]["p"] for k in nombres], q); nom = []
    for k, rj in zip(nombres, rech):
        v = res[k]; v["bh"] = bool(rj); v["calibra"] = True if calibra is None else bool(calibra(k))
        efecto = v.get("R_bruto", v.get("dif_bruto"))
        v["nominada"] = bool(rj and v["calibra"] and efecto is not None and efecto > 0 and v.get("frac_anios_pos", 1.0) >= min_frac_anios)
        if v["nominada"]: nom.append(k)
    return nom


# ------------------------------------------------------------------------------------- K49: potencia antes de gastar REP/HOLDOUT
def plan_lectura(familia: str, ses_desc, r_desc, n_dias: int, factor: float = 0.5, nivel: float | None = None) -> dict:
    """K49 (2026-11-18): potencia de UNA lectura (REP u holdout) calculada en DÍAS, no en filas: efecto = `factor` × la media por
    sesión de DESC (suma por sesión), desvío por sesión de DESC, N = sesiones de la lectura, α = nivel LORD++ de la familia. GEX gastó
    REP con potencia ≈ 0,3 porque se contaron filas instrumento × día como independientes."""
    from edgelab.research import holdout_ventanas as HV
    if nivel is None:
        from edgelab.funnel.libro_lord import LibroLord
        nivel = LibroLord().nivel(familia)
    s = pd.Series(np.asarray(r_desc, float)).groupby(np.asarray(ses_desc)).sum()
    ef = factor * float(s.mean()); sd = float(s.std(ddof=1)) if len(s) > 1 else float("nan")
    if not (ef > 0 and sd > 0): return dict(potencia=0.0, efecto=ef, sd_dia=sd, n_dias=int(n_dias), alfa=nivel, problemas=["efecto de DESC ≤ 0"])
    pl = HV.plan_potencia("fijo", ef, sd, n=int(n_dias), alfa=nivel, fuente_efecto=f"{factor} × media por sesión de DESC (K49)")
    return dict(pl, sd_dia=sd, n_dias=int(n_dias))


POTENCIA_LECTURA_MIN = 0.8


def exigir_potencia(plan: dict, que: str) -> None:
    if plan.get("potencia", 0.0) < POTENCIA_LECTURA_MIN:
        raise ValueError(f"K49: {que}: potencia {plan.get('potencia', 0):.2f} < {POTENCIA_LECTURA_MIN} en días "
                         f"(efecto {plan.get('efecto'):.4g}, sd/día {plan.get('sd_dia'):.4g}, días {plan.get('n_dias')}): seguir explorando en DESC "
                         "o juntar más N antes de gastar la lectura")
