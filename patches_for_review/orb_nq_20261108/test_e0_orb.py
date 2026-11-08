"""E0 con parquet y ticks sintéticos; sin datos de mercado."""
import importlib.util
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

folder = Path(__file__).parent
sys.path.insert(0, str(folder))
spec = importlib.util.spec_from_file_location('e0_orb_draft', folder / 'e0_orb.py')
e0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(e0)


def ticks():
    times = pd.date_range('2026-03-10 08:50', periods=181, freq='min', tz='America/New_York').tz_convert('UTC').as_unit('ns').asi8
    n=len(times); price=np.full(n, 400, dtype=np.int64)
    price[41]=401; price[46]=404; price[56]=408; price[71]=412
    return pd.DataFrame(dict(ts_utc_ns=times, price_ticks=price, trade_date=np.full(n,20260310),
                             regime_id=np.zeros(n,dtype=int), outside_regular=np.zeros(n,dtype=bool)))


def test_e0_senales_solo():
    d=e0.resumen_sesion(ticks())
    assert list(d.duracion)==[5,15,30]
    assert list(d.lado)==[1,1,1]
    assert set(d.columns)=={'k','ses','duracion','lado','hi','lo','dia','hora','atr14'}


def test_rechaza_mezcla_sesiones():
    b=ticks(); b.loc[1,'trade_date']=20260311
    with pytest.raises(ValueError, match='una sola sesión'): e0.resumen_sesion(b)


def test_rechaza_fecha_holdout_sintetica():
    b=ticks(); b['trade_date']=20261001
    with pytest.raises(ValueError, match='holdout'): e0.resumen_sesion(b)


def test_rechaza_dos_segmentos_mismo_minuto():
    b=ticks(); row=b.iloc[[10]].copy(); row['ts_utc_ns']+=1; row['regime_id']=1
    with pytest.raises(ValueError, match='dos segmentos'): e0.resumen_sesion(pd.concat([b,row]))
