# Principal del kernel AREAS-EXP-1 (lo envuelve tools/kaggle_areas/construir_kernel.py con los módulos embebidos).
# Parámetros por variable de entorno: FUENTE = NQ | USATECH, MODO = E0 | DESC, DESDE/HASTA = YYYYMMDD, VR_CORTES = "a,b" (opcional).
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HOLDOUT_TD = 20261001                                   # copia de edgelab/holdout.py (verificada por tests/test_holdout_unico.py)
HOLDOUT_NS = 1_790_805_600_000_000_000
FUENTE = os.environ.get("FUENTE", "NQ"); MODO = os.environ.get("MODO", "E0")
DESDE = int(os.environ.get("DESDE", "20250805")); HASTA = int(os.environ.get("HASTA", "20260331"))
assert HASTA < HOLDOUT_TD, "la ventana toca el holdout"
FRICCION = 1.545; EXTRA_ADVERSO = 0.5                   # edgelab.costos NQ base / adverso - base (USATECH: referencia, no operable)


def _td(ns):
    t = pd.DatetimeIndex(pd.to_datetime(ns, unit="ns", utc=True)).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    return np.asarray(t.strftime("%Y%m%d"), dtype=np.int64)


def bloques_nq():
    f = glob.glob(os.environ.get("ENTRADA", "/kaggle/input") + "/**/NQ_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f)
    i_td = pf.schema_arrow.get_field_index("trade_date"); por_dia = {}
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(i_td).statistics
        if st.min < DESDE or st.max > HASTA: continue
        por_dia.setdefault(int(st.min), []).append(g)
    for td in sorted(por_dia):
        t = pf.read_row_groups(por_dia[td], columns=["ts_utc_ns", "price_ticks", "volume", "trade_date", "regime_id", "outside_regular"]).to_pandas()
        t = t[(~t.outside_regular) & (t.ts_utc_ns < HOLDOUT_NS)].sort_values("ts_utc_ns", kind="stable")
        yield pd.DataFrame(dict(ts_ns=t.ts_utc_ns.to_numpy(), px=t.price_ticks.to_numpy() * 0.25, vol=t.volume.to_numpy(float),
                                sesion=t.trade_date.to_numpy(np.int64), segmento=t.regime_id.to_numpy(np.int64)))


def bloques_usatech():
    f = glob.glob(os.environ.get("ENTRADA", "/kaggle/input") + "/**/USATECHIDXUSD_ticks.parquet", recursive=True)[0]; pf = pq.ParquetFile(f)
    lo = pd.Timestamp(str(DESDE), tz="America/Chicago").value - 8 * 3600 * 10**9; hi = min(pd.Timestamp(str(HASTA), tz="America/Chicago").value + 17 * 3600 * 10**9, HOLDOUT_NS)
    resto = None
    for g in range(pf.num_row_groups):
        st = pf.metadata.row_group(g).column(0).statistics
        if st.max < lo or st.min >= hi: continue
        t = pf.read_row_group(g).to_pandas(); t = t[(t.time_utc_ns >= lo) & (t.time_utc_ns < hi)]
        if resto is not None: t = pd.concat([resto, t])
        if not len(t): continue
        td = _td(t.time_utc_ns.to_numpy()); ult = td.max()
        listo = td < ult; resto = t[~listo]
        yield from _usatech_df(t[listo], td[listo])
    if resto is not None and len(resto): yield from _usatech_df(resto, _td(resto.time_utc_ns.to_numpy()))


def _usatech_df(t, td):
    keep = (td >= DESDE) & (td <= HASTA)
    t, td = t[keep], td[keep]
    if not len(t): return
    mid = np.round(((t.bid.to_numpy() + t.ask.to_numpy()) / 2) / 0.01) * 0.01
    for d in np.unique(td):
        m = td == d
        yield pd.DataFrame(dict(ts_ns=t.time_utc_ns.to_numpy()[m], px=mid[m], vol=(t.bid_vol.to_numpy() + t.ask_vol.to_numpy())[m].astype(float),
                                sesion=np.full(m.sum(), d, np.int64), segmento=np.zeros(m.sum(), np.int64)))


def main():
    from edgelab.research import areas_expansion_run as R
    t0 = time.time(); log = lambda s: print(f"[{time.time() - t0:7.0f}s] {s}", flush=True)
    vr = [float(x) for x in os.environ["VR_CORTES"].split(",")] if os.environ.get("VR_CORTES") else None
    cc = [float(x) for x in os.environ["COM_CORTES"].split(",")] if os.environ.get("COM_CORTES") else None
    celdas = json.loads(os.environ["CELDAS"]) if os.environ.get("CELDAS") else None          # REP: celdas congeladas
    cfg = dict(NQ=dict(b=bloques_nq, G=1.0, tick=0.25), USATECH=dict(b=bloques_usatech, G=1.0, tick=0.01))[FUENTE]
    res, ctx = R.correr(cfg["b"](), modo=MODO, G=cfg["G"], tick=cfg["tick"], friccion=FRICCION, extra_adverso=EXTRA_ADVERSO, vr_cortes=vr, com_cortes=cc, celdas=celdas, log=log)
    res.update(fuente=FUENTE, desde=DESDE, hasta=HASTA, friccion_pts=FRICCION, codigo=CODIGO_SHA)
    json.dump(res, open(f"AREAS_{FUENTE}_{MODO}.json", "w"), indent=1, default=float)
    D = ctx if MODO == "E0" else ctx["D"]
    D.drop(columns=[], errors="ignore").to_parquet(f"AREAS_{FUENTE}_disparos.parquet")       # target-free: disparos y variables
    log(json.dumps({k: v for k, v in res.items() if k in ("E0", "celdas", "evaluables", "nominadas", "ambiguedad_M1", "a_replica", "replica")}, default=float)[:4000])


main()
