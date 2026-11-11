"""LUXIMB-AMARILLA (2026-11-11, pedido de Nico: «mezclá la lógica de expansión → caja amarilla → expansión → entrada con la de
LUX-IMB y expansiones; hacé variantes»). Pre-registro: docs/research/luximb_amarilla_20261111/PREREGISTRO.md. Cadena estándar.

Une dos familias que hasta hoy se midieron por separado:
  - el IMPULSO de LUX-IMB (expansión del visor con zonas OG/VI en su 25 % inicial; `luximb_hvn.eventos`, con su control sin zonas), y
  - la secuencia de CORREDOR-VOL-GAPS / CVGAP-2 (`edgelab/research/corredor_vol_gaps.py` §1–4): caja amarilla de volumen alto en el
    extremo del impulso → ruptura de la caja A FAVOR del impulso con una excursión A → regreso a un punto estructural → entrada EN
    CONTRA, hacia el 50 %, el 75 % de retroceso o el origen del impulso, con stop detrás del extremo de la excursión.

Construcción (causal; todo se decide al cierre de una vela):
  1. Marca LUX-IMB en la vela k: origen A (pa), extremo B (ext), rango H, dirección d.
  2. Sector amarillo en B (como el padre): [B − d·0,25·H, B + d·0,25·H] (alto H_am = 0,5·H), abierto W·(k − i0 + 1) velas después de
     la marca (W = 1 o 2). Al cerrarse (vela kf) se mide el volumen del sector por vela (perfil por nivel); es «amarilla» si supera
     el percentil 80 causal de los sectores ya cerrados (≥ 20 previos). «sin_filtro» = cualquier sector (control del volumen).
  3. Después de kf: ruptura a favor (cierre más allá del borde externo), excursión A = extremo − borde externo ≥ e·H_am
     (e = 1, 2, 4); se invalida si un cierre vuelve al borde interno antes de armarse; vence a 1.440 velas o al fin del segmento.
  4. Regreso (el primer cierre que lo cumple, una vez armado): ANTES (retrocede 40 % de A, todavía afuera de la caja), EN_CAJA
     (cierre de vuelta en el borde externo) o DESPUES (cierre más allá del borde interno).
  5. Entrada a mercado en el primer tick de la vela siguiente, EN CONTRA del impulso (lado = −d). Objetivos: 50 % del impulso
     (`obj_50`), 75 % de retroceso (`obj_75`) u origen (`obj_0`). Stops: el extremo de la excursión (`stop_ext`) o el extremo más
     0,25·H_am (`stop_ext25`). Ejecuciones PRECIOS del motor único.
Definiciones = base de LUX-IMB (visor z2, z3, D2 z2, control z0) × W × filtro (amarilla / sin_filtro) × e × punto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import luximb_hvn as H

try:
    from numba import njit
except ImportError:                                     # sin numba: misma lógica en Python (lento; sólo tests chicos)
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "LUXIMB-AMARILLA"
CARPETA = "docs/research/luximb_amarilla_20261111"
BASES = {"visor": "D3_20_a0_z2", "z3": "D3_20_a0_z3", "d2": "D2_20_a0_z2", "ctrl": "D3_20_a0_z0"}
WS = (1, 2)
FILTROS_VOL = ("amarilla", "sin_filtro")
ES = (1.0, 2.0, 4.0)
PUNTOS = ("ANTES", "EN_CAJA", "DESPUES")
PCT, MIN_HIST, HIST = 80.0, 20, 50
VENCE = 1440
DEFINICIONES = [f"{b}|W{w}|{f}|e{int(e)}|{p}" for b in BASES for w in WS for f in FILTROS_VOL for e in ES for p in PUNTOS]
CONTROL = {**{f"{b}|W{w}|amarilla|e{int(e)}|{p}": f"{b}|W{w}|sin_filtro|e{int(e)}|{p}" for b in BASES for w in WS for e in ES for p in PUNTOS},
           **{f"{b}|W{w}|{f}|e{int(e)}|{p}": f"ctrl|W{w}|{f}|e{int(e)}|{p}" for b in ("visor", "z3", "d2") for w in WS for f in ("sin_filtro",)
              for e in ES for p in PUNTOS}}
EJECUCIONES = [("PRECIOS", o, s) for o in ("obj_50", "obj_75", "obj_0") for s in ("stop_ext", "stop_ext25")]
PERIODOS = [("DESC", 20250805, 20260331), ("REP", 20260401, 20260930)]


@njit(cache=False)
def _secuencia_nb(h, l, c, kf, fin, d, lo_s, hi_s, ham, e):
    """Ruptura a favor, excursión ≥ e·H_am y regreso. Devuelve, por punto (ANTES, EN_CAJA, DESPUES), la vela de decisión y el
    extremo de la excursión en ese momento (−1 / nan si no ocurre)."""
    ext_b = hi_s if d == 1 else lo_s; int_b = lo_s if d == 1 else hi_s
    roto = False; armado = False; E = 0.0; ks = np.full(3, -1, np.int64); xs = np.full(3, np.nan)
    for j in range(kf + 1, min(fin, kf + 1 + 1440)):
        if not roto:
            if d * (c[j] - int_b) <= 0: return ks, xs                          # volvió a la caja por dentro antes de romper
            if d * (c[j] - ext_b) > 0:
                roto = True; E = h[j] if d == 1 else l[j]
            continue
        if d == 1 and h[j] > E: E = h[j]
        if d == -1 and l[j] < E: E = l[j]
        A = d * (E - ext_b)
        if not armado:
            if d * (c[j] - int_b) <= 0: return ks, xs                          # invalidada antes de armarse
            if A >= e * ham: armado = True
            else: continue
        if ks[0] < 0 and d * (c[j] - (E - d * 0.4 * A)) <= 0 and d * (c[j] - ext_b) > 0:
            ks[0] = j; xs[0] = E
        if ks[1] < 0 and d * (c[j] - ext_b) <= 0:
            ks[1] = j; xs[1] = E
        if ks[2] < 0 and d * (c[j] - int_b) <= 0:
            ks[2] = j; xs[2] = E
            break
    return ks, xs


def eventos(ctx) -> pd.DataFrame:
    h, l, c, seg = (np.asarray(ctx[x]) for x in ("h", "l", "c", "seg")); n = len(c)
    vs = np.asarray(ctx["vp_start"], np.int64); vpx = np.asarray(ctx["vp_px"], float); vvo = np.asarray(ctx["vp_vol"], float)
    M = H.eventos(ctx)
    cols = ["k", "lado", "ref", "ext", "rg", "base", "W", "filtro", "e", "punto", "k_marca", "sector_vpb", "obj_50", "obj_75", "obj_0", "stop_ext", "stop_ext25"]
    if not len(M): return pd.DataFrame(columns=cols + DEFINICIONES)
    M = M[M[list(BASES.values())].any(axis=1)].reset_index(drop=True)
    ini = np.r_[0, np.flatnonzero(seg[1:] != seg[:-1]) + 1]; finseg = np.r_[ini[1:], n]
    filas = []
    for w in WS:
        cerrados = []                                                          # (kf, volumen por vela) de sectores ya cerrados
        orden = []
        for r in M.itertuples():
            k = int(r.k); d = int(r.d); B = float(r.ext); Hh = float(r.rg); pa = float(r.pa)
            kf = k + w * (k - int(r.i0) + 1)
            sg = np.searchsorted(ini, k, side="right") - 1; fin = int(finseg[sg])
            if kf >= fin - 1 or Hh <= 0: continue
            lo_s, hi_s = sorted((B - d * 0.25 * Hh, B + d * 0.25 * Hh)); ham = 0.5 * Hh
            z0, z1 = vs[k + 1], vs[kf + 1]; px = vpx[z0:z1]
            vpb = float(vvo[z0:z1][(px >= lo_s) & (px <= hi_s)].sum()) / (kf - k)
            orden.append((kf, k, d, B, Hh, pa, lo_s, hi_s, ham, vpb, fin, r))
        orden.sort(key=lambda x: x[0])
        hist = []
        for kf, k, d, B, Hh, pa, lo_s, hi_s, ham, vpb, fin, r in orden:
            prev = [v for (kk, v) in hist if kk < kf][-HIST:]
            amarilla = len(prev) >= MIN_HIST and vpb >= np.percentile(prev, PCT)
            hist.append((kf, vpb))
            bases = [b for b, col in BASES.items() if bool(getattr(r, col))]
            for e in ES:
                ks, xs = _secuencia_nb(h, l, c, kf, fin, d, lo_s, hi_s, ham, e)
                for pi, punto in enumerate(PUNTOS):
                    if ks[pi] < 0: continue
                    E = float(xs[pi])
                    filas.append(dict(k=int(ks[pi]), lado=-d, ref=pa, ext=float(c[ks[pi]]), rg=Hh, base=",".join(bases), W=w,
                                      amarilla=bool(amarilla), e=e, punto=punto, k_marca=k, sector_vpb=vpb,
                                      obj_50=pa + 0.5 * (B - pa), obj_75=pa + 0.25 * (B - pa), obj_0=pa,
                                      stop_ext=E, stop_ext25=E + d * 0.25 * ham))
    E_ = pd.DataFrame(filas)
    if not len(E_): return pd.DataFrame(columns=cols + DEFINICIONES)
    defs = {}
    for b in BASES:
        tiene = E_.base.str.split(",").apply(lambda xs: b in xs).to_numpy()
        for w in WS:
            for f in FILTROS_VOL:
                mf = E_.amarilla.to_numpy() if f == "amarilla" else np.ones(len(E_), bool)
                for e in ES:
                    for p in PUNTOS:
                        defs[f"{b}|W{w}|{f}|e{int(e)}|{p}"] = tiene & (E_.W.to_numpy() == w) & mf & (E_.e.to_numpy() == e) & (E_.punto.to_numpy() == p)
    E_ = pd.concat([E_, pd.DataFrame(defs, index=E_.index)], axis=1)
    E_["filtro"] = np.where(E_.amarilla, "amarilla", "sin_filtro")
    return E_.sort_values(["k", "k_marca"], kind="mergesort").reset_index(drop=True)
