import copy,pytest
from pathlib import Path
from edgelab.research.bt2a_event_store import canonical_sha256,validate_event_checkpoint

def checkpoint():
 event={'event_id':'E1','arm':'K_ABS','contract':'GC','cme_session':'S','direction':1}; event['identity_sha256']=canonical_sha256(event)
 event2={'event_id':'E2','arm':'K_BT2','contract':'GC','cme_session':'S','direction':-1}; event2['identity_sha256']=canonical_sha256(event2)
 events=[event,event2]
 return {'status':'COMPLETE','contract':'GC','cme_session':'S','sample_registry_payload_sha256':'a','input_registry_payload_sha256':'b','events':events,'events_sha256':canonical_sha256(events)}
def test_checkpoint_identity_and_tamper_detection():
 value=checkpoint(); assert len(validate_event_checkpoint(value,contract='GC',session='S',sample_registry_sha256='a',input_registry_sha256='b'))==2
 bad=copy.deepcopy(value); bad['events'][0]['direction']=-1
 with pytest.raises(RuntimeError): validate_event_checkpoint(bad,contract='GC',session='S',sample_registry_sha256='a',input_registry_sha256='b')
def test_p2a_reasserts_gate1_eligibility():
 source=Path('tools/run_bt2a_gate2_p2a.py').read_text(); assert '~cache.eligible[abs_idx]' in source and '~cache.eligible[bt_idx]' in source
