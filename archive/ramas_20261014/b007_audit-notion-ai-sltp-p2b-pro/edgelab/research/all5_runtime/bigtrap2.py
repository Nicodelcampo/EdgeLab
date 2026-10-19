from __future__ import annotations
DEFAULTS=dict(ticks_per_row=1,imbalance_mode='Diagonal',trap_volume_source='AggressiveSide',imbalance_ratio=3.0,use_wick_filter=True,wick_zone_pct=30.0,min_delta_filter=0.0,min_trap_volume=30.0,min_export_volume=1.0,invalidation_mode='CloseThrough',max_age_bars=2000,max_touches=0)
def run(ticks,bars,footprints,params=None,chart_tz='UTC'):
    p={**DEFAULTS,**(params or {})}; out=[]; ts=float(ticks.tick_size)
    for b in range(1,len(bars)):
        amap=footprints.ask[b]; bmap=footprints.bid[b]
        if not amap and not bmap:continue
        rt=max(1,int(p['ticks_per_row'])); ra={}; rb={}
        for tk,v in amap.items():r=tk//rt;ra[r]=ra.get(r,0.0)+v
        for tk,v in bmap.items():r=tk//rt;rb[r]=rb.get(r,0.0)+v
        keys=sorted(set(ra)|set(rb)); close=float(bars.close_t[b])*ts; lo=float(bars.low_t[b])*ts; hi=float(bars.high_t[b])*ts; rng=hi-lo; wh=hi-rng*float(p['wick_zone_pct'])/100.; wl=lo+rng*float(p['wick_zone_pct'])/100.
        buy={'vol':0.0,'n':0}; sell={'vol':0.0,'n':0}
        for r in keys:
            a=ra.get(r,0.0); bv=rb.get(r,0.0)
            if abs(a-bv)<float(p['min_delta_filter']):continue
            if p['imbalance_mode']=='Diagonal':br=a/max(rb.get(r-1,0.0),1.0);sr=bv/max(ra.get(r+1,0.0),1.0)
            else:br=a/max(bv,1.0);sr=bv/max(a,1.0)
            rp=(r*rt+(rt-1)/2.)*ts; cb=a if p['trap_volume_source']=='AggressiveSide' else a+bv; cs=bv if p['trap_volume_source']=='AggressiveSide' else a+bv
            if a>=1 and br>=float(p['imbalance_ratio']) and rp>close and (not p['use_wick_filter'] or (rng>0 and rp>=wh)):buy['vol']+=cb;buy['n']+=1
            if bv>=1 and sr>=float(p['imbalance_ratio']) and rp<close and (not p['use_wick_filter'] or (rng>0 and rp<=wl)):sell['vol']+=cs;sell['n']+=1
        if buy['n'] and buy['vol']>=float(p['min_trap_volume']):out.append({'id':f'{b}_B','kind':'trapped_buyers','created_bar':b})
        if sell['n'] and sell['vol']>=float(p['min_trap_volume']):out.append({'id':f'{b}_S','kind':'trapped_sellers','created_bar':b})
    return {'zones':out,'params':p,'events':[]}
