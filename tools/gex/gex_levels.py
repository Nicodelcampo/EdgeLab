#!/usr/bin/env python3
"""gex_levels.py — Genera el archivo de niveles GEX que lee el indicador NT8.

DOS FUENTES, un solo archivo de salida:

  --history   Lee los parquets locales de opciones (E:\\options_data\\SPY_options.parquet)
              y calcula los niveles DIA POR DIA hacia atras (~17 anos).
  --today     Baja la cadena delayed de CBOE (gratis, sin API key) y agrega/actualiza
              la fila de HOY. Gamma se calcula in-house con Black-Scholes desde la IV
              de CBOE (la cadena no trae gamma, trae IV).

Salida: un CSV que el indicador GexLevels.cs lee:
  date,symbol,spot_index,call_wall,put_wall,gamma_flip,net_gex_bn,regime,source

  - Todos los niveles en PUNTOS DE INDICE (SPY x 10 ~ SPX). El indicador tiene un
    parametro PriceOffset para el basis ES si lo queres ajustar a mano.

Correcciones respecto de reconstruct_daily_gex.py (P-39):
  - gex en DOLARES reales: OI x gamma x spot^2 x 0.01 x 100 (faltaba el spot^2).
  - spot estimado por put-call parity (mediana de strike + call_mid - put_mid),
    no "mediana de strikes".
  - gamma_flip por interpolacion del cruce de GEX acumulado (declarado aproximado).

Uso:
  python gex_levels.py --history     # una vez, tarda unos minutos
  python gex_levels.py --today       # cada dia (o un par de veces al dia)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from datetime import date as _date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ config ---
OPTIONS_DIR = Path(r"E:\options_data")
# Anclado al repo donde vive este archivo. Estaba fijo en D:\EdgeLab, que es OTRO clon
# (hay tres en esta maquina): el indicador leia el CSV de un repo distinto del editado.
OUT_CSV = Path(__file__).resolve().parents[2] / "data" / "gex" / "gex_levels.csv"

# multiplier: del underlier del parquet al indice. SPY x 10 ~ SPX.
SYMBOLS = {"SPY": 10.0}

RISK_FREE = 0.043          # solo se usa para gamma del fetch de hoy (BS)
DIV_YIELD = {"SPY": 0.012}  # estimacion; error de 2do orden en gamma

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/%s.json"


# ------------------------------------------------------------------- BS -----
def _phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs_gamma(spot: float, strike: float, t_years: float, iv: float,
             r: float, q: float) -> float:
    """Gamma Black-Scholes generalizada (misma para call y put)."""
    if t_years <= 0 or iv <= 0 or spot <= 0 or strike <= 0:
        return 0.0
    vol_sqrt_t = iv * math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * iv * iv) * t_years) / vol_sqrt_t
    return _phi(d1) * math.exp(-q * t_years) / (spot * vol_sqrt_t)


# --------------------------------------------------------------- niveles ----
def compute_levels_one_day(df: pd.DataFrame, spot: float,
                           multiplier: float) -> dict:
    """df: opciones de UN dia con columnas strike/type/open_interest/gamma.
    Devuelve niveles en puntos de indice (ya multiplicados)."""
    # Dollar GEX por contrato: OI * gamma * spot^2 * 0.01 * 100  (convencion 1% move)
    scale = spot * spot * 0.01 * 100.0
    is_call = df["type"].str.upper().str.startswith("C")
    sign = np.where(is_call, 1.0, -1.0)
    df = df.assign(gex=df["open_interest"].to_numpy(float)
                   * df["gamma"].to_numpy(float) * sign * scale)

    by_strike = df.groupby("strike")["gex"].sum().sort_index()
    if by_strike.empty:
        return {}

    call_gex = df.loc[is_call].groupby("strike")["gex"].sum()
    put_gex = df.loc[~is_call].groupby("strike")["gex"].sum()

    call_wall = float(call_gex.idxmax()) if len(call_gex) else np.nan
    put_wall = float(put_gex.idxmin()) if len(put_gex) else np.nan
    net_gex = float(by_strike.sum())

    # Gamma flip aproximado: cruce de cero del GEX acumulado por strike,
    # interpolado linealmente entre los dos strikes que lo encierran.
    cum = by_strike.cumsum()
    vals = cum.to_numpy(float)
    strikes = cum.index.to_numpy(float)
    flip = np.nan
    for i in range(len(vals) - 1):
        if vals[i] == 0.0:
            flip = strikes[i]
            break
        if vals[i] * vals[i + 1] < 0:
            w = abs(vals[i]) / (abs(vals[i]) + abs(vals[i + 1]))
            flip = strikes[i] + w * (strikes[i + 1] - strikes[i])
            break
    if math.isnan(flip):
        flip = float(by_strike.abs().idxmax())  # fallback: muro dominante

    return {
        "spot_index": round(spot * multiplier, 2),
        "call_wall": round(call_wall * multiplier, 2),
        "put_wall": round(put_wall * multiplier, 2),
        "gamma_flip": round(flip * multiplier, 2),
        "net_gex_bn": round(net_gex / 1e9, 3),
        "regime": "POS" if net_gex > 0 else "NEG",
    }


# --------------------------------------------------------------- history ----
def parity_spot(day: pd.DataFrame) -> float:
    """Spot del dia por put-call parity: strike + call_mid - put_mid (mediana).

    La paridad vale ENTRE CALL Y PUT DEL MISMO VENCIMIENTO. La version anterior hacia
    `merge(on="strike")` sobre un dia que contiene todos los vencimientos, o sea un
    producto cartesiano: cada call de cada expiracion contra cada put de cada otra. Con
    ~40 vencimientos son ~1.600 pares basura por strike, y el spot salia de la mediana
    de comparaciones sin sentido. Ahora se empareja por (expiration, strike).
    """
    mid = (day["bid"].fillna(0) + day["ask"].fillna(0)) / 2.0
    day = day.assign(mid=np.where(mid > 0, mid, day["last"]))
    llave = ["expiration", "strike"] if "expiration" in day.columns else ["strike"]
    calls = day[day["type"].str.upper().str.startswith("C")][llave + ["mid"]]
    puts = day[day["type"].str.upper().str.startswith("P")][llave + ["mid"]]
    j = calls.merge(puts, on=llave, suffixes=("_c", "_p"))
    j = j[(j["mid_c"] > 0) & (j["mid_p"] > 0)]
    if j.empty:
        return float(day["strike"].median())
    est = j["strike"] + (j["mid_c"] - j["mid_p"])
    return float(est.median())


def run_history(symbol: str, multiplier: float) -> pd.DataFrame:
    path = OPTIONS_DIR / f"{symbol}_options.parquet"
    if not path.exists():
        print(f"  !! no existe {path} — salteo {symbol}")
        return pd.DataFrame()
    cols = ["date", "expiration", "strike", "type", "open_interest", "gamma",
            "last", "bid", "ask"]
    # El filtro se empuja a pyarrow: sin esto se materializan 24,7 M de filas x 9
    # columnas (~2 GB con las de texto) para descartar la mayoria enseguida.
    df = pd.read_parquet(path, columns=cols,
                         filters=[("open_interest", ">", 0), ("gamma", ">", 0)])
    df["type"] = df["type"].str.upper()
    df = df[(df["open_interest"] > 0) & (df["gamma"] > 0)].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    print(f"  {symbol}: {len(df):,} opciones activas, {df['date'].nunique()} dias")

    rows = []
    for dt, day in df.groupby("date"):
        spot = parity_spot(day)
        lev = compute_levels_one_day(day, spot, multiplier)
        if lev:
            rows.append({"date": str(dt), "symbol": symbol, "source": "parquet",
                         **lev})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------- today ----
def parse_occ(occ: str):
    """'SPY  260918C00650000' -> (expiry date, 'C', 650.0)."""
    tail = occ.replace(" ", "")[-15:]
    expiry = datetime.strptime(tail[:6], "%y%m%d").date()
    cp = tail[6]
    strike = int(tail[7:]) / 1000.0
    return expiry, cp, strike


def run_today(symbol: str, multiplier: float) -> pd.DataFrame:
    url = CBOE_URL % symbol
    print(f"  bajando {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    data = json.loads(raw.decode("utf-8"))["data"]
    spot = float(data["current_price"])  # delayed ~15 min: ok para niveles
    today = _date.today()
    q = DIV_YIELD.get(symbol, 0.0)

    recs = []
    for o in data["options"]:
        oi = float(o.get("open_interest") or 0)
        iv = float(o.get("iv") or 0)
        if oi <= 0 or iv <= 0:
            continue
        expiry, cp, strike = parse_occ(o["option"])
        # 0DTE: `days = 0` daba t = 0, y bs_gamma corta con `t <= 0` -> gamma 0 -> el
        # `if g > 0` de abajo los descartaba a TODOS. Justo el vencimiento que concentra
        # casi toda la gamma quedaba afuera. Piso de un cuarto de dia (~6 h de sesion).
        t = max((expiry - today).days, 0.25) / 365.0
        g = bs_gamma(spot, strike, t, iv, RISK_FREE, q)
        if g > 0:
            recs.append({"strike": strike, "type": cp,
                         "open_interest": oi, "gamma": g})
    df = pd.DataFrame(recs)
    lev = compute_levels_one_day(df, spot, multiplier)
    if not lev:
        return pd.DataFrame()
    return pd.DataFrame([{"date": str(today), "symbol": symbol,
                          "source": "cboe_delayed", **lev}])


# ------------------------------------------------------------------ main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true", help="serie diaria desde parquets")
    ap.add_argument("--today", action="store_true", help="fila de hoy desde CBOE")
    ap.add_argument("--out", default=str(OUT_CSV))
    a = ap.parse_args()
    if not (a.history or a.today):
        a.history = a.today = True

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for sym, mult in SYMBOLS.items():
        if a.history:
            frames.append(run_history(sym, mult))
        if a.today:
            try:
                frames.append(run_today(sym, mult))
            except Exception as e:
                print(f"  !! fetch CBOE fallo ({e}) — sigo con lo que hay")

    frames = [f for f in frames if not f.empty]
    if not frames:
        sys.exit("sin datos: no se escribio nada")

    new = pd.concat(frames, ignore_index=True)
    if out.exists():
        old = pd.read_csv(out, dtype=str)
        new = pd.concat([old, new.astype(str)], ignore_index=True)
    new = new.drop_duplicates(subset=["date", "symbol"], keep="last")
    new = new.sort_values(["symbol", "date"]).reset_index(drop=True)
    new.to_csv(out, index=False)
    print(f"\nescrito {out}  ({len(new)} filas)")
    print(new.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
