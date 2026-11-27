#!/usr/bin/env python3
"""CRIPTO-PIT (2026-11-27): universo punto en el tiempo de perpetuos USDT-M de Binance y réplica de las 3 reglas cripto de la
auditoría de Antigravity (congeladas, `tools/cartera_cripto_binance.py::build_strategies`) con costos con deslizamiento.

  python tools/cripto_pit.py universo      # target-free: lista TODOS los perpetuos (incluidos los dados de baja), baja velas 1D,
                                           # arma la pertenencia mensual top-K por volumen de los 30 días previos
  python tools/cripto_pit.py velas         # baja velas 1h + funding de toda moneda que alguna vez entró al universo
  python tools/cripto_pit.py medir         # DESC/REP de A5 (pre-registro docs/research/cripto_pit_20261127/PREREGISTRO.md)
  python tools/cripto_pit.py holdout       # apertura única del HOLDOUT A5 de CRIPTO_BINANCE (pre-registro aparte)

Datos: data.binance.vision (público), en data/crypto_binance_pit/ (gitignorado). Corte estricto < 2026-10-01.
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from edgelab.holdout import a5_bloque  # noqa: E402

DATA = ROOT / "data" / "crypto_binance_pit"
OUT = ROOT / "docs" / "research" / "cripto_pit_20261127"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VIS = "https://data.binance.vision"
CORTE = "2026-10-01"
MESES = pd.period_range("2020-01", "2026-09", freq="M").strftime("%Y-%m").tolist()
K_UNIVERSO = 25           # pre-registrado: top-25 por volumen en USDT de los 30 días previos
MIN_DIAS = 60             # pre-registrado: al menos 60 días cotizando antes de entrar
UA = {"User-Agent": "edgelab-research"}


def _get(url: str, timeout: int = 30) -> bytes | None:
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
    return None


def _listar(prefix: str) -> list[str]:
    """Prefijos o claves bajo `prefix` en el bucket público (paginado)."""
    out, marker = [], ""
    while True:
        from urllib.parse import quote
        x = _get(f"{S3}?delimiter=/&prefix={quote(prefix)}&marker={quote(marker)}")
        if x is None:
            raise SystemExit(f"no se pudo listar {prefix}")
        t = x.decode()
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", t)[1:] + re.findall(r"<Key>([^<]+)</Key>", t)
        if "<IsTruncated>true</IsTruncated>" not in t:
            return out
        marker = re.search(r"<NextMarker>([^<]+)</NextMarker>", t).group(1)


def simbolos() -> list[str]:
    f = DATA / "simbolos.json"
    if f.exists():
        return json.loads(f.read_text())
    pre = _listar("data/futures/um/monthly/klines/")
    s = sorted({p.rstrip("/").split("/")[-1] for p in pre})
    s = [x for x in s if x.endswith("USDT") and "_" not in x]          # perpetuos lineales en USDT (sin trimestrales)
    DATA.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(s))
    return s


def _kline_mes(sym: str, iv: str, ym: str) -> pd.DataFrame | None:
    from urllib.parse import quote
    b = _get(quote(f"{VIS}/data/futures/um/monthly/klines/{sym}/{iv}/{sym}-{iv}-{ym}.zip", safe=":/"))
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b)); raw = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if not str(raw.iloc[0, 0]).isdigit():
        raw = raw.iloc[1:]
    raw = raw.iloc[:, :8].astype(float); raw.columns = ["t", "open", "high", "low", "close", "volume", "t_cierre", "quote_volume"]
    return raw


def _meses_de(sym: str, iv: str) -> list[str]:
    keys = _listar(f"data/futures/um/monthly/klines/{sym}/{iv}/")
    return sorted({m.group(1) for k in keys if (m := re.search(rf"{sym}-{iv}-(\d{{4}}-\d{{2}})\.zip$", k))} & set(MESES))


def _serie(sym: str, iv: str) -> pd.DataFrame | None:
    f = DATA / iv / f"{sym}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    partes = [p for ym in _meses_de(sym, iv) if (p := _kline_mes(sym, iv, ym)) is not None]
    f.parent.mkdir(parents=True, exist_ok=True)
    if not partes:
        pd.DataFrame().to_parquet(f); return None
    d = pd.concat(partes).drop_duplicates("t").sort_values("t")
    d.index = pd.to_datetime(d.t.astype("int64"), unit="ms", utc=True)
    d = d[d.index < pd.Timestamp(CORTE, tz="UTC")][["open", "high", "low", "close", "volume", "quote_volume"]]
    d.to_parquet(f)
    return d


def universo() -> int:
    """Target-free: pertenencia mensual. Para el mes m entra una moneda si cotizó ≥ MIN_DIAS días antes del 1.º de m y está en el
    top-K por volumen en USDT de los 30 días previos al 1.º de m. Sólo usa volumen y fechas de cotización (nunca retornos)."""
    syms = simbolos(); print(len(syms), "perpetuos USDT-M (vivos y dados de baja)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(24) as ex:
        series = dict(zip(syms, ex.map(lambda s: _serie(s, "1d"), syms)))
    qv = pd.DataFrame({s: d.quote_volume for s, d in series.items() if d is not None and len(d)}).sort_index()
    qv.index = qv.index.tz_localize(None).normalize()
    primero = qv.apply(lambda c: c.first_valid_index())
    filas = []
    for m in pd.period_range("2020-09", "2026-09", freq="M"):
        ini = m.start_time
        ven = qv[(qv.index < ini) & (qv.index >= ini - pd.Timedelta(days=30))]
        vol = ven.sum(min_count=20)                                       # ≥ 20 días con datos en la ventana
        ok = vol[(primero <= ini - pd.Timedelta(days=MIN_DIAS)) & vol.notna()].sort_values(ascending=False)
        for r, (s, v) in enumerate(ok.head(K_UNIVERSO).items(), 1):
            filas.append(dict(mes=str(m), simbolo=s, rango=r, quote_vol_30d=float(v)))
    u = pd.DataFrame(filas); OUT.mkdir(parents=True, exist_ok=True); u.to_csv(OUT / "UNIVERSO_PIT.csv", index=False)
    ult = qv.apply(lambda c: c.last_valid_index())
    muertas = sorted(s for s in u.simbolo.unique() if ult[s] < pd.Timestamp("2026-09-01"))
    print(f"{u.simbolo.nunique()} monedas alguna vez en el top-{K_UNIVERSO}; dejaron de cotizar antes de 2026-09: {muertas}")
    return 0


def velas() -> int:
    u = pd.read_csv(OUT / "UNIVERSO_PIT.csv"); syms = sorted(u.simbolo.unique())
    from cartera_cripto_binance import _download_month_funding          # reutiliza la bajada de funding de la auditoría
    def una(s):
        k = _serie(s, "1h")
        f = DATA / "funding" / f"{s}.parquet"
        if not f.exists():
            partes = [p for ym in MESES if (p := _download_month_funding(s, ym)) is not None and len(p)]
            fr = pd.concat(partes).drop_duplicates("calc_time").sort_values("calc_time") if partes else pd.DataFrame(columns=["calc_time", "rate"])
            f.parent.mkdir(parents=True, exist_ok=True); fr.to_parquet(f)
        return s, None if k is None else len(k)
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        for s, n in ex.map(una, syms):
            print(s, n, flush=True)
    return 0


# ----------------------------------------------------------------------------------------------------------------------------------
# Medición (pre-registro docs/research/cripto_pit_20261127/PREREGISTRO.md). Reglas congeladas de la auditoría (Antigravity,
# tools/cartera_cripto_binance.py::build_strategies) con tres cambios declarados para el universo punto en el tiempo:
#   1. posición 0 en toda moneda que ese mes no está en el universo (se cierra al salir, con costo);
#   2. el tamaño por moneda se escala por 8 / n_elegibles (mismo presupuesto de riesgo que con 8 monedas);
#   3. el momentum transversal rankea y neutraliza sólo entre elegibles.
COSTOS_RT = {"base": 0.0020, "bajo": 0.0010, "alto": 0.0030}      # comisión taker 5 pb/lado + deslizamiento 5 pb/lado (base)
REGLAS = ("CR_Donchian_1D", "CR_Trend_4H_EMA", "CR_XSMOM_Neutral")


def _barras(syms: list[str]) -> dict:
    out = {}
    for s in syms:
        k = _serie(s, "1h")
        if k is None or not len(k):
            continue
        f = pd.read_parquet(DATA / "funding" / f"{s}.parquet")
        fr = pd.Series(dtype=float)
        if len(f):
            fr = f.assign(dt=pd.to_datetime(f.calc_time.astype("int64"), unit="ms", utc=True).dt.floor("h")).groupby("dt").rate.last()
        out[s] = k.assign(funding=fr.reindex(k.index).fillna(0.0))[["open", "high", "low", "close", "funding"]]
    return out


def _agg(d: dict, regla: str) -> dict:
    return {s: x.resample(regla, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                                                     "funding": "sum"}).dropna(subset=["close"]) for s, x in d.items()}


def _tabla(b: dict, campo: str) -> pd.DataFrame:
    return pd.DataFrame({s: x[campo] for s, x in b.items()}).sort_index()


def _elegible(idx: pd.DatetimeIndex, cols, u: pd.DataFrame) -> pd.DataFrame:
    mes = idx.tz_localize(None).to_period("M").astype(str)
    m = pd.DataFrame(False, index=idx, columns=cols)
    for per, g in u.groupby("mes"):
        sel = mes == per
        m.loc[sel, [c for c in g.simbolo if c in m.columns]] = True
    return m


def _pnl(close: pd.DataFrame, w: pd.DataFrame, fund: pd.DataFrame, costo_rt: float) -> pd.Series:
    """Igual que backtest_weights_bar de la auditoría: peso decidido al cierre t, expuesto a t+1; funding y costo por cambio de peso."""
    w1 = w.shift(1).fillna(0.0); dw = (w1 - w1.shift(1).fillna(0.0)).abs()
    r = (w1 * close.pct_change(fill_method=None).fillna(0.0) - w1 * fund.fillna(0.0) - dw * costo_rt / 2).sum(axis=1) * 10_000.0
    d = r.resample("1D").sum(); d.index = d.index.tz_localize(None)
    return d


def _estado_donchian(c, h20, l20, h10, l10):
    st, p = 0.0, np.zeros(len(c))
    for i in range(21, len(c)):
        if st == 0:
            st = 1.0 if c[i] > h20[i] else -1.0 if c[i] < l20[i] else 0.0
        elif st > 0 and c[i] < l10[i]:
            st = -1.0 if c[i] < l20[i] else 0.0
        elif st < 0 and c[i] > h10[i]:
            st = 1.0 if c[i] > h20[i] else 0.0
        p[i] = st
    return p


def _estado_ema(c, hi, lo, ef, es, a):
    st, stop, p = 0.0, 0.0, np.zeros(len(c))
    for i in range(100, len(c)):
        if not np.isfinite(a[i]) or a[i] <= 0:
            continue
        if st > 0:
            stop = max(stop, c[i] - 2.5 * a[i]); st = 0.0 if (lo[i] <= stop or ef[i] < es[i]) else st
        elif st < 0:
            stop = min(stop, c[i] + 2.5 * a[i]); st = 0.0 if (hi[i] >= stop or ef[i] > es[i]) else st
        if st == 0:
            if ef[i] > es[i] and c[i] > ef[i]: st, stop = 1.0, c[i] - 2.5 * a[i]
            elif ef[i] < es[i] and c[i] < ef[i]: st, stop = -1.0, c[i] + 2.5 * a[i]
        p[i] = st
    return p


def series_reglas(barras: dict, u: pd.DataFrame, costo_rt: float) -> pd.DataFrame:
    d1, h4 = _agg(barras, "1D"), _agg(barras, "4h")
    C1, H1, L1, F1 = (_tabla(d1, k) for k in ("close", "high", "low", "funding"))
    C4, H4, L4, F4 = (_tabla(h4, k) for k in ("close", "high", "low", "funding"))
    E1, E4 = _elegible(C1.index, C1.columns, u), _elegible(C4.index, C4.columns, u)
    esc1 = (8.0 / E1.sum(axis=1).clip(lower=1)).to_numpy()[:, None]; esc4 = (8.0 / E4.sum(axis=1).clip(lower=1)).to_numpy()[:, None]
    tr1 = np.maximum(H1 - L1, np.maximum((H1 - C1.shift(1)).abs(), (L1 - C1.shift(1)).abs()))
    vol1 = (tr1.rolling(20).mean() / C1).clip(lower=0.01)
    tr4 = np.maximum(H4 - L4, np.maximum((H4 - C4.shift(1)).abs(), (L4 - C4.shift(1)).abs()))
    a42 = tr4.rolling(42).mean(); vol4 = (a42 / C4).clip(lower=0.005)
    out = {}
    # 1) Donchian 20/10 diario
    h20, l20 = H1.shift(1).rolling(20).max(), L1.shift(1).rolling(20).min()
    h10, l10 = H1.shift(1).rolling(10).max(), L1.shift(1).rolling(10).min()
    pos = pd.DataFrame({s: _estado_donchian(*(x[s].to_numpy() for x in (C1, h20, l20, h10, l10))) for s in C1.columns}, index=C1.index)
    out["CR_Donchian_1D"] = _pnl(C1, (pos * (0.005 / vol1).clip(upper=0.25)).where(E1, 0.0) * esc1, F1, costo_rt)
    # 2) EMA 24/96 en 4 h con stop móvil 2,5 ATR42
    ef, es = C4.ewm(span=24, adjust=False).mean(), C4.ewm(span=96, adjust=False).mean()
    pos = pd.DataFrame({s: _estado_ema(*(x[s].to_numpy() for x in (C4, H4, L4, ef, es, a42))) for s in C4.columns}, index=C4.index)
    out["CR_Trend_4H_EMA"] = _pnl(C4, (pos * (0.003 / vol4).clip(upper=0.20)).where(E4, 0.0) * esc4, F4, costo_rt)
    # 3) Momentum transversal 14 d ajustado por vol, largo top-2 / corto bottom-2 entre elegibles, rebalanceo cada 3 días, neutral
    sc = (C1.pct_change(14, fill_method=None) / vol1).where(E1)
    rk = sc.rank(axis=1, ascending=False, method="first"); n = sc.notna().sum(axis=1).to_numpy()[:, None]
    pos = pd.DataFrame(0.0, index=C1.index, columns=C1.columns)
    pos[(rk <= 2) & (n >= 6)] = 1.0; pos[(rk >= n - 1) & (n >= 6)] = -1.0
    pos = pos.iloc[::3].reindex(C1.index).ffill().fillna(0.0)
    w = (pos * (0.005 / vol1).clip(upper=0.25)).where(E1, 0.0)
    w = w.sub(w.where(E1).mean(axis=1), axis=0).where(E1, 0.0)
    out["CR_XSMOM_Neutral"] = _pnl(C1, w, F1, costo_rt)
    df = pd.DataFrame(out).fillna(0.0)
    df = df[(df.index >= "2021-01-01") & (df.index < CORTE)]
    df["CR_1N"] = df[list(REGLAS)].mean(axis=1)
    return df


def _est(x: pd.Series) -> dict:
    m = x.groupby(x.index.to_period("M")).sum(); n = len(m)
    sd = float(m.std(ddof=1)) if n > 1 else 0.0; mu = float(m.mean()) if n else 0.0
    from math import erf, sqrt
    t = mu / (sd / np.sqrt(n)) if sd > 0 else 0.0
    eq = x.cumsum()
    return dict(usd_mes=round(mu, 1), t_mes=round(t, 2), p_una_cola=round(0.5 * (1 - erf(t / sqrt(2))), 4), sharpe=round(mu / sd * np.sqrt(12), 2) if sd > 0 else 0.0,
                pct_meses_pos=round(float((m > 0).mean()), 2), caida_max=round(float((eq - eq.cummax()).min()), 0), meses=n)


def medir() -> int:
    from registro_global import exigir_contada
    exigir_contada(OUT / "PREREGISTRO.md")
    u = pd.read_csv(OUT / "UNIVERSO_PIT.csv")
    barras = _barras(sorted(u.simbolo.unique()))
    res, series = {}, {}
    for esc, c in COSTOS_RT.items():
        df = series_reglas(barras, u, c)
        b = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in df.index], index=df.index)
        assert not b.isin(["TERMINAL"]).any()
        series[esc] = df.where(b.isin(["DESC", "REP"]).to_numpy()[:, None])          # HOLDOUT y EMBARGO sellados (NaN)
        res[esc] = {r: {blq: _est(df.loc[b == blq, r]) for blq in ("DESC", "REP")} | {"DESC+REP": _est(df.loc[b.isin(["DESC", "REP"]), r])}
                    for r in df.columns}
    series["base"].to_csv(OUT / "SERIES_DESC_REP_BASE.csv.gz")
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for esc in COSTOS_RT:
        for r in list(REGLAS) + ["CR_1N"]:
            print(esc, r, res[esc][r])
    return 0


def main(argv=None) -> int:
    a = (argv or sys.argv[1:]) + [""]
    return {"universo": universo, "velas": velas, "medir": medir}.get(a[0], lambda: print(__doc__) or 2)()


if __name__ == "__main__":
    raise SystemExit(main())
