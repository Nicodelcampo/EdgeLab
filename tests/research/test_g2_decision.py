import pytest
import edgelab.research.g2_decision as decision
from edgelab.research.g2_decision import *
A="a"*64; B="b"*64
def gate(n,p=True): return GateResult(n,p,.01,.05,B)
def primary(lo=.1): return PrimaryCI(lo,.5,.95,"stationary_bootstrap_t",197,B)
def complete(**kw):
 d=dict(decision_id="g2-1",campaign_id="camp",run_id="run",config_id="cfg",contract_sha256=A,estimand_id=ESTIMAND_ID,cluster_unit=CLUSTER_UNIT,null_id="null",gate_results=tuple(gate(n) for n in G2_REQUIRED_GATES),primary_ci=primary(),multiplicity_method="holm",n_effective=120.,created_utc="2026-08-04T00:30:00Z"); d.update(kw); return G2ValidationDecision(**d)
def dsr(p=.95,sha=A): return DSREvidence(p,"session","non_annualized",197,120.,48.,-.2,4.,"session_hac_validated",sha)
def test_dsr_umbral_y_autorizacion(monkeypatch):
 monkeypatch.setattr(decision,"AUTHORIZED_DSR_METHOD_SHA256S",frozenset({A})); assert not dsr(.949).passed and dsr(.95).passed and not dsr(.99,B).passed
def test_ic_y_gate_bloquean():
 assert not complete(primary_ci=primary(0)).passed
 assert not complete(gate_results=tuple(gate(n,n!="pbo") for n in G2_REQUIRED_GATES)).passed
def test_decision_determinista():
 a,b=complete(),complete(); assert a.passed and a.evidence_digest==b.evidence_digest and a.decision_digest==b.decision_digest
def test_reconstruye_y_no_confia_en_flags():
 raw=complete().to_dict(); assert validate_decision_dict(raw).passed
 bad=dict(raw); bad["passed"]=False
 with pytest.raises(G2DecisionError,match="passed"): validate_decision_dict(bad)
 bad=dict(raw); bad["evidence_digest"]=A
 with pytest.raises(G2DecisionError,match="evidence_digest"): validate_decision_dict(bad)
def test_sin_ic_no_promueve():
 raw=complete().to_dict(); del raw["primary_ci"]
 with pytest.raises(G2DecisionError,match="incompleta"): validate_decision_dict(raw)
def test_rechaza_semantica_incompatible():
 with pytest.raises(G2DecisionError,match="estimand"): complete(estimand_id="sharpe")
 with pytest.raises(G2DecisionError,match="cluster_unit"): complete(cluster_unit="trade")
 with pytest.raises(G2DecisionError,match="n_effective"): complete(n_effective=198)
 with pytest.raises(G2DecisionError,match="UTC"): complete(created_utc="2026-08-03T21:30:00-03:00")
 with pytest.raises(G2DecisionError,match="160 sesiones"): PrimaryCI(.1,.5,.95,"stationary_bootstrap_t",159,B)
