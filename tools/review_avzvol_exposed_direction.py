#!/usr/bin/env python3
"""Opt-in review of existing direction/continuation exports; no new market outcomes."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,json,hashlib,math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1]
AUDIT_SHA='1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e'
STAGE_SHA='889d9b23cf2428167c93e18bfc45436b9efb48f67dd44d5a43c00654aa5c365c'
CONTRACTS=['MNQ_09-25','MNQ_12-25','MNQ_03-26','MNQ_06-26','MNQ_09-26','MNQ_12-26']
CELLS=[f'{m}_{w}_{a}' for m in (4,5,6,8) for w in (250,500,1000) for a in (20,30,45)]
COLS=['contract','cell','kind','session','clock','t0','te','dir','o2','trend','pos']
KEYS=['contract','session','cell']
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def plan():
    return {'scope':'ALREADY_EXPOSED_DIRECTION_DESCRIPTIVE_NOT_CAUSAL_OR_ECONOMIC','blind_or_preregistered':False,'cell_universe':CELLS,'columns':COLS,
      'primary':'O2 known 0/1 continuation: reach one frozen band height from exited edge in observed exit direction before closing back inside; original same-session maximum 2000 subsequent 25-trade bars, excluding exit bar; not a trading fill probability',
      'missing':'O2=-1 unresolved kept in ledger and adversarial bounds; no recorded exit separate; no imputations or duplicate removal',
      'secondary':'Agreement of pre-anchor 500-bar trend sign with observed later exit, restricted to anchor inside band (pos=0), nonzero trend and valid exit; this is NOT a directional zone signal',
      'weights':'Within contract/session/cell mean real minus legacy pseudo; equal supported sessions then cells then six contracts; all36 cells retained including unsupported',
      'context_check':'O2 compare within exact contract/session/cell/clock/trend strata, equal supported strata per session; descriptive overlap, not calibrated matching or causal controls',
      'bounds':'On exactly primary supported session/cell groups, all observed exits including unresolved O2; lower=success/exits, upper=(success+unresolved)/exits; real lower minus pseudo upper, real upper minus pseudo lower',
      'post_inspection_extension':'Exact clock/trend overlap for trend agreement and same-population O2 decomposition added after first exposed run; diagnostic only, not blind confirmation',
      'no_new_price_outcomes':True,'no_economic_outcomes':True,'no_holdout':True,'no_filter_optimization':True,'no_formal_inference':True}
def aggregate(d,metric,keys=KEYS):
    f=d[d[metric].notna()]
    g=f.groupby(keys+['kind'])[metric].mean().unstack('kind').reindex(columns=['real','pseudo'])
    g['delta']=g.real-g.pseudo
    if keys!=KEYS:
        g=g[g.delta.notna()].groupby(KEYS)[['real','pseudo','delta']].mean()
    return g

def independent_groups(d,metric,keys):
    bins=defaultdict(list)
    for row in d[keys+['kind',metric]].itertuples(index=False,name=None):
        if pd.notna(row[-1]):bins[tuple(row[:-1])].append(float(row[-1]))
    result={}
    for key in bins:
        if key[-1]=='real' and key[:-1]+('pseudo',) in bins:
            r=bins[key];p=bins[key[:-1]+('pseudo',)]
            result[key[:-1]]=(math.fsum(r)/len(r),math.fsum(p)/len(p))
    if keys!=KEYS:
        q=defaultdict(list)
        for key,v in result.items():q[key[:3]].append(v)
        result={k:(math.fsum(v[0] for v in x)/len(x),math.fsum(v[1] for v in x)/len(x)) for k,x in q.items()}
    return result

def summarize(d,metric,keys=KEYS):
    g=aggregate(d,metric,keys);supported=g[g.delta.notna()]
    cc=supported.groupby(['contract','cell'])[['real','pseudo','delta']].mean()
    common=[cell for cell in CELLS if all((c,cell) in cc.index for c in CONTRACTS)]
    direct=independent_groups(d,metric,keys)
    diffs=[]
    for k,r in supported.iterrows():
        a,b=direct[k];diffs.extend([abs(a-r.real),abs(b-r.pseudo),abs(a-b-r.delta)])
    require(set(direct)==set(supported.index) and max(diffs,default=0)<1e-12,'independent group calculation differs')
    def mean(vals):return math.fsum(vals)/len(vals) if vals else None
    cellrows=[]
    for cell in CELLS:
        vals=[cc.loc[(c,cell)] for c in CONTRACTS if (c,cell) in cc.index]
        cellrows.append({'cell':cell,'contracts_supported':len(vals),'common_six_contracts':cell in common,'gap_pp':100*mean([x.delta for x in vals]) if vals else None})
    bycontract=[]
    for c in CONTRACTS:
        vals=[cc.loc[(c,cell)] for cell in common]
        bycontract.append({'contract':c,'real_rate_percent':100*mean([x.real for x in vals]) if vals else None,'pseudo_rate_percent':100*mean([x.pseudo for x in vals]) if vals else None,'gap_pp':100*mean([x.delta for x in vals]) if vals else None})
    headline={k:mean([r[k] for r in bycontract]) if common else None for k in ['real_rate_percent','pseudo_rate_percent','gap_pp']}
    headline.update(common_cells=len(common),supported_session_cell_groups=len(supported),independent_max_error=max(diffs,default=0))
    return {'headline':headline,'contracts':bycontract,'cells':cellrows},supported,common

def censor_bounds(d,supported,common):
    f=d[d.te>=0].copy();f['lower']=f.o2.eq(1).astype(float);f['upper']=f.o2.ne(0).astype(float)
    lo=aggregate(f,'lower').reindex(supported.index);up=aggregate(f,'upper').reindex(supported.index)
    b=pd.DataFrame({'lower':lo.real-up.pseudo,'upper':up.real-lo.pseudo})
    cc=b.groupby(['contract','cell']).mean()
    vals=[cc.loc[(c,cell)] for c in CONTRACTS for cell in common]
    return {'lower_gap_pp':100*math.fsum(v.lower for v in vals)/len(vals),'upper_gap_pp':100*math.fsum(v.upper for v in vals)/len(vals),'population':'all observed exits in exact groups supporting primary known-O2 contrast; equal session/cell/contract weights'} if vals else None

def same_overlap_base(d,metric,keys):
    known=d[d[metric].notna()]
    idx=known.groupby(keys+['kind']).size().unstack('kind').reindex(columns=['real','pseudo']).dropna().index
    keep=pd.MultiIndex.from_frame(known[keys]).isin(idx)
    return summarize(known.loc[keep],metric)[0]

def independent_bounds(d,supported,common):
    bins=defaultdict(lambda:Counter())
    for c,s,cell,kind,te,code in d[KEYS+['kind','te','o2']].itertuples(index=False,name=None):
        if te>=0:bins[(c,s,cell,kind)][int(code)]+=1
    cc=defaultdict(list)
    for c,s,cell in supported.index:
        if cell not in common:continue
        r=bins[(c,s,cell,'real')];p=bins[(c,s,cell,'pseudo')];rn=sum(r.values());pn=sum(p.values())
        cc[(c,cell)].append((r[1]/rn-(p[1]+p[-1])/pn,(r[1]+r[-1])/rn-p[1]/pn))
    means=[(math.fsum(v[0] for v in cc[(c,cell)])/len(cc[(c,cell)]),math.fsum(v[1] for v in cc[(c,cell)])/len(cc[(c,cell)])) for c in CONTRACTS for cell in common]
    return tuple(100*math.fsum(v[i] for v in means)/len(means) for i in [0,1]) if means else (None,None)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inventory','historical-stage-source','out-dir']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--allow-exposed-direction-review',action='store_true',required=True);a=p.parse_args()
    require(digest(a.historical_stage_source)==STAGE_SHA,'historical stage pin mismatch')
    ref=ROOT/'docs/infra/AVZVOL_AUDIT_20261010.json';require(digest(ref)==AUDIT_SHA,'export reference mismatch')
    pins={r['file']:r for r in json.loads(ref.read_text())['covariate_audit']['files']};inv=json.loads(a.inventory.read_text())
    paths={Path(r['file']).name:Path(r['file']) for r in inv};require(len(inv)==len(paths)==6 and set(paths)==set(pins),'exact six exports required')
    opened={}
    for name,file in paths.items():
        pf=pq.ParquetFile(file);require(pf.metadata.num_rows==pins[name]['rows'] and set(COLS)<=set(pf.schema_arrow.names),'export shape mismatch')
        for i in range(pf.num_row_groups):
            s=pf.metadata.row_group(i).column(pf.schema_arrow.names.index('session')).statistics
            require(s and s.has_min_max and s.has_null_count and s.null_count==0 and int(s.max)<20261001,'reserved or unknown partition')
        require(digest(file)==pins[name]['sha256'],'export bytes mismatch');opened[name]=pf
    a.out_dir.mkdir(parents=True,exist_ok=False)
    (a.out_dir/'analysis-plan.json').write_text(json.dumps(plan(),indent=2)+'\n') # BEFORE reading any payload
    frames=[];profile=[]
    for name,pf in opened.items():
        d=pf.read(columns=COLS).to_pandas()
        require(d.notna().all().all() and set(d.contract)=={name.removesuffix('_avzp2racgrid.parquet')},'missing/invalid identity')
        require(set(d.cell)<=set(CELLS) and set(d.kind)<={'real','pseudo'},'unknown cell/kind')
        require(set(d.dir)<={-1,0,1} and set(d.trend)<={-1,0,1} and set(d.pos)<={-1,0,1} and set(d.o2)<={-1,0,1},'invalid outcome code')
        require(((d.te<0)==d.dir.eq(0)).all() and (d.loc[d.te<0,'o2']==-1).all(),'exit code contradiction')
        require((d.loc[d.te>=0,'te']>d.loc[d.te>=0,'t0']).all(),'exit not after anchor')
        profile.append({'file':name,'rows':len(d),'nulls':{c:int(d[c].isna().sum()) for c in COLS},'o2_codes':{str(k):int(v) for k,v in d.o2.value_counts().items()},'duplicate_rows_retained':int(d.duplicated().sum())})
        frames.append(d)
    d=pd.concat(frames,ignore_index=True)
    d['continuation']=d.o2.where(d.o2.isin([0,1]),np.nan).astype(float)
    d['trend_agreement']=np.where(d.pos.eq(0)&d.trend.ne(0)&d.te.ge(0),d.dir.eq(d.trend).astype(float),np.nan)
    primary,sg,common=summarize(d,'continuation')
    context,_,_=summarize(d,'continuation',KEYS+['clock','trend'])
    agreement,_,_=summarize(d,'trend_agreement')
    agreement_context,_,_=summarize(d,'trend_agreement',KEYS+['clock','trend'])
    agreement_overlap_base=same_overlap_base(d,'trend_agreement',KEYS+['clock','trend'])
    overlap_base=same_overlap_base(d,'continuation',KEYS+['clock','trend'])
    bounds=censor_bounds(d,sg,common);check_bounds=independent_bounds(d,sg,common)
    require(bounds is None or max(abs(bounds[k]-v) for k,v in zip(['lower_gap_pp','upper_gap_pp'],check_bounds))<1e-10,'independent bounds mismatch')
    ledgers=[]
    for c in CONTRACTS:
        for kind in ['real','pseudo']:
            x=d[d.contract.eq(c)&d.kind.eq(kind)];ex=x[x.te>=0];known=x[x.o2.isin([0,1])]
            ledgers.append({'contract':c,'kind':kind,'rows':len(x),'no_exit':int((x.te<0).sum()),'observed_exit':len(ex),'exit_up':int(ex.dir.eq(1).sum()),'exit_down':int(ex.dir.eq(-1).sum()),'o2_success':int(x.o2.eq(1).sum()),'o2_return_before_threshold':int(x.o2.eq(0).sum()),'o2_unresolved_after_exit':int((x.te.ge(0)&x.o2.eq(-1)).sum()),'o2_known':len(known),'trend_agreement_eligible':int(x.trend_agreement.notna().sum()),'trend_agreement_success':int(x.trend_agreement.eq(1).sum())})
    # Independent whole-population counts directly from row tuples, not vector masks.
    check=Counter()
    for kind,te,code in zip(d.kind,d.te,d.o2):
        check[(kind,'rows')]+=1;check[(kind,'no_exit')]+=int(te<0);check[(kind,'o2_success')]+=int(code==1);check[(kind,'o2_return_before_threshold')]+=int(code==0);check[(kind,'o2_unresolved_after_exit')]+=int(te>=0 and code==-1)
    for kind in ['real','pseudo']:
        for k in ['rows','no_exit','o2_success','o2_return_before_threshold','o2_unresolved_after_exit']:require(sum(r[k] for r in ledgers if r['kind']==kind)==check[(kind,k)],'independent count discrepancy')
    result={'schema':'edgelab_exposed_direction_review_v1','plan':plan(),'source_export_reference_sha256':AUDIT_SHA,'source_stage_sha256':STAGE_SHA,'all_six_pins_and_footers_before_payload':True,'profile':profile,'rows':len(d),'accounting':ledgers,'o2_continuation':primary,'o2_context_exact_strata':context,'o2_unresolved_adversarial_bounds':bounds,'bounds_independently_checked':True,'o2_same_context_overlap_unstratified':overlap_base,'trend_exit_agreement':agreement,'trend_exit_agreement_context_exact_strata':agreement_context,'trend_same_context_overlap_unstratified':agreement_overlap_base,'independent_counts_checked':True,
      'comparison_plan':[{'grain':'six contracts, supported session/cell strata','population':'known O2, legacy real and pseudo','unit':'percentage points','derivation':'equal-weight real minus pseudo continuation rate','disposition':'chart','reason':'shows cross-contract sign and heterogeneity without promoting a winner'},{'grain':'aggregate exact clock/trend supported overlap','population':'known O2','unit':'percentage points','disposition':'prose','reason':'diagnostic overlap only, not equivalent to matched causal controls'},{'grain':'aggregate trend/exit agreement','population':'inside-band anchors, nonzero pretrend and observed exit','unit':'percent and percentage points','disposition':'prose','reason':'trend baseline is not a predicted zone direction'},{'grain':'36 cells each endpoint','population':'all supported groups, missing retained','unit':'percentage points','disposition':'table','reason':'retain every cell and support exception without selecting by effect'}],
      **{k:False for k in ['new_market_outcomes_computed','raw_price_payload_read','economic_outcomes_computed','holdout_payload_read','causal_zone_direction_validated','controls_zone_free_certified','formal_inference_executed','research_release_authorized','historical_outputs_modified']}}
    (a.out_dir/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    for k in ['o2_continuation','o2_context_exact_strata','o2_same_context_overlap_unstratified','trend_exit_agreement','trend_exit_agreement_context_exact_strata']:print(k,json.dumps(result[k]['headline']),json.dumps(result[k]['contracts']))
    print('bounds',result['o2_unresolved_adversarial_bounds']);print('accounting',ledgers)
if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,OSError) as e:print(json.dumps({'status':'STOP','reason':str(e)}));raise SystemExit(2)
