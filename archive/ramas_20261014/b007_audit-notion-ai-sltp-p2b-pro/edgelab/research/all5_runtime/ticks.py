from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np
from edgelab.data.nt8_contract import INSTRUMENT_SPECS
@dataclass
class TickSeries:
    ts_ns:np.ndarray; price_ticks:np.ndarray; volume:np.ndarray
    bid_ticks:Optional[np.ndarray]; ask_ticks:Optional[np.ndarray]; sequence:np.ndarray
    tick_size:float; instrument:str='?'; contract:str='?'; source:str='?'
    def __post_init__(self):
        d=np.diff(self.ts_ns)
        if len(d) and d.min()<0: raise ValueError('ticks no monótonos')
    def __len__(self): return len(self.ts_ns)
def load_canonical_parquet(path,contract=None,start_utc_ns=None,end_utc_ns=None,instrument=None):
    import pyarrow.parquet as pq
    filters=[]
    if contract is not None: filters.append(('contract','==',contract))
    if start_utc_ns is not None: filters.append(('ts_utc_ns','>=',int(start_utc_ns)))
    if end_utc_ns is not None: filters.append(('ts_utc_ns','<',int(end_utc_ns)))
    tbl=pq.read_table(path,filters=filters or None)
    def col(n): return tbl.column(n).to_numpy(zero_copy_only=False)
    inst=instrument or str(tbl.column('instrument')[0].as_py())
    spec=INSTRUMENT_SPECS[inst]
    return TickSeries(col('ts_utc_ns').astype(np.int64),col('price_ticks').astype(np.int64),col('volume').astype(np.float64),col('bid_ticks').astype(np.int64),col('ask_ticks').astype(np.int64),col('sequence').astype(np.int64),spec.tick_size,inst,contract or str(tbl.column('contract')[0].as_py()),str(path))
