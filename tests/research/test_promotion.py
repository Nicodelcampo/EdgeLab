from __future__ import annotations
import json
import pytest
import edgelab.research.promotion as promotion
from edgelab.research.g2_decision import CLUSTER_UNIT, ESTIMAND_ID, G2_REQUIRED_GATES, G2ValidationDecision, GateResult, PrimaryCI
from edgelab.research.promotion import PromotionError, RegistryIntegrityError, append_record, current_status, load_registry, validate_record
A="a"*64; B="b"*64
@pytest.fixture(autouse=True)
def approved(monkeypatch): monkeypatch.setattr(promotion,"APPROVED_G2_CONTRACT_SHA256S",frozenset({A}))
def record(record_id,candidate="edge-1",status="idea",**extra):
 row=dict(record_id=record_id,candidate_id=candidate,status=status,recorded_utc="2026-08-04T03:00:00Z",reason="fixture",evidence_refs=[]); row.update(extra); return row
def canonical_decision(*,campaign="camp-1",run="run-1",config="cfg-1",lower=.1,failed_gate=None,contract=A):
 gates=tuple(GateResult(n,n!=failed_gate,1.,0.,B) for n in G2_REQUIRED_GATES)
 return G2ValidationDecision("g2-1",campaign,run,config,contract,ESTIMAND_ID,CLUSTER_UNIT,"null-1",gates,PrimaryCI(lower,.5,.95,"stationary_bootstrap_t",197,B),"holm",120.,"2026-08-04T03:00:00Z").to_dict()
def supported(record_id="r4",**extra):
 base=dict(campaign_id="camp-1",run_id="run-1",config_id="cfg-1",validation_decision=canonical_decision()); base.update(extra); return record(record_id,status="statistically_supported",**base)
def advance(path):
 append_record(path,record("r1")); append_record(path,record("r2",status="technically_valid")); append_record(path,record("r3",status="exploratory_candidate"))
def test_estados_previos_no_exigen_g2():
 for status in ("external_candidate","idea","technically_valid","exploratory_candidate"): validate_record(record("r-"+status,status=status))
def test_promocion_canonica_valida(): validate_record(supported())
def test_no_confia_en_passed_recibido():
 raw=canonical_decision(); raw["passed"]=False
 with pytest.raises(PromotionError,match="passed"): validate_record(supported(validation_decision=raw))
def test_no_confia_en_evidence_digest_recibido():
 raw=canonical_decision(); raw["evidence_digest"]=A
 with pytest.raises(PromotionError,match="evidence_digest"): validate_record(supported(validation_decision=raw))
def test_ic_primario_ausente_bloquea():
 raw=canonical_decision(); del raw["primary_ci"]
 with pytest.raises(PromotionError,match="incompleta"): validate_record(supported(validation_decision=raw))
def test_ic_con_cota_no_positiva_bloquea():
 with pytest.raises(PromotionError,match="no aprobo"): validate_record(supported(validation_decision=canonical_decision(lower=0)))
def test_gate_fallido_bloquea():
 with pytest.raises(PromotionError,match="no aprobo"): validate_record(supported(validation_decision=canonical_decision(failed_gate="dsr")))
@pytest.mark.parametrize("field,kw",[("campaign_id",{"campaign":"otra"}),("run_id",{"run":"otro"}),("config_id",{"config":"otra"})])
def test_identidad_de_registro_y_decision_debe_coincidir(field,kw):
 with pytest.raises(PromotionError,match=field): validate_record(supported(validation_decision=canonical_decision(**kw)))
def test_contrato_no_aprobado_congela(monkeypatch):
 monkeypatch.setattr(promotion,"APPROVED_G2_CONTRACT_SHA256S",frozenset())
 with pytest.raises(PromotionError,match="no aprobado"): validate_record(supported())
def test_forma_superficial_anterior_ya_no_alcanza():
 raw=dict(decision_id="g2",gate="G2",passed=True,contract_sha256=A,evidence_digest=B,required_gates=list(G2_REQUIRED_GATES),gate_results={n:{"passed":True} for n in G2_REQUIRED_GATES})
 with pytest.raises(PromotionError,match="incompleta|mal formada"): validate_record(supported(validation_decision=raw))
def test_secuencia_completa_append_only(tmp_path):
 p=tmp_path/"r.jsonl"; advance(p); append_record(p,supported()); assert current_status(p,"edge-1")=="statistically_supported"; assert len(load_registry(p))==4
def test_no_salto_de_gate(tmp_path):
 p=tmp_path/"r.jsonl"; append_record(p,record("r1"))
 with pytest.raises(PromotionError,match="salto|transicion"): append_record(p,supported("r2"))
def test_integridad_detecta_alteracion(tmp_path):
 p=tmp_path/"r.jsonl"; append_record(p,record("r1")); row=json.loads(p.read_text()); row["reason"]="alterado"; p.write_text(json.dumps(row)+"\n")
 with pytest.raises(RegistryIntegrityError,match="record_digest"): load_registry(p)
def test_terminal_no_reabre(tmp_path):
 p=tmp_path/"r.jsonl"; append_record(p,record("r1")); append_record(p,record("r2",status="failed"))
 with pytest.raises(PromotionError,match="terminal"): append_record(p,record("r3"))
def test_timestamp_utc_y_campos_sistema():
 with pytest.raises(PromotionError,match="UTC"): validate_record(record("x",recorded_utc="2026-08-04T00:00:00-03:00"))
 with pytest.raises(PromotionError,match="campos de integridad"): validate_record(record("x",record_digest="x"),allow_system_fields=False)
