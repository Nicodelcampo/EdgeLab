"""DELTASWEEP-PAT (2026-11-14, pedido de Nico): PATRONES de disparos DeltaSweep en NQ para tener más casos (más potencia) y filtrarlos
bien. Pre-registro: docs/research/deltasweep_20261114/PREREGISTRO_PAT.md. Cadena estándar (motor único, R neto, costos canónicos).

Disparos (`deltasweep_seq.POR_BLOQUE`, 1-tick causal con agresor bid/ask) por compuerta: PERM (todos los permisivos, la más densa),
V4W (ráfaga ancha), V3 (adaptativa z), V5 (barre el swing y recupera), spread ≤ 2 ticks.
Patrón = n disparos seguidos en la misma dirección y sesión, cada uno a ≤ g s del anterior, con una forma:
  any       sin condición de precio;
  escalera  cada disparo mejor que el anterior a favor (compras con precios más altos: el barrido ya no hace nuevos extremos);
  dpX       dispersión (máx − mín del precio) de los disparos ANTERIORES al de la entrada ≤ X ticks (X = 8, 16, 32);
  dtX       dispersión de TODOS los disparos del patrón, incluido el de la entrada, ≤ X ticks.
Se dispara una vez, en el n-ésimo. n ∈ {2, 3, 4, 5}, g ∈ {10, 30, 60, 300} s, NY 09:30–12:00 o 09:30–16:00. Control: n = 1 de la misma
compuerta y régimen. Entrada a favor de los disparos:
  MERCADO  vela M1 siguiente; stop/objetivo fijos sobre D = 160 ticks: 80/160, 160/160, 160/320, 240/480;
  LIMITE   retroceso de 0,25·D o 0,5·D desde el cierre de la vela del patrón, stop D y objetivo 2·D desde el límite;
  PRECIOS  stop ESTRUCTURAL 4 ticks detrás del extremo de los disparos del patrón, objetivo 2× esa distancia."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import deltasweep_seq as DS

LIBRO = True
NOMBRE = "DELTASWEEP-PAT"
CARPETA = "docs/research/deltasweep_20261114/pat"
DEPENDENCIAS_KERNEL = ("edgelab.research.deltasweep_nq",)
POR_BLOQUE = DS.POR_BLOQUE
GATES = {"PERM": -1, "V4W": 64, "V3": 4, "V5": 16}
NS = (1, 2, 3, 4, 5)
GAPS = (10, 30, 60, 300)                                 # s entre disparos (v2: se agregan 10 y 30 s; se saca 900, pedido de Nico)
DISP = (8, 16, 32)                                       # dispersión en precio (ticks) de los disparos del patrón
FORMAS = ("any", "escalera") + tuple(f"dp{x}" for x in DISP) + tuple(f"dt{x}" for x in DISP)
REGS = {"AM": (930, 1200), "RTH": (930, 1600)}
D_TICKS = 160
DEFINICIONES = ([f"{g}|n1|{r}" for g in GATES for r in REGS] +
                [f"{g}|n{n}|g{gp}|{f}|{r}" for g in GATES for n in NS[1:] for gp in GAPS for f in FORMAS for r in REGS])
CONTROL = {f"{g}|n{n}|g{gp}|{f}|{r}": f"{g}|n1|{r}" for g in GATES for n in NS[1:] for gp in GAPS for f in FORMAS for r in REGS}
EJECUCIONES = ([("MERCADO", sl, tp, 0, 0) for sl, tp in ((0.5, 1.0), (1.0, 1.0), (1.0, 2.0), (1.5, 3.0))] +
               [("LIMITE", x, 1.0, 2.0) for x in (0.25, 0.5)] + [("PRECIOS", "obj_pat", "stop_pat")])
PERIODOS = [("DESC", 20250805, 20260331), ("REP", 20260401, 20260930)]


def patrones(Z: pd.DataFrame, bit: int, n: int, gap: int, forma: str, tick: float):
    """Máscara causal (el n-ésimo disparo del patrón) y el extremo de los disparos del patrón (para el stop estructural)."""
    m = (((Z.vm.to_numpy() & bit) > 0) if bit > 0 else np.ones(len(Z), bool)) & (Z.sp.to_numpy() <= 2)
    out = np.zeros(len(Z), bool); xt_pat = np.full(len(Z), np.nan)
    t, d, s, px, xt = (Z[c].to_numpy() for c in ("t_ns", "dir", "ses", "px", "xt"))
    racha = []
    for i in np.flatnonzero(m):
        ok = bool(racha) and s[i] == s[racha[-1]] and d[i] == d[racha[-1]] and t[i] - t[racha[-1]] <= gap * 1_000_000_000
        if ok and forma == "escalera": ok = d[i] * (px[i] - px[racha[-1]]) > 0
        racha = racha + [i] if ok else [i]
        if len(racha) == n:
            if forma.startswith("dp") and (px[racha[:-1]].max() - px[racha[:-1]].min()) > int(forma[2:]) * tick: continue
            if forma.startswith("dt") and (px[racha].max() - px[racha].min()) > int(forma[2:]) * tick: continue
            out[i] = True; xt_pat[i] = xt[racha].min() if d[i] == 1 else xt[racha].max()
    return out, xt_pat


def eventos(ctx) -> pd.DataFrame:
    Z = ctx.get("por_bloque"); c = np.asarray(ctx["c"], float); tick = float(ctx["tick"])
    cols = ["k", "lado", "ref", "ext", "rg", "obj_pat", "stop_pat"] + DEFINICIONES
    if Z is None or not len(Z): return pd.DataFrame(columns=cols)
    Z = Z.sort_values("t_ns", kind="mergesort").reset_index(drop=True)
    k = DS.a_velas(ctx, Z.t_ns.to_numpy()); hh = Z.hhmm.to_numpy(); defs = {}; xpat = np.full(len(Z), np.nan)
    for g, bit in GATES.items():
        for n in NS:
            for gp in (GAPS if n > 1 else (0,)):
                for f in (FORMAS if n > 1 else ("any",)):
                    mp, xp = patrones(Z, bit, n, gp, f, tick)
                    xpat = np.where(np.isnan(xpat) & mp, xp, xpat)
                    for r, (a, b) in REGS.items():
                        nm = f"{g}|n1|{r}" if n == 1 else f"{g}|n{n}|g{gp}|{f}|{r}"
                        defs[nm] = mp & (hh >= a) & (hh < b) & (k >= 0)
    algun = np.any(np.column_stack(list(defs.values())), axis=1)
    if not algun.any(): return pd.DataFrame(columns=cols)
    kk = k[algun]; lado = Z.dir.to_numpy()[algun]; D = D_TICKS * tick; ck = c[kk]
    xp = np.where(np.isnan(xpat[algun]), Z.xt.to_numpy()[algun], xpat[algun])
    stop = xp - lado * 4 * tick; dist = np.maximum(lado * (ck - stop), 8 * tick); stop = ck - lado * dist
    E = pd.DataFrame(dict(k=kk, lado=lado, ref=ck + lado * D, ext=ck, rg=np.full(len(kk), D), obj_pat=ck + lado * 2 * dist, stop_pat=stop))
    E = pd.concat([E, pd.DataFrame({nm: m[algun] for nm, m in defs.items()}, index=E.index)], axis=1)
    E = E.groupby(["k", "lado"], as_index=False).agg({**{x: "first" for x in ("ref", "ext", "rg", "obj_pat", "stop_pat")},
                                                     **{x: "max" for x in DEFINICIONES}})
    return E.sort_values("k", kind="mergesort").reset_index(drop=True)
