"""Invented detector births, preserving copied legacy rule; not NT8 parity."""
import ast
import hashlib
from pathlib import Path
import unittest
import random
from tools.research_ops.confluence.racimo_asof import _racimo,RacimoObservation
from tools.research_ops.confluence.asof_intersections import Snapshot,ZoneKey
from tools.research_ops.confluence.racimo_asof import Creation,RacimoTape,LEGACY_FUNCTION_SHA256
from tools.research_ops.confluence.asof_intersections import Clock
H='a'*64;B='b'*64

def tape(**p):return RacimoTape(params={'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10,**p},config_sha256=H,build_sha256=B)
def z(i,bar,lo=100,hi=101,session='2026-09-01',c=None):return Creation(str(i),bar,lo,hi,session,c or Clock(100+bar,bar))

class RacimoTests(unittest.TestCase):
    def test_function_source_pin(self):
        p=Path(__file__).resolve().parents[2]/'tools/research_ops/confluence/racimo_asof.py';s=p.read_text();tree=ast.parse(s)
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_racimo')
        self.assertEqual(hashlib.sha256((ast.get_source_segment(s,f)+'\n').encode()).hexdigest(),LEGACY_FUNCTION_SHA256)
    def test_recognized_at_third_not_first_zone(self):
        t=tape();self.assertEqual(t.observe_batch([z(0,0)]),());self.assertEqual(t.observe_batch([z(1,1)]),())
        r=t.observe_batch([z(2,2)])[0];self.assertEqual(r.snapshot.recognized,z(2,2).available);self.assertEqual(r.formation_start_bar,0);self.assertEqual(r.legacy_first_recognition_bar,2)
    def test_expansion_available_now(self):
        t=tape();t.observe_batch([z(0,0)]);t.observe_batch([z(1,1)]);r0=t.observe_batch([z(2,2)])[0]
        r1=t.observe_batch([z(3,3,103,104)])[0];self.assertEqual(r1.snapshot.recognized,r0.snapshot.recognized);self.assertEqual(r1.snapshot.hi2,208);self.assertEqual(r0.snapshot.hi2,202);self.assertEqual(r1.snapshot.revision,1)
    def test_membership_change_without_geometry(self):
        t=tape();t.observe_batch([z(0,0)]);t.observe_batch([z(1,1)]);t.observe_batch([z(2,2)])
        r=t.observe_batch([z(3,3)])[0];self.assertTrue(r.legacy_member_state_changed);self.assertEqual(len(r.member_ids),4)
    def test_same_bar_order_preserved_and_coalesced(self):
        t=tape();c=Clock(100,0);r=t.observe_batch([z(0,0,c=c),z(1,0,c=c),z(2,0,c=c),z(3,0,c=c)])
        self.assertEqual(len(r),1);self.assertEqual(len(r[0].member_ids),4);self.assertEqual(r[0].snapshot.revision,0)
    def test_cross_session_legacy_explicit(self):
        t=tape();t.observe_batch([z(0,0)]);t.observe_batch([z(1,1)])
        r=t.observe_batch([z(2,2,session='2026-09-02')])[0];self.assertTrue(r.spans_sessions);self.assertEqual(len(r.member_trade_dates),2)
    def test_warmup_events_not_backdated_when_cluster_expands(self):
        t=tape();t.observe_batch([z(0,0)]);t.observe_batch([z(1,1)]);r=t.observe_batch([z(2,2)])[0]
        a=t.observe_batch([z(3,3,session='2026-09-02')])[0];self.assertEqual(a.snapshot.recognized,r.snapshot.recognized)
    def test_no_racimo_outside_bar_window(self):
        t=tape(racimo_bars=1);t.observe_batch([z(0,0)]);t.observe_batch([z(1,2)]);self.assertEqual(t.observe_batch([z(2,4)]),())
    def test_duplicate_ids_fail(self):
        t=tape();t.observe_batch([z(0,0)])
        with self.assertRaises(ValueError):t.observe_batch([z(0,1)])
    def test_mixed_batch_rejected(self):
        with self.assertRaises(ValueError):tape().observe_batch([z(0,0),z(1,1)])
    def test_history_capacity_not_truncation(self):
        t=RacimoTape(params={'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10},config_sha256=H,build_sha256=B,max_zones=1);t.observe_batch([z(0,0)])
        with self.assertRaises(ValueError):t.observe_batch([z(1,1)])
        self.assertEqual(len(t.zones),1)
    def test_holdout_rejected(self):
        with self.assertRaises(ValueError):z(0,0,session='2026-10-01')
    def test_prefix_states_immutable(self):
        t=tape();t.observe_batch([z(0,0)]);t.observe_batch([z(1,1)]);r=t.observe_batch([z(2,2)])[0];t.observe_batch([z(3,3,103,104)]);self.assertEqual(r.snapshot.hi2,202)
    def test_indexed_membership_matches_full_scan_reference(self):
        rng=random.Random(20261011)
        for params in ({'racimo_min':3,'racimo_bars':10,'racimo_altura_ticks':10}, {'racimo_min':6,'racimo_bars':50,'racimo_altura_ticks':30}):
            t=RacimoTape(params=params,config_sha256=H,build_sha256=B)
            zones=[];clusters=[];ids={};published={};serial=0
            for bar in range(180):
                cs=[];clock=Clock(1000+bar,bar);session='2026-09-01' if bar<90 else '2026-09-02'
                for _ in range(rng.randrange(1,4)):
                    serial+=1;lo=rng.randrange(90,130);cs.append(z(serial,bar,lo,lo+rng.randrange(1,5),session,clock))
                for c in cs:
                    nz=dict(bar=c.bar,low_tick=c.low_tick,high_tick=c.high_tick,racimo_bar=-1,rac=None,zone_id=c.zone_id,trade_date=c.trade_date)
                    _racimo(nz,zones,clusters,bar,params);zones.append(nz)
                want=[]
                for k in clusters:
                    obj=id(k)
                    if obj not in ids:ids[obj]=(str(len(ids)),clock)
                    ms=[v for v in zones if v['rac'] is k]
                    mids=tuple(sorted(v['zone_id'] for v in ms));dates=tuple(sorted(set(v['trade_date'] for v in ms)))
                    signature=(k['start'],k['low'],k['high'],mids);prev=published.get(obj)
                    if prev and prev[0]==signature:continue
                    rev=prev[1]+1 if prev else 0;cid,born=ids[obj]
                    snap=Snapshot(ZoneKey('RACIMO',H,B,cid),rev,clock,born,2*k['low'],2*k['high'])
                    want.append(RacimoObservation(snap,mids,dates,k['start'],k['bar'],bool(prev and prev[0][3]!=mids),len(dates)>1))
                    published[obj]=(signature,rev)
                self.assertEqual(t.observe_batch(cs),tuple(want))

if __name__=='__main__':unittest.main()
