"""Lectores de ticks para kernels de Kaggle (compartidos por todos los experimentos de grilla; antes vivían dentro de areas_main).

Cada lector devuelve bloques de un día de trading completo (DataFrame ts_ns, px, vol, sesion, segmento), en orden, sin nada
del holdout (frontera única de `edgelab/holdout.py`). Para sumar una fuente: una función más con la misma salida y una
entrada en FUENTES (tick y fricción salen de edgelab/costos.py cuando el instrumento es operable).
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, HOLDOUT_PRIMERA_SESION_INT


def _td(ns):
    t = pd.DatetimeIndex(pd.to_datetime(ns, unit="ns", utc=True)).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    return np.asarray(t.strftime("%Y%m%d"), dtype=np.int64)


def _check(desde, hasta):
    if hasta >= HOLDOUT_PRIMERA_SESION_INT or desde >= HOLDOUT_PRIMERA_SESION_INT: raise ValueError("la ventana toca el holdout")


def bloques_nq(desde, hasta, entrada="/kaggle/input"):
    import pyarrow.parquet as pq
    _check(desde, hasta)
    f = glob.glob(entrada + "/**/NQ_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f)
    i_td = pf.schema_arrow.get_field_index("trade_date"); por_dia = {}
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(i_td).statistics
        if st.min < desde or st.max > hasta: continue
        por_dia.setdefault(int(st.min), []).append(g)
    for td in sorted(por_dia):
        t = pf.read_row_groups(por_dia[td], columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "regime_id", "outside_regular"]).to_pandas()
        t = t[(~t.outside_regular) & (t.ts_utc_ns < HOLDOUT_APERTURA_UTC_NS)].sort_values("ts_utc_ns", kind="stable")
        yield pd.DataFrame(dict(ts_ns=t.ts_utc_ns.to_numpy(), px=t.price_ticks.to_numpy() * 0.25, vol=t.volume.to_numpy(float),
                                sesion=t.trade_date.to_numpy(np.int64), segmento=t.regime_id.to_numpy(np.int64)))


def bloques_usatech(desde, hasta, entrada="/kaggle/input"):
    import pyarrow.parquet as pq
    _check(desde, hasta)
    f = glob.glob(entrada + "/**/USATECHIDXUSD_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f)
    lo = pd.Timestamp(str(desde), tz="America/Chicago").value - 8 * 3600 * 10**9
    hi = min(pd.Timestamp(str(hasta), tz="America/Chicago").value + 17 * 3600 * 10**9, HOLDOUT_APERTURA_UTC_NS)
    resto = None
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(0).statistics
        if st.max < lo or st.min >= hi: continue
        t = pf.read_row_group(g).to_pandas(); t = t[(t.time_utc_ns >= lo) & (t.time_utc_ns < hi)]
        if resto is not None: t = pd.concat([resto, t])
        if not len(t): continue
        td = _td(t.time_utc_ns.to_numpy()); ult = td.max(); listo = td < ult; resto = t[~listo]
        yield from _usatech_df(t[listo], td[listo], desde, hasta)
    if resto is not None and len(resto): yield from _usatech_df(resto, _td(resto.time_utc_ns.to_numpy()), desde, hasta)


def _usatech_df(t, td, desde, hasta):
    keep = (td >= desde) & (td <= hasta); t, td = t[keep], td[keep]
    if not len(t): return
    mid = np.round(((t.bid.to_numpy() + t.ask.to_numpy()) / 2) / 0.01) * 0.01
    for d in np.unique(td):
        m = td == d
        yield pd.DataFrame(dict(ts_ns=t.time_utc_ns.to_numpy()[m], px=mid[m], vol=(t.bid_vol.to_numpy() + t.ask_vol.to_numpy())[m].astype(float),
                                sesion=np.full(m.sum(), d, np.int64), segmento=np.zeros(m.sum(), np.int64)))


# fuente -> (lector, tick, fricción por operación en puntos, adverso extra). NQ: edgelab.costos base/adverso. USATECH: CFD,
# referencia con los costos de NQ (no operable tal cual).
FUENTES = {"NQ": (bloques_nq, 0.25, 1.5455, 0.5), "USATECH": (bloques_usatech, 0.01, 1.5455, 0.5)}   # tests/research/test_fuentes_ticks.py: = edgelab.costos
