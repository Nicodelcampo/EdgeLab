import json
import numpy as np
import pyarrow as pa
from economic import replay,costs,evaluate,NS

def batch(ts,bid=None,ask=None):
 bid=bid if bid is not None else [100.]*len(ts);ask=ask if ask is not None else [101.]*len(ts)
 return pa.RecordBatch.from_pydict({'ts_utc_ns':pa.array(ts,type=pa.int64()),'bid_ticks':pa.array(bid,type=pa.float64()),'ask_ticks':pa.array(ask,type=pa.float64())})
def slot(i='a',signal=0):return {'id':i,'signal_ns':signal,'hold_min':1,'cutoff_ns':100*NS,'direction':1,'U':2,'asset':'RTY'}
def test_strict_latency_empty_batch_and_arithmetic():
 s=slot();replay([s],[batch([]),batch([250000000,250000001,60250000001],[100,100,104],[101,101,105])]);assert s['entry_ns']==250000001 and s['status']=='COMPLETE' and s['gross_ticks']==3 and s['alpha_ticks']==4

def test_no_entry():
 s=slot();replay([s],[batch([31*NS])]);assert s['status']=='NO_ENTRY_QUOTE_WITHIN30S'
def test_unknown_exit_never_complete():
 s=slot();replay([s],[batch([NS,110*NS])]);assert s['status']=='UNKNOWN_EXIT_NO_QUOTE_BY16ET'
def test_short_arithmetic():
 s=slot();s['direction']=-1;replay([s],[batch([NS,61*NS],[100,96],[101,97])]);assert s['gross_ticks']==3 and s['alpha_ticks']==4

def test_exact_exit_and_invalid_quote():
 s=slot();replay([s],[batch([NS,61*NS,62*NS],[100,106,107],[101,106,108])]);assert s['exit_ns']==62*NS

def test_costs_explicit():
 m=json.load(open('manifest.json'));assert abs(costs(m,'RTY',1)-2.9)<1e-9;assert abs(costs(m,'MNQ',1)-4.4)<1e-9;assert abs(costs(m,'YM',1)-2.96)<1e-9
