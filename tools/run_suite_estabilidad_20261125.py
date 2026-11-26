#!/usr/bin/env python3
"""Runner unificado de la Suite de Rentabilidad y Estabilidad (2026-11-25): EXP-1 a EXP-6C.

Reglas de protocolo:
  - Llama `registro_global.exigir_contada` para cada pre-registro (K51).
  - Evaluacion primaria estricta en bloque `DESC` (`a5_bloque == "DESC"`).
  - Replica congelada en `REP` solo para variantes nominadas / diagnostico de cartera (`K49`).
  - Jamas lee ni evalua datos `>= 2026-10-01` (`HOLDOUT-A4`) ni meses `HOLDOUT` de A5.
  - Usa friccion canonica de `edgelab/costos.py` y veto de noticias tier-1 de `edgelab/veto_noticias.py`.
"""
from __future__ import annotations

import gc
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import fundedsync_iter2_cartera as IT2  # noqa: E402
import fundedsync_post_il_cadena as BASE  # noqa: E402
import fundedsync_prop_opt as PO  # noqa: E402
import fundedsync_mecanismos as FM  # noqa: E402
import lucid_guia as LG  # noqa: E402
from edgelab import costos, noticias, veto_noticias as VN  # noqa: E402
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque  # noqa: E402
from edgelab.research import a5, estrategias_scrapeadas as SCR  # noqa: E402
from edgelab.research.fundedsyncstack import correr_modulo  # noqa: E402
from edgelab.research.fundedsyncstack.base_series import build_multi_series, load_m1_data  # noqa: E402
from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig  # noqa: E402
from edgelab.research.quantlab_mt5.session_open_momentum import correr_session_open_momentum  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

OUT_DIR = ROOT / "docs" / "research" / "estabilidad_rentabilidad_20261125"
M1_DIR = ROOT / "data" / "m1nt8"
DESDE = "2018-06-01"
HASTA = "2026-09-29"
EVAL_INI = 20200101

FRIC = {
    k: float(costos.friccion_rt_ticks(k) * costos.tick_size(k))
    for k in ("NQ", "MNQ", "ES", "MES", "YM", "MYM", "RTY")
}
PV = {
    k: float(costos.tick_value_usd(k) / costos.tick_size(k))
    for k in ("NQ", "MNQ", "ES", "MES")
}


def _verificar_preregistros() -> None:
    for fn in (
        "PREREGISTRO_EXP1_T_ESCALA.md",
        "PREREGISTRO_EXP2_SOM_NOTICIAS.md",
        "PREREGISTRO_EXP3_SIZING_VOLTARGET.md",
        "PREREGISTRO_EXP4_RQ5_SELECTIVIDAD.md",
        "PREREGISTRO_EXP5_ENSAMBLE_MULTIESTABLE.md",
        "PREREGISTRO_EXP6_EJECUCION_Y_SATELITES.md",
    ):
        exigir_contada(f"docs/research/estabilidad_rentabilidad_20261125/{fn}")


def _cargar_m1_raw(inst: str, desde: str = DESDE) -> tuple[pd.DataFrame, dict[str, np.ndarray], pd.Series]:
    pq = M1_DIR / f"{inst}_M1_nonadj_utc.parquet"
    raw = pd.read_parquet(
        pq,
        filters=[
            ("datetime", ">=", pd.Timestamp(desde)),
            ("datetime", "<", pd.Timestamp(HASTA) + pd.Timedelta(days=1)),
        ],
    ).reset_index()
    d_ny = PO.leer_m1nt8(pq)
    d_ny = d_ny[(d_ny.index >= desde) & (d_ny.index <= HASTA)]
    ts_utc = d_ny.index.tz_localize("America/New_York").tz_convert("UTC")
    ts_ns = PO._idx_utc_ns(ts_utc)
    ok = ts_ns < HOLDOUT_APERTURA_UTC_NS
    m1_arr = {
        "ts_ns": np.ascontiguousarray(ts_ns[ok], dtype=np.int64),
        "o": np.ascontiguousarray(d_ny["o"].to_numpy(float)[ok]),
        "h": np.ascontiguousarray(d_ny["h"].to_numpy(float)[ok]),
        "l": np.ascontiguousarray(d_ny["l"].to_numpy(float)[ok]),
        "c": np.ascontiguousarray(d_ny["c"].to_numpy(float)[ok]),
    }
    ap = pd.Series(m1_arr["o"], index=pd.DatetimeIndex(pd.to_datetime(m1_arr["ts_ns"], unit="ns", utc=True)))
    del d_ny, ts_utc
    gc.collect()
    return raw, m1_arr, ap


def _aplicar_veto_df(df: pd.DataFrame, ap: pd.Series, fric_mini: float, fric_micro: float) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    idx = ap.index.as_unit("ns").asi8
    k = np.clip(np.searchsorted(idx, df["en_ns"].to_numpy(np.int64), side="right") - 1, 0, len(idx) - 1)
    ent = ap.to_numpy(float)[k]
    side = df["side"].to_numpy(int)
    ops_in = pd.DataFrame({
        "entrada_ns": df["en_ns"].to_numpy(np.int64),
        "salida_ns": df["ex_ns"].to_numpy(np.int64),
        "lado": side,
        "precio_entrada": ent,
        "precio_salida": ent + side * df["pnl_pts"].to_numpy(float),
    })
    o = VN.aplicar_veto(ops_in, ap)
    out = df.copy()
    out["veto"] = o["veto"].to_numpy()
    out["ex_ns"] = o["salida_ns"].to_numpy(np.int64)
    out["pnl_pts"] = o["pts"].to_numpy(float)
    out = out[out["veto"] != "anulada"].copy().reset_index(drop=True)
    rg = np.maximum(out["riesgo_pts"].to_numpy(float), 1e-6)
    out["dur_min"] = np.maximum((out["ex_ns"] - out["en_ns"]) / 60_000_000_000.0, 0.0)
    out["R_bruto"] = out["pnl_pts"] / rg
    out["R_neto_mini"] = (out["pnl_pts"] - fric_mini) / rg
    out["R_neto_micro"] = (out["pnl_pts"] - fric_micro) / rg
    return out


def _boot_p_diff(s_cand: pd.Series, s_ctrl: pd.Series, B: int = 2000, seed: int = 17) -> tuple[float, float, float]:
    """Bootstrap pareado por sesion de (cand - ctrl): (diff_mean_ses, se_ses, p_one_sided)."""
    idx = s_cand.index.union(s_ctrl.index).sort_values()
    d = (s_cand.reindex(idx, fill_value=0.0) - s_ctrl.reindex(idx, fill_value=0.0)).to_numpy(float)
    n = len(d)
    if n < 10 or np.std(d) == 0:
        return 0.0, 0.0, 1.0
    rng = np.random.default_rng(seed)
    means = np.empty(B, dtype=float)
    for b in range(B):
        ix = rng.integers(0, n, size=n)
        means[b] = float(d[ix].mean())
    d0 = float(d.mean())
    se = float(means.std(ddof=1))
    p = float((1 + (means <= 0.0).sum()) / (B + 1))
    return d0, se, p


def _metrics_df(df: pd.DataFrame, bloque: str, min_fecha: int = EVAL_INI, ses_idx: np.ndarray | None = None) -> dict[str, Any]:
    sub = df[(df["a5"] == bloque) & (df["fecha_int"] >= min_fecha)].copy()
    if sub.empty:
        return {"n": 0, "R_mean": 0.0, "R_sum": 0.0, "MaxDD_R": 0.0, "Sharpe": 0.0, "Calmar": 0.0, "yrs_pos": "0/0"}
    r = sub["R_neto_mini"].to_numpy(float)
    daily = sub.groupby("fecha_int")["R_neto_mini"].sum()
    if ses_idx is not None:
        daily = daily.reindex(ses_idx, fill_value=0.0)
    cum = daily.cumsum().to_numpy()
    pk = np.maximum.accumulate(np.r_[0.0, cum])[1:]
    mdd = float((cum - pk).min())
    n_yrs = max(1.0, len(np.unique(sub["fecha_int"].to_numpy() // 10000)))
    sh = float((daily.mean() / daily.std(ddof=1)) * math.sqrt(len(daily) / n_yrs)) if len(daily) > 1 and daily.std(ddof=1) > 0 else 0.0
    ann_r = float(r.sum()) / n_yrs
    cal = float(ann_r / abs(mdd)) if mdd < -1e-9 else 0.0
    yr_g = sub.groupby(sub["fecha_int"] // 10000)["R_neto_mini"].sum()
    mo_g = sub.groupby(sub["fecha_int"] // 100)["R_neto_mini"].sum()
    return {
        "n": int(len(sub)),
        "R_mean": round(float(r.mean()), 4),
        "R_sum": round(float(r.sum()), 2),
        "R_mes": round(float(r.sum()) / max(1.0, len(mo_g)), 2),
        "MaxDD_R": round(mdd, 2),
        "Sharpe": round(sh, 2),
        "Calmar": round(cal, 2),
        "yrs_pos": f"{int((yr_g > 0).sum())}/{len(yr_g)}",
        "pct_mes_pos": round(float((mo_g > 0).mean() * 100.0), 1),
        "by_year": {int(k): round(float(v), 2) for k, v in yr_g.items()},
    }


def _bh_q(pvals: list[float]) -> list[float]:
    m = len(pvals)
    if m == 0:
        return []
    order = np.argsort(pvals)
    q = np.empty(m, dtype=float)
    prev = 1.0
    for rank_rev in range(m - 1, -1, -1):
        idx = order[rank_rev]
        val = min(prev, pvals[idx] * m / float(rank_rev + 1))
        q[idx] = val
        prev = val
    return [round(float(x), 4) for x in q]


# ---------------------------------------------------------------------------
# EXP-1: T con tope de stop invariante de escala
# ---------------------------------------------------------------------------
def run_exp1(raw_nq, m1_nq, ap_nq, raw_es, m1_es, ap_es) -> tuple[dict[str, Any], pd.DataFrame]:
    t0 = time.time()
    out: dict[str, Any] = {"experimento": "EXP1_T_ESCALA", "NQ": {}, "ES": {}}
    best_t_df = None

    for inst, raw, m1_arr, ap in (("NQ", raw_nq, m1_nq, ap_nq), ("ES", raw_es, m1_es, ap_es)):
        df_m1 = load_m1_data(raw, start=None, end=HASTA, tz_input="UTC", allow_sellado=False)
        ms = build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
        del df_m1
        ops = correr_modulo("T", ms, perfil="il_fabrica", use_exclusion_calendars=False)
        atr, _, _, _ = BASE._cargar_series_sesion(inst, m1_dir=M1_DIR, desde=DESDE)
        orb = IT2._cargar_orb_raw(inst, m1_dir=M1_DIR)
        ny_raw = pd.DatetimeIndex(pd.to_datetime(raw["datetime"], utc=True)).tz_convert("America/New_York").tz_localize(None)
        c_prev = pd.Series(raw["close"].to_numpy(float), index=ny_raw).groupby(ny_raw.normalize()).last()

        en_ns, en_dt = PO._col_a_ns_y_dt(ops["entry_time_utc"])
        ex_ns, _ = PO._col_a_ns_y_dt(ops["exit_time_utc"])
        ses_d = en_dt.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        c_prev_aligned = c_prev.shift(1).reindex(ses_d).to_numpy(float)
        atr_aligned = atr.reindex(ses_d).to_numpy(float)
        orb_aligned = orb.reindex(ses_d).to_numpy(float)
        be_trig = 1.5 if inst == "NQ" else 0.0
        f_cap_fijo = 100.0 if inst == "NQ" else 29.0
        fric_mini = FRIC[inst]
        fric_micro = FRIC[f"M{inst}"]

        variantes = {
            "T_FIJO_100": np.minimum(np.maximum(2.0 if inst == "NQ" else 0.6, orb_aligned), f_cap_fijo),
            "T_PCT_060": np.minimum(np.maximum(0.0002 * c_prev_aligned, orb_aligned), 0.0060 * c_prev_aligned),
            "T_PCT_080": np.minimum(np.maximum(0.0002 * c_prev_aligned, orb_aligned), 0.0080 * c_prev_aligned),
            "T_PCT_100": np.minimum(np.maximum(0.0002 * c_prev_aligned, orb_aligned), 0.0100 * c_prev_aligned),
            "T_ATR_050": np.minimum(np.maximum(2.0, orb_aligned), 0.50 * atr_aligned),
            "T_ATR_075": np.minimum(np.maximum(2.0, orb_aligned), 0.75 * atr_aligned),
            "T_SIN_CAP": np.maximum(2.0 if inst == "NQ" else 0.6, orb_aligned),
        }

        dfs_v: dict[str, pd.DataFrame] = {}
        ok_a4 = en_ns < HOLDOUT_APERTURA_UTC_NS
        side_arr = ops["side"].to_numpy(int)
        en_p_arr = ops["entry_price"].to_numpy(float)
        ex_p_arr = ops["exit_price"].to_numpy(float)
        fecha_int_arr = ses_d.dt.strftime("%Y%m%d").astype(np.int64).to_numpy()
        mes_arr = ses_d.dt.strftime("%Y-%m").to_numpy()
        a5_arr = np.array([a5_bloque(int(f)) for f in fecha_int_arr], dtype=object)

        for vname, sl_vec in variantes.items():
            valid = ok_a4 & np.isfinite(sl_vec) & (sl_vec > 0)
            sl_pass = np.where(valid, sl_vec, 1e9)
            tp_zeros = np.zeros(len(ops), dtype=np.float64)
            is_mkt = np.zeros(len(ops), dtype=np.bool_)
            pnl_new, mae_new, mfe_new, ex_new = PO._evaluar_overlay_m1_numba(
                m1_arr["ts_ns"], m1_arr["o"], m1_arr["h"], m1_arr["l"], m1_arr["c"],
                en_ns, ex_ns, side_arr, en_p_arr, ex_p_arr, sl_pass, tp_zeros, is_mkt,
                be_trig, -1.0, 0.0, -1.0, 0.0,
            )
            df_v = pd.DataFrame({
                "fecha_int": fecha_int_arr[valid],
                "mes": mes_arr[valid],
                "a5": a5_arr[valid],
                "en_ns": en_ns[valid],
                "ex_ns": np.maximum(ex_new[valid], en_ns[valid]),
                "pnl_pts": pnl_new[valid],
                "riesgo_pts": sl_vec[valid],
                "side": side_arr[valid],
                "capped": (sl_vec[valid] < orb_aligned[valid] - 0.1) if vname != "T_SIN_CAP" else False,
            })
            df_v = _aplicar_veto_df(df_v, ap, fric_mini, fric_micro)
            dfs_v[vname] = df_v

        ctrl_ser_d = dfs_v["T_FIJO_100"][(dfs_v["T_FIJO_100"]["a5"] == "DESC") & (dfs_v["T_FIJO_100"]["fecha_int"] >= EVAL_INI)].groupby("fecha_int")["R_neto_mini"].sum()
        pvals = []
        vlist = list(variantes.keys())
        rows_inst = {}
        for vname in vlist:
            df_v = dfs_v[vname]
            md = _metrics_df(df_v, "DESC")
            mr = _metrics_df(df_v, "REP")
            s_d = df_v[(df_v["a5"] == "DESC") & (df_v["fecha_int"] >= EVAL_INI)].groupby("fecha_int")["R_neto_mini"].sum()
            d0, se, pv = _boot_p_diff(s_d, ctrl_ser_d) if vname != "T_FIJO_100" else (0.0, 0.0, 1.0)
            pvals.append(pv)
            sub_25_26 = df_v[(df_v["a5"] == "DESC") & (df_v["fecha_int"] >= 20250101)]
            cap_25_26 = round(float(sub_25_26["capped"].mean() * 100.0), 1) if len(sub_25_26) else 0.0
            rows_inst[vname] = {
                "DESC": md,
                "REP": mr,
                "cap_pct_2025_26": cap_25_26,
                "diff_vs_ctrl_ses_R": round(d0, 4),
                "p_vs_ctrl": round(pv, 4),
            }
        qs = _bh_q(pvals)
        for vname, qv in zip(vlist, qs):
            rows_inst[vname]["q_bh"] = qv
        out[inst] = rows_inst
        if inst == "NQ":
            # Selecciona ganadora en DESC (mayor Sharpe si q_bh < 0.10 o mejor balance si empate)
            best_v = max(vlist, key=lambda k: (1 if rows_inst[k]["q_bh"] < 0.10 else 0, rows_inst[k]["DESC"]["Calmar"], rows_inst[k]["DESC"]["R_sum"]))
            out["NQ_ganadora_DESC"] = best_v
            best_t_df = dfs_v[best_v]
            out["NQ_ctrl_df"] = dfs_v["T_FIJO_100"]
    print(f"[{time.time() - t0:.1f}s] EXP-1 completado (NQ ganadora DESC: {out['NQ_ganadora_DESC']})")
    return out, best_t_df


# ---------------------------------------------------------------------------
# EXP-2: SOM_sin_finde + noticias 10:00 + adaptive risk + ATR stop
# ---------------------------------------------------------------------------
def _som_trades_variant(df_srv: pd.DataFrame, ap_nq: pd.Series, news_days_1000: set[int], *, mode: str, use_adapt: bool, sl_mult: float) -> pd.DataFrame:
    # Reloj servidor QuantLab: NY + 7h -> 09:30 NY = 16:30, 10:05 NY = 17:05
    open_ny = "17:05" if mode == "post_1005" else "16:30"
    cfg = replace(
        SessionOpenMomentumConfig(),
        open_ny=open_ny,
        close_eod=False,
        close_weekend=True,
        use_adaptive_risk=use_adapt,
        sl_atr_mult=sl_mult,
    )

    def _permitir(ts_srv_ns: int, side: int) -> bool:
        if mode != "skip_1000" and mode != "post_1005":
            return True
        ny_naive = pd.Timestamp(ts_srv_ns, unit="ns", tz="UTC").tz_localize(None) - pd.Timedelta(hours=7)
        f_int = int(ny_naive.strftime("%Y%m%d"))
        if mode == "skip_1000":
            return f_int not in news_days_1000
        return True

    if mode == "post_1005":
        # En dias sin noticia 10:00 entra a 09:35 (16:30 srv); en dias CON noticia 10:00 entra a 10:10 (17:05 srv)
        cfg_base = replace(cfg, open_ny="16:30")
        tr1 = correr_session_open_momentum(df_srv, config=cfg_base, instrument="NQ", permitir=lambda ts, s: int((pd.Timestamp(ts, unit="ns", tz="UTC").tz_localize(None) - pd.Timedelta(hours=7)).strftime("%Y%m%d")) not in news_days_1000)
        tr2 = correr_session_open_momentum(df_srv, config=cfg, instrument="NQ", permitir=lambda ts, s: int((pd.Timestamp(ts, unit="ns", tz="UTC").tz_localize(None) - pd.Timedelta(hours=7)).strftime("%Y%m%d")) in news_days_1000)
        # Keep non-overlapping cleanly (tr1 skips news days)
        tr = pd.concat([tr1, tr2], ignore_index=True)
    else:
        tr = correr_session_open_momentum(df_srv, config=cfg, instrument="NQ", permitir=_permitir)

    def _srv_to_utc(col: pd.Series) -> np.ndarray:
        ny_naive = pd.to_datetime(col.to_numpy(np.int64), unit="ns", utc=True).tz_convert(None) - pd.Timedelta(hours=7)
        return ny_naive.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC").asi8

    en_ns = _srv_to_utc(tr["entry_time_utc"])
    ex_ns = _srv_to_utc(tr["exit_time_utc"])
    en_ny = pd.to_datetime(en_ns, unit="ns", utc=True).tz_convert("America/New_York")
    f_int = en_ny.strftime("%Y%m%d").astype(np.int64)
    mes = en_ny.strftime("%Y-%m")
    a5_arr = f_int.map(lambda f: a5_bloque(int(f)))
    rg = (tr["entry_price"].astype(float) - tr["stop_price"].astype(float)).abs().to_numpy(float)
    qty_arr = tr["qty"].astype(float).to_numpy(float)
    df = pd.DataFrame({
        "fecha_int": f_int.to_numpy(),
        "mes": mes.to_numpy(),
        "a5": a5_arr.to_numpy(),
        "en_ns": en_ns,
        "ex_ns": ex_ns,
        "pnl_pts": tr["pnl_pts"].astype(float).to_numpy(float),
        "riesgo_pts": np.maximum(rg, 1e-6),
        "side": tr["side"].astype(int).to_numpy(),
        "adapt_qty": qty_arr,
    })
    df = df[(df["a5"].isin(["DESC", "REP"])) & (df["ex_ns"] < HOLDOUT_APERTURA_UTC_NS)].reset_index(drop=True)
    df = _aplicar_veto_df(df, ap_nq, FRIC["NQ"], FRIC["MNQ"])
    # Con use_adaptive_risk, el peso de riesgo aplicado refleja qty relativa respecto a mediana de adapt_qty
    if use_adapt and len(df):
        med_q = max(float(np.median(df["adapt_qty"])), 1e-6)
        fac = np.clip(df["adapt_qty"].to_numpy(float) / med_q, 0.4, 2.0)
        df["R_neto_mini"] = df["R_neto_mini"] * fac
        df["R_neto_micro"] = df["R_neto_micro"] * fac
    return df


def run_exp2(raw_nq, ap_nq) -> tuple[dict[str, Any], pd.DataFrame]:
    t0 = time.time()
    ny_srv = pd.to_datetime(raw_nq["datetime"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None) + pd.Timedelta(hours=7)
    df_srv = pd.DataFrame({
        "time": ny_srv.dt.tz_localize("UTC"),
        "open": raw_nq["open"].to_numpy(float),
        "high": raw_nq["high"].to_numpy(float),
        "low": raw_nq["low"].to_numpy(float),
        "close": raw_nq["close"].to_numpy(float),
        "volume": raw_nq["volume"].to_numpy(float) if "volume" in raw_nq else np.ones(len(raw_nq), float),
    })

    cal = noticias.cargar()
    cal_t1 = cal[cal["impacto"] == "tier1"]
    ev_ny = pd.to_datetime(cal_t1["ts_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    mins = ev_ny.dt.hour * 60 + ev_ny.dt.minute
    news_days_1000 = set(int(x) for x in ev_ny[(mins >= 570) & (mins <= 615)].dt.strftime("%Y%m%d").astype(int))

    specs = [
        ("SOM_BASE_VETO", dict(mode="base", use_adapt=False, sl_mult=8.0)),
        ("SOM_SKIP_1000", dict(mode="skip_1000", use_adapt=False, sl_mult=8.0)),
        ("SOM_POST_1005", dict(mode="post_1005", use_adapt=False, sl_mult=8.0)),
        ("SOM_ADAPT_RISK", dict(mode="base", use_adapt=True, sl_mult=8.0)),
        ("SOM_SKIP_ADAPT", dict(mode="skip_1000", use_adapt=True, sl_mult=8.0)),
        ("SOM_ATR6_SKIP", dict(mode="skip_1000", use_adapt=False, sl_mult=6.0)),
        ("SOM_ATR10_SKIP", dict(mode="skip_1000", use_adapt=False, sl_mult=10.0)),
    ]
    dfs = {nom: _som_trades_variant(df_srv, ap_nq, news_days_1000, **kw) for nom, kw in specs}
    ctrl_ser = dfs["SOM_BASE_VETO"][(dfs["SOM_BASE_VETO"]["a5"] == "DESC") & (dfs["SOM_BASE_VETO"]["fecha_int"] >= EVAL_INI)].groupby("fecha_int")["R_neto_mini"].sum()
    pvals = []
    res = {}
    for nom, _ in specs:
        d = dfs[nom]
        md = _metrics_df(d, "DESC")
        mr = _metrics_df(d, "REP")
        s_d = d[(d["a5"] == "DESC") & (d["fecha_int"] >= EVAL_INI)].groupby("fecha_int")["R_neto_mini"].sum()
        d0, se, pv = _boot_p_diff(s_d, ctrl_ser) if nom != "SOM_BASE_VETO" else (0.0, 0.0, 1.0)
        pvals.append(pv)
        res[nom] = {
            "DESC": md,
            "REP": mr,
            "cerradas_news_veto": int((d["veto"] == "cerrada_por_noticia").sum()),
            "diff_vs_ctrl_ses_R": round(d0, 4),
            "p_vs_ctrl": round(pv, 4),
        }
    for (nom, _), qv in zip(specs, _bh_q(pvals)):
        res[nom]["q_bh"] = qv
    best_v = max(res.keys(), key=lambda k: (1 if res[k]["q_bh"] < 0.10 else 0, res[k]["DESC"]["Calmar"], res[k]["DESC"]["R_sum"]))
    res["ganadora_DESC"] = best_v
    print(f"[{time.time() - t0:.1f}s] EXP-2 completado (ganadora DESC: {best_v})")
    return res, dfs[best_v], dfs["SOM_BASE_VETO"]


# ---------------------------------------------------------------------------
# EXP-4: RQ5 selectivo (m, corte, skip 10:00 news)
# ---------------------------------------------------------------------------
def run_exp4() -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    t0 = time.time()
    rq = pd.read_csv(ROOT / "docs" / "research" / "rq5_regimen_20261119" / "OPS_DESC_REP.csv.gz")
    rcol = "r_P_obj_s0.45_tp2_stop_s0.45_tp2_fin"
    kcol = "k_P_obj_s0.45_tp2_stop_s0.45_tp2_fin"
    cal = noticias.cargar()
    cal_t1 = cal[cal["impacto"] == "tier1"]
    ev_ny = pd.to_datetime(cal_t1["ts_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    mins_ev = ev_ny.dt.hour * 60 + ev_ny.dt.minute
    news_1000 = set(int(x) for x in ev_ny[(mins_ev >= 590) & (mins_ev <= 610)].dt.strftime("%Y%m%d").astype(int))

    # Detectar minuto de entrada NY de rq['t']
    en_ny = pd.to_datetime(rq["t"], unit="s", utc=True).dt.tz_convert("America/New_York")
    rq["min_ny"] = en_ny.dt.hour * 60 + en_ny.dt.minute

    variants = {
        "RQ5_FAB": ("L60_m1_c689", False),
        "RQ5_M12_C1130": ("L60_m1.2_c689", False),
        "RQ5_M10_C1100": ("L60_m1_c659", False),
        "RQ5_M12_C1100": ("L60_m1.2_c659", False),
        "RQ5_SKIP_1000_NEWS": ("L60_m1_c689", True),
    }

    out = {}
    ctrl_ser = None
    pvals = []
    dfs_comb = {}
    best_inst_dfs: dict[str, pd.DataFrame] = {}

    for vname, (col, skip_10) in variants.items():
        partes = []
        for inst in ("NQ", "ES"):
            sub = rq[(rq["inst"] == inst) & (rq[col].astype(bool)) & (rq["ses"].astype(int) >= EVAL_INI)].copy()
            if skip_10:
                sub = sub[~((sub["ses"].astype(int).isin(news_1000)) & (sub["min_ny"] >= 595) & (sub["min_ny"] <= 605))]
            rg = sub[kcol].to_numpy(float)
            bruto_pts = sub[rcol].to_numpy(float) * rg
            t_s = sub["t"].to_numpy(np.int64) * 1_000_000_000
            df_i = pd.DataFrame({
                "fecha_int": sub["ses"].astype(np.int64).to_numpy(),
                "mes": (sub["ses"].astype(int) // 100).astype(str).str.slice(0, 4) + "-" + (sub["ses"].astype(int) % 10000 // 100).astype(str).str.zfill(2),
                "a5": sub["bloque"].to_numpy(),
                "en_ns": t_s,
                "ex_ns": t_s + 120 * 60_000_000_000,
                "dur_min": 120.0,
                "pnl_pts": bruto_pts,
                "riesgo_pts": rg,
                "R_bruto": sub[rcol].to_numpy(float),
                "R_neto_mini": sub[rcol].to_numpy(float) - FRIC[inst] / rg,
                "R_neto_micro": sub[rcol].to_numpy(float) - FRIC[f"M{inst}"] / rg,
                "side": sub["lado"].astype(int).to_numpy(),
                "inst": inst,
            })
            partes.append(df_i)
        comb = pd.concat(partes, ignore_index=True)
        dfs_comb[vname] = comb
        md = _metrics_df(comb, "DESC")
        mr = _metrics_df(comb, "REP")
        s_d = comb[comb["a5"] == "DESC"].groupby("fecha_int")["R_neto_mini"].sum()
        if vname == "RQ5_FAB":
            ctrl_ser = s_d
            d0, pv = 0.0, 1.0
        else:
            d0, _, pv = _boot_p_diff(s_d, ctrl_ser)
        pvals.append(pv)
        out[vname] = {"DESC": md, "REP": mr, "diff_vs_ctrl_ses_R": round(d0, 4), "p_vs_ctrl": round(pv, 4)}

    for vname, qv in zip(variants.keys(), _bh_q(pvals)):
        out[vname]["q_bh"] = qv
    best_v = max(variants.keys(), key=lambda k: (1 if out[k]["q_bh"] < 0.10 else 0, out[k]["DESC"]["Calmar"], out[k]["DESC"]["R_mean"]))
    out["ganadora_DESC"] = best_v
    best_comb = dfs_comb[best_v]
    for inst in ("NQ", "ES"):
        best_inst_dfs[inst] = best_comb[best_comb["inst"] == inst].drop(columns=["inst"]).reset_index(drop=True)
    print(f"[{time.time() - t0:.1f}s] EXP-4 completado (ganadora DESC: {best_v})")
    return out, best_inst_dfs


# ---------------------------------------------------------------------------
# Helpers ES5N (ES) y Franklin (NQ) + LucidFlex
# ---------------------------------------------------------------------------
def _generar_es5n_es(raw_es: pd.DataFrame, ap_es: pd.Series) -> pd.DataFrame:
    from collections import deque
    from edgelab.research.externas_estructurales_a5 import _rsi_wilder_step

    ny_idx = pd.DatetimeIndex(pd.to_datetime(raw_es["datetime"], utc=True)).tz_convert("America/New_York").tz_localize(None)
    o = raw_es["open"].to_numpy(float); h = raw_es["high"].to_numpy(float)
    l = raw_es["low"].to_numpy(float); c = raw_es["close"].to_numpy(float)
    ts_ns = PO._idx_utc_ns(pd.DatetimeIndex(pd.to_datetime(raw_es["datetime"], utc=True)))
    mo = ny_idx.hour.to_numpy() * 60 + ny_idx.minute.to_numpy()
    ses = ny_idx.strftime("%Y%m%d").astype(int).to_numpy()

    atr20 = deque(maxlen=20)
    prev_c = None; avg_g = None; avg_l = None; rsi10 = 50.0
    filas = []
    for s in np.unique(ses):
        ix = np.flatnonzero((ses == s) & (mo >= 570) & (mo < 960))
        if not len(ix):
            continue
        ab = float(o[ix[0]]); hi_r = float(h[ix].max()); lo_r = float(l[ix].min()); cl_r = float(c[ix[-1]])
        atr_val = float(np.mean(atr20)) if len(atr20) >= 4 else np.nan
        if np.isfinite(atr_val) and atr_val > 0 and prev_c is not None:
            k1000 = ix[mo[ix] == 599]
            if len(k1000) and (40.0 <= rsi10 <= 60.0):
                k = int(k1000[0])
                ret30 = float(c[k]) - ab
                if abs(ret30) >= 0.12 * atr_val and k < int(ix[-1]):
                    side = 1 if ret30 > 0 else -1
                    sl_d = 0.45 * atr_val
                    st = float(c[k]) - side * sl_d
                    ult = int(ix[-1])
                    ent_p = float(o[k + 1])
                    # Intrabar stop / EOD
                    seg = (l[k + 1:ult + 1] <= st) if side == 1 else (h[k + 1:ult + 1] >= st)
                    if seg.any():
                        j = k + 1 + int(np.argmax(seg))
                        ex_p = min(float(o[j]), st) if side == 1 else max(float(o[j]), st)
                        ex_t = int(ts_ns[j])
                    else:
                        ex_p = float(c[ult])
                        ex_t = int(ts_ns[ult])
                    bl = a5_bloque(int(s))
                    if bl in ("DESC", "REP") and ex_t < HOLDOUT_APERTURA_UTC_NS:
                        filas.append({
                            "fecha_int": int(s), "mes": f"{str(s)[:4]}-{str(s)[4:6]}", "a5": bl,
                            "en_ns": int(ts_ns[k + 1]), "ex_ns": ex_t,
                            "pnl_pts": side * (ex_p - ent_p), "riesgo_pts": sl_d, "side": side,
                        })
        tr = max(hi_r - lo_r, abs(hi_r - prev_c), abs(lo_r - prev_c)) if prev_c is not None else (hi_r - lo_r)
        atr20.append(tr)
        avg_g, avg_l, rsi10 = _rsi_wilder_step(prev_c, cl_r, avg_g, avg_l, 10)
        prev_c = cl_r
    df = pd.DataFrame(filas)
    return _aplicar_veto_df(df, ap_es, FRIC["ES"], FRIC["MES"])


def _generar_franklin_nq(raw_nq: pd.DataFrame, ap_nq: pd.Series) -> pd.DataFrame:
    ny_idx = pd.DatetimeIndex(pd.to_datetime(raw_nq["datetime"], utc=True)).tz_convert("America/New_York").tz_localize(None)
    d_m1 = pd.DataFrame({
        "o": raw_nq["open"].to_numpy(float),
        "h": raw_nq["high"].to_numpy(float),
        "l": raw_nq["low"].to_numpy(float),
        "c": raw_nq["close"].to_numpy(float),
        "v": raw_nq["volume"].to_numpy(float) if "volume" in raw_nq else np.ones(len(raw_nq), float),
    }, index=ny_idx)
    V = FM.contexto(d_m1)
    noche_alto = set(int(x.strftime("%Y%m%d")) for x in V[V["noche"] == "alto"].index)
    ctx = SCR.ctx_de_m1(d_m1)
    fr = SCR.franklin_variantes(ctx, celdas=[("1000", "rango", "ninguno")])
    fr = fr[~fr["fecha"].isin(noche_alto)].copy()
    fr["a5"] = [a5_bloque(int(f)) for f in fr["fecha"].astype(int)]
    fr = fr[fr["a5"].isin(["DESC", "REP"]) & (fr["riesgo"] > 0)].copy().reset_index(drop=True)
    fstr = fr["fecha"].astype(int).astype(str)
    en_ny = pd.DatetimeIndex(pd.to_datetime(fstr + " 10:00:00", format="%Y%m%d %H:%M:%S"))
    en_ns = PO._idx_utc_ns(en_ny.tz_localize("America/New_York").tz_convert("UTC"))
    mot = pd.to_numeric(fr["motivo"], errors="coerce").fillna(1).to_numpy(int)
    dur = np.where(mot == 3, 355.0, 60.0)
    ex_ns = en_ns + (dur * 60_000_000_000.0).astype(np.int64)
    ok = ex_ns < HOLDOUT_APERTURA_UTC_NS
    df = pd.DataFrame({
        "fecha_int": fr["fecha"].astype(np.int64).to_numpy()[ok],
        "mes": (fstr.str[:4] + "-" + fstr.str[4:6]).to_numpy()[ok],
        "a5": fr["a5"].to_numpy()[ok],
        "en_ns": en_ns[ok],
        "ex_ns": ex_ns[ok],
        "pnl_pts": fr["bruto"].to_numpy(float)[ok],
        "riesgo_pts": fr["riesgo"].to_numpy(float)[ok],
        "side": fr["lado"].astype(np.int64).to_numpy()[ok],
    })
    return _aplicar_veto_df(df, ap_nq, FRIC["NQ"], FRIC["MNQ"])


def _cargar_c2_vz_esnq() -> dict[str, pd.DataFrame]:
    c2 = pd.read_csv(ROOT / "docs" / "research" / "carril2_20261119" / "OPS_LOTE2.csv.gz")
    out = {}
    for inst in ("NQ", "ES"):
        sub = c2[(c2["definicion"] == "C2_VZ") & (c2["inst"] == inst) & (c2["fecha"].astype(int) >= EVAL_INI)].copy()
        f_int = sub["fecha"].astype(np.int64).to_numpy()
        en_ny = pd.DatetimeIndex(pd.to_datetime(sub["fecha"].astype(int).astype(str) + " 18:00:00", format="%Y%m%d %H:%M:%S"))
        en_ns = PO._idx_utc_ns(en_ny.tz_localize("America/New_York").tz_convert("UTC"))
        dur_m = np.maximum(sub["barras"].astype(float).to_numpy() * 1380.0, 60.0)
        ex_ns = np.minimum(en_ns + (dur_m * 60_000_000_000.0).astype(np.int64), HOLDOUT_APERTURA_UTC_NS - 1)
        rg = (sub["entrada"].astype(float) - sub["stop0"].astype(float)).abs().to_numpy()
        fr_m = FRIC[f"M{inst}"]
        rb = sub["Rb"].astype(float).to_numpy()
        out[f"C2_VZ::{inst}"] = pd.DataFrame({
            "fecha_int": f_int,
            "mes": pd.Series(sub["fecha"].astype(int).astype(str)).str[:4].to_numpy() + "-" + pd.Series(sub["fecha"].astype(int).astype(str)).str[4:6].to_numpy(),
            "a5": sub["bloque"].to_numpy(),
            "en_ns": en_ns,
            "ex_ns": ex_ns,
            "dur_min": dur_m,
            "pnl_pts": rb * rg,
            "riesgo_pts": rg,
            "R_bruto": rb,
            "R_neto_mini": sub["R"].astype(float).to_numpy(),
            "R_neto_micro": rb - fr_m / np.maximum(rg, 1e-6),
            "side": sub["lado"].astype(int).to_numpy(),
        })
    return out


def _sim_lucid_series(daily_usd: np.ndarray) -> dict[str, Any]:
    out = {}
    for tam in ("25K", "50K"):
        cfg = LG.TAMANOS[tam]
        pr = LG.precio(tam, True, 0.50)
        scale = 1.0 if tam == "50K" else 0.75
        for mn, mult in (("real_100", 1.0), ("contr_60", 0.60)):
            y0 = daily_usd * scale
            ysc = y0 - np.mean(y0) + mult * np.mean(y0)
            acc = LG.por_cuenta(ysc, cfg, 0.50, N=3000)
            car = LG.cartera(ysc, cfg, 0.50, pr, max_eval=5, por_dia=1, N=1000, H=504)
            out[f"{tam}|{mn}"] = {
                "usd_dia": round(float(np.mean(ysc)), 2),
                "worst_day": round(float(np.min(ysc)), 1),
                "ev_examen": round(float(acc["cobrado_medio"] - pr), 1),
                "pasa_pct": round(float(acc["pasa"] * 100.0), 1),
                "cartera_neto": round(float(car["neto_medio"]), 1),
                "usd_mes": round(float(car["usd_por_mes_hasta_fin"]), 1),
            }
    return out


# ---------------------------------------------------------------------------
# EXP-5 y EXP-3: Ensamble MultiEstable y VolTarget Sizing
# ---------------------------------------------------------------------------
def run_exp5_and_exp3(streams: dict[str, pd.DataFrame], ses_desc: pd.Index, ses_rep: pd.Index) -> tuple[dict, dict]:
    t0 = time.time()
    composiciones = {
        "P0_CORE3": ["T::NQ", "R::NQ", "Z::NQ"],
        "P1_CORE_SOM": ["T::NQ", "R::NQ", "Z::NQ", "SOM::NQ"],
        "P2_CORE_SOM_RQ5": ["T::NQ", "R::NQ", "Z::NQ", "SOM::NQ", "RQ5::NQ", "RQ5::ES"],
        "P3_MULTIESTABLE": ["T::NQ", "R::NQ", "Z::NQ", "SOM::NQ", "RQ5::NQ", "RQ5::ES", "C2_VZ::NQ", "C2_VZ::ES"],
        "P4_MULTI_ES5N": ["T::NQ", "R::NQ", "Z::NQ", "SOM::NQ", "RQ5::NQ", "RQ5::ES", "C2_VZ::NQ", "C2_VZ::ES", "ES5N::ES"],
        "P5_MULTI_FRANKLIN": ["T::NQ", "R::NQ", "Z::NQ", "SOM::NQ", "RQ5::NQ", "RQ5::ES", "C2_VZ::NQ", "C2_VZ::ES", "ES5N::ES", "Franklin::NQ"],
    }

    m_desc = BASE._meses_activos_a5(EVAL_INI, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(EVAL_INI, 20260930, "REP")
    res5: dict[str, Any] = {"pruebas": {}}
    p0_ser_desc = None
    pvals5 = []
    keys5 = []
    tr_best = None

    for cnom, slist in composiciones.items():
        s_d = {k: streams[k][(streams[k]["a5"] == "DESC") & (streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        s_r = {k: streams[k][(streams[k]["a5"] == "REP") & (streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        D_d = pd.DataFrame({k: v.groupby("fecha_int")["R_neto_mini"].sum() for k, v in s_d.items()}, index=ses_desc).fillna(0.0)
        M_d = pd.DataFrame({k: v.groupby("mes")["R_neto_mini"].sum() for k, v in s_d.items()}).fillna(0.0)
        dur = {k: (float(v["dur_min"].median()) if len(v) else 60.0) for k, v in s_d.items()}
        p_dict = IT2.calcular_pesos_esquemas(D_d, M_d, dur)
        # Pesos W0_cap3R: nucleo=1.0, satelites=0.5 (C2_VZ 0.25 por lado = 0.5 total)
        w_nom = {}
        for k in slist:
            if k in ("T::NQ", "R::NQ", "Z::NQ", "SOM::NQ"):
                w_nom[k] = 1.0
            elif k.startswith("C2_VZ::"):
                w_nom[k] = 0.25
            else:
                w_nom[k] = 0.5

        for esq_nom, w_map in (("W0_cap3R", w_nom), ("W5_ERC_cap3R", p_dict["W5_freq_dur_conc"])):
            tr_d, mx_d = IT2.aplicar_tope_concurrencia_causal(s_d, w_map, None, cap_r=3.0)
            tr_r, mx_r = IT2.aplicar_tope_concurrencia_causal(s_r, w_map, None, cap_r=3.0)
            sd_ser = tr_d.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0)
            sr_ser = tr_r.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0)
            ev_d = IT2.evaluar_serie_cartera(sd_ser, m_desc, mc_reps=2000, seed=99)
            ev_r = IT2.evaluar_serie_cartera(sr_ser, m_rep, mc_reps=2000, seed=99)
            key = f"{cnom}|{esq_nom}"
            if key == "P0_CORE3|W0_cap3R":
                p0_ser_desc = sd_ser
                d0, pv = 0.0, 1.0
            else:
                d0, _, pv = _boot_p_diff(sd_ser, p0_ser_desc)
            pvals5.append(pv)
            keys5.append(key)
            luc = _sim_lucid_series(sd_ser.to_numpy(float) * 200.0)
            luc_r = _sim_lucid_series(sr_ser.to_numpy(float) * 200.0)
            res5["pruebas"][key] = {
                "DESC": ev_d, "REP": ev_r, "max_open_R_desc": mx_d,
                "diff_vs_P0_ses_R": round(d0, 4), "p_vs_P0": round(pv, 4),
                "lucid_DESC": luc, "lucid_REP": luc_r,
            }
            if cnom == "P3_MULTIESTABLE" and esq_nom == "W0_cap3R":
                tr_best = (tr_d, tr_r, sd_ser, sr_ser)

    for key, qv in zip(keys5, _bh_q(pvals5)):
        res5["pruebas"][key]["q_bh"] = qv
    res5["ganadora_DESC"] = max(keys5, key=lambda k: (1 if res5["pruebas"][k]["q_bh"] < 0.10 else 0, res5["pruebas"][k]["DESC"]["sharpe_anual"], res5["pruebas"][k]["DESC"]["R_mes"]))

    # EXP-3: Sizing & VolTarget sobre P3_MULTIESTABLE|W0_cap3R (y comparativo P0_CORE3)
    res3: dict[str, Any] = {"carteras": {}}
    for label, slist in (("P0_CORE3", composiciones["P0_CORE3"]), ("P3_MULTIESTABLE", composiciones["P3_MULTIESTABLE"])):
        s_d = {k: streams[k][(streams[k]["a5"] == "DESC") & (streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        s_r = {k: streams[k][(streams[k]["a5"] == "REP") & (streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        w_nom = {k: (1.0 if k in ("T::NQ", "R::NQ", "Z::NQ", "SOM::NQ") else (0.25 if k.startswith("C2_VZ::") else 0.5)) for k in slist}
        tr_d, _ = IT2.aplicar_tope_concurrencia_causal(s_d, w_nom, None, cap_r=3.0)
        tr_r, _ = IT2.aplicar_tope_concurrencia_causal(s_r, w_nom, None, cap_r=3.0)

        # Serie base diaria en R
        sd_r = tr_d.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0)
        sr_r = tr_r.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0)
        vol_obj = float(sd_r.iloc[:50].std(ddof=1)) if len(sd_r) >= 50 else float(sd_r.std(ddof=1))
        vol_obj = max(vol_obj, 0.20)

        def _apply_policy(df_tr: pd.DataFrame, s_idx: pd.Index, pol: str) -> np.ndarray:
            daily_r = df_tr.groupby("fecha_int")["R_eff"].sum().reindex(s_idx, fill_value=0.0).to_numpy(float)
            n = len(daily_r)
            out_usd = np.zeros(n, dtype=float)
            if pol == "S0_FIJO_MICRO":
                # Escala contratos constantes = $200 / (med_riesgo_pts * PV_micro)
                tr_c = df_tr.copy()
                # aproximacion directa causal en contratos fijos: factor = 200 / riesgo_medio_inicial vs riesgo_pts
                med_sl = float(tr_d["riesgo_pts"].iloc[:max(20, len(tr_d) // 5)].median())
                fac = med_sl / np.maximum(tr_c["riesgo_pts"].to_numpy(float), 1.0)
                tr_c["usd"] = tr_c["R_eff"].to_numpy(float) * np.clip(fac, 0.25, 3.0) * 200.0
                return tr_c.groupby("fecha_int")["usd"].sum().reindex(s_idx, fill_value=0.0).to_numpy(float)

            # Causales al cierre d-1
            dd = 0.0; peak = 0.0; eq = 0.0; dd_half = False
            for i in range(n):
                f_vol = 1.0
                if i >= 20 and pol in ("S2_VOLTARGET_20D", "S4_VOLTARGET_DD"):
                    v20 = float(np.std(daily_r[i - 20:i], ddof=1))
                    if v20 > 1e-6:
                        f_vol = float(np.clip(vol_obj / v20, 0.50, 1.50))
                f_dd = 1.0
                if pol in ("S3_DD_STEP", "S4_VOLTARGET_DD"):
                    if dd <= -8.0:
                        dd_half = True
                    elif dd >= -3.0:
                        dd_half = False
                    if dd_half:
                        f_dd = 0.50
                f = f_vol if pol == "S2_VOLTARGET_20D" else (f_dd if pol == "S3_DD_STEP" else (min(f_vol, f_dd) if pol == "S4_VOLTARGET_DD" else 1.0))
                ret_usd = daily_r[i] * f * 200.0
                out_usd[i] = ret_usd
                eq += daily_r[i] * f
                peak = max(peak, eq)
                dd = eq - peak
            return out_usd

        c_out = {}
        for pol in ("S0_FIJO_MICRO", "S1_R_CONST", "S2_VOLTARGET_20D", "S3_DD_STEP", "S4_VOLTARGET_DD"):
            ud = _apply_policy(tr_d, ses_desc, pol)
            ur = _apply_policy(tr_r, ses_rep, pol)
            sd_u = pd.Series(ud / 200.0, index=ses_desc)
            sr_u = pd.Series(ur / 200.0, index=ses_rep)
            c_out[pol] = {
                "DESC": IT2.evaluar_serie_cartera(sd_u, m_desc, mc_reps=2000, seed=77),
                "REP": IT2.evaluar_serie_cartera(sr_u, m_rep, mc_reps=2000, seed=77),
                "lucid_DESC": _sim_lucid_series(ud),
                "lucid_REP": _sim_lucid_series(ur),
            }
        res3["carteras"][label] = c_out
    print(f"[{time.time() - t0:.1f}s] EXP-5 y EXP-3 completados")
    return res5, res3


# ---------------------------------------------------------------------------
# EXP-6C: Satelite puro ES / MES
# ---------------------------------------------------------------------------
def run_exp6c(streams: dict[str, pd.DataFrame], raw_es: pd.DataFrame, ap_es: pd.Series, ses_desc: pd.Index, ses_rep: pd.Index) -> dict[str, Any]:
    t0 = time.time()
    # Agregar R_ES y T_ES con preset ES_Core_US500
    df_m1 = load_m1_data(raw_es, start=None, end=HASTA, tz_input="UTC", allow_sellado=False)
    ms_es = build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
    del df_m1
    atr_es, _, _, _ = BASE._cargar_series_sesion("ES", m1_dir=M1_DIR, desde=DESDE)
    orb_es = IT2._cargar_orb_raw("ES", m1_dir=M1_DIR)

    def _to_es_df(ops_df: pd.DataFrame, stop_vec: np.ndarray, be_tr: float = -1.0) -> pd.DataFrame:
        en_ns, en_dt = PO._col_a_ns_y_dt(ops_df["entry_time_utc"])
        ex_ns, _ = PO._col_a_ns_y_dt(ops_df["exit_time_utc"])
        ny_d = en_dt.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
        ok = en_ns < HOLDOUT_APERTURA_UTC_NS
        f_int = ny_d.dt.strftime("%Y%m%d").astype(np.int64).to_numpy()
        df = pd.DataFrame({
            "fecha_int": f_int[ok],
            "mes": ny_d.dt.strftime("%Y-%m").to_numpy()[ok],
            "a5": np.array([a5_bloque(int(f)) for f in f_int[ok]], dtype=object),
            "en_ns": en_ns[ok],
            "ex_ns": ex_ns[ok],
            "pnl_pts": (ops_df["exit_price"].to_numpy(float) - ops_df["entry_price"].to_numpy(float))[ok] * ops_df["side"].to_numpy(int)[ok],
            "riesgo_pts": np.maximum(stop_vec[ok], 0.5),
            "side": ops_df["side"].to_numpy(int)[ok],
        })
        return _aplicar_veto_df(df, ap_es, FRIC["ES"], FRIC["MES"])

    ops_t_es = correr_modulo("T", ms_es, perfil="il_fabrica", use_exclusion_calendars=False)
    _, en_t = PO._col_a_ns_y_dt(ops_t_es["entry_time_utc"])
    ny_t = en_t.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    t_es_df = _to_es_df(ops_t_es, np.maximum(0.6, orb_es.reindex(ny_t).to_numpy(float)))
    ops_r_es = correr_modulo("R", ms_es, perfil="il_fabrica", osc_atr_mult=2.0, entry_end_min_et=660)
    _, en_r = PO._col_a_ns_y_dt(ops_r_es["entry_time_utc"])
    ny_r = en_r.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    r_es_df = _to_es_df(ops_r_es, 0.50 * atr_es.reindex(ny_r).to_numpy(float))

    es_streams = {
        "RQ5::ES": streams["RQ5::ES"],
        "C2_VZ::ES": streams["C2_VZ::ES"],
        "ES5N::ES": streams["ES5N::ES"],
        "T_ES_NOCAP::ES": t_es_df,
        "R_ES::ES": r_es_df,
    }
    nq_core_d = sum(streams[k][(streams[k]["a5"] == "DESC") & (streams[k]["fecha_int"] >= EVAL_INI)].groupby("fecha_int")["R_neto_mini"].sum().reindex(ses_desc, fill_value=0.0) for k in ("T::NQ", "R::NQ", "Z::NQ", "SOM::NQ"))

    m_desc = BASE._meses_activos_a5(EVAL_INI, 20260930, "DESC")
    m_rep = BASE._meses_activos_a5(EVAL_INI, 20260930, "REP")
    sats = {
        "ES_SAT_1": ["RQ5::ES", "C2_VZ::ES"],
        "ES_SAT_2": ["RQ5::ES", "C2_VZ::ES", "ES5N::ES"],
        "ES_SAT_3": ["RQ5::ES", "C2_VZ::ES", "ES5N::ES", "T_ES_NOCAP::ES", "R_ES::ES"],
    }
    out = {"EXP6A_costos": "PENDIENTE_DATOS_L1", "EXP6B_limites_ticks": "PENDIENTE_DATOS_L1", "EXP6C": {}}
    for nom, slist in sats.items():
        s_d = {k: es_streams[k][(es_streams[k]["a5"] == "DESC") & (es_streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        s_r = {k: es_streams[k][(es_streams[k]["a5"] == "REP") & (es_streams[k]["fecha_int"] >= EVAL_INI)].copy() for k in slist}
        w_map = {k: 1.0 for k in slist}
        tr_d, _ = IT2.aplicar_tope_concurrencia_causal(s_d, w_map, None, cap_r=3.0)
        tr_r, _ = IT2.aplicar_tope_concurrencia_causal(s_r, w_map, None, cap_r=3.0)
        sd = tr_d.groupby("fecha_int")["R_eff"].sum().reindex(ses_desc, fill_value=0.0)
        sr = tr_r.groupby("fecha_int")["R_eff"].sum().reindex(ses_rep, fill_value=0.0)
        corr_nq = float(sd.corr(nq_core_d)) if sd.std() > 0 and nq_core_d.std() > 0 else 0.0
        out["EXP6C"][nom] = {
            "DESC": IT2.evaluar_serie_cartera(sd, m_desc, mc_reps=2000, seed=55),
            "REP": IT2.evaluar_serie_cartera(sr, m_rep, mc_reps=2000, seed=55),
            "corr_vs_NQ_CORE_DESC": round(corr_nq, 3),
        }
    print(f"[{time.time() - t0:.1f}s] EXP-6C completado")
    return out


def main() -> int:
    _verificar_preregistros()
    t_all = time.time()

    raw_nq, m1_nq, ap_nq = _cargar_m1_raw("NQ")
    raw_es, m1_es, ap_es = _cargar_m1_raw("ES")
    fechas_nq = IT2._cargar_fechas_a5_inst("NQ", m1_dir=M1_DIR)
    ses_desc = pd.Index([f for f in fechas_nq["DESC"] if f >= EVAL_INI])
    ses_rep = pd.Index([f for f in fechas_nq["REP"] if f >= EVAL_INI])

    res1, t_best_df = run_exp1(raw_nq, m1_nq, ap_nq, raw_es, m1_es, ap_es)
    res1_save = {k: v for k, v in res1.items() if k != "NQ_ctrl_df"}
    (OUT_DIR / "EXP1_RESULTADO.json").write_text(json.dumps(res1_save, indent=1, default=str), encoding="utf-8")

    res2, som_best_df, _ = run_exp2(raw_nq, ap_nq)
    (OUT_DIR / "EXP2_RESULTADO.json").write_text(json.dumps(res2, indent=1, default=str), encoding="utf-8")

    res4, rq5_dfs = run_exp4()
    (OUT_DIR / "EXP4_RESULTADO.json").write_text(json.dumps(res4, indent=1, default=str), encoding="utf-8")

    # Cargar R y Z con veto de candidatas_nt8_20261125
    def _load_py_ref_with_veto(glob_pat: str) -> pd.DataFrame:
        p = sorted((ROOT / "docs" / "research" / "candidatas_nt8_20261125").glob(glob_pat))[0]
        df = pd.read_csv(p)
        return _aplicar_veto_df(df, ap_nq, FRIC["NQ"], FRIC["MNQ"])

    c2_dfs = _cargar_c2_vz_esnq()
    es5n_es_df = _generar_es5n_es(raw_es, ap_es)
    frk_nq_df = _generar_franklin_nq(raw_nq, ap_nq)

    streams = {
        "T::NQ": t_best_df,
        "R::NQ": _load_py_ref_with_veto("R/PY_*.csv"),
        "Z::NQ": _load_py_ref_with_veto("Z/PY_*.csv"),
        "SOM::NQ": som_best_df,
        "RQ5::NQ": rq5_dfs["NQ"],
        "RQ5::ES": rq5_dfs["ES"],
        "C2_VZ::NQ": c2_dfs["C2_VZ::NQ"],
        "C2_VZ::ES": c2_dfs["C2_VZ::ES"],
        "ES5N::ES": es5n_es_df,
        "Franklin::NQ": frk_nq_df,
    }

    res5, res3 = run_exp5_and_exp3(streams, ses_desc, ses_rep)
    (OUT_DIR / "EXP5_RESULTADO.json").write_text(json.dumps(res5, indent=1, default=str), encoding="utf-8")
    (OUT_DIR / "EXP3_RESULTADO.json").write_text(json.dumps(res3, indent=1, default=str), encoding="utf-8")

    res6 = run_exp6c(streams, raw_es, ap_es, ses_desc, ses_rep)
    (OUT_DIR / "EXP6C_RESULTADO.json").write_text(json.dumps(res6, indent=1, default=str), encoding="utf-8")

    print(f"SUITE COMPLETA EN {time.time() - t_all:.1f}s -> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
