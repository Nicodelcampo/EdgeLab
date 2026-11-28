#!/usr/bin/env python3
"""CRIPTO-XSMOM-SPOT-PRE: CR3_XSMOM_21d_Stag5d y CR3_XSMOM_BetaNeut_Stag5d en Binance Spot (2017-08 → 2019-08).

Pre-registro: docs/research/cripto_xsmom_spot_2017_2019_20261127/PREREGISTRO.md (K32/K51/K60).
Cero parámetros nuevos; universo mensual PiT top-25 por quote_volume del mes previo (excl. stablecoins).
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import sys
import zipfile
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from cripto_pit_v2 import _get, _normalize_active_neutral, _pnl, _safe_close_returns, _stagger_weights, build_eligibility, stats_serie  # noqa: E402
from cripto_pit_v3 import _beta_scale_legs  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/cripto_xsmom_spot_2017_2019_20261127/PREREGISTRO.md"
DATA = ROOT / "data/crypto_binance_spot_2017_2019"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs/research/cripto_xsmom_spot_2017_2019_20261127"
OUT.mkdir(parents=True, exist_ok=True)

VIS = "https://data.binance.vision"
MESES = pd.period_range("2017-08", "2019-08", freq="M").strftime("%Y-%m").tolist()
CORTE_SPOT = pd.Timestamp("2019-09-01")
STABLES = {"TUSDUSDT", "PAXUSDT", "USDCUSDT", "USDSUSDT", "BUSDUSDT", "SUSDUSDT", "USDSBUSDT"}
CANDIDATOS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "BCCUSDT", "NEOUSDT", "LTCUSDT", "QTUMUSDT", "ADAUSDT", "XRPUSDT", "EOSUSDT",
    "IOTAUSDT", "XLMUSDT", "ONTUSDT", "TRXUSDT", "ETCUSDT", "ICXUSDT", "VENUSDT", "NULSUSDT", "VETUSDT", "BCHABCUSDT",
    "BCHSVUSDT", "LINKUSDT", "WAVESUSDT", "BTTUSDT", "ONGUSDT", "HOTUSDT", "ZILUSDT", "ZRXUSDT", "FETUSDT", "BATUSDT",
    "XMRUSDT", "ZECUSDT", "IOSTUSDT", "CELRUSDT", "DASHUSDT", "NANOUSDT", "OMGUSDT", "THETAUSDT", "ENJUSDT", "MITHUSDT",
    "MATICUSDT", "ATOMUSDT", "TFUELUSDT", "ONEUSDT", "FTMUSDT", "ALGOUSDT", "DOGEUSDT", "GTOUSDT", "MFTUSDT", "DOCKUSDT",
    "WANUSDT", "FUNUSDT", "CVCUSDT", "KEYUSDT", "DENTUSDT", "ANKRUSDT", "WINUSDT", "COSUSDT", "COCOSUSDT", "PERLUSDT",
    "ERDUSDT", "TOMOUSDT", "PHBUSDT", "NPXSUSDT", "STORMUSDT",
]


def _dl_spot(args: tuple[str, str]) -> tuple[str, pd.DataFrame | None]:
    sym, ym = args
    b = _get(f"{VIS}/data/spot/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip", timeout=10)
    if b is None:
        return sym, None
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(raw.iloc[0, 0]).isdigit():
            raw = raw.iloc[1:]
        raw = raw.iloc[:, [0, 1, 2, 3, 4, 7]].astype(float)
        raw.columns = ["t", "open", "high", "low", "close", "quote_volume"]
        return sym, raw
    except Exception:
        return sym, None


def load_spot_universe() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    pq_ready = {s: pd.read_parquet(DATA / f"{s}_1d.parquet") for s in CANDIDATOS if s not in STABLES and (DATA / f"{s}_1d.parquet").exists()}
    missing = [(s, ym) for s in CANDIDATOS if s not in STABLES and s not in pq_ready for ym in MESES]
    if missing:
        print(f"Descargando spot 2017-08..2019-08 ({len(missing)} pares-mes en 24 hilos)...", flush=True)
        acc: dict[str, list[pd.DataFrame]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
            for sym, part in ex.map(_dl_spot, missing):
                if part is not None and len(part):
                    acc.setdefault(sym, []).append(part)
        for s in CANDIDATOS:
            if s in STABLES or s in pq_ready:
                continue
            parts = acc.get(s, [])
            pq = DATA / f"{s}_1d.parquet"
            if not parts:
                pd.DataFrame().to_parquet(pq)
                continue
            df = pd.concat(parts, ignore_index=True).drop_duplicates("t").sort_values("t")
            df["dt"] = pd.to_datetime(df["t"].astype("int64"), unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
            df = df[df["dt"] < CORTE_SPOT].drop_duplicates("dt").set_index("dt")[["open", "high", "low", "close", "quote_volume"]]
            df.to_parquet(pq)
            if len(df):
                pq_ready[s] = df
    bars = {s: df for s, df in pq_ready.items() if len(df) > 0}
    # Build causal monthly PiT universe: shift(1) ranking of previous-month quote_volume
    qv = pd.DataFrame({s: df["quote_volume"] for s, df in bars.items()}).sort_index()
    mq = qv.groupby(qv.index.to_period("M")).sum()
    rows = []
    meses_list = list(mq.index)
    for idx_m in range(1, len(meses_list)):
        prev_m = mq.loc[meses_list[idx_m - 1]].dropna()
        prev_m = prev_m[prev_m > 0].sort_values(ascending=False)
        for rk, (sym, val) in enumerate(prev_m.head(25).items(), 1):
            rows.append({"mes": str(meses_list[idx_m]), "simbolo": sym, "rango": rk, "prev_quote_vol_usd": round(float(val), 1)})
    u = pd.DataFrame(rows)
    u.to_csv(OUT / "UNIVERSO_SPOT_PIT.csv", index=False)
    return bars, u


def _run_xsmom(C, H, L, r_safe, u, min_live: int, min_n: int, idx_eval: pd.DatetimeIndex, btc: pd.Series) -> dict:
    tr = np.maximum(H - L, np.maximum((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    vol1 = (tr.rolling(20, min_periods=10).mean() / C).clip(lower=0.01)
    inv_vol = (0.01 / vol1).clip(upper=0.25)
    vol60 = r_safe.rolling(min_live, min_periods=min(30, min_live)).std() * np.sqrt(365.0)
    live = (C.notna().rolling(min_live, min_periods=min_live).sum() >= min_live) & (vol60 >= 0.25)
    E_hyst = build_eligibility(C.index, C.columns, u, top_k=20, hysteresis_exit=25) & live

    btc_var = btc.rolling(30, min_periods=15).var().replace(0.0, np.nan)
    beta_btc = pd.DataFrame(1.0, index=C.index, columns=C.columns)
    for s in C.columns:
        cov_b = r_safe[s].rolling(30, min_periods=15).cov(btc)
        beta_btc[s] = (cov_b / btc_var).shift(1).fillna(1.0)

    sc21 = (C.pct_change(21, fill_method=None) / vol1).where(E_hyst)
    rk21 = sc21.rank(axis=1, ascending=False, method="first")
    n21 = sc21.notna().sum(axis=1).to_numpy()[:, None]
    p_raw = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p_raw[(rk21 <= 4) & (n21 >= min_n)] = 1.0
    p_raw[(rk21 >= n21 - 3) & (n21 >= min_n)] = -1.0

    w_eq = _stagger_weights(_normalize_active_neutral(p_raw, inv_vol, max_w=0.20), E_hyst, 5)
    w_bn = _stagger_weights(_beta_scale_legs(p_raw, inv_vol, beta_btc, max_w=0.20), E_hyst, 5)
    F0 = pd.DataFrame(0.0, index=C.index, columns=C.columns)

    out = {"series_20bps": pd.DataFrame(index=idx_eval), "rules": {}}
    for name, W in [("CR3_XSMOM_21d_Stag5d", w_eq), ("CR3_XSMOM_BetaNeut_Stag5d", w_bn)]:
        r_d = {"por_costo": {}}
        for bps in (10, 20, 30, 40):
            s_raw, _, turn_m, dh = _pnl(C, W, F0, bps / 10_000.0, r_override=r_safe)
            s = s_raw.reindex(idx_eval).fillna(0.0)
            st_all = stats_serie(s)
            st_2017 = stats_serie(s[s.index.year == 2017])
            st_1819 = stats_serie(s[s.index.year >= 2018])
            if bps == 20:
                out["series_20bps"][name] = s
                r_d["turnover_x_mes"] = turn_m
                r_d["corr_BTC"] = round(float(s.corr(btc.reindex(idx_eval).fillna(0.0))), 3) if s.std() > 0 else 0.0
                r_d["meses"] = {str(k): round(float(v), 1) for k, v in s.groupby(s.index.to_period("M")).sum().items()}
                # Long vs short leg attribution (gross & 20bps)
                Wl = W.clip(lower=0.0)
                Ws = W.clip(upper=0.0)
                sl, _, _, _ = _pnl(C, Wl, F0, bps / 10_000.0, r_override=r_safe)
                ss, _, _, _ = _pnl(C, Ws, F0, bps / 10_000.0, r_override=r_safe)
                r_d["long_leg_20bps"] = stats_serie(sl.reindex(idx_eval).fillna(0.0))
                r_d["short_leg_20bps"] = stats_serie(ss.reindex(idx_eval).fillna(0.0))
            r_d["por_costo"][str(bps)] = {"todo": st_all, "solo_2017": st_2017, "ex_2017_2018_2019": st_1819}
        out["rules"][name] = r_d
    return out


def main() -> int:
    exigir_contada(PRE)
    bars, u = load_spot_universe()
    C = pd.DataFrame({s: df["close"] for s, df in bars.items()}).sort_index()
    H = pd.DataFrame({s: df["high"] for s, df in bars.items()}).reindex(C.index)
    L = pd.DataFrame({s: df["low"] for s, df in bars.items()}).reindex(C.index)
    C = C[C.index < CORTE_SPOT]
    H, L = H.reindex(C.index), L.reindex(C.index)
    r_safe = _safe_close_returns(C, max_gap=5)
    btc = r_safe["BTCUSDT"].fillna(0.0)

    idx_eval = C.index[(C.index >= "2017-10-01") & (C.index < "2019-09-01")]
    prim = _run_xsmom(C, H, L, r_safe, u, min_live=60, min_n=10, idx_eval=idx_eval, btc=btc)
    sens = _run_xsmom(C, H, L, r_safe, u, min_live=30, min_n=6, idx_eval=idx_eval, btc=btc)

    prim["series_20bps"].to_csv(OUT / "SERIES_SPOT_2017_2019.csv.gz")

    r_eq = prim["rules"]["CR3_XSMOM_21d_Stag5d"]["por_costo"]["20"]
    r_bn = prim["rules"]["CR3_XSMOM_BetaNeut_Stag5d"]["por_costo"]["20"]
    res = {
        "n_pares_cargados": len(bars),
        "ventana_primaria": f"{idx_eval[0].date()} -> {idx_eval[-1].date()}",
        "primaria_live60_n10": prim["rules"],
        "sensibilidad_live30_n6": sens["rules"],
        "veredicto_primario": {
            "XSMOM_todo": r_eq["todo"],
            "XSMOM_ex2017": r_eq["ex_2017_2018_2019"],
            "BetaNeut_todo": r_bn["todo"],
            "BetaNeut_ex2017": r_bn["ex_2017_2018_2019"],
        },
    }
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    md = [
        "# CRIPTO-XSMOM-SPOT-PRE: `CR3_XSMOM` Congelado en Binance Spot (`2017-10 → 2019-08`)",
        "",
        f"Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`2` pruebas, `CRIPTO_XSMOM_SPOT_PRE`). `{len(bars)}` pares Spot USDT PiT cargados (`20 pb RT`, `0` funding). Muestra primaria K60 sin recortes post hoc: `{idx_eval[0].date()} → {idx_eval[-1].date()}`.",
        "",
        "| Regla (`20 pb`, `live60, n>=10`) | `Todo (23m) Sh (t)` | `Solo 2017 (3m)` | `2018–2019 (20m) Sh (t)` | `p (1-cola)` | `Long leg Sh` | `Short leg Sh` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for nm in ("CR3_XSMOM_21d_Stag5d", "CR3_XSMOM_BetaNeut_Stag5d"):
        rr = prim["rules"][nm]
        c20 = rr["por_costo"]["20"]
        md.append(
            f"| `{nm}` | **`{c20['todo']['sharpe']} ({c20['todo']['t_mes']})`** | `{c20['solo_2017']['sharpe']} ({c20['solo_2017']['t_mes']})` | "
            f"**`{c20['ex_2017_2018_2019']['sharpe']} ({c20['ex_2017_2018_2019']['t_mes']})`** | `{c20['todo']['p_una_cola']}` | "
            f"`{rr['long_leg_20bps']['sharpe']}` | `{rr['short_leg_20bps']['sharpe']}` |"
        )
    s_eq = sens["rules"]["CR3_XSMOM_21d_Stag5d"]["por_costo"]["20"]
    s_bn = sens["rules"]["CR3_XSMOM_BetaNeut_Stag5d"]["por_costo"]["20"]
    md.extend([
        "",
        f"- **Sensibilidad (`live30, n>=6`):** `CR3_XSMOM_21d_Stag5d` `todo={s_eq['todo']['sharpe']} (t={s_eq['todo']['t_mes']})`, `2018-19={s_eq['ex_2017_2018_2019']['sharpe']}`; `BetaNeut` `todo={s_bn['todo']['sharpe']} (t={s_bn['todo']['t_mes']})`.",
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (`2` reglas congeladas de `cripto_pit_v3.py`, sin optimizar perillas).",
        "Episodios: detallado `2017` vs `2018–2019` (ex-burbuja) en la tabla superior y mes a mes en `RESULTADO.json`.",
        "",
        "Aporte al referente: prueba las reglas XSMOM congeladas de `cripto_pit_v3` sobre casi `2` años vírgenes de Spot (`2017–2019`) sin tocar el holdout 2021–2026.",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(res["veredicto_primario"], indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
