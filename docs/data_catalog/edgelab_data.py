"""edgelab_data — ÚNICA puerta de entrada a los datos de EdgeLab en Kaggle (o local).

Uso (notebook de Kaggle con el dataset `edgelab-data-catalog` y los datasets de ticks agregados como input):
    import sys; sys.path.insert(0, '/kaggle/input/edgelab-data-catalog')
    import edgelab_data as ed
    ed.sessions('MNQ')                                  # tabla de sesiones aprobadas (fecha, contrato, dataset, archivo)
    df = ed.load_ticks('MNQ', '2026-01-01', '2026-09-30')  # sólo sesiones aprobadas, serie líder, sin holdout
    m1 = ed.load_m1('MNQ', '2026-01-01', '2026-09-30')     # barras M1 construidas desde esos mismos ticks

Reglas que este módulo hace cumplir (no las saltees leyendo parquets a mano):
- Una respuesta por sesión: dataset/archivo/contrato salen de RESOLVER.json (serie líder, prioridad de fuente fija).
- Sesiones no aprobadas (liquidez baja, truncadas) se excluyen salvo include_rejected=True, y siempre se informan.
- Holdout: nada con fecha de sesión >= 2026-10-01; pedirlo es un error.
- Spot Dukascopy NO se mezcla con futuros: ver RESOLVER['spot_complement'].
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
RESOLVER = json.loads((HERE / "RESOLVER.json").read_text(encoding="utf-8"))
HOLDOUT = RESOLVER["holdout_first_trade_date"]
ROOTS = [Path(p) for p in os.environ.get("EDGELAB_DATA_ROOTS", "/kaggle/input").split(os.pathsep)]
CT = "America/Chicago"


def _check(start, end):
    if end >= HOLDOUT or start >= HOLDOUT:
        raise ValueError(f"holdout: no se leen sesiones desde {HOLDOUT}")


def sessions(inst: str, start: str = "1900-01-01", end: str = "2026-09-30", include_rejected: bool = False) -> pd.DataFrame:
    _check(start, end)
    s = pd.DataFrame(RESOLVER["instruments"][inst]["sessions"])
    s = s[(s.date >= start) & (s.date <= end)]
    return s if include_rejected else s[s.approved]


def _path(dataset: str, file: str) -> Path:
    for r in ROOTS:
        for cand in (r / dataset / file, *(r / dataset).glob(f"**/{Path(file).name}")):
            if cand.exists():
                return cand
    raise FileNotFoundError(f"agregá el dataset '{dataset}' como input (falta {file}); raíces: {ROOTS}")


def _session_date(ts_ns: np.ndarray) -> np.ndarray:
    """Fecha de sesión CME (17:00-16:00 CT), idéntica a la del catálogo (edgelab.discovery.data.tdate_ordinal):
    se etiqueta por el fin del minuto, se corre 1 ns atrás y se suman 7 h en hora de Chicago."""
    lab = (np.asarray(ts_ns) // 60_000_000_000 + 1) * 60_000_000_000 - 1
    ix = pd.to_datetime(lab, unit="ns", utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    return ix.strftime("%Y-%m-%d").to_numpy()


def load_ticks(inst: str, start: str, end: str, columns=None, include_rejected: bool = False) -> pd.DataFrame:
    """Ticks de las sesiones aprobadas, leyendo de cada archivo SOLO las sesiones que el resolver le asigna."""
    s = sessions(inst, start, end, include_rejected)
    if columns is not None and "ts_utc_ns" not in columns:
        columns = ["ts_utc_ns", *columns]
    out = []
    for (ds, fl), g in s.groupby(["dataset", "file"]):
        want = set(g.date)
        pf = pq.ParquetFile(_path(ds, fl))
        # rango UTC que cubre las sesiones pedidas (sesión d = d-1 17:00 CT .. d 16:00 CT; margen de 1 día)
        lo = pd.Timestamp(min(want)).tz_localize("UTC").value - 2 * 86_400 * 10**9
        hi = pd.Timestamp(max(want)).tz_localize("UTC").value + 2 * 86_400 * 10**9
        icol = pf.schema_arrow.get_field_index("ts_utc_ns")
        for i in range(pf.num_row_groups):
            st = pf.metadata.row_group(i).column(icol).statistics
            if st is not None and st.has_min_max and (st.max < lo or st.min > hi):
                continue
            t = pf.read_row_group(i, columns=columns).to_pandas()
            if not len(t):
                continue
            sd = _session_date(t["ts_utc_ns"].to_numpy())
            m = np.isin(sd, list(want))
            if m.any():
                t = t[m].copy(); t["session_date"] = sd[m]; out.append(t)
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True).sort_values("ts_utc_ns", kind="stable").reset_index(drop=True)
    tick = RESOLVER["instruments"][inst]["tick_size"]
    df.attrs.update(instrument=inst, tick_size=tick, holdout=HOLDOUT)
    return df


def load_m1(inst: str, start: str, end: str, include_rejected: bool = False) -> pd.DataFrame:
    """Barras M1 (inicio de minuto, UTC) desde load_ticks: OHLC en ticks de precio, volumen, trades, compra/venta agresora."""
    t = load_ticks(inst, start, end, ["ts_utc_ns", "price_ticks", "volume", "aggressor", "contract"], include_rejected)
    if t.empty:
        return t
    t["minute"] = (t.ts_utc_ns // 60_000_000_000) * 60_000_000_000
    g = t.groupby(["session_date", "minute"], sort=True)
    m1 = g.agg(open=("price_ticks", "first"), high=("price_ticks", "max"), low=("price_ticks", "min"),
               close=("price_ticks", "last"), volume=("volume", "sum"), trades=("price_ticks", "size"),
               contract=("contract", "first")).reset_index()
    buy = t[t.aggressor == "buy"].groupby(["session_date", "minute"]).volume.sum()
    m1["buy_volume"] = m1.set_index(["session_date", "minute"]).index.map(buy).fillna(0).to_numpy()
    m1.attrs.update(instrument=inst, tick_size=t.attrs["tick_size"], units="price_ticks")
    return m1


def load_spot(inst: str, start: str, end: str, kind: str = "m1") -> pd.DataFrame:
    """Spot/CFD Dukascopy hermano del futuro `inst` (kind='m1' o 'ticks'). SOLO para potencia en pruebas de información;
    ver RESOLVER['spot_complement']. Aplica las exclusiones del proveedor y bloquea el holdout. Fechas en UTC."""
    _check(start, end)
    ds = RESOLVER["spot_datasets"][inst]
    files = [p for p in (r / ds for r in ROOTS) if p.exists()]
    if not files:
        raise FileNotFoundError(f"agregá el dataset '{ds}' como input")
    f = next(files[0].glob(f"*_{'m1' if kind == 'm1' else 'ticks'}.parquet"))
    lo = pd.Timestamp(start, tz="UTC").value; hi = pd.Timestamp(end, tz="UTC").value + 86_400 * 10**9
    t = pq.read_table(f, filters=[("time_utc_ns", ">=", lo), ("time_utc_ns", "<", hi)]).to_pandas()
    for x in RESOLVER["spot_exclusions"]:
        if ds in x["datasets"]:
            a, b = pd.Timestamp(x["from_utc"]).value, pd.Timestamp(x["to_utc"]).value
            t = t[(t.time_utc_ns < a) | (t.time_utc_ns >= b)]
    t.attrs.update(instrument=inst, spot_dataset=ds, warning=RESOLVER["spot_complement"])
    return t.reset_index(drop=True)
