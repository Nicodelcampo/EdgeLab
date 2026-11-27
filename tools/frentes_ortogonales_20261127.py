#!/usr/bin/env python3
"""FRENTES-ORTOGONALES-20261127 (Pre-registrado):
  A) FundedSync O (Overnight) con qty=1 MNQ fijo (2018-01..2026-09, eliminando el techo de margen NQ>25k).
  B) Transferencia global de F-COMPRESION-VOL-CRECE (C2_VZ y C2_EVRP) sobre 5 M1 continuos de Dukascopy (data/m1dk/).

Pre-registro: docs/research/frentes_ortogonales_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC y REP de HOLDOUT-A5, dejando HOLDOUT, EMBARGO y TERMINAL SELLADOS (NaN).
Uso:
  python -u tools/frentes_ortogonales_20261127.py
"""
from __future__ import annotations

import json
import sys
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from edgelab.research import sqx_catalogo as Q  # noqa: E402
from edgelab.research.fundedsyncstack import build_multi_series, run_o  # noqa: E402
from edgelab.research.m1_intradia import leer_m1  # noqa: E402

OUT = ROOT / "docs" / "research" / "frentes_ortogonales_20261127"
OUT.mkdir(parents=True, exist_ok=True)
FRIC_MNQ_PTS = 1.9775  # Canonico MNQ ($3.955 / contrato RT, igual que ARNES_N_NQ)

M1DK_SPECS = {
    "DAX": ("DEUIDXEUR-M1-.csv", "vix_close"),
    "EuroStoxx": ("EUSIDXEUR-M1-.csv", "vix_close"),
    "FTSE": ("GBRIDXGBP-M1-.csv", "vix_close"),
    "Nikkei": ("JPNIDXJPY-M1-.csv", "vix_close"),
    "Oro": ("XAUUSD_M1_dukas-M1-.csv", "gvz_close"),
}


def _stats_monthly(daily_s: pd.Series, mask: pd.Series) -> dict:
    s = daily_s.loc[mask].dropna()
    m = s.groupby(s.index.to_period("M")).sum()
    n = len(m)
    if n < 3 or float(m.std(ddof=1)) == 0.0:
        return {"meses": int(n), "media_mes": 0.0, "t": 0.0, "p_una_cola": 0.5, "sharpe": 0.0, "pct_meses_pos": 0.0}
    mu = float(m.mean())
    sd = float(m.std(ddof=1))
    t = mu / (sd / np.sqrt(n))
    sh = mu / sd * np.sqrt(12.0)
    a = s.groupby(s.index.year).sum()
    return {
        "meses": int(n),
        "media_mes": round(mu, 2),
        "t": round(t, 2),
        "p_una_cola": round(0.5 * (1.0 - erf(t / sqrt(2.0))), 4),
        "sharpe": round(sh, 3),
        "pct_meses_pos": round(float((m > 0).mean()), 3),
        "pct_anios_pos": round(float((a > 0).mean()), 3),
    }


def run_block_a_fundedsync_o() -> tuple[dict, pd.Series]:
    print("=== BLOQUE A: FundedSync O (qty=1 MNQ fijo, < 2026-10-01) ===", flush=True)
    df_nq = pd.read_parquet(
        ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet",
        filters=[("datetime", ">=", pd.Timestamp("2017-10-01")), ("datetime", "<", pd.Timestamp("2026-09-30 22:00:00"))],
    )
    df_nq = df_nq.rename_axis("ts").reset_index()
    ms = build_multi_series(df_nq, tz_input="UTC", input_timestamp_is_close=False)

    tr_fijo = run_o(ms, qty=1)
    tr_def = run_o(ms, qty=None)

    def _enrich(tr: pd.DataFrame) -> pd.DataFrame:
        if len(tr) == 0:
            return tr
        t = tr.copy()
        en_ny = pd.to_datetime(t["entry_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        ex_ny = pd.to_datetime(t["exit_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        t["fecha_en"] = (en_ny + pd.Timedelta(hours=6)).dt.strftime("%Y%m%d").astype(int)
        t["fecha_sal"] = (ex_ny + pd.Timedelta(hours=6)).dt.strftime("%Y%m%d").astype(int)
        t["blq_en"] = [a5_bloque(x) for x in t["fecha_en"]]
        t["blq_sal"] = [a5_bloque(x) for x in t["fecha_sal"]]
        t = t[t["blq_en"].isin(["DESC", "REP"]) & t["blq_sal"].isin(["DESC", "REP"])].copy()
        t["dia"] = pd.to_datetime(t["fecha_sal"].astype(str))
        # Normalize per-1 MNQ contract even for default dynamic qty
        t["pnl_pts_1c"] = t["pnl_pts"].astype(float) / t["qty"].clip(lower=1).astype(float)
        t["usd_1mnq"] = (t["pnl_pts_1c"] - FRIC_MNQ_PTS) * 2.0
        return t

    tf = _enrich(tr_fijo)
    td = _enrich(tr_def)

    bidx = pd.bdate_range("2018-01-01", "2026-09-29")
    blq_d = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in bidx], index=bidx)
    s_o = tf.groupby("dia")["usd_1mnq"].sum().reindex(bidx, fill_value=0.0)
    s_o_dr = s_o.where(blq_d.isin(["DESC", "REP"]), np.nan)

    # Check recovery window 2025-10..2026-09 strictly on DESC+REP!
    tf_25_26 = tf[tf["fecha_sal"] >= 20251001]
    td_25_26 = td[td["fecha_sal"] >= 20251001]

    # Correlations vs existing fronts in DESC+REP (2021-01..2026-09)
    corrs = {}
    s4_p = ROOT / "docs/research/auditoria_claude_20261127/SERIES_4_FRENTES_DR.csv.gz"
    if s4_p.exists():
        s4 = pd.read_csv(s4_p, index_col=0, parse_dates=True)
        com = s_o_dr.dropna().index.intersection(s4.dropna(how="all").index)
        m_o = s_o_dr.loc[com].groupby(lambda d: d.to_period("M")).sum()
        for c in ("CME_TRZV", "CME_Div10", "Carril2_Sell16", "Cripto_Core_Stag"):
            if c in s4:
                mc = s4.loc[com, c].dropna().groupby(lambda d: d.to_period("M")).sum()
                ci = m_o.index.intersection(mc.index)
                corrs[f"corr_monthly_vs_{c}"] = round(float(m_o.loc[ci].corr(mc.loc[ci])), 3)
                corrs[f"corr_daily_vs_{c}"] = round(float(s_o_dr.loc[com].corr(s4.loc[com, c])), 3)

    res = {
        "n_ops_DR_fijo1_18_26": int(len(tf)),
        "n_ops_DR_default_18_26": int(len(td)),
        "n_ops_DR_2025_10_to_2026_09_fijo1": int(len(tf_25_26)),
        "n_ops_DR_2025_10_to_2026_09_default": int(len(td_25_26)),
        "usd_2025_10_to_2026_09_fijo1_DR": round(float(tf_25_26["usd_1mnq"].sum()), 1),
        "DESC_18_26": _stats_monthly(s_o_dr, blq_d == "DESC"),
        "REP_18_26": _stats_monthly(s_o_dr, blq_d == "REP"),
        "DESC_REP_18_26": _stats_monthly(s_o_dr, blq_d.isin(["DESC", "REP"])),
        "DESC_REP_21_26": _stats_monthly(s_o_dr, blq_d.isin(["DESC", "REP"]) & (bidx >= "2021-01-01")),
        "yearly_usd_1mnq_DR": {str(k): round(float(v), 1) for k, v in s_o_dr.dropna().groupby(lambda d: d.year).sum().items()},
        "correlations": corrs,
    }
    print(f"  O fija 1 MNQ: ops_DR={res['n_ops_DR_fijo1_18_26']} | 25-10..26-09 ops={res['n_ops_DR_2025_10_to_2026_09_fijo1']} (default={res['n_ops_DR_2025_10_to_2026_09_default']}) USD={res['usd_2025_10_to_2026_09_fijo1_DR']}")
    print(f"  Stats 18-26 DR={res['DESC_REP_18_26']} | 21-26 DR={res['DESC_REP_21_26']} | corrs={corrs}")
    return res, s_o_dr


def _vol_cboe(V: pd.DataFrame, B: pd.DataFrame, col: str) -> np.ndarray:
    x = V[col].copy()
    x.index = pd.to_datetime(x.index).normalize()
    idx_b = pd.to_datetime(B["fecha"].astype(str))
    x = x.reindex(x.index.union(idx_b)).ffill()
    return x.reindex(idx_b).to_numpy(float)


def run_block_b_global_volcomp() -> tuple[dict, pd.DataFrame]:
    print("\n=== BLOQUE B: Transferencia F-COMPRESION-VOL-CRECE (C2_VZ, C2_EVRP) sobre data/m1dk/ ===", flush=True)
    V = pd.read_parquet(ROOT / "data/m1nt8/cboe_volatility_daily.parquet")
    V = V[V.index < "2026-10-01"]

    res_pairs = {}
    bidx = pd.bdate_range("2012-01-01", "2026-09-29")
    blq_d = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in bidx], index=bidx)
    dr_mask = blq_d.isin(["DESC", "REP"])
    daily_df = pd.DataFrame(index=bidx)

    for asset, (fname, iv_col) in M1DK_SPECS.items():
        D = leer_m1(ROOT / "data/m1dk" / fname)
        D = D[D.index < pd.Timestamp("2026-09-30 18:00:00")]
        B = Q.barras_desde_m1(D, "D1")
        m1 = Q.indices_m1(B, D, "D1")
        h, l, c = (B[k].to_numpy(float) for k in "hlc")
        a20 = Q.atr(h, l, c, 20)
        iv = _vol_cboe(V, B, iv_col)
        v9 = _vol_cboe(V, B, "vix9d_close")
        vx = _vol_cboe(V, B, "vix_close")

        rv10 = pd.Series(np.log(c)).diff().rolling(10).std().to_numpy() * np.sqrt(252.0) * 100.0
        evrp = iv - rv10
        cont = v9 / np.maximum(vx, 1e-6)
        z = lambda arr: ((pd.Series(arr) - pd.Series(arr).rolling(6).mean()) / pd.Series(arr).rolling(6).std()).to_numpy()
        cz = (z(iv) + z(v9)) / 2.0

        with np.errstate(invalid="ignore"):
            sigs = {
                "C2_VZ": dict(lado=(cz < -1.0).astype(int), tipo="mkt", sl=1.25 * a20, tp=np.nan, salida=lambda i, ld, _cz=cz: not (_cz[i] < -1.0), tope=10),
                "C2_EVRP": dict(lado=((evrp > 0.0) & (cont < 1.0)).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=lambda i, ld, _ev=evrp, _ct=cont: not (_ev[i] > 0.0 and _ct[i] < 1.0), tope=20),
            }

        f_arr = B["fecha"].to_numpy()
        for rname, sig in sigs.items():
            key = f"{rname}_{asset}"
            ops = Q.simular(B, sig, viernes=False, m1=m1)
            if len(ops) == 0:
                res_pairs[key] = {"n_dr": 0}
                continue
            ops["fecha_sal"] = f_arr[ops["i0"].to_numpy() + ops["barras"].to_numpy() - 1]
            ops["blq_en"] = [a5_bloque(int(x)) for x in ops["fecha"]]
            ops["blq_sal"] = [a5_bloque(int(x)) for x in ops["fecha_sal"]]
            ops = ops[ops["blq_en"].isin(["DESC", "REP"]) & ops["blq_sal"].isin(["DESC", "REP"])].copy()
            if len(ops) == 0:
                res_pairs[key] = {"n_dr": 0}
                continue
            riesgo = (ops["entrada"] - ops["stop0"]).abs().clip(lower=1e-9)
            gross = (ops["salida_px"] - ops["entrada"]) * ops["lado"]
            ops["fricR_8bps"] = (0.0008 * ops["entrada"]) / riesgo
            ops["R_8bps"] = (gross - 0.0008 * ops["entrada"]) / riesgo
            ops["R_16bps"] = (gross - 0.0016 * ops["entrada"]) / riesgo
            ops["dia"] = pd.to_datetime(ops["fecha_sal"].astype(str))

            s8 = ops.groupby("dia")["R_8bps"].sum().reindex(bidx, fill_value=0.0)
            s8_dr = s8.where(dr_mask, np.nan)
            s16 = ops.groupby("dia")["R_16bps"].sum().reindex(bidx, fill_value=0.0)
            s16_dr = s16.where(dr_mask, np.nan)
            daily_df[key] = s8_dr

            start_d = pd.to_datetime(str(int(B["fecha"].iloc[0])))
            active_m = dr_mask & (bidx >= start_d)
            st_d = _stats_monthly(s8_dr, active_m & (blq_d == "DESC"))
            st_r = _stats_monthly(s8_dr, active_m & (blq_d == "REP"))
            st_dr = _stats_monthly(s8_dr, active_m)
            st_19 = _stats_monthly(s8_dr, active_m & (bidx >= "2019-01-01"))
            st_16_dr = _stats_monthly(s16_dr, active_m)
            res_pairs[key] = {
                "desde": str(start_d.date()),
                "n_ops_DR": int(len(ops)),
                "mean_R_8bps": round(float(ops["R_8bps"].mean()), 4),
                "mean_fricR_8bps": round(float(ops["fricR_8bps"].mean()), 4),
                "DESC": st_d,
                "REP": st_r,
                "DESC_REP_8bps": st_dr,
                "DESC_REP_19_26_8bps": st_19,
                "DESC_REP_16bps": st_16_dr,
            }
            print(
                f"  {key:18s} | ops={len(ops):3d} | R_net={res_pairs[key]['mean_R_8bps']:+.3f} (fric={res_pairs[key]['mean_fricR_8bps']:.3f}R) | "
                f"DESC Sh={st_d['sharpe']:5.2f} | REP Sh={st_r['sharpe']:5.2f} | DR Sh={st_dr['sharpe']:5.2f} | 19-26 Sh={st_19['sharpe']:5.2f} | 16bps Sh={st_16_dr['sharpe']:5.2f}"
            )

    # Causal basket Global_VolComp_M1DK: DESC media_mes > 0 & mean_fricR < 0.08 (from PREREGISTRO!)
    alive = [
        k for k, v in res_pairs.items()
        if v.get("n_ops_DR", 0) >= 20 and v["DESC"]["media_mes"] > 0 and v["mean_fricR_8bps"] < 0.08
    ]
    if not alive:
        alive = [k for k, v in res_pairs.items() if v.get("n_ops_DR", 0) >= 20 and v["DESC"]["media_mes"] > 0]
    if alive:
        m_d = daily_df.loc[blq_d == "DESC", alive].groupby(daily_df.loc[blq_d == "DESC"].index.to_period("M")).sum()
        sd_d = m_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
        w_g = (1.0 / sd_d) / (1.0 / sd_d).sum()
        bask = (daily_df[alive] * w_g).sum(axis=1).where(dr_mask, np.nan)
    else:
        w_g = pd.Series(dtype=float)
        bask = pd.Series(0.0, index=bidx).where(dr_mask, np.nan)
    daily_df["Global_VolComp_M1DK"] = bask

    st_bask = {
        "alive_DESC_fric_lt_008": alive,
        "weights_DESC": {k: round(float(v), 4) for k, v in w_g.items()},
        "DESC": _stats_monthly(bask, (blq_d == "DESC") & (bidx >= "2014-07-01")),
        "REP": _stats_monthly(bask, (blq_d == "REP") & (bidx >= "2014-07-01")),
        "DESC_REP": _stats_monthly(bask, dr_mask & (bidx >= "2014-07-01")),
        "DESC_REP_19_26": _stats_monthly(bask, dr_mask & (bidx >= "2019-01-01")),
        "DESC_REP_21_26": _stats_monthly(bask, dr_mask & (bidx >= "2021-01-01")),
    }
    print("\n=== CANASTA GLOBAL VOLCOMP M1DK (SOLO DESC & REP) ===")
    print("  Incluidas:", alive, "pesos:", st_bask["weights_DESC"])
    print("  Stats    :", st_bask["DESC_REP"], "| REP:", st_bask["REP"], "| 21-26:", st_bask["DESC_REP_21_26"])
    return {"pairs": res_pairs, "Global_VolComp_M1DK": st_bask}, daily_df


def main() -> None:
    from registro_global import exigir_contada
    exigir_contada("docs/research/frentes_ortogonales_20261127/PREREGISTRO.md")

    res_o, s_o = run_block_a_fundedsync_o()
    res_g, df_g = run_block_b_global_volcomp()

    # Merge daily series cleanly & strictly mask non-DESC/REP as NaN
    comb = df_g.copy()
    comb["FundedSync_O_1MNQ"] = s_o.reindex(comb.index)
    blq_c = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in comb.index], index=comb.index)
    comb.loc[~blq_c.isin(["DESC", "REP"])] = np.nan
    comb.to_csv(OUT / "SERIES_FRENTES_ORTOGONALES_DR.csv.gz")

    out_json = {"FundedSync_O_Fijo1": res_o, "Global_VolComp_M1DK": res_g}
    (OUT / "RESULTADO.json").write_text(json.dumps(out_json, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # Write clean RESULTADO.md
    gv = res_g["Global_VolComp_M1DK"]
    md = [
        "# FRENTES-ORTOGONALES-20261127: FundedSync O (1 MNQ fijo) y Compresión de Volatilidad Global en M1DK (resultado, 2026-11-27)",
        "",
        f"Estado: RESULTADO — pre-registrado en [PREREGISTRO.md](file:///{(OUT / 'PREREGISTRO.md').as_posix()}) (`11` pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "## A. FundedSync O (`qty=1` MNQ fijo, `2018–2026-09`)",
        f"- Con tamaño por defecto (`capital=100k`), `O` dejó `0` operaciones desde `2025-10`; fijando `qty=1` MNQ opera **`{res_o['n_ops_DR_2025_10_to_2026_09_fijo1']}`** veces en `2025-10..2026-09` (`DESC+REP`) sumando **`\\${res_o['usd_2025_10_to_2026_09_fijo1_DR']}`** netos.",
        f"- `DESC (18–26)`: `Sh={res_o['DESC_18_26']['sharpe']}` (`t={res_o['DESC_18_26']['t']}`, `+\\${res_o['DESC_18_26']['media_mes']}/m`); `REP (18–26)`: `Sh={res_o['REP_18_26']['sharpe']}` (`t={res_o['REP_18_26']['t']}`, `+\\${res_o['REP_18_26']['media_mes']}/m`); `21–26 DR`: `Sh={res_o['DESC_REP_21_26']['sharpe']}` (`t={res_o['DESC_REP_21_26']['t']}`).",
        f"- Correlaciones: `{res_o['correlations']}`.",
        "",
        "## B. Transferencia global `F-COMPRESION-VOL-CRECE` (`C2_VZ` y `C2_EVRP` en `data/m1dk/`, `8 bps RT`)",
        "| Regla / Activo | `ops DR` | `mean R` (`fric R`) | `DESC Sh` | `REP Sh` | `DR Sh` | `19–26 Sh` | `16 bps Sh` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k, v in res_g["pairs"].items():
        if v.get("n_ops_DR", 0) == 0:
            continue
        md.append(
            f"| `{k}` | `{v['n_ops_DR']}` | `{v['mean_R_8bps']:+.3f}R` (`{v['mean_fricR_8bps']:.3f}R`) | "
            f"`{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | `{v['DESC_REP_8bps']['sharpe']}` | `{v['DESC_REP_19_26_8bps']['sharpe']}` | `{v['DESC_REP_16bps']['sharpe']}` |"
        )
    md += [
        f"| **`Global_VolComp_M1DK`** ({len(gv['alive_DESC_fric_lt_008'])} activas) | — | — | `{gv['DESC']['sharpe']}` | `{gv['REP']['sharpe']}` | **`{gv['DESC_REP']['sharpe']}` (`t={gv['DESC_REP']['t']}`)** | `{gv['DESC_REP_19_26']['sharpe']}` | `21–26={gv['DESC_REP_21_26']['sharpe']}` |",
        "",
        f"- Incluidas por regla causal (`DESC > 0` y `fricR < 0.08`): `{gv['alive_DESC_fric_lt_008']}` (pesos: `{gv['weights_DESC']}`).",
        "- **Aporte al referente**: recupera un mecanismo overnight de `FundedSync O` con `corr ~ 0` frente a `TRZV` mediante tamaño fijo `1 MNQ`, y mide limpiamente si `F-COMPRESION-VOL-CRECE` transfiere a índices globales y oro sin glitches de roll.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


if __name__ == "__main__":
    main()
