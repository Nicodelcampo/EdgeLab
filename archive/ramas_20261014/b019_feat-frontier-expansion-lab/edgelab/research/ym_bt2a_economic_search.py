"""Preregistered economic search primitives for the YM/BT2A campaign."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from itertools import product
from math import sqrt
from statistics import mean, median
from typing import Iterable, Sequence
from .ym_bt2a_retest_pilot import Policy, Tick

@dataclass(frozen=True)
class ExitSpec:
    spec_id: str
    stop_ticks: int
    target_ticks: int
    max_hold_ticks: int
    break_even_trigger_ticks: int | None = None
    break_even_lock_ticks: int = 0

@dataclass(frozen=True)
class TradeOutcome:
    state: str
    direction: str
    entry_ts_ns: int
    entry_sequence: int
    entry_price_half_ticks: int
    exit_ts_ns: int | None
    exit_sequence: int | None
    exit_price_half_ticks: int | None
    exit_reason: str
    held_ticks: int
    break_even_activated: bool
    gross_ticks: float | None
    cost_ticks: float
    net_ticks: float | None

def entry_policy_grid_v2() -> list[Policy]:
    out=[Policy("E000_IMMEDIATE","IMMEDIATE")]
    for wait in (5,10,25,50,100,200): out.append(Policy(f"E_WAIT_{wait}","WAIT_TICKS",wait_ticks=wait))
    for departure,depth,max_wait in product((1,2,4,6,8),(0.0,.25,.5,.75,1.0),(100,250,500,1000,2000)):
        out.append(Policy(f"E_RET_D{departure}_Z{int(depth*100)}_W{max_wait}","RETEST",departure_ticks=departure,depth=depth,max_wait_ticks=max_wait))
    assert len(out)==132
    return out

def _be_configs(triggers: Sequence[int],locks: Sequence[int]):
    yield None,0
    for trigger,lock in product(triggers,locks):
        if lock<trigger: yield trigger,lock

def coarse_exit_grid_v1() -> list[ExitSpec]:
    out=[]
    for stop,target,hold,(trigger,lock) in product((6,12,24),(6,12,24),(250,1000),tuple(_be_configs((6,12),(0,)))):
        tag="OFF" if trigger is None else f"T{trigger}_L{lock}"; out.append(ExitSpec(f"X_C_S{stop}_T{target}_H{hold}_BE{tag}",stop,target,hold,trigger,lock))
    assert len(out)==54
    return out

def refinement_exit_grid_v1() -> list[ExitSpec]:
    out=[]; be=tuple(_be_configs((4,6,8,12,16),(0,1,2)))
    for stop,target,hold,(trigger,lock) in product((4,6,8,10,12,16,20,24),(4,6,8,10,12,16,20,24,32),(100,250,500,1000,2000),be):
        tag="OFF" if trigger is None else f"T{trigger}_L{lock}"; out.append(ExitSpec(f"X_R_S{stop}_T{target}_H{hold}_BE{tag}",stop,target,hold,trigger,lock))
    assert len(out)==5760
    return out

def validate_exit_spec(spec: ExitSpec)->None:
    if spec.stop_ticks<=0 or spec.target_ticks<=0 or spec.max_hold_ticks<=0: raise ValueError("stop, target and max hold must be positive")
    if spec.break_even_trigger_ticks is None:
        if spec.break_even_lock_ticks!=0: raise ValueError("break-even lock requires a trigger")
    elif not 0<=spec.break_even_lock_ticks<spec.break_even_trigger_ticks: raise ValueError("break-even lock must be nonnegative and below trigger")

def simulate_trade(*,entry:Tick,future_ticks:Iterable[Tick],direction:str,spec:ExitSpec,cost_ticks:float)->TradeOutcome:
    validate_exit_spec(spec)
    if direction not in {"long","short"}: raise ValueError("direction must be long or short")
    if cost_ticks<0: raise ValueError("cost_ticks must be nonnegative")
    ticks=[t for t in future_ticks if (t.ts_ns,t.sequence)>(entry.ts_ns,entry.sequence) and t.session_id==entry.session_id]
    if not ticks: return TradeOutcome("CENSORED",direction,entry.ts_ns,entry.sequence,entry.price_half_ticks,None,None,None,"NO_POST_ENTRY_TICK",0,False,None,cost_ticks,None)
    sign=1 if direction=="long" else -1; active_stop=entry.price_half_ticks-sign*2*spec.stop_ticks; target=entry.price_half_ticks+sign*2*spec.target_ticks; be_active=False; window=ticks[:spec.max_hold_ticks]
    for held,tick in enumerate(window,start=1):
        favorable2=sign*(tick.price_half_ticks-entry.price_half_ticks)
        if spec.break_even_trigger_ticks is not None and not be_active and favorable2>=2*spec.break_even_trigger_ticks:
            be_active=True; active_stop=entry.price_half_ticks+sign*2*spec.break_even_lock_ticks
        stopped=tick.price_half_ticks<=active_stop if direction=="long" else tick.price_half_ticks>=active_stop
        targeted=tick.price_half_ticks>=target if direction=="long" else tick.price_half_ticks<=target
        if stopped: exit_price=tick.price_half_ticks; reason="BREAK_EVEN" if be_active else "STOP"
        elif targeted: exit_price=target; reason="TARGET"
        else: continue
        gross=sign*(exit_price-entry.price_half_ticks)/2
        return TradeOutcome("EXITED",direction,entry.ts_ns,entry.sequence,entry.price_half_ticks,tick.ts_ns,tick.sequence,exit_price,reason,held,be_active,gross,cost_ticks,gross-cost_ticks)
    last=window[-1]; gross=sign*(last.price_half_ticks-entry.price_half_ticks)/2; reason="TIME_EXIT" if len(window)>=spec.max_hold_ticks else "SESSION_END"
    return TradeOutcome("EXITED",direction,entry.ts_ns,entry.sequence,entry.price_half_ticks,last.ts_ns,last.sequence,last.price_half_ticks,reason,len(window),be_active,gross,cost_ticks,gross-cost_ticks)

def summarize_net_ticks(outcomes:Iterable[TradeOutcome])->dict[str,float|int|None]:
    values=[o.net_ticks for o in outcomes if o.state=="EXITED" and o.net_ticks is not None]
    if not values:return {"trades":0,"mean":None,"median":None,"win_rate":None,"standard_error":None}
    mu=mean(values); variance=sum((x-mu)**2 for x in values)/max(1,len(values)-1)
    return {"trades":len(values),"mean":mu,"median":median(values),"win_rate":sum(x>0 for x in values)/len(values),"standard_error":sqrt(variance/len(values))}

def exit_spec_record(spec:ExitSpec)->dict:return asdict(spec)
