import json
import numpy as np
import pytest
from edgelab.funnel.device import detect_device
from edgelab.funnel.hypothesis import HypothesisProposal
from edgelab.funnel.screen import cheap_screen,iter_screen_batches
from edgelab.funnel.splits import make_splits,mask_for
from edgelab.funnel.ledger import FunnelLedger

def test_d2_fail_closed():
    td=np.repeat(np.arange(20260101,20260121),2);s=make_splits(td)
    with pytest.raises(PermissionError):mask_for(s,td,'D2')
    assert mask_for(s,td,'D2',unlock_token=s.split_hash).any()
def test_llm_proposal_not_evidence():
    with pytest.raises(ValueError):HypothesisProposal('h','f','economic mechanism long enough',{}, {}, {}, {},('shuffle',),('L1',),4)
    with pytest.raises(ValueError):HypothesisProposal('h','f','economic mechanism long enough',{}, {}, {}, {},('shuffle',),('L1',),1,True)
def test_cpu_screen_known_paths():
    h=np.array([100,100,112,100,100,100],np.int32);l=np.array([100,99,99,88,100,100],np.int32);bo=np.full(6,99,np.int32);ao=np.full(6,101,np.int32)
    out,dev=cheap_screen(np.array([0,2]),np.array([1,-1],np.int8),h,l,bo,ao,np.array([10]),np.array([10]),max_hold_bars=2,backend='cpu')
    assert dev.backend=='cpu' and out.shape==(2,1)
    batches=list(iter_screen_batches(np.array([0,2]),np.array([1,-1],np.int8),h,l,bo,ao,
                                     np.array([10,10,10]),np.array([10,11,12]),
                                     backend='cpu',max_matrix_bytes=16))
    assert [(a,b) for a,b,_,_ in batches]==[(0,1),(1,2),(2,3)]
    assert all(matrix.nbytes <= 16 for _,_,matrix,_ in batches)
def test_hash_chain_detects_tamper(tmp_path):
    p=tmp_path/'ledger.jsonl';x=FunnelLedger(p);x.append('trial_recorded','a',{'asserts_edge':False});assert x.verify()['valid']
    rows=p.read_text().splitlines();r=json.loads(rows[0]);r['payload']['asserts_edge']=True;p.write_text(json.dumps(r)+'\n');assert not x.verify()['valid']
