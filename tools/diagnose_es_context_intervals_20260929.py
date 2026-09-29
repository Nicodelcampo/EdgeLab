import json, hashlib, csv, sys
from pathlib import Path
import pandas as pd

RAW=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/data/raw/es_diagnostic')
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/data/analysis/es_nq_ipc_review')
OUT.mkdir(parents=True,exist_ok=True)
d=pd.read_csv(RAW/'intervals.csv', dtype={'sesion':str})
d['evaluacion']=d['evaluacion'].astype(str).str.lower().eq('true')
for c in ('inicio_ct','fin_ct'):
    d[c]=pd.to_datetime(d[c],utc=True)
assert ((d.fin_ct-d.inicio_ct).dt.total_seconds()/60 == d.minutos).all()
assert not d.duplicated().any()
g=json.loads((RAW/'gate_report.json').read_text())
assert set(d.loc[d.evaluacion,'sesion'])==set(g['evaluation_sessions'])
assert set(d.loc[~d.evaluacion,'sesion'])==set(g['train_sessions'])
overlaps=0; gaps=[]
for session,sub in d.groupby('sesion'):
    sub=sub.sort_values('inicio_ct')
    diff=(sub.inicio_ct.iloc[1:].reset_index(drop=True)-sub.fin_ct.iloc[:-1].reset_index(drop=True)).dt.total_seconds()/60
    overlaps+=int((diff<0).sum())
    gaps.extend([{'session':session,'gap_min':float(v)} for v in diff[diff>0]])
assert overlaps==0
summary={}
for name,sub in [('train',d[~d.evaluacion]),('eval',d[d.evaluacion]),('all',d)]:
    summary[name]={'sessions':sub.sesion.nunique(),'minutes':int(sub.minutos.sum()),
      'states':{state:{'runs':len(x),'minutes':int(x.minutos.sum()),
             'median_run':float(x.minutos.median()),'max_run':int(x.minutos.max())}
          for state,x in sub.groupby('estado')}}
for state,val in g['persistence'].items():
    assert summary['eval']['states'][state]['minutes']==val['minutes']
    assert summary['eval']['states'][state]['median_run']==val['median_run_min']
# Independent CSV-module cross-foot.
rows=list(csv.DictReader((RAW/'intervals.csv').open()))
independent={}
for row in rows:
    if row['evaluacion']=='True':
        independent[row['estado']]=independent.get(row['estado'],0)+int(row['minutos'])
assert sum(independent.values())==g['coverage']['labeled']
assert all(independent[k]==v['minutes'] for k,v in summary['eval']['states'].items())
by=d[d.evaluacion].groupby(['sesion','estado']).minutos.sum().unstack(fill_value=0)
toxic_share=by['toxic']/by.sum(axis=1)
out={
 'source_commit':'3804c276b00a3a610aae76fc486c098a76cccf41',
 'outcomes_accessed':False,
 'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.iterdir()},
 'profile_resolution':{'sesion':'nonadditive YYYYMMDD identifier','dates':'parsed timezone-aware UTC',
                       'grain':'one half-open run [start,end)','gaps':'preserved, never filled or pooled across gaps'},
 'summary':summary,'overlap_count':overlaps,'internal_gap_count':len(gaps),
 'internal_gaps':gaps,'toxic_sessions_eval':int((by['toxic']>0).sum()),
 'toxic_share_eval_range':{'min':float(toxic_share.min()),'max':float(toxic_share.max())},
 'independent_check':{'pass':True,'eval_minutes':sum(independent.values()),'eval_state_minutes':independent},
 'code_findings':[
   'seed_labels evaluates forward-filter HMM argmax before sticky filtering and toxic overlay',
   'toxic overlay calibrated on train features, not on HMM seed',
   'same overlay across HMM seeds is deterministic identity, not out-of-sample validity',
   'calm/non-toxic are not synonymous: normal and volatile are also non-toxic',
   'endpoints of full runs are retrospective; live rule must never use eventual duration'],
 'visual_plan':[{'finding':'utility not measured; underlying code distinction is the relevant finding',
                 'disposition':'prose','reason':'state composition would not establish predictive/economic utility'}]
}
(OUT/'evidence.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:out[k] for k in ['summary','overlap_count','internal_gap_count','toxic_sessions_eval','toxic_share_eval_range','independent_check']},indent=2))