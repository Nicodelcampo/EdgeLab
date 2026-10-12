"""Bounded Parquet batches -> existing exploratory natural-session tapes.

Use real source only inside Kaggle. Not a quality audit or certificate. Range is
fixed before reading and below closed holdout; skips nonintersecting row groups.
Caller already binds the approved physical source. No sorting/dropping bad ticks.
"""
from __future__ import annotations
import numpy as np
from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries
from .asof_intersections import Clock
from .session_primitives import SessionTape

HOLDOUT_NS=1790805600000000000
COLUMNS=('ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')

def iter_sessions(path,*,start_ns,end_ns,contract='MNQ_09-26',batch_size=100000,max_session_ticks=5000000,max_total_ticks=8000000):
    if type(start_ns) is not int or type(end_ns) is not int or not 0<start_ns<end_ns<=HOLDOUT_NS:raise ValueError('prebound preholdout range required')
    for v in (batch_size,max_session_ticks,max_total_ticks):
        if type(v) is not int or v<1:raise ValueError('finite reader budgets')
    import pyarrow.parquet as pq
    pf=pq.ParquetFile(path);col=pf.schema_arrow.names.index('ts_utc_ns');groups=[]
    for i in range(pf.metadata.num_row_groups):
        stats=pf.metadata.row_group(i).column(col).statistics
        if stats is None or not stats.has_min_max:raise ValueError('range pushdown unavailable; no whole-file fallback')
        if stats.max<start_ns or stats.min>=end_ns:continue
        if stats.max>=HOLDOUT_NS:raise ValueError('row group intersects closed holdout; no payload read')
        groups.append(i)
    parts=[];have=0;sid=None;absolute=0;total=0;last_clock=None
    for batch in pf.iter_batches(batch_size=batch_size,row_groups=groups,columns=list(COLUMNS),use_threads=False):
        vals=[batch.column(i).to_numpy(zero_copy_only=False) for i in range(len(COLUMNS))]
        if any(batch.column(i).null_count for i in range(len(COLUMNS))):raise ValueError('null runtime input; no imputation')
        mask=(vals[0]>=start_ns)&(vals[0]<end_ns)
        if not mask.any():continue
        vals=[v[mask] for v in vals];n=len(vals[0]);total+=n
        if total>max_total_ticks:raise ValueError('full range exceeds tick budget; no silent prefix truncation')
        clocks=vals[0];seq=vals[-1]
        if np.any(clocks[1:]<clocks[:-1]) or np.any(seq[1:]<=seq[:-1]) or (last_clock and (int(clocks[0])<last_clock.ns or int(seq[0])<=last_clock.sequence)):raise ValueError('source order invalid; no sorting')
        last_clock=Clock(int(clocks[-1]),int(seq[-1]));ss=B.session_ids(clocks);edges=np.r_[0,np.flatnonzero(np.diff(ss))+1,n]
        for a,z in zip(edges[:-1],edges[1:]):
            a=int(a);z=int(z);new=int(ss[a])
            if sid is not None and new!=sid:
                if new<sid:raise ValueError('retrograde session')
                arr=[np.concatenate([p[k] for p in parts]) for k in range(len(COLUMNS))]
                tape=TickSeries(*arr,.25,instrument='MNQ',contract=contract)
                yield SessionTape(tape,absolute,Clock(int(clocks[a]),int(seq[a])),sid)
                absolute+=have;parts=[];have=0
            sid=new;have+=z-a
            if have>max_session_ticks:raise ValueError('natural session exceeds memory budget; no reset/truncation')
            parts.append([v[a:z].copy() for v in vals])
    if parts:
        arr=[np.concatenate([p[k] for p in parts]) for k in range(len(COLUMNS))]
        yield SessionTape(TickSeries(*arr,.25,instrument='MNQ',contract=contract),absolute,None,sid)
