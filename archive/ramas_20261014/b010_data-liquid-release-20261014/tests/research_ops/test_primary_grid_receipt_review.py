import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from tools.research_ops.audits.review_primary_grid_receipt import review,PLAN,INTS,FLOATS,STAGES,PROGRAMS,plan_hash
class ReceiptReviewTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'receipt.json';self.programs={p:'b'*64 for p in PROGRAMS};self.r={'schema':'mnq_full_primary_grid_parity_v1','plan':copy.deepcopy(PLAN),'plan_sha256':plan_hash(),'rows_checked':11340,'empty_rows':0,'sessions':46,'private_input_rows':68499,'integer_fields_checked':INTS,'float_fields_checked_exact_roundtrip':FLOATS,'reference_sha256':PLAN['inputs']['effects']['sha256'],'counts_sha256':'a'*64,'results_sha256':'a'*64,'draws_sha256':'a'*64,'stage_seconds':{p:1. for p in STAGES},'wall_seconds':10.,'outer_seconds':11.,'ru_maxrss_bytes':1000000,'rss_scope':'SELF_HIGH_WATER_TECHNICAL_REPLAY_ONLY_NOT_ORIGINAL_JOB','python':'3.11.1','numpy':'2.0.1','pandas':'2.1.1','exact_parity':True,'full_pipeline_parity':False,'matched_contrast_parity':False,'longevity_detector_profiled':False,'private_rows_exported':False,'validated_edge':False,'adoption_authorized':False,'source_checkpoint':'c'*40,'program_sha256':self.programs}
 def tearDown(self):self.t.cleanup()
 def call(self):
  b=json.dumps(self.r).encode();self.p.write_bytes(b);return review(self.p,expected_receipt_sha256=hashlib.sha256(b).hexdigest(),expected_source_commit='c'*40,expected_program_sha256=self.programs)
 def test_valid_no_authority(self):
  r=self.call();self.assertFalse(r['authenticated_custody']);self.assertFalse(r['adoption_authorized']);self.assertEqual(r['fields_per_row'],19)
 def test_missing_or_extra_fields(self):
  self.r['extra']='x'
  with self.assertRaises(ValueError):self.call()
 def test_wrong_source(self):
  self.r['source_checkpoint']='d'*40
  with self.assertRaises(ValueError):self.call()
 def test_partial_grid(self):
  self.r['rows_checked']=60
  with self.assertRaises(ValueError):self.call()
 def test_self_promotion(self):
  self.r['adoption_authorized']=True
  with self.assertRaises(ValueError):self.call()
 def test_missing_bands(self):
  self.r['float_fields_checked_exact_roundtrip']=['target_percent']
  with self.assertRaises(ValueError):self.call()
 def test_bad_time_accounting(self):
  self.r['stage_seconds']['count_formation']=100
  with self.assertRaises(ValueError):self.call()
 def test_bad_hash(self):
  self.r['results_sha256']='x'*64
  with self.assertRaises(ValueError):self.call()

 def test_boolean_alias_in_plan(self):
  self.r['plan']['adoption_authorized']=0
  with self.assertRaises(ValueError):self.call()
