import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import medir_exploratorio as m

def test_fill_bidask_slippage_and_riesgo():
    ts=np.array([10,11,12,20]); last=np.array([400,404,392,400]); bid=np.array([399,403,391,399]); ask=np.array([401,405,393,401])
    # buy at 101.5 (ask 101.25 + .25), exit stop at 97.5 (bid 97.75 - .25)
    assert m.fill(ts,last,bid,ask,10,20,30,1,99,1)==pytest.approx((-4-.288)/2.5)
    # short, gap through 101: entry 100.5 and exit 101.5; risk 1.5
    assert m.fill(ts,np.array([400,404,408,400]),bid,np.array([401,405,405,401]),10,20,30,-1,102,1)==pytest.approx((-1-.288)/1.5)

def test_news_closed_interval_and_no_future_outcome_selection():
    assert m.blocked(10*m.MIN,20*m.MIN,np.array([21*m.MIN]))
    assert not m.blocked(10*m.MIN,20*m.MIN,np.array([22*m.MIN]))

def test_sin_atr_included_in_any_only_and_count_grid():
    rows=pd.DataFrame([dict(ses=20260102,duracion=5,dia=4,hora=0,atr_bin=-1,r_base=.5,r_adv=.4),dict(ses=20260105,duracion=5,dia=0,hora=1,atr_bin=0,r_base=-.5,r_adv=-.6)])
    out=m.summarize(rows,20260101)
    anyrow=next(x for x in out['celdas'] if [x['duracion'],x['dia'],x['hora'],x['atr']]==[5,5,4,3])
    lowrow=next(x for x in out['celdas'] if [x['duracion'],x['dia'],x['hora'],x['atr']]==[5,5,4,0])
    assert anyrow['n']==2 and anyrow['media_r_base']==0
    assert lowrow['n']==1 and out['celdas_nominales']==360

def test_timestamp_equal_excluded_and_close_first_tick():
    t=np.array([10,10,11,20]); p=np.array([400,404,408,412]); b=p-1; a=p+1
    got=m.fill(t,p,b,a,10,20,30,1,99,0)
    assert got==pytest.approx(((411-409)*.25-.288)/(409*.25-99))

def test_no_salida_falla_cerrado():
    with pytest.raises(ValueError,match='sin salida'):
        m.fill(np.array([11,12]),np.array([400,401]),np.array([399,400]),np.array([401,402]),10,20,30,1,99,1)

def fake_rth():
    day=20260112; base=m.midnight(day); mins=np.arange(570,956); n=len(mins)
    # Cada minuto tiene una observación; caja de 100, luego ruptura a 105.
    price=np.where(mins<600,400,420)
    return pd.DataFrame(dict(ts_utc_ns=base+mins*m.MIN+10_000_000_000,price_ticks=price,
        bid_ticks=price-1,ask_ticks=price+1,trade_date=np.full(n,day),regime_id=np.ones(n,int),outside_regular=np.zeros(n,bool)))

def test_caja_y_datos_rth_presencia_completa():
    df=fake_rth(); # dar rango no degenerado en las tres cajas
    df.loc[df.index[::2],'price_ticks']-=4
    df.loc[df.index[::2],'bid_ticks']-=4; df.loc[df.index[::2],'ask_ticks']-=4
    ticks,signals=m.prep(df)
    assert len(ticks)==386 and set(signals.duracion)=={5,15,30}
    assert m.prep(df.drop(df.index[2])) is None

def test_celda_vacia_y_maxT_sesiones_sintetico():
    rs=[dict(ses=20260101+i,duracion=5,dia=i%5,hora=i%4,atr_bin=i%3,lado=1,r_base=1.,r_adv=.8) for i in range(35)]
    old=m.B; m.B=199
    try: out=m.summarize(pd.DataFrame(rs),20260101)
    finally: m.B=old
    a=next(x for x in out['celdas'] if [x['duracion'],x['dia'],x['hora'],x['atr']]==[5,5,4,3])
    # Varianza cero, expresamente sin inferencia en esa celda.
    assert a['n']==35 and not a['evaluable'] and a['p_maxt'] is None

def test_retraso_salida_no_puede_cruzar_noticia():
    times=np.array([11,24])*m.MIN; prices=np.array([400,401]); bid=prices-1; ask=prices+1
    with pytest.raises(ValueError,match='cruza noticia'):
        m.fill(times,prices,bid,ask,10*m.MIN,20*m.MIN,30*m.MIN,1,99,1,events=[23*m.MIN])

def test_circuito_completo_sintetico_sin_red(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    import pyarrow as pa
    import pyarrow.parquet as pq
    days=[20260112,20260113,20260114]
    root=tmp_path/'release'; (root/'metadata').mkdir(parents=True)
    (root/'release_manifest.json').write_text('fake')
    batches=[]
    for idx,day in enumerate(days):
        df=fake_rth(); df['trade_date']=day; mins=np.arange(570,956); base=m.midnight(day)
        df['ts_utc_ns']=base+mins*m.MIN+10_000_000_000
        px=np.where(mins<600,400+np.where(mins%2==0,idx*4+4,0),430+idx*3)
        df['price_ticks']=px; df['bid_ticks']=px-1; df['ask_ticks']=px+1
        batches.append(df)
    path=root/'ticks.parquet'
    with pq.ParquetWriter(path,pa.Table.from_pandas(batches[0]).schema) as writer:
        for df in batches: writer.write_table(pa.Table.from_pandas(df),row_group_size=len(df))
    meta=pd.DataFrame({'instrument':['NQ']*3,'trade_date':days,'prev_trade_date':[20260109,20260112,20260113],'status':['SELECTED']*3})
    meta.to_parquet(root/'metadata/session_index.parquet')
    calendar=[]
    for d in pd.date_range('2026-01-09','2026-01-14'):
        calendar.append({'trade_date':int(d.strftime('%Y%m%d')),'session_class':'CLOSED' if d.weekday()>=5 else 'NORMAL'})
    cal=tmp_path/'cal.json'; cal.write_text(json.dumps({'sessions':calendar}))
    news=tmp_path/'news.csv'; news.write_text('ts_utc,evento,fuente_url,impacto\n2026-01-14T16:00Z,X,https://example.com,tier1\n')
    monkeypatch.setattr(m,'CAL',cal); monkeypatch.setattr(m,'NEWS',news); monkeypatch.setattr(m,'D0',days[0]); monkeypatch.setattr(m,'D1',days[-1]); monkeypatch.setattr(m,'B',99)
    monkeypatch.setattr(m.RR,'sha256_file',lambda x: m.H if x.name=='release_manifest.json' else m.CAL_SHA if x.name=='cal.json' else m.NEWS_SHA)
    monkeypatch.setattr(m.RR,'load_manifest',lambda *a,**kw:{'NQ':SimpleNamespace(path=path,sha256='synthetic')})
    out=tmp_path/'out'; m.run(root,out)
    e0=json.loads((out/'ORB_NQ_E0_CONGELADO.json').read_text()); measured=json.loads((out/'ORB_NQ_RESULTADOS_EXPLORATORIOS.json').read_text())
    assert e0['conteos']['sesiones_calidad']==3 and e0['conteos']['vetos_noticias']==3
    assert measured['total']['operaciones']==6 and len(e0['atr_cortes'])==2
    assert measured['total']['celdas_nominales']==360 and measured['estado']=='EXPLORATORIO_NO_VALIDADO'
