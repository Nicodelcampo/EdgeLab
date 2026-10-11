"""Fixed cross-contract replication with clock-grid price-only references.
No optimization on new contract labels; source pins/catalog selection unchanged.
No raw ticks published. Sources streamed into private memmaps to bound RAM.
"""
import csv,hashlib,itertools,json,sys,time,types,gc,os
from collections import defaultdict,Counter
from pathlib import Path
from types import SimpleNamespace
import numpy as np,pandas as pd,pyarrow.parquet as pq
sys.path[:0]=['/data/analysis/avzvol-pilot','/data/analysis/avzvol-expansion']
from bounded_csr import bounded_csr
from fast_racimo import replay
from run_pilot import sid_hour,DAY,CUTOFF
from expanded_passage import evaluate,reference,STATUS
P=Path(os.environ['REPLICATION_ROOT']);P.mkdir(parents=True,exist_ok=True);OLD=Path('/data/analysis/avzvol-pilot')
CONTRACTS=[os.environ['REPLICATION_CONTRACT']];DS=[20,40,80];QS=[.25,.5,.75];ORIGINS=['real_racimo','delayed_translated250','clock_price_width1','clock_price_width10','clock_price_width20']
HEAD=['contract','session','origin','D','q','anchor_idx','trigger_idx','last_idx','status','occupancy','target_ticks','opposite_ticks','trigger_ticks','peak_distance','skipped_small','source_trigger_sequence','source_last_sequence']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
 return h.hexdigest()
def prepare(contract,pin,sel,win):
 root=P/contract;root.mkdir(exist_ok=True);source=Path('/data/raw/avzvol-ticks')/pin['file'];assert source.stat().st_size==pin['bytes'] and digest(source)==pin['sha256'];pf=pq.ParquetFile(source);assert pf.metadata.num_rows==pin['rows']
 for i in range(pf.metadata.num_row_groups):
  rg=pf.metadata.row_group(i);s=rg.column(pf.schema_arrow.names.index('ts_utc_ns')).statistics;assert s.max<CUTOFF and s.null_count==0
  for c,val in [('instrument','MNQ'),('contract',contract.replace('_',' '))]:
   x=rg.column(pf.schema_arrow.names.index(c)).statistics;assert x.min==x.max==val and x.null_count==0
 approved=np.array([pd.Timestamp(x['session_label']).value//DAY for x in sel]);a=win['legacy_read_window_start_utc_ns'];z=min(win['legacy_read_window_end_utc_ns_exclusive'],CUTOFF)
 paths={c:root/(c+'-private.bin') for c in ['ts','px','vol','sid','seq']};files={c:paths[c].open('wb') for c in paths};counts=Counter();full_counts=Counter();outside_hours=Counter();nin=nout=excluded=maintenance=0;lastts=-1;lastseq=-1
 for batch in pf.iter_batches(batch_size=262144,columns=['ts_utc_ns','price_ticks','volume','sequence'],use_threads=False):
  ts,px,vol,seq=[batch.column(i).to_numpy(zero_copy_only=False) for i in range(4)];assert ts[0]>=lastts and seq[0]>lastseq and np.all(np.diff(ts)>=0) and np.all(np.diff(seq)>0) and np.all(vol>0);lastts=int(ts[-1]);lastseq=int(seq[-1]);inside=(ts>=a)&(ts<z);all_sid,all_hour=sid_hour(ts)
  for dd,nn in zip(*np.unique(all_sid,return_counts=True)):full_counts[int(dd)]+=int(nn)
  outside_selected=np.isin(all_sid,approved)&~inside
  for hh,nn in zip(*np.unique(all_hour[outside_selected],return_counts=True)):outside_hours[int(hh)]+=int(nn)
  if not inside.any():continue
  ts,px,vol,seq=[x[inside] for x in [ts,px,vol,seq]];sid,hour=all_sid[inside],all_hour[inside];nin+=len(ts)
  for d,n in zip(*np.unique(sid,return_counts=True)):counts[int(d)]+=int(n)
  mask=(sid<approved.min())|np.isin(sid,approved);excluded+=int((~mask).sum());maintenance+=int((mask&(hour==16)).sum());keep=mask&(hour!=16);nout+=int(keep.sum())
  for c,arr in zip(paths,[ts,px,vol,sid,seq]):np.asarray(arr[keep],dtype=np.float64 if c=='vol' else np.int64).tofile(files[c])
 for f in files.values():f.close()
 for x in sel:assert full_counts[pd.Timestamp(x['session_label']).value//DAY]==int(float(x['trades']))
 assert all(hh==16 for hh in outside_hours), 'SELECTED_USABLE_RECORD_OUTSIDE_DECLARED_WINDOW'
 # Catalog counts describe full raw sessions; legacy window can stop at16h.
 # Outside-window selected observations are only already-excluded maintenance.
 arrays=[np.memmap(paths[c],dtype=np.float64 if c=='vol' else np.int64,mode='r') for c in paths];assert all(len(x)==nout for x in arrays);ts,px,vol,sid,seq=arrays
 ss=np.r_[0,np.flatnonzero(sid[1:]!=sid[:-1])+1];ee=np.r_[ss[1:],nout];st=np.concatenate([np.arange(a,b,25,dtype=np.int64) for a,b in zip(ss,ee)]);en=np.minimum(st+25,np.repeat(ee,[(b-a+24)//25 for a,b in zip(ss,ee)]));bs=np.asarray(sid[st]);full=en-st==25
 idx=np.memmap(root/'bar-index-private.bin',dtype=np.int64,mode='w+',shape=(nout,))
 for j,(a,b) in enumerate(zip(st,en)):idx[a:b]=j
 bars=SimpleNamespace(start_ns=np.asarray(ts[st]),end_ns=np.asarray(ts[en-1]),open_t=np.asarray(px[st]),close_t=np.asarray(px[en-1]),high_t=np.maximum.reduceat(px,st),low_t=np.minimum.reduceat(px,st),volume=np.add.reduceat(vol,st),tick_bar_idx=idx)
 fps=bounded_csr(px,vol,st,en,root);assert np.array_equal(np.add.reduceat(fps.vols,fps.offsets[:-1]),bars.volume)
 print('PREPARED',contract,nout,'ticks',len(st),'bars',flush=True)
 qa=dict(source=pin,raw_original_unchanged=True,read_window_rows=nin,detector_rows=nout,removed_nonselected_after_first_selected=excluded,removed_maintenance_derived=maintenance,selected_sessions=len(sel),selected_raw_counts_exact=True,selected_records_outside_legacy_window=sum(outside_hours.values()),outside_window_selected_hours=dict(outside_hours),source_certified=False,holdout_opened=False)
 (root/'source-selection-check.json').write_text(json.dumps(qa,indent=2)+'\n');return root,ts,px,seq,bars,fps,st,en,bs,full,ss,ee,approved

def main():
 t0=time.time();auth=json.loads(Path('/data/raw/avzvol-selected-risk/pr111-authorization.json').read_text());assert auth['gates']['user_exploratory_authorized'] and not auth['holdout_access_authorized'];selected=list(csv.DictReader(open('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv')));metadata=json.loads(Path('/data/raw/avzvol-selected-risk/metadata-review.json').read_text())
 manifest=dict(status='FIXED_BEFORE_REPLICATION_LABELS',contracts=CONTRACTS,config=dict(percentile=80,window_bars=5,min_zones=8,racimo_window=1000,max_height_ticks=20),D=DS,q=QS,primary=dict(D=40,q=.5,endpoint='touch',mode='first_D_qualifying',occupancy_lt=.25,temporal_bin_records=6250),sensitivity_bin_records=25000,origins=ORIGINS,clock_reference='full bar256 then every250 full bars from session start; fixed widths1/10/20 and anchor price center; no racimo detection required for reference births',geometry_reference_caveat='fixed width/center controls are not exact width/anchor-position matches to real births',wait_bars=2000,horizon_bars=2000,gap_seconds=10,context='fraction of last256 closed bars whose ranges intersect remaining corridor to edge',source_pins=[next(x for x in auth['files'] if x['contract']==c) for c in CONTRACTS],event_dates={c:[x['session_label'] for x in selected if x['contract']==c] for c in CONTRACTS},source_certified=False,holdout_opened=False,pnl_computed=False,other_contract_labels_not_used_to_retune=True,not_virgin_holdout='prior broad bar-based research exists; fixed-parameter cross-contract diagnostic, not sealed test',rule_groups_per_contract=45,source_selection_sha256=digest(Path('/data/analysis/avzvol-selected-risk/selected-event-sessions.csv')),code_sha256={n:digest(P/n) for n in ['run_replication.py','bounded_csr.py']})
 (P/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('MANIFEST_PINNED',flush=True)
 summaries=[];day_summary=[];census=[];checks=[];label_rows=signal_rows=0
 for contract in CONTRACTS:
  pin=next(x for x in auth['files'] if x['contract']==contract);sel=[x for x in selected if x['contract']==contract];win=next(x for x in metadata['contracts'] if x['contract']==contract)
  root,ts,px,seq,bars,fps,st,en,bs,full,ss,ee,approved=prepare(contract,pin,sel,win);bar=bars.tick_bar_idx;nbar=len(st);startbar=np.maximum.accumulate(np.where(np.r_[True,bs[1:]!=bs[:-1]],np.arange(nbar),0));endbar=ee[np.searchsorted(ss,st,side='right')-1]
  mod=types.ModuleType('legacy');mod.__dict__.update(np=np,pd=pd,defaultdict=defaultdict);exec((OLD/'legacy_detector.py').read_text(),mod.__dict__);det=mod.run(bars,fps,bs,dict(racimo_min=0,ob_bars=0,window_bars=5,detection_percentile=80));zz=det['zones'];birth=replay(np.array([x['bar'] for x in zz]),np.array([x['low_tick'] for x in zz]),np.array([x['high_tick'] for x in zz]),8,1000,20);birth=birth[np.isin(bs[birth[:,0]],approved)&full[birth[:,0]]];del zz,det,fps;gc.collect();print('RACIMOS',contract,len(birth),flush=True)
  if contract=='MNQ_12-26':assert len(birth)==4631
  cases=[]
  for b,_,lo,hi in birth:
   anchor=int(en[b]-1);label=str(pd.Timestamp(int(bs[b])*DAY).date());cases.append(('real_racimo',int(b),anchor,int(endbar[b]),int(lo),int(hi),label))
   cb=b+250
   if cb<nbar and bs[cb]==bs[b] and full[cb]:
    ca=int(en[cb]-1);shift=int(px[ca]-px[anchor]);cases.append(('delayed_translated250',int(cb),ca,int(endbar[cb]),int(lo)+shift,int(hi)+shift,label))
  # Synthetic geometry references originate on a regular clock, not a volume event.
  for b in range(nbar):
   if not full[b] or bs[b] not in approved:continue
   within=b-int(startbar[b])
   if within<256 or (within-256)%250:continue
   anchor=int(en[b]-1);label=str(pd.Timestamp(int(bs[b])*DAY).date())
   for width in [1,10,20]:
    lo=int(px[anchor])-(width-1)//2;hi=lo+width-1;cases.append((f'clock_price_width{width}',b,anchor,int(endbar[b]),lo,hi,label))
  counter=defaultdict(Counter);days=defaultdict(Counter);references_done=set();f=(root/'signals-private.csv').open('w',newline='');writer=csv.DictWriter(f,fieldnames=HEAD);writer.writeheader()
  for origin,b,anchor,stop,low,high,label in cases:
   assert label in manifest['event_dates'][contract]
   for d,q in itertools.product(DS,QS):
    key=(contract,origin,d,q);c=counter[key];dc=days[(*key,label)];c['formations']+=1;dc['formations']+=1;result=evaluate(px,ts,bar,anchor,stop,low,high,d,q,0,1);status,ex,pk,tr,last,side,peak,target,opposite,skips=result;c[STATUS[status]]+=1;dc[STATUS[status]]+=1;label_rows+=1
    if tr<0:continue
    c['signals']+=1;dc['signals']+=1;signal_rows+=1
    tb=int(bar[tr]);hb=np.arange(max(int(startbar[tb]),tb-256),tb);bottom=min(int(px[tr]),target);top=max(int(px[tr]),target);occupancy=float(np.mean((bars.high_t[hb]>=bottom)&(bars.low_t[hb]<=top))) if len(hb) else None
    writer.writerow(dict(contract=contract,session=label,origin=origin,D=d,q=q,anchor_idx=anchor,trigger_idx=tr,last_idx=last,status=STATUS[status],occupancy=occupancy,target_ticks=target,opposite_ticks=opposite,trigger_ticks=int(px[tr]),peak_distance=peak,skipped_small=skips,source_trigger_sequence=int(seq[tr]),source_last_sequence=int(seq[last])))
    assert abs(px[tr]-target)==abs(px[tr]-opposite) and tr>anchor and last>=tr
    strata=(origin,d,q)
    if strata not in references_done and last-anchor<10000:
     end=min(stop,last+2);expected=reference(px[anchor:end].tolist(),ts[anchor:end].tolist(),(bar[anchor:end]-bar[anchor]).tolist(),0,end-anchor,low,high,d,q,0,1);actual=list(result)
     for j in [1,2,3,4]:
      if actual[j]>=0:actual[j]-=anchor
     assert tuple(actual)==expected,(contract,strata,actual,expected);references_done.add(strata);checks.append(dict(contract=contract,origin=origin,D=d,q=q,source_records=end-anchor,exact_reference_match=True))
  f.close()
  for k,c in counter.items():summaries.append({**dict(zip(['contract','origin','D','q'],k)),**c})
  for k,c in days.items():day_summary.append({**dict(zip(['contract','origin','D','q','session'],k)),**c})
  census.append(dict(contract=contract,selected_sessions=len(sel),real_formations=len(birth),origins=dict(Counter(x[0] for x in cases)),source_records=len(ts),detector_bars=nbar,reference_strata_checked=len(references_done)))
  pd.DataFrame(summaries).fillna(0).to_csv(P/'rule-counts.csv',index=False);pd.DataFrame(day_summary).fillna(0).to_csv(P/'daily-counts.csv',index=False)
  # Close mmaps before processing the next source; no accumulated contract buffers.
  del ts,px,seq,bars,st,en,bs,full,ss,ee,approved,bar,startbar,endbar,cases,birth;gc.collect()
 evidence=dict(status='FIXED_REPLICATION_COMPLETE',contracts=census,rule_groups=len(summaries),label_evaluations_not_independent=label_rows,signal_rows_not_independent=signal_rows,scope_leakage=0,reference_checks=checks,source_certified=False,holdout_opened=False,pnl_computed=False,all_six_contracts_complete=False,wall_seconds=time.time()-t0)
 (P/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print('COMPLETE',json.dumps({k:v for k,v in evidence.items() if k!='reference_checks'}),flush=True)
if __name__=='__main__':main()
