"""Contexto causal común y vetos estructurales por operación (2026-11-04).

Diseño y correcciones incorporadas:
  1. Cero look-ahead e invariante al truncado:
     - `atr_sesion` y `vwap_sesion` reinician estrictamente en cada cambio de sesión (`ses[k] != ses[k-1]`), evitando que el salto
       overnight contamine el True Range o la media móvil al abrir la sesión.
     - Hora local de Nueva York con horario de verano (`regimen_sesion.minuto_ny`).
  2. Cuantiles móviles causales del propio instrumento (20 sesiones cerradas previas, con soporte para `ctx["calentamiento"]`):
     - Ningún umbral continuo se fija a ojo: los terciles (`P33`, `P67`) y el decil de huida (`P90`) de la sesión actual se calculan
       únicamente con la distribución de las hasta `N_SES_HIST = 20` sesiones cerradas ANTERIORES (`min_periods = 3`).
  3. Orientación según el lado `s` de la operación (`+1` compra, `-1` venta):
     - Las variables direccionales (`ctx_tendencia_favor`, `ctx_vwap_favor`, `ctx_eficiencia_contra`, `veto_muro`, `veto_huida`) se
       orientan con `s`, evitando que largos y cortos se cancelen entre sí en el meta-análisis.
  4. Cuatro vetos estructurales binarios (`0 = pasa`, `1 = vetado`), sin recortar objetivos:
     - `veto_horizonte`: menos de 60 min para el cierre de la sesión CME (`>= 16:00 ET`).
     - `veto_muro`: nivel estructural mayor conocido (`PDH`, `PDL`, `ONH/ONL` tras 09:30 ET, o `VWAP` de sesión) interpuesto en el
       recorrido entre la entrada `e` y el objetivo `tp`.
     - `veto_huida`: impulso de 60 velas en contra del lado `s` con eficiencia intra-sesión `er_sesion(60)` en el decil superior
       (`> P90`) de las 20 sesiones cerradas previas del propio instrumento.
     - `veto_liquidez_macro`: ventana ilíquida nocturna (`18:00–02:00 ET`) o `±5 min` de anuncio macro Tier-1 (`eventos.TIPOS_TIER1`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.eventos import TIPOS_TIER1, cerca
from edgelab.research.regimen_sesion import er_sesion, minuto_ny

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

N_ATR = 14
N_EF = 60
N_VOL = 30
N_SES_HIST = 20
MIN_SES_HIST = 3
CALENTAMIENTO_DIAS = 40

ETIQUETAS_CONTEXTO = {
    "ctx_vol_diaria": ["baja", "media", "alta"],
    "ctx_atr_rel": ["bajo", "medio", "alto"],
    "ctx_tendencia_favor": ["contra_fuerte", "neutra", "favor_fuerte"],
    "ctx_vwap_favor": ["contra_vwap", "favor_vwap"],
    "ctx_eficiencia_contra": ["favor_o_baja", "contra_media", "contra_alta"],
    "ctx_hora_ny": ["overnight_18_03", "londres_03_0930", "ny_manana_0930_12", "ny_tarde_12_16", "cierre_16_17"],
    "ctx_vol_rel": ["bajo", "medio", "alto"],
    "veto_horizonte": ["pasa", "vetado"],
    "veto_muro": ["pasa", "vetado"],
    "veto_huida": ["pasa", "vetado"],
    "veto_liquidez_macro": ["pasa", "vetado"],
}


@njit(cache=False)
def atr_sesion(h: np.ndarray, l: np.ndarray, c: np.ndarray, ses: np.ndarray, w: int = N_ATR) -> np.ndarray:
    """ATR(w) causal con corte estricto por sesión: la primera vela de la sesión usa `h - l` (sin salto overnight) y la ventana
    sólo promedia velas de la MISMA sesión (`NaN` hasta completar `w` velas de la sesión actual)."""
    n = len(c)
    out = np.full(n, np.nan)
    tr_buf = np.empty(n, np.float64)
    ini = 0
    suma = 0.0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            ini = k
            suma = 0.0
            tr = h[k] - l[k]
        else:
            pc = c[k - 1]
            tr = max(h[k] - l[k], max(abs(h[k] - pc), abs(l[k] - pc)))
        tr_buf[k] = tr
        suma += tr
        m = k - ini + 1
        if m > w:
            suma -= tr_buf[k - w]
        if m >= w:
            out[k] = suma / w
    return out


@njit(cache=False)
def vwap_sesion(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, ses: np.ndarray) -> np.ndarray:
    """VWAP causal acumulado dentro de cada sesión (`(h + l + c) / 3` ponderado por volumen; si el volumen acumulado es 0, usa el
    promedio simple de precios típicos de la sesión hasta `k`)."""
    n = len(c)
    out = np.full(n, np.nan)
    pv = 0.0
    vv = 0.0
    ps = 0.0
    m = 0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            pv = 0.0
            vv = 0.0
            ps = 0.0
            m = 0
        tp = (h[k] + l[k] + c[k]) / 3.0
        vk = max(v[k], 0.0)
        pv += tp * vk
        vv += vk
        ps += tp
        m += 1
        out[k] = pv / vv if vv > 0.0 else ps / m
    return out


@njit(cache=False)
def _vol_media_sesion(v: np.ndarray, ses: np.ndarray, w: int = N_VOL) -> np.ndarray:
    """Media móvil simple de volumen de las últimas `w` velas dentro de la misma sesión (`NaN` antes de `w` velas)."""
    n = len(v)
    out = np.full(n, np.nan)
    ini = 0
    suma = 0.0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            ini = k
            suma = 0.0
        suma += v[k]
        m = k - ini + 1
        if m > w:
            suma -= v[k - w]
        if m >= w:
            out[k] = suma / w
    return out


@njit(cache=False)
def _delta_sesion(c: np.ndarray, ses: np.ndarray, w: int = N_EF) -> np.ndarray:
    """Cambio de precio `c[k] - c[k - w]` dentro de la misma sesión (`NaN` si la sesión tiene menos de `w + 1` velas)."""
    n = len(c)
    out = np.full(n, np.nan)
    ini = 0
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            ini = k
        if k - ini >= w:
            out[k] = c[k] - c[k - w]
    return out


@njit(cache=False)
def _overnight_hl(h: np.ndarray, l: np.ndarray, ses: np.ndarray, min_ny: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Máximo y mínimo overnight (`min_ny < 570` = antes de 09:30 ET, o `min_ny >= 1080` = desde 18:00 ET) de cada sesión,
    expuestos ÚNICAMENTE a partir de las 09:30 ET (`570 <= min_ny < 1080`) para que estén cerrados y fijos sin look-ahead."""
    n = len(h)
    onh = np.full(n, np.nan)
    onl = np.full(n, np.nan)
    cur_h = np.nan
    cur_l = np.nan
    for k in range(n):
        if k == 0 or ses[k] != ses[k - 1]:
            cur_h = np.nan
            cur_l = np.nan
        m = min_ny[k]
        if m >= 1080 or m <= 570:
            cur_h = h[k] if np.isnan(cur_h) or h[k] > cur_h else cur_h
            cur_l = l[k] if np.isnan(cur_l) or l[k] < cur_l else cur_l
        if 570 <= m < 1080:
            onh[k] = cur_h
            onl[k] = cur_l
    return onh, onl


def _concatenar_calentamiento(ctx: dict) -> tuple[dict, int]:
    """Si `ctx` trae `ctx["calentamiento"]` (velas de sesiones previas a `desde`), las antepone para poblar la ventana de 20 sesiones
    desde el primer día evaluado y devuelve `(ctx_completo, offset_inicio)`."""
    cal = ctx.get("calentamiento")
    if not cal or not len(cal.get("c", ())):
        return ctx, 0
    ses0 = int(ctx["ses"][0]) if len(ctx.get("ses", ())) else None
    keep = np.asarray(cal["ses"]) < ses0 if ses0 is not None else np.ones(len(cal["c"]), bool)
    n_pre = int(keep.sum())
    if n_pre == 0:
        return ctx, 0
    claves = ("o", "h", "l", "c", "v", "t", "ses")
    full = {k: np.concatenate([np.asarray(cal[k])[keep], np.asarray(ctx[k])]) for k in claves if k in ctx and k in cal}
    if "o" not in full:
        full["o"] = full["c"].copy()
    return full, n_pre


def _umbrales_sesiones_previas(ses_u: np.ndarray, valores_por_sesion: list[np.ndarray], qs: tuple[float, ...],
                               ventana: int = N_SES_HIST, min_ses: int = MIN_SES_HIST) -> dict[float, np.ndarray]:
    """Para cada sesión `i` en `ses_u`, calcula los cuantiles `qs` juntando las observaciones válidas de las sesiones cerradas
    `max(0, i - ventana) .. i - 1`. Totalmente causal: la sesión `i` sólo mira sesiones `< i`."""
    n_s = len(ses_u)
    out = {q: np.full(n_s, np.nan) for q in qs}
    for i in range(n_s):
        ini = max(0, i - ventana)
        partes = [valores_por_sesion[j] for j in range(ini, i) if len(valores_por_sesion[j])]
        if len(partes) < min_ses:
            continue
        pool = np.concatenate(partes)
        if not len(pool):
            continue
        vals = np.quantile(pool, qs)
        for q, val in zip(qs, vals):
            out[q][i] = float(val)
    return out


def por_vela(ctx: dict) -> dict[str, np.ndarray]:
    """Calcula todas las primitivas y umbrales causales por vela M1 para `ctx` (usando `ctx["calentamiento"]` si está presente).
    Cada arreglo devuelto tiene el mismo largo `len(ctx["c"])` y depende exclusivamente del pasado `<= k`."""
    full, offset = _concatenar_calentamiento(ctx)
    h, l, c, v, t, ses = (np.asarray(full[x]) for x in ("h", "l", "c", "v", "t", "ses"))
    o = np.asarray(full["o"] if "o" in full else c, float)
    h, l, c, v = (x.astype(float) for x in (h, l, c, v))
    t_i = t.astype(np.int64)
    ses_i = ses.astype(np.int64)
    n = len(c)
    if n == 0:
        vacio = np.zeros(0, float)
        return {k: vacio for k in ("atr_rel", "rango_prev_ratio", "tend_raw", "er60", "delta60", "vol_rel", "vwap", "pdh", "pdl",
                                   "onh", "onl", "min_ny", "hora_ny", "macro_5m",
                                   "q33_vol_d", "q67_vol_d", "q33_atr", "q67_atr", "q33_tend", "q67_tend",
                                   "q33_er", "q67_er", "q90_er", "q33_vrel", "q67_vrel")}

    atr = atr_sesion(h, l, c, ses_i, N_ATR)
    vwap = vwap_sesion(h, l, c, v, ses_i)
    er60 = er_sesion(c, ses_i, N_EF)
    delta60 = _delta_sesion(c, ses_i, N_EF)
    vol30 = _vol_media_sesion(v, ses_i, N_VOL)
    min_ny = minuto_ny(t_i)
    onh, onl = _overnight_hl(h, l, ses_i, min_ny)

    # Bloques horarios en Nueva York (con DST):
    # 0: 18:00-03:00 ET | 1: 03:00-09:30 ET | 2: 09:30-12:00 ET | 3: 12:00-16:00 ET | 4: 16:00-17:00 ET
    hora_ny = np.select(
        [(min_ny >= 18 * 60) | (min_ny < 3 * 60), min_ny < 9 * 60 + 30, min_ny < 12 * 60, min_ny < 16 * 60],
        [0, 1, 2, 3],
        default=4,
    ).astype(float)

    # Estadísticas por sesión cerrada (en orden de aparición; las sesiones vienen ordenadas en el tiempo)
    cortes = np.flatnonzero(np.r_[True, ses_i[1:] != ses_i[:-1], True])
    n_ses = len(cortes) - 1
    ses_u = np.array([ses_i[cortes[i]] for i in range(n_ses)], dtype=np.int64)
    inv_ses = np.repeat(np.arange(n_ses, dtype=np.int64), np.diff(cortes))

    ses_hi = np.array([h[cortes[i]:cortes[i + 1]].max() for i in range(n_ses)], dtype=float)
    ses_lo = np.array([l[cortes[i]:cortes[i + 1]].min() for i in range(n_ses)], dtype=float)
    ses_rng = ses_hi - ses_lo
    ses_rmean = np.array([(h[cortes[i]:cortes[i + 1]] - l[cortes[i]:cortes[i + 1]]).mean() for i in range(n_ses)], dtype=float)
    ses_vmean = np.array([v[cortes[i]:cortes[i + 1]].mean() for i in range(n_ses)], dtype=float)
    ses_open = np.array([o[cortes[i]] for i in range(n_ses)], dtype=float)

    # Valores de la sesión inmediatamente anterior (NaN en i = 0)
    prev_hi = np.r_[np.nan, ses_hi[:-1]]
    prev_lo = np.r_[np.nan, ses_lo[:-1]]
    prev_rng = np.r_[np.nan, ses_rng[:-1]]
    prev_rmean = np.r_[np.nan, ses_rmean[:-1]]
    prev_vmean = np.r_[np.nan, ses_vmean[:-1]]

    # Ratio del rango de cada sesión respecto de la mediana de las 20 sesiones previas a ella
    s_rng_ser = pd.Series(ses_rng)
    med_20 = s_rng_ser.shift(1).rolling(N_SES_HIST, min_periods=MIN_SES_HIST).median().to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ses_rng_ratio = np.where(med_20 > 0, ses_rng / med_20, np.nan)
    prev_rng_ratio = np.r_[np.nan, ses_rng_ratio[:-1]]

    pdh = prev_hi[inv_ses]
    pdl = prev_lo[inv_ses]
    rango_prev = prev_rng[inv_ses]
    rango_prev_ratio = prev_rng_ratio[inv_ses]
    open_ses = ses_open[inv_ses]

    with np.errstate(invalid="ignore", divide="ignore"):
        atr_rel = np.where(prev_rmean[inv_ses] > 0, atr / prev_rmean[inv_ses], np.nan)
        tend_raw = np.where(rango_prev > 0, (c - open_ses) / rango_prev, np.nan)
        vol_rel = np.where(prev_vmean[inv_ses] > 0, vol30 / prev_vmean[inv_ses], np.nan)

    # Cuantiles móviles causales de las 20 sesiones cerradas previas para cada variable continua:
    # para `ses_rng_ratio`, en la sesión `i` las sesiones cerradas `max(0, i - N_SES_HIST) .. i - 1` son las observaciones históricas
    hist_vol_d = [np.array([ses_rng_ratio[i]]) if np.isfinite(ses_rng_ratio[i]) else np.zeros(0) for i in range(n_ses)]
    hist_atr = [atr_rel[cortes[i]:cortes[i + 1]][np.isfinite(atr_rel[cortes[i]:cortes[i + 1]])] for i in range(n_ses)]
    hist_tend = []
    for i in range(n_ses):
        sl = tend_raw[cortes[i]:cortes[i + 1]]
        sl = sl[np.isfinite(sl)]
        # Simetrizado (+sl y -sl) para que los terciles de tendencia a favor no dependan del sesgo alcista/bajista de las 20 sesiones
        hist_tend.append(np.concatenate([sl, -sl]) if len(sl) else np.zeros(0))
    hist_er = [er60[cortes[i]:cortes[i + 1]][np.isfinite(er60[cortes[i]:cortes[i + 1]])] for i in range(n_ses)]
    hist_vrel = [vol_rel[cortes[i]:cortes[i + 1]][np.isfinite(vol_rel[cortes[i]:cortes[i + 1]])] for i in range(n_ses)]

    q_vol_d = _umbrales_sesiones_previas(ses_u, hist_vol_d, (1 / 3, 2 / 3))
    q_atr = _umbrales_sesiones_previas(ses_u, hist_atr, (1 / 3, 2 / 3))
    q_tend = _umbrales_sesiones_previas(ses_u, hist_tend, (1 / 3, 2 / 3))
    q_er = _umbrales_sesiones_previas(ses_u, hist_er, (1 / 3, 2 / 3, 0.90))
    q_vrel = _umbrales_sesiones_previas(ses_u, hist_vrel, (1 / 3, 2 / 3))

    macro_5m = cerca(t_i, antes_min=5, despues_min=5, tipos=TIPOS_TIER1).astype(float)

    out_full = dict(
        atr_rel=atr_rel,
        rango_prev_ratio=rango_prev_ratio,
        tend_raw=tend_raw,
        er60=er60,
        delta60=delta60,
        vol_rel=vol_rel,
        vwap=vwap,
        pdh=pdh,
        pdl=pdl,
        onh=onh,
        onl=onl,
        min_ny=min_ny.astype(float),
        hora_ny=hora_ny,
        macro_5m=macro_5m,
        q33_vol_d=q_vol_d[1 / 3][inv_ses],
        q67_vol_d=q_vol_d[2 / 3][inv_ses],
        q33_atr=q_atr[1 / 3][inv_ses],
        q67_atr=q_atr[2 / 3][inv_ses],
        q33_tend=q_tend[1 / 3][inv_ses],
        q67_tend=q_tend[2 / 3][inv_ses],
        q33_er=q_er[1 / 3][inv_ses],
        q67_er=q_er[2 / 3][inv_ses],
        q90_er=q_er[0.90][inv_ses],
        q33_vrel=q_vrel[1 / 3][inv_ses],
        q67_vrel=q_vrel[2 / 3][inv_ses],
    )
    return {k: v[offset:] for k, v in out_full.items()}


def _tercil(x: np.ndarray, q33: np.ndarray, q67: np.ndarray) -> np.ndarray:
    """Clasifica `x` en `{0, 1, 2}` usando los umbrales causales `q33` y `q67` (`-1` donde `x` o los umbrales son `NaN`)."""
    ok = np.isfinite(x) & np.isfinite(q33) & np.isfinite(q67)
    out = np.full(len(x), -1, dtype=np.int64)
    out[ok & (x <= q33)] = 0
    out[ok & (x > q33) & (x <= q67)] = 1
    out[ok & (x > q67)] = 2
    return out


def etiquetar_operaciones(sim: dict, O: np.ndarray, desfase_vela: int = 0, cache: dict | None = None) -> dict[str, np.ndarray]:
    """Etiqueta cada fila de `O` (`(i, ei, start, limite, s, entrada, stop, objetivo, be)`) con las 7 variables de contexto común
    y los 4 vetos estructurales, evaluados en la vela cerrada `k_ctx = max(0, start - desfase_vela)` y orientados según el lado
    `s = O[:, 4]` (`+1` compra, `-1` venta) de la operación."""
    m = len(O)
    if m == 0:
        return {k: np.zeros(0, np.int64) for k in ETIQUETAS_CONTEXTO}
    if cache is not None and "contexto_vela" in cache:
        V = cache["contexto_vela"]
    else:
        V = por_vela(sim)
        if cache is not None:
            cache["contexto_vela"] = V

    n_barras = len(sim["c"])
    k_start = np.clip(O[:, 2].astype(np.int64) - int(desfase_vela), 0, n_barras - 1)
    s = np.where(O[:, 4] >= 0, 1.0, -1.0)
    e = O[:, 5].astype(float)
    tp = O[:, 7].astype(float)
    c_k = np.asarray(sim["c"], float)[k_start]
    tick = float(sim.get("tick", 0.25) or 0.25)

    # 1. Contexto común (orientado por `s` en las variables direccionales)
    ctx_vol_diaria = _tercil(V["rango_prev_ratio"][k_start], V["q33_vol_d"][k_start], V["q67_vol_d"][k_start])
    ctx_atr_rel = _tercil(V["atr_rel"][k_start], V["q33_atr"][k_start], V["q67_atr"][k_start])

    tend_favor = s * V["tend_raw"][k_start]
    ctx_tendencia_favor = _tercil(tend_favor, V["q33_tend"][k_start], V["q67_tend"][k_start])

    vw = V["vwap"][k_start]
    ok_vw = np.isfinite(vw) & np.isfinite(c_k)
    ctx_vwap_favor = np.full(m, -1, dtype=np.int64)
    ctx_vwap_favor[ok_vw & (s * (c_k - vw) <= 0)] = 0
    ctx_vwap_favor[ok_vw & (s * (c_k - vw) > 0)] = 1

    er_k = V["er60"][k_start]
    d60_k = V["delta60"][k_start]
    q33_er = V["q33_er"][k_start]
    q67_er = V["q67_er"][k_start]
    ok_er = np.isfinite(er_k) & np.isfinite(d60_k) & np.isfinite(q33_er) & np.isfinite(q67_er)
    contra_imp = (s * d60_k) < 0
    ctx_eficiencia_contra = np.full(m, -1, dtype=np.int64)
    ctx_eficiencia_contra[ok_er & ((~contra_imp) | (er_k <= q33_er))] = 0
    ctx_eficiencia_contra[ok_er & contra_imp & (er_k > q33_er) & (er_k <= q67_er)] = 1
    ctx_eficiencia_contra[ok_er & contra_imp & (er_k > q67_er)] = 2

    ctx_hora_ny = V["hora_ny"][k_start].astype(np.int64)
    ctx_vol_rel = _tercil(V["vol_rel"][k_start], V["q33_vrel"][k_start], V["q67_vrel"][k_start])

    # 2. Cuatro vetos estructurales binarios (0 = pasa, 1 = vetado), sin recortar objetivos
    min_ny_k = V["min_ny"][k_start]
    # Veto 1: Horizonte restante < 60 min antes del cierre de sesión CME (16:00-17:00 ET)
    veto_horizonte = ((min_ny_k >= 16 * 60) & (min_ny_k < 17 * 60)).astype(np.int64)

    # Veto 2: Muro estructural conocido (PDH, PDL, ONH/ONL tras 09:30 ET, o VWAP de sesión) interpuesto entre `e` y `tp`
    veto_muro = np.zeros(m, dtype=np.int64)
    lo_camino = np.minimum(e, tp) + tick
    hi_camino = np.maximum(e, tp) - tick
    hay_espacio = hi_camino > lo_camino
    for col_nv in ("pdh", "pdl", "onh", "onl", "vwap"):
        nv = V[col_nv][k_start]
        en_camino = hay_espacio & np.isfinite(nv) & (nv >= lo_camino) & (nv <= hi_camino)
        veto_muro |= en_camino.astype(np.int64)

    # Veto 3: Huida direccional (impulso de 60 velas en contra de `s` con ER60 > decil P90 móvil causal de las 20 sesiones previas)
    q90_er = V["q90_er"][k_start]
    ok_huida = np.isfinite(er_k) & np.isfinite(d60_k) & np.isfinite(q90_er)
    veto_huida = np.full(m, -1, dtype=np.int64)
    veto_huida[ok_huida] = (contra_imp[ok_huida] & (er_k[ok_huida] > q90_er[ok_huida])).astype(np.int64)

    # Veto 4: Ventana ilíquida nocturna (18:00-02:00 ET) o shock de anuncio macro Tier-1 (±5 min)
    iliquida = (min_ny_k >= 18 * 60) | (min_ny_k < 2 * 60)
    macro = V["macro_5m"][k_start] > 0
    veto_liquidez_macro = (iliquida | macro).astype(np.int64)

    return dict(
        ctx_vol_diaria=ctx_vol_diaria,
        ctx_atr_rel=ctx_atr_rel,
        ctx_tendencia_favor=ctx_tendencia_favor,
        ctx_vwap_favor=ctx_vwap_favor,
        ctx_eficiencia_contra=ctx_eficiencia_contra,
        ctx_hora_ny=ctx_hora_ny,
        ctx_vol_rel=ctx_vol_rel,
        veto_horizonte=veto_horizonte,
        veto_muro=veto_muro,
        veto_huida=veto_huida,
        veto_liquidez_macro=veto_liquidez_macro,
    )


def marginales_contexto(sim: dict, O: np.ndarray, net: np.ndarray, ses: np.ndarray, desfase_vela: int = 0,
                        cache: dict | None = None) -> dict:
    """Agrega las estadísticas `(nivel, n, suma, suma2, sesiones)` de las 7 variables de contexto común y los 4 vetos sobre todas
    las operaciones con resultado finito `net` (mismo formato que `grilla_generica.marginales_globales`)."""
    net = np.asarray(net, float)
    ses = np.asarray(ses)
    ok = np.isfinite(net)
    etq = etiquetar_operaciones(sim, O, desfase_vela=desfase_vela, cache=cache)
    out = {}
    for nombre, ix in etq.items():
        filas = []
        for lv in np.unique(ix[ok & (ix >= 0)]):
            m = ok & (ix == lv)
            x = net[m]
            filas.append(dict(
                nivel=int(lv),
                n=int(m.sum()),
                suma=float(x.sum()),
                suma2=float((x * x).sum()),
                sesiones=int(len(np.unique(ses[m]))),
            ))
        out[nombre] = filas
        out[nombre + ".etiquetas"] = ETIQUETAS_CONTEXTO[nombre]
    return out
