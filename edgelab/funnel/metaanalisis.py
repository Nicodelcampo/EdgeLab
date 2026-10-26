"""Meta-análisis entre instrumentos de UNA regla congelada (2026-10-26, POTENCIA_MISMOS_DATOS §3).

Cada instrumento aporta su media neta y su IC90 (por sesiones, como lo publica `grilla_generica.evaluar`); se combinan por el
inverso de la varianza. Efecto fijo si la heterogeneidad no se detecta; si I² es alto se informa también el de efectos aleatorios
(DerSimonian-Laird), que es más conservador y es el que vale para decidir. Requisitos para que la combinación signifique algo:
la misma celda congelada en todos, cada uno en su propia unidad normalizada (P&L en R o en rango de sesión, `NORMALIZAR`) o en una
moneda común, y ventanas que ninguno usó para elegir. El resultado es un p unilateral: sirve como UN paso de LORD++ de la familia.
"""
from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()
Z90 = 1.6448536


def combinar(filas: list[dict]) -> dict:
    """filas: [{instrumento, media, ic90:[lo,hi], n}] con la misma unidad. Devuelve efecto fijo, aleatorio y heterogeneidad."""
    xs = [(f, f["media"], ((f["ic90"][1] - f["ic90"][0]) / (2 * Z90)) ** 2) for f in filas
          if f.get("ic90") and f.get("media") is not None and f["ic90"][1] > f["ic90"][0]]
    if not xs: return dict(k=0, nota="sin filas evaluables")
    w = [1 / v for _, _, v in xs]; sw = sum(w)
    mf = sum(wi * m for wi, (_, m, _) in zip(w, xs)) / sw; sef = math.sqrt(1 / sw)
    q = sum(wi * (m - mf) ** 2 for wi, (_, m, _) in zip(w, xs)); k = len(xs)
    i2 = max(0.0, (q - (k - 1)) / q) if q > 0 else 0.0
    tau2 = max(0.0, (q - (k - 1)) / (sw - sum(wi ** 2 for wi in w) / sw)) if k > 1 else 0.0
    wr = [1 / (v + tau2) for _, _, v in xs]; swr = sum(wr)
    mr = sum(wi * m for wi, (_, m, _) in zip(wr, xs)) / swr; ser = math.sqrt(1 / swr)
    p_q = 1 - _chi2_cdf(q, k - 1) if k > 1 else 1.0
    fijo = dict(media=mf, se=sef, ic90=[mf - Z90 * sef, mf + Z90 * sef], p_unilateral=1 - _N.cdf(mf / sef))
    aleat = dict(media=mr, se=ser, ic90=[mr - Z90 * ser, mr + Z90 * ser], p_unilateral=1 - _N.cdf(mr / ser), tau2=tau2)
    return dict(k=k, n=sum(int(f.get("n") or 0) for f, _, _ in xs), instrumentos=[f.get("instrumento") for f, _, _ in xs],
                fijo=fijo, aleatorio=aleat, Q=q, p_heterogeneidad=p_q, I2=i2,
                decide="aleatorio" if k > 1 and i2 > 0 else "fijo",
                nota="decide el modelo aleatorio salvo heterogeneidad nula; signos opuestos con I² alto = la regla no es general")


def _chi2_cdf(x: float, k: int) -> float:
    """CDF de chi² con k grados (serie de la gamma incompleta regularizada; k chico, sin scipy)."""
    if x <= 0 or k <= 0: return 0.0
    a, z = k / 2, x / 2; term = s = 1 / a; n = 1
    while abs(term) > 1e-14 * abs(s) and n < 500:
        term *= z / (a + n); s += term; n += 1
    return min(1.0, s * math.exp(-z + a * math.log(z) - math.lgamma(a)))
