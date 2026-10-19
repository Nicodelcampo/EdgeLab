#!/usr/bin/env python3
r"""Capa GEX del visor (sólo dibujo, target-free) + bundle ES 09-26 de 1m/5m para verla.

Fuente: SquawkFlow spx-gamma-levels (CC BY 4.0, https://github.com/dhawalc/spx-gamma-levels), un registro por sesión
con niveles SPX (call_wall, put_wall, zero_gamma_flip, vol_trigger) calculados con el OI de `oi_settle_date` (día
hábil previo). `spot` = cierre SPX de ese día.

Causalidad (verificada 2026-10-06 contra los cierres de SqueezeMetrics y el historial de commits del repo):
- El archivo de la sesión D se publica ~13:30 UTC de D (commit del repo). Se dibuja DESDE `available_utc` = D 13:31Z
  HASTA el fin de la sesión CME de D (16:00 CT). Antes de eso, en la sesión D, no existe.
- Conversión SPX -> ES: basis = último tick ES <= 15:00 CT de `oi_settle_date` (cierre cash) menos `spot` (cierre SPX
  de ese día). Ambos conocidos antes de la sesión D. nivel_ES = nivel_SPX + basis, redondeado al tick.
- Sesiones >= 2026-10-01 (holdout) se excluyen.

    .venv\Scripts\python tools\build_gex_viewer_layer.py
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
PARQUET = Path(r"E:\EdgeLab\data\nt8_reexport_20261005\ES\ES_09-26_ticks_ext.parquet")
AID = "ES_09-26_GEX"
BUNDLES = REPO / "viewer/nt8_bridge/bundles"
CSV_URL = "https://raw.githubusercontent.com/dhawalc/spx-gamma-levels/main/data/spx-gamma-levels.csv"
CT = ZoneInfo("America/Chicago")
TICK = 0.25
HOLDOUT = "2026-10-01"
LEVELS = [("call_wall", "CW"), ("put_wall", "PW"), ("zero_gamma_flip", "Flip"), ("vol_trigger", "VT")]


def candles(sec):
    q = f"""SELECT CAST((ts_utc_ns//1000000000) - ((ts_utc_ns//1000000000) % {sec}) AS BIGINT) t,
            FIRST(price_ticks ORDER BY ts_utc_ns)*{TICK}, MAX(price_ticks)*{TICK}, MIN(price_ticks)*{TICK},
            LAST(price_ticks ORDER BY ts_utc_ns)*{TICK}, CAST(SUM(volume) AS DOUBLE)
            FROM read_parquet('{PARQUET.as_posix()}') GROUP BY 1 ORDER BY 1"""
    return [dict(time=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]), volume=float(r[5])) for r in duckdb.query(q).fetchall()]


def main():
    raw = urllib.request.urlopen(CSV_URL, timeout=60).read().decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), dtype={"date": str, "oi_settle_date": str})
    df = df[df.date < HOLDOUT].sort_values("date")
    t = pq.read_table(PARQUET, columns=["ts_utc_ns", "price_ticks"])
    ts = t["ts_utc_ns"].to_numpy(); px = t["price_ticks"].to_numpy() * TICK
    out = []; skipped = []
    df["stale"] = df[["net_gex_dollars", "zero_gamma_flip", "call_wall", "put_wall"]].eq(
        df[["net_gex_dollars", "zero_gamma_flip", "call_wall", "put_wall"]].shift()).all(axis=1)
    for r in df.itertuples():
        if not isinstance(r.oi_settle_date, str) or r.stale:          # sin fecha de OI o copia del día anterior
            skipped.append(r.date); continue
        oi = datetime.strptime(r.oi_settle_date, "%Y-%m-%d")
        ref = datetime.combine(oi.date(), time(15, 0), CT).astimezone(timezone.utc)
        k = np.searchsorted(ts, int(ref.timestamp() * 1e9), side="right") - 1
        if k < 0 or (int(ref.timestamp() * 1e9) - ts[k]) > 15 * 60 * 10**9:    # sin tick ES cerca del cierre cash
            continue
        basis = float(px[k]) - float(r.spot)
        d = datetime.strptime(r.date, "%Y-%m-%d").date()
        avail = datetime.combine(d, time(13, 31), timezone.utc)
        end = datetime.combine(d, time(16, 0), CT).astimezone(timezone.utc)
        lv = []
        for col, lab in LEVELS:
            v = getattr(r, col)
            if pd.notna(v):
                lv.append(dict(id=col, label=lab, spx=float(v), price=round((float(v) + basis) / TICK) * TICK))
        out.append(dict(session=r.date, oi_settle_date=r.oi_settle_date, available_utc=int(avail.timestamp()),
                        end_utc=int(end.timestamp()), spx_spot=float(r.spot), es_ref=float(px[k]), basis=round(basis, 2),
                        regime=r.gamma_regime, net_gex_dollars=float(r.net_gex_dollars), levels=lv))
    (BUNDLES / "gex").mkdir(parents=True, exist_ok=True)
    meta = dict(source="SquawkFlow spx-gamma-levels (CC BY 4.0) https://github.com/dhawalc/spx-gamma-levels",
                causal_rule="sesion D: desde available_utc (D 13:31Z, publicacion) hasta 16:00 CT de D; basis = ES 15:00 CT del dia del OI - cierre SPX",
                warning="GEX naive (dealers largos calls / cortos puts, OI del cierre previo): modelo, no posicion; no ve 0DTE intradia",
                skipped_sessions=skipped, built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), holdout_excluded_from=HOLDOUT)
    (BUNDLES / "gex" / f"{AID}.json").write_text(json.dumps(dict(meta=meta, sessions=out)), encoding="utf-8")
    print("sesiones con niveles:", len(out), out[0]["session"] if out else None, "->", out[-1]["session"] if out else None)

    c1, c5 = candles(60), candles(300)
    bundle = dict(meta=dict(id=AID, name="ES 09-26 · GEX (1m / 5m)", instrument="ES", contract="ES 09-26", tick_size=TICK,
                            precision=2, n_zones=0),
                  bar_series=dict(time_1m=dict(kind="time_1m", name="1 Minuto", candles=c1),
                                  time_5m=dict(kind="time_5m", name="5 Minuto", candles=c5)), runs=[])
    (BUNDLES / f"{AID}.json").write_text(json.dumps(bundle), encoding="utf-8")
    man = BUNDLES / "manifest.js"; txt = man.read_text(encoding="utf-8")
    if f'"{AID}"' not in txt:
        entry = dict(id=AID, name="ES 09-26 · GEX (1m / 5m)", group="ES (GEX)", instrument="ES", contract="ES 09-26",
                     tick_size=TICK, precision=2, candles=len(c1), zones=0, rolls=0, parity_status="PARITY_ABSTAIN")
        i = txt.find("window.ASSET_CATALOG = [") + len("window.ASSET_CATALOG = [\n")
        man.write_text(txt[:i] + "  " + json.dumps(entry) + ",\n" + txt[i:], encoding="utf-8")
    print("bundle", AID, "1m", len(c1), "5m", len(c5))


if __name__ == "__main__":
    main()
