from edgelab.research.bt2a_gate_l2 import validate_run_identity
from tools.validate_bt2a_gate_l2_package import declared_artifact_hashes,match_declared_hash

def clean_manifest():
 return {'status':'COMPLETE_TARGET_FREE_CONTEXT_EXTRACTION','model_id':'m','CAMPAIGN_OUTCOMES_OPENED':False,'EDGE_DECLARED':False,'code_commit_start':'a','code_commit_end':'a','dirty_start':False,'dirty_end':False}

def test_identity_requires_model_id_in_all_three_artifacts():
 assert not validate_run_identity(clean_manifest(),{'model_id':'m'},{} )['identity_ready']
 assert validate_run_identity(clean_manifest(),{'model_id':'m'},{'model_id':'m'})['identity_ready']

def test_hash_inventory_normalizes_and_matches_basename():
 digest='a'*64; manifest={'artifacts':{'labels':{'path':'out/gate_l2_context_labels.parquet','sha256':digest}}}
 declared=declared_artifact_hashes(manifest)
 assert match_declared_hash(declared,'gate_l2_context_labels.parquet')==digest
 assert match_declared_hash(declared,'other.parquet') is None
