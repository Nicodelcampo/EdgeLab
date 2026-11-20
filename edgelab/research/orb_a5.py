"""ORB-A5 (2026-11-18): variantes de Opening Range Breakout diseñadas con lo medido en EdgeLab y la literatura.
Diseño: docs/research/orb_a5_20261118/DISENO.md; pre-registro: docs/research/orb_a5_20261118/PREREGISTRO.md.

Contrato de `edgelab/research/tablas.py`. Hora de Nueva York, sesión RTH 9:30–16:00 sobre M1 de NT8. La decisión es al cierre de la vela
M1 `k`; la entrada es el primer tick de la vela siguiente (motor). Salida al cierre RTH con la ejecución PRECIOS de 4 elementos (la
columna `fin` = k + los minutos hasta las 15:59, causal; con minutos faltantes la salida puede quedar unos minutos después de las 16). Unidades relativas al rango de apertura o al rango diario (K36).

Definiciones:
  O1  ORB 5 min (Zarattini-Aziz 2023): dirección de la vela 9:30–9:35, stop en su lado opuesto, objetivo 10R o cierre
  O2  ORB 15 min: primer cierre M1 fuera del rango 9:30–9:45 (9:45–12:00) a favor; stop en el lado opuesto; cierre
  O3  ORB 30 min con contracción (Crabel): rango 9:30–10:00 / ATR20 ≤ percentil 30 de 120 sesiones previas; stop en la mitad; cierre
      O3N: la misma ruptura sin contracción (complemento)
  O4  O2 a favor del gap (|gap| ≥ 0,1·ATR20)                       O4N: O2 sin esa condición (complemento)
  O5  O2 con volumen 9:30–9:45 ≥ 1,5× su media de 20 sesiones     O5N: complemento
  O6  momentum de la primera media hora (Gao et al. 2018): signo cierre previo → 10:00; entrada 15:30; stop 1× rango medio de 30 min
  O7  Noise Area (Zarattini-Aziz-Barbon 2024): ruptura de la banda de ruido de 14 días y del VWAP en :00/:30; stop VWAP o banda
  O8  ORB 15 fallido: ruptura por cierre y vuelta adentro en ≤ 15 min → fade al lado opuesto; stop extremo + 0,05·rango
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny

NOMBRE = "ORB-A5"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["O1", "O2", "O3", "O4", "O5", "O6", "O7", "O8"]
CONTROL = {"O3": "O3N", "O4": "O4N", "O5": "O5N"}
RTH0, RTH1, BRK_FIN = 570, 960, 720
LEJOS = 1000.0                                       # objetivo inalcanzable (en riesgos): la salida es al cierre RTH


def eventos(ctx) -> pd.DataFrame:
    o, h, l, c, v, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "v", "ses"))
    o, h, l, c, v = (x.astype(float) for x in (o, h, l, c, v)); mo = minuto_ny(ctx["t"])
    filas = []; prev = None; rangos = deque(maxlen=120); atr = deque(maxlen=20); vol15 = deque(maxlen=20); r30 = deque(maxlen=20)
    ruido = deque(maxlen=14)

    def hasta_cierre(k):                             # vela de salida: k + los minutos que faltan hasta 15:59 (sólo depende de k: causal)
        return int(k) + int(RTH1 - 1 - mo[k])

    def fila(defn, k, lado, stop, obj, fin=None, **extra):
        filas.append(dict(k=int(k), lado=int(lado), ref=float(obj), ext=float(stop), rg=abs(float(c[k]) - float(stop)) or 1e-9,
                          obj=float(obj), stop=float(stop), fin=hasta_cierre(k), **{defn: True}, **extra))

    for s in np.unique(ses):
        m = np.flatnonzero((ses == s) & (mo >= RTH0) & (mo < RTH1))
        if not len(m):
            continue
        mm = mo[m]; fin = None; ab = o[m[0]]
        ATR = np.mean(atr) if len(atr) >= 10 else np.nan
        # ---------- O1: vela de 5 min ----------
        i5 = m[mm < RTH0 + 5]
        if len(i5) >= 3 and prev is not None and mo[i5[-1]] == RTH0 + 4:          # vela de 5 min COMPLETA (decide a las 9:34)
            O5, C5, H5, L5 = o[i5[0]], c[i5[-1]], h[i5].max(), l[i5].min()
            if H5 > L5 and abs(C5 - O5) >= 0.05 * (H5 - L5):
                lado = 1 if C5 > O5 else -1; stop = L5 if lado == 1 else H5
                fila("O1", i5[-1], lado, stop, C5 + lado * 10 * abs(C5 - stop), fin)
        # ---------- rango de 15 min: O2, O4, O5, O8 ----------
        i15 = m[mm < RTH0 + 15]; post = m[(mm >= RTH0 + 15) & (mm < BRK_FIN)]
        if len(i15) >= 10 and prev is not None and len(post):
            H15, L15 = h[i15].max(), l[i15].min(); R15 = H15 - L15; v15 = v[i15].sum()
            br = next((q for q in post if c[q] > H15 or c[q] < L15), None)
            if br is not None and R15 > 0:
                lado = 1 if c[br] > H15 else -1; stop = L15 if lado == 1 else H15
                gap = ab - prev["c"]
                a_favor = ATR == ATR and abs(gap) >= 0.1 * ATR and np.sign(gap) == lado
                vol_ok = len(vol15) >= 10 and v15 >= 1.5 * np.mean(vol15)
                fila("O2", br, lado, stop, c[br] + lado * LEJOS * abs(c[br] - stop), fin, O4=bool(a_favor), O4N=not a_favor,
                     O5=bool(vol_ok), O5N=(len(vol15) >= 10) and not vol_ok)
                # O8: vuelta adentro en ≤ 15 min
                ext = h[br] if lado == 1 else l[br]
                for q in post[(post > br) & (post <= br + 15)]:
                    ext = max(ext, h[q]) if lado == 1 else min(ext, l[q])
                    if (lado == 1 and c[q] < H15) or (lado == -1 and c[q] > L15):
                        st = ext + lado * 0.05 * R15; ob = L15 if lado == 1 else H15
                        if -lado * (ob - c[q]) > 0 and -lado * (c[q] - st) > 0: fila("O8", q, -lado, st, ob, fin)
                        break
            vol15.append(v15)
        # ---------- O3: rango de 30 min con contracción ----------
        i30 = m[mm < RTH0 + 30]; post30 = m[(mm >= RTH0 + 30) & (mm < BRK_FIN)]
        if len(i30) >= 20 and prev is not None and len(post30) and ATR == ATR:
            H30, L30 = h[i30].max(), l[i30].min(); R30 = H30 - L30; rel = R30 / ATR
            p30 = np.percentile(rangos, 30) if len(rangos) >= 60 else np.nan
            br = next((q for q in post30 if c[q] > H30 or c[q] < L30), None)
            if br is not None and R30 > 0 and p30 == p30:
                lado = 1 if c[br] > H30 else -1; mid = (H30 + L30) / 2; contr = rel <= p30
                filas.append(dict(k=int(br), lado=lado, ref=c[br] + lado * LEJOS * abs(c[br] - mid), ext=mid, rg=abs(c[br] - mid) or 1e-9,
                                  obj=c[br] + lado * LEJOS * abs(c[br] - mid), stop=mid, fin=hasta_cierre(br), O3=bool(contr), O3N=not contr))
            rangos.append(rel)
        # ---------- O6: momentum de la primera media hora ----------
        k10 = m[mm == RTH0 + 29]; k1529 = m[mm == 929]
        if prev is not None and len(k10) and len(k1529) and len(r30) >= 10:
            ret = c[k10[0]] - prev["c"]
            if ret != 0:
                lado = 1 if ret > 0 else -1; d = float(np.mean(r30)); k = int(k1529[0])
                fila("O6", k, lado, c[k] - lado * d, c[k] + lado * LEJOS * d, fin)
        g30 = (mm - RTH0) // 30
        r30.append(np.mean([h[m[g30 == g]].max() - l[m[g30 == g]].min() for g in np.unique(g30)]))
        # ---------- O7: Noise Area ----------
        if prev is not None and len(ruido) >= 10:
            sig = np.nanmean(np.vstack(ruido), axis=0)                                   # |c/apertura − 1| medio por minuto RTH
            arriba, abajo = max(ab, prev["c"]), min(ab, prev["c"])
            pv = np.cumsum(c[m] * v[m]); vv = np.cumsum(v[m])
            for j, q in enumerate(m):
                mq = mo[q]
                if mq < RTH0 + 30 or (mq + 1 - RTH0) % 30 != 0 or mq >= RTH1 - 1: continue
                s_ = sig[mq - RTH0]; vw = pv[j] / vv[j] if vv[j] > 0 else np.nan
                ub, lb = arriba * (1 + s_), abajo * (1 - s_)
                if c[q] > ub and c[q] > vw:
                    st = max(vw, ub); fila("O7", q, 1, st, c[q] + LEJOS * (c[q] - st), fin) if c[q] > st else None; break
                if c[q] < lb and c[q] < vw:
                    st = min(vw, lb); fila("O7", q, -1, st, c[q] - LEJOS * (st - c[q]), fin) if c[q] < st else None; break
        dev = np.full(RTH1 - RTH0, np.nan); dev[mm - RTH0] = np.abs(c[m] / ab - 1); ruido.append(dev)
        atr.append(h[m].max() - l[m].min()); prev = dict(c=c[m[-1]])
    cols = ["k", "lado", "ref", "ext", "rg", "obj", "stop", "fin"] + DEFINICIONES + sorted(set(CONTROL.values()))
    if not filas: return pd.DataFrame(columns=cols)
    E = pd.DataFrame(filas)
    for col in DEFINICIONES + sorted(set(CONTROL.values())):
        E[col] = E[col].fillna(False).astype(bool) if col in E else False
    return E[cols].astype(dict(k=np.int64, lado=np.int64, fin=np.int64)).sort_values("k", kind="mergesort").reset_index(drop=True)
