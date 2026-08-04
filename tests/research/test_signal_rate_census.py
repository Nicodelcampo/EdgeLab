from __future__ import annotations
import pytest
from diag.tasa_senales.audit_post_sepmin import CensusAuditError,audit
from diag.tasa_senales.census_plan import CensusPlanError,build_full_plan,build_run_manifest
from diag.tasa_senales.explore_preflight import audit_event_policy
def contract(dates,counts,name="BigTrap2"): return {"fechas":dates,"ind":{name:{"n_dias":len(dates),"post_por_dia":dict(zip(dates,counts))}}}
def test_piloto_parcial_no_cierra_el_censo():
 r=audit({"c1":contract(["d1","d2"],[8,10])},expected_days=4); assert r["status"]=="INSUFFICIENT"; assert r["observed_unique_days"]==2
def test_censo_completo_agrega_numerador_y_dias_no_medias_de_contrato():
 r=audit({"c1":contract(["d1"],[10]),"c2":contract(["d2","d3","d4"],[1,2,3])},expected_days=4); assert r["status"]=="COMPLETE"; assert r["indicators"]["BigTrap2"]["mean_per_day"]==4
def test_sesiones_duplicadas_entre_contratos_fallan():
 with pytest.raises(CensusAuditError): audit({"c1":contract(["d1"],[1]),"c2":contract(["d1"],[1])},expected_days=1)
def test_plan_incluye_todas_las_sesiones():
 assert build_full_plan([{"fecha":"d2","archivo":"b"},{"fecha":"d1","archivo":"a"}])==[("a",["d1"]),("b",["d2"])]
def test_plan_falla_si_una_sesion_aparece_en_dos_contratos():
 with pytest.raises(CensusPlanError): build_full_plan([{"fecha":"d1","archivo":"a"},{"fecha":"d1","archivo":"b"}])
def manifest(): return build_run_manifest(plan=[("a",["d1"])],universe_sha256="a"*64,output_sha256="b"*64,code_commit="c"*40,universe_info={},indicators=["BigTrap2"],generated_utc="2026-08-04T03:00:00Z")
def test_run_manifest_declara_poblacion_y_cero_outcomes():
 m=manifest(); assert m["configuration"]["outcomes_accessed"] is False; assert m["configuration"]["event_anchor_policy"]=="zone_created_ms"
def test_censo_de_creaciones_no_congela_primer_toque():
 r=audit_event_policy(manifest(),primary_event_policy="first_touch_after_creation_bar"); assert r["status"]=="BLOCKED_EVENT_POLICY_MISMATCH"; assert not r["may_freeze_hypotheses"]
def test_preflight_pasa_solo_con_misma_poblacion():
 assert audit_event_policy(manifest(),primary_event_policy="zone_created_ms")["status"]=="PASS"
