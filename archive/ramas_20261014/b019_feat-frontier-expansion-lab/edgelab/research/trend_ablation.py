"""Deterministic, pre-outcome ablation manifest for trend/carrier interactions."""
from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass
from enum import Enum
from edgelab.research.trend_carriers import CarrierMechanism,CarrierSource
from edgelab.research.trend_context import TrendParameters
CONTRACT_VERSION="TREND_ABLATION_MANIFEST_V1"; NORTH_STAR_SHA256="d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"
class ContextCell(str,Enum):
    CARRIER_ONLY="CARRIER_ONLY"; EMA_ONLY="EMA_ONLY"; SMA_ONLY="SMA_ONLY"; VWAP_ONLY="VWAP_ONLY"; ALL_COMPONENTS="ALL_COMPONENTS"; SHUFFLED_ALL_WITHIN_SESSION="SHUFFLED_ALL_WITHIN_SESSION"
@dataclass(frozen=True,slots=True)
class CarrierHypothesis: source:CarrierSource; mechanism:CarrierMechanism
@dataclass(frozen=True,slots=True)
class AblationCell: cell_id:str; hypothesis:CarrierHypothesis; context_cell:ContextCell; parameter_set_index:int; placebo:bool
@dataclass(frozen=True,slots=True)
class TrendAblationManifest:
    contract_version:str; north_star_sha256:str; parameter_sets:tuple[TrendParameters,...]; cells:tuple[AblationCell,...]; shuffle_seed:int; shuffle_replicates:int; policy_count:int; outcome_access:str; holdout_access:str; digest:str
DEFAULT_HYPOTHESES=(CarrierHypothesis(CarrierSource.BIGTRAP2,CarrierMechanism.TRAPPED_AGGRESSOR_FADE),CarrierHypothesis(CarrierSource.BIGTRAP2_ABSORPTION,CarrierMechanism.TRAPPED_AGGRESSOR_FADE),CarrierHypothesis(CarrierSource.HFTZONES2,CarrierMechanism.FORMATION_CONTINUATION),CarrierHypothesis(CarrierSource.HFTZONES2,CarrierMechanism.ZONE_BOUNCE),CarrierHypothesis(CarrierSource.HFTZONES2,CarrierMechanism.CONFIRMED_ZONE_BREACH),CarrierHypothesis(CarrierSource.HFTZONES_NQ_V2,CarrierMechanism.FORMATION_CONTINUATION),CarrierHypothesis(CarrierSource.HFTZONES_NQ_V2,CarrierMechanism.ZONE_BOUNCE),CarrierHypothesis(CarrierSource.HFTZONES_NQ_V2,CarrierMechanism.CONFIRMED_ZONE_BREACH))
def build_manifest(*,hypotheses=DEFAULT_HYPOTHESES,parameter_sets=(TrendParameters(),),shuffle_seed=20260921,shuffle_replicates=100):
    if not hypotheses or not parameter_sets: raise ValueError("hypotheses and parameter_sets are required")
    if len(set(hypotheses))!=len(hypotheses): raise ValueError("duplicate hypotheses are forbidden")
    if len(set(parameter_sets))!=len(parameter_sets): raise ValueError("duplicate parameter sets are forbidden")
    if shuffle_seed<0 or shuffle_replicates<1: raise ValueError("invalid shuffle contract")
    cells=tuple(AblationCell(f"P{pi}:{h.source.value}:{h.mechanism.value}:{cc.value}",h,cc,pi,cc is ContextCell.SHUFFLED_ALL_WITHIN_SESSION) for pi,_ in enumerate(parameter_sets) for h in hypotheses for cc in ContextCell)
    p=dict(contract_version=CONTRACT_VERSION,north_star_sha256=NORTH_STAR_SHA256,parameter_sets=[asdict(x) for x in parameter_sets],cells=[dict(cell_id=c.cell_id,source=c.hypothesis.source.value,mechanism=c.hypothesis.mechanism.value,context_cell=c.context_cell.value,parameter_set_index=c.parameter_set_index,placebo=c.placebo) for c in cells],shuffle_seed=shuffle_seed,shuffle_replicates=shuffle_replicates,outcome_access="FORBIDDEN_UNTIL_EXPLICIT_AUTHORIZATION",holdout_access="SEALED")
    d=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return TrendAblationManifest(CONTRACT_VERSION,NORTH_STAR_SHA256,parameter_sets,cells,shuffle_seed,shuffle_replicates,len(cells),p["outcome_access"],p["holdout_access"],d)
