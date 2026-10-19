"""HP-007 campaign-v2 primitives: causal horizons, weighting, ablations and audit gates."""
from __future__ import annotations

import hashlib, json, math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np

CT = ZoneInfo("America/Chicago")
UTC = ZoneInfo("UTC")

class CampaignV2Error(ValueError): pass

@dataclass(frozen=True)
class ZoneState:
    zone_id: str; source: str; side: int; lower_tick: int; upper_tick: int
    created_ns: int; available_ns: int; strength: float; touches_asof: int = 0
    invalidated_asof: bool = False

@dataclass(frozen=True)
class WeightSpec:
    strength_mode: str = "power"
    strength_power: float = .25
    maturation_hours: float = 1.0
    decay_starts_hours: float = 4.0
    half_life_hours: float = 12.0
    wear_coeff: float = .5
    wear_power: float = .6
    invalidation_penalty: float = .35
    use_maturation: bool = True
    use_time_decay: bool = True
    use_wear: bool = True

@dataclass(frozen=True)
class FieldSpec:
    sigma_ticks: float = 1.2
    span_ticks: int = 14
    combine_sources: str = "sum"
    source_weights: tuple[tuple[str,float], ...] = ()


def canonical_sha256(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",",":"), default=str).encode()).hexdigest()


def cme_trade_date(ts_ns: int) -> str:
    local = datetime.fromtimestamp(ts_ns / 1e9, UTC).astimezone(CT)
    d = local.date() + (timedelta(days=1) if local.hour >= 17 else timedelta())
    while d.weekday() >= 5: d += timedelta(days=1)
    return d.isoformat()


def validate_tick_order(ts_ns: Sequence[int], sequence: Sequence[int]) -> None:
    if len(ts_ns) != len(sequence) or len(ts_ns) == 0: raise CampaignV2Error("timestamps and sequence required")
    t, q = np.asarray(ts_ns, np.int64), np.asarray(sequence, np.int64)
    if np.any(t <= 0): raise CampaignV2Error("non-positive timestamp")
    bad = (t[1:] < t[:-1]) | ((t[1:] == t[:-1]) & (q[1:] <= q[:-1]))
    if np.any(bad): raise CampaignV2Error(f"tick order violation at {int(np.flatnonzero(bad)[0])+1}")


def causal_horizon_indices(ts_ns: Sequence[int], decision_ns: int, horizon_ns: int, session_end_ns: int) -> tuple[int,int,bool]:
    if horizon_ns <= 0: raise CampaignV2Error("positive horizon required")
    t = np.asarray(ts_ns, np.int64)
    start = int(np.searchsorted(t, decision_ns, side="right"))
    boundary = min(decision_ns + horizon_ns, session_end_ns)
    end = int(np.searchsorted(t, boundary, side="right"))
    complete = bool(len(t) and t[-1] >= boundary)
    return start, end, complete


def _strength(x: float, spec: WeightSpec, ref: float) -> float:
    r=max(ref,1e-12); z=max(x,0.0)/r
    if spec.strength_mode=="count": return 1.0
    if spec.strength_mode=="power": return z**spec.strength_power
    if spec.strength_mode=="sqrt": return math.sqrt(z)
    if spec.strength_mode=="log": return math.log1p(z)/math.log(2)
    if spec.strength_mode=="winsorized_power": return min(z,3.0)**spec.strength_power
    raise CampaignV2Error("unknown strength_mode")


def zone_weight(z: ZoneState, decision_ns: int, spec: WeightSpec, ref_strength: float=20.0) -> float:
    if z.created_ns > z.available_ns or z.available_ns > decision_ns: raise CampaignV2Error("non-causal zone")
    age=max(0.0,(decision_ns-z.created_ns)/3.6e12)
    mat=1.0 if not spec.use_maturation else (1.0 if age>=spec.maturation_hours else .35+.65*age/max(spec.maturation_hours,1e-9))
    dec=1.0 if (not spec.use_time_decay or age<=spec.decay_starts_hours) else 2**(-(age-spec.decay_starts_hours)/spec.half_life_hours)
    wear=1.0 if not spec.use_wear else (1/(1+spec.wear_coeff*z.touches_asof))**spec.wear_power
    inv=spec.invalidation_penalty if z.invalidated_asof else 1.0
    return _strength(z.strength,spec,ref_strength)*mat*dec*wear*inv


def ablation_specs(base: WeightSpec) -> dict[str,WeightSpec]:
    return {"FULL":base,"NO_MATURATION":replace(base,use_maturation=False),"NO_TIME_DECAY":replace(base,use_time_decay=False),"NO_WEAR":replace(base,use_wear=False)}


def directional_field(price_tick:int,direction:int,zones:Iterable[ZoneState],decision_ns:int,weight:WeightSpec,field:FieldSpec) -> tuple[np.ndarray,np.ndarray]:
    if direction not in (-1,1) or field.sigma_ticks<0: raise CampaignV2Error("invalid field")
    pts=np.array([price_tick+direction*k for k in range(1,field.span_ticks+1)])
    by_source:dict[str,np.ndarray]={}; sw=dict(field.source_weights)
    for z in zones:
        if z.available_ns>decision_ns: continue
        arr=by_source.setdefault(z.source,np.zeros(len(pts)))
        dist=np.maximum(0,np.maximum(z.lower_tick-pts,pts-z.upper_tick))
        kernel=(dist==0).astype(float) if field.sigma_ticks==0 else np.exp(-(dist**2)/(2*field.sigma_ticks**2))
        arr += sw.get(z.source,1.0)*zone_weight(z,decision_ns,weight)*kernel
    if not by_source:return pts,np.zeros(len(pts))
    stacks=np.stack(list(by_source.values()))
    if field.combine_sources=="sum": raw=stacks.sum(axis=0)
    elif field.combine_sources=="max": raw=stacks.max(axis=0)
    elif field.combine_sources=="noisy_or": return pts,1-np.prod(np.exp(-stacks),axis=0)
    elif field.combine_sources=="consensus_product": raw=np.prod(1-np.exp(-stacks),axis=0)
    else: raise CampaignV2Error("unknown source combiner")
    return pts,1-np.exp(-raw)


def required_resamples_for_holm(n_tests:int,alpha:float=.05)->int:
    if n_tests<1 or not 0<alpha<1: raise CampaignV2Error("invalid multiplicity inputs")
    return math.floor(n_tests/alpha)


def assert_permutation_resolution(n_resamples:int,n_tests:int,alpha:float=.05)->None:
    need=required_resamples_for_holm(n_tests,alpha)
    if n_resamples<=need: raise CampaignV2Error(f"{n_resamples} resamples cannot pass Holm; require > {need}")


def economic_labels(candidate_net_r:float,control_net_r:float)->list[str]:
    out=[]
    if candidate_net_r<=0: out.append("FAIL_ABSOLUTE_NET_EXPECTANCY_NONPOSITIVE")
    if candidate_net_r<=control_net_r: out.append("FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL")
    return out


def cache_key(*,data_sha256:str,code_sha256:str,params:Mapping[str,object],contract:str)->str:
    return canonical_sha256({"data":data_sha256,"code":code_sha256,"params":params,"contract":contract})


def zero_event_status(n_pairs:int)->str:
    return "ABSTAIN_NO_CAUSAL_EVENTS" if n_pairs==0 else "EVALUABLE"


@dataclass
class CampaignState:
    """Encapsulates active mutable state of the HP-007 campaign.

    Enforces mandatory zeroing of indicator state, active zones, touches, fields,
    normalizers, frozen corridors, and pending matches whenever a contract roll
    or state_reset_flag == True occurs.
    """
    active_zones: list[ZoneState]
    touches: dict[str, int]
    field_cache: dict[str, object]
    normalizers: dict[str, object]
    frozen_corridors: list[object]
    active_episodes: list[object]
    indicator_state: dict[str, object]

    def reset_on_roll(self) -> list[object]:
        """Terminate active episodes with CENSORED_CONTRACT_ROLL and wipe all state. Fail closed."""
        terminated_episodes = []
        for ep in self.active_episodes:
            if isinstance(ep, dict):
                c = dict(ep)
                c["terminal"] = "CENSORED_CONTRACT_ROLL"
                c["stage_at_censoring"] = c.get("stage_at_censoring") or "ACTIVE_AT_ROLL"
                terminated_episodes.append(c)
            elif hasattr(ep, "terminal"):
                try:
                    kwargs = {"terminal": "CENSORED_CONTRACT_ROLL"}
                    if hasattr(ep, "stage_at_censoring") and getattr(ep, "stage_at_censoring") is None:
                        kwargs["stage_at_censoring"] = "ACTIVE_AT_ROLL"
                    terminated_episodes.append(replace(ep, **kwargs))
                except Exception as exc:
                    raise CampaignV2Error(f"cannot censor active episode at roll: {type(ep)!r}") from exc
            else:
                raise CampaignV2Error(f"cannot censor active episode at roll: {type(ep)!r}")

        self.active_zones.clear()
        self.touches.clear()
        self.field_cache.clear()
        self.normalizers.clear()
        self.frozen_corridors.clear()
        self.active_episodes.clear()
        self.indicator_state.clear()
        return terminated_episodes


def reset_campaign_state_on_roll(state: CampaignState) -> list[object]:
    """Executable helper to execute state wipe at roll boundary."""
    return state.reset_on_roll()


class CampaignProcessor:
    """Canonical stream processor orchestrator scaffold for HP-007.

    Status: ROLL_SAFE_PROCESSOR_SCAFFOLD = IMPLEMENTED.
    Enforces mandatory strict processing order:
    1. Inspect state_reset_flag FIRST.
    2. If state_reset_flag is True:
       a. Censor all active episodes from previous regime as CENSORED_CONTRACT_ROLL.
       b. Persist / emit those censored episodes into censored_at_rolls.
       c. Wipe all state (zones, touches, fields, normalizers, corridors, indicator state).
       d. Initialize new contract regime.
    3. Only after state wipe, process the tick in the new regime.
       - Increment touches for active zones containing price_tick.
       - Execute optional on_tick_hook if provided.
    """

    def __init__(self, state: CampaignState | None = None) -> None:
        self.state = state if state is not None else CampaignState(
            active_zones=[],
            touches={},
            field_cache={},
            normalizers={},
            frozen_corridors=[],
            active_episodes=[],
            indicator_state={},
        )
        self.censored_at_rolls: list[object] = []
        self.processed_ticks_count: int = 0
        self.last_reset_tick_index: int | None = None

    def add_zone(self, zone: ZoneState) -> None:
        """Register an active zone in the current regime."""
        self.state.active_zones.append(zone)
        if zone.zone_id not in self.state.touches:
            self.state.touches[zone.zone_id] = 0

    def add_corridor(self, corridor: object) -> None:
        """Register a frozen corridor in the current regime."""
        self.state.frozen_corridors.append(corridor)

    def add_episode(self, episode: object) -> None:
        """Register an active episode in the current regime."""
        self.state.active_episodes.append(episode)

    def process_tick(
        self,
        ts_ns: int,
        price_tick: int,
        volume: float,
        sequence: int,
        state_reset_flag: bool = False,
        session_id: object = None,
        on_tick_hook: object | None = None,
    ) -> dict[str, object]:
        # 1. Inspect state_reset_flag FIRST
        if state_reset_flag:
            # 2. Censor episodes of previous regime & 3. Persist & 4. Wipe state
            censored = self.state.reset_on_roll()
            self.censored_at_rolls.extend(censored)
            self.last_reset_tick_index = self.processed_ticks_count
            # 5. Initialize new regime
            self.state.indicator_state["regime_initialized"] = True
            self.state.indicator_state["regime_start_ts_ns"] = ts_ns

        # 6. Only after reset, process tick in the active regime
        # Update zone touches if price falls within active zone boundaries
        for zone in self.state.active_zones:
            low = getattr(zone, "lower_tick", getattr(zone, "bottom_tick", None))
            high = getattr(zone, "upper_tick", getattr(zone, "top_tick", None))
            if low is not None and high is not None and low <= price_tick <= high:
                self.state.touches[zone.zone_id] = self.state.touches.get(zone.zone_id, 0) + 1

        tick_record = {
            "ts_ns": ts_ns,
            "price_tick": price_tick,
            "volume": volume,
            "sequence": sequence,
            "state_reset_flag": state_reset_flag,
            "session_id": session_id,
            "active_zones_count": len(self.state.active_zones),
            "active_episodes_count": len(self.state.active_episodes),
            "censored_roll_events_count": len(self.censored_at_rolls),
        }

        if callable(on_tick_hook):
            on_tick_hook(self.state, tick_record)

        self.processed_ticks_count += 1
        return tick_record

