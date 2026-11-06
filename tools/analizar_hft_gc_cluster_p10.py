"""Análisis estructurado en EdgeLab para HFTZonesGCClusterP10 (SQLite Logger NT8).

Arquitectura en 3 capas (dejando listo el libro causal de zonas activas para el filtro de barreras HFT
en la siguiente etapa, sin medir ni activar dicho filtro ahora):
1. `LibroZonasActivas`: estado barra a barra de todas las zonas HFT, su vigencia en reloj de mercado activo,
   estado de mitigación (`virgen`, `parcial`, `comerciada_entera`), confirmación de borde gris y pertenencia a Cluster P10.
   Incluye `zonas_en_recorrido(...)` listo para conectar como filtro de barreras/frenos HFT cuando lo pidas.
2. Paridad matemática 100% entre C# (`HFTZonesGCClusterP10.cs`) y Python (`verificar_paridad_solver_p10`).
3. Evaluación en `R` (estándar Programa R) y deriva direccional (ticks y R) de los mecanismos del indicador:
   - Mecanismo B1: Entrada en el inicio (`Open`) de la primera vela tras confirmarse el alejamiento (vela de la flecha).
   - Mecanismo B2: Mitigación (primer retorno del precio) a una zona con Borde Gris (aislada vs dentro de Cluster P10).
   - Mecanismo A: Clusters P10 (ruptura de la banda, reversión al POC desde los extremos, re-testeo post-escape y
     comparación contra el grupo de control `P10..2xP10` y `> 2xP10`).
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


DB_DEFAULT = Path(r"C:\LoggerHFT\data\hft_logger_gc_cluster_p10.sqlite")


@dataclass
class ConfigSimulacionR:
    tick_size: float = 0.10
    piso_riesgo_ticks: int = 12          # Piso mínimo de stop (12 ticks = $1.20 en GC)
    buffer_stop_S3_ticks: int = 6        # Holgura estructural S3 detrás de la zona/cluster
    max_duracion_min: int = 240          # Tope estándar Programa R (240 min = 4h)
    costo_ida_vuelta_ticks: float = 1.6  # Costo neto conservador en GC


class LibroZonasActivas:
    """Mantiene barra a barra el inventario causal de zonas HFT y Clusters P10.

    Deja preparado `zonas_en_recorrido()` para la siguiente etapa (filtrar entradas cuando existan
    zonas HFT vigentes que actúen como barrera y frenen al precio camino al objetivo).
    """

    def __init__(self, bars_df: pd.DataFrame, zones_df: pd.DataFrame, away_df: pd.DataFrame,
                 clusters_df: pd.DataFrame, vigencia_mercado_seg: float = 360 * 60.0):
        self.bars = bars_df.sort_values("bar_idx").reset_index(drop=True)
        self.zones = zones_df.sort_values("zone_id").reset_index(drop=True)
        self.away = away_df.set_index("zone_id") if len(away_df) else pd.DataFrame()
        self.clusters = clusters_df.sort_values("event_seq").reset_index(drop=True)
        self.vigencia_seg = vigencia_mercado_seg
        self._precomputar_ciclo_vida()

    def _precomputar_ciclo_vida(self) -> None:
        hi = self.bars["high"].to_numpy(dtype=np.float64)
        lo = self.bars["low"].to_numpy(dtype=np.float64)
        n_bars = len(hi)

        first_touch_upper = np.full(len(self.zones), -1, dtype=np.int64)
        first_touch_lower = np.full(len(self.zones), -1, dtype=np.int64)
        first_mitigated_full = np.full(len(self.zones), -1, dtype=np.int64)
        first_retest_after_away = np.full(len(self.zones), -1, dtype=np.int64)

        away_res_map = self.away["resolution"].to_dict() if len(self.away) else {}
        away_bar_map = self.away["resolved_bar"].to_dict() if len(self.away) else {}
        away_dir_map = self.away["away_dir"].to_dict() if len(self.away) else {}

        # También marcar todas las zonas que fueron miembro de algún cluster P10
        member_ids = set()
        for s in self.clusters["member_zone_ids"].dropna():
            for tok in str(s).split(","):
                tok = tok.strip()
                if tok.isdigit():
                    member_ids.add(int(tok))

        in_any_cluster = np.zeros(len(self.zones), dtype=np.int64)

        for idx, z in self.zones.iterrows():
            zid = int(z["zone_id"])
            if zid in member_ids or int(z["triggered_cluster"]) == 1:
                in_any_cluster[idx] = 1

            eb = int(z["end_bar"])
            z_up = float(z["price_upper"])
            z_lo = float(z["price_lower"])

            t_up = -1
            t_lo = -1
            t_full = -1
            for b in range(eb + 1, n_bars):
                if t_up < 0 and hi[b] >= z_up - 1e-9:
                    t_up = b
                if t_lo < 0 and lo[b] <= z_lo + 1e-9:
                    t_lo = b
                if t_up >= 0 and t_lo >= 0:
                    t_full = b
                    break

            first_touch_upper[idx] = t_up
            first_touch_lower[idx] = t_lo
            first_mitigated_full[idx] = t_full

            if away_res_map.get(zid) == "CONFIRMED":
                rbar = int(away_bar_map.get(zid, -1))
                adir = int(away_dir_map.get(zid, 0))
                if rbar >= 0 and adir != 0:
                    for b in range(rbar + 1, n_bars):
                        if adir == 1 and lo[b] <= z_up + 1e-9:
                            first_retest_after_away[idx] = b
                            break
                        elif adir == -1 and hi[b] >= z_lo - 1e-9:
                            first_retest_after_away[idx] = b
                            break

        self.zones["in_any_cluster"] = in_any_cluster
        self.zones["first_touch_upper_bar"] = first_touch_upper
        self.zones["first_touch_lower_bar"] = first_touch_lower
        self.zones["first_mitigated_bar"] = first_mitigated_full
        self.zones["first_retest_after_away_bar"] = first_retest_after_away

    def zonas_en_recorrido(
        self,
        bar_idx: int,
        market_clock_sec: float,
        precio_origen: float,
        precio_destino: float,
        solo_no_mitigadas: bool = True,
        excluir_zone_id: int = -1,
    ) -> pd.DataFrame:
        """Hook preparado (NO medido aún): devuelve las zonas HFT vigentes en `bar_idx` interpuestas
        entre `precio_origen` y `precio_destino` que podrían actuar como barrera/freno."""
        p_min = min(precio_origen, precio_destino)
        p_max = max(precio_origen, precio_destino)

        cond = (
            (self.zones["end_bar"] < bar_idx)
            & ((market_clock_sec - self.zones["market_clock_sec"]) <= self.vigencia_seg)
            & (self.zones["zone_id"] != excluir_zone_id)
            & (self.zones["price_upper"] >= p_min)
            & (self.zones["price_lower"] <= p_max)
        )
        if solo_no_mitigadas:
            cond &= (self.zones["first_mitigated_bar"] < 0) | (self.zones["first_mitigated_bar"] > bar_idx)
        return self.zones.loc[cond].copy()


def verificar_paridad_solver_p10(zones_df: pd.DataFrame, vigencia_seg: float = 360 * 60.0,
                                 k_req: int = 4, ventana_n: int = 100, min_warmup: int = 20,
                                 percentil: float = 10.0, estricto: bool = True) -> Dict[str, int]:
    hist: List[int] = []
    dif_min4 = 0
    dif_p10 = 0
    dif_trig = 0

    rows = zones_df.to_dict("records")
    for idx, nz in enumerate(rows):
        vig = []
        for j in range(idx, -1, -1):
            cand = rows[j]
            if (nz["market_clock_sec"] - cand["market_clock_sec"]) > vigencia_seg + 1e-9:
                break
            vig.append(cand)

        if len(vig) < k_req:
            if int(nz["min4_height_ticks"]) != -1:
                dif_min4 += 1
            continue

        otras = [z for z in vig if z["zone_id"] != nz["zone_id"]]
        otras.sort(key=lambda z: int(z["upper_tick"]))
        need = k_req - 1
        best_h4 = 10**12

        for z_piso in vig:
            piso = int(z_piso["lower_tick"])
            if piso > int(nz["lower_tick"]):
                continue
            tomados = 0
            max_up = int(nz["upper_tick"])
            for oz in otras:
                if int(oz["lower_tick"]) < piso:
                    continue
                if int(oz["upper_tick"]) > max_up:
                    max_up = int(oz["upper_tick"])
                tomados += 1
                if tomados == need:
                    break
            if tomados == need:
                span = max_up - piso
                if span < best_h4:
                    best_h4 = span

        n_hist = len(hist)
        es_cluster = False
        umbral_p10 = 0
        if n_hist >= min_warmup:
            ordenado = sorted(hist)
            idx_corte = max(0, min(n_hist - 1, int(math.ceil((percentil / 100.0) * n_hist)) - 1))
            umbral_p10 = ordenado[idx_corte]
            piso_hist = ordenado[0]
            max_span = (umbral_p10 - 1) if (estricto and umbral_p10 > piso_hist) else umbral_p10
            es_cluster = best_h4 <= max_span

        hist.append(best_h4)
        if len(hist) > ventana_n:
            hist.pop(0)

        if best_h4 != int(nz["min4_height_ticks"]):
            dif_min4 += 1
        if umbral_p10 != int(nz["p10_threshold_ticks"]):
            dif_p10 += 1
        if int(es_cluster) != int(nz["triggered_cluster"]):
            dif_trig += 1

    return {
        "total_zonas": len(rows),
        "discrepancias_min4_height": dif_min4,
        "discrepancias_p10_threshold": dif_p10,
        "discrepancias_trigger": dif_trig,
    }


def simular_trayectoria(
    hi: np.ndarray,
    lo: np.ndarray,
    cl: np.ndarray,
    close_ts_ms: np.ndarray,
    start_eval_bar: int,
    entry_price: float,
    side: int,
    stop_dist: float,
    cfg: ConfigSimulacionR,
) -> Optional[Dict[str, float]]:
    n_bars = len(cl)
    if start_eval_bar >= n_bars or stop_dist <= 0:
        return None

    costo_r = (cfg.costo_ida_vuelta_ticks * cfg.tick_size) / stop_dist
    t0_ms = close_ts_ms[max(0, start_eval_bar - 1)]
    max_ms = cfg.max_duracion_min * 60 * 1000

    sl_px = entry_price - side * stop_dist
    tp1_px = entry_price + side * (1.0 * stop_dist)
    tp2_px = entry_price + side * (2.0 * stop_dist)
    tp3_px = entry_price + side * (3.0 * stop_dist)

    res_t1 = None
    res_t2 = None
    res_t3 = None
    res_t2_bruto = None
    mfe_60 = 0.0
    mae_60 = 0.0

    # Deriva pura sin stop en barras (5, 10, 20 barras de 50-Tick)
    drift_5b_ticks = ((cl[min(n_bars - 1, start_eval_bar + 4)] - entry_price) * side) / cfg.tick_size
    drift_10b_ticks = ((cl[min(n_bars - 1, start_eval_bar + 9)] - entry_price) * side) / cfg.tick_size
    drift_20b_ticks = ((cl[min(n_bars - 1, start_eval_bar + 19)] - entry_price) * side) / cfg.tick_size

    last_b = start_eval_bar
    for b in range(start_eval_bar, n_bars):
        last_b = b
        dt_ms = close_ts_ms[b] - t0_ms

        if side == 1:
            fav_r = (hi[b] - entry_price) / stop_dist
            adv_r = (entry_price - lo[b]) / stop_dist
            hit_sl = lo[b] <= sl_px + 1e-9
            hit_tp1 = hi[b] >= tp1_px - 1e-9
            hit_tp2 = hi[b] >= tp2_px - 1e-9
            hit_tp3 = hi[b] >= tp3_px - 1e-9
        else:
            fav_r = (entry_price - lo[b]) / stop_dist
            adv_r = (hi[b] - entry_price) / stop_dist
            hit_sl = hi[b] >= sl_px - 1e-9
            hit_tp1 = lo[b] <= tp1_px + 1e-9
            hit_tp2 = lo[b] <= tp2_px + 1e-9
            hit_tp3 = lo[b] <= tp3_px + 1e-9

        if dt_ms <= 60 * 60 * 1000:
            if fav_r > mfe_60:
                mfe_60 = fav_r
            if adv_r > mae_60:
                mae_60 = adv_r

        if res_t1 is None:
            if hit_sl:
                res_t1 = -1.0 - costo_r
            elif hit_tp1:
                res_t1 = +1.0 - costo_r

        if res_t2 is None:
            if hit_sl:
                res_t2 = -1.0 - costo_r
                res_t2_bruto = -1.0
            elif hit_tp2:
                res_t2 = +2.0 - costo_r
                res_t2_bruto = +2.0

        if res_t3 is None:
            if hit_sl:
                res_t3 = -1.0 - costo_r
            elif hit_tp3:
                res_t3 = +3.0 - costo_r

        if (res_t1 is not None and res_t2 is not None and res_t3 is not None) and dt_ms > 60 * 60 * 1000:
            break
        if dt_ms >= max_ms:
            break

    final_raw_r = ((cl[last_b] - entry_price) * side) / stop_dist
    if res_t1 is None:
        res_t1 = final_raw_r - costo_r
    if res_t2 is None:
        res_t2 = final_raw_r - costo_r
        res_t2_bruto = final_raw_r
    if res_t3 is None:
        res_t3 = final_raw_r - costo_r

    return {
        "r_t1": res_t1,
        "r_t2": res_t2,
        "r_t2_bruto": res_t2_bruto,
        "r_t3": res_t3,
        "mfe_r_60m": mfe_60,
        "mae_r_60m": mae_60,
        "drift_5b_ticks": drift_5b_ticks,
        "drift_10b_ticks": drift_10b_ticks,
        "drift_20b_ticks": drift_20b_ticks,
        "stop_ticks": stop_dist / cfg.tick_size,
    }


def resumir_df(df: pd.DataFrame, col: str = "r_t2") -> Dict[str, float]:
    if len(df) == 0 or col not in df:
        return {"n": 0, "media_r_neta": 0.0, "media_r_bruta": 0.0, "t_stat": 0.0, "win_pct": 0.0,
                "mfe60_med": 0.0, "mae60_med": 0.0, "drift10b_ticks": 0.0}
    v = df[col].dropna().to_numpy(dtype=np.float64)
    n = len(v)
    mean = float(np.mean(v))
    std = float(np.std(v, ddof=1)) if n > 1 else 0.0
    t_stat = mean / (std / math.sqrt(n)) if std > 1e-9 and n > 1 else 0.0
    bruto = float(np.mean(df["r_t2_bruto"])) if "r_t2_bruto" in df else mean
    return {
        "n": int(n),
        "media_r_neta": round(mean, 4),
        "media_r_bruta": round(bruto, 4),
        "t_stat": round(t_stat, 2),
        "win_pct": round(float(np.mean(v > 0) * 100.0), 1),
        "mfe60_med": round(float(np.median(df["mfe_r_60m"])), 2),
        "mae60_med": round(float(np.median(df["mae_r_60m"])), 2),
        "drift10b_ticks": round(float(np.mean(df["drift_10b_ticks"])), 2),
        "stop_ticks_med": round(float(np.median(df["stop_ticks"])), 1),
    }


def franja_horaria_et(ts_ms: int) -> str:
    dt_utc = pd.to_datetime(ts_ms, unit="ms", utc=True)
    dt_et = dt_utc - pd.Timedelta(hours=4)
    hm = dt_et.hour * 60 + dt_et.minute
    if 18 * 60 <= hm or hm < 3 * 60:
        return "1_Asia_1800_0300_ET"
    elif 3 * 60 <= hm < 8 * 60 + 20:
        return "2_Londres_0300_0820_ET"
    elif 8 * 60 + 20 <= hm < 12 * 60:
        return "3_COMEX_Manana_0820_1200_ET"
    else:
        return "4_NY_Tarde_1200_1700_ET"


def ejecutar_estudio(db_path: Path = DB_DEFAULT) -> dict:
    conn = sqlite3.connect(str(db_path))
    run_row = pd.read_sql_query("SELECT * FROM logger_runs ORDER BY run_id DESC LIMIT 1", conn).iloc[0]
    run_id = int(run_row["run_id"])

    bars = pd.read_sql_query(f"SELECT * FROM primary_bars WHERE run_id = {run_id} ORDER BY bar_idx", conn)
    zones = pd.read_sql_query(f"SELECT * FROM hft_zones WHERE run_id = {run_id} ORDER BY zone_id", conn)
    clusters = pd.read_sql_query(f"SELECT * FROM hft_clusters_p10 WHERE run_id = {run_id} ORDER BY event_seq", conn)
    away = pd.read_sql_query(f"SELECT * FROM hft_away_events WHERE run_id = {run_id} ORDER BY zone_id", conn)
    conn.close()

    cfg = ConfigSimulacionR(tick_size=float(run_row["tick_size"]))
    libro = LibroZonasActivas(bars, zones, away, clusters)
    paridad = verificar_paridad_solver_p10(zones)

    hi = bars["high"].to_numpy(dtype=np.float64)
    lo = bars["low"].to_numpy(dtype=np.float64)
    cl = bars["close"].to_numpy(dtype=np.float64)
    op = bars["open"].to_numpy(dtype=np.float64)
    close_ts = bars["close_ts"].to_numpy(dtype=np.int64)
    zones_by_id = libro.zones.set_index("zone_id")

    confirmed_away = away[away["resolution"] == "CONFIRMED"].copy()

    # 1. B1_OPEN: Entrada exactamente en el Open de `arrow_bar` (inicio de la primera vela tras confirmarse la zona)
    b1_open_cont = []
    b1_open_fade = []
    for _, aw in confirmed_away.iterrows():
        zid = int(aw["zone_id"])
        abar = int(aw["arrow_bar"])
        adir = int(aw["away_dir"])
        if abar < 0 or abar >= len(bars) or zid not in zones_by_id.index:
            continue
        z = zones_by_id.loc[zid]
        entry_px = float(op[abar])
        if adir == 1:
            raw_stop = (entry_px - float(z["price_lower"])) + cfg.buffer_stop_S3_ticks * cfg.tick_size
        else:
            raw_stop = (float(z["price_upper"]) - entry_px) + cfg.buffer_stop_S3_ticks * cfg.tick_size
        stop_dist = max(raw_stop, cfg.piso_riesgo_ticks * cfg.tick_size)

        sc = simular_trayectoria(hi, lo, cl, close_ts, abar, entry_px, adir, stop_dist, cfg)
        if sc:
            sc["bucket"] = z["bucket"]
            sc["franja"] = franja_horaria_et(int(close_ts[abar]))
            sc["in_cluster"] = int(z["in_any_cluster"])
            b1_open_cont.append(sc)

        sf = simular_trayectoria(hi, lo, cl, close_ts, abar, entry_px, -adir, stop_dist, cfg)
        if sf:
            sf["bucket"] = z["bucket"]
            sf["franja"] = franja_horaria_et(int(close_ts[abar]))
            sf["in_cluster"] = int(z["in_any_cluster"])
            b1_open_fade.append(sf)

    df_b1_cont = pd.DataFrame(b1_open_cont)
    df_b1_fade = pd.DataFrame(b1_open_fade)

    # 2. B2_LIMIT: Mitigación (primer retorno a tocar el borde de la zona con Borde Gris: orden Limit en el borde)
    b2_limit_rebote = []
    for _, aw in confirmed_away.iterrows():
        zid = int(aw["zone_id"])
        adir = int(aw["away_dir"])
        if zid not in zones_by_id.index:
            continue
        z = zones_by_id.loc[zid]
        rt_bar = int(z["first_retest_after_away_bar"])
        if rt_bar < 0 or rt_bar + 1 >= len(bars):
            continue

        # Entrada Limit en el borde de la zona gris (z_upper si alcista, z_lower si bajista)
        entry_px = float(z["price_upper"]) if adir == 1 else float(z["price_lower"])
        z_span = max(float(z["price_upper"]) - float(z["price_lower"]), cfg.tick_size)
        stop_dist = max(z_span + cfg.buffer_stop_S3_ticks * cfg.tick_size, cfg.piso_riesgo_ticks * cfg.tick_size)

        # Evaluamos desde la propia barra de toque `rt_bar`
        sr = simular_trayectoria(hi, lo, cl, close_ts, rt_bar, entry_px, adir, stop_dist, cfg)
        if sr:
            sr["bucket"] = z["bucket"]
            sr["franja"] = franja_horaria_et(int(close_ts[rt_bar]))
            sr["in_cluster"] = int(z["in_any_cluster"])
            sr["fast_retest"] = 1 if (rt_bar - int(aw["resolved_bar"])) <= 30 else 0
            b2_limit_rebote.append(sr)

    df_b2_limit = pd.DataFrame(b2_limit_rebote)

    # 3. A_CLUSTER_POC_REVERSION: cuando el precio se aleja del POC del cluster P10 al borde y revierte,
    #    o primer re-testeo Limit en el borde del cluster P10 tras ruptura
    a_retest_limit = []
    a_fade_borde = []
    new_clusters = clusters[clusters["event_type"] == "NEW"].copy()
    for _, cz in new_clusters.iterrows():
        cbar = int(cz["confirmed_bar"])
        c_up = float(cz["price_upper"])
        c_lo = float(cz["price_lower"])
        c_span = max(c_up - c_lo, cfg.piso_riesgo_ticks * cfg.tick_size)
        stop_dist = max(c_span + cfg.buffer_stop_S3_ticks * cfg.tick_size, cfg.piso_riesgo_ticks * cfg.tick_size)

        # Buscar primera salida de la caja del cluster
        for b in range(cbar + 1, min(len(bars) - 1, cbar + 300)):
            if cl[b] > c_up + 1e-9 or cl[b] < c_lo - 1e-9:
                bdir = 1 if cl[b] > c_up + 1e-9 else -1
                # Fade de regreso al POC
                sf = simular_trayectoria(hi, lo, cl, close_ts, b + 1, float(op[b + 1]), -bdir, stop_dist, cfg)
                if sf:
                    sf["franja"] = franja_horaria_et(int(close_ts[b]))
                    a_fade_borde.append(sf)

                # Si se escapa >= 1x altura y vuelve al borde del cluster, operar rebote Limit en el borde
                escaped = False
                for b2 in range(b + 1, min(len(bars) - 1, b + 400)):
                    if bdir == 1 and hi[b2] >= c_up + c_span:
                        escaped = True
                    elif bdir == -1 and lo[b2] <= c_lo - c_span:
                        escaped = True
                    if escaped:
                        if (bdir == 1 and lo[b2] <= c_up + 1e-9) or (bdir == -1 and hi[b2] >= c_lo - 1e-9):
                            epx = c_up if bdir == 1 else c_lo
                            srt = simular_trayectoria(hi, lo, cl, close_ts, b2, epx, bdir, stop_dist, cfg)
                            if srt:
                                srt["franja"] = franja_horaria_et(int(close_ts[b2]))
                                a_retest_limit.append(srt)
                            break
                break

    df_a_fade = pd.DataFrame(a_fade_borde)
    df_a_retest = pd.DataFrame(a_retest_limit)

    def agrupar(df: pd.DataFrame, col: str) -> dict:
        if len(df) == 0 or col not in df:
            return {}
        return {str(k): resumir_df(sub, "r_t2") for k, sub in df.groupby(col)}

    return {
        "paridad_c_sharp_vs_python": paridad,
        "anatomia_15d_sep": {
            "rango_local": f"{run_row['first_bar_local']} -> {run_row['last_bar_local']}",
            "barras_50t": int(len(bars)),
            "zonas_hft": int(len(zones)),
            "zonas_por_bucket": zones["bucket"].value_counts().to_dict(),
            "clusters_p10_nuevos": int(len(new_clusters)),
            "clusters_p10_expansiones": int((clusters["event_type"] == "EXPAND").sum()),
            "umbral_p10_ticks_cuartiles": [
                float(np.percentile(zones.loc[zones["hist4_count"] >= 20, "p10_threshold_ticks"], q))
                for q in (25, 50, 75)
            ],
            "away_resoluciones": away["resolution"].value_counts().to_dict(),
        },
        "B1_entrada_open_vela_flecha": {
            "continuacion_T1": resumir_df(df_b1_cont, "r_t1"),
            "continuacion_T2": resumir_df(df_b1_cont, "r_t2"),
            "continuacion_T3": resumir_df(df_b1_cont, "r_t3"),
            "continuacion_por_bucket_T2": agrupar(df_b1_cont, "bucket"),
            "continuacion_por_franja_T2": agrupar(df_b1_cont, "franja"),
            "continuacion_en_cluster_vs_aislada_T2": agrupar(df_b1_cont, "in_cluster"),
            "fade_contra_flecha_T2": resumir_df(df_b1_fade, "r_t2"),
        },
        "B2_mitigacion_limit_borde_gris": {
            "rebote_global_T1": resumir_df(df_b2_limit, "r_t1"),
            "rebote_global_T2": resumir_df(df_b2_limit, "r_t2"),
            "rebote_global_T3": resumir_df(df_b2_limit, "r_t3"),
            "rebote_por_bucket_T2": agrupar(df_b2_limit, "bucket"),
            "rebote_por_franja_T2": agrupar(df_b2_limit, "franja"),
            "rebote_en_cluster_vs_aislada_T2": agrupar(df_b2_limit, "in_cluster"),
            "rebote_retest_rapido_vs_tardio_T2": agrupar(df_b2_limit, "fast_retest"),
        },
        "A_clusters_p10": {
            "fade_regreso_al_poc_T2": resumir_df(df_a_fade, "r_t2"),
            "fade_por_franja_T2": agrupar(df_a_fade, "franja"),
            "retest_borde_cluster_post_escape_T2": resumir_df(df_a_retest, "r_t2"),
            "retest_por_franja_T2": agrupar(df_a_retest, "franja"),
        },
    }


if __name__ == "__main__":
    print(json.dumps(ejecutar_estudio(), indent=2, ensure_ascii=False))
