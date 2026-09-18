"""Instrument-agnostic wrapper around the frozen HFT V2 streak engine.

The certified NQ implementation remains untouched. This module makes engine
transport explicit while refusing to transport NQ parity or calibration claims.
"""
from __future__ import annotations
from . import hftzones_nq as _frozen
NAME="HFTZonesUniversal"; VERSION="0.1"; ENGINE="hftzones_nq_frozen_v2_semantics"; BAR_KEY="tick_25"
LITERAL_NQ_PROFILE=dict(_frozen.ACCEPT_DEFAULTS)
def profile(profile_name: str="NQ_LITERAL_TRANSFER")->dict:
    if profile_name!="NQ_LITERAL_TRANSFER": raise ValueError(f"unknown frozen profile: {profile_name}")
    return dict(LITERAL_NQ_PROFILE)
def detect_candidates(*args,**kwargs): return _frozen.detect_candidates(*args,**kwargs)
def accept_all(candidates,thresholds=None,tick_size=0.25): return _frozen.accept_all(candidates,thresholds,tick_size)
def transfer_status(instrument:str,explicit_parity_status:str|None=None)->dict:
    parity=explicit_parity_status or "PARITY_ABSTAIN"
    return {"engine_status":"ENGINE_PORTABLE","parameter_status":("NQ_LITERAL_PROFILE" if instrument=="NQ" else "PARAMETERS_UNCALIBRATED"),"parity_status":parity}
