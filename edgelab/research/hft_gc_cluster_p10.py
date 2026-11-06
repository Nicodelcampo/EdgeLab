"""HFT-GC-P10 (2026-11-05, Programa R): Zonas HFT de Oro COMEX (`GC`) con Borde Gris + Flecha y Clusters `P10`.

Evalúa en todo el embudo formal de EdgeLab (`DESC 2025-08-05..2026-03-31` → `PISTAS / INDAGA / INTEGRIDAD / OOS 2026-04-01..2026-09-30`
→ `TOPES / ACTA / CONTEO / HOLDOUT >= 2026-10-01`) los 4 mecanismos estructurales del indicador `HFTZonesGCClusterP10.cs`:
  0. `B2_RETEST_GRIS`: Al confirmarse el alejamiento fijo de `20 ticks` sin comerciar la zona entera (Borde Gris),
     orden `Limit` (`limite=1`) en el borde cercano de la zona esperando la primera mitigación como Order Block HFT.
  1. `B1_FLECHA_CONT`: En la primera vela tras confirmarse el alejamiento (`limite=2`, `Open` de la vela de la flecha),
     entrada de continuación a favor de `away_dir` con stop detrás de la zona gris.
  2. `A1_CLUSTER_FADE`: Para cada `Cluster P10` nuevo (`>= 4` zonas HFT vigentes dentro del `P10` de los 100 grupos previos),
     en el primer cierre M1 fuera de la envolvente `[lo, hi]` sin rotura desbocada (`<= 4 * max(H, 10*tick)`),
     entrada (`limite=2`) operando el freno / regreso hacia el equilibrio (`POC` gravitacional) del cluster.
  3. `A2_CLUSTER_PULLBACK`: Cuando un `Cluster P10` confirma escape limpio de `20 ticks` sin comerciarse entero,
     orden `Limit` (`limite=1`) en el borde cercano del cluster operando soporte/resistencia institucional.

Paridad certificada 100% contra NinjaTrader 8 (`C:\\LoggerHFT\\data\\hft_logger_gc_cluster_p10.sqlite`: `0` discrepancias
en las `1.224` zonas, `124` eventos de cluster, `POC` y `1.223` eventos de alejamiento).
Pre-registro: `docs/research/hft_gc_p10_20261105/PREREGISTRO_HFT_GC_P10.md`.
"""
from __future__ import annotations

import glob
import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from edgelab.bridge.indicators import hft_gc_cluster_p10 as HGC
from edgelab.research.contexto_comun import atr_sesion
from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import lineas_salida  # noqa: F401
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "HFT-GC-P10"
INDICADORES = ["HFT-GC-CLUSTER-P10"]
NORMALIZAR = "riesgo"
PREFLIGHT_T0_S = 1_760_047_200
LINEAS_SOLO_TIEMPO = True
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)

MECANISMOS = ("B2_RETEST_GRIS", "B1_FLECHA_CONT", "A1_CLUSTER_FADE", "A2_CLUSTER_PULLBACK")
VARIABLES = [
    Variable("mecanismo", "mec", "grupo", categoria=len(MECANISMOS)),
    Variable("tipo_zona", "bkt", "eq_any", categoria=2),        # 0 Predator/Fast · 1 Absorb/Ultra · 2 cualquiera
    Variable("estructura", "en_cl", "eq_any", categoria=2),     # 0 aislada / 4z · 1 en cluster / >=5z · 2 cualquiera
    Variable("franja_ny", "franja", "eq_any", categoria=4),     # 0 Asia · 1 Londres · 2 COMEX Mañana · 3 NY Tarde · 4 cualquiera
    Variable("fuerza_vol", "vol_rel", "ge", cuantiles=3),       # volumen HFT relativo
    Variable("compresion", "alt_rel", "le", cuantiles=3),       # altura relativa a ATR14 de sesión
]
EJES_ORDINALES = (4, 5)
STOPS = ("S1_ZONA", "S3_ATR")
OBJETIVOS = (1.5, 2.0, 3.0)
EJECUCIONES = [(st, tp) for st in STOPS for tp in OBJETIVOS]
BASE = {
    "mecanismo": 0,
    "tipo_zona": 2,
    "estructura": 2,
    "franja_ny": 4,
    "fuerza_vol": 0,
    "compresion": 2,
    "ejecución": EJECUCIONES.index(("S3_ATR", 2.0)),
}
VACIO = [
    "k", "ses", "lado", "mec", "bkt", "en_cl", "franja",
    "vol_rel", "alt_rel", "zlo", "zhi", "poc", "atr",
]

_CACHE_REAL: Dict[Tuple, Dict[str, pd.DataFrame]] = {}


def _franja_oro_ny(min_ny_apertura: np.ndarray) -> np.ndarray:
    """Clasifica el minuto de apertura NY [0..1439] en las 4 subastas del oro; -1 en 16:30..17:59 ET (cierre COMEX)."""
    m = np.asarray(min_ny_apertura, np.int64)
    out = np.full(len(m), -1, np.int64)
    out[(m >= 1080) | (m < 180)] = 0           # 18:00 - 03:00 ET (Asia / Shanghái)
    out[(m >= 180) & (m < 500)] = 1            # 03:00 - 08:20 ET (Londres LBMA)
    out[(m >= 500) & (m < 720)] = 2            # 08:20 - 12:00 ET (COMEX Mañana + AM Fix)
    out[(m >= 720) & (m < 990)] = 3            # 12:00 - 16:30 ET (NY Tarde; excluye últimos 30m antes del cierre)
    return out


def _fuente_sintetica_causal(ctx: dict) -> Dict[str, pd.DataFrame]:
    """SOLO preflight y tests sintéticos (cuando no hay `sensor`): genera rachas sintéticas causales desde las velas M1
    del propio `ctx` y las pasa por el MISMO solver causal `P10` y `RevisarAlejamiento` que usa `GC` en producción."""
    t = np.asarray(ctx["t"], np.int64)
    o = np.asarray(ctx["o"], float)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    c = np.asarray(ctx["c"], float)
    v = np.asarray(ctx["v"], float)
    tick = float(ctx["tick"])
    n = len(c)
    if n < 10:
        return HGC.ejecutar_detector_completo(
            np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, float), np.zeros(0, np.int64), tick, 50
        )

    dt = np.diff(t, prepend=t[0]).astype(float)
    mc = np.cumsum(np.minimum(np.maximum(dt, 0.0), 300.0))
    rng_tk = np.round((h - l) / tick).astype(np.int64)
    body_tk = np.round(np.abs(c - o) / tick).astype(np.int64)
    cand = np.flatnonzero((np.arange(n) >= 5) & (rng_tk >= 3) & ((body_tk >= 3) | ((np.arange(n) % 4) == 0)))
    if not len(cand):
        return HGC.ejecutar_detector_completo(
            np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, float), np.zeros(0, np.int64), tick, 50
        )

    z_dir = np.where(c[cand] >= o[cand], 1, -1).astype(np.int64)
    es_abs = body_tk[cand] <= np.maximum(1, rng_tk[cand] // 2)
    z_bkt = np.where(es_abs, 3, np.where(v[cand] >= v[cand - 1], 0, 1)).astype(np.int64)
    lo_px = np.where(z_dir == 1, l[cand], np.minimum(o[cand], c[cand]))
    hi_px = np.where(z_dir == 1, np.maximum(o[cand], c[cand]), h[cand])
    hi_px = np.maximum(hi_px, lo_px + tick)
    lo_tk = np.round(lo_px / tick).astype(np.int64)
    hi_tk = np.maximum(lo_tk + 1, np.round(hi_px / tick).astype(np.int64))
    lo_px = lo_tk.astype(float) * tick
    hi_px = hi_tk.astype(float) * tick
    z_vol = v[cand] + 0.17 * rng_tk[cand].astype(float) + 0.03 * (cand % 7).astype(float)
    t_avail_ns = t[cand] * 10**9

    cl_cols, clust_df = HGC.evaluar_clusters_p10_causal(
        cand, cand, t_avail_ns, lo_tk, hi_tk, z_bkt, z_vol, mc[cand],
        tick=tick, min_zonas_cluster=4, vigencia_zona_min=360.0,
        ventana_grupos=100, min_grupos_warmup=15, percentil_altura=10.0,
        comparacion_estricta=True, extension_cluster_barras=360,
    )
    b_end_ns = t * 10**9
    aw_code, aw_dir, aw_bar, aw_ns = HGC.resolver_alejamiento_barras_nb(
        cand, lo_px, hi_px, z_dir, z_bkt, c[cand],
        b_end_ns, h, l, tick,
        alejamiento_ticks=12, excluir_vshape=0, vshape_pct=50.0, excluir_absorb=0, max_barras=0,
    )
    if len(clust_df):
        c_eb = clust_df["confirmed_bar"].to_numpy(np.int64)
        c_lo = clust_df["lo"].to_numpy(float)
        c_hi = clust_df["hi"].to_numpy(float)
        c_aw_code, c_aw_dir, _, c_aw_ns = HGC.resolver_alejamiento_barras_nb(
            c_eb, c_lo, c_hi, np.ones(len(clust_df), np.int64), np.full(len(clust_df), 3, np.int64), c_lo,
            b_end_ns, h, l, tick,
            alejamiento_ticks=12, excluir_vshape=0, vshape_pct=50.0, excluir_absorb=0, max_barras=0,
        )
        clust_df["away_res_code"] = c_aw_code
        clust_df["away_dir"] = c_aw_dir
        clust_df["t_away_ns"] = c_aw_ns
    else:
        clust_df["away_res_code"] = np.zeros(0, np.int64)
        clust_df["away_dir"] = np.zeros(0, np.int64)
        clust_df["t_away_ns"] = np.zeros(0, np.int64)

    zones_df = pd.DataFrame(dict(
        zone_id=np.arange(1, len(cand) + 1, dtype=np.int64),
        t_ns=t_avail_ns,
        lo=lo_px,
        hi=hi_px,
        dir=z_dir,
        bucket=z_bkt,
        total_vol=z_vol,
        market_clock_sec=mc[cand],
        in_cluster=cl_cols["in_cluster"],
        first_in_cluster_ns=cl_cols["first_in_cluster_ns"],
        away_res_code=aw_code,
        away_dir=aw_dir,
        t_away_ns=aw_ns,
    ))
    return {"HFTGCP10": zones_df, "HFTGCP10_CLUST": clust_df}


def cargar_fuente_gc(ctx: dict) -> Dict[str, pd.DataFrame]:
    """Carga el almacén precalculado `ZONAS_HFTGCP10_<INST>.parquet` si está adjunto, o lo calcula al vuelo en Numba
    directamente sobre `<INST>_ticks.parquet` (desarrollo y `SELLADO=1` holdout)."""
    if "zonas_hftgc" in ctx:
        return ctx["zonas_hftgc"]
    sensor = ctx.get("sensor") or os.environ.get("SENSOR")
    if not sensor:
        return _fuente_sintetica_causal(ctx)

    entrada = os.environ.get("ENTRADA", "/kaggle/input")
    sellado = os.environ.get("SELLADO") == "1"
    fz = glob.glob(f"{entrada}/**/ZONAS_HFTGCP10_{sensor}.parquet", recursive=True)
    fc = glob.glob(f"{entrada}/**/ZONAS_HFTGCP10_CLUST_{sensor}.parquet", recursive=True)
    if (not sellado) and fz and fc:
        key = ("parquet", fz[0], fc[0])
        if key not in _CACHE_REAL:
            _CACHE_REAL[key] = {"HFTGCP10": pd.read_parquet(fz[0]), "HFTGCP10_CLUST": pd.read_parquet(fc[0])}
        return _CACHE_REAL[key]

    from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, HOLDOUT_PRIMERA_SESION_INT
    from edgelab.research import fuentes_ticks as F

    tick = float(F.TICK_FUTURO[sensor])
    if sellado:
        hasta = int(os.environ.get("HASTA", 20991231))
        key = ("sellado", sensor, hasta, entrada)
        if key not in _CACHE_REAL:
            r = sorted(glob.glob(f"{entrada}/**/{sensor}_*ticks.parquet", recursive=True))
            if not r:
                raise FileNotFoundError(f"sin ticks sellados de {sensor} en {entrada}")
            acta = os.environ.get("ACTA_HOLDOUT_RUTA") or os.path.abspath("ACTA_HOLDOUT.json")
            bl = list(F.bloques_nq_sellado(HOLDOUT_PRIMERA_SESION_INT, hasta, r, acta, tick))
            out_s = HGC.almacen_gc(bl, tick=tick, spec=50)
            if fz and fc:
                zd = pd.read_parquet(fz[0]); zd = zd[zd.t_ns < HOLDOUT_APERTURA_UTC_NS]
                cd = pd.read_parquet(fc[0]); cd = cd[cd.t_ns < HOLDOUT_APERTURA_UTC_NS]
                out_s = {
                    "HFTGCP10": pd.concat([zd, out_s["HFTGCP10"]], ignore_index=True).sort_values("t_ns", kind="stable", ignore_index=True),
                    "HFTGCP10_CLUST": pd.concat([cd, out_s["HFTGCP10_CLUST"]], ignore_index=True).sort_values("t_ns", kind="stable", ignore_index=True),
                }
            _CACHE_REAL[key] = out_s
        return _CACHE_REAL[key]

    t_close = np.asarray(ctx["t"], np.int64)
    d0_env = int(os.environ.get("DESDE") or int(pd.Timestamp(int(t_close[0]), unit="s", tz="UTC").strftime("%Y%m%d")))
    d1_env = min(int(os.environ.get("HASTA") or int(pd.Timestamp(int(t_close[-1]), unit="s", tz="UTC").strftime("%Y%m%d"))), 20260930)
    d_cal = max(20250701, int((pd.Timestamp(str(d0_env)) - pd.Timedelta(days=45)).strftime("%Y%m%d")))
    key = ("ticks_dev", sensor, d_cal, d1_env, entrada)
    if key not in _CACHE_REAL:
        _CACHE_REAL[key] = HGC.almacen_gc(F.bloques_futuro(sensor, d_cal, d1_env, entrada), tick=tick, spec=50)
    return _CACHE_REAL[key]


def _vol_medio_causal(v: np.ndarray, ses: np.ndarray, ventana: int = 20) -> np.ndarray:
    """Media móvil causal de volumen M1 dentro de cada sesión CME (`[max(s_ini, k-ventana+1) .. k]`)."""
    n = len(v)
    out = np.empty(n, np.float64)
    i = 0
    while i < n:
        s0 = i
        while i < n and ses[i] == ses[s0]:
            i += 1
        csum = np.cumsum(v[s0:i])
        for j in range(i - s0):
            a = j - ventana
            s_v = csum[j] - (csum[a] if a >= 0 else 0.0)
            cnt = j - max(a, -1)
            out[s0 + j] = max(s_v / float(max(cnt, 1)), 1.0)
    return out


def disparos(ctx: dict) -> pd.DataFrame:
    t = np.asarray(ctx["t"], np.int64)
    if not len(t):
        return pd.DataFrame(columns=VACIO)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    c = np.asarray(ctx["c"], float)
    v = np.asarray(ctx["v"], float)
    ses = np.asarray(ctx["ses"], np.int64)
    tick = float(ctx["tick"])
    n = len(c)

    atr_raw = atr_sesion(h, l, c, ses, 14)
    atr_ok = np.isfinite(atr_raw)
    atr = np.where(atr_ok, np.maximum(atr_raw, tick), tick)
    v_med = _vol_medio_causal(v, ses, 20)
    franjas = _franja_oro_ny(minuto_ny(t - 60))

    fuente = cargar_fuente_gc(ctx)
    Z = fuente["HFTGCP10"]
    C = fuente["HFTGCP10_CLUST"]
    t_min_ns = (int(t[0]) - 60) * 10**9
    t_max_ns = int(t[-1]) * 10**9

    filas = []

    # --- Mecanismos B2 (0: Retest Zona Gris) y B1 (1: Continuación Flecha) ---
    if len(Z):
        aw_ok = (
            (Z["away_res_code"].to_numpy(np.int64) == 1)
            & (Z["t_away_ns"].to_numpy(np.int64) > t_min_ns)
            & (Z["t_away_ns"].to_numpy(np.int64) <= t_max_ns)
        )
        Za = Z.loc[aw_ok]
        if len(Za):
            t_aw_s = np.ceil(Za["t_away_ns"].to_numpy(np.int64) / 1e9).astype(np.int64)
            ks = np.searchsorted(t, t_aw_s, side="left")
            zlo_a = Za["lo"].to_numpy(float)
            zhi_a = Za["hi"].to_numpy(float)
            adir_a = Za["away_dir"].to_numpy(np.int64)
            bkt_raw = Za["bucket"].to_numpy(np.int64)
            vol_a = Za["total_vol"].to_numpy(float)
            f_cl_ns = Za["first_in_cluster_ns"].to_numpy(np.int64)

            for i in range(len(ks)):
                k = int(ks[i])
                if k < 1 or k >= n or not atr_ok[k]:
                    continue
                fr = int(franjas[k])
                if fr < 0:
                    continue
                lado = int(adir_a[i])
                if lado == 0:
                    continue
                bkt = 1 if int(bkt_raw[i]) in (1, 3) else 0
                en_cl = 1 if (f_cl_ns[i] > 0 and f_cl_ns[i] <= int(t[k]) * 10**9) else 0
                zlo = float(zlo_a[i])
                zhi = float(zhi_a[i])
                mid = 0.5 * (zlo + zhi)
                ak = float(atr[k])
                vr = float(vol_a[i]) / float(v_med[k])
                ar = max(zhi - zlo, tick) / ak
                sk = int(ses[k])
                # 0 = B2_RETEST_GRIS (Limit en el borde de la zona gris)
                filas.append((k, sk, lado, 0, bkt, en_cl, fr, vr, ar, zlo, zhi, mid, ak))
                # 1 = B1_FLECHA_CONT (Open de la primera vela tras confirmarse la zona gris)
                filas.append((k, sk, lado, 1, bkt, en_cl, fr, vr, ar, zlo, zhi, mid, ak))

    # --- Mecanismos A1 (2: Cluster P10 Fade al POC) y A2 (3: Cluster P10 Pullback Soporte) ---
    if len(C):
        c_new = C.loc[(C["event_type"] == "NEW") & (C["t_ns"].to_numpy(np.int64) <= t_max_ns)]
        if len(c_new):
            tc_s = np.ceil(c_new["t_ns"].to_numpy(np.int64) / 1e9).astype(np.int64)
            k_conf = np.searchsorted(t, tc_s, side="left")
            clo_a = c_new["lo"].to_numpy(float)
            chi_a = c_new["hi"].to_numpy(float)
            cpoc_a = c_new["poc"].to_numpy(float)
            cvol_a = c_new["total_vol"].to_numpy(float)
            czcnt_a = c_new["zone_count"].to_numpy(np.int64)
            cab_a = c_new["absorb_ultra_frac"].to_numpy(float)
            c_aw_code = c_new["away_res_code"].to_numpy(np.int64)
            c_aw_dir = c_new["away_dir"].to_numpy(np.int64)
            c_aw_ns = c_new["t_away_ns"].to_numpy(np.int64)

            for i in range(len(k_conf)):
                kc = int(k_conf[i])
                clo = float(clo_a[i])
                chi = float(chi_a[i])
                cpoc = float(cpoc_a[i])
                bkt_c = 1 if float(cab_a[i]) >= 0.5 else 0
                en_cl_c = 1 if int(czcnt_a[i]) >= 5 else 0
                hc = max(chi - clo, 10.0 * tick)

                # A1: primera vela M1 posterior a kc que cierra fuera de [clo, chi] dentro de 360 min
                if 0 <= kc < n:
                    t_lim = int(t[kc]) + 360 * 60
                    tup = False
                    tlo = False
                    for j in range(kc + 1, n):
                        if int(t[j]) > t_lim:
                            break
                        if c[j] > chi + 1e-9 or c[j] < clo - 1e-9:
                            lado_f = -1 if c[j] > chi else 1
                            exc = (c[j] - chi) if lado_f == -1 else (clo - c[j])
                            fr = int(franjas[j])
                            if atr_ok[j] and fr >= 0:
                                aj = float(atr[j])
                                if exc <= max(8.0 * hc, 6.0 * aj):
                                    vr = float(cvol_a[i]) / float(v_med[j])
                                    ar = max(chi - clo, tick) / aj
                                    filas.append((j, int(ses[j]), lado_f, 2, bkt_c, en_cl_c, fr, vr, ar, clo, chi, cpoc, aj))
                            break
                        if h[j] >= chi - 1e-9:
                            tup = True
                        if l[j] <= clo + 1e-9:
                            tlo = True
                        if tup and tlo:
                            break

                # A2: pullback Limit al borde del Cluster tras confirmar alejamiento de 20 ticks
                if int(c_aw_code[i]) == 1 and t_min_ns < int(c_aw_ns[i]) <= t_max_ns:
                    kaw = int(np.searchsorted(t, int(np.ceil(c_aw_ns[i] / 1e9)), side="left"))
                    lado_p = int(c_aw_dir[i])
                    if 1 <= kaw < n and atr_ok[kaw] and lado_p != 0:
                        fr = int(franjas[kaw])
                        if fr >= 0:
                            ak = float(atr[kaw])
                            vr = float(cvol_a[i]) / float(v_med[kaw])
                            ar = max(chi - clo, tick) / ak
                            filas.append((kaw, int(ses[kaw]), lado_p, 3, bkt_c, en_cl_c, fr, vr, ar, clo, chi, cpoc, ak))

    if not filas:
        return pd.DataFrame(columns=VACIO)
    df = pd.DataFrame(filas, columns=VACIO)
    return df.sort_values(["k", "mec", "lado", "zlo", "zhi"], kind="stable").reset_index(drop=True)


def niveles(fila: dict, ej: tuple, ctx: dict):
    st_modo, mult_tp = ej
    k = int(fila["k"])
    s = int(fila["lado"])
    mec = int(fila["mec"])
    zlo = float(fila["zlo"])
    zhi = float(fila["zhi"])
    atr = float(fila["atr"])
    tick = float(ctx["tick"])
    c_k = float(ctx["c"][k])
    h_k = float(ctx["h"][k])
    l_k = float(ctx["l"][k])

    ancho_z = max(zhi - zlo, tick)
    holgura = 6.0 * tick if st_modo == "S1_ZONA" else max(16.0 * tick, 0.50 * atr)
    piso_tk = 15.0 * tick if st_modo == "S1_ZONA" else 24.0 * tick

    if mec in (0, 3):  # Orden Limit en el borde cercano de la zona gris o del Cluster P10
        limite = 1
        entrada = zhi if s == 1 else zlo
        dist_stop = max(piso_tk, ancho_z + holgura)
    elif mec == 1:     # Entrada Open en la vela de la flecha (k + 1)
        limite = 2
        entrada = c_k
        borde_op = zlo if s == 1 else zhi
        dist_raw = (entrada - borde_op) * s
        if dist_raw <= -4.0 * tick:
            return None
        dist_stop = max(piso_tk + 3.0 * tick, max(dist_raw, 4.0 * tick) + holgura)
    else:              # mec == 2: Fade Cluster P10 desde el cierre fuera de la banda
        limite = 2
        entrada = c_k
        extremo_v = l_k if s == 1 else h_k
        dist_raw = max((entrada - extremo_v) * s, 2.0 * tick)
        dist_stop = max(piso_tk, dist_raw + holgura)

    entrada = float(np.round(entrada / tick) * tick)
    st_raw = entrada - s * dist_stop
    stop = float((np.floor(st_raw / tick) if s == 1 else np.ceil(st_raw / tick)) * tick)
    riesgo = abs(entrada - stop)
    if riesgo < tick:
        return None
    objetivo = float(np.round((entrada + s * float(mult_tp) * riesgo) / tick) * tick)
    if (objetivo - entrada) * s < tick:
        return None
    return (k, limite, s, entrada, stop, objetivo, 0, (0 if s == 1 else 1), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    m = len(D)
    out = np.full((m, 9), np.nan, dtype=np.float64)
    if m == 0:
        return out
    st_modo, mult_tp = ej
    tick = float(ctx["tick"])
    k = D["k"].to_numpy(np.int64)
    s = D["lado"].to_numpy(np.int64)
    mec = D["mec"].to_numpy(np.int64)
    zlo = D["zlo"].to_numpy(np.float64)
    zhi = D["zhi"].to_numpy(np.float64)
    atr = D["atr"].to_numpy(np.float64)
    c_k = np.asarray(ctx["c"], np.float64)[k]
    h_k = np.asarray(ctx["h"], np.float64)[k]
    l_k = np.asarray(ctx["l"], np.float64)[k]

    ancho_z = np.maximum(zhi - zlo, tick)
    holgura = np.full(m, 6.0 * tick) if st_modo == "S1_ZONA" else np.maximum(16.0 * tick, 0.50 * atr)
    piso_tk = 15.0 * tick if st_modo == "S1_ZONA" else 24.0 * tick

    es_lim = (mec == 0) | (mec == 3)
    es_b1 = mec == 1

    limite = np.where(es_lim, 1.0, 2.0)
    entrada = np.where(es_lim, np.where(s == 1, zhi, zlo), c_k)

    borde_op = np.where(s == 1, zlo, zhi)
    dist_b1 = (entrada - borde_op) * s
    extremo_v = np.where(s == 1, l_k, h_k)
    dist_a1 = np.maximum((entrada - extremo_v) * s, 2.0 * tick)

    dist_stop = np.where(
        es_lim,
        np.maximum(piso_tk, ancho_z + holgura),
        np.where(
            es_b1,
            np.maximum(piso_tk + 3.0 * tick, np.maximum(dist_b1, 4.0 * tick) + holgura),
            np.maximum(piso_tk, dist_a1 + holgura),
        ),
    )

    valido = (~es_b1) | (dist_b1 > -4.0 * tick)
    entrada_r = np.round(entrada / tick) * tick
    st_raw = entrada_r - s * dist_stop
    stop_r = np.where(s == 1, np.floor(st_raw / tick), np.ceil(st_raw / tick)) * tick
    riesgo = np.abs(entrada_r - stop_r)
    valido &= riesgo >= tick
    objetivo_r = np.round((entrada_r + s * float(mult_tp) * riesgo) / tick) * tick
    valido &= ((objetivo_r - entrada_r) * s) >= tick

    out[valido, 0] = k[valido]
    out[valido, 1] = limite[valido]
    out[valido, 2] = s[valido]
    out[valido, 3] = entrada_r[valido]
    out[valido, 4] = stop_r[valido]
    out[valido, 5] = objetivo_r[valido]
    out[valido, 6] = 0.0
    out[valido, 7] = np.where(s[valido] == 1, 0.0, 1.0)
    out[valido, 8] = 0.0
    return out
