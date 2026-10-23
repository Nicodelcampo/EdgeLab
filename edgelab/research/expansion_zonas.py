"""EXPANSION-ZONAS (2026-10-23): expansiones (impulsos) y zonas LUX-IMB en su extremo inicial, en dos variantes.

Pedido de Nico (2026-10-23): barrer con la metodología del embudo (1) la estrategia de expansiones con zonas en su 25 % inicial
(regla del visor, `docs/research/luximb_parity_20261020/CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`) y (2) la variante con las
OG/VI en el extremo inicial pero POR FUERA de la expansión: antes de su inicio. Spec: docs/research/expansion_zonas_20261023/SPEC.md.

Expansión (causal, en tiempo real): en la vela k el cierre se alejó >= R·ATR14 (ATR de las 14 velas anteriores) del extremo
opuesto A de las últimas `VENTANA` velas (A = mínimo para una expansión alcista, máximo para una bajista). Se marca la PRIMERA
vela que lo cumple; la misma dirección no vuelve a marcar hasta `VENTANA` velas después. Todo con velas <= k.
  DENTRO: zonas creadas entre A y k cuyo punto medio cae en el `FRAC` inicial del rango A -> cierre(k).
  ANTES : zonas creadas antes de A, vivas en A, por fuera de la expansión (más allá de A) y a lo sumo a `FRAC`·rango de A.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research.grilla_generica import Variable

NOMBRE = "EXPANSION-ZONAS"
INDICADORES = ["LUX-IMB"]
VENTANA, FRAC = 30, 0.25
RS = (8.0, 15.0, 25.0)                                    # amplitud mínima en ATR(14) de M1
VARIANTES = ("DENTRO", "ANTES")

VARIABLES = [
    Variable("variante", "var", "grupo", categoria=2),
    Variable("R", "ri", "grupo", categoria=len(RS)),
    Variable("n_zonas", "nz", "ge", cortes=(1.0, 2.0, 3.0, 5.0), piso=True),
    Variable("velocidad", "vel", "extremos", cuantiles=3),            # rango / velas desde A
    Variable("og_vi", "ogvi", "eq_any", categoria=3),                # 0 sólo VI · 1 mezcla · 2 sólo OG
    Variable("posicion", "pos", "extremos", cuantiles=3),            # posición media de las zonas (0 = en A, 1 = en el borde de FRAC)
    Variable("tamano", "tam", "extremos", cuantiles=3),              # altura media de zona / rango
    Variable("vol_rel", "vrel", "extremos", cuantiles=3),            # volumen por vela de la expansión / sesión anterior
]
EJES_ORDINALES = (2,)
# ejecuciones: CONTRA (vuelve hacia A) y FAVOR (continúa). d = |entrada − A|.
EJECUCIONES = ([("CONTRA", en, ob, f) for en in ("E1C", "E1A") for ob in ("A", "50", "ZONAS") for f in (0.2, 0.5, 1.0)] +
               [("FAVOR", en, f"{m}R", f) for en in ("E1C", "E1A") for m in (1, 2, 3) for f in (0.2, 0.5)])
BASE = {"variante": 0, "R": 1, "ejecución": EJECUCIONES.index(("CONTRA", "E1C", "A", 0.2))}       # la regla del visor


def _atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().shift(1).to_numpy()                       # sólo velas anteriores


def disparos(ctx):
    o, h, l, c, v, t, ses, seg = (ctx[x] for x in ("o", "h", "l", "c", "v", "t", "ses", "seg"))
    atr = _atr(h, l, c); lo_w = pd.Series(l).rolling(VENTANA, min_periods=VENTANA).min().to_numpy()
    hi_w = pd.Series(h).rolling(VENTANA, min_periods=VENTANA).max().to_numpy()
    df = pd.DataFrame(dict(ses=ses, v=v)); rate = df.groupby("ses").v.mean(); us = np.array(sorted(rate.index))
    base_rate = pd.Series(np.r_[np.nan, rate.loc[us].to_numpy()[:-1]], index=us).reindex(ses).to_numpy(float)
    filas = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a0, b0 = idx[0], idx[-1] + 1
        Z = AX.zonas(t[a0:b0], o[a0:b0], h[a0:b0], l[a0:b0], c[a0:b0])
        zi, zlo, zhi, zfin, zog = Z["zi"] + a0, Z["zlo"], Z["zhi"], Z["zfin"] + a0, Z["og"]
        for ri, R in enumerate(RS):
            ultimo = {1: -10**9, -1: -10**9}
            for k in range(a0 + VENTANA, b0):
                if not np.isfinite(atr[k]) or atr[k] <= 0: continue
                for d, ext in ((1, lo_w[k]), (-1, hi_w[k])):
                    if (c[k] - ext) * d < R * atr[k] or k - ultimo[d] < VENTANA: continue
                    w = np.arange(k - VENTANA + 1, k + 1)
                    A = int(w[np.argmin(l[w])] if d == 1 else w[np.argmax(h[w])]); pA = float(l[A] if d == 1 else h[A])
                    if ses[A] != ses[k]: continue
                    ultimo[d] = k; rango = abs(c[k] - pA); mid = (zlo + zhi) / 2
                    dentro = (zi > A) & (zi <= k) & ((mid - pA) * d >= 0) & ((mid - pA) * d <= FRAC * rango)
                    antes = (zi < A) & (zfin > A) & (((zhi - pA) * d <= 0) if d == 1 else ((zlo - pA) * d <= 0)) \
                            & ((pA - (zlo if d == 1 else zhi)) * d <= FRAC * rango)
                    for var, m in ((0, dentro), (1, antes)):
                        nz = int(m.sum())
                        if nz == 0: continue
                        pos = float(np.mean(np.abs(mid[m] - pA) / (FRAC * rango)))
                        og = float(zog[m].mean())
                        filas.append(dict(k=k, A=A, pA=pA, d=d, ri=ri, var=var, nz=nz, vel=rango / max(k - A, 1),
                                          ogvi=0 if og == 0 else (2 if og == 1 else 1), pos=pos, tam=float(np.mean(zhi[m] - zlo[m]) / rango),
                                          vrel=(v[A:k + 1].mean() / base_rate[k]) if base_rate[k] > 0 else np.nan, zmid=float(np.mean(mid[m]))))
    return pd.DataFrame(filas)


def niveles(r, ej, ctx):
    lado, en, ob, f = ej; d = int(r["d"]); k = int(r["k"]); e = float(ctx["c"][k]); pA = r["pA"]; tick = ctx["tick"]
    dist = abs(e - pA); lim = 0 if en == "E1C" else 2
    if dist < 2 * tick: return None
    if lado == "CONTRA":
        s = -d; tp = {"A": pA, "50": (e + pA) / 2, "ZONAS": r["zmid"]}[ob]; st = e + d * f * dist
    else:
        s = d; st = e - d * f * dist; tp = e + d * int(ob[0]) * f * dist
    if (tp - e) * s < tick or (e - st) * s < tick: return None
    return k, lim, s, e, st, tp, 0
