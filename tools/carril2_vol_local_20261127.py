#!/usr/bin/env python3
"""CARRIL2-VOL-LOCAL: Corrección K61 de volatilidad implícita local en C2_VBB, C2_VZ y C2_EVRP.

Pre-registro: docs/research/carril2_vol_local_20261127/PREREGISTRO.md (K51/K61/K62).
Compara insumo local (^AXVI, ^VXD, ^RVX, ^GVZ) vs ^VIX exógeno de EE. UU. contra control N.
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
from edgelab.research.embudo_runners import friccion  # noqa: E402
from datos import ruta  # noqa: E402
from m1_largo import cargar  # noqa: E402
import confianza_sin_forward as CSF  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/carril2_vol_local_20261127/PREREGISTRO.md"
DATA = ROOT / "data/confianza_sf"
OUT = ROOT / "docs/research/carril2_vol_local_20261127"
OUT.mkdir(parents=True, exist_ok=True)
CORTE_INT = 20261001


def _stats(m: pd.Series) -> dict:
    m = m.dropna()
    n = int(len(m))
    if n < 3 or m.std(ddof=1) == 0:
        return dict(meses=n, media=0.0, sharpe_anual=0.0, t=0.0, p_una_cola=1.0)
    mu, sd = float(m.mean()), float(m.std(ddof=1))
    t = mu / (sd / sqrt(n))
    return dict(
        meses=n,
        media=round(mu, 4),
        sharpe_anual=round(mu / sd * sqrt(12), 3),
        t=round(t, 2),
        p_una_cola=round(0.5 * (1.0 - erf(t / sqrt(2.0))), 4),
    )


def _senales_vol(B: pd.DataFrame, iv_col: pd.Series) -> dict:
    h, l, c = (B[k].to_numpy(float) for k in "hlc")
    a20 = Q.atr(h, l, c, 20)
    iv = iv_col.reindex(pd.to_datetime(B["fecha"].astype(str))).ffill().to_numpy(float)
    S = pd.Series(iv)
    m20, s20 = S.rolling(20).mean().to_numpy(), S.rolling(20).std().to_numpy()
    rv10 = pd.Series(np.log(c)).diff().rolling(10).std().to_numpy() * np.sqrt(252) * 100.0
    evrp = iv - rv10
    cz = ((S - S.rolling(6).mean()) / S.rolling(6).std()).to_numpy()
    with np.errstate(invalid="ignore"):
        dos_alzas = lambda i, ld: c[i] > c[i - 1] > c[i - 2]
        return {
            "C2_VBB": dict(lado=(iv > m20 + 2 * s20).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=dos_alzas, tope=10),
            "C2_VBBN": dict(lado=(iv < m20 - 1 * s20).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=dos_alzas, tope=10),
            "C2_VZ_1F": dict(lado=(cz < -1).astype(int), tipo="mkt", sl=1.25 * a20, tp=np.nan, salida=lambda i, ld: not (cz[i] < -1), tope=10),
            "C2_VZ_1FN": dict(lado=(cz > 1).astype(int), tipo="mkt", sl=1.25 * a20, tp=np.nan, salida=lambda i, ld: not (cz[i] > 1), tope=10),
            "C2_EVRP_1F": dict(lado=(evrp > 0).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=lambda i, ld: not (evrp[i] > 0), tope=20),
            "C2_EVRP_1FN": dict(lado=(evrp <= 0).astype(int), tipo="mkt", sl=2.0 * a20, tp=np.nan, salida=lambda i, ld: not (evrp[i] <= 0), tope=20),
        }


def _eval_pair(B: pd.DataFrame, m1, iv_series: pd.Series, bps: float | None, fr_pts: float | None, min_date: int) -> pd.DataFrame:
    S = _senales_vol(B, iv_series)
    f = B["fecha"].to_numpy()
    partes = []
    for d, sig in S.items():
        O = Q.simular(B, sig, viernes=False, m1=m1)
        if not len(O):
            continue
        rg = (O["entrada"] - O["stop0"]).abs()
        fr = fr_pts if fr_pts is not None else O["entrada"] * (bps / 1e4)
        O["R"] = (O["lado"] * (O["salida_px"] - O["entrada"]) - fr) / rg
        O["fecha_sal"] = f[np.minimum(O["i0"] + O["barras"] - 1, len(f) - 1)]
        O = O[(O["fecha"] >= min_date) & (O["fecha"] < CORTE_INT) & (O["fecha_sal"] < CORTE_INT) & O["stop0"].notna() & (rg > 0)].copy()
        if len(O):
            O["definicion"] = d
            partes.append(O)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def main() -> int:
    exigir_contada(PRE)
    DATA.mkdir(parents=True, exist_ok=True)
    for sym, nm in [("^AXJO", "ASX200"), ("^DJI", "Dow"), ("^RUT", "Russell2000"), ("^VIX", "VIX"), ("^AXVI", "AXVI")]:
        pq = DATA / f"{nm}.parquet"
        if not pq.exists():
            df_y, sha_y = CSF._yahoo(sym)
            df_y.to_parquet(pq)
            if nm == "AXVI":
                sha_axvi = sha_y
        elif nm == "AXVI":
            sha_axvi = "cached"
    axvi = pd.read_parquet(DATA / "AXVI.parquet")
    vix_yahoo = pd.read_parquet(DATA / "VIX.parquet")["c"]
    cboe = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet")
    cboe.index = pd.to_datetime(cboe.index).normalize()

    pairs = [
        ("ASX200", "AXVI", CSF._barras("ASX200"), None, axvi["c"], vix_yahoo, 3.0, None, 20080102),
        ("Dow", "VXD", CSF._barras("Dow"), None, cboe["vxd_close"], cboe["vix_close"], 3.0, None, 20060103),
        ("Russell2000", "RVX", CSF._barras("Russell2000"), None, cboe["rvx_close"], cboe["vix_close"], 3.0, None, 20060103),
        ("GC", "GVZ", None, True, cboe["gvz_close"], cboe["vix_close"], None, float(friccion("GC")[0]), 20080603),
    ]

    res = {"axvi_sha256": sha_axvi, "por_activo": {}, "resumen_reglas": {}}
    all_rows = []
    for inst, iv_name, B, use_m1, iv_loc, iv_us, bps, fr_pts, min_d in pairs:
        m1 = None
        if use_m1:
            D = cargar("GC", ruta("M1NT8"))
            B = Q.barras_desde_m1(D, "D1")
            m1 = Q.indices_m1(B, D, "D1")
        all_m = pd.to_datetime(B[(B["fecha"] >= min_d) & (B["fecha"] < CORTE_INT)]["fecha"].astype(str)).dt.to_period("M").unique()

        inst_res = {}
        for mode, iv_s in [("LOCAL", iv_loc), ("VIX_EEUU", iv_us)]:
            T = _eval_pair(B, m1, iv_s, bps, fr_pts, min_d)
            T["mes"] = pd.to_datetime(T["fecha"].astype(str)).dt.to_period("M")
            T["inst"] = inst
            T["modo"] = mode
            all_rows.append(T)
            mout = {}
            for r in ("C2_VBB", "C2_VZ_1F", "C2_EVRP_1F"):
                mr = T[T["definicion"] == r].groupby("mes")["R"].sum().reindex(all_m).fillna(0.0)
                mc = T[T["definicion"] == r + "N"].groupby("mes")["R"].sum().reindex(all_m).fillna(0.0)
                mout[r] = {"regla": _stats(mr), "control_N": _stats(mc), "diff": _stats(mr - mc), "ops": int((T["definicion"] == r).sum())}
            inst_res[mode] = mout
        res["por_activo"][f"{inst}_{iv_name}"] = inst_res

    big = pd.concat(all_rows, ignore_index=True)
    for r in ("C2_VBB", "C2_VZ_1F", "C2_EVRP_1F"):
        rout = {}
        for mode in ("LOCAL", "VIX_EEUU"):
            sub = big[big["modo"] == mode]
            mr = sub[sub["definicion"] == r].pivot_table(index="mes", columns="inst", values="R", aggfunc="sum").fillna(0.0).mean(axis=1)
            mc = sub[sub["definicion"] == r + "N"].pivot_table(index="mes", columns="inst", values="R", aggfunc="sum").fillna(0.0).mean(axis=1)
            rout[mode] = {"regla": _stats(mr), "control_N": _stats(mc), "diff": _stats(mr - mc)}
        res["resumen_reglas"][r] = rout

    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [
        "# CARRIL2-VOL-LOCAL: Corrección K61 de Volatilidad Implícita Local (`2006–2026-09`)",
        "",
        "Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` contrastes, `CARRIL2_VOL_LOCAL`). Cobertura verificada K62: `ASX200/^AXVI`, `Dow/^VXD`, `Russell2000/^RVX`, `GC/^GVZ` (`^V2TX/^VHSI/^JNIV/^VDAX` no disponibles vía Yahoo/TLS en este entorno).",
        "",
        "## Resumen agregado por regla (`LOCAL` vs `VIX_EEUU`)",
        "| Regla | `LOCAL Regla Sh (t)` | `LOCAL Diff vs N Sh (t)` | `VIX Regla Sh (t)` | `VIX Diff vs N Sh (t)` |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for r, rd in res["resumen_reglas"].items():
        lc, vx = rd["LOCAL"], rd["VIX_EEUU"]
        md.append(f"| `{r}` | `{lc['regla']['sharpe_anual']} ({lc['regla']['t']})` | **`{lc['diff']['sharpe_anual']} ({lc['diff']['t']})`** | `{vx['regla']['sharpe_anual']} ({vx['regla']['t']})` | `{vx['diff']['sharpe_anual']} ({vx['diff']['t']})` |")

    md.extend(["", "## Detalle por par activo × volatilidad implícita", "| Par | Regla | `LOCAL Sh (t)` | `LOCAL diff N (t)` | `VIX Sh (t)` | `VIX diff N (t)` |", "| :--- | :--- | :---: | :---: | :---: | :---: |"])
    for pair_k, pd_d in res["por_activo"].items():
        for r in ("C2_VBB", "C2_VZ_1F", "C2_EVRP_1F"):
            l1, v1 = pd_d["LOCAL"][r], pd_d["VIX_EEUU"][r]
            md.append(f"| `{pair_k}` | `{r}` | `{l1['regla']['sharpe_anual']} ({l1['regla']['t']})` | `{l1['diff']['sharpe_anual']} ({l1['diff']['t']})` | `{v1['regla']['sharpe_anual']} ({v1['regla']['t']})` | `{v1['diff']['sharpe_anual']} ({v1['diff']['t']})` |")

    md.extend([
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (`3` reglas congeladas comparando insumo local vs `^VIX`).",
        "Episodios: cubre `2006/2008–2026-09` completo sobre los `4` activos con volatilidad implícita local verificada.",
        "",
        "Aporte al referente: corrige el error K61 donde se usó `^VIX` de EE. UU. como proxy universal en reglas de volatilidad implícita.",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(res["resumen_reglas"], indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
