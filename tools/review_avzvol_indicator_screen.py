"""Reproduce a descriptive screen of already-exposed export labels.

No raw tick loader, P&L, order generation, threshold promotion, or blind holdout.
Requires optional research dependencies numpy, pandas and pyarrow.
"""
from pathlib import Path
import json,math
from collections import Counter
import numpy as np
import pandas as pd
A=None
FEATURES=['trend_dir','momentum_dir','trend_sign_dir','volume100','volume_occ','duration100','duration_occ','amplitude','occupancy','band_height','clock','noise_control','exit_delay_bars','delay_per_declared_band_tick','range_over_band','momentum_per_range','trend_per_range','log_intensity100','log_intensity_change']
PAIRS={'delay_x_range_band':('exit_delay_bars','range_over_band'),'delay_x_momentum':('exit_delay_bars','momentum_dir'),'range_band_x_momentum':('range_over_band','momentum_dir'),'occupancy_x_range_band':('occupancy','range_over_band'),'delay_x_duration100':('exit_delay_bars','duration100'),'trend_x_momentum':('trend_dir','momentum_dir'),'intensity_x_momentum':('log_intensity100','momentum_dir')}
LABELS={'continuation':'o2','post_retest_exit_side':'o3b'}

def weights(d):
    sizes=d.groupby(['session','contract','t0'])['t0'].transform('size').to_numpy(float)
    anchors=d.groupby(['session','contract'])['t0'].transform('nunique').to_numpy(float)
    contracts=d.groupby('session')['contract'].transform('nunique').to_numpy(float)
    w=1/(sizes*anchors*contracts)
    sums=pd.Series(w,index=d.index).groupby(d.session).sum()
    assert np.allclose(sums.to_numpy(),1,atol=1e-12)
    return w

def weighted_quantile(x,w,level):
    order=np.argsort(x,kind='stable');sx=x[order];sw=w[order]
    cdf=(np.cumsum(sw)-.5*sw)/sw.sum()
    return float(np.interp(level,cdf,sx))

def auc(y,p,w):
    _,inv=np.unique(p,return_inverse=True)
    pos=np.bincount(inv,weights=w*y);neg=np.bincount(inv,weights=w*(1-y))
    if pos.sum()==0 or neg.sum()==0:return None
    return float(np.dot(pos,np.cumsum(neg)-.5*neg)/(pos.sum()*neg.sum()))

def stats(y,p,w):
    b=float(np.sum(w*(p-y)**2)/w.sum())
    independent=math.fsum(float(ww)*float(pp-yy)**2 for yy,pp,ww in zip(y,p,w))/math.fsum(map(float,w))
    assert abs(b-independent)<1e-12
    # Independent all-pairs oracle on a bounded deterministic sample for tied weighted AUC.
    idx=np.arange(min(len(y),256));yy=y[idx];pp=p[idx];ww=w[idx]
    pos=yy==1;neg=yy==0
    if pos.any() and neg.any():
        cmp=(pp[pos,None]>pp[None,neg])+.5*(pp[pos,None]==pp[None,neg])
        brute=float(np.sum(cmp*ww[pos,None]*ww[None,neg])/(ww[pos].sum()*ww[neg].sum()))
        assert abs(auc(yy,pp,ww)-brute)<1e-12
    return {'brier':b,'auc':auc(y,p,w),'weighted_label_rate':float(np.dot(y,w)/w.sum())}

def rate_map(keys,y,w,prior):
    f=pd.DataFrame({'k':keys,'yes':y*w,'w':w});s=f.groupby('k').sum()
    return (s.yes/s.w).to_dict()

def logit(p):
    p=np.clip(p,1e-6,1-1e-6);return np.log(p/(1-p))

def predict(train,test,feature,y,w,base,prior):
    if feature in PAIRS:
        parts=[];testparts=[];cuts={}
        for col in PAIRS[feature]:
            x=train[col].to_numpy(float);order=np.argsort(x,kind='stable');sw=w[order]
            cdf=(np.cumsum(sw)-.5*sw)/sw.sum();edges=np.unique(np.interp([1/3,2/3],cdf,x[order]))
            parts.append(np.searchsorted(edges,x,side='right').astype(str))
            testparts.append(np.searchsorted(edges,test[col].to_numpy(float),side='right').astype(str));cuts[col]=edges.tolist()
        tr=np.char.add(np.char.add(parts[0],':'),parts[1]);te=np.char.add(np.char.add(testparts[0],':'),testparts[1])
    elif feature=='clock':
        tr=train[feature].astype(str).to_numpy();te=test[feature].astype(str).to_numpy();cuts=None
    else:
        x=train[feature].to_numpy(float);order=np.argsort(x,kind='stable');sx=x[order];sw=w[order]
        cdf=(np.cumsum(sw)-.5*sw)/sw.sum();cuts=np.unique(np.interp([.2,.4,.6,.8],cdf,sx))
        tr=np.searchsorted(cuts,x,side='right');te=np.searchsorted(cuts,test[feature].to_numpy(float),side='right')
    mp=rate_map(tr,y,w,prior);context=np.array([mp.get(k,prior) for k in te])
    p=1/(1+np.exp(-(logit(base)+logit(context)-logit(prior))))
    return p,{'training_only_edges':cuts if isinstance(cuts,dict) else None if cuts is None else cuts.tolist(),'training_only_bucket_rates':{str(k):float(v) for k,v in mp.items()}},te

def main(argv=None):
    import argparse, hashlib
    import pyarrow.parquet as pq
    global A
    parser=argparse.ArgumentParser(description="Exploratory geometric screen: no profits or new price outcomes")
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--plan',type=Path,default=Path(__file__).resolve().parents[1]/'docs/research/avzvol_indicator_screen_20261011/analysis-plan.json')
    args=parser.parse_args(argv);A=args.out;A.mkdir(parents=True,exist_ok=True)
    plan=json.loads(args.plan.read_text());frames=[];profiles=[]
    for pin in sorted(plan['pins'],key=lambda x:x['basename']):
        paths=list(args.input_dir.rglob(pin['basename']))
        if len(paths)!=1:raise ValueError('Each pinned basename must resolve exactly once: '+pin['basename'])
        path=paths[0]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pin['sha256']:raise ValueError('Pinned hash mismatch: '+pin['basename'])
        pf=pq.ParquetFile(path)
        if pf.metadata.num_rows!=pin['rows']:raise ValueError('Pinned rows mismatch')
        si=pf.schema_arrow.names.index('session')
        for i in range(pf.metadata.num_row_groups):
            st=pf.metadata.row_group(i).column(si).statistics
            if st is None or not st.has_min_max or st.max>=20261001:raise ValueError('Holdout isolation not demonstrated')
        frame=pq.read_table(path,columns=plan['analytical_columns']).to_pandas()
        if not frame.notna().all().all():raise ValueError('Unexpected nulls')
        profiles.append({'basename':pin['basename'],'rows':len(frame),'session_min':int(frame.session.min()),'session_max':int(frame.session.max()),'duplicate_identity_rows':int(frame.duplicated(['contract','session','t0','cell','kind']).sum())})
        frames.append(frame)
    (A/'analysis-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    (A/'native-profile.json').write_text(json.dumps({'profiles':profiles,'duplicates':'retained and share anchor weight'},indent=2))
    if len(frames)!=6:raise ValueError('Expected six pinned exports')
    d=pd.concat(frames,ignore_index=True);assert len(d)==544531
    assert d.notna().all().all();assert (d.session<20261001).all()
    ledger=[]
    for cohort in ['real','pseudo']:
        q=d[d.kind.eq(cohort)&d.pos.eq(0)]
        ledger.append({'kind':cohort,'inside_anchor_rows':len(q),'no_exit_rows':int((q.te<0).sum()),
                       'o2_unresolved_given_exit':int(((q.te>=0)&q.o2.eq(-1)).sum()),
                       'o3b_no_retest':int(q.o3a.eq(0).sum()),'o3b_same_bar_both':int(q.o3b.eq(-2).sum()),
                       'o3b_unresolved_given_retest':int((q.o3a.eq(1)&q.o3b.eq(-1)).sum())})
    dates=np.sort(d.session.unique());seed=int(len(dates)*.4)
    blocks=np.array_split(dates[seed:],3)
    q=d[d.pos.eq(0)&d.te.ge(0)].copy()
    q['trend_dir']=q.trend_h*q.dir;q['momentum_dir']=q.mom100_h*q.dir;q['trend_sign_dir']=q.trend*q.dir
    for feat,col in [('volume100','vol_100'),('volume_occ','vol_occ'),('duration100','dur_100'),('duration_occ','dur_occ')]:q[feat]=np.log1p(q[col])
    q['amplitude']=q.amp;q['occupancy']=q.occ;q['band_height']=q.h
    assert (q.te>=q.t0).all() and (q.h>0).all() and (q.amp>0).all()
    assert (q.mx_h>=0).all()
    q['exit_delay_bars']=q.te-q.t0;q['delay_per_declared_band_tick']=(q.te-q.t0)/q.h
    q['range_over_band']=q.amp/q.h
    q['momentum_per_range']=q.mom100_h*q.dir*q.h/q.amp;q['trend_per_range']=q.trend_h*q.dir*q.h/q.amp
    q['log_intensity100']=q.vol_100-q.dur_100
    q['log_intensity_change']=(q.vol_100-q.dur_100)-(q.vol_occ-q.dur_occ)
    noise_keys=pd.MultiIndex.from_frame(q[['contract','session','t0']]);codes,uniques=pd.factorize(noise_keys,sort=False)
    q['noise_control']=np.random.default_rng(20261011).random(len(uniques))[codes]
    records=[];contracts=[];foldinfo=[];models=[];buckets=[]
    for k,testdates in enumerate(blocks,1):
        testfirst=int(testdates[0]);pos=int(np.searchsorted(dates,testfirst));train_dates=dates[:pos-1]
        assert train_dates[-1]<dates[pos-1]<testdates[0]
        foldinfo.append({'fold':k,'training_first':int(train_dates[0]),'training_last':int(train_dates[-1]),
                         'embargo_session':int(dates[pos-1]),'test_first':testfirst,'test_last':int(testdates[-1]),
                         'training_global_sessions':len(train_dates),'test_global_sessions':len(testdates)})
        for cohort in ['real','pseudo']:
            for endpoint,label in LABELS.items():
                z=q[q.kind.eq(cohort)&q[label].isin([0,1])]
                tr=z[z.session.isin(train_dates)].copy();te=z[z.session.isin(testdates)].copy()
                assert len(tr)>0 and len(te)>0 and set(tr.session).isdisjoint(set(te.session))
                y=tr[label].to_numpy(float);yt=te[label].to_numpy(float);w=weights(tr);wt=weights(te)
                prior=float(np.dot(y,w)/w.sum());mp=rate_map(tr.cell.to_numpy(),y,w,prior)
                base=np.array([mp.get(c,prior) for c in te.cell]);baseline=stats(yt,base,wt)
                all_predictions={'cell_baseline':base}
                for f in FEATURES+list(PAIRS):
                    p,model,bucket=predict(tr,te,f,y,w,base,prior);all_predictions[f]=p
                    models.append({'fold':k,'cohort':cohort,'endpoint':endpoint,'feature':f,**model})
                    for b in np.unique(bucket):
                        mask=bucket==b;mass=math.fsum(map(float,wt[mask]));yes=math.fsum(map(float,wt[mask]*yt[mask]))
                        buckets.append({'fold':k,'cohort':cohort,'endpoint':endpoint,'feature':f,'bucket':str(b),
                          'training_only_edges':json.dumps(model['training_only_edges']),'rows':int(mask.sum()),
                          'sessions':int(te.loc[mask,'session'].nunique()),
                          'anchor_keys':len(te.loc[mask,['contract','session','t0']].drop_duplicates()),
                          'test_weight_mass':mass,'weighted_label_rate':yes/mass,
                          'observed_excursion_h_p50':weighted_quantile(te.loc[mask,'mx_h'].to_numpy(float),wt[mask],.5),
                          'observed_excursion_h_p90':weighted_quantile(te.loc[mask,'mx_h'].to_numpy(float),wt[mask],.9),
                          'observed_excursion_ticks_p50':weighted_quantile((te.loc[mask,'mx_h']*te.loc[mask,'h']).to_numpy(float),wt[mask],.5),
                          'observed_excursion_ticks_p90':weighted_quantile((te.loc[mask,'mx_h']*te.loc[mask,'h']).to_numpy(float),wt[mask],.9)})
                for f,p in all_predictions.items():
                    m=stats(yt,p,wt)
                    records.append({'fold':k,'cohort':cohort,'endpoint':endpoint,'feature':f,
                      'train_rows':len(tr),'test_rows':len(te),'test_sessions':int(te.session.nunique()),
                      'test_anchor_keys':len(te[['contract','session','t0']].drop_duplicates()),
                      **m,'baseline_brier':baseline['brier'],'brier_reduction':baseline['brier']-m['brier'],
                      'baseline_auc':baseline['auc'],'auc_increment':m['auc']-baseline['auc']})
                    for c in sorted(te.contract.unique()):
                        mask=te.contract.eq(c).to_numpy();wc=weights(te.loc[mask]);mc=stats(yt[mask],p[mask],wc);bc=stats(yt[mask],base[mask],wc)
                        contracts.append({'fold':k,'cohort':cohort,'endpoint':endpoint,'feature':f,'contract':c,
                          'rows':int(mask.sum()),'sessions':int(te.loc[mask,'session'].nunique()),**mc,
                          'brier_reduction':bc['brier']-mc['brier'],'auc_increment':None if mc['auc'] is None or bc['auc'] is None else mc['auc']-bc['auc']})
    pd.DataFrame(buckets).to_csv(A/'test-bucket-metrics.csv',index=False)
    rows=pd.DataFrame(records);rows.to_csv(A/'fold-metrics.csv',index=False);pd.DataFrame(contracts).to_csv(A/'contract-fold-metrics.csv',index=False)
    summaries=[]
    for (cohort,endpoint,feature),g in rows.groupby(['cohort','endpoint','feature'],sort=False):
        assert len(g)==3
        summaries.append({'cohort':cohort,'endpoint':endpoint,'feature':feature,'folds':3,
          'mean_brier_reduction':float(g.brier_reduction.mean()),'worst_fold_brier_reduction':float(g.brier_reduction.min()),
          'best_fold_brier_reduction':float(g.brier_reduction.max()),'improved_folds':int(g.brier_reduction.gt(0).sum()),
          'mean_auc':float(g.auc.mean()),'mean_auc_increment':float(g.auc_increment.mean()),
          'auc_by_fold':g.auc.tolist(),'brier_reduction_by_fold':g.brier_reduction.tolist(),
          'scored_rows':int(g.test_rows.sum()),'scored_sessions_sum_across_disjoint_folds':int(g.test_sessions.sum())})
    native=Counter((kind,int(pos==0),int(te>=0)) for kind,pos,te in d[['kind','pos','te']].itertuples(index=False,name=None))
    for x in ledger:assert x['inside_anchor_rows']==sum(n for (kind,inside,ex),n in native.items() if kind==x['kind'] and inside)
    evidence={'scope':'EXPLORATORY_PROXY_PREDICTION_NOT_PROFITABILITY','plan':json.load(open(A/'analysis-plan.json')),
      'profile':json.load(open(A/'native-profile.json')),'ledger':ledger,'folds':foldinfo,'summaries':summaries,
      'independent_brier_and_bounded_auc_oracles_passed':True,'forward_global_date_separation_verified':True,
      'new_price_outcomes_created':False,'pnl_or_entry_fills_measured':False,'fresh_blind_validation':False,
      'zone_causality_proven':False,'controls_zone_free_certified':False,'operational_filter_selected':False}
    (A/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False))
    (A/'training-models.json').write_text(json.dumps(models,indent=2,allow_nan=False))
    print('Temporal blocks',foldinfo)
    print('Real indicators: Brier improvement and AUC; positive improvement means lower predictive error, not profits.')
    for e in LABELS:
      print(e)
      for x in sorted([s for s in summaries if s['cohort']=='real' and s['endpoint']==e and s['feature']!='cell_baseline'],key=lambda x:-x['mean_brier_reduction']):
        print(x['feature'],round(x['mean_brier_reduction']*1000,4),'Brier x1e-3;',round(x['mean_auc'],4),'AUC;',x['improved_folds'],'/3 positive; folds',[round(v*1000,4) for v in x['brier_reduction_by_fold']])
    print('Ledger:',ledger)
def export_summary_artifacts(folder):
    """Render recorded evidence, not a second fit or a threshold optimizer."""
    e=json.loads((folder/'evidence.json').read_text())
    b=pd.read_csv(folder/'test-bucket-metrics.csv');c=pd.read_csv(folder/'contract-fold-metrics.csv');r=pd.read_csv(folder/'fold-metrics.csv')
    feature='delay_x_range_band'
    chosen=b[(b.feature==feature)&(b.endpoint=='continuation')&b.bucket.isin(['0:2','2:0'])]
    assert len(chosen)==12
    for cohort in ['real','pseudo']:
        for fold in [1,2,3]:
            z=chosen[(chosen.cohort==cohort)&(chosen.fold==fold)].set_index('bucket')
            assert z.loc['0:2','weighted_label_rate']>z.loc['2:0','weighted_label_rate']
    real=[x for x in e['summaries'] if x['cohort']=='real' and x['endpoint']=='continuation' and x['feature']!='cell_baseline']
    best=max(real,key=lambda x:x['mean_brier_reduction']);assert best['feature']==feature and best['improved_folds']==3
    after=[x for x in e['summaries'] if x['cohort']=='real' and x['endpoint']=='post_retest_exit_side' and x['feature']!='cell_baseline']
    assert len(real)==26 and len(after)==26 and all(x['mean_brier_reduction']<0 for x in after)
    pairs=c[(c.cohort=='real')&(c.endpoint=='continuation')&c.feature.isin([feature,'range_over_band'])]
    g=pairs.groupby(['contract','feature']).brier_reduction.mean();contracts=sorted(pairs.contract.unique())
    assert len(contracts)==4 and g.loc[('MNQ_12-26','range_over_band')]<0
    plan=[{'question':'Does exit context distinguish continuation, and is the pattern zone-specific?','grain':'forward block x cohort x training-defined mechanism bucket','population':'O2 resolved inside-anchor observed exits','unit':'weighted geometric O2 rate percent','finding':'Fast/high-range bucket exceeds slow/low-range bucket in all3blocks in BOTH cohorts','derivation':'bucket weighted positive mass / same bucket eligible weight','disposition':'chart','reason':'Keep all3 blocks and both cohorts visible, not a single attractive pooled contrast; two illustrated corners selected after exploration, all9 buckets retained in CSV'},
          {'question':'Does normalization transfer across contracts?','grain':'contract x feature','population':'O2 real resolved eligible forward tests; only4contracts appear in test dates','unit':'mean Brier reduction x1000 over supported folds','finding':'Normalized range alone reverses in MNQ_12-26; joint delay/range positive but small there','derivation':'mean within-contract cell-baseline error minus feature error','disposition':'chart','reason':'Aggregate improvement hides a consequential negative subgroup; retain low support 10sessions'},
          {'question':'Which tested mechanisms add the most predictive information?','grain':'feature x endpoint x cohort','population':'each endpoint own resolved subset','unit':'Brier reduction, AUC, positive folds','finding':'26 tests retained; best descriptive O2 joint delay/range, all26 negative mean O3b error improvements','disposition':'table','reason':'Complete tested list and failures retained, no taller ranking of26groups'},
          {'question':'How far did price move?','grain':'test block x selected bucket','population':'same O2 test rows','unit':'observed max excursion in h and ticks','finding':'Existing future excursion label available, not an entry covariate or complete path timing','disposition':'table','reason':'Do not fabricate peak time, return speed or full path'},
          {'question':'Which return/peak structure predicts entries?','grain':'causally observable path at decision','population':'not present in existing export','unit':'unavailable','finding':'Return timestamps/OHLC/confirmed pivots absent','disposition':'prose','reason':'Research hypotheses and observable timing specified, no made-up peak result'}]
    e['comparison_plan']=plan;e['illustrated_extremes_selected_after_exploration']=True
    e['bucket_rates_have_changing_training_only_thresholds']=True
    e['return_peak_paths_measured']=False
    e['illustrated_bucket_support']=chosen.to_dict(orient='records')
    e['contract_support']=pairs.groupby(['contract','feature']).agg(folds=('fold','nunique'),sessions=('sessions','sum'),rows=('rows','sum'),mean_brier_reduction=('brier_reduction','mean')).reset_index().to_dict(orient='records')
    series=[];colors={}
    for cohort,bucket,label,hue in [('real','0:2','Rápida/amplia · real','blue'),('real','2:0','Lenta/estrecha · real','purple'),('pseudo','0:2','Rápida/amplia · control','teal'),('pseudo','2:0','Lenta/estrecha · control','orange')]:
        q=chosen[(chosen.cohort==cohort)&(chosen.bucket==bucket)].sort_values('fold')
        series.append({'label':label,'valueKind':'percent','role':'subject' if not series else 'base','derived':True,'derivationReason':'weighted O2 positive mass / eligible bucket mass x100','data':(q.weighted_label_rate*100).tolist()});colors[label]=hue
    panel1={'version':1,'form':'categorical-bars','mode':'grouped','title':'Salida rápida + rango amplio: más continuación','aside':'O2, no ganancias; extremos ilustrativos, cortes variables del pasado','labels':['Ene–abr','Abr–jun','Jun–sep'],'tooltipLabels':[str(x['test_first'])+'–'+str(x['test_last']) for x in e['folds']],'axis':{'zero':True},'series':series}
    series2=[]
    for f,label,hue in [(feature,'Demora × rango/ancho','green'),('range_over_band','Rango/ancho','pink')]:
        series2.append({'label':label,'valueKind':'number','role':'subject' if not series2 else 'base','derived':True,'derivationReason':'mean baseline Brier minus feature Brier over supported folds, x1000','data':[float(g.loc[(ct,f)])*1000 for ct in contracts]});colors[label]=hue
    panel2={'version':1,'form':'categorical-bars','mode':'grouped','title':'Rango/ancho falla solo en MNQ_12-26','aside':'ΔBrier ×1.000; positivo mejora; MNQ_12-26 sólo 10 sesiones','labels':[ct.replace('MNQ_','') for ct in contracts],'tooltipLabels':contracts,'axis':{'zero':True},'series':series2}
    spec={'version':1,'form':'paired-panels','title':'El contexto de salida ayuda; no prueba rentabilidad','aside':'Exploración interna, 26 pruebas y 3 bloques temporales','panels':[panel1,panel2],'colorMap':colors}
    (folder/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2,allow_nan=False))
    (folder/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2,allow_nan=False))
    pd.DataFrame(e['summaries']).to_csv(folder/'summary-metrics.csv',index=False)
    lines=['# AVZVOL: indicadores, forma de salida y prioridad de entradas','','## Resultado para decidir','La primera prioridad es investigar **continuación después de una salida rápida, cuando el rango previo es grande respecto del ancho de la banda**. Es la combinación con mayor reducción media de error Brier entre las 26 pruebas de esta exploración. **No demuestra rentabilidad ni una ventaja propia de las zonas:** el patrón también aparece en pseudo-controles legacy, que todavía no están certificados como zone-free.','',f"AUC media de la combinación: {best['mean_auc']:.4f}, frente a {next(x for x in e['summaries'] if x['cohort']=='real' and x['endpoint']=='continuation' and x['feature']=='cell_baseline')['mean_auc']:.4f} de la base por celda. AUC NO es tasa de aciertos ni de operaciones ganadoras. Mejora media Brier: {best['mean_brier_reduction']:.7f}; positiva en los tres bloques, pero modesta en magnitud absoluta.",'','**Después del retest:** ninguna de las 26 pruebas mejora en promedio el error Brier para O3b en reales. No implica que toda estrategia de retest sea imposible: estas variables son viejas, tomadas en t0, y no describen la estructura del regreso.','','## Qué significa salida rápida y rango amplio','- Demora: `te-t0`, número de barras de 25 trades hasta la salida observada. No segundos.','- Rango previo: `amp`, máximo high menos mínimo low de las 200 barras terminadas en t0. No desplazamiento de la salida.','- Rango/ancho: `amp/h`, con `h=H-L+1`. Es contexto de escala y facilidad del objetivo geométrico; NO demuestra impulso direccional propio de la zona.','- La esquina ilustrativa rápida/amplia usa el tercil inferior de demora y superior de rango/ancho. La esquina lenta/estrecha, lo opuesto. Cortes aprendidos sólo del pasado, distintos por bloque y cohorte. Se ilustran tras inspeccionar; no son reglas operativas congeladas.','- Covariables antiguas en t0; dirección `dir` sólo observable tras la salida, nunca como señal en t0.','- El primer tercil de demora de reales resulta menor que 5 barras en los tres entrenamientos. El corte superior de rango/ancho cambia; no adoptar un número optimizado.','','## Continuación por contexto y soporte','O2 significa llegar una altura h más allá del borde de salida antes del primer cierre dentro, excluyendo la barra de salida, hasta 2.000 barras posteriores de la misma sesión. No hay entrada, stop, fill ni costos medidos. Las tasas usan las ponderaciones del bloque original restringidas al grupo, no una nueva reponderación igualando sólo las sesiones del subgrupo.','','| Bloque | Grupo | O2 real | Filas / anclas / sesiones | O2 control |','|---|---|---:|---|---:|']
    for fold in [1,2,3]:
        for bucket,label in [('0:2','Rápida/amplia'),('2:0','Lenta/estrecha')]:
            x=chosen[(chosen.fold==fold)&(chosen.cohort=='real')&(chosen.bucket==bucket)].iloc[0];z=chosen[(chosen.fold==fold)&(chosen.cohort=='pseudo')&(chosen.bucket==bucket)].iloc[0]
            lines.append(f"| {fold} | {label} | {x.weighted_label_rate*100:.2f}% | {int(x.rows)} / {int(x.anchor_keys)} / {int(x.sessions)} | {z.weighted_label_rate*100:.2f}% |")
    lines+=['','Las filas son evento×celda, no observaciones independientes. Las anclas pueden aparecer en varias celdas; las sesiones no son replicaciones independientes entre contratos del mismo mercado. CSV completo conserva los nueve grupos, cortes, masas y soporte.','','## Distancia ya disponible, no señal de entrada','`mx_h` registra la máxima excursión observada del lado de salida desde el borde, dividida por h, hasta el primer cierre dentro o el final de la ventana/sesión. Excluye la barra de salida e incluye high/low de la barra que vuelve a cerrar dentro. Si la ventana termina antes de la vuelta, la distancia sigue siendo un máximo observado acotado, no la excursión completa futura. No usarla para filtrar una entrada antes de observarla.','','| Bloque | Grupo real | Mediana máxima observada (h) | P90 (h) | Mediana (ticks) |','|---|---|---:|---:|---:|']
    for _,x in chosen[chosen.cohort=='real'].sort_values(['fold','bucket']).iterrows():
        lines.append(f"| {int(x.fold)} | {'Rápida/amplia' if x.bucket=='0:2' else 'Lenta/estrecha'} | {x.observed_excursion_h_p50:.3f} | {x.observed_excursion_h_p90:.3f} | {x.observed_excursion_ticks_p50:.2f} |")
    lines+=['','`(te-t0)/h` mide demora previa normalizada por ancho declarado, no velas por distancia efectivamente recorrida. Faltan índice/tiempo del máximo, precio al salir y trayectoria de regreso: no hay medición válida de velocidad de vuelta ni de picos en estos exports.','','## Todas las pruebas: conservar también los fracasos','ΔBrier se muestra ×1.000. Positivo = menor error que la base histórica por celda. Promedio de tres bloques, NO significancia estadística ni beneficio esperado. El control de ruido cuenta entre las 26 pruebas.','','| Indicador / mecanismo | ΔBrier O2 ×1.000 | AUC O2 | Bloques mejora O2 | ΔBrier O3b ×1.000 |','|---|---:|---:|---:|---:|']
    for x in sorted(real,key=lambda v:-v['mean_brier_reduction']):
        z=next(y for y in after if y['feature']==x['feature']);lines.append(f"| `{x['feature']}` | {x['mean_brier_reduction']*1000:+.4f} | {x['mean_auc']:.4f} | {x['improved_folds']}/3 | {z['mean_brier_reduction']*1000:+.4f} |")
    lines+=['','## Transferencia por contrato','Los dos contratos más antiguos sólo aparecen en entrenamiento con este corte global; no se presentan como seis confirmaciones. En prueba hay cuatro contratos. Rango/ancho por sí solo se invierte en MNQ_12-26; la combinación mejora allí muy poco y tiene sólo diez sesiones.','','| Contrato | Sesiones / bloques | ΔBrier combinación ×1.000 | ΔBrier rango/ancho ×1.000 |','|---|---|---:|---:|']
    for ct in contracts:
        z=pairs[(pairs.contract==ct)&(pairs.feature==feature)];lines.append(f"| {ct} | {int(z.sessions.sum())} / {z.fold.nunique()} | {g.loc[(ct,feature)]*1000:+.4f} | {g.loc[(ct,'range_over_band')]*1000:+.4f} |")
    lines+=['','## Qué lógica de entrada conviene investigar','1. **Continuación temprana:** salida observada, demora corta y rango previo amplio relativo al objetivo; medir entrada ejecutable posterior a la señal, stop, costos, recorrido adverso/favorable y vencimiento. No entrar retrospectivamente al borde ni asumir fill en la barra ya terminada.','2. **Retest con estructura nueva:** no reutilizar estos filtros como dirección del rebote. Actualizar contexto al retest; estudiar rechazo fuera, recuperación dentro y pivotes confirmados como mecanismos separados.','3. **Evitar como filtro central por ahora:** tendencia larga alineada y volumen aislado; fueron peores que la base en O2, y no rescataron O3b. No significa que toda variante de ellos sea inútil.','4. **No optimizar para conseguir un ganador:** las familias y combinaciones se ampliaron después de mirar resultados, a pedido del usuario. Congelar pocos candidatos y confirmar en datos realmente no vistos antes de promover una estrategia.','','## Salida, vuelta y picos: pruebas de mecanismo pendientes','Estas son hipótesis, NO resultados medidos en la vuelta:','- Salida: desplazamiento del cierre desde el borde, excursión antes del retest, barras y tiempo por distancia real, eficiencia de trayectoria (desplazamiento / suma de cambios absolutos), cuerpo/mechas, cierres fuera y solapamiento.','- Vuelta: fracción devuelta de la excursión observada hasta ese momento; velocidad de vuelta relativa a la salida; compresión de rango, solapamiento, profundidad y número de cruces. Un regreso lento/comprimido y uno rápido/agresivo deben contrastarse, no suponerse equivalentes.','- Picos: picos aislados frente a cadenas de dos o más; máximos decrecientes/mínimos crecientes; tolerancia al nivel, separación en barras/segundos, pullback intermedio y ruptura del último pico.','- Confirmación: comparar cierre de la propia barra de retest cuando ya es observable, confirmación posterior y recuperación del interior. Nunca inferir orden de high/low intrabar sin datos suficientes.','- Distancia y stops: buscar si la estructura reduce excursión adversa y deja recorrido favorable suficiente tras el precio ejecutable; la probabilidad geométrica O2 sola no responde esa pregunta.','','Fuentes del repo:','- [liqpool.find_pivots](../../edgelab/bridge/indicators/liqpool.py): pivote en i disponible sólo al cierre de i+R; no anticiparlo en i ni sustituir toda la trayectoria por el cluster final.','- [peaks_rule histórico](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/tools/peaks_rule.py): `chains` confirma q=j-w; `series` devuelve segmentos finales y pertenencia retrospectiva. `backfill` extiende un segmento visual hacia atrás: esa fecha no es el nacimiento conocido de la señal.','- [Diseño de etiquetado de picos](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/docs/research/ETIQUETADO_PICOS_Y_ML_20260926.md): reconocer un patrón humano no prueba entradas rentables.','- `liqheat` detecta picos de densidad sobre el eje de precio, no los swings temporales de la vuelta. No intercambiarlos.','','## Método y reproducción','Seis Parquets pinned, 544.531 filas totales; todas las celdas. Comparación real/pseudo separada, sin suponer controles certificados. Igual peso global por sesión, contrato dentro de sesión, ancla t0 dentro de contrato/sesión y filas dentro de ancla; duplicados retenidos compartiendo peso.','Entrenamiento sólo en fechas globales anteriores; una sesión de embargo; primer 40% para iniciar entrenamiento y tres bloques con el restante 60%. Sesiones de prueba disjuntas. Cada desenlace se evalúa sólo donde su etiqueta está resuelta; ausencias y dobles hits quedan en el ledger. Todos los contratos del mismo mercado comparten fechas: no tratarlos como réplicas independientes.','Historia ya inspeccionada: validación temporal INTERNA, no OOS ciego. Modelos univariados por quintiles o pares por terciles, sin búsqueda de hiperparámetros, reglas económicas ni optimización de cutoff. Actividad exportada ya está log-transformada; las transformaciones monotónicas adicionales de los univariados sólo ordenan grupos. Intensidad usa diferencia de logs originales de volumen/tiempo.','Los checks independientes de Brier (math.fsum) y AUC (pares en muestra acotada) se ejecutan dentro del cálculo. Hashes exactos y footers preholdout verificados antes de abrir el payload. El profiler genérico no soportó estos Parquets: validación nativa más proyecciones CSV verificadas, no una declaración de corrupción.','No se certifica calidad de fuente, censo causal ni snapshots as-of; no se despejan gates. No se mide P&L, fills, spread/slippage ni órdenes.','','```bash','python tools/review_avzvol_indicator_screen.py --input-dir /ruta/privada/a/los/seis/exports --out /ruta/de/salida','```','','Dependencias de investigación: numpy, pandas, pyarrow. El script sólo abre los seis nombres/hashes de export fijados en el plan; no carga ticks ni la reserva ciega.','','[Plan y pins](avzvol_indicator_screen_20261011/analysis-plan.json) · [Evidencia](avzvol_indicator_screen_20261011/evidence.json) · [Resumen completo](avzvol_indicator_screen_20261011/summary-metrics.csv) · [Bloques](avzvol_indicator_screen_20261011/fold-metrics.csv) · [Contratos](avzvol_indicator_screen_20261011/contract-fold-metrics.csv) · [Todos los grupos y distancias](avzvol_indicator_screen_20261011/test-bucket-metrics.csv)']
    (folder/'report.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
    export_summary_artifacts(A)
