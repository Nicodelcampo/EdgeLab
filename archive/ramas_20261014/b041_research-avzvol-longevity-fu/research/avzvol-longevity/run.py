"""Exploratory zone-age campaign. Fixed manifest; selected sessions only; no final-life selection."""
import os,sys,json,csv,time,itertools,types,gc,gzip
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path[:0]=['/data/analysis/avzvol-replication-rest','/data/analysis/avzvol-pilot','/data/analysis/avzvol-expansion','/data/analysis/avzvol-longevity']
from run_replication import prepare,digest
from fast_racimo import replay
from run_pilot import sid_hour,DAY,CUTOFF
from expanded_passage import evaluate,reference,STATUS
from feature_schema import attach_features
from engine import first_visit,dedup_masks,features,build_cache,cached_features
P=Path('/data/analysis/avzvol-longevity');C=os.environ['REPLICATION_CONTRACT'];ROOT=Path(os.environ['REPLICATION_ROOT']);AGES=[0,250,500,1000,2000,3000,5000];TAPES=[(80,5),(90,5),(80,10)];GEOM=list(itertools.product([8,18],[1000,2000,3000]));RULES=[(d,q,0) for d,q in itertools.product([20,40,80],[.25,.5,.75])]+[(40,.5,1),(40,.5,2)]
HEAD=['contract','family','origin','landmark','D','q','endpoint','session','zone_id','dedup75','dedup50','anchor_idx','trigger_idx','last_idx','status','visits1','visits5','visits_clock10s','volume_inside_fraction','inside_seconds_observed','recency_seconds','prior_gap_count','speed_ratio','return_seconds','return_bars_per_tick','return_efficiency','return_imbalance_proxy_toward','proxy_coverage','remaining_ticks','age_bars','age_seconds','hour','volatility256_ticks','distance_bin','source_trigger_sequence']
def main():
 t0=time.time();auth=json.load(open('/data/raw/avzvol-selected-risk/pr111-authorization.json'));assert auth['gates']['user_exploratory_authorized'] and not auth['holdout_access_authorized'];pin=next(x for x in auth['files'] if x['contract']==C);selected=list(csv.DictReader(open('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv')));sel=[x for x in selected if x['contract']==C];meta=json.load(open('/data/raw/avzvol-selected-risk/metadata-review.json'));win=next(x for x in meta['contracts'] if x['contract']==C)
 manifest=dict(feature_schema_version=2,status='FIXED_BEFORE_LABELS',contract=C,tapes=TAPES,geometry=GEOM,height_ticks=20,landmarks=AGES,rules=RULES,expected_rule_groups=2772,origins=['real','translated_geometry250'],event_dates=[x['session_label'] for x in sel],source=pin,primary=dict(family='P80_W5_R18_2000_20',landmarks=[2000,3000],D=40,q=.5,endpoint=0,dedup=.75,temporal_bin_records=6250),definition='first actual inside print at/after landmark within2000bars, then first-D-qualified departure/retracement within2000bars and symmetric post-trigger barriers; same selected birth session only',age='closed25Last-record bars since observable frozen birth, not final zone length',control='same exact frozen width and initial anchor-relative position translated at250later closed bars; equal-age landmark; conditioned on original birth, not randomised null',visit_definitions='actual inside prints on fully closed bars after birth, separated by1or5fully outside bars or10seconds outside; current forming trigger bar excluded',flow='bid/ask inferred proxy, unknown remains0; no exchange aggressor claim',features='measured at trigger only; volume including actual prefix of current bar, visits from closed bars only',intrasesession_only=True,prior_gap_policy='retain observed histories with gap count and separate gap-free sensitivity; do not claim unknown visit counts across gaps',source_certified=False,holdout_opened=False,pnl_computed=False,multiplicity_corrected=False,prior_universe_inspected=True,code_sha256={n:digest(P/n) for n in ['run.py','engine.py','test_engine.py','test_cache.py','feature_schema.py']});(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('MANIFEST',C,flush=True)
 root,ts,px,seq,bars,fps,st,en,bs,full,ss,ee,approved=prepare(C,pin,sel,win);bar=bars.tick_bar_idx;vol=np.memmap(root/'vol-private.bin',dtype=np.float64,mode='r');flowpath=root/'flow-private.bin';a=win['legacy_read_window_start_utc_ns'];z=min(win['legacy_read_window_end_utc_ns_exclusive'],CUTOFF)
 # Bounded second stream with identical selection; exact sequence parity guard.
 k=0
 with flowpath.open('wb') as f:
  for batch in pq.ParquetFile(Path('/data/raw/avzvol-ticks')/pin['file']).iter_batches(batch_size=262144,columns=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','sequence'],use_threads=False):
   tt,pp,bb,aa,sq=[batch.column(i).to_numpy(zero_copy_only=False) for i in range(5)];si,ho=sid_hour(tt);keep=(tt>=a)&(tt<z)&((si<approved.min())|np.isin(si,approved))&(ho!=16);sq=sq[keep];assert np.array_equal(seq[k:k+len(sq)],sq);g=np.where(pp[keep]>=aa[keep],1,np.where(pp[keep]<=bb[keep],-1,0)).astype(np.int8);g.tofile(f);k+=len(g)
 assert k==len(ts);flow=np.memmap(flowpath,dtype=np.int8,mode='r');starts=np.maximum.accumulate(np.where(np.r_[True,bs[1:]!=bs[:-1]],np.arange(len(st)),0));ends=ee[np.searchsorted(ss,st,side='right')-1];mod=types.ModuleType('legacy');mod.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec(Path('/data/analysis/avzvol-pilot/legacy_detector.py').read_text(),mod.__dict__)
 census=[];checks=[];counts=defaultdict(Counter);days=defaultdict(Counter);nrows=0;refseen=set()
 with gzip.open(ROOT/'signals-private.csv.gz','wt',newline='',compresslevel=1) as out:
  writer=csv.DictWriter(out,fieldnames=HEAD);writer.writeheader()
  for pct,w in TAPES:
   det=mod.run(bars,fps,bs,dict(racimo_min=0,ob_bars=0,window_bars=w,detection_percentile=pct));zz=det['zones'];zb=np.array([x['bar'] for x in zz],np.int64);zl=np.array([x['low_tick'] for x in zz],np.int64);zh=np.array([x['high_tick'] for x in zz],np.int64);del zz,det;gc.collect();print('TAPE',C,pct,w,len(zb),flush=True)
   for minimum,window in GEOM:
    family=f'P{pct}_W{w}_R{minimum}_{window}_20';birth=replay(zb,zl,zh,minimum,window,20);birth=birth[np.isin(bs[birth[:,0]],approved)&full[birth[:,0]]];m75=dedup_masks(birth,bs,.75);m50=dedup_masks(birth,bs,.5);census.append(dict(contract=C,family=family,births=len(birth),dedup75_births=int(m75.sum()),dedup50_births=int(m50.sum())));print('FAMILY',C,family,len(birth),int(m75.sum()),flush=True)
    for origin,age,(d,q,ep) in itertools.product(['real','translated_geometry250'],AGES,RULES):
     key=(family,origin,age,d,q,ep);counts[key]['births']+=0
     for x in sel:days[(*key,x['session_label'])]['births']+=0
    for zid,(b,_,lo,hi) in enumerate(birth):
     b=int(b);bi=int(en[b]-1);stop=int(ends[b]);date=str(pd.Timestamp(int(bs[b])*DAY).date());assert date in manifest['event_dates'];cases=[('real',b,bi,int(lo),int(hi))];cb=b+250
     if cb<len(st) and bs[cb]==bs[b] and full[cb]:
      ci=int(en[cb]-1);shift=int(px[ci]-px[bi]);cases.append(('translated_geometry250',cb,ci,int(lo)+shift,int(hi)+shift))
     for origin,b0,i0,low,high in cases:
      cache_stop=min(stop,int(en[min(len(en)-1,b0+9000)]));prefix=build_cache(px,ts,vol,flow,bar,st,en,b0,i0,cache_stop,low,high)
      for age in AGES:
       mb=b0+age
       keys=[(family,origin,age,d,q,ep) for d,q,ep in RULES]
       for key in keys:counts[key]['births']+=1;days[(*key,date)]['births']+=1
       if mb>=len(st) or bs[mb]!=bs[b0] or not full[mb]:
        for key in keys:counts[key]['LANDMARK_SESSION_CENSORED']+=1;days[(*key,date)]['LANDMARK_SESSION_CENSORED']+=1
        continue
       marker=int(en[mb]-1);anchor,why=first_visit(px,ts,bar,marker,stop,low,high)
       for key in keys:counts[key]['landmark_reached']+=1;days[(*key,date)]['landmark_reached']+=1
       if anchor<0:
        reason=['UNUSED','NO_VISIT_SESSION_END','NO_VISIT_WAIT_LIMIT','NO_VISIT_GAP'][why]
        for key in keys:counts[key][reason]+=1;days[(*key,date)][reason]+=1
        continue
       cache={}
       for key in keys:
        _,_,_,d,q,ep=key;r=evaluate(px,ts,bar,anchor,stop,low,high,d,q,ep,1);status,ex,pk,tr,last,side,peak,target,opp,skips=r;counts[key][STATUS[status]]+=1;days[(*key,date)][STATUS[status]]+=1
        if tr<0:continue
        counts[key]['signals']+=1;days[(*key,date)]['signals']+=1;nrows+=1;ck=(ex,pk,tr,side)
        if ck not in cache:cache[ck]=cached_features(px,ts,bar,b0,i0,tr,ex,pk,side,peak,target,low,high,prefix)
        values=list(cache[ck]);values[13]=abs(px[tr]-target);bb=int(bar[tr]);past=np.arange(max(int(starts[bb]),bb-256),bb);vr=int(np.max(bars.high_t[past])-np.min(bars.low_t[past])) if len(past) else None;hour=int(pd.Timestamp(int(ts[tr]),tz='UTC').tz_convert('America/Chicago').hour)
        row=dict(contract=C,family=family,origin=origin,landmark=age,D=d,q=q,endpoint=ep,session=date,zone_id=zid,dedup75=int(m75[zid]),dedup50=int(m50[zid]),anchor_idx=anchor,trigger_idx=tr,last_idx=last,status=STATUS[status],hour=hour,volatility256_ticks=vr,distance_bin=int(abs(px[tr]-target)//10),source_trigger_sequence=int(seq[tr]));attach_features(row,values);assert len(values)==16 and abs(px[tr]-target)==abs(px[tr]-opp) and tr>anchor and last>=tr;writer.writerow(row)
        stratum=(ep,d,q)
        if stratum not in refseen and last-anchor<3000:
         z0=min(stop,last+2);rr=reference(px[anchor:z0].tolist(),ts[anchor:z0].tolist(),(bar[anchor:z0]-bar[anchor]).tolist(),0,z0-anchor,low,high,d,q,ep,1);actual=list(r)
         for j in [1,2,3,4]:
          if actual[j]>=0:actual[j]-=anchor
         assert tuple(actual)==rr;refseen.add(stratum);checks.append(dict(endpoint=ep,D=d,q=q,exact_reference=True))
    out.flush();pd.DataFrame(census).to_csv(ROOT/'frequency.csv',index=False)
 keysnames=['family','origin','landmark','D','q','endpoint'];pd.DataFrame([{**dict(zip(keysnames,key)),**v} for key,v in counts.items()]).fillna(0).to_csv(ROOT/'rule-counts.csv',index=False);pd.DataFrame([{**dict(zip(keysnames+['session'],key)),**v} for key,v in days.items()]).fillna(0).to_csv(ROOT/'daily-counts.csv',index=False)
 for key,c in counts.items():assert c['births']==c['LANDMARK_SESSION_CENSORED']+c['NO_VISIT_SESSION_END']+c['NO_VISIT_WAIT_LIMIT']+c['NO_VISIT_GAP']+sum(c[x] for x in STATUS.values())
 assert len(counts)==2772
 evidence=dict(feature_schema_version=2,status='LONGEVITY_CONTRACT_COMPLETE',contract=C,selected_sessions=len(sel),configurations=18,landmark_rule_groups=len(counts),signal_rows_not_independent=nrows,scope_leakage=0,reference_checks=checks,source_certified=False,holdout_opened=False,pnl_computed=False,wall_seconds=time.time()-t0,carry_across_sessions_tested=False);(ROOT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print('COMPLETE',C,nrows,len(checks),time.time()-t0,flush=True)
if __name__=='__main__':main()
