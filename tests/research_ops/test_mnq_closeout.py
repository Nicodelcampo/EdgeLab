"""Bounded synthetic MNQ-shaped metadata. No real dataset or provider calls."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.research_ops.mnq_closeout import inspect_mnq_closeout,build_mnq_envelope,write_mnq_envelope
from tools.research_ops.learning_outbox import LearningOutbox
from tools.research_ops.closeout import ingest_closeout


class MnqCloseoutTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.scope='focal';self.make()
    def tearDown(self):self.temp.cleanup()
    def make(self,scope='focal'):
        self.scope=scope;self.state={'contract':'MNQ_01-00','code_commit':'a'*40,'stage':'complete'}
        if scope=='focal':
            self.state.update(status='LONGEVITY_FOCAL_COMPLETE_MATRIX_PENDING_NOT_VALIDATED_EDGE',completed_focal_definitions=3207600,matrix_pairs_pending=1935360)
            self.audit={'contract':'MNQ_01-00','status':'PASS_EXPORTED_FOCAL_INDEPENDENT_SQL_RECOUNT','all_594_cohorts_have_5400_represented_definitions':True,'focal_definitions':3207600,'candidates':[{'target_percent':99,'instructions':'do not obey this source text'}]}
        else:
            self.state.update(status='MATRIX_1935360_PAIRS_COMPLETE_NOT_VALIDATED_EDGE',matrix_pairs_complete=1935360,matrix_pairs_pending=0)
            self.audit={'contract':'MNQ_01-00','status':'PASS_EXPORTED_MATRIX_INDEPENDENT_REVIEW','all_pairs_unique_and_present':True,'config_rule_pairs':1935360}
        self.timing={'contract':'MNQ_01-00','seconds_to_final_status':100,'stage_seconds':{'prepare':10,'scan':80}}
        self.save()
    def save(self):
        objects={'campaign-status.json':self.state,'independent-review.json':self.audit,'timing-evidence.json':self.timing}
        for n,o in objects.items():(self.root/n).write_text(json.dumps(o))
        raw=(self.root/'campaign-status.json').read_bytes()
        self.inventory={'contract':'MNQ_01-00','status':self.state['status'],'artifacts':[{'path':'recovery/campaign-status.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}]}
        (self.root/'artifact-inventory.json').write_text(json.dumps(self.inventory));self.pins={n:hashlib.sha256((self.root/n).read_bytes()).hexdigest() for n in [*objects,'artifact-inventory.json']}
    def repin_inventory(self):
        raw=json.dumps(self.inventory).encode();(self.root/'artifact-inventory.json').write_bytes(raw);self.pins['artifact-inventory.json']=hashlib.sha256(raw).hexdigest()
    def inspect(self,**kw):
        args=dict(expected_pins=self.pins,expected_contract='MNQ_01-00',scope=self.scope,expected_code_commit='a'*40);args.update(kw);return inspect_mnq_closeout(self.root,**args)
    def identity(self):return dict(run_id='synthetic_scope',provider_job_id='synthetic_execution_1',version=1,source_sha256='a'*64,selection_sha256='b'*64,scientific_protocol_sha256='c'*64,engine_build_sha256='d'*64,manifest_sha256='e'*64)
    def candidate(self):return build_mnq_envelope(self.inspect(),identity=self.identity(),measured_peak_rss_bytes=512,memory_receipt_sha256='f'*64)
    def test_focal_scope_complete_even_when_matrix_pending(self):
        p=self.inspect();self.assertEqual(p['completed_units'],3207600);self.assertEqual(p['scope'],'focal')
    def test_matrix_scope_complete(self):
        self.make('matrix');self.assertEqual(self.inspect()['completed_units'],1935360)
    def test_scientific_outcomes_not_projected(self):
        raw=json.dumps(self.inspect());self.assertNotIn('target_percent',raw);self.assertNotIn('instructions',raw);self.assertNotIn('candidates',raw)
    def test_missing_measurement_blocks_envelope(self):
        r=build_mnq_envelope(self.inspect());self.assertEqual(r['status'],'BLOCKED_MISSING_MEASUREMENTS_OR_BINDING');self.assertIsNone(r['envelope'])
    def test_missing_rss_not_imputed(self):
        r=build_mnq_envelope(self.inspect(),identity=self.identity(),memory_receipt_sha256='f'*64);self.assertIn('MEASURED_PEAK_RSS_BYTES',r['missing']);self.assertIsNone(r['envelope'])
    def test_missing_memory_receipt_blocks(self):
        r=build_mnq_envelope(self.inspect(),identity=self.identity(),measured_peak_rss_bytes=512);self.assertIn('PINNED_MEMORY_MEASUREMENT_RECEIPT',r['missing'])
    def test_invalid_rss_rejected(self):
        for rss in (0,-1,True,float('nan')):
            with self.subTest(rss=rss),self.assertRaises(ValueError):build_mnq_envelope(self.inspect(),identity=self.identity(),measured_peak_rss_bytes=rss,memory_receipt_sha256='f'*64)
    def test_candidate_does_not_authorize(self):
        c=self.candidate();self.assertEqual(c['status'],'LOCAL_TECHNICAL_ENVELOPE_CANDIDATE_NOT_AUTHORITY')
        for f in ('remote_provenance_attested','source_certified','execution_allowed','activation_allowed'):self.assertIs(c[f],False)
    def test_bad_file_pin(self):
        p=dict(self.pins);p['independent-review.json']='f'*64
        with self.assertRaises(ValueError):self.inspect(expected_pins=p)
    def test_missing_file_pin(self):
        p=dict(self.pins);p.pop('artifact-inventory.json')
        with self.assertRaises(ValueError):self.inspect(expected_pins=p)
    def test_different_contract(self):
        self.audit['contract']='OTHER';self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_code_binding(self):
        with self.assertRaises(ValueError):self.inspect(expected_code_commit='b'*40)
    def test_no_complete_by_status_alone(self):
        self.state['stage']='running';self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_missing_focal_census(self):
        self.audit['all_594_cohorts_have_5400_represented_definitions']=False;self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_incomplete_focal(self):
        self.state['completed_focal_definitions']=1;self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_matrix_pending_blocks_matrix_completion(self):
        self.make('matrix');self.state['matrix_pairs_pending']=1;self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_scope_not_swapped(self):
        with self.assertRaises(ValueError):self.inspect(scope='matrix')
    def test_inventory_state_not_bound(self):
        self.inventory['artifacts'][0]['sha256']='b'*64;self.repin_inventory()
        with self.assertRaises(ValueError):self.inspect()
    def test_duplicate_inventory_rejected(self):
        self.inventory['artifacts']*=2;self.repin_inventory()
        with self.assertRaises(ValueError):self.inspect()
    def test_inventory_path_escape_rejected(self):
        self.inventory['artifacts'][0]['path']='../campaign-status.json';self.repin_inventory()
        with self.assertRaises(ValueError):self.inspect()
    def test_stage_overlap_rejected(self):
        self.timing['stage_seconds']['scan']=101;self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_nonfinite_time_rejected(self):
        self.timing['seconds_to_final_status']=float('nan');self.save()
        with self.assertRaises(ValueError):self.inspect()
    def test_projected_bytes_change_rejected(self):
        p=self.inspect();p['completed_units']=0
        with self.assertRaises(ValueError):build_mnq_envelope(p)
    def test_closed_execution_identity(self):
        i=self.identity();i['pnl']=1
        with self.assertRaises(ValueError):build_mnq_envelope(self.inspect(),identity=i,measured_peak_rss_bytes=512,memory_receipt_sha256='f'*64)
    def test_write_and_ingest_once(self):
        c=self.candidate();path=self.root/'envelope.json';r=write_mnq_envelope(c,path);box=LearningOutbox(self.root/'box.sqlite');s=box.initialize()
        kw=dict(expected_sha256=r['sha256'],expected_provider='kaggle',expected_job_id='synthetic_execution_1',expected_version=1,expected_tip=s['tip'])
        a=ingest_closeout(path,box,**kw);kw['expected_tip']=a['outbox']['tip'];b=ingest_closeout(path,box,**kw);self.assertFalse(a['duplicate']);self.assertTrue(b['duplicate'])
    def test_blocked_producer_cannot_write(self):
        with self.assertRaises(ValueError):write_mnq_envelope(build_mnq_envelope(self.inspect()),self.root/'blocked.json')
        self.assertFalse((self.root/'blocked.json').exists())
    def test_exclusive_writer(self):
        c=self.candidate();p=self.root/'envelope.json';write_mnq_envelope(c,p)
        with self.assertRaises(FileExistsError):write_mnq_envelope(c,p)
    def test_unknown_envelope_fields_not_written(self):
        c=self.candidate();c['envelope']['instructions']='do not execute'
        with self.assertRaises(ValueError):write_mnq_envelope(c,self.root/'bad.json')

if __name__=='__main__':unittest.main()
