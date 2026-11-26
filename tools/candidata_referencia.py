"""Referencia Python de una variante FundedSync tal como la corre `EdgeLabCandidataFS` en NT8 (para la paridad).

La variante se toma de la lista pre-registrada `fundedsync_prop_opt.specs_etapa1_iter4()` (campaña
FUNDEDSYNC_PROP_OPT_20261122, contada): parámetros del módulo de fábrica + ajuste causal en M1 (stop, BE, TP, trail)
con `fundedsync_prop_opt.aplicar_overlay_m1_causal`. Sobre esas operaciones aplica el veto de noticias
(`edgelab.veto_noticias`, ±2 min / FOMC ±5) y escribe las dos listas (sin y con veto).

  python tools/candidata_referencia.py --variante T_stop100_BE15R_calFalse --inst NQ \
      --desde 2008-01-02 --hasta 2025-09-30 --out <carpeta>

Sólo DESC/REP (corta antes del holdout). No elige nada: reproduce una variante ya definida.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import fundedsync_iter2_cartera as IT2  # noqa: E402
import fundedsync_post_il_cadena as BASE  # noqa: E402
import fundedsync_prop_opt as PO  # noqa: E402
from edgelab import costos, veto_noticias as VN  # noqa: E402
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque  # noqa: E402
from edgelab.research.fundedsyncstack import correr_modulo  # noqa: E402
from edgelab.research.fundedsyncstack.base_series import build_multi_series, load_m1_data  # noqa: E402
from edgelab.research.quantlab_mt5.contracts import SessionOpenMomentumConfig  # noqa: E402
from edgelab.research.quantlab_mt5.session_open_momentum import correr_session_open_momentum  # noqa: E402

M1_DIR = ROOT / "data" / "m1nt8"


def _generar_som(variante: str, inst: str, desde: str, hasta: str, out: Path) -> None:
    """Genera referencia Python de `SOMEOD_ext_NQ` (cierre diario) o `SOM_sin_finde` (cierre viernes)."""
    t0 = time.time()
    pq = M1_DIR / f"{inst}_M1_nonadj_utc.parquet"
    raw = pd.read_parquet(pq, filters=[("datetime", ">=", pd.Timestamp(desde)),
                                       ("datetime", "<", pd.Timestamp(hasta) + pd.Timedelta(days=1))]).reset_index()
    # Reloj del servidor QuantLab: hora NY + 7h rotulada UTC (igual que tools/kaggle_grilla/som_main.py)
    ny_srv = pd.to_datetime(raw["datetime"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None) + pd.Timedelta(hours=7)
    df_srv = pd.DataFrame({
        "time": ny_srv.dt.tz_localize("UTC"),
        "open": raw["open"].to_numpy(float),
        "high": raw["high"].to_numpy(float),
        "low": raw["low"].to_numpy(float),
        "close": raw["close"].to_numpy(float),
        "volume": raw["volume"].to_numpy(float) if "volume" in raw else np.ones(len(raw), dtype=float),
    })
    close_eod = variante == "SOMEOD_ext_NQ"
    cfg = replace(SessionOpenMomentumConfig(), close_eod=close_eod, close_weekend=True, use_adaptive_risk=False)
    tr = correr_session_open_momentum(df_srv, config=cfg, instrument=inst)

    def _srv_to_utc_ns(col: pd.Series) -> np.ndarray:
        ny_naive = pd.to_datetime(col.to_numpy(np.int64), unit="ns", utc=True).tz_convert(None) - pd.Timedelta(hours=7)
        utc_ts = ny_naive.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
        return utc_ts.asi8

    en_ns = _srv_to_utc_ns(tr["entry_time_utc"])
    ex_ns = _srv_to_utc_ns(tr["exit_time_utc"])
    en_ny = pd.to_datetime(en_ns, unit="ns", utc=True).tz_convert("America/New_York")
    fecha_int = en_ny.strftime("%Y%m%d").astype(int)
    mes = en_ny.strftime("%Y-%m")
    a5 = fecha_int.map(lambda f: a5_bloque(int(f)))

    riesgo_pts = (tr["entry_price"].astype(float) - tr["stop_price"].astype(float)).abs().to_numpy(float)
    pnl_pts = tr["pnl_pts"].astype(float).to_numpy(float)
    pv = costos.tick_value_usd(inst) / costos.tick_size(inst)
    mae_pts = tr["mae_usd"].astype(float).to_numpy(float) / (tr["qty"].astype(float).to_numpy(float) * pv)
    mfe_pts = tr["mfe_usd"].astype(float).to_numpy(float) / (tr["qty"].astype(float).to_numpy(float) * pv)

    fric_mini = costos.friccion_rt_ticks(inst) * costos.tick_size(inst)
    micro_root = f"M{inst}" if not inst.startswith("M") else inst
    try:
        fric_micro = costos.friccion_rt_ticks(micro_root) * costos.tick_size(micro_root)
    except KeyError:
        fric_micro = fric_mini

    o = pd.DataFrame({
        "fecha_int": fecha_int,
        "mes": mes,
        "a5": a5,
        "en_ns": en_ns,
        "ex_ns": ex_ns,
        "dur_min": (ex_ns - en_ns) / 60_000_000_000.0,
        "pnl_pts": pnl_pts,
        "mae_pts": mae_pts,
        "mfe_pts": mfe_pts,
        "riesgo_pts": riesgo_pts,
        "R_bruto": pnl_pts / np.maximum(riesgo_pts, 1e-9),
        "R_neto_mini": (pnl_pts - fric_mini) / np.maximum(riesgo_pts, 1e-9),
        "R_neto_micro": (pnl_pts - fric_micro) / np.maximum(riesgo_pts, 1e-9),
        "fric_R": fric_mini / np.maximum(riesgo_pts, 1e-9),
        "side": tr["side"].astype(int).to_numpy(),
    })
    o = o[(o["a5"].isin(["DESC", "REP"])) & (o["ex_ns"] < HOLDOUT_APERTURA_UTC_NS)].reset_index(drop=True)
    out.mkdir(parents=True, exist_ok=True)
    o.to_csv(out / f"PY_{variante}_{inst}.csv", index=False)
    (out / f"PY_{variante}_{inst}.json").write_text(json.dumps(dict(
        variante=variante, inst=inst, desde=desde, hasta=hasta, close_eod=close_eod, close_weekend=True,
        use_adaptive_risk=False, n=len(o)), indent=1), encoding="utf-8")
    print(f"[{time.time() - t0:.1f}s] {variante} ({inst}): {len(o)} ops DESC+REP guardadas en {out}")


def spec(variante: str) -> dict:
    for sp in PO.specs_etapa1_iter4():
        if sp["variante"] == variante:
            return sp
    raise SystemExit(f"variante no está en specs_etapa1_iter4: {variante}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", required=True)
    ap.add_argument("--inst", default="NQ")
    ap.add_argument("--desde", default="2019-01-02")   # mismo inicio que el Strategy Analyzer (2019 = calentamiento)
    ap.add_argument("--hasta", default="2026-09-30")   # último día antes del holdout (HOLDOUT-A4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.variante in ("SOMEOD_ext_NQ", "SOM_sin_finde"):
        _generar_som(a.variante, a.inst, a.desde, a.hasta, a.out)
        return 0
    sp = spec(a.variante)
    if sp.get("externa") or sp["overlay"].get("banda_miembros"):
        raise SystemExit("variante externa o de banda: no soportada acá")
    t0 = time.time()
    pq = M1_DIR / f"{a.inst}_M1_nonadj_utc.parquet"
    raw = pd.read_parquet(pq, filters=[("datetime", ">=", pd.Timestamp(a.desde)),   # misma fecha de inicio que la corrida de NT8
                                       ("datetime", "<", pd.Timestamp(a.hasta) + pd.Timedelta(days=1))]).reset_index()
    df_m1 = load_m1_data(raw, start=None, end=a.hasta, tz_input="UTC", allow_sellado=False)
    ms = build_multi_series(df_m1, tz_input="UTC", allow_sellado=False)
    ops = correr_modulo(sp["modulo"], ms, perfil="il_fabrica", **sp["params"])
    print(f"[{time.time() - t0:.0f}s] módulo {sp['modulo']} de fábrica: {len(ops)} operaciones")
    atr, _, pv, _ = BASE._cargar_series_sesion(a.inst, m1_dir=M1_DIR)
    orb = IT2._cargar_orb_raw(a.inst, m1_dir=M1_DIR)
    m1 = PO.cargar_m1_arrays_nq(m1_dir=M1_DIR, desde=a.desde)
    ov = sp["overlay"]
    o = PO.aplicar_overlay_m1_causal(ops, sp["modulo"], atr, orb, pv, m1,
                                     sl_atr_k=ov.get("sl_atr_k"), tp_atr_k=ov.get("tp_atr_k"), be_trigger_r=ov.get("be_trigger_r"),
                                     trail_tiers=ov.get("trail_tiers"), tp_r=ov.get("tp_r"),
                                     stop_orb_mult=ov.get("stop_orb_mult", 1.25), stop_min_pts=ov.get("stop_min_pts", 2.0),
                                     stop_max_pts=ov.get("stop_max_pts", 100.0))
    print(f"[{time.time() - t0:.0f}s] overlay {a.variante}: {len(o)} operaciones; columnas {list(o.columns)[:20]}")
    a.out.mkdir(parents=True, exist_ok=True)
    o.to_csv(a.out / f"PY_{a.variante}_{a.inst}.csv", index=False)
    (a.out / f"PY_{a.variante}_{a.inst}.json").write_text(json.dumps(dict(variante=a.variante, inst=a.inst, desde=a.desde, hasta=a.hasta,
                                                                          spec={k: str(v) for k, v in sp.items()}, n=len(o)), indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
