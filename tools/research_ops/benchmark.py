"""Fixed synthetic prior-bar range benchmark, not market replay or engine parity.
At bar b use [max(session_start,b-window),b): current bar excluded. Reset each session.
"""
from collections import deque
import hashlib,json
from statistics import median
from time import perf_counter

def _validate(highs,lows,sessions,window):
    if type(window) is not int or not 1<=window<=3000: raise ValueError('window out of bounds')
    if not len(highs)==len(lows)==len(sessions) or len(highs)>16384: raise ValueError('bounded aligned inputs required')
    for h,l,s in zip(highs,lows,sessions):
        if any(type(v) is not int for v in (h,l,s)) or h<l: raise ValueError('integer synthetic ranges required')
    if any(a>b for a,b in zip(sessions,sessions[1:])): raise ValueError('monotonic contiguous sessions required')

def reference_ranges(highs,lows,sessions,window):
    _validate(highs,lows,sessions,window);result=[];start=0
    for b in range(len(highs)):
        if b==0 or sessions[b]!=sessions[b-1]: start=b
        a=max(start,b-window)
        result.append(None if a==b else max(highs[a:b])-min(lows[a:b]))
    return result

def deque_ranges(highs,lows,sessions,window):
    _validate(highs,lows,sessions,window);upper,lower=deque(),deque();result=[]
    for b in range(len(highs)):
        if b==0 or sessions[b]!=sessions[b-1]: upper.clear();lower.clear()
        else:
            i=b-1
            while upper and highs[upper[-1]]<=highs[i]: upper.pop()
            while lower and lows[lower[-1]]>=lows[i]: lower.pop()
            upper.append(i);lower.append(i)
        while upper and upper[0]<b-window: upper.popleft()
        while lower and lower[0]<b-window: lower.popleft()
        result.append(None if not upper else highs[upper[0]]-lows[lower[0]])
    return result

def run_benchmark():
    n,window,repeats=4096,256,3
    lows=[((i*7919)%2003)-1000 for i in range(n)]
    highs=[v+(i%31) for i,v in enumerate(lows)];sessions=[i//1024 for i in range(n)]
    timings={};outputs=[]
    for fn in (reference_ranges,deque_ranges):
        elapsed=[]
        for _ in range(repeats):
            t0=perf_counter();out=fn(highs,lows,sessions,window);elapsed.append(perf_counter()-t0)
        timings[fn.__name__]=dict(seconds=elapsed,median_seconds=median(elapsed));outputs.append(out)
    if outputs[0]!=outputs[1]: raise ValueError('exact parity failed')
    def digest(v): return hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
    return dict(status='PASS_SYNTHETIC_RANGE_PARITY_ONLY',bars=n,window=window,sessions=4,repeats=repeats,input_sha256=digest([highs,lows,sessions,window]),output_sha256=digest(outputs[0]),timings=timings,current_bar_excluded=True,market_data_read=False,active_runner_changed=False,campaign_speedup_established=False,limitations='fixed Python integer fixture; contended host; no full-engine parity or performance claim')
