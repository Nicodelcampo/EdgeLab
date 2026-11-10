"""Motor causal compilado en Numba de Barreras HFT frontales (`BARRERAS-HFT-R`, 2026-11-05).

Pre-registro: `docs/research/hft_gc_p10_20261105/PREREGISTRO_BARRERAS_HFT_R.md`.

Evalúa en cualquier vela de decisión `k` (sin ningún look-ahead, 100% invariante al truncado en `<= k`) la distancia libre
frontal `d_libre_px` desde el precio de entrada `e` en la dirección `s` (+1 compra, -1 venta) hasta el borde cercano de la
primera barrera HFT vigente según los 4 ejes paramétricos:
  1. `tipo_barrera`:
     - `0: TODAS_HFT`           (cualquier zona HFT individual vigente)
     - `1: FUERTE_VOL_ABS`      (zonas `Predator`/`Absorb` o en el tercil superior causal `>= P67` de las 200 zonas previas)
     - `2: BORDE_GRIS_OPUESTO`  (zonas con alejamiento confirmado en `<= k` y polaridad opuesta `away_dir == -s`)
     - `3: SOLO_CLUSTER_P10`    (únicamente `Clusters P10` de >= 4 zonas comprimidas vigentes en `<= k`)
  2. `antiguedad_max` (edad en tiempo de mercado activo, arrancando en `5m`):
     - `0: 5m` (`300s`), `1: 15m` (`900s`), `2: 60m` (`3600s`), `3: 180m` (`10800s`), `4: sesion` (misma sesión CME)
  3. `mitigacion`:
     - `0: VIRGEN`        (ningún toque posterior en `(zi, k]`)
     - `1: NO_ATRAVESADA` (aún no se comerciaron ambos bordes `lo` y `hi` en `(zi, k]`)
  4. `rango_libre_min` y `modo_accion` (`VETO_PURO` vs `CAP_TP_DELANTE`).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from edgelab.bridge.indicators import hft_gc_cluster_p10 as HGC

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

TIPOS_BARRERA = ("TODAS_HFT", "FUERTE_VOL_ABS", "BORDE_GRIS_OPUESTO", "SOLO_CLUSTER_P10")
ANTIGUEDADES = (
    ("5m", 300.0, 0),
    ("15m", 900.0, 0),
    ("60m", 3600.0, 0),
    ("180m", 10800.0, 0),
    ("sesion", 86400.0, 1),
)
MITIGACIONES = ("VIRGEN", "NO_ATRAVESADA")
INF_PX = 1e18


@njit(cache=False)
def reloj_activo_m1_nb(t_close_s):
    """Reloj acumulado de mercado activo en segundos sobre velas M1 (pausa máxima computada por salto = `300s`, como NT8)."""
    n = len(t_close_s)
    mc = np.zeros(n, np.float64)
    for i in range(1, n):
        dt = float(t_close_s[i] - t_close_s[i - 1])
        if dt > 0.0:
            mc[i] = mc[i - 1] + (dt if dt < 300.0 else 300.0)
        else:
            mc[i] = mc[i - 1]
    return mc


@njit(cache=False)
def _p67_causal_nb(vals, ventana=200, min_hist=15):
    """Marca `1` cuando `vals[i]` está en el tercil superior (`>= P67`) de las hasta `ventana` zonas anteriores."""
    n = len(vals)
    out = np.zeros(n, np.int64)
    for i in range(n):
        a = 0 if i < ventana else (i - ventana)
        m = i - a
        if m < min_hist:
            out[i] = 1
            continue
        sub = np.sort(vals[a:i])
        idx = int(0.67 * float(m))
        if idx >= m:
            idx = m - 1
        if vals[i] >= sub[idx] - 1e-12:
            out[i] = 1
    return out


@njit(cache=False)
def _mitigacion_barreras_nb(zi_m1, zlo, zhi, h_m1, l_m1):
    """Ciclo de vida causal de cada barrera `[zlo, zhi]` creada en `zi_m1`:
    1) Primero detecta la primera vela `k > zi_m1` completamente fuera de `[zlo, zhi]` (`salio = -1` debajo de `lo`, `+1` encima de `hi`),
       para no confundir la vela de salida inicial con un retesteo.
    2) Una vez fuera (`salio != 0`):
       - `first_any`: primera vela posterior que vuelve a tocar el borde cercano (`h >= lo` desde abajo, `l <= hi` desde arriba).
       - `first_full`: primera vela posterior que alcanza/atraviesa el borde lejano (`h >= hi` desde abajo, `l <= lo` desde arriba).
    Si aún no ocurrió hasta el fin del array, vale `nm + 10` (`> k` para todo `k < nm`, 100% invariante al truncado)."""
    nz = len(zi_m1)
    nm = len(h_m1)
    centinela = nm + 10
    first_any = np.full(nz, centinela, np.int64)
    first_full = np.full(nz, centinela, np.int64)
    for i in range(nz):
        b0 = zi_m1[i]
        if b0 < 0 or b0 + 1 >= nm:
            continue
        lo = zlo[i]
        hi = zhi[i]
        salio = 0
        for k in range(b0 + 1, nm):
            hk = h_m1[k]
            lk = l_m1[k]
            if salio == 0:
                if hk < lo - 1e-9:
                    salio = -1
                elif lk > hi + 1e-9:
                    salio = 1
                continue
            if salio == -1:
                if first_any[i] == centinela and hk >= lo - 1e-9:
                    first_any[i] = k
                if hk >= hi - 1e-9:
                    first_full[i] = k
                    break
            else:
                if first_any[i] == centinela and lk <= hi + 1e-9:
                    first_any[i] = k
                if lk <= lo + 1e-9:
                    first_full[i] = k
                    break
    return first_any, first_full


@njit(cache=False)
def distancias_libres_lote_nb(
    k_ops, s_ops, e_ops, r_ops,
    mc_m1, ses_m1,
    zi, z_mc, z_ses, zlo, zhi, z_fuerte, z_away_k, z_away_dir, z_first_any, z_first_full,
    ci, c_mc, c_ses, clo, chi, c_first_any, c_first_full,
    tipo_barrera, max_edad_seg, solo_misma_sesion, modo_mitigacion
):
    """Calcula `d_libre_px` (en puntos de precio; `INF_PX` si no hay barrera) para cada operación candidata `(k, s, e, r)`."""
    m = len(k_ops)
    out = np.full(m, INF_PX, np.float64)
    if m == 0:
        return out

    es_cluster = tipo_barrera == 3
    b_i = ci if es_cluster else zi
    b_mc = c_mc if es_cluster else z_mc
    b_ses = c_ses if es_cluster else z_ses
    b_lo = clo if es_cluster else zlo
    b_hi = chi if es_cluster else zhi
    b_f_any = c_first_any if es_cluster else z_first_any
    b_f_full = c_first_full if es_cluster else z_first_full

    nb = len(b_i)
    if nb == 0:
        return out

    # Puntero upper_bound por búsqueda binaria (soporta `k_ops` en cualquier orden)
    for j in range(m):
        k = k_ops[j]
        s = s_ops[j]
        e = e_ops[j]
        r = r_ops[j]
        if k < 0 or k >= len(mc_m1) or r <= 0.0:
            continue
        mc_k = mc_m1[k]
        ses_k = ses_m1[k]
        delta_min = 0.15 * r
        atras_max = 0.50 * r

        # Último índice `idx` con `b_i[idx] <= k`
        lo_idx = 0
        hi_idx = nb
        while lo_idx < hi_idx:
            mid = (lo_idx + hi_idx) // 2
            if b_i[mid] <= k:
                lo_idx = mid + 1
            else:
                hi_idx = mid
        top = lo_idx - 1
        if top < 0:
            continue

        mejor = INF_PX
        for idx in range(top, -1, -1):
            edad = mc_k - b_mc[idx]
            if edad > max_edad_seg + 1e-9:
                break
            if solo_misma_sesion == 1 and b_ses[idx] != ses_k:
                continue

            # Mitigación causal hasta `k` inclusive
            f_mit = b_f_any[idx] if modo_mitigacion == 0 else b_f_full[idx]
            if f_mit <= k:
                continue

            if not es_cluster:
                if tipo_barrera == 1 and z_fuerte[idx] == 0:
                    continue
                elif tipo_barrera == 2:
                    ak = z_away_k[idx]
                    if ak < 0 or ak > k or z_away_dir[idx] != -s:
                        continue

            lz = b_lo[idx]
            hz = b_hi[idx]
            if s == 1:
                if hz <= e + delta_min or lz < e - atras_max:
                    continue
                d_px = lz - e
                if d_px < 0.0:
                    d_px = 0.0
            else:
                if lz >= e - delta_min or hz > e + atras_max:
                    continue
                d_px = e - hz
                if d_px < 0.0:
                    d_px = 0.0

            if d_px < mejor:
                mejor = d_px
                if mejor == 0.0:
                    break
        out[j] = mejor

    return out


def preparar_inventario_barreras(
    zones_df: pd.DataFrame,
    ctx: dict,
    clust_df: Optional[pd.DataFrame] = None,
    alejamiento_ticks_m1: int = 16,
) -> dict:
    """Prepara en memoria los arreglos causales alineados al `ctx` M1 para consultar cualquier combinación de parámetros.
    Funciona tanto con almacenes ricos (`ZONAS_HFTGCP10_GC` + `ZONAS_HFTGCP10_CLUST_GC`) como con almacenes minimalistas
    (`ZONAS_HFTNQ_*` / `ZONAS_HFT2_*` que sólo traen `t_ns, lo, hi`)."""
    t = np.asarray(ctx["t"], np.int64)
    h = np.asarray(ctx["h"], np.float64)
    l = np.asarray(ctx["l"], np.float64)
    c = np.asarray(ctx["c"], np.float64)
    v = np.asarray(ctx["v"], np.float64)
    ses = np.asarray(ctx["ses"], np.int64)
    tick = float(ctx["tick"])
    nm = len(t)
    mc_m1 = reloj_activo_m1_nb(t)

    z0_i = np.zeros(0, np.int64)
    z0_f = np.zeros(0, np.float64)
    vacio = dict(
        mc_m1=mc_m1, ses_m1=ses,
        zi=z0_i, z_mc=z0_f, z_ses=z0_i, zlo=z0_f, zhi=z0_f,
        z_fuerte=z0_i, z_away_k=z0_i, z_away_dir=z0_i, z_first_any=z0_i, z_first_full=z0_i,
        ci=z0_i, c_mc=z0_f, c_ses=z0_i, clo=z0_f, chi=z0_f, c_first_any=z0_i, c_first_full=z0_i,
    )
    if nm == 0 or zones_df is None or not len(zones_df):
        return vacio

    t_min_ns = (int(t[0]) - 86400 * 5) * 10**9
    t_max_ns = int(t[-1]) * 10**9
    t_z_all = zones_df["t_ns"].to_numpy(np.int64)
    m_keep = (t_z_all >= t_min_ns) & (t_z_all <= t_max_ns)
    if not m_keep.any():
        return vacio

    Z = zones_df.loc[m_keep].sort_values("t_ns", kind="stable").reset_index(drop=True)
    tz_ns = Z["t_ns"].to_numpy(np.int64)
    tz_s = np.ceil(tz_ns / 1e9).astype(np.int64)
    zi = np.searchsorted(t, tz_s, side="left").astype(np.int64)
    ok = zi < nm
    if not ok.any():
        return vacio
    if not ok.all():
        Z = Z.loc[ok].reset_index(drop=True)
        tz_ns = tz_ns[ok]
        tz_s = tz_s[ok]
        zi = zi[ok]

    # Reloj activo exacto al segundo dentro de la vela M1 `zi` (100% invariante al truncado en `>= zi`)
    sub_s = np.clip(t[zi].astype(np.float64) - tz_ns.astype(np.float64) * 1e-9, 0.0, 60.0)
    z_mc = mc_m1[zi] - sub_s
    # Garantizar monotonía no decreciente para el corte hacia atrás `edad > max_edad_seg`
    z_mc = np.maximum.accumulate(z_mc)
    z_ses = ses[zi]

    zlo = np.minimum(Z["lo"].to_numpy(np.float64), Z["hi"].to_numpy(np.float64))
    zhi = np.maximum(Z["lo"].to_numpy(np.float64), Z["hi"].to_numpy(np.float64))
    z_first_any, z_first_full = _mitigacion_barreras_nb(zi, zlo, zhi, h, l)

    # `z_fuerte`: Predator/Absorb o P67 causal de volumen HFT (o volumen M1 de creación si el almacén sólo tiene t_ns/lo/hi)
    vol_base = Z["total_vol"].to_numpy(np.float64) if "total_vol" in Z.columns else v[zi]
    p67_v = _p67_causal_nb(vol_base, 200, 15)
    if "bucket" in Z.columns:
        bkt = Z["bucket"].to_numpy(np.int64)
        z_fuerte = np.where((bkt == 0) | (bkt == 3) | (p67_v == 1), 1, 0).astype(np.int64)
    else:
        z_fuerte = p67_v

    # `z_away_k` y `z_away_dir`: del almacén exacto en 50T si existe, si no `resolver_alejamiento_barras_nb` causal en M1
    if "away_res_code" in Z.columns and "t_away_ns" in Z.columns and "away_dir" in Z.columns:
        aw_code = Z["away_res_code"].to_numpy(np.int64)
        taw_ns = Z["t_away_ns"].to_numpy(np.int64)
        aw_dir = Z["away_dir"].to_numpy(np.int64)
        taw_s = np.ceil(np.maximum(taw_ns, 0) / 1e9).astype(np.int64)
        ak_raw = np.searchsorted(t, taw_s, side="left")
        z_away_k = np.where((aw_code == 1) & (taw_ns > 0) & (taw_ns <= t_max_ns) & (ak_raw < nm), ak_raw, -1).astype(np.int64)
        z_away_dir = np.where(z_away_k >= 0, aw_dir, 0).astype(np.int64)
    else:
        b_end_ns = t * 10**9
        dummy_dir = np.ones(len(zi), np.int64)
        dummy_bkt = np.full(len(zi), 3, np.int64)
        aw_code, aw_dir, aw_bar, _ = HGC.resolver_alejamiento_barras_nb(
            zi, zlo, zhi, dummy_dir, dummy_bkt, c[zi],
            b_end_ns, h, l, tick,
            int(alejamiento_ticks_m1), 0, 50.0, 0, 0,
        )
        z_away_k = np.where((aw_code == 1) & (aw_bar >= 0) & (aw_bar < nm), aw_bar, -1).astype(np.int64)
        z_away_dir = np.where(z_away_k >= 0, aw_dir, 0).astype(np.int64)

    # Inventario de Clusters P10 (del almacén precalculado o calculado causalmente con `evaluar_clusters_p10_causal`)
    if clust_df is None:
        lo_tk = np.round(zlo / tick).astype(np.int64)
        hi_tk = np.maximum(lo_tk + 1, np.round(zhi / tick).astype(np.int64))
        bkt_c = Z["bucket"].to_numpy(np.int64) if "bucket" in Z.columns else np.zeros(len(zi), np.int64)
        _, clust_df = HGC.evaluar_clusters_p10_causal(
            zi, zi, tz_ns, lo_tk, hi_tk, bkt_c, vol_base, z_mc,
            tick=tick, min_zonas_cluster=4, vigencia_zona_min=360.0,
            ventana_grupos=100, min_grupos_warmup=20, percentil_altura=10.0,
            comparacion_estricta=True, extension_cluster_barras=360,
        )

    if clust_df is not None and len(clust_df):
        tc_all = clust_df["t_ns"].to_numpy(np.int64)
        mc_c_keep = (tc_all >= t_min_ns) & (tc_all <= t_max_ns)
        C = clust_df.loc[mc_c_keep].sort_values("t_ns", kind="stable").reset_index(drop=True)
    else:
        C = pd.DataFrame()

    if len(C):
        tc_ns = C["t_ns"].to_numpy(np.int64)
        ci = np.searchsorted(t, np.ceil(tc_ns / 1e9).astype(np.int64), side="left").astype(np.int64)
        ok_c = ci < nm
        if ok_c.any():
            C = C.loc[ok_c].reset_index(drop=True)
            tc_ns = tc_ns[ok_c]
            ci = ci[ok_c]
            sub_cs = np.clip(t[ci].astype(np.float64) - tc_ns.astype(np.float64) * 1e-9, 0.0, 60.0)
            c_mc = np.maximum.accumulate(mc_m1[ci] - sub_cs)
            c_ses = ses[ci]
            clo = C["lo"].to_numpy(np.float64)
            chi = C["hi"].to_numpy(np.float64)
            c_first_any, c_first_full = _mitigacion_barreras_nb(ci, clo, chi, h, l)
        else:
            ci = c_ses = c_first_any = c_first_full = z0_i
            c_mc = clo = chi = z0_f
    else:
        ci = c_ses = c_first_any = c_first_full = z0_i
        c_mc = clo = chi = z0_f

    return dict(
        mc_m1=mc_m1, ses_m1=ses,
        zi=zi, z_mc=z_mc, z_ses=z_ses, zlo=zlo, zhi=zhi,
        z_fuerte=z_fuerte, z_away_k=z_away_k, z_away_dir=z_away_dir,
        z_first_any=z_first_any, z_first_full=z_first_full,
        ci=ci, c_mc=c_mc, c_ses=c_ses, clo=clo, chi=chi,
        c_first_any=c_first_any, c_first_full=c_first_full,
    )


def evaluar_distancia_frontal(
    inv: dict,
    k_ops: np.ndarray,
    s_ops: np.ndarray,
    e_ops: np.ndarray,
    r_ops: np.ndarray,
    tipo_idx: int,
    edad_idx: int,
    mit_idx: int,
) -> np.ndarray:
    """Wrapper limpio sobre `distancias_libres_lote_nb` indexado por `(tipo_idx, edad_idx, mit_idx)`."""
    _, max_seg, solo_ses = ANTIGUEDADES[int(edad_idx)]
    return distancias_libres_lote_nb(
        np.asarray(k_ops, np.int64),
        np.asarray(s_ops, np.int64),
        np.asarray(e_ops, np.float64),
        np.asarray(r_ops, np.float64),
        inv["mc_m1"], inv["ses_m1"],
        inv["zi"], inv["z_mc"], inv["z_ses"], inv["zlo"], inv["zhi"],
        inv["z_fuerte"], inv["z_away_k"], inv["z_away_dir"], inv["z_first_any"], inv["z_first_full"],
        inv["ci"], inv["c_mc"], inv["c_ses"], inv["clo"], inv["chi"], inv["c_first_any"], inv["c_first_full"],
        int(tipo_idx), float(max_seg), int(solo_ses), int(mit_idx),
    )
