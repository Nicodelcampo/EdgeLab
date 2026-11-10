"""Investigación USATECH privada, sólo pre-holdout. Contrato y límites en manifiesto."""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from senales_orb import disparos
from medir_exploratorio import summarize, blocked

D0,D1=20230103,20260331
TICK_SHA='7037b34d431d1fe61d2a866a8305688d21c646bbb017b38559aef8d0dd332011'
NEWS_SHA='8a152d092314c42498638cbee2144cef0851b013a8536ed0b661c3fdb8381234'
HOLDOUT_NS=1790805600000000000
MIN=60_000_000_000


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def schedule(path):
    x=json.loads(Path(path).read_text())['sessions']
    dates=np.array([r['date'] for r in x],dtype=np.int64)
    opens=np.array([r['open_ns'] for r in x],dtype=np.int64)
    closes=np.array([r['close_ns'] for r in x],dtype=np.int64)
    if not len(dates) or np.any(np.diff(dates)<=0) or np.any(np.diff(opens)<=0):raise ValueError('calendario desordenado')
    if dates.min()<D0 or dates.max()>D1 or np.any(closes-opens!=390*MIN):raise ValueError('calendario fuera de alcance')
    return dates,opens,closes


def iter_days(path,cal):
    """Lectura de grupos temporales sin exportar ticks. Sesión = RTH + 30 min de calentamiento ATR."""
    dates, opens, closes=cal
    starts=opens-30*MIN
    pf=pq.ParquetFile(path); ix=pf.schema_arrow.get_field_index('time_utc_ns')
    if ix<0:raise ValueError('sin columna temporal')
    active=None; parts=[]; prev_max=None
    for g in range(pf.num_row_groups):
        st=pf.metadata.row_group(g).column(ix).statistics
        if st is None or not st.has_min_max:raise ValueError('faltan estadísticas temporales del grupo')
        lo,hi=int(st.min),int(st.max)
        if prev_max is not None and lo<prev_max:raise ValueError('grupos temporales solapados o fuera de orden')
        prev_max=hi
        if hi<starts[0] or lo>=closes[-1]:continue
        if hi>=HOLDOUT_NS:raise ValueError('el grupo intersecta holdout: abortar sin leer')
        table=pf.read_row_group(g,columns=['time_utc_ns','bid','ask']).to_pandas()
        t=table.time_utc_ns.to_numpy(np.int64)
        if np.any(np.diff(t)<0) or np.any(t>=HOLDOUT_NS):raise ValueError('ticks desordenados o holdout')
        which=np.searchsorted(starts,t,side='right')-1
        safe=np.clip(which,0,len(dates)-1)
        mask=(which>=0)&(t<closes[safe])
        table=table.loc[mask].copy(); which=which[mask]
        if not len(table):continue
        split=np.r_[0,np.flatnonzero(np.diff(which)!=0)+1,len(which)]
        for a,b in zip(split[:-1],split[1:]):
            idx=int(which[a]); piece=table.iloc[a:b]
            if active is not None and idx!=active:
                yield int(dates[active]),int(opens[active]),int(closes[active]),pd.concat(parts,ignore_index=True)
                parts=[]
            if active is not None and idx<active:raise ValueError('sesiones fuera de orden')
            active=idx;parts.append(piece)
    if active is not None:
        yield int(dates[active]),int(opens[active]),int(closes[active]),pd.concat(parts,ignore_index=True)


def prepare(day, op, cl, raw):
    t=raw.time_utc_ns.to_numpy(np.int64); bid=raw.bid.to_numpy(float); ask=raw.ask.to_numpy(float)
    if not len(t):return None
    if np.any(np.diff(t)<0) or not np.all(np.isfinite(bid)&np.isfinite(ask)&(bid>0)&(ask>=bid)):
        raise ValueError('cotizaciones inválidas o desordenadas')
    mid=np.round(((bid+ask)/2.0)/.01)*.01
    bars=pd.DataFrame({'t':(t//MIN+1)*60,'mid':mid}).groupby('t',sort=True).mid.agg(h='max',l='min',c='last').reset_index()
    expected=(op//1_000_000_000+np.arange(1,386)*60)
    if not np.isin(expected,bars.t.to_numpy(np.int64)).all() or not np.any((t>=cl-5*MIN)&(t<cl)):
        return None
    n=len(bars);ctx={k:bars[k].to_numpy() for k in ('t','h','l','c')}
    ctx['ses']=np.full(n,day,np.int64);ctx['seg']=np.zeros(n,np.int64)
    s=disparos(ctx)
    if len(s):s['signal_ns']=bars.t.to_numpy(np.int64)[s.k.to_numpy(np.int64)]*1_000_000_000
    return t,bid,ask,mid,s


def fill(t,bid,ask,mid,signal,close,limit,side,stop,slip,events):
    i=int(np.searchsorted(t,signal,side='right'))
    if i>=len(t) or t[i]>=close:return None
    entry=(ask[i] if side==1 else bid[i])+side*slip*.25
    risk=side*(entry-stop)
    if risk<=0:return None
    end=int(np.searchsorted(t,limit,side='left'))
    hits=np.flatnonzero((t[i+1:end]>=close)|(side*(mid[i+1:end]-stop)<=0))
    if not len(hits):raise ValueError('sin salida antes del límite')
    j=i+1+int(hits[0])
    if t[j]>=close and blocked(close,int(t[j]),events):raise ValueError('salida tardía cruza noticia listada')
    exit_=(bid[j] if side==1 else ask[j])-side*slip*.25
    return (side*(exit_-entry)-5.76/20.0)/risk


def run(path,cal_path,news_path,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    if sha(path)!=TICK_SHA:raise ValueError('SHA de tick no coincide con versión auditada')
    if sha(news_path)!=NEWS_SHA:raise ValueError('calendario noticias inesperado')
    cal=schedule(cal_path)
    news=pd.read_csv(news_path);events=pd.to_datetime(news.ts_utc,utc=True).dt.as_unit('ns').astype('int64').to_numpy()
    counts={'sesiones_calendario':len(cal[0]),'sesiones_con_ticks':0,'calidad_rth_falla':0,'sesiones_calidad':0,'senales':0,'vetos_noticias':0,'sin_atr':0,'fill_invalido':0}
    sel=[]
    for day,op,cl,raw in iter_days(path,cal):
        counts['sesiones_con_ticks']+=1; prepared=prepare(day,op,cl,raw)
        if prepared is None:counts['calidad_rth_falla']+=1;continue
        t,bid,ask,mid,signals=prepared;counts['sesiones_calidad']+=1
        for s in signals.itertuples():
            counts['senales']+=1
            if blocked(s.signal_ns,cl-5*MIN,events):counts['vetos_noticias']+=1;continue
            if not np.isfinite(s.atr14):counts['sin_atr']+=1
            sel.append({'ses':day,'duracion':s.duracion,'dia':s.dia,'hora':s.hora,'atr14':s.atr14,'signal_ns':int(s.signal_ns),'lado':s.lado,'stop':s.lo if s.lado==1 else s.hi})
    e=pd.DataFrame(sel)
    if e.empty:raise ValueError('sin señales elegibles')
    valid=e.loc[np.isfinite(e.atr14),'atr14'];cuts=np.quantile(valid,[1/3,2/3])
    if len(valid)<2 or not cuts[0]<cuts[1]:raise ValueError('ATR inválido')
    e0={'estado':'E0_EXPLORATORIO','conteos':counts.copy(),'atr_finitos':len(valid),'atr_cortes':cuts.tolist(),'ticks_sha256':TICK_SHA,'calendario_sha256':sha(cal_path),'noticias_sha256':NEWS_SHA}
    (outdir/'ORB_CFD_E0_CONGELADO.json').write_text(json.dumps(e0,indent=2,ensure_ascii=False))
    e['atr_bin']=np.where(np.isfinite(e.atr14),np.searchsorted(cuts,e.atr14,side='right'),-1)
    groups={int(day):chunk for day,chunk in e.groupby('ses',sort=True)};rows=[]
    for day,op,cl,raw in iter_days(path,cal):
        if day not in groups:continue
        p=prepare(day,op,cl,raw)
        if p is None:raise ValueError('población cambió')
        t,bid,ask,mid,_=p
        for s in groups[day].itertuples():
            a=fill(t,bid,ask,mid,s.signal_ns,cl-5*MIN,cl,int(s.lado),s.stop,1,events)
            z=fill(t,bid,ask,mid,s.signal_ns,cl-5*MIN,cl,int(s.lado),s.stop,2,events)
            if a is None or z is None:
                if (a is None)!=(z is None):raise ValueError('elegibilidad difiere entre escenarios')
                counts['fill_invalido']+=1;continue
            rows.append({'ses':int(day),'duracion':int(s.duracion),'dia':int(s.dia),'hora':int(s.hora),'lado':int(s.lado),'atr_bin':int(s.atr_bin),'r_base':a,'r_adv':z})
    data=pd.DataFrame(rows)
    if data.empty:raise ValueError('sin operaciones')
    por_ano=[]
    for (y,d),a in data.groupby([data.ses//10000,'duracion']):
        por_ano.append({'ano':int(y),'duracion':int(d),'n':len(a),'media_r_base':float(a.r_base.mean()),'media_r_adverso':float(a.r_adv.mean())})
    total=summarize(data,D0)
    cells=total['celdas']
    unfiltered=[c for c in cells if (c['dia'],c['hora'],c['atr'])==(5,4,3)]
    best=sorted((c for c in cells if c['evaluable']),key=lambda c:c['p_maxt'])[:5]
    pivot=data.pivot(index='ses',columns='duracion',values='r_base')
    pairs=[]
    for a,b in ((5,15),(5,30),(15,30)):
        if a not in pivot or b not in pivot:continue
        both=pivot[[a,b]].dropna(); union=pivot[[a,b]].fillna(0.0)
        def corr(x):
            r=x.corr().iloc[0,1]
            return float(r) if np.isfinite(r) else None
        pairs.append({'duraciones':[a,b],'rho_sesiones_union_cero':corr(union),
                      'n_sesiones_union_global':len(union),'rho_ambas_activas':corr(both),'n_ambas_activas':len(both)})
    lectura={'sin_filtros':unfiltered,'mejores_p_maxt_descriptivos':best,'correlaciones_por_sesion':pairs}
    result={'estado':'EXPLORATORIO_NO_VALIDADO','instrumento':'DK:USATECHIDXUSD CFD (NO CME NQ)',
        'ventana':'2023-01-03 a 2026-03-31','ticks_sha256':TICK_SHA,'calendario_sha256':sha(cal_path),'noticias_sha256':NEWS_SHA,
        'conteos':counts,'atr_cortes':cuts.tolist(),
        'costos':'bid/ask CFD contemporáneo más supuesto equivalente NQ: 0.25 o 0.50 puntos por pata y 0.288 puntos RT; NO costos reales de un broker CFD',
        'limites':['no corresponde mezclar datos CFD y futuro','filtro de noticias incompleto y retrospectivo','sesiones con cobertura retrospectiva','calendario NYSE no certifica horarios Dukascopy','sin revisión independiente integral','historia y selección no son réplica independiente'],
        'resumen_lectura':lectura,'por_ano_descriptivo':por_ano,'total':total}
    (outdir/'ORB_CFD_RESULTADOS_EXPLORATORIOS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    print('ORB_CFD_COMPLETO: salida agregada privada, sin ticks ni operaciones individuales',flush=True)

if __name__=='__main__':
    run(Path(os.environ['CFD_TICKS']),Path('sesiones_xnys.json'),Path('config/noticias/calendario_usd_tier1.csv'),Path('/kaggle/working'))
