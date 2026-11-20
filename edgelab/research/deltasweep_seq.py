"""DELTASWEEP-SEQ (2026-11-14, pedido de Nico): los disparos de DeltaSweep NQ (`edgelab/research/deltasweep_nq.py`, barrido de delta +
flip, detector 1-tick causal con agresor por bid/ask) medidos en la CADENA ESTÁNDAR (motor único, R neto, costos canónicos). Lo que mejor
salió en las corridas exploratorias de Nico (Kaggle, 13-nov, fuera del contador) fue esperar 2 o 3 disparos seguidos en la misma
dirección: acá se pre-registra esa forma con su control (el disparo suelto). Pre-registro: docs/research/deltasweep_20261114/PREREGISTRO.md.

Construcción: los disparos salen de los ticks de cada día (`POR_BLOQUE`, con bid/ask: `LIBRO`); un disparo entra a la primera vela M1 cuyo
cierre es ≥ su instante; la secuencia (2 o 3 seguidos misma dirección, separados ≤ gap s, misma sesión) se arma sobre los disparos del
filtro (V4 ancho o estricto, spread ≤ 2 ticks). Entrada a mercado en la vela siguiente a favor del disparo; stop y objetivo fijos en ticks
(D = 160 ticks: 160/160, 160/320, 200/400 y 80/160)."""
from __future__ import annotations

import numpy as np
import pandas as pd

LIBRO = True
NOMBRE = "DELTASWEEP-SEQ"
CARPETA = "docs/research/deltasweep_20261114"
DEPENDENCIAS_KERNEL = ("edgelab.research.deltasweep_nq",)
GATES = {"V4W": 64, "V4S": 8, "V2A": 2}          # V4 ancho, V4 estricto, absorción (las tres compuertas de su corrida 3)
SEQS = {"S1": (1, 0), "S2g60": (2, 60), "S2g600": (2, 600), "S3g600": (3, 600)}
REGS = {"AM": (930, 1200), "RTH": (930, 1600)}
D_TICKS = 160
DEFINICIONES = [f"{g}|{s}|{r}" for g in GATES for s in SEQS for r in REGS]
CONTROL = {f"{g}|{s}|{r}": f"{g}|S1|{r}" for g in GATES for s in SEQS if s != "S1" for r in REGS}
EJECUCIONES = [("MERCADO", 1.0, 1.0, 0, 0), ("MERCADO", 1.0, 2.0, 0, 0), ("MERCADO", 1.25, 2.5, 0, 0), ("MERCADO", 0.5, 1.0, 0, 0)]
PERIODOS = [("DESC", 20250805, 20260331), ("REP", 20260401, 20260930)]


def POR_BLOQUE(B: pd.DataFrame, tick: float) -> pd.DataFrame:
    from edgelab.research import deltasweep_nq as DS
    bid = B["bid"].to_numpy() if "bid" in B else None; ask = B["ask"].to_numpy() if "ask" in B else None
    d = DS.detectar_eventos_tick(B.ts_ns.to_numpy(), B.px.to_numpy(), B.vol.to_numpy(), bid, ask, tick_size=tick)
    return pd.DataFrame(dict(t_ns=d["ts_ns"].astype(np.int64), dir=d["dir"].astype(np.int64), vm=d["var_mask"].astype(np.int64),
                             sp=d["spread_ticks"].astype(float), hhmm=d["ny_hhmm"].astype(np.int64),
                             px=d["dot_tick"].astype(float) * tick, xt=d["ext_tick"].astype(float) * tick,
                             ses=np.full(len(d["ts_ns"]), int(B.sesion.iloc[0]) if len(B) else 0, np.int64)))


def secuencias(Z: pd.DataFrame, bit: int, n: int, gap_s: int) -> np.ndarray:
    """Máscara causal: el disparo es el n-ésimo seguido en la misma dirección (≤ gap s del anterior, misma sesión) entre los del filtro."""
    m = ((Z.vm.to_numpy() & bit) > 0) & (Z.sp.to_numpy() <= 2)            # sp < 0 = sin quote válido (sólo datos sintéticos)
    out = np.zeros(len(Z), bool)
    if n == 1: return m
    t, d, s = Z.t_ns.to_numpy(), Z.dir.to_numpy(), Z.ses.to_numpy(); racha, pt, pd_, ps = 0, -1, 0, -1
    for i in np.flatnonzero(m):
        if s[i] == ps and t[i] - pt <= gap_s * 1_000_000_000 and d[i] == pd_: racha += 1
        else: racha = 1
        out[i] = racha == n; pt, pd_, ps = t[i], d[i], s[i]
    return out


def a_velas(ctx, t_ns: np.ndarray) -> np.ndarray:
    tc = (np.asarray(ctx["t"], float) * 1e9).astype(np.int64)
    k = np.searchsorted(tc, t_ns, side="left")                          # primera vela cuyo cierre es >= instante del disparo
    return np.where(k < len(tc), k, -1)


def eventos(ctx) -> pd.DataFrame:
    Z = ctx.get("por_bloque"); c = np.asarray(ctx["c"], float); tick = float(ctx["tick"])
    cols = ["k", "lado", "ref", "ext", "rg"] + DEFINICIONES
    if Z is None or not len(Z): return pd.DataFrame(columns=cols)
    Z = Z.sort_values("t_ns", kind="mergesort").reset_index(drop=True)
    k = a_velas(ctx, Z.t_ns.to_numpy()); hh = Z.hhmm.to_numpy()
    defs = {}
    for g, bit in GATES.items():
        for s, (n, gap) in SEQS.items():
            ms = secuencias(Z, bit, n, gap)
            for r, (a, b) in REGS.items(): defs[f"{g}|{s}|{r}"] = ms & (hh >= a) & (hh < b) & (k >= 0)
    algun = np.any(np.column_stack(list(defs.values())), axis=1)
    if not algun.any(): return pd.DataFrame(columns=cols)
    kk = k[algun]; lado = Z.dir.to_numpy()[algun]; D = D_TICKS * tick
    E = pd.DataFrame(dict(k=kk, lado=lado, ref=c[kk] + lado * D, ext=c[kk], rg=np.full(len(kk), D)))
    for nm, m in defs.items(): E[nm] = m[algun]
    E = E.groupby(["k", "lado"], as_index=False).agg({**{x: "first" for x in ("ref", "ext", "rg")}, **{x: "max" for x in DEFINICIONES}})
    return E.sort_values("k", kind="mergesort").reset_index(drop=True)
