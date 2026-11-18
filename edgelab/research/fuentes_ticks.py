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


# M1 de Dukascopy (CFD, 2003/2012 → 2026-09-29) exportadas de SQX: dataset privado `edgelab-sqx-m1` (2026-11-15). Cada símbolo se mide
# con el tick y los costos del futuro equivalente (precios de la misma escala).
M1DK_FUTURO = {"NQ_M1_dukas": "NQ", "SP_M1_dukas": "ES", "DJ_M1_dukas": "YM", "USSC2000IDXUSD": "RTY", "XAUUSD_M1_dukas": "GC"}
M1DK_DATASET = "nicolasbuttaro/edgelab-sqx-m1"
SERVIDOR_MENOS_NY_H = 7                                          # hora del servidor de datos de SQX (EST+07, sigue el horario de NY)
M1_EN_UTC = ("USSC2000IDXUSD", "DEUIDXEUR", "EUSIDXEUR", "GBRIDXGBP", "JPNIDXJPY", "LIGHTCMDUSD",
          "AUDUSD", "BRENTCMDUSD", "BUNDTREUR", "COPPERCMDUSD", "DOLLARIDXUSD", "GASCMDUSD", "NZDUSD", "UKGILTTRGBP", "USDCAD",
          "USTBONDTRUSD", "XAGUSD")      # 2026-11-17: confirmado en SQX (list_data) por Antigravity   # 2026-11-16: = m1_intradia.EN_UTC (test)


def bloques_m1dk(simbolo, desde, hasta, entrada="/kaggle/input"):
    """M1 de Dukascopy como ticks: 4 por barra (apertura; mínimo y máximo en el orden conservador —si la vela cierra al alza, primero el
    mínimo; si cierra a la baja, primero el máximo—; cierre) a +0/15/30/45 s, volumen repartido. Sesión CME (desde las 18:00 de NY es el
    día siguiente). Precio redondeado al tick del futuro equivalente. Nunca entrega nada desde la apertura del holdout."""
    _check(desde, hasta)
    f = sorted(glob.glob(entrada + f"/**/{simbolo}-M1-*.csv", recursive=True))[0]; tk = TICK_FUTURO[M1DK_FUTURO[simbolo]]
    D = pd.read_csv(f, dtype={"Date": str, "Time": str})
    raw = pd.to_datetime(D.Date + " " + D.Time, format="%Y%m%d %H:%M:%S")
    if simbolo.startswith(M1_EN_UTC): ny = raw.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None)   # 2026-11-16
    elif "_M1_dukas" in simbolo: ny = raw - pd.Timedelta(hours=SERVIDOR_MENOS_NY_H)
    else: raise ValueError(f"{simbolo}: zona horaria del M1 no declarada")
    utc = ny.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    ok = utc.notna().to_numpy(); D, ny, utc = D[ok], ny[ok], utc[ok]
    td = (ny + pd.Timedelta(hours=6)).dt.strftime("%Y%m%d").astype(np.int64).to_numpy()   # 18:00 NY → sesión del día siguiente
    t0 = utc.dt.tz_convert(None).astype("datetime64[ns]").astype(np.int64).to_numpy()
    ok = pd.to_datetime(td.astype(str), format="%Y%m%d").dayofweek.to_numpy() < 5           # sin sesiones de fin de semana
    D, td, t0 = D[ok], td[ok], t0[ok]
    o, h, l, c, v = (D[k].to_numpy(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    sube = c >= o
    p1 = np.where(sube, l, h); p2 = np.where(sube, h, l)
    for d in np.unique(td[(td >= desde) & (td <= hasta)]):
        m = np.flatnonzero(td == d)
        ts = (t0[m][:, None] + np.array([0, 15, 30, 45]) * 1_000_000_000).ravel()
        px = np.column_stack([o[m], p1[m], p2[m], c[m]]).ravel(); px = np.round(px / tk) * tk
        vv = np.repeat(v[m] / 4.0, 4); keep = ts < HOLDOUT_APERTURA_UTC_NS
        yield pd.DataFrame(dict(ts_ns=ts[keep], px=px[keep], vol=vv[keep], sesion=np.full(int(keep.sum()), int(d), np.int64),
                                segmento=np.zeros(int(keep.sum()), np.int64), sintetico=np.ones(int(keep.sum()), np.bool_)))   # K40


# M1 REAL de futuros CME exportado de NinjaTrader 8 (2026-11-17, dataset privado `edgelab-nt8-m1-futuros`): NQ/ES/YM desde 2006-01, GC
# desde 2008-01; MergeNonBackAdjusted (precios reales), índice `datetime` = APERTURA de la vela en UTC (manifest.json). El archivo llega
# hasta la fecha del export, holdout incluido: este lector corta SIEMPRE en la frontera única (nunca entrega nada desde su apertura).
M1NT8_DATASET = "nicolasbuttaro/edgelab-nt8-m1-futuros"
M1NT8_INSTRUMENTOS = ("NQ", "ES", "YM", "GC", "EMD", "RTY")             # EMD y RTY: subidos por Nico el 2026-11-17 (m1_largo, índices)
TICK_M1NT8_EXTRA = {"EMD": 0.1}                                            # fuera del catálogo de ticks del release (RESOLVER.json)


def _velas_a_ticks(t0, o, h, l, c, v, td, desde, hasta, tk):
    """4 ticks por vela (apertura; mínimo y máximo en el orden conservador; cierre) a +0/15/30/45 s: la misma convención calibrada de
    `bloques_m1dk` (papel_m1_20261115/VALIDACION.md)."""
    sube = c >= o; p1 = np.where(sube, l, h); p2 = np.where(sube, h, l)
    for d in np.unique(td[(td >= desde) & (td <= hasta)]):
        m = np.flatnonzero(td == d)
        ts = (t0[m][:, None] + np.array([0, 15, 30, 45]) * 1_000_000_000).ravel()
        px = np.column_stack([o[m], p1[m], p2[m], c[m]]).ravel(); px = np.round(px / tk) * tk
        vv = np.repeat(v[m] / 4.0, 4); keep = ts < HOLDOUT_APERTURA_UTC_NS
        if keep.any():
            yield pd.DataFrame(dict(ts_ns=ts[keep], px=px[keep], vol=vv[keep], sesion=np.full(int(keep.sum()), int(d), np.int64),
                                    segmento=np.zeros(int(keep.sum()), np.int64), sintetico=np.ones(int(keep.sum()), np.bool_)))   # K40


def bloques_m1nt8(simbolo, desde, hasta, entrada="/kaggle/input"):
    """M1 de futuros de NT8 como ticks (misma convención que `bloques_m1dk`). Sesión CME: desde las 18:00 de NY es el día siguiente.
    Doble corte del holdout: `_check` sobre la ventana pedida y descarte de toda vela con apertura >= HOLDOUT_APERTURA_UTC_NS."""
    import pyarrow.parquet as pq
    _check(desde, hasta)
    if simbolo not in M1NT8_INSTRUMENTOS: raise ValueError(f"{simbolo}: sin M1 de NT8")
    fs = sorted(glob.glob(entrada + f"/**/{simbolo}_M1_nonadj_utc.parquet", recursive=True))
    if not fs: raise FileNotFoundError(f"sin {simbolo}_M1_nonadj_utc.parquet en {entrada}: ¿se lanzó con la cuenta dueña de {M1NT8_DATASET}?")
    D = pq.read_table(fs[0]).to_pandas()
    t0 = (D.index.to_numpy() if "datetime" not in D else D["datetime"].to_numpy()).astype("datetime64[ns]").astype(np.int64)
    ok = t0 < HOLDOUT_APERTURA_UTC_NS; D, t0 = D[ok], t0[ok]
    ny = pd.to_datetime(t0).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
    td = (ny + pd.Timedelta(hours=6)).strftime("%Y%m%d").astype(np.int64).to_numpy()
    ok = pd.to_datetime(td.astype(str), format="%Y%m%d").dayofweek.to_numpy() < 5
    D, t0, td = D[ok], t0[ok], td[ok]
    yield from _velas_a_ticks(t0, *(D[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume")), td, desde, hasta,
                              TICK_FUTURO.get(simbolo) or TICK_M1NT8_EXTRA[simbolo])


def resolver(nombre: str, libro: bool = False):
    """'NQ' -> futuro del release; 'DK:USATECHIDXUSD' -> spot de Dukascopy. Devuelve (lector(desde, hasta, entrada), tick).
    `libro=True` (módulos con `LIBRO = True`, p. ej. DeltaSweep): los futuros traen bid/ask para clasificar el agresor."""
    if nombre.startswith("M1NT8:"):
        sym = nombre[6:]
        return (lambda d0, d1, e="/kaggle/input": bloques_m1nt8(sym, d0, d1, e)), TICK_FUTURO.get(sym) or TICK_M1NT8_EXTRA[sym]
    if nombre.startswith("M1DK:"):
        sym = nombre[5:]
        return (lambda d0, d1, e="/kaggle/input": bloques_m1dk(sym, d0, d1, e)), TICK_FUTURO[M1DK_FUTURO[sym]]
    if nombre.startswith("DK:"):
        sym = nombre[3:]
        return (lambda d0, d1, e="/kaggle/input": bloques_dukascopy(sym, d0, d1, e)), REDONDEO_SPOT[sym]
    return (lambda d0, d1, e="/kaggle/input": bloques_futuro(nombre, d0, d1, e, libro=libro)), TICK_FUTURO[nombre]


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
    from edgelab.holdout import sesion_excluida
    inst = (str(t.contract.iloc[0]).split()[0].split("_")[0] if "contract" in t and len(t) else
            Path(ruta[0] if isinstance(ruta, (list, tuple)) else ruta).name.split("_")[0])
    for td, g in t.groupby("trade_date", sort=True):
        if sesion_excluida(inst, td): continue                          # 2026-11-02: sesiones incompletas declaradas (holdout.py)
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
    from edgelab.holdout import sesion_excluida
    td = _td(t.time_utc_ns.to_numpy()); fuera = np.array([sesion_excluida(simbolo, d) for d in td], bool)   # 2026-11-02: declaradas
    yield from _spot_df(t[~fuera], td[~fuera], desde, hasta, red)
