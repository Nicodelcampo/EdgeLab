import pytest
import edgelab.research.g2_decision as decision
from edgelab.research.g2_decision import *

A="a"*64; B="b"*64

def gate(name,passed=True): return GateResult(name,passed,.01,.05,B)
def primary(lower=.1): return PrimaryCI(lower,.5,.95,"stationary_bootstrap_t",197,B)
def complete(**changes):
    data=dict(decision_id="g2-1",campaign_id="camp-1",run_id="run-1",config_id="cfg-1",contract_sha256=A,estimand_id=ESTIMAND_ID,cluster_unit=CLUSTER_UNIT,null_id="null-1",gate_results=tuple(gate(n) for n in G2_REQUIRED_GATES),primary_ci=primary(),multiplicity_method="holm",n_effective=120.,created_utc="2026-08-04T00:30:00Z")
    data.update(changes); return G2ValidationDecision(**data)
def dsr(p=.95,sha=A): return DSREvidence(p,"session","non_annualized",197,120.,48.,-.2,4.,"session_hac_validated",sha)

def test_dsr_umbral_inclusivo_y_metodo_autorizado(monkeypatch):
    monkeypatch.setattr(decision,"AUTHORIZED_DSR_METHOD_SHA256S",frozenset({A}))
    assert not dsr(.949999).passed and dsr(.95).passed and not dsr(.99,B).passed

def test_dsr_exige_sesion_escala_y_dependencia():
    with pytest.raises(G2DecisionError,match="session"): DSREvidence(.99,"trade","non_annualized",197,120,48,0,3,"hac",A)
    with pytest.raises(G2DecisionError,match="non_annualized"): DSREvidence(.99,"session","annualized",197,120,48,0,3,"hac",A)
    with pytest.raises(G2DecisionError,match="dependence_method"): DSREvidence(.99,"session","non_annualized",197,120,48,0,3,"",A)

def test_decision_exige_gates_exactos_y_ordenados():
    with pytest.raises(G2DecisionError,match="exactamente"): complete(gate_results=tuple(gate(n) for n in reversed(G2_REQUIRED_GATES)))

def test_ic_primario_bloquea_aunque_cinco_pasaron():
    x=complete(primary_ci=primary(0)); assert not x.passed and x.to_dict()["passed"] is False

def test_un_gate_false_bloquea():
    assert not complete(gate_results=tuple(gate(n,n!="pbo") for n in G2_REQUIRED_GATES)).passed

def test_decision_determinista_y_persistible():
    a,b=complete(),complete(); assert a.passed and a.evidence_digest==b.evidence_digest and a.decision_digest==b.decision_digest
    assert a.to_dict()["required_gates"]==list(G2_REQUIRED_GATES)

def test_rechaza_estimando_cluster_neff_y_hora():
    with pytest.raises(G2DecisionError,match="estimand"): complete(estimand_id="sharpe")
    with pytest.raises(G2DecisionError,match="cluster_unit"): complete(cluster_unit="trade")
    with pytest.raises(G2DecisionError,match="n_effective"): complete(n_effective=198)
    with pytest.raises(G2DecisionError,match="UTC"): complete(created_utc="2026-08-03T21:30:00-03:00")

def test_ic_rechaza_menos_de_160_sesiones():
    with pytest.raises(G2DecisionError,match="160 sesiones"): PrimaryCI(.1,.5,.95,"stationary_bootstrap_t",159,B)
