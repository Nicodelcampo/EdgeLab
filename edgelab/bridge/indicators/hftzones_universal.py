"""Instrument-agnostic wrapper around the frozen HFT V2 streak engine.

The certified NQ implementation remains untouched. This module makes engine
transport explicit while refusing to transport NQ parity claims.

Perfiles:
- `NQ_LITERAL_TRANSFER`: los umbrales de NQ tal cual (historico; la densidad de zonas por tick varia ~30x entre activos).
- `SCALED_FUNNEL_V1`: mismo motor, umbrales escalados por activo con `tools/calibrate_hftzones_universal_profiles.py`
  (target-free). Los valores viven en `hftzones_universal_profiles.json`, con el hash de su evidencia.
"""
from __future__ import annotations
import json
from pathlib import Path
from . import hftzones_nq as _frozen
NAME="HFTZonesUniversal"; VERSION="0.2"; ENGINE="hftzones_nq_frozen_v2_semantics"; BAR_KEY="tick_25"
LITERAL_NQ_PROFILE=dict(_frozen.ACCEPT_DEFAULTS)
LITERAL="NQ_LITERAL_TRANSFER"; SCALED="SCALED_FUNNEL_V1"
_PROFILES_PATH=Path(__file__).with_name("hftzones_universal_profiles.json")
def _scaled_table()->dict:
    if not _PROFILES_PATH.exists(): raise FileNotFoundError(f"{_PROFILES_PATH.name} missing: run tools/calibrate_hftzones_universal_profiles.py")
    d=json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))
    if d.get("name")!=SCALED: raise ValueError("profile table name mismatch")
    return d["profiles"]
def profile(profile_name: str=LITERAL, instrument: str|None=None)->dict:
    if profile_name==LITERAL: return dict(LITERAL_NQ_PROFILE)
    if profile_name==SCALED:
        if instrument is None: raise ValueError(f"{SCALED} is per-instrument: pass instrument")
        table=_scaled_table()
        if instrument not in table: raise ValueError(f"no {SCALED} profile for {instrument}")
        return {k:v for k,v in table[instrument].items() if k in LITERAL_NQ_PROFILE}
    raise ValueError(f"unknown frozen profile: {profile_name}")
def detect_candidates(*args,**kwargs): return _frozen.detect_candidates(*args,**kwargs)
def accept_all(candidates,thresholds=None,tick_size=0.25): return _frozen.accept_all(candidates,thresholds,tick_size)
def transfer_status(instrument:str,explicit_parity_status:str|None=None,profile_name:str=LITERAL)->dict:
    parity=explicit_parity_status or "PARITY_ABSTAIN"
    if profile_name==SCALED: param="NQ_LITERAL_PROFILE" if instrument=="NQ" else "SCALED_FUNNEL_V1_TARGET_FREE"
    else: param="NQ_LITERAL_PROFILE" if instrument=="NQ" else "PARAMETERS_UNCALIBRATED"
    return {"engine_status":"ENGINE_PORTABLE","parameter_status":param,"parity_status":parity}
