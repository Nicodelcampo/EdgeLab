"""Rasgos comunes que la cadena de tablas agrega a TODA familia (2026-11-11, pedido de Nico: «probá filtrar con VWAP diario, VWAP de
NY y ambos; no hay una manera definida, usá todas las mejores»). AUTOMATIZACION_PROCESOS_20261111 I4.

VWAP (causal: en la vela k usa sólo velas ≤ k, con el volumen por nivel de precio del perfil de cada vela):
  vwap_d    anclado al inicio de la sesión (trade date CME)            vwap_ny   anclado a las 09:30 de Nueva York (sigue hasta la
                                                                                  próxima apertura: de noche es el de la última apertura)
  sd_*      desvío estándar ponderado por volumen alrededor del VWAP (bandas de VWAP)
Rasgos relativos a la operación de cada fila (con `lado`):
  vwapd_hacia / vwapny_hacia   1 si la operación va HACIA el VWAP (el precio está del otro lado del VWAP respecto de la dirección)
  vwapd_dist / vwapny_dist     |cierre − VWAP| en desvíos (0 = en el VWAP)
  vwap_ambos                   +1 si la operación va hacia los dos VWAP, −1 si se aleja de los dos, 0 si están mezclados
Filtros comunes (`FILTROS`): hacia / contra cada VWAP, ambos hacia / ambos contra, lejos (≥ 1 desvío) y lejos-hacia de cada uno.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FILTROS = {"vwapD_hacia": ("vwapd_hacia", "==", 1.0), "vwapD_contra": ("vwapd_hacia", "==", 0.0),
           "vwapNY_hacia": ("vwapny_hacia", "==", 1.0), "vwapNY_contra": ("vwapny_hacia", "==", 0.0),
           "vwap_ambos_hacia": ("vwap_ambos", "==", 1.0), "vwap_ambos_contra": ("vwap_ambos", "==", -1.0),
           "vwapD_lejos": ("vwapd_dist", ">=", 1.0), "vwapNY_lejos": ("vwapny_dist", ">=", 1.0),
           "vwapD_lejos_hacia": ("vwapd_lejos_hacia", "==", 1.0), "vwapNY_lejos_hacia": ("vwapny_lejos_hacia", "==", 1.0)}


def _por_vela(ctx):
    """Σ precio·vol, Σ precio²·vol y Σ vol por vela, del perfil de volumen (o de la vela típica si no hay perfil)."""
    n = len(ctx["c"])
    if "vp_start" in ctx and len(ctx["vp_vol"]):
        vs = np.asarray(ctx["vp_start"], np.int64); px = np.asarray(ctx["vp_px"], float); vo = np.asarray(ctx["vp_vol"], float)
        cpv = np.r_[0.0, np.cumsum(px * vo)]; cp2 = np.r_[0.0, np.cumsum(px * px * vo)]; cv = np.r_[0.0, np.cumsum(vo)]
        return cpv[vs[1:n + 1]] - cpv[vs[:n]], cp2[vs[1:n + 1]] - cp2[vs[:n]], cv[vs[1:n + 1]] - cv[vs[:n]]
    tp = (np.asarray(ctx["h"]) + np.asarray(ctx["l"]) + np.asarray(ctx["c"])) / 3; v = np.asarray(ctx["v"], float)
    return tp * v, tp * tp * v, v


def _anclado(pv, p2v, v, ancla):
    g = np.cumsum(ancla)                                                   # grupo = anclas vistas hasta la vela (incluida)
    def cum(x):
        c = np.cumsum(x); ini = np.r_[0.0, c][np.searchsorted(g, g, side="left")]    # suma antes del inicio del grupo
        return c - ini
    V = cum(v)
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = cum(pv) / V; sd = np.sqrt(np.maximum(cum(p2v) / V - vw * vw, 0.0))
    return np.where(V > 0, vw, np.nan), np.where(V > 0, sd, np.nan)


def vwap(ctx) -> dict:
    """Por vela: vwap_d, sd_d (sesión) y vwap_ny, sd_ny (desde las 09:30 ET)."""
    pv, p2v, v = _por_vela(ctx); ses = np.asarray(ctx["ses"]); n = len(ses)
    a_d = np.r_[True, ses[1:] != ses[:-1]]
    et = pd.to_datetime(np.asarray(ctx["t"], float) - 60, unit="s", utc=True).tz_convert("America/New_York")   # apertura de la vela
    mins = (et.hour * 60 + et.minute).to_numpy(); dia = et.normalize().to_numpy()
    nueva = np.r_[True, dia[1:] != dia[:-1]]
    a_ny = (mins >= 570) & (np.r_[True, mins[:-1] < 570] | nueva)             # primera vela de cada día con hora >= 09:30
    a_ny[0] = True
    vd, sd = _anclado(pv, p2v, v, a_d); vn, sn = _anclado(pv, p2v, v, a_ny)
    return dict(vwap_d=vd, sd_d=sd, vwap_ny=vn, sd_ny=sn)


def agregar(E: pd.DataFrame, ctx) -> pd.DataFrame:
    """Columnas de VWAP para cada fila (vela k, dirección lado). Nunca reemplaza columnas que la familia ya trae."""
    if not len(E) or "k" not in E or "lado" not in E: return E
    W = vwap(ctx); k = E.k.to_numpy(np.int64); c = np.asarray(ctx["c"], float)[k]; lado = E.lado.to_numpy(float); out = {}
    for s, nom in (("d", "vwapd"), ("ny", "vwapny")):
        vw, sd = W[f"vwap_{s}"][k], W[f"sd_{s}"][k]
        with np.errstate(invalid="ignore", divide="ignore"):
            hacia = np.where(np.isfinite(vw), ((vw - c) * lado > 0).astype(float), np.nan)
            dist = np.where(sd > 0, np.abs(c - vw) / sd, np.nan)
        out[f"{nom}"] = vw; out[f"{nom}_hacia"] = hacia; out[f"{nom}_dist"] = dist
        out[f"{nom}_lejos_hacia"] = np.where(np.isfinite(hacia) & np.isfinite(dist), ((hacia == 1) & (dist >= 1)).astype(float), np.nan)
    a, b = out["vwapd_hacia"], out["vwapny_hacia"]
    out["vwap_ambos"] = np.where(np.isfinite(a) & np.isfinite(b), np.where((a == 1) & (b == 1), 1.0, np.where((a == 0) & (b == 0), -1.0, 0.0)), np.nan)
    return pd.concat([E, pd.DataFrame({x: y for x, y in out.items() if x not in E}, index=E.index)], axis=1)
