import hashlib,json,tempfile,unittest
from pathlib import Path
from collections import Counter
from edgelab.bridge import bars as B
from tools.research_ops.confluence.market_pilot import run_pilot,PrivateStore,trade_date
from tools.research_ops.confluence.pilot_runtime import synthetic_fixture,Prepared
from tools.research_ops.confluence.detector_capture import capture_run

class MarketPilotTests(unittest.TestCase):
    def test_full_96_pilot_on_invented_parquet_matches_reference_capture_counts(self):
        import pyarrow as pa,pyarrow.parquet as pq
        root=Path(__file__).resolve().parents[2];roster=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());t,_=synthetic_fixture()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invented.parquet';pq.write_table(pa.table({k:pa.array(v) for k,v in zip(('ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence'),(t.ts_ns,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,t.sequence))}),p,row_group_size=733)
            target=trade_date(int(t.ts_ns[-1]));plan={'scope':'EXISTING_EXPLORATORY_TARGET_FREE_DENSITY_GEOMETRY','outcomes':False,'holdout_access':False,'start_ns':int(t.ts_ns[0]),'end_ns':int(t.ts_ns[-1])+1,'max_session_ticks':5000,'max_total_ticks':100000,'max_capture_records':200000,'max_private_bytes':100000000,'target_session':target,'contract':'SYN','pin':{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}
            result=run_pilot(p,roster,plan,d,deadline_seconds=240);self.assertEqual(result['configs_completed'],96);self.assertEqual(result['aligned_triads_completed'],32);self.assertFalse(result['outcomes_evaluated']);self.assertFalse(result['arrival_labels_evaluated']);prepared=Prepared(t)
            for c,got in zip(roster['configs'],result['config_counts']):
                family={'avolzonepoi2':'AVZP2','bigtrap2':'BT2','bigtrap2absorption':'BT2A'}[c['indicator']]
                if family=='BT2A':_,ref=capture_run(family,t,params=c['params'])
                else:
                    kind,size=c['bar_spec'].split(':');b=B.build_tick_bars(t,int(size)) if kind=='tick' else B.build_time_bars(t,int(size))
                    if family=='BT2':f=B.build_footprints(t,b);_,ref=capture_run(family,t,bars=b,footprints=f,params=c['params'])
                    else:
                        from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
                        f=build_total_footprint_csr_nt8(t,b);_,ref=capture_run(family,t,bars=b,footprints=f,sessions=B.session_ids(b.end_ns),params=c['params'])
                self.assertEqual(got['all_capture_counts'],dict(Counter(x.kind for x in ref.records)),c['config_sha256'])
                self.assertEqual(got['unobservable_eof_events'],ref.unavailable_time_events)
                h=hashlib.sha256()
                for x in ref.records:
                    payload=json.dumps([x.kind,x.key.zone_id,x.consumed_tick_index,x.source_bar,x.lo2,x.hi2,x.side,x.properties,x.reason],separators=(',',':'));h.update(f'{x.clock.ns}|{x.clock.sequence}|{payload}\n'.encode())
                self.assertEqual(got['ordered_private_capture_sha256'],h.hexdigest(),c['config_sha256'])
    def test_outcome_plan_rejected_before_source_read(self):
        with self.assertRaises(ValueError):run_pilot('/missing',{'configs':[]},{'scope':'EXISTING_EXPLORATORY_TARGET_FREE_DENSITY_GEOMETRY','outcomes':True,'holdout_access':False},'/missing')
    def test_private_capture_budget_no_truncation(self):
        from test_confluence_detector_pipeline import fixture
        from types import SimpleNamespace
        _,rs,_=fixture();c={'indicator':'bigtrap2','config_sha256':rs[0].parameter_sha256}
        with tempfile.TemporaryDirectory() as d:
            store=PrivateStore(Path(d)/'invented.sqlite',[c],max_records=1)
            with self.assertRaises(ValueError):store.add(0,SimpleNamespace(records=rs[0].records,unavailable_events=0),'2026-09-01')
            store.db.close()
if __name__=='__main__':unittest.main()
