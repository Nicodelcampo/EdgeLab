"""Variables de RÉGIMEN causales, listas para usar como perillas de cualquier experimento de grilla (2026-10-24).

Pedido de Nico (2026-10-24): «algunas estrategias funcionan por régimen, y eso no significa que no ganen plata ahora». La forma
rigurosa de buscarlas no es mirar el P&L por año y quedarse con el año bueno (eso es elegir la ventana después de verla), sino
declarar el régimen ANTES, como una perilla más del experimento:
  - la perilla se cuenta en `n_celdas` (cada nivel multiplica las celdas: la multiplicidad queda registrada sola);
  - la celda congelada incluye su nivel de régimen, así que la réplica, el OOS y el holdout evalúan exactamente la estrategia
    «señal SOLO cuando el régimen está presente»: si en 2023 el régimen casi no aparece, ese OOS da pocas operaciones
    (SIN_POTENCIA, no refutación); si aparece y pierde, es evidencia en contra de verdad;
  - el régimen se detecta en tiempo real (todas las variables usan sólo velas <= k o sesiones ya cerradas): operable en vivo.

Columnas que agrega `agregar(D, ctx)` (por disparo, en su vela de decisión k):
  reg_atr_rel         ATR(14) de las velas <= k / rango medio por vela de la sesión ANTERIOR       (volatilidad de ahora)
  reg_rango_prev      rango de la sesión anterior / mediana de las 20 sesiones previas a ella        (régimen de volatilidad diario)
  reg_eficiencia      |c_k - c_{k-60}| / recorrido en 60 velas (edgelab/regimes/state.py)           (tendencia 1 / rango 0)
  reg_tendencia_dia   (c_k - apertura de la sesión) / rango de la sesión anterior, con signo         (dirección del día)
  reg_vol_rel         volumen de las 30 velas <= k / volumen medio por vela de la sesión anterior    (actividad)
  reg_hora            bloque UTC fijo de la vela: 0 Asia 22-07 · 1 Europa 07-13:30 · 2 NY 13:30-20 · 3 cierre 20-22
                      (bloques fijos en UTC: NO ajusta horario de verano; declararlo así en la spec si importa)
  reg_dia             día de la semana de la sesión (0 lunes … 4 viernes; la sesión CME abre 22:00 UTC del día anterior)
Las continuas se cortan por cuantiles del E0 de la misma fuente (`Variable(..., cuantiles=3)`), nunca a ojo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.regimes.state import efficiency
from edgelab.research.grilla_generica import Variable

N_ATR, N_EF, N_VOL, N_RANGO = 14, 60, 30, 20

# Perillas listas: agregarlas a VARIABLES del experimento (cada una multiplica n_celdas por sus niveles: se cuenta sola).
VARIABLES_REGIMEN = {
    "vol_ahora": Variable("reg_vol_ahora", "reg_atr_rel", "extremos", cuantiles=3),
    "vol_diaria": Variable("reg_vol_diaria", "reg_rango_prev", "extremos", cuantiles=3),
    "eficiencia": Variable("reg_eficiencia", "reg_eficiencia", "extremos", cuantiles=3),
    "tendencia_dia": Variable("reg_tendencia_dia", "reg_tendencia_dia", "extremos", cuantiles=3),
    "actividad": Variable("reg_actividad", "reg_vol_rel", "extremos", cuantiles=3),
    "hora": Variable("reg_hora", "reg_hora", "eq_any", categoria=4),
    "dia": Variable("reg_dia", "reg_dia", "eq_any", categoria=5),
}


def _por_sesion_previa(valor_ses: pd.Series, ses: np.ndarray) -> np.ndarray:
    """Valor de la sesión ANTERIOR (en orden) para cada vela; NaN en la primera sesión."""
    us = np.array(sorted(valor_ses.index))
    prev = pd.Series(np.r_[np.nan, valor_ses.loc[us].to_numpy(float)[:-1]], index=us)
    return prev.reindex(ses).to_numpy(float)


def por_vela(ctx) -> dict:
    """Todas las variables de régimen para cada vela M1 (arreglos de largo n). Sólo pasado: velas <= k y sesiones cerradas."""
    h, l, c, v, t, ses = (np.asarray(ctx[x]) for x in ("h", "l", "c", "v", "t", "ses"))
    h, l, c, v = (x.astype(float) for x in (h, l, c, v)); n = len(c)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(N_ATR, min_periods=N_ATR).mean().to_numpy()
    df = pd.DataFrame(dict(ses=ses, r=h - l, v=v, h=h, l=l))
    g = df.groupby("ses")
    rango_ses = g.h.max() - g.l.min()
    rango_medio_prev = _por_sesion_previa(g.r.mean(), ses)
    vol_medio_prev = _por_sesion_previa(g.v.mean(), ses)
    rango_prev = _por_sesion_previa(rango_ses, ses)
    us = np.array(sorted(rango_ses.index)); rs = rango_ses.loc[us]
    ratio_ses = rs / rs.shift(1).rolling(N_RANGO, min_periods=5).median()           # rango de cada sesión / mediana de las 20 previas
    reg_rango_prev = _por_sesion_previa(ratio_ses, ses)                             # ... y se usa recién en la sesión siguiente
    o_ses = pd.Series(np.asarray(ctx["o"], float) if "o" in ctx else c).groupby(ses).transform("first").to_numpy()
    vol_n = pd.Series(v).rolling(N_VOL, min_periods=N_VOL).mean().to_numpy()
    seg_ok = pd.Series(ses).rolling(N_VOL, min_periods=N_VOL).apply(lambda x: x[0] == x[-1], raw=True).to_numpy() == 1
    minuto = ((t.astype(np.int64) - 60) // 60) % 1440                               # minuto UTC de inicio de la vela
    hora = np.select([(minuto >= 22 * 60) | (minuto < 7 * 60), minuto < 13 * 60 + 30, minuto < 20 * 60], [0, 1, 2], 3)
    dia_ses = pd.to_datetime((t.astype(np.int64) + 2 * 3600), unit="s", utc=True).dayofweek.to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        out = dict(reg_atr_rel=atr / rango_medio_prev,
                   reg_rango_prev=reg_rango_prev,
                   reg_eficiencia=efficiency(c, ses, N_EF),
                   reg_tendencia_dia=(c - o_ses) / rango_prev,
                   reg_vol_rel=np.where(seg_ok, vol_n / vol_medio_prev, np.nan),
                   reg_hora=hora.astype(float),
                   reg_dia=np.where(dia_ses <= 4, dia_ses, np.nan).astype(float))
    for k_, x in out.items(): out[k_] = np.where(np.isfinite(x), x, np.nan)
    assert all(len(x) == n for x in out.values())
    return out


def agregar(D: pd.DataFrame, ctx, cache: dict | None = None) -> pd.DataFrame:
    """Copia de D con las columnas reg_* en su vela de decisión k. `cache` (dict) evita recalcular por vela entre llamadas."""
    if cache is not None and "regimen" in cache: R = cache["regimen"]
    else:
        R = por_vela(ctx)
        if cache is not None: cache["regimen"] = R
    k = D.k.to_numpy(np.int64); D = D.copy()
    for col, x in R.items(): D[col] = x[k]
    return D
