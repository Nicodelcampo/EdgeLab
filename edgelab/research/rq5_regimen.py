"""RQ5-REGIMEN (2026-11-19): la banda de ruido intradía (Zarattini/Chuk; RQ5 de `roboquant_a5.py`) con su grilla de vecinos, para medir si
su neto en el régimen actual (2018–2025) es una meseta o un pico, en cinco índices. Pre-registro: docs/research/rq5_regimen_20261119/PREREGISTRO.md.

Misma regla que `roboquant_a5.RQ5` (verificado contra ella en el test: la definición de fábrica da los mismos eventos):
  sesión RTH de NY (9:30–16:00); en el cierre de cada vela de 30 min desde las 10:00, movimiento desde la apertura |c − open_930| ≥ m × la
  media de ese mismo movimiento en las últimas L sesiones (mismo slot); del lado del VWAP típico de la sesión; la primera señal del día
  hasta el slot `corte` (fábrica: 11:30). Entrada en la vela siguiente (motor único `ejecucion.py`), stop d = max(s × ATR20, 0,5 × banda),
  objetivo tp × d, salida forzada al cierre RTH.
Perillas (definiciones = L × m × corte; ejecuciones = s × tp):
  L ∈ {40, 60, 90} sesiones · m ∈ {0,8; 1,0; 1,2} · corte ∈ {11:00, 11:30, 12:00} · s ∈ {0,30; 0,45; 0,60} · tp ∈ {1,5; 2; 3; cierre}.
Fábrica: L60 · m1,0 · corte 11:30 · s0,45 · tp2.
"""
from __future__ import annotations

from collections import deque
from itertools import product

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny

NOMBRE = "RQ5-REGIMEN"
RTH0, RTH1 = 570, 960
SLOTS = (599, 629, 659, 689, 719)                        # cierres de 10:00, 10:30, 11:00, 11:30 y 12:00 (minuto de apertura de la vela M1)
LS, MS, CORTES = (40, 60, 90), (0.8, 1.0, 1.2), (659, 689, 719)
SS, TPS = (0.30, 0.45, 0.60), (1.5, 2.0, 3.0, 0.0)       # tp 0 = sin objetivo (salida al cierre)
FABRICA = dict(L=60, m=1.0, corte=689, s=0.45, tp=2.0)


def _ndef(L, m, corte): return f"L{L}_m{m:g}_c{corte}"
def _nej(s, tp): return f"s{s:g}_tp{tp:g}"


DEFINICIONES = [_ndef(*x) for x in product(LS, MS, CORTES)]
EJECUCIONES = [("PRECIOS", f"obj_{_nej(s, tp)}", f"stop_{_nej(s, tp)}", "fin") for s, tp in product(SS, TPS)]
DEF_FABRICA = _ndef(FABRICA["L"], FABRICA["m"], FABRICA["corte"])
EJ_FABRICA = _nej(FABRICA["s"], FABRICA["tp"])
FILTROS: dict = {}


def eventos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    mo = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr20 = deque(maxlen=20); hist = {sm: deque(maxlen=max(LS)) for sm in SLOTS}
    prev_close = prev_hi = prev_lo = None; filas = {}
    for s_ in np.unique(ses):
        m_ = np.flatnonzero((ses == s_) & (mo >= RTH0) & (mo < RTH1))
        if not len(m_): continue
        mm = mo[m_]; ab = float(o[m_[0]]); hi, lo, cl = float(h[m_].max()), float(l[m_].min()), float(c[m_[-1]])
        ATR = float(np.mean(atr20)) if len(atr20) >= 3 else (prev_hi - prev_lo if prev_hi is not None else np.nan)
        tp_ = (h[m_] + l[m_] + c[m_]) / 3.0; vwap = np.cumsum(tp_) / np.arange(1, len(m_) + 1)
        hechos = set()
        for sm in SLOTS:
            pos = np.flatnonzero(mm == sm)
            if not len(pos): continue
            p = int(pos[0]); k = int(m_[p]); ck = float(c[k]); mv = abs(ck - ab); hs = list(hist[sm])
            if np.isfinite(ATR) and ATR > 0:
                lado = 1 if ck > ab else -1
                vw_ok = (lado == 1 and ck >= vwap[p]) or (lado == -1 and ck <= vwap[p])
                for L, mult, corte in product(LS, MS, CORTES):
                    nd = _ndef(L, mult, corte)
                    if nd in hechos or sm > corte or len(hs) < 10: continue
                    band = float(np.mean(hs[-L:]))
                    if band > 0 and mv >= mult * band and vw_ok:
                        hechos.add(nd)
                        fin = k + int(RTH1 - 1 - mo[k])            # salida por reloj (como `hasta_cierre` de roboquant): causal
                        f = filas.setdefault(k, dict(k=k, lado=lado, fin=fin, band=band, atr=ATR))
                        if f["band"] != band:                    # mismo k con otra banda (otro L): fila aparte
                            f = filas.setdefault((k, L), dict(k=k, lado=lado, fin=fin, band=band, atr=ATR))
                        f[nd] = True
            hist[sm].append(mv)
        tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close)) if prev_close is not None else hi - lo
        atr20.append(tr); prev_close, prev_hi, prev_lo = cl, hi, lo
    if not filas: return pd.DataFrame(columns=["k", "lado", "ref", "ext", "rg", "fin"] + DEFINICIONES)
    E = pd.DataFrame(list(filas.values()))
    for nd in DEFINICIONES: E[nd] = E[nd].fillna(False).astype(bool) if nd in E else False
    ck = c[E.k.to_numpy()]; lado = E.lado.to_numpy()
    for s, tpm in product(SS, TPS):
        d = np.maximum(s * E.atr.to_numpy(), 0.5 * E.band.to_numpy())
        E[f"stop_{_nej(s, tpm)}"] = ck - lado * d
        E[f"obj_{_nej(s, tpm)}"] = ck + lado * (tpm * d if tpm > 0 else 1e6 * E.atr.to_numpy())
    d0 = np.maximum(FABRICA["s"] * E.atr.to_numpy(), 0.5 * E.band.to_numpy())
    E["ref"] = ck + lado * FABRICA["tp"] * d0; E["ext"] = ck - lado * d0; E["rg"] = d0
    return E.drop(columns=["band"]).reset_index(drop=True)
