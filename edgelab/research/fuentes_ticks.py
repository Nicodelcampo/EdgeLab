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


def _td_lento(ns):
    """Referencia (oráculo de `_td`): conversión tick por tick."""
    t = pd.DatetimeIndex(pd.to_datetime(ns, unit="ns", utc=True)).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    return np.asarray(t.strftime("%Y%m%d"), dtype=np.int64)


def _td(ns):
    """Trade date CME (YYYYMMDD) por instante: fecha de Chicago + 7 h. Se convierte una vez por HORA única (el corrimiento de
    Chicago cambia sólo en horas enteras) y se expande: mismo resultado que `_td_lento`, sin strftime por tick (era el 80 % del
    tiempo de carga de los kernels de Dukascopy, medido 2026-10-25)."""
    ns = np.asarray(ns, dtype=np.int64)
    if not len(ns): return np.zeros(0, np.int64)
    uh, inv = np.unique(ns // 3_600_000_000_000, return_inverse=True)
    return _td_lento(uh * 3_600_000_000_000)[inv]


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


def _por_dia(ts, px, vol, td):
    """Un bloque por trade date, en orden. `td` no decrece (los ticks vienen en orden de tiempo), así que cada día es un tramo
    contiguo: se corta por los bordes en vez de una máscara sobre todo el arreglo por día. Si no viniera ordenado, se ordena estable
    por `td` (mismo resultado que la máscara)."""
    if len(td) > 1 and (np.diff(td) < 0).any():
        o = np.argsort(td, kind="stable"); ts, px, vol, td = ts[o], px[o], vol[o], td[o]
    cortes = np.flatnonzero(np.diff(td)) + 1; ini = np.r_[0, cortes]; fin = np.r_[cortes, len(td)]
    for a, b in zip(ini, fin):
        yield pd.DataFrame(dict(ts_ns=ts[a:b], px=px[a:b], vol=vol[a:b], sesion=np.full(b - a, td[a], np.int64), segmento=np.zeros(b - a, np.int64)))


def _usatech_df(t, td, desde, hasta):
    keep = (td >= desde) & (td <= hasta); t, td = t[keep], td[keep]
    if not len(t): return
    mid = np.round(((t.bid.to_numpy() + t.ask.to_numpy()) / 2) / 0.01) * 0.01
    yield from _por_dia(t.time_utc_ns.to_numpy(), mid, (t.bid_vol.to_numpy() + t.ask_vol.to_numpy()).astype(float), td)


# --- genéricos (2026-10-23): cualquier futuro del release y cualquier spot de Dukascopy ------------------------------------
DUKASCOPY = {"NQ": "USATECHIDXUSD", "MNQ": "USATECHIDXUSD", "ES": "USA500IDXUSD", "MES": "USA500IDXUSD", "YM": "USA30IDXUSD", "MYM": "USA30IDXUSD",
             "GC": "XAUUSD", "MGC": "XAUUSD", "6E": "EURUSD", "6B": "GBPUSD", "6J": "USDJPY"}
REDONDEO_SPOT = {"USATECHIDXUSD": 0.01, "USA500IDXUSD": 0.01, "USA30IDXUSD": 0.01, "XAUUSD": 0.001, "EURUSD": 0.00001, "GBPUSD": 0.00001, "USDJPY": 0.001}
TICK_FUTURO = {"6B": 0.0001, "6E": 0.00005, "6J": 0.0000005, "ES": 0.25, "GC": 0.1, "MBT": 5.0, "MES": 0.25, "MGC": 0.1, "MNQ": 0.25, "MYM": 1.0,
               "NQ": 0.25, "RTY": 0.1, "YM": 1.0, "ZB": 0.03125}      # = RESOLVER.json (test)


def bloques_futuro(inst, desde, hasta, entrada="/kaggle/input", libro=False):
    """Cualquier futuro del release (`<INST>_ticks.parquet`, mismo esquema que NQ): un bloque por trade_date, sin fuera de horario.
    `libro=True` agrega bid/ask (precio; NaN si el quote es inválido) para los indicadores que clasifican el agresor (BigTrap2)."""
    import pyarrow.parquet as pq
    _check(desde, hasta)
    f = glob.glob(entrada + f"/**/{inst}_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f); tk = TICK_FUTURO[inst]
    i_td = pf.schema_arrow.get_field_index("trade_date"); por_dia = {}
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(i_td).statistics
        if st.min < desde or st.max > hasta: continue
        por_dia.setdefault(int(st.min), []).append(g)
    for td in sorted(por_dia):
        t = pf.read_row_groups(por_dia[td], columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "regime_id", "outside_regular"]
                               + (["bid_ticks", "ask_ticks"] if libro else [])).to_pandas()
        t = t[(~t.outside_regular) & (t.ts_utc_ns < HOLDOUT_APERTURA_UTC_NS)].sort_values("ts_utc_ns", kind="stable")
        d = dict(ts_ns=t.ts_utc_ns.to_numpy(), px=t.price_ticks.to_numpy() * tk, vol=t.volume.to_numpy(float),
                 sesion=t.trade_date.to_numpy(np.int64), segmento=t.regime_id.to_numpy(np.int64))
        if libro:
            b, a = t.bid_ticks.to_numpy(float), t.ask_ticks.to_numpy(float); ok = (b > 0) & (a >= b)
            d.update(bid=np.where(ok, b * tk, np.nan), ask=np.where(ok, a * tk, np.nan))
        yield pd.DataFrame(d)


def bloques_dukascopy(simbolo, desde, hasta, entrada="/kaggle/input"):
    """Cualquier spot de Dukascopy (`<SIMBOLO>_ticks.parquet`: time_utc_ns, bid, ask, bid_vol, ask_vol): mid redondeado, sesión CME."""
    import pyarrow.parquet as pq
    _check(desde, hasta)
    f = glob.glob(entrada + f"/**/{simbolo}_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f); red = REDONDEO_SPOT[simbolo]
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
        yield from _spot_df(t[listo], td[listo], desde, hasta, red)
    if resto is not None and len(resto): yield from _spot_df(resto, _td(resto.time_utc_ns.to_numpy()), desde, hasta, red)


def _spot_df(t, td, desde, hasta, red):
    keep = (td >= desde) & (td <= hasta); t, td = t[keep], td[keep]
    if not len(t): return
    mid = np.round(((t.bid.to_numpy() + t.ask.to_numpy()) / 2) / red) * red
    ts, vol = t.time_utc_ns.to_numpy(), (t.bid_vol.to_numpy() + t.ask_vol.to_numpy()).astype(float)
    yield from _por_dia(ts, mid, vol, td)


def resolver(nombre: str):
    """'NQ' -> futuro del release; 'DK:USATECHIDXUSD' -> spot de Dukascopy. Devuelve (lector(desde, hasta, entrada), tick)."""
    if nombre.startswith("DK:"):
        sym = nombre[3:]
        return (lambda d0, d1, e="/kaggle/input": bloques_dukascopy(sym, d0, d1, e)), REDONDEO_SPOT[sym]
    return (lambda d0, d1, e="/kaggle/input": bloques_futuro(nombre, d0, d1, e)), TICK_FUTURO[nombre]


# fuente -> (lector, tick, fricción por operación en puntos, adverso extra). NQ: edgelab.costos base/adverso. USATECH: CFD,
# referencia con los costos de NQ (no operable tal cual).
FUENTES = {"NQ": (bloques_nq, 0.25, 1.5455, 0.5), "USATECH": (bloques_usatech, 0.01, 1.5455, 0.5)}   # tests/research/test_fuentes_ticks.py: = edgelab.costos


def _leer_sellado_futuro(ruta):
    """Un parquet o una lista (2026-11-01: el logger de NT8 sube un archivo por día, `<INST>_<yyyymmdd>_ticks.parquet`, junto a los
    exports por contrato). Si una sesión está en varios archivos, manda el diario más nuevo: nunca se suman dos copias de un día."""
    import re
    import pyarrow.parquet as pq
    rutas = [ruta] if isinstance(ruta, (str, bytes)) or not hasattr(ruta, "__iter__") else list(ruta)
    rutas = sorted(map(str, rutas), key=lambda r: (bool(re.search(r"_\d{8}_ticks\.parquet$", r)), r))
    partes, vistos = [], set()
    for r in reversed(rutas):
        t = pq.read_table(r, columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "contract"]).to_pandas()
        t = t[~t.trade_date.isin(vistos)]; vistos |= set(t.trade_date.unique().tolist()); partes.append(t)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "contract"])


def bloques_nq_sellado(desde, hasta, ruta, acta, tick: float = 0.25):
    """Ticks del HOLDOUT (sesiones >= 2026-10-01) desde la carpeta sellada local. Sólo para una apertura registrada: exige la
    ruta de un acta de apertura committeada ANTES de correr y no entrega nada anterior a la frontera (no mezcla desarrollo).
    No está en FUENTES a propósito: nunca se usa por accidente."""
    from pathlib import Path
    import pyarrow.parquet as pq
    if not acta or not Path(acta).exists(): raise ValueError("apertura del holdout sin acta registrada")
    if desde < HOLDOUT_PRIMERA_SESION_INT: raise ValueError("una apertura del holdout no mezcla sesiones de desarrollo")
    t = _leer_sellado_futuro(ruta)
    t = t[(t.trade_date >= desde) & (t.trade_date <= hasta) & (t.ts_utc_ns >= HOLDOUT_APERTURA_UTC_NS)]
    contratos = {c: i for i, c in enumerate(sorted(t.contract.unique()))}
    for td, g in t.groupby("trade_date", sort=True):
        g = g.sort_values("ts_utc_ns", kind="stable")
        yield pd.DataFrame(dict(ts_ns=g.ts_utc_ns.to_numpy(), px=g.price_ticks.to_numpy() * float(tick), vol=g.volume.to_numpy(float),
                                sesion=np.full(len(g), int(td), np.int64), segmento=g.contract.map(contratos).to_numpy(np.int64)))


def bloques_spot_sellado(simbolo, desde, hasta, raiz):
    """Spot del HOLDOUT desde la carpeta sellada de la máquina: parquet diarios de tools/dukascopy_descarga.py (<raiz>/<SIM>/*.parquet)
    o binarios de la estrategia HD_NQ de JForex (<raiz>/<SIM>/ticks/*.bin). Sólo sesiones >= la frontera; nunca suben a Kaggle."""
    from pathlib import Path
    if desde < HOLDOUT_PRIMERA_SESION_INT: raise ValueError("una apertura del holdout no mezcla sesiones de desarrollo")
    base = Path(raiz) / simbolo; red = REDONDEO_SPOT[simbolo]; partes = []
    plano = Path(raiz) / f"{simbolo}_ticks.parquet"                      # dataset de Kaggle (aplana carpetas): un parquet por símbolo
    if plano.exists(): partes.append(pd.read_parquet(plano))
    for f in ([] if partes else sorted(base.glob("*.parquet"))): partes.append(pd.read_parquet(f))
    if not partes and (base / "ticks").exists():
        dt_ = np.dtype([("ms", ">i8"), ("bid", ">f8"), ("ask", ">f8"), ("bv", ">f4"), ("av", ">f4")])
        for f in sorted((base / "ticks").glob("*.bin")):
            a = np.fromfile(f, dtype=dt_)
            partes.append(pd.DataFrame(dict(time_utc_ns=a["ms"].astype(np.int64) * 1_000_000, bid=a["bid"], ask=a["ask"], bid_vol=a["bv"].astype(float), ask_vol=a["av"].astype(float))))
    if not partes: return
    t = pd.concat(partes, ignore_index=True).sort_values("time_utc_ns", kind="stable")
    t = t[t.time_utc_ns >= HOLDOUT_APERTURA_UTC_NS]
    yield from _spot_df(t, _td(t.time_utc_ns.to_numpy()), desde, hasta, red)
