"""Preflight fail-closed entre el censo de tasas y EXPLORE-001."""
from __future__ import annotations
class ExplorePreflightError(ValueError): pass
def audit_event_policy(run_manifest,*,primary_event_policy):
    """Impide usar una tasa de otra población para congelar H1-H3."""
    if not isinstance(run_manifest,dict): raise ExplorePreflightError("run_manifest debe ser objeto")
    config=run_manifest.get("configuration")
    if not isinstance(config,dict): raise ExplorePreflightError("falta configuration")
    census_policy=config.get("event_anchor_policy")
    if not isinstance(census_policy,str) or not census_policy: raise ExplorePreflightError("falta event_anchor_policy")
    if not isinstance(primary_event_policy,str) or not primary_event_policy: raise ExplorePreflightError("primary_event_policy debe ser texto")
    matched=census_policy==primary_event_policy
    return {"status":"PASS" if matched else "BLOCKED_EVENT_POLICY_MISMATCH","census_event_policy":census_policy,"primary_event_policy":primary_event_policy,"may_freeze_hypotheses":matched,"reason":"misma poblacion operacional" if matched else "la tasa censada no corresponde a la poblacion primaria"}
