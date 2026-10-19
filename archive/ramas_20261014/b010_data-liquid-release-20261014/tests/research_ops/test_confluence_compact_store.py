import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from tools.research_ops.confluence.market_pilot import PrivateStore
from tools.research_ops.confluence.compact_store import ClusteredPrivateStore
from tools.research_ops.confluence.detector_capture import Capture,PINS
from tools.research_ops.confluence.asof_intersections import Clock,ZoneKey

def captures(n=1200):
    out=[]
    for j in range(n):
        cfg=j%3;key=ZoneKey('BT2','a'*64,PINS['BT2'],str(j//4))
        out.append((cfg,Capture(('BIRTH','TOUCH','CLASSIFY','REMOVE')[j%4],key,Clock(1781586000000000000+j//6,j%6),j,j//5,10,14,(-1,0,1)[j%3],(('x',1.5),('s','invented')), 'reason' if j%4==3 else '')))
    return out
class CompactTests(unittest.TestCase):
    def stores(self,d,**kwargs):
        configs=[{'indicator':'bigtrap2','config_sha256':'a'*64}]*3
        return [cls(Path(d)/str(i),configs,**kwargs) for i,cls in enumerate((PrivateStore,ClusteredPrivateStore))]
    def test_exact_payload_order_hashes_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            stores=self.stores(d)
            for cfg,x in captures():
                for s in stores:s.add(cfg,SimpleNamespace(records=(x,),unavailable_events=0),'2026-06-16')
            for s in stores:s.ready()
            a,b=stores;self.assertEqual(a.counts,b.counts);self.assertEqual(a.target_counts,b.target_counts);self.assertEqual([h.hexdigest() for h in a.hashes],[h.hexdigest() for h in b.hashes])
            for cfg in range(3):self.assertEqual(list(a.records(cfg)),list(b.records(cfg)))
            for s in stores:s.db.close()
    def test_same_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            stores=self.stores(d,max_records=1)
            for s in stores:
                for cfg,x in captures(1):s.add(cfg,SimpleNamespace(records=(x,),unavailable_events=0),'2026-06-16')
                with self.assertRaises(ValueError):s.add(0,SimpleNamespace(records=(x,),unavailable_events=0),'2026-06-16')
                s.db.close()
    def test_baseline_nested_storage_timings(self):
        with tempfile.TemporaryDirectory() as d:
            stores=self.stores(d)
            for s in stores:
                cfg,x=captures(1)[0];s.add(cfg,SimpleNamespace(records=(x,),unavailable_events=0),'2026-06-16');s.ready();self.assertIn('capture_encode_hash_seconds',s.storage_seconds);self.assertIn('insert_commit_seconds',s.storage_seconds);s.db.close()
    def test_partial_capture_prefix_survives_geometry_failure(self):
        from unittest.mock import patch
        import pyarrow as pa,pyarrow.parquet as pq
        from tools.research_ops.confluence.pilot_runtime import synthetic_fixture
        from tools.research_ops.confluence.market_pilot import run_pilot,trade_date
        root=Path(__file__).resolve().parents[2];roster=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes());t,_=synthetic_fixture(sessions=1,ticks_per_session=1200)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'invented.parquet';pq.write_table(pa.table({k:pa.array(v) for k,v in zip(('ts_utc_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence'),(t.ts_ns,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,t.sequence))}),path)
            plan={'scope':'EXISTING_EXPLORATORY_TARGET_FREE_DENSITY_GEOMETRY','outcomes':False,'holdout_access':False,'start_ns':int(t.ts_ns[0]),'end_ns':int(t.ts_ns[-1])+1,'max_session_ticks':5000,'max_total_ticks':5000,'max_capture_records':200000,'max_private_bytes':100000000,'target_session':trade_date(int(t.ts_ns[-1])),'contract':'SYN','pin':{'sha256':'a'*64}}
            out=Path(d)/'partial.json'
            with patch('tools.research_ops.confluence.market_pilot.GeometryReplay.apply',side_effect=ValueError('invented later geometry failure')):
                with self.assertRaises(ValueError):run_pilot(path,roster,plan,d,partial_receipt_path=out)
            r=json.loads(out.read_bytes());self.assertEqual(r['target_ticks'],1200);self.assertGreater(r['capture_rows'],0);self.assertEqual(len(r['config_prefix_counts']),96);self.assertFalse(r['complete_census']);self.assertEqual(r['geometry_triads_reported_complete'],[0]);self.assertEqual(r['stage'],'GEOMETRY_TRIAD_COMPLETE');self.assertNotIn('invented later geometry failure',out.read_text())
            import hashlib,copy
            from tools.research_ops.confluence.terminal_acquisition import review_partial
            from tools.research_ops.confluence.build_target_free_pilot import digest
            pkg={'source_commit':'a'*40,'bundle_sha256':'b'*64}
            boot={**pkg,'partial_receipt_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
            reviewed=review_partial(json.dumps(boot).encode(),out.read_bytes(),package=pkg,plan=plan,roster=roster);self.assertFalse(reviewed['complete_census'])
            for field in ('overclaim','rows','hash','config','triads','times'):
                bad=copy.deepcopy(r)
                if field=='overclaim':bad['complete_census']=True
                elif field=='rows':bad['capture_rows']+=1
                elif field=='hash':bad['config_prefix_counts'][0]['ordered_prefix_capture_sha256']='z'*64
                elif field=='config':bad['config_prefix_counts'][0]['config_sha256']='z'*64
                elif field=='triads':bad['geometry_triads_reported_complete']=[1]
                else:bad['stage_seconds']['raw_text']=1
                bb=json.dumps(bad).encode();boot['partial_receipt_sha256']=hashlib.sha256(bb).hexdigest()
                with self.assertRaises(ValueError):review_partial(json.dumps(boot).encode(),bb,package=pkg,plan=plan,roster=roster)

    def test_no_partial_success_on_empty_input(self):
        from unittest.mock import patch
        from tools.research_ops.confluence.market_pilot import run_pilot
        root=Path(__file__).resolve().parents[2];roster=json.loads((root/'docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json').read_bytes())
        # Empty reader cannot create a false successful census.
        plan={'scope':'EXISTING_EXPLORATORY_TARGET_FREE_DENSITY_GEOMETRY','outcomes':False,'holdout_access':False,'max_session_ticks':5000,'max_capture_records':200000,'max_private_bytes':100000000,'start_ns':1,'end_ns':2,'max_total_ticks':1000,'target_session':'2026-06-16'}
        with tempfile.TemporaryDirectory() as d,patch('tools.research_ops.confluence.market_pilot.iter_sessions',return_value=iter(())):
            with self.assertRaises(ValueError):run_pilot('/missing',roster,plan,d,partial_receipt_path=Path(d)/'partial.json')
            self.assertFalse((Path(d)/'partial.json').exists())
if __name__=='__main__':unittest.main()
