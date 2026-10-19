#!/usr/bin/env python3
"""Timestamp-only structural QA of candidate AVZVOL bar identity, NOT research.
No prices, detector, new O5, causal controls, certification or historical attestation.
"""
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

CT='America/Chicago';SIZE=25;CUTOFF=pd.Timestamp('2026-09-30T22:00:00Z').value
CODE_PINS={'stage':'889d9b23cf2428167c93e18bfc45436b9efb48f67dd44d5a43c00654aa5c365c',
           'bars':'03a9aa2c781aeabe13d2ec8f8f401ba43bec4d0a80a6c11fce51953f8d76890f'}
RESOLVER_SHA='9b21eeff751d4397465fcc6831ea615b7dd401a5605a5997f52c8bfd9248117c'
EXPORT_AUDIT_SHA='1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e'
ROOT=Path(__file__).resolve().parents[1]

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def minute_fields(ts):
    um,inv=np.unique(ts//60_000_000_000,return_inverse=True)
    local=pd.to_datetime(um*60_000_000_000,utc=True).tz_convert(CT)
    minute=np.asarray(local.hour*60+local.minute)
    # Exact candidate build_tick_bars/session_ids convention, not a CME calendar.
    ids=np.asarray(local.normalize().asi8)//86_400_000_000_000+(np.asarray(local.hour)>=17)
    return ids[inv],minute[inv]

class TimestampBarBuilder:
    """Stream chronological timestamps; carry partial 25-tick bar across batches.
    Flush SHORT final bar at each declared session boundary, never pad/deduplicate.
    """
    def __init__(self):
        self.current=None;self.remainder=0;self.last=None;self.parts=[];self.counts=Counter()
    def feed(self,ts,sids):
        require(len(ts)==len(sids),'length mismatch')
        if len(ts)==0:return
        require(not (np.diff(ts)<0).any(),'timestamp backward; no silent sorting')
        require(self.last is None or ts[0]>=self.last,'batch timestamp backward')
        breaks=np.r_[0,np.flatnonzero(np.diff(sids))+1,len(ts)]
        for a,b in zip(breaks[:-1],breaks[1:]):
            sid=int(sids[a]);x=ts[a:b]
            if sid!=self.current:
                if self.remainder:self.parts.append(np.array([self.last],dtype=np.int64))
                self.current=sid;self.remainder=0
            first=SIZE-self.remainder-1
            self.parts.append(x[first::SIZE].copy())
            self.remainder=(self.remainder+len(x))%SIZE
            self.counts[sid]+=len(x);self.last=int(x[-1])
    def finish(self):
        if self.remainder:self.parts.append(np.array([self.last],dtype=np.int64));self.remainder=0
        result=np.concatenate(self.parts) if self.parts else np.array([],dtype=np.int64)
        expected=sum((n+SIZE-1)//SIZE for n in self.counts.values())
        require(len(result)==expected,'bar count vs independent session counts mismatch')
        return result

def legacy_session_labels(end):
    """Exact original session_end_vec close grid; not holidays or independent clock."""
    require(len(end)>0,'empty candidate bars')
    d0=pd.Timestamp(int(end.min()),tz='UTC').tz_convert(CT).normalize()-pd.Timedelta(days=1)
    d1=pd.Timestamp(int(end.max()),tz='UTC').tz_convert(CT).normalize()+pd.Timedelta(days=8)
    days=pd.date_range(d0.tz_localize(None),d1.tz_localize(None),freq='D')
    days=days[days.weekday<5]
    closes=np.sort((days+pd.Timedelta(hours=16)).tz_localize(CT).tz_convert('UTC').asi8)
    ix=np.searchsorted(closes,end,side='right');require((ix<len(closes)).all(),'close grid coverage unknown')
    send=closes[ix];u,inv=np.unique(send,return_inverse=True)
    dates=np.asarray(pd.to_datetime(u,utc=True).tz_convert(CT).strftime('%Y%m%d').astype(int))[inv]
    return dates,send,int(d0.hour*60+d0.minute)

def reference_weekday_close_labels(end):
    """Ordinary weekday 16 CT REFERENCE, not independently reviewed CME calendar.
    Calendar-day subtraction avoids the elapsed-Timedelta start-grid DST shift.
    """
    low=pd.Timestamp(int(end.min()),tz='UTC').tz_convert(CT).normalize().tz_localize(None)-pd.Timedelta(days=1)
    high=pd.Timestamp(int(end.max()),tz='UTC').tz_convert(CT).normalize().tz_localize(None)+pd.Timedelta(days=8)
    days=pd.date_range(low,high,freq='D');days=days[days.weekday<5]
    closes=np.sort((days+pd.Timedelta(hours=16)).tz_localize(CT).tz_convert('UTC').asi8)
    ix=np.searchsorted(closes,end,side='right');require((ix<len(closes)).all(),'reference coverage unknown')
    u,inv=np.unique(closes[ix],return_inverse=True)
    return np.asarray(pd.to_datetime(u,utc=True).tz_convert(CT).strftime('%Y%m%d').astype(int))[inv]

def check_export(d,end,labels,clock,logged_bars):
    require(len(end)==logged_bars,'candidate bar count disagrees with historical log')
    require(d[['contract','cell','kind','session','clock','t0','te']].notna().all().all(),'missing export identities')
    require(set(d.kind)<={'real','pseudo'} and not np.isinf(d.o5).any(),'invalid kind/O5')
    for col in ['session','clock','t0','te']:
        require(pd.api.types.is_integer_dtype(d[col]),'noninteger export identity')
    require((d.session<20261001).all() and (d.t0>=0).all(),'invalid/reserved export')
    require((d.t0<len(end)).all(),'anchor out of candidate map')
    t=d.t0.to_numpy();s=d.session.to_numpy();finite=np.isfinite(d.o5)
    require(not (finite & (d.te<0)).any(),'finite O5 without exit')
    require((d.te<=np.iinfo(np.int64).max-200).all(),'bar index overflow')
    session_bad=labels[t]!=s;clock_bad=clock[t]!=d.clock.to_numpy()
    aligned=not session_bad.any() and not clock_bad.any()
    categories=Counter();guard_witness=0;bykind={k:Counter() for k in ['real','pseudo']}
    # Complete candidate map, not sparse anchors. Two full-window checks agree:
    # prefix changes within each export session vs every-label loop of each UNIQUE window.
    cache={}
    for kind,te,ss in zip(d.loc[finite,'kind'],d.loc[finite,'te'],d.loc[finite,'session']):
        te=int(te);ss=int(ss);key=(te,ss)
        if not aligned:cat='UNKNOWN_CANDIDATE_ANCHOR_ALIGNMENT'
        elif te+200>=len(end):cat='POST_WINDOW_OUT_OF_CANDIDATE_BOUNDS'
        else:
            if key not in cache:
                window=labels[te+1:te+201]
                all_same=bool(np.all(window==ss))
                direct=all(int(v)==ss for v in window)
                require(all_same==direct,'independent full-window label mismatch')
                cache[key]=(all_same,bool(labels[te+199]==labels[te] and labels[te+200]!=labels[te]))
            same,witness=cache[key]
            cat='FULL_POST_WINDOW_WITHIN_CANDIDATE_SESSION' if same else 'POST_WINDOW_CROSSES_CANDIDATE_SESSION'
            guard_witness+=int(witness)
        categories[cat]+=1;bykind[kind][cat]+=1
    require(sum(categories.values())==int(finite.sum()),'finite cross-foot mismatch')
    return {'export_rows':len(d),'finite_o5_rows':int(finite.sum()),'missing_o5_rows':int((~finite).sum()),
        'candidate_bar_count':len(end),'historical_logged_bar_count':logged_bars,
        'candidate_map_matches_logged_bar_count':True,
        'anchor_session_mismatch_rows':int(session_bad.sum()),'anchor_clock_mismatch_rows':int(clock_bad.sum()),
        'all_export_anchors_align':aligned,'finite_post_window_categories':dict(categories),
        'legacy_guard_last_bar_cross_witness_rows':guard_witness,
        'by_kind':{k:dict(v) for k,v in bykind.items()},'all_postwindow_labels_checked':aligned,
        'independent_postwindow_check_passed':True,
        'prewindow_not_reconstructible_from_export_alone':True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['raw-inventory','export-inventory','resolver','historical-stage-source','historical-bars-source','log-dir','out-dir']:
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--allow-timestamp-structural-qa',action='store_true',required=True)
    a=p.parse_args()
    require(digest(a.resolver)==RESOLVER_SHA,'resolver pin mismatch')
    require(digest(a.historical_stage_source)==CODE_PINS['stage'] and digest(a.historical_bars_source)==CODE_PINS['bars'],'historical code pin mismatch')
    audit=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json';require(digest(audit)==EXPORT_AUDIT_SHA,'export reference pin mismatch')
    quality=ROOT/'config/research/avzvol_mnq_raw_quality_review_20261010.json'
    rawpins={r['structural_audit']['file']:r['structural_audit'] for r in json.loads(quality.read_text())['files']}
    epins={r['file']:r for r in json.loads(audit.read_text())['covariate_audit']['files']}
    rawinv=json.loads(a.raw_inventory.read_text());einv=json.loads(a.export_inventory.read_text())
    rawpaths={Path(r['file']).name:Path(r['file']) for r in rawinv};epaths={Path(r['file']).name:Path(r['file']) for r in einv}
    require(len(rawpaths)==len(rawinv)==6 and set(rawpaths)==set(rawpins),'raw universe mismatch')
    require(len(epaths)==len(einv)==6 and set(epaths)==set(epins),'export universe mismatch')
    # All 12 file pins and all footer holdout/identity checks BEFORE any payload.
    opened={}
    for name,file in rawpaths.items():
        pin=rawpins[name];pf=pq.ParquetFile(file)
        require(file.stat().st_size==pin['bytes'] and pf.metadata.num_rows==pin['rows'],'raw bytes/rows mismatch')
        for k in range(pf.num_row_groups):
            for col,identity in [('instrument','MNQ'),('contract',pin['contract'])]:
                st=pf.metadata.row_group(k).column(pf.schema_arrow.names.index(col)).statistics
                require(st and st.has_min_max and st.has_null_count and st.null_count==0 and st.min==st.max==identity,'raw identity footer mismatch')
            st=pf.metadata.row_group(k).column(pf.schema_arrow.names.index('ts_utc_ns')).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<CUTOFF,'unknown/reserved raw footer')
        require(digest(file)==pin['sha256'],'raw SHA mismatch');opened[name]=pf
    for name,file in epaths.items():
        pin=epins[name];pf=pq.ParquetFile(file);require(pf.metadata.num_rows==pin['rows'],'export footer rows mismatch')
        for k in range(pf.num_row_groups):
            st=pf.metadata.row_group(k).column(pf.schema_arrow.names.index('session')).statistics
            require(st and st.has_min_max and st.has_null_count and st.null_count==0 and int(st.max)<20261001,'unknown/reserved export footer')
        require(digest(file)==pin['sha256'],'export SHA mismatch')
    resolver=json.loads(a.resolver.read_text());sess=pd.DataFrame(resolver['instruments']['MNQ']['sessions'])
    sess=sess[sess.approved & sess.date.between('2025-07-01','2026-09-30')]
    logs='\n'.join((a.log_dir/(k+'-historical-log.txt')).read_text() for k in ['k1','k2','k3'])
    logged={c:int(n) for c,n in re.findall(r'(MNQ_\d\d-\d\d).*?velas (\d+)',logs)}
    require(set(logged)=={n.removesuffix('_avzp2racgrid.parquet') for n in epins},'historical log universe mismatch')
    a.out_dir.mkdir(parents=True,exist_ok=False);records=[]
    for ename in sorted(epins):
        contract=ename.removesuffix('_avzp2racgrid.parquet');rname=contract+'_ticks_ext.parquet'
        rows=sess[sess.contract==contract]
        # Resolver contract text is exact legacy representation; no fallback.
        require(len(rows)>0,'missing resolver contract')
        ds,source=rows.groupby(['dataset','file']).size().idxmax()
        require(Path(source).name==rname,'resolver file mismatch')
        start=int((pd.Timestamp(rows.date.min()).tz_localize(CT)-pd.Timedelta(days=45)).value)
        stop=int(min((pd.Timestamp(rows.date.max()).tz_localize(CT)+pd.Timedelta(hours=16)).value,CUTOFF))
        builder=TimestampBarBuilder();seen=0;retained=0;pause_removed=0;previous=None
        for batch in opened[rname].iter_batches(batch_size=1_000_000,columns=['ts_utc_ns']):
            ts=batch.column(0).to_numpy();seen+=len(ts)
            require(not (np.diff(ts)<0).any() and (previous is None or ts[0]>=previous),'raw nonchronological: no reconstruction')
            previous=int(ts[-1]);ts=ts[(ts>=start)&(ts<stop)]
            if not len(ts):continue
            sids,minute=minute_fields(ts);keep=~((minute>=960)&(minute<1020))
            pause_removed+=int((~keep).sum());retained+=int(keep.sum())
            builder.feed(ts[keep],sids[keep])
        end=builder.finish();labels,send,gridstart=legacy_session_labels(end);_,minutes=minute_fields(end)
        clock=minutes//30
        d=pq.read_table(epaths[ename],columns=['contract','cell','kind','session','clock','t0','te','o5']).to_pandas()
        require(set(d.contract)=={contract},'export physical contract mismatch')
        record=check_export(d,end,labels,clock,logged[contract])
        record.update(contract=contract,raw_file=rname,raw_sha256=rawpins[rname]['sha256'],export_file=ename,
            export_sha256=epins[ename]['sha256'],candidate_dataset=ds,rows_seen=seen,
            retained_timestamp_rows=retained,pause_timestamp_rows_removed=pause_removed,
            candidate_close_grid_start_minute=gridstart,
            reference_weekday_16_close_label_difference_bars=int((reference_weekday_close_labels(end)!=labels).sum()),
            private_bar_map_saved=True)
        private=a.out_dir/(contract+'-private-map.npz');np.savez_compressed(private,end_ns=end,session=labels,clock=clock)
        record['private_map_sha256']=digest(private);records.append(record)
        print(json.dumps({k:record[k] for k in ['contract','candidate_bar_count','all_export_anchors_align','finite_post_window_categories','legacy_guard_last_bar_cross_witness_rows']}),flush=True)
    totals={k:sum(r[k] for r in records) for k in ['export_rows','finite_o5_rows','missing_o5_rows','candidate_bar_count','anchor_session_mismatch_rows','anchor_clock_mismatch_rows','legacy_guard_last_bar_cross_witness_rows']}
    totals['finite_post_window_categories']=dict(sum((Counter(r['finite_post_window_categories']) for r in records),Counter()))
    evidence={'schema':'edgelab_avzvol_candidate_bar_map_qa_v1','status':'CANDIDATE_TIMESTAMP_MAP_ONLY_NOT_CERTIFIED',
        'source_code_commit':'4e1e26930f9778f974a4dd4946977ac48b1725d8','source_code_pins':CODE_PINS,
        'resolver_sha256':RESOLVER_SHA,'raw_quality_reference_sha256':digest(quality),'export_audit_reference_sha256':EXPORT_AUDIT_SHA,
        'method':'Timestamp-only exact legacy window, pause and session-reset 25-tick count; final short bar retained, timestamps repeated not deduplicated. Compare full bar count to logs and ALL anchors session/clock to exports; inspect all 200 candidate post labels. No price/O5 magnitude used.',
        'all_twelve_pins_and_footers_before_payload':True,'raw_payload_columns_read':['ts_utc_ns'],
        'export_o5_read_for_finiteness_only':True,'private_complete_maps_not_published':True,'files':records,'totals':totals,
        **{k:False for k in ['research_authorized','source_quality_certified','clock_independently_certified','calendar_certified',
            'continuity_certified','liquidity_certified','historical_runtime_consumption_verified','causal_controls_verified',
            'prewindow_verified','new_price_outcomes_computed','existing_o5_recomputed','economic_outcomes_computed',
            'holdout_payload_opened','original_outputs_modified','candidate_alignment_is_scientific_approval']}}
    (a.out_dir/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'status':'STOP','reason':str(exc)}));raise SystemExit(2)
