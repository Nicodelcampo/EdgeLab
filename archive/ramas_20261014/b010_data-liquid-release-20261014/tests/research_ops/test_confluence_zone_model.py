import ast,base64,copy,hashlib,json,os,subprocess,sys,tempfile,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries
from tools.research_ops.confluence import zone_model_pilot as P
from tools.research_ops.confluence import zone_model_design as D
from tools.research_ops.confluence import package_zone_model as K
from tools.research_ops.confluence.zone_scene import ZoneScene
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.confluence.phenomena_models import FEATURES,TRAIN,EVAL
from tools.research_ops.confluence.session_primitives import SessionTape
from tools.research_ops.confluence.asof_intersections import Clock
from tests.research_ops.test_phenomena import tape
ROOT=Path(__file__).resolve().parents[2]
def plan():return json.loads((ROOT/P.PLAN).read_bytes())
def cal():return json.loads((ROOT/P.CAL_PATH).read_bytes())

def fixtures(dates):
    out=[];offset=0
    for d in dates:
        end=int(__import__('datetime').datetime.fromisoformat(d+'T22:00:00+00:00').timestamp())*10**9
        a=tape(2200);a[0]=end-86400*10**9+np.arange(2200,dtype=np.int64)*500000000;a[1]+=offset
        t=TickSeries(a[0],a[2],a[3],a[4],a[5],a[1],.25,instrument='SYN',contract='SYN')
        out.append(SessionTape(t,offset,None,int(B.session_ids(t.ts_ns)[0])));offset+=len(t)
    from dataclasses import replace
    return [replace(st,next_clock=Clock(int(out[i+1].ticks.ts_ns[0]),int(out[i+1].ticks.sequence[0]))) if i+1<len(out) else st for i,st in enumerate(out)]

class ZoneModelTests(unittest.TestCase):
    def test_fixed_plan_and_all_mutations_rejected(self):
        p=plan();P.validate_plan(p)
        for k,v in [('wall_seconds',99999),('holdout',True),('evaluation_outcomes_previously_inspected',False),('models',[]),('warmup_start_ns',0),('max_query_hits',True)]:
            q=copy.deepcopy(p);q[k]=v
            with self.assertRaises(ValueError):P.validate_plan(q)

    def test_design_dimensions_capacity_matched(self):
        rng=np.random.default_rng(3);x=rng.normal(size=(100,len(FEATURES)));z=rng.normal(size=(100,16))
        for name in D.MODELS[1:]:self.assertEqual(D.design(x,z[:,:8],z[:,8:12],z[:,12:],name).shape,(100,D.FEATURE_COUNTS[name]))
        self.assertEqual(D.FEATURE_COUNTS['GEOMETRY'],D.FEATURE_COUNTS['GEOMETRY_CC']);self.assertEqual(D.FEATURE_COUNTS['ARRIVAL'],D.FEATURE_COUNTS['ARRIVAL_CC'])
        with self.assertRaises(ValueError):D.design(x,z[:,:7],z[:,8:12],z[:,12:],'GEOMETRY')
        with self.assertRaises(ValueError):D.design(x,z[:,:8],z[:,8:12],z[:,12:],'TUNED_WINNER')

    def test_same_labels_rows_and_equal_session_weight(self):
        rng=np.random.default_rng(12);tr=[]
        for n,label in ((100,0),(400,1)):
            x=rng.normal(size=(n,len(FEATURES)));z=rng.normal(size=(n,16));tr.append((x,z[:,:8],z[:,8:12],z[:,12:],np.full(n,label)))
        models,prior=P.fit_models(tr);np.testing.assert_allclose(prior,[.5,.5,0])
        x,d,g,a,y=tr[0];data=(x,np.zeros((100,2)),np.zeros((100,2)),y,np.array(['OTHER:1']*100),np.array(['NEITHER']*100),{})
        r=P.score(data,np.column_stack((d,g,a)),models,prior)
        self.assertEqual(r['scores']['anchors'],100);self.assertEqual(set(r['scores']['mean_brier']),set(D.MODELS))
        for key,delta in r['paired_deltas'].items():
            left,right=key.split('_MINUS_');self.assertAlmostEqual(delta,r['scores']['mean_brier'][left]-r['scores']['mean_brier'][right])

    def test_native_scene_synthetic_continuity_not_mocked(self):
        p=plan();s=ZoneScene(p);events=[]
        for st,date in zip(fixtures(['2026-06-12','2026-06-15','2026-06-16']),['2026-06-12','2026-06-15','2026-06-16']):
            ev,diag=s.session(st,date,retain=date!='2026-06-12');events.extend(ev)
            self.assertEqual(diag['ticks'],2200)
            self.assertTrue(all(all(z.available==c for z in up) for c,up,rem in ev))
        self.assertEqual(s.total_ticks,6600);self.assertEqual(s.primitives.next_index,6600)
        self.assertGreater(s.stream.history_values,0)

    def test_native_birth_snapshots_match_full_reference_on_invented_tape(self):
        from dataclasses import replace
        from tests.research_ops.test_confluence_detector_capture import avz_tape
        from tools.research_ops.confluence.detector_capture import capture_run
        from tools.research_ops.confluence._pinned_total_footprint import build_total_footprint_csr_nt8
        t=avz_tape();p=plan();cfg=p['avzp2_config'];cfg['bar_spec']='tick:5'
        cfg['params'].update(window_bars=1,min_samples=2,lookback_sessions=3)
        cfg['config_sha256']=digest({k:cfg[k] for k in ('indicator','bar_spec','params')})
        b=B.build_tick_bars(t,5);fp=build_total_footprint_csr_nt8(t,b);ses=B.session_ids(b.end_ns)
        _,receipt=capture_run('AVZP2',t,bars=b,footprints=fp,sessions=ses,params=cfg['params'])
        expected=[r.birth_snapshot() for r in receipt.records if r.kind=='BIRTH']
        ids=B.session_ids(t.ts_ns);edges=np.r_[0,np.flatnonzero(np.diff(ids))+1,len(t)]
        scene=ZoneScene(p);actual=[];excluded=0
        for lo,hi in zip(edges[:-1],edges[1:]):
            lo=int(lo);hi=int(hi);sub=TickSeries(*(getattr(t,k)[lo:hi] for k in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),.25,instrument='SYN',contract='SYN')
            following=Clock(int(t.ts_ns[hi]),int(t.sequence[hi])) if hi<len(t) else None
            st=SessionTape(sub,lo,following,int(ids[lo]))
            date=__import__('datetime').datetime.fromtimestamp(st.session_id*86400,__import__('datetime').timezone.utc).date().isoformat()
            events,diag=scene.session(st,date,retain=True)
            actual.extend(z for c,ups,rem in events for z in ups if z.key.family=='AVZP2')
            excluded+=diag['capture_counts'].get('racimo_carry_or_mixed_excluded',0)
        self.assertGreater(len(actual),0);self.assertEqual(actual,expected)
        self.assertGreater(excluded,0)  # Legacy carry remains native, not relabeled primary.

    def test_full_synthetic_native_and_labels_shared_pass(self):
        p=plan();dates=['2026-06-12']+list(TRAIN+EVAL);ss=fixtures(dates);seen=[];original=P.fit_models
        def fitter(tr):seen.append(len(tr));return original(tr)
        with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(P,'iter_sessions',return_value=iter(ss)),patch.object(P,'fit_models',fitter):
            r=P.run('SYNTHETIC',p,'/tmp/private-zone-synthetic',cal())
        self.assertEqual(seen,[2]);self.assertEqual(r['available_evaluation_session_count'],12)
        self.assertEqual(r['total_ticks'],15*2200);self.assertEqual(r['warmup_sessions'],1)
        self.assertFalse(r['retained_pair_graph']);self.assertFalse(r['holdout_opened']);self.assertFalse(r['confirmation'])
        for s in r['training_sessions']+r['evaluation_sessions']:
            self.assertEqual(s['common_usable_anchors'],s['zone_context']['common_anchors'])
            self.assertEqual(s['anchors'],s['common_usable_anchors']+sum(s['excluded_counts'].values()))
        self.assertEqual(set(r['mean_session_brier']),set(D.MODELS))
        from tools.research_ops.audits.review_zone_models import review
        raw=json.dumps(r).encode();pkg={'source_commit':'a'*40,'bundle_sha256':'b'*64,'plan_sha256':digest(p)}
        boot={**pkg,'status':'DEVELOPMENT_ZONE_COMPLETE_NOT_EDGE','exit_code':0,'stop_reason':None,'outcomes_computed':True,'zone_receipt_sha256':hashlib.sha256(raw).hexdigest()}
        self.assertTrue(review(boot,r,p,pkg,raw)['status'].startswith('PASS_'))
        for key,val in [('holdout_opened',True),('evaluation_outcomes_previously_inspected',False),('mean_session_brier',{'PRIOR':-1})]:
            bad=copy.deepcopy(r);bad[key]=val
            with self.assertRaises((ValueError,KeyError)):review(boot,bad,p,pkg,raw)
        bad=copy.deepcopy(r);bad['evaluation_sessions'][0]['common_usable_anchors']+=1
        with self.assertRaises(ValueError):review(boot,bad,p,pkg,raw)

    def test_empty_eval_no_replacement_and_fit_missing_rejected(self):
        p=plan();dates=[d for d in TRAIN+EVAL if d!='2026-06-18'];ss=fixtures(dates)
        with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(P,'iter_sessions',return_value=iter(ss)):
            r=P.run('SYNTHETIC',p,'/tmp/private-zone-synthetic',cal())
        self.assertEqual(r['unavailable_evaluation_sessions'][0]['trade_date'],'2026-06-18');self.assertEqual(r['available_evaluation_session_count'],11)
        with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}),patch.object(P,'iter_sessions',return_value=iter(fixtures(list(EVAL)))):
            with self.assertRaisesRegex(ValueError,'fit before evaluation'):P.run('SYNTHETIC',p,'/tmp/private-zone-synthetic',cal())

    def test_runtime_guard_and_private_output_guard(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):P.run('SYNTHETIC',plan(),'/tmp/private',cal())
        with patch.dict(os.environ,{'KAGGLE_KERNEL_RUN_TYPE':'SYNTHETIC'}):
            with self.assertRaises(ValueError):P.run('SYNTHETIC',plan(),'/kaggle/working/private',cal())

    def test_exact_bundle_isolated_startup_and_no_secret_receipt(self):
        url='https://storage.googleapis.com/kagglesdsdata/datasets/synthetic/MNQ/MNQ_09-26_ticks_ext.parquet'
        request,receipt=K.build_request(ROOT,url=url,source_commit='a'*40)
        text=request['request']['text'];compile(text,'boot','exec');self.assertNotIn(url,json.dumps(receipt))
        self.assertTrue(request['request']['isPrivate']);self.assertFalse(receipt['submitted'])
        tree=ast.parse(text);encoded=next(ast.literal_eval(t.value) for t in tree.body if isinstance(t,ast.Assign) and isinstance(t.targets[0],ast.Name) and t.targets[0].id=='DATA')
        bundle=json.loads(zlib.decompress(base64.b64decode(encoded)))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,rec in bundle.items():
                q=root/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(base64.b64decode(rec['data']))
            for pkg in ('tools','tools/research_ops','tools/research_ops/confluence'):(root/pkg/'__init__.py').touch()
            env=dict(os.environ);env.pop('PYTHONPATH',None);env['OPENBLAS_NUM_THREADS']='1'
            startup=subprocess.run([sys.executable,'-m','tools.research_ops.confluence.zone_model_pilot','--help'],cwd=root,env=env,text=True,capture_output=True,timeout=30)
            self.assertEqual(startup.returncode,0,startup.stderr)
            (root/'tools/research_ops/confluence/zone_context.py').unlink()
            broken=subprocess.run([sys.executable,'-m','tools.research_ops.confluence.zone_model_pilot','--help'],cwd=root,env=env,text=True,capture_output=True,timeout=30)
            self.assertNotEqual(broken.returncode,0)

if __name__=='__main__':unittest.main()
