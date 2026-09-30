import importlib.util
import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

spec=importlib.util.spec_from_file_location("pair",Path(__file__).resolve().parents[2]/"tools/l2_pairing_preflight.py")
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Tests(unittest.TestCase):
    def setUp(self):
        self.x=np.array([[1000,50,2],[1000,50,2],[2000,51,1]],dtype=np.int64)
    def test_exact_duplicates_retained(self):
        self.assertEqual(M.ordered_tape(self.x,self.x.copy())["ticks"],3)
    def test_no_nearest(self):
        y=self.x.copy();y[1,0]+=1
        self.assertEqual(M.ordered_tape(self.x,y)["timestamp_mismatches"],1)
    def test_order_not_multiset(self):
        y=self.x[[2,1,0]]
        self.assertNotEqual(M.ordered_tape(self.x,y)["gate"],"PASS")
    def test_length_not_resampled(self):
        self.assertEqual(M.ordered_tape(self.x,self.x[:2])["gate"],"ABSTAIN_TAPE_LENGTH")
    def test_price_mismatch(self):
        y=self.x.copy();y[0,1]+=1
        self.assertEqual(M.ordered_tape(self.x,y)["price_mismatches"],1)
    def test_volume_mismatch(self):
        y=self.x.copy();y[0,2]+=1
        self.assertEqual(M.ordered_tape(self.x,y)["volume_mismatches"],1)
    def test_float_clock_not_accepted(self):
        with self.assertRaisesRegex(M.Abstain,"INTEGER_TAPE_REQUIRED"):
            M.ordered_tape(self.x.astype(float),self.x)
    def test_no_offset_default(self):
        e=M.audit({"instrument":"ES"})
        self.assertEqual(e["reason"],"EXPLICIT_INTEGER_CLOCK_OFFSET_REQUIRED")
    def test_no_clock_provenance_default(self):
        e=M.audit({"instrument":"GC","clock_offset_ns":0})
        self.assertEqual(e["reason"],"CLOCK_PROVENANCE_REQUIRED")
    def test_no_instrument_inference(self):
        self.assertEqual(M.audit({})["reason"],"EXPLICIT_INSTRUMENT_REQUIRED")
    def test_missing_file_abstains(self):
        c=dict(instrument="ES",contract="ES 09-26",tick_size=.25,clock_offset_ns=0,
               clock_resolution_source="synthetic test, not absolute certificate",
               holdout_boundary_ns=10**18,files={k:dict(path="/NO_SUCH_FILE",sha256="0"*64)
                  for k in ("ticks","l1","l2","session_manifest")})
        self.assertEqual(M.audit(c)["gate"],"ABSTAIN")
    def test_es_grid_not_gc_grid(self):
        a=dict(source_row=np.array([0]),ts_us=np.array([1]),price_tick=np.array([201]),
               price=np.array([50.25]),size=np.array([1]),side=np.array([2]))
        b=dict(source_row=np.array([1]),ts_us=np.array([1]),price_tick=np.array([202]),
               price=np.array([50.5]),size=np.array([1]),side=np.array([0]),
               operation=np.array([0]),level=np.array([0]))
        M.raw_checks(a,b,.25)
        with self.assertRaisesRegex(M.Abstain,"GRID"):
            M.raw_checks(a,b,.1)
    def test_nontrade_l1_volume_record_preserved(self):
        a=dict(source_row=np.array([0]),ts_us=np.array([1]),price_tick=np.array([200]),
               price=np.array([50.]),size=np.array([5]),side=np.array([5]))
        b=dict(source_row=np.array([1]),ts_us=np.array([1]),price_tick=np.array([202]),
               price=np.array([50.5]),size=np.array([1]),side=np.array([0]),
               operation=np.array([0]),level=np.array([0]))
        M.raw_checks(a,b,.25)
        self.assertEqual(int((a["side"]==2).sum()),0)
        b["level"]=np.array([10])
        M.raw_checks(a,b,.25)  # displaced tail, not eleventh visible feature
        b["level"]=np.array([-1])
        with self.assertRaisesRegex(M.Abstain,"NEGATIVE_L2_LEVEL"):
            M.raw_checks(a,b,.25)
    def test_es_full_synthetic_custody_and_tape(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            schema_meta={b"edgelab_schema":b"nt8_l1_quotes_trades_v2",
                         b"side_codes":b"0=ASK,1=BID,2=LAST,5=DAILY_VOLUME"}
            l1=pa.table(dict(source_row=[0,2,3],ts_us=[1000,2000,2000],
                     price_tick=[201,202,202],price=[50.25,50.5,50.5],
                     size=[1,2,3],side=[2,2,5])).replace_schema_metadata(schema_meta)
            l2=pa.table(dict(source_row=[1],ts_us=[1000],price_tick=[202],
                     price=[50.5],size=[2],side=[0],level=[0],operation=[0])).replace_schema_metadata(
                         {b"edgelab_schema":b"nt8_l2_depth_v2"})
            ticks=pa.table(dict(ts_utc_ns=[1000000,2000000],price_ticks=[201,202],
                     volume=[1,2],instrument=["ES","ES"],contract=["ES 09-26"]*2,
                     tick_type=["trade"]*2))
            for label,t in [("l1",l1),("l2",l2),("ticks",ticks)]:
                pq.write_table(t,r/(label+".parquet"))
            m=dict(instrument="ES 09-26",session_name="synthetic",conversion=dict(tick_size=.25),
                   outputs={k:dict(sha256=M.sha256(r/(v+".parquet")),rows=t.num_rows)
                            for k,v,t in [("l1_quotes","l1",l1),("l2_depth","l2",l2)]})
            (r/"manifest.json").write_text(json.dumps(m))
            c=dict(instrument="ES",contract="ES 09-26",session="synthetic",tick_size=.25,
                   clock_offset_ns=0,clock_resolution_source="SYNTHETIC_TEST_ONLY",
                   holdout_boundary_ns=3000000,files={
                    k:dict(path=str(r/f),sha256=M.sha256(r/f)) for k,f in
                    [("l1","l1.parquet"),("l2","l2.parquet"),("ticks","ticks.parquet"),
                     ("session_manifest","manifest.json")]})
            e=M.audit(c)
            self.assertEqual(e["gate"],"PASS",e)
            self.assertEqual(e["tape"]["ticks"],2)  # not DAILY_VOLUME
            self.assertEqual(e["book_replay_gate"],"NOT_RUN")
            c["tick_size"]=.1
            self.assertEqual(M.audit(c)["reason"],"MANIFEST_TICK_SIZE_FAIL")

if __name__=="__main__": unittest.main()