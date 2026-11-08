"""ORB NQ exploratorio: E0 primero, después medición. Sin holdout ni export de ticks.
Solo ejecutable dentro de Kaggle privado, una versión; reglas en el manifiesto.
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import t as student
from edgelab.data.liquid_release import release_reader as RR
from senales_orb import disparos
from conciliar_calendario import conciliar

D0,D1=20250805,20260331
H='db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5'
CAL=Path('docs/research/cme_equity_index_calendar_20260902/cme_equity_index_session_calendar_v1.json')
NEWS=Path('config/noticias/calendario_usd_tier1.csv')
CAL_SHA='9d8c318f84046844987dce247d6b67c2198771d6c00325157ea52605bfd92d86'
NEWS_SHA='8a152d092314c42498638cbee2144cef0851b013a8536ed0b661c3fdb8381234'
ET='America/New_York'; MIN=60_000_000_000
B=10000; SEED=20261108; ALPHA=.05; NMIN=30
Q_FDR=.10; M_HEREDADO=705     # 2026-11-08: nominación por FDR q 0,10 (criterio del embudo); linaje ORB_HORARIOS (704) + ORB0100 (1)


def midnight(d):
    return pd.Timestamp(str(d)).tz_localize(ET).value


def prep(df):
    df=df.loc[~df.outside_regular].reset_index(drop=True)
    if df.empty or df.trade_date.nunique()!=1 or df.regime_id.nunique()!=1: return None
    if np.any(np.diff(df.ts_utc_ns.to_numpy(np.int64))<0): raise ValueError('ticks desordenados')
    if (df[['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','regime_id']].isna().any().any()
        or (df.price_ticks<=0).any() or (df.bid_ticks<=0).any() or (df.ask_ticks<df.bid_ticks).any()):
        raise ValueError('ticks/cotizaciones inválidos')
    df['t']=(df.ts_utc_ns//MIN+1)*60
    m=df.groupby('t',sort=True).agg(h=('price_ticks','max'),l=('price_ticks','min'),c=('price_ticks','last'),ses=('trade_date','first'),seg=('regime_id','first')).reset_index()
    day=int(df.trade_date.iloc[0]); base=midnight(day)
    # Calidad retrospectiva declarada: 385 barras de RTH completas, sin inferir actividad ausente.
    expected=(base//1_000_000_000+np.arange(571,956)*60)
    present=np.isin(expected,m.t.to_numpy(np.int64)).all()
    end=base+955*MIN; endlim=base+960*MIN
    has_close=((df.ts_utc_ns>=end)&(df.ts_utc_ns<endlim)).any()
    if not present or not has_close: return None
    ctx={k:m[k].to_numpy(np.int64) for k in ('t','ses','seg')}
    ctx.update({k:m[k].to_numpy(float)*.25 for k in ('h','l','c')})
    s=disparos(ctx)
    if len(s): s['signal_ns']=m.t.to_numpy(np.int64)[s.k.to_numpy(np.int64)]*1_000_000_000
    return df,s


def blocked(signal,close,events):
    # Conocido en la señal en el modelo; el calendario histórico es retrospectivo parcial.
    return bool(np.any((events-MIN<=close)&(events+MIN>=signal)))


def fill(t,last,bid,ask,signal,close,limit,side,stop,slip,events=()):
    """Last dispara stop; ejecución en bid/ask del tick más slippage por pata."""
    i=int(np.searchsorted(t,signal,side='right'))
    if i>=len(t) or t[i]>=close:return None
    entry=(ask[i] if side==1 else bid[i])*.25+side*slip*.25
    risk=side*(entry-stop)
    if risk<=0:return None
    end=int(np.searchsorted(t,limit,side='left'))
    tt=t[i+1:end]; lp=last[i+1:end]*.25
    hits=np.flatnonzero((tt>=close)|(side*(lp-stop)<=0))
    if not len(hits): raise ValueError('posición sin salida durante sesión')
    j=i+1+int(hits[0])
    if t[j]>=close and blocked(close,int(t[j]),np.asarray(events,dtype=np.int64)):
        raise ValueError('salida retrasada cruza noticia listada')
    exit_=(bid[j] if side==1 else ask[j])*.25-side*slip*.25
    return (side*(exit_-entry)-5.76/20.0)/risk


def summarize(rows, start):
    d=rows[rows.ses>=start].reset_index(drop=True)
    keys=[]; masks=[]
    for dur in (5,15,30):
        for day in range(6):
            for hour in range(5):
                for atr in range(4):
                    mask=(d.duracion==dur)&((d.dia==day) if day<5 else True)&((d.hora==hour) if hour<4 else True)&((d.atr_bin==atr) if atr<3 else True)
                    keys.append([dur,day,hour,atr]); masks.append(mask.to_numpy(bool))
    X=np.array(masks).T if len(d) else np.zeros((0,360),bool)
    ses,inv=np.unique(d.ses.to_numpy(),return_inverse=True)
    v=d.r_base.to_numpy(float); alt=d.r_adv.to_numpy(float)
    count=X.sum(0); summ=X.T@v; sq=X.T@(v*v)
    with np.errstate(invalid='ignore',divide='ignore'):
        mu=summ/count; var=(sq-count*mu**2)/(count-1); se=np.sqrt(var/count); t=mu/se
    ev=(count>=NMIN)&np.isfinite(t)&(se>0)
    # maxT una etapa (más conservador que step-down), signos compartidos por sesión.
    ES=np.zeros((len(ses),360))
    for i in range(len(v)): ES[inv[i]]+=X[i]*v[i]
    denom=np.sqrt((ES*ES).sum(0)); eligible=ev & (denom>0)
    T=np.full(360,np.nan); p=np.ones(360)
    if eligible.any():
        T[eligible]=ES[:,eligible].sum(0)/denom[eligible]
        W=np.random.default_rng(SEED).choice((-1.,1.),size=(B,len(ses)))
        maxima=((W@ES[:,eligible])/denom[eligible]).max(axis=1)
        p[eligible]=(1+(maxima[:,None]>=T[None,eligible]).sum(axis=0))/(B+1)
        Z=(W@ES[:,eligible])/denom[eligible]                                # p marginal por celda, mismos signos
        pm=np.ones(360); pm[eligible]=(1+(Z>=T[None,eligible]).sum(axis=0))/(B+1)
    else: pm=np.ones(360)
    m_fdr=int(eligible.sum())+M_HEREDADO; orden=np.argsort(pm); nom_fdr=np.zeros(360,bool)
    pasa=[j for r,j in enumerate(orden,1) if eligible[j] and pm[j]<=Q_FDR*r/m_fdr]
    if pasa: nom_fdr[orden[:list(orden).index(pasa[-1])+1]]=True; nom_fdr&=eligible
    result=[]
    for i,k in enumerate(keys):
        if count[i]==0: continue
        n=int(count[i]); ci=None
        if n>1 and np.isfinite(se[i]):
            a=float(student.ppf(.975,n-1)*se[i]); ci=[float(mu[i]-a),float(mu[i]+a)]
        result.append({'duracion':k[0],'dia':k[1],'hora':k[2],'atr':k[3], 'n':n,
            'media_r_base':float(mu[i]),'ic95_t_no_ajustado':ci,'media_r_adverso':float(alt[X[:,i]].mean()),
            't_operacion':float(t[i]) if np.isfinite(t[i]) else None,'evaluable':bool(eligible[i]),
            'p_maxt':float(p[i]) if eligible[i] else None,'nomina':bool(eligible[i] and p[i]<=ALPHA),
            'p_marginal':float(pm[i]) if eligible[i] else None,'nomina_fdr':bool(nom_fdr[i])})
    return {'desde':start,'hasta':D1,'sesiones_operaciones':len(ses),'operaciones':len(d),'celdas_nominales':360,
            'celdas_con_operaciones':len(result),'evaluables':int(eligible.sum()),'nominadas':int(sum(x['nomina'] for x in result)),
            'nominadas_fdr':int(nom_fdr.sum()),'m_fdr':m_fdr,'q_fdr':Q_FDR,
            'metodo':'maxT una etapa, signos por sesión; simetría no comprobada; alfa por canal, no global entre canales',
            'B':B,'semilla':SEED,'min_n':NMIN,'celdas':result}


def run(root, output_dir=Path("/kaggle/working")):
    output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    if RR.sha256_file(root/'release_manifest.json')!=H or RR.sha256_file(CAL)!=CAL_SHA or RR.sha256_file(NEWS)!=NEWS_SHA:
        raise RR.ReleaseStop('SHA distinto')
    files=RR.load_manifest(root,verify_hash=True,purpose='research')
    cal=json.loads(CAL.read_text())['sessions']; classes={int(x['trade_date']):x['session_class'] for x in cal}
    meta=pd.read_parquet(root/'metadata/session_index.parquet',filters=[('instrument','==','NQ'),('trade_date','>=',D0),('trade_date','<=',D1)])
    records=json.loads(meta[['trade_date','prev_trade_date','status']].to_json(orient='records'))
    rec=conciliar(cal,records,D0,D1); allowed={x['trade_date'] for x in rec['filas'] if x['clase_cme']=='NORMAL' and x['revision']=='ANTERIOR_COINCIDE'}
    news=pd.read_csv(NEWS); events=pd.to_datetime(news.ts_utc,utc=True).dt.as_unit('ns').astype('int64').to_numpy()
    pf=pq.ParquetFile(files['NQ'].path); groups=RR.select_row_groups(pf,D0,D1); ix=pf.schema_arrow.names.index('trade_date'); bydate={}
    for g in groups:
        st=pf.metadata.row_group(g).column(ix).statistics; lo,hi=int(st.min),int(st.max)
        if lo!=hi: raise RR.ReleaseStop('row group mezcla sesiones')
        bydate.setdefault(lo,[]).append(g)
    counts={'sesiones_footer':len(bydate),'no_normal_o_d1':0,'calidad_rth':0,'sesiones_calidad':0,'senales':0,'vetos_noticias':0,'sin_atr':0,'fill_invalido':0}
    # Primera pasada sólo señales/ATR: no ejecutar fill ni evaluar resultados.
    selected=[]
    cols=['ts_utc_ns','price_ticks','bid_ticks','ask_ticks','trade_date','regime_id','outside_regular']
    for day,gs in sorted(bydate.items()):
        if day not in allowed: counts['no_normal_o_d1']+=1; continue
        raw=pf.read_row_groups(gs,columns=cols).to_pandas()
        if (raw.trade_date!=day).any() or (raw.ts_utc_ns>=RR.HOLDOUT_FIRST_TS_NS).any(): raise RR.ReleaseStop('fecha o timestamp no permitido')
        prepared=prep(raw)
        if prepared is None: counts['calidad_rth']+=1; continue
        ticks,signals=prepared; counts['sesiones_calidad']+=1
        end=midnight(day)+955*MIN
        for s in signals.itertuples():
            counts['senales']+=1
            if blocked(s.signal_ns,end,events): counts['vetos_noticias']+=1;continue
            if not np.isfinite(s.atr14):counts['sin_atr']+=1
            selected.append({'ses':day,'duracion':s.duracion,'dia':s.dia,'hora':s.hora,'atr14':s.atr14,'signal_ns':int(s.signal_ns),'lado':s.lado,'stop':s.lo if s.lado==1 else s.hi})
        del raw,ticks,signals
    e=pd.DataFrame(selected)
    if e.empty: raise ValueError('sin señales elegibles')
    valid=e.loc[np.isfinite(e.atr14),'atr14']; cuts=np.quantile(valid,[1/3,2/3])
    if len(valid)<2 or not cuts[0]<cuts[1]:raise ValueError('ATR sin cortes válidos')
    # Cortes congelados antes de calcular un solo fill o retorno. Salida target-free persistida.
    e0={'estado':'E0_CONGELADO_EXPLORATORIO','conteos':counts.copy(),'atr_finitos':len(valid),'atr_cortes':cuts.tolist(),'manifest_sha256':H,
        'advertencia':'calendario noticias retrospectivo incompleto; calidad por sesión retrospectiva; v4 política con calibración inicial in-sample'}
    (output_dir/'ORB_NQ_E0_CONGELADO.json').write_text(json.dumps(e0,ensure_ascii=False,indent=2))
    e['atr_bin']=np.where(np.isfinite(e.atr14),np.searchsorted(cuts,e.atr14,side='right'),-1)
    rows=[]
    for day,chunk in e.groupby('ses',sort=True):
        raw=pf.read_row_groups(bydate[int(day)],columns=cols).to_pandas(); prepared=prep(raw)
        if prepared is None: raise ValueError('población cambió entre pasadas')
        ticks,_=prepared
        t=ticks.ts_utc_ns.to_numpy(np.int64); last=ticks.price_ticks.to_numpy(float); bid=ticks.bid_ticks.to_numpy(float); ask=ticks.ask_ticks.to_numpy(float)
        end=midnight(day)+955*MIN; limit=midnight(day)+960*MIN
        for s in chunk.itertuples():
            a=fill(t,last,bid,ask,s.signal_ns,end,limit,int(s.lado),s.stop,1,events)
            z=fill(t,last,bid,ask,s.signal_ns,end,limit,int(s.lado),s.stop,2,events)
            if a is None or z is None:
                if (a is None)!=(z is None): raise ValueError('escenarios difieren en elegibilidad')
                counts['fill_invalido']+=1;continue
            rows.append({'ses':int(day),'duracion':s.duracion,'dia':s.dia,'hora':s.hora,'lado':int(s.lado),'atr_bin':s.atr_bin,'r_base':a,'r_adv':z})
    results=pd.DataFrame(rows)
    if results.empty: raise ValueError('sin operaciones')
    out={'estado':'EXPLORATORIO_NO_VALIDADO','manifest_sha256':H,'nq_sha256':files['NQ'].sha256,'cal_sha256':CAL_SHA,'news_sha256':NEWS_SHA,'conteos':counts,'atr_cortes':cuts.tolist(),
         'direcciones':{'largos':int((results.lado==1).sum()),'cortos':int((results.lado==-1).sum())},
         'metodo':'fills bid/ask con slippage 1/2 ticks por pata; comisión 5.76 USD/viaje; stop por last; riesgo desde fill; cierre primer tick >=15:55 ET',
         'limitaciones':['Noticias USD sólo eventos listados y calendario retrospectivo; no acredita ausencia de todos los eventos rojos.', 'Sesiones con barras completas seleccionadas retrospectivamente; release incluye política calibrada in-sample inicialmente.', 'Sin réplica independiente ni promoción; no es recomendación operativa.', 'Celdas e intervalos seleccionados tienen sesgo de selección; dos canales separados.'],
         'total':summarize(results,D0),'reciente':summarize(results,20260101)}
    (output_dir/'ORB_NQ_RESULTADOS_EXPLORATORIOS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
    print('MEDICION_EXPLORATORIA_COMPLETA; salida agregada privada; no se exportan ticks ni operaciones individuales.',flush=True)

if __name__=='__main__':run(Path(os.environ['RELEASE_DIR']))
