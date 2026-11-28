#!/usr/bin/env python3
"""CARRIL2-EMD: Transferencia congelada de Carril 2 a E-mini S&P MidCap 400 (EMD, M1 NT8, 2006–2026-09).

Pre-registro: docs/research/carril2_emd_20261127/PREREGISTRO.md (K33/K51).
Evalúa reglas congeladas de tools/carril2.py en EMD (instrumento nunca usado por Carril 2) vs control N exacto.
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

from edgelab import costos  # noqa: E402
from edgelab.holdout import a5_bloque  # noqa: E402
from edgelab.research import sqx_catalogo as Q  # noqa: E402
from edgelab.research.embudo_runners import friccion  # noqa: E402
from datos import ruta  # noqa: E402
from m1_largo import cargar  # noqa: E402
import carril2 as C2  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/carril2_emd_20261127/PREREGISTRO.md"
OUT = ROOT / "docs/research/carril2_emd_20261127"
OUT.mkdir(parents=True, exist_ok=True)
CORTE_INT = 20261001
NUCLEO5 = ("C2_IBS", "C2_D7", "C2_TT", "C2_TOM", "C2_VBB")
TODAS9 = NUCLEO5 + ("C2_P80", "C2_EVRP", "C2_VZ", "C2_DBO")


def _stats(m: pd.Series) -> dict:
    m = m.dropna()
    n = int(len(m))
    if n < 3:
        return dict(meses=n, media=0.0, sharpe_anual=0.0, t=0.0, p_una_cola=1.0, pct_meses_pos=0.0)
    mu = float(m.mean())
    sd = float(m.std(ddof=1))
    t = mu / (sd / sqrt(n)) if sd > 0 else 0.0
    sh = mu / sd * sqrt(12) if sd > 0 else 0.0
    p = 0.5 * (1.0 - erf(t / sqrt(2.0)))
    return dict(
        meses=n,
        media=round(mu, 4),
        sharpe_anual=round(sh, 3),
        t=round(t, 2),
        p_una_cola=round(p, 4),
        pct_meses_pos=round(float((m > 0).mean()), 3),
    )


def _mensual(T: pd.DataFrame, reglas: tuple[str, ...], col: str, ctrl: bool = False) -> pd.Series:
    defs = [r + "N" if ctrl else r for r in reglas]
    sub = T[T["definicion"].isin(defs)].copy()
    if not len(sub):
        return pd.Series(dtype=float)
    sub["regla"] = sub["definicion"].str[:-1] if ctrl else sub["definicion"]
    p = sub.pivot_table(index="mes", columns="regla", values=col, aggfunc="sum")
    for r in reglas:
        if r not in p.columns:
            p[r] = 0.0
    return p[list(reglas)].fillna(0.0).mean(axis=1)


def main() -> int:
    exigir_contada(PRE)
    with costos.estimados_permitidos(PRE):
        fr_base, extra_adv = [float(x) for x in friccion("EMD")]
        fr_adv = round(fr_base + extra_adv, 6)

    V = pd.read_parquet(Path(ruta("M1NT8")) / "cboe_volatility_daily.parquet")
    vc = V["vix_close"].copy()
    vc.index = pd.to_datetime(vc.index).normalize()
    vix_reg = (vc > vc.rolling(100).mean()).shift(1)

    D = cargar("EMD", ruta("M1NT8"))
    B = Q.barras_desde_m1(D, "D1")
    m1 = Q.indices_m1(B, D, "D1")
    vix_ok = vix_reg.reindex(pd.to_datetime(B["fecha"].astype(str))).ffill().fillna(False).to_numpy(bool)

    mens_dummy = pd.Series(dtype=float)
    mens_dummy.attrs["sma"] = pd.Series(dtype=float)
    S = {**C2._senales(B, vix_ok), **{k: v for k, v in C2._senales2(B, "EMD", V, mens_dummy).items() if not k.startswith("C2_ROT")}}

    f = B["fecha"].to_numpy()
    partes = []
    for d, sig in S.items():
        base_r = d[:-1] if d.endswith("N") and d[:-1] in TODAS9 else d
        if base_r not in TODAS9:
            continue
        O = Q.simular(B, sig, viernes=False, m1=m1)
        if not len(O):
            continue
        rg = (O["entrada"] - O["stop0"]).abs()
        O = O[O["stop0"].notna() & (rg > 0)].copy()
        rg = rg.loc[O.index]
        gross = O["lado"] * (O["salida_px"] - O["entrada"])
        O["R_bruto"] = gross / rg
        O["R_base"] = (gross - fr_base) / rg
        O["R_adv"] = (gross - fr_adv) / rg
        O["R_2x"] = (gross - 2.0 * fr_base) / rg
        O["fricR_base"] = fr_base / rg
        O["fecha_salida"] = f[np.minimum(O["i0"] + O["barras"] - 1, len(f) - 1)]
        O["definicion"] = d
        partes.append(O)

    T = pd.concat(partes, ignore_index=True)
    T = T[(T["fecha"] < CORTE_INT) & (T["fecha_salida"] < CORTE_INT)].copy()
    bl = {int(x): a5_bloque(int(x)) for x in pd.unique(np.r_[T["fecha"].to_numpy(), T["fecha_salida"].to_numpy()])}
    T["bloque"] = T["fecha"].map(bl)
    T["bloque_salida"] = T["fecha_salida"].map(bl)
    assert not T["bloque"].isin(["TERMINAL"]).any() and not T["bloque_salida"].isin(["TERMINAL"]).any()
    T["mes"] = pd.to_datetime(T["fecha"].astype(str)).dt.to_period("M")

    # Universal month index across all D1 EMD bars < 2026-10-01
    B_clip = B[B["fecha"] < CORTE_INT]
    all_months = pd.to_datetime(B_clip["fecha"].astype(str)).dt.to_period("M").unique()
    mes_blq = pd.Series([a5_bloque(int(f"{p.year:04d}{p.month:02d}15")) for p in all_months], index=all_months)

    T.to_csv(OUT / "OPS_EMD.csv.gz", index=False)

    res: dict = {
        "instrumento": "EMD",
        "friccion_base_pts": fr_base,
        "friccion_adv_pts": fr_adv,
        "ops_regla_todas9": int((~T["definicion"].str.endswith("N")).sum()),
        "ops_control_todas9": int(T["definicion"].str.endswith("N").sum()),
        "fricR_media_base": round(float(T["fricR_base"].mean()), 4),
        "grupos": {},
        "por_regla_base": {},
    }

    windows = {
        "todo_2006_2026": lambda m: pd.Series(True, index=m.index),
        "antes_2009": lambda m: m.index < pd.Period("2009-01", "M"),
        "desde_2009": lambda m: m.index >= pd.Period("2009-01", "M"),
        "desde_2019": lambda m: m.index >= pd.Period("2019-01", "M"),
        "DESC": lambda m: mes_blq.reindex(m.index) == "DESC",
        "REP": lambda m: mes_blq.reindex(m.index) == "REP",
        "HOLDOUT": lambda m: mes_blq.reindex(m.index) == "HOLDOUT",
    }

    for gname, rtuple in [("nucleo_5", NUCLEO5), ("todas_9", TODAS9)]:
        gout = {}
        for cost_col in ("R_base", "R_bruto", "R_adv", "R_2x"):
            mr = _mensual(T, rtuple, cost_col, ctrl=False).reindex(all_months).fillna(0.0)
            mc = _mensual(T, rtuple, cost_col, ctrl=True).reindex(all_months).fillna(0.0)
            mdiff = mr - mc
            cout = {}
            for wname, wfn in windows.items():
                msk = wfn(mr)
                cout[wname] = {
                    "regla": _stats(mr[msk]),
                    "control_N": _stats(mc[msk]),
                    "regla_menos_control": _stats(mdiff[msk]),
                }
            gout[cost_col] = cout
        res["grupos"][gname] = gout

    for r in TODAS9:
        mr = _mensual(T, (r,), "R_base", ctrl=False).reindex(all_months).fillna(0.0)
        mc = _mensual(T, (r,), "R_base", ctrl=True).reindex(all_months).fillna(0.0)
        res["por_regla_base"][r] = {
            "ops_regla": int((T["definicion"] == r).sum()),
            "ops_control": int((T["definicion"] == r + "N").sum()),
            "todo": _stats(mr),
            "desde_2009": _stats(mr[windows["desde_2009"](mr)]),
            "diff_todo": _stats(mr - mc),
            "diff_desde_2009": _stats((mr - mc)[windows["desde_2009"](mr)]),
        }

    p_2009 = res["grupos"]["nucleo_5"]["R_base"]["desde_2009"]["regla_menos_control"]
    res["veredicto_primario"] = {
        "criterio": "PLAN_ESPIRAL_20261127 #3: Regla − Control N en EMD desde 2009 (nucleo_5 base)",
        "t": p_2009["t"],
        "sharpe": p_2009["sharpe_anual"],
        "veredicto": "CONFIRMA" if p_2009["t"] >= 1.645 else ("NO_CONCLUYENTE" if p_2009["media"] > 0 else "EN_CONTRA"),
    }

    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    n5 = res["grupos"]["nucleo_5"]["R_base"]
    t9 = res["grupos"]["todas_9"]["R_base"]
    md = [
        "# CARRIL2-EMD: Transferencia Congelada a MidCap 400 (`EMD`, `2006–2026-09`)",
        "",
        f"Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` pruebas, `CARRIL2_EMD`). Costo K33 estimado base `{fr_base}` pts (`fricR={res['fricR_media_base']}`), adverso `{fr_adv}` pts. `TERMINAL >= 2026-10-01` sellado.",
        "",
        "| Grupo (`R_base`) | Ventana | `Regla Sh (t)` | `Control N Sh (t)` | `Regla − Control Sh (t)` | `p (1-cola diff)` |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for gname, gdict in [("Nucleo 5 (IBS,D7,TT,TOM,VBB)", n5), ("Todas 9 Carril 2", t9)]:
        for w in ("todo_2006_2026", "antes_2009", "desde_2009", "desde_2019", "DESC", "REP", "HOLDOUT"):
            rg, ct, df = gdict[w]["regla"], gdict[w]["control_N"], gdict[w]["regla_menos_control"]
            md.append(f"| `{gname}` | `{w}` (`{rg['meses']}m`) | `{rg['sharpe_anual']} ({rg['t']})` | `{ct['sharpe_anual']} ({ct['t']})` | **`{df['sharpe_anual']} ({df['t']})`** | `{df['p_una_cola']}` |")

    md.extend(["", "## Por regla individual en `EMD` (`R_base`)", "| Regla | Ops (R/N) | `todo Sh (t)` | `2009+ Sh (t)` | `diff todo (t)` | `diff 2009+ (t)` |", "| :--- | :---: | :---: | :---: | :---: | :---: |"])
    for r, d in res["por_regla_base"].items():
        md.append(f"| `{r}` | `{d['ops_regla']}/{d['ops_control']}` | `{d['todo']['sharpe_anual']} ({d['todo']['t']})` | `{d['desde_2009']['sharpe_anual']} ({d['desde_2009']['t']})` | `{d['diff_todo']['sharpe_anual']} ({d['diff_todo']['t']})` | `{d['diff_desde_2009']['sharpe_anual']} ({d['diff_desde_2009']['t']})` |")

    md.extend([
        "",
        f"Veredicto primario (`nucleo_5` diff `2009+`): **`{res['veredicto_primario']['veredicto']}`** (`Sh={p_2009['sharpe_anual']}`, `t={p_2009['t']}`).",
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (reglas congeladas de Carril 2 en instrumento nuevo EMD).",
        "Episodios: desglose explícito pre-2009, 2009–2026-09, 2019–2026-09 y bloques DESC/REP/HOLDOUT en la tabla superior.",
        "",
        "Aporte al referente: mide fuera de muestra instrumental si el mecanismo de Carril 2 sobrevive sobre su placebo exacto `N` en EE. UU. post-2009 sobre MidCap (`EMD`).",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"veredicto_primario": res["veredicto_primario"], "nucleo5_todo": n5["todo_2006_2026"], "todas9_2009": t9["desde_2009"]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
