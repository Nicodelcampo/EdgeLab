import json,sys
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'patches_for_review/orb_cfd_20261108'),str(ROOT/'patches_for_review/orb_nq_20261108'),str(ROOT)]
import medir_cfd as m


def day(d):
    op=pd.Timestamp(d+' 09:30',tz='America/New_York').as_unit('ns').value
    close=op+390*m.MIN
    times=np.arange(op-30*m.MIN,close,m.MIN,dtype=np.int64)
    vals=100+np.arange(len(times))*.05
    frame=pd.DataFrame({'time_utc_ns':times,'bid':vals-.05,'ask':vals+.05})
    return op,close,frame


def test_calendario_excluye_feriados_y_cortos():
    dates,opens,closes=m.schedule(ROOT/'patches_for_review/orb_cfd_20261108/sesiones_xnys.json')
    assert set([20230103,20241127,20250108]) <= set(dates)
    assert not ({20230703,20231124,20241129,20250109,20251128} & set(dates))
    assert np.all(closes-opens == 390*m.MIN)


def test_fragmentos_de_rowgroups_no_duplican_sesion(tmp_path):
    o,c,f=day('2023-01-03');o2,c2,f2=day('2023-01-04'); p=tmp_path/'ticks.parquet'
    pq.write_table(pa.Table.from_pandas(pd.concat([f,f2],ignore_index=True)),p,row_group_size=59)
    cal=(np.array([20230103,20230104]),np.array([o,o2]),np.array([c,c2]))
    blocks=list(m.iter_days(p,cal))
    assert [x[0] for x in blocks]==[20230103,20230104]
    assert [len(x[3]) for x in blocks]==[len(f),len(f2)]
    assert np.array_equal(blocks[0][3].time_utc_ns.to_numpy(),f.time_utc_ns.to_numpy())


def test_caja_dura_y_atr_causal():
    o,c,f=day('2023-01-03'); r=m.prepare(20230103,o,c,f)
    assert r is not None
    sig=r[-1]; assert set(sig.duracion)=={5,15,30}
    assert np.isfinite(sig.atr14).all()
    incomplete=f.drop(f.index[60]); assert m.prepare(20230103,o,c,incomplete) is None


def test_fill_long_stop_bidask_slippage_y_riesgo():
    t=np.array([100,101,102,103],dtype='int64')
    bid=np.array([100,100,98,99.]);ask=bid+.2;mid=bid+.1
    ans=m.fill(t,bid,ask,mid,100,200,300,1,99,1,np.array([],dtype='int64'))
    entry=100.2+.25;exit_=98-.25;risk=entry-99
    assert ans==pytest.approx((exit_-entry-5.76/20)/risk)


def test_fill_short_and_timestamps_duplicados():
    t=np.array([100,100,101,102],dtype='int64')
    bid=np.array([100,101,102,104.]);ask=bid+.2;mid=bid+.1
    ans=m.fill(t,bid,ask,mid,100,200,300,-1,103,1,np.array([],dtype='int64'))
    entry=102-.25;exit_=104.2+.25;risk=103-entry
    assert ans==pytest.approx((entry-exit_-5.76/20)/risk)


def test_veto_noticias_toca_limites():
    e=np.array([100*m.MIN],dtype='int64')
    assert m.blocked(1*m.MIN,99*m.MIN,e)
    assert not m.blocked(1*m.MIN,98*m.MIN,e)


def test_cotizacion_cruzada_aborta():
    o,c,f=day('2023-01-03');f.loc[0,'ask']=f.loc[0,'bid']-1
    with pytest.raises(ValueError):m.prepare(20230103,o,c,f)


def test_pipeline_sintetico_guardado_solo_agregado(tmp_path,monkeypatch):
    dates=['2023-01-03','2023-01-04','2023-01-05','2023-01-06']
    sessions=[]; frames=[]
    for i,d in enumerate(dates):
        op,cl,frame=day(d)
        midpoint=100+np.arange(len(frame))*(.05+i*.02)
        frame['bid']=midpoint-.05;frame['ask']=midpoint+.05
        sessions.append({'date':int(d.replace('-','')),'open_ns':int(op),'close_ns':int(cl)})
        frames.append(frame)
    p=tmp_path/'ticks.parquet';pq.write_table(pa.Table.from_pandas(pd.concat(frames,ignore_index=True)),p,row_group_size=59)
    cal=tmp_path/'cal.json';cal.write_text(json.dumps({'sessions':sessions}))
    news=tmp_path/'news.csv';news.write_text('ts_utc,evento,fuente_url,impacto\n2022-01-04T15:00Z,test,example,tier1\n')
    monkeypatch.setattr(m,'TICK_SHA',m.sha(p));monkeypatch.setattr(m,'NEWS_SHA',m.sha(news))
    m.run(p,cal,news,tmp_path)
    out=json.loads((tmp_path/'ORB_CFD_RESULTADOS_EXPLORATORIOS.json').read_text())
    assert out['conteos']['sesiones_calidad']==4
    assert out['total']['operaciones']==12
    assert [(x['duracion'],x['n']) for x in out['resumen_lectura']['sin_filtros']]==[(5,4),(15,4),(30,4)]
    assert 'rows' not in out and 'operaciones_individuales' not in out


def test_rowgroup_con_holdout_aborta_antes_de_leer(tmp_path):
    op,cl,f=day('2023-01-03')
    f.loc[len(f)]={'time_utc_ns':m.HOLDOUT_NS,'bid':100.,'ask':100.1}
    p=tmp_path/'ticks.parquet';pq.write_table(pa.Table.from_pandas(f),p,row_group_size=len(f))
    cal=(np.array([20230103]),np.array([op]),np.array([cl]))
    with pytest.raises(ValueError,match='holdout'):
        list(m.iter_days(p,cal))
