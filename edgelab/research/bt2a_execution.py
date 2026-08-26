"""Integer-tick, nanosecond execution layer for BT2A Gate 2 P2-B."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
import numpy as np

@dataclass(frozen=True)
class ExecutionCost:
    name:str; slip_entry:int; slip_target:int; slip_stop:int; slip_exit:int
    commission_per_side_usd:float

def scenarios(commission_per_side_usd:float):
    c=float(commission_per_side_usd)
    if c<0: raise ValueError("commission must be nonnegative")
    return {"ideal":ExecutionCost("ideal",0,0,0,0,0.),"base":ExecutionCost("base",1,1,1,1,c),"adverso":ExecutionCost("adverso",2,2,2,2,c),"severo":ExecutionCost("severo",3,3,3,3,c)}

def _digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def _arrays(ts,source,last,bid,ask,sessions):
    values=[np.asarray(ts,dtype=np.int64),np.asarray(source,dtype=np.int64),np.asarray(last,dtype=np.int64),np.asarray(bid,dtype=np.int64),np.asarray(ask,dtype=np.int64),np.asarray(sessions)]
    n=len(values[0])
    if not n or any(len(x)!=n for x in values): raise ValueError("invalid execution arrays")
    if np.any(values[0][1:]<values[0][:-1]) or np.any(values[1][1:]<=values[1][:-1]): raise ValueError("noncanonical ordering")
    if np.any(values[3]>values[4]): raise ValueError("crossed BBO")
    return values

def _strict_next(ts,source,signal_ts,signal_source):
    i=int(np.searchsorted(source,int(signal_source),side="right"))
    while i<len(source) and (int(ts[i]),int(source[i]))<=(int(signal_ts),int(signal_source)): i+=1
    return None if i>=len(source) else i

def simulate(signals,ts_utc_ns,source_row,last_ticks,bid_ticks,ask_ticks,session_ids,*,cost:ExecutionCost,tick_value_usd:float,close_at_session_end=True):
    ts,source,last,bid,ask,sessions=_arrays(ts_utc_ns,source_row,last_ticks,bid_ticks,ask_ticks,session_ids)
    tick_value=float(tick_value_usd)
    if tick_value<=0: raise ValueError("tick_value_usd must be positive")
    ordered=sorted(signals,key=lambda x:(int(x["signal_ts_utc_ns"]),int(x["signal_source_row"]),str(x["event_id"])))
    trades=[]; rejected=[]; open_until=-1
    for sig in ordered:
        d=int(sig["direction"]); target_ticks=int(sig["target_ticks"]); stop_ticks=int(sig["stop_ticks"])
        if d not in (-1,1) or min(target_ticks,stop_ticks)<1: raise ValueError("invalid signal")
        signal_pos=int(np.searchsorted(source,int(sig["signal_source_row"]),side="left"))
        if signal_pos>=len(source) or int(source[signal_pos])!=int(sig["signal_source_row"]): rejected.append({"event_id":sig["event_id"],"reason":"signal_row_missing"}); continue
        entry=_strict_next(ts,source,sig["signal_ts_utc_ns"],sig["signal_source_row"])
        if entry is None: rejected.append({"event_id":sig["event_id"],"reason":"no_execution_tick"}); continue
        if sessions[entry]!=sessions[signal_pos]: rejected.append({"event_id":sig["event_id"],"reason":"fill_crosses_session"}); continue
        if entry<=open_until: rejected.append({"event_id":sig["event_id"],"reason":"position_open"}); continue
        entry_book=int(ask[entry] if d>0 else bid[entry]); entry_mid=(int(bid[entry])+int(ask[entry]))/2
        entry_fill=entry_book+d*cost.slip_entry; target=entry_fill+d*target_ticks; stop=entry_fill-d*stop_ticks
        seconds=sig.get("time_stop_seconds"); deadline=None if seconds in (None,0) else int(ts[entry])+int(round(float(seconds)*1_000_000_000))
        exit_idx=None; exit_ref=None; reason=None; kind=None; session=sessions[entry]
        for j in range(entry,len(ts)):
            if sessions[j]!=session: break
            px=int(last[j]); hit_target=px>=target if d>0 else px<=target; hit_stop=px<=stop if d>0 else px>=stop
            if hit_target: exit_idx=j; exit_ref=target; reason="target"; kind="target"; break
            if hit_stop: exit_idx=j; exit_ref=stop; reason="stop"; kind="stop"; break
            if deadline is not None and int(ts[j])>=deadline: exit_idx=j; reason="time_stop"; kind="market"; break
            if j==len(ts)-1: exit_idx=j; reason="data_edge"; kind="market"; break
            if close_at_session_end and sessions[j+1]!=session: exit_idx=j; reason="session_close"; kind="market"; break
        if exit_idx is None: rejected.append({"event_id":sig["event_id"],"reason":"no_exit_tick"}); continue
        if kind=="market":
            exit_book=int(bid[exit_idx] if d>0 else ask[exit_idx]); exit_mid=(int(bid[exit_idx])+int(ask[exit_idx]))/2
            slip=cost.slip_exit; exit_fill=exit_book-d*slip; gross=d*(exit_mid-entry_mid); spread=d*(entry_book-entry_mid)+d*(exit_mid-exit_book)
        else:
            slip=cost.slip_target if kind=="target" else cost.slip_stop; exit_fill=exit_ref-d*slip; gross=d*(exit_ref-entry_mid); spread=d*(entry_book-entry_mid)
        slippage=cost.slip_entry+slip; net=gross-spread-slippage; from_fills=d*(exit_fill-entry_fill)
        if abs(net-from_fills)>1e-9: raise AssertionError("cost identity failure")
        commission=2*cost.commission_per_side_usd
        trades.append({"event_id":str(sig["event_id"]),"direction":d,"cme_session":str(session),"entry_idx":entry,"entry_ts_utc_ns":int(ts[entry]),"entry_source_row":int(source[entry]),"entry_price_ticks":int(entry_fill),"exit_idx":exit_idx,"exit_ts_utc_ns":int(ts[exit_idx]),"exit_source_row":int(source[exit_idx]),"exit_price_ticks":int(exit_fill),"exit_reason":reason,"gross_ticks":float(gross),"spread_ticks":float(spread),"slippage_ticks":float(slippage),"commission_usd":float(commission),"net_ticks":float(net),"net_usd":float(net*tick_value-commission)})
        open_until=exit_idx
    net_ticks=sum(x["net_ticks"] for x in trades); net_usd=sum(x["net_usd"] for x in trades); eligible=len(ordered)
    summary={"scenario":cost.name,"n_eligible_signals":eligible,"n_trades":len(trades),"n_rejected":len(rejected),"net_ticks":net_ticks,"net_usd":net_usd,"mean_net_ticks_per_trade":net_ticks/len(trades) if trades else None,"mean_net_ticks_per_eligible_signal":net_ticks/eligible if eligible else None,"mean_net_usd_per_trade":net_usd/len(trades) if trades else None,"mean_net_usd_per_eligible_signal":net_usd/eligible if eligible else None,"close_at_session_end":bool(close_at_session_end)}
    return {"trades":trades,"rejected":rejected,"summary":summary,"digest":_digest({"trades":trades,"rejected":rejected,"summary":summary})}
