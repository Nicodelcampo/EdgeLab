"""Pure declared-tape first-passage prototype. No market loader or gate override.
Tests must use invented inputs until a separate reviewed market adapter is enabled.
One first departure and at most one signal per frozen zone/parameter/endpoint.
Prices are integer ticks; complete ordered trade sequence required, not OHLC.
"""
from dataclasses import dataclass,asdict
from math import isfinite

@dataclass(frozen=True)
class Trade:
    seq:int
    ns:int
    bar:int
    price:int
    session:str
    volume:float=1.0
    aggressor:int=0  # -1 sell, +1 buy, 0 unknown; no inferred aggressor

@dataclass(frozen=True)
class Zone:
    id:str
    low:int
    high:int
    created_seq:int

@dataclass(frozen=True)
class Rule:
    min_excursion_ticks:float
    retracement_fraction:float
    endpoint:str='touch'
    horizon_bars:int=2000

def validate(tape,zone,rule):
    if not tape or zone.low>zone.high:raise ValueError('empty tape or invalid zone')
    if not 0<rule.retracement_fraction<1 or rule.min_excursion_ticks<=0:raise ValueError('invalid threshold/fraction')
    if rule.endpoint not in ('touch','enter_one_tick','cross_one_tick') or rule.horizon_bars<1:raise ValueError('invalid endpoint/horizon')
    for i,t in enumerate(tape):
        if any(type(x) is not int for x in (t.seq,t.ns,t.bar,t.price)):raise ValueError('integer seq/time/bar/price required')
        if not isfinite(t.volume) or t.volume<=0 or t.aggressor not in (-1,0,1):raise ValueError('bad volume/aggressor')
        if i and (t.seq<=tape[i-1].seq or t.ns<tape[i-1].ns):raise ValueError('tape ordering violated')
        if i and t.session==tape[i-1].session and t.bar<tape[i-1].bar:raise ValueError('bar ordering violated')
    anchors=[i for i,t in enumerate(tape) if t.seq==zone.created_seq]
    if len(anchors)!=1:raise ValueError('exact creation observation required')
    return anchors[0]

def imbalance(leg,side):
    total=sum(t.volume for t in leg);known=sum(t.volume for t in leg if t.aggressor!=0)
    delta=sum(t.volume*t.aggressor for t in leg)
    return {'signed_delta_away':side*delta,'delta_over_total_away':None if not known else side*delta/total,'known_volume_fraction':known/total if total else None,'volume':total}

def features(tape,start,peak,trigger,side,edge,peak_distance):
    away=tape[start:peak+1];back=tape[peak:trigger+1]
    def leg_metrics(leg,distance):
        seconds=(leg[-1].ns-leg[0].ns)/1e9;bars=leg[-1].bar-leg[0].bar+1
        path=sum(abs(b.price-a.price) for a,b in zip(leg,leg[1:]))
        return {'observed_net_distance_ticks':abs(leg[-1].price-leg[0].price),'seconds':seconds,'inclusive_bars':bars,'bars_per_tick':bars/distance if distance else None,'ticks_per_second':distance/seconds if seconds else None,'path_efficiency':abs(leg[-1].price-leg[0].price)/path if path else None,**imbalance(leg[1:],side)}
    retraced=peak_distance-side*(tape[trigger].price-edge)
    out={'peak_distance_ticks':peak_distance,'actual_retraced_fraction':retraced/peak_distance,'distance_to_edge_ticks':side*(tape[trigger].price-edge),'outgoing':leg_metrics(away,peak_distance),'returning':leg_metrics(back,retraced)}
    a=out['outgoing']['ticks_per_second'];b=out['returning']['ticks_per_second'];out['return_to_outgoing_speed_ratio']=b/a if a and b is not None else None
    return out

def evaluate(tape,zone,rule):
    """At trigger freeze peak, features, target and equal-distance opposite barrier.
    Running peak is first attainment of highest observed displacement, NOT final max.
    No outcomes on trigger tick, no later peak updates, no replay of final geometry.
    The returned labels are tape first passage, not a fill or profit simulation.
    """
    anchor=validate(tape,zone,rule);born=tape[anchor];base={'zone':asdict(zone),'rule':asdict(rule),'signal':False}
    if not zone.low<=born.price<=zone.high:return {**base,'status':'ANCHOR_OUTSIDE'}
    exit_i=None
    for i in range(anchor+1,len(tape)):
        t=tape[i]
        if t.session!=born.session:break
        if t.price>zone.high or t.price<zone.low:exit_i=i;break
    if exit_i is None:return {**base,'status':'NO_DEPARTURE'}
    side=1 if tape[exit_i].price>zone.high else -1;edge=zone.high if side==1 else zone.low
    peak_i=exit_i;peak=side*(tape[exit_i].price-edge)
    for i in range(exit_i+1,len(tape)):
        t=tape[i]
        if t.session!=born.session:return {**base,'status':'NO_TRIGGER_SESSION_END'}
        x=side*(t.price-edge)
        if x<=0:return {**base,'status':'TOUCH_BEFORE_OBSERVED_TRIGGER'}
        if x>peak:peak=x;peak_i=i
        if peak<rule.min_excursion_ticks or x>peak*(1-rule.retracement_fraction):continue
        target=edge if rule.endpoint=='touch' else edge-side if rule.endpoint=='enter_one_tick' else (zone.low-1 if side==1 else zone.high+1)
        distance=side*(t.price-target);assert distance>0
        stop=t.price+side*distance
        result={**base,'signal':True,'status':'UNRESOLVED_TAPE_END','trigger_seq':t.seq,'trigger_ns':t.ns,'trigger_bar':t.bar,'entry_observation_price':t.price,'side':side,'frozen_target':target,'frozen_opposite':stop,'symmetric_distance_ticks':distance,'features':features(tape,exit_i-1,peak_i,i,side,edge,peak)}
        for u in tape[i+1:]:
            if u.session!=born.session:return {**result,'status':'UNRESOLVED_SESSION_END'}
            if u.bar-t.bar>rule.horizon_bars:return {**result,'status':'UNRESOLVED_HORIZON'}
            hit=side*(u.price-target)<=0;opposite=side*(u.price-stop)>=0
            assert not(hit and opposite)
            if hit or opposite:return {**result,'status':'TARGET_FIRST' if hit else 'OPPOSITE_FIRST','outcome_seq':u.seq,'outcome_ns':u.ns,'outcome_bar':u.bar}
        return result
    return {**base,'status':'NO_TRIGGER_TAPE_END'}
