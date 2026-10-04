"""Etapa C (PREREGISTRO_ETAPA_C_GC_SPOT.md + enmienda C1): celda GC 04:15 CT sobre XAU/USD spot de Dukascopy."""
import lzma,struct,glob,os,sys,json,datetime as dt,numpy as np
from zoneinfo import ZoneInfo
CHI=ZoneInfo('America/Chicago');UTC=dt.timezone.utc;TICK=0.1;COMM=0.45;MIN=60;NSIM=20000;SEED=20261008
def read_hour(fn):
    if not os.path.exists(fn) or os.path.getsize(fn)==0:return None
    d=lzma.LZMADecompressor(format=lzma.FORMAT_AUTO).decompress(open(fn,'rb').read());n=len(d)//20
    a=np.frombuffer(d[:n*20],dtype=np.dtype([('ms','>u4'),('ask','>u4'),('bid','>u4'),('av','>f4'),('bv','>f4')]))
    return a['ms'].astype(np.int64),a['ask'].astype(np.float64)/1000,a['bid'].astype(np.float64)/1000
DUKAS_BIN=os.environ.get('DUKAS_BIN')   # carpeta con YYYY-MM-DD.bin de tools/jforex/HistDownloader.java (>q d d f f)
def session_ticks_bin(d):
    fn=os.path.join(DUKAS_BIN,f'{d:%Y-%m-%d}.bin')
    if not os.path.exists(fn) or os.path.getsize(fn)==0:return None
    a=np.fromfile(fn,dtype=np.dtype([('t','>i8'),('bid','>f8'),('ask','>f8'),('bv','>f4'),('av','>f4')]))
    base=int(dt.datetime(d.year,d.month,d.day,7,tzinfo=UTC).timestamp())*1000;m=(a['t']>=base)&(a['t']<base+5*3600_000)  # 07–12 UTC, como el feed por horas
    if not m.any():return None
    return a['t'][m].astype(np.int64),a['ask'][m].astype(np.float64),a['bid'][m].astype(np.float64)
def session_ticks(d):
    if DUKAS_BIN:return session_ticks_bin(d)
    ts=[];ask=[];bid=[]
    for h in (7,8,9,10,11):
        r=read_hour(f'raw/{d:%Y%m%d}_{h:02d}.bi5')
        if r is None:continue
        base=int(dt.datetime(d.year,d.month,d.day,h,tzinfo=UTC).timestamp())*1000
        ts.append(r[0]+base);ask.append(r[1]);bid.append(r[2])
    if not ts:return None
    return np.concatenate(ts),np.concatenate(ask),np.concatenate(bid)
def one(d):
    s=session_ticks(d)
    if s is None:return None
    ts,ask,bid=s;mid=(ask+bid)/2
    slot=dt.datetime(d.year,d.month,d.day,4,15,tzinfo=CHI).astimezone(UTC);b0=int(slot.timestamp())*1000
    b1=b0+60_000;ent_t=b0+120_000;ex_t=ent_t+15*60_000
    # elegibilidad
    w=(ts>=ent_t)&(ts<ex_t);p=(ts>=b0-15*60_000+60_000)&(ts<b0+60_000)   # 15 min previos a la barra de señal
    if w.sum()<50 or p.sum()<50:return {'date':str(d),'eligible':False}
    # cierre de la barra que termina en b1 y de la que termina en b1-15min (última cotización antes de esos instantes)
    i1=np.searchsorted(ts,b1,'left')-1;ir=np.searchsorted(ts,b1-15*60_000,'left')-1
    if i1<0 or ir<0:return {'date':str(d),'eligible':False}
    delta=mid[i1]-mid[ir]
    ie=np.searchsorted(ts,ent_t,'left');ix=np.searchsorted(ts,ex_t,'left')
    if ix>=len(ts) or ie>=len(ts):return {'date':str(d),'eligible':False}
    short=(bid[ie]-ask[ix])/TICK-COMM          # vende al bid, recompra al ask (ticks de GC)
    long_=(bid[ix]-ask[ie])/TICK-COMM
    return {'date':str(d),'eligible':True,'delta_usd':float(delta),'up':bool(delta>0),'short':float(short),'long':float(long_),'entry_delay_s':float((ts[ie]-ent_t)/1000),'exit_delay_s':float((ts[ix]-ex_t)/1000),'n_win':int(w.sum()),'spread_usd':float(np.median((ask-bid)[w]))}
def signflip(adv,seed=SEED,n=NSIM):
    adv=np.asarray(adv,float);V=(adv**2).sum()
    if V==0:return 0.,1.
    e=np.random.default_rng(seed).choice(np.array([-1.,1.]),size=(n,len(adv)));z=adv.sum()/np.sqrt(V);zn=(e@adv)/np.sqrt(V);return float(z),float((np.sum(zn>=z)+1)/(n+1))
if __name__=='__main__':
    lo=dt.date.fromisoformat(sys.argv[1]);hi=dt.date.fromisoformat(sys.argv[2]);R=[];d=lo
    while d<=hi:
        if d.weekday()<5:
            r=one(d)
            if r:R.append(r)
        d+=dt.timedelta(days=1)
    el=[r for r in R if r['eligible']];up=[r for r in el if r['up']];dn=[r for r in el if not r['up'] and r['delta_usd']<0]
    out={'sessions_in_window':len(R),'eligible_sessions':len(el),'ineligible':[r['date'] for r in R if not r['eligible']],'max_exit_delay_s':max(r['exit_delay_s'] for r in el),'median_spread_usd':float(np.median([r['spread_usd'] for r in el]))}
    if up:
        adv=[(r['short']-r['long'])/2 for r in up];z,p=signflip(adv);m=float(np.mean([r['short'] for r in up]))
        out['primary']={'trades':len(up),'mean_net_ticks':m,'win_rate':float(np.mean([r['short']>0 for r in up])),'z':z,'p_one_sided':p,'decision':'Replica' if (m>0 and p<=0.05) else ('No replica' if m<=0 else 'Inconcluso'),'by_day':[(r['date'],round(r['delta_usd'],2),round(r['short'],1)) for r in up]}
    adv=[(r['short']-r['long'])/2 for r in el];z,p=signflip(adv,SEED+1) if el else (0,1)
    out['secondary']={'short_no_cond':{'trades':len(el),'mean_net_ticks':float(np.mean([r['short'] for r in el])) if el else None,'z':z,'p_one_sided':p},'long_after_down':{'trades':len(dn),'mean_net_ticks':float(np.mean([r['long'] for r in dn])) if dn else None}}
    json.dump(out,open('/tmp/claude-0/ghostlocal/duka/spot_cell_result.json','w'),indent=1);print(json.dumps(out,indent=1))
