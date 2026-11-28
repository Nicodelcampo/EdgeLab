#!/usr/bin/env python3
"""TENDENCIA-NO-EQUITY (2026-11-27): momentum de serie de tiempo mensual (Moskowitz, Ooi y Pedersen 2012) en 14 ETFs de tasas, metales,
energía, granos y divisas. Pre-registro: docs/research/tendencia_no_equity_20261127/PREREGISTRO.md.

  python tools/tendencia_no_equity.py bajar    # precios ajustados de Yahoo (sin retornos), corte < 2026-10-01, data/tendencia_no_equity/
  python tools/tendencia_no_equity.py medir    # DESC y, si pasa, REP de A5 (HOLDOUT y EMBARGO sellados)
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.holdout import a5_bloque  # noqa: E402

DATA = ROOT / "data" / "tendencia_no_equity"
OUT = ROOT / "docs" / "research" / "tendencia_no_equity_20261127"
CLASES = {"TLT": "tasas", "IEF": "tasas", "GLD": "metales", "SLV": "metales", "DBB": "metales", "USO": "energia", "UNG": "energia",
          "DBA": "granos", "FXE": "divisas", "FXY": "divisas", "FXB": "divisas", "FXA": "divisas", "FXC": "divisas", "FXF": "divisas"}
CORTE = pd.Timestamp("2026-10-01")
COSTO_LADO = {"base": 0.0005, "alto": 0.0010}


def bajar() -> int:
    DATA.mkdir(parents=True, exist_ok=True); proc = {}
    p2 = int(CORTE.timestamp())
    for s in CLASES:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1=1104537600&period2={p2}&interval=1d&events=div,split"
        b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
        j = json.loads(b)["chart"]["result"][0]
        d = pd.Series(j["indicators"]["adjclose"][0]["adjclose"], index=pd.to_datetime(j["timestamp"], unit="s").normalize(), name=s)
        d = d[d.index < CORTE].dropna()
        d.to_frame("adjclose").to_parquet(DATA / f"{s}.parquet")
        proc[s] = dict(desde=str(d.index[0].date()), hasta=str(d.index[-1].date()), n=len(d), sha256_respuesta=hashlib.sha256(b).hexdigest())
        print(s, proc[s], flush=True)
    (DATA / "PROCEDENCIA.json").write_text(json.dumps(dict(fuente="query1.finance.yahoo.com v8 chart (adjclose)", archivos=proc), indent=1))
    return 0


def cartera(px: pd.DataFrame, costo_lado: float) -> tuple[pd.Series, pd.DataFrame]:
    """Retorno mensual de la cartera (fracción del capital) y contribución por activo. Señal y tamaño al último cierre del mes m-1,
    expuestos durante el mes m."""
    r = px.pct_change(fill_method=None)
    sig = np.sign(px / px.shift(252) - 1.0)
    vol = r.rolling(63).std() * np.sqrt(252)
    fin = px.groupby(px.index.to_period("M")).apply(lambda g: g.index[-1])           # último día hábil de cada mes
    s_m, v_m = sig.loc[fin.values], vol.loc[fin.values]
    s_m.index = v_m.index = fin.index
    n = s_m.notna().sum(axis=1).replace(0, np.nan)
    w = (s_m * (0.40 / v_m)).clip(-2, 2).div(n, axis=0).fillna(0.0)                 # pesos decididos al cierre del mes m
    rm = (1 + r).groupby(r.index.to_period("M")).prod() - 1                             # retorno de cada activo en el mes
    w_apl = w.shift(1).fillna(0.0)                                                      # se aplican durante el mes siguiente
    contrib = w_apl * rm.reindex(w_apl.index).fillna(0.0)
    costo = (w - w.shift(1).fillna(0.0)).abs().sum(axis=1).shift(1).fillna(0.0) * costo_lado
    return contrib.sum(axis=1) - costo, contrib


def _est(x: pd.Series) -> dict:
    from math import erf, sqrt
    n = len(x); mu = float(x.mean()); sd = float(x.std(ddof=1))
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    mde = 2.49 * sd / np.sqrt(n)                                                        # 1,645 + 0,84: α 0,05 una cola, potencia 0,8
    return dict(meses=n, ret_mes_pct=round(100 * mu, 3), t=round(t, 2), p_una_cola=round(0.5 * (1 - erf(t / sqrt(2))), 4),
                sharpe=round(mu / sd * np.sqrt(12), 2) if sd > 0 else 0.0, pct_meses_pos=round(float((x > 0).mean()), 2),
                mde_ret_mes_pct=round(100 * mde, 3), mde_sharpe=round(mde / sd * np.sqrt(12), 2) if sd > 0 else None)


def medir() -> int:
    from registro_global import exigir_contada
    exigir_contada(OUT / "PREREGISTRO.md")
    px = pd.concat([pd.read_parquet(DATA / f"{s}.parquet").adjclose.rename(s) for s in CLASES], axis=1).sort_index()
    px = px[px.index < CORTE]
    res = {}
    for esc, c in COSTO_LADO.items():
        ret, contrib = cartera(px, c)
        ret = ret[ret.index >= pd.Period("2008-01", "M")]
        # bloque del mes: el de su día 15 (los días de embargo están en los bordes; el mes entero es DESC, REP u HOLDOUT)
        blq = pd.Series([a5_bloque(int((m.start_time + pd.Timedelta(days=14)).strftime("%Y%m%d"))) for m in ret.index], index=ret.index)
        assert not blq.isin(["TERMINAL"]).any()
        d = ret[blq == "DESC"]
        r = dict(DESC=_est(d))
        cd = contrib.reindex(d.index)
        tot = float(cd.sum().sum())
        r["DESC_por_clase_pct_del_total"] = {k: round(100 * float(cd[[s for s in CLASES if CLASES[s] == k]].sum().sum()) / tot, 1) if tot else None
                                             for k in sorted(set(CLASES.values()))}
        r["DESC_mayor_activo"] = {cd.sum().idxmax(): round(100 * float(cd.sum().max()) / tot, 1)} if tot else None
        r["DESC_por_anio_pct"] = {str(a): round(100 * float(v), 2) for a, v in d.groupby(d.index.year).sum().items()}
        pasa = r["DESC"]["t"] >= 1.65
        r["pasa_DESC"] = bool(pasa)
        if pasa:                                                                         # la réplica se lee sólo si DESC pasa
            r["REP"] = _est(ret[blq == "REP"])
        res[esc] = r
        if esc == "base":
            ret.where(blq.isin(["DESC", "REP"] if pasa else ["DESC"])).to_csv(OUT / "SERIE_MENSUAL_LEIDA.csv")
    # correlación con la cartera Intradía (meses DESC)
    X = pd.read_csv(ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    intra = X[["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]].sum(axis=1)
    im = intra.groupby(intra.index.to_period("M")).sum()
    tb = pd.read_csv(OUT / "SERIE_MENSUAL_LEIDA.csv", index_col=0).iloc[:, 0]; tb.index = pd.PeriodIndex(tb.index, freq="M")
    comun = tb.dropna().index.intersection(im.index)
    res["corr_mensual_vs_INTRADIA8_meses_leidos"] = round(float(tb[comun].corr(im[comun])), 3)
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False, default=float))
    return 0


def main(argv=None) -> int:
    a = (argv or sys.argv[1:]) + [""]
    return {"bajar": bajar, "medir": medir}.get(a[0], lambda: print(__doc__) or 2)()


if __name__ == "__main__":
    raise SystemExit(main())
