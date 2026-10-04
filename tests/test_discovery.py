import numpy as np,pytest
from edgelab.discovery import GridSpec,spec_hash,get_backend
from edgelab.discovery.spec import Condition,spec_dict
from edgelab.discovery import data as Dd,features as F,pipeline as P,scan as S,calibrate as C

def synth_ticks(n_sessions=12,seed=0,start="2026-03-02"):
    """Ticks sintéticos: paseo aleatorio, un tick cada ~3 s, sesión CME completa (17:00-16:00 CT), agresor al azar."""
    import pandas as pd
    rng=np.random.default_rng(seed);ts=[];days=pd.bdate_range(start,periods=n_sessions)
    for d in days:
        s0=(pd.Timestamp(d.date())-pd.Timedelta(days=1)).tz_localize("America/Chicago")+pd.Timedelta(hours=17)
        n=int(23*3600/3);off=np.cumsum(rng.integers(1,6,n))*10**9;ts.append(s0.tz_convert("UTC").value+off)
    ts=np.concatenate(ts);n=len(ts);px=(100000+np.cumsum(rng.integers(-2,3,n))).astype(np.int64)
    bid=px-1;ask=px+1;vol=rng.integers(1,6,n).astype(np.int32);ag=rng.choice(np.array([1,-1],np.int8),n)
    return {"ts_utc_ns":ts,"price_ticks":px,"bid_ticks":bid,"ask_ticks":ask,"volume":vol,"aggressor":ag}

def small_spec():
    return GridSpec(name="t",holds=(15,30),slots_hhmm=(100,415,1000,1330),conditions=(Condition("mom_15","gt",0.),Condition("mom_15","lt",0.),Condition("absorb_30","zgt",1.0)),pairs=((0,2),),min_trades=5,n_sims=1000,zscore_min_history=3)

def build_T(tk,spec):
    bars=Dd.minute_bars(tk);segs,elig=Dd.continuous_segments({"X":Dd.daily_volume(bars)},["X"],0.0);return P.build(spec,{"X":tk},{"X":bars},["X"],segs,elig),bars

def test_spec_hash_stable_and_validates():
    s=small_spec();s.validate();assert spec_hash(s)==spec_hash(small_spec());assert spec_hash(s)!=spec_hash(GridSpec(name="otro"))
    with pytest.raises(ValueError):GridSpec(name="x",conditions=(Condition("foo_5","gt"),)).validate()
    with pytest.raises(ValueError):GridSpec(name="x",n_sims=10).validate()

def test_features_are_causal():
    """Cambiar los ticks POSTERIORES a la barra de señal no debe alterar ninguna característica de esa barra."""
    tk=synth_ticks(6);bars=Dd.minute_bars(tk);t=bars["t"];b1=t[len(t)//2:len(t)//2+1]
    names={"mom_15","rng_30","vwapdev_30","imb_15","absorb_30","effort_15","spread_15","emadev_20"};a,_=F.compute(bars,b1,names)
    tk2={k:v.copy() for k,v in tk.items()};cut=int(np.searchsorted(tk["ts_utc_ns"],b1[0]));tk2["price_ticks"][cut:]+=500;tk2["volume"][cut:]*=7
    b,_=F.compute(Dd.minute_bars(tk2),b1,names)
    for n in names:assert np.allclose(a[n],b[n],equal_nan=True),n

def test_delay_guard_discards_far_ticks():
    """Con un hueco de datos sobre la franja 04:15, la oportunidad se descarta; no se usa un tick lejano como precio."""
    import pandas as pd
    tk=synth_ticks(6);spec=small_spec();T0,_=build_T(tk,spec);ok0=int(np.isfinite(T0.rt).sum())
    d=pd.Timestamp("2026-03-04",tz="America/Chicago")+pd.Timedelta(hours=4,minutes=14);g0=d.tz_convert("UTC").value;g1=g0+150*60*10**9
    ts=tk["ts_utc_ns"];keep=~((ts>=g0)&(ts<g1));tk2={k:v[keep] for k,v in tk.items()}
    T1,_=build_T(tk2,spec);assert int(np.isfinite(T1.rt).sum())<ok0
    assert T1.meta["dropped"]["entry_delay"]+T1.meta["dropped"]["exit_delay"]>T0.meta["dropped"]["entry_delay"]+T0.meta["dropped"]["exit_delay"]

def test_outcomes_use_book_fills():
    tk=synth_ticks(6);spec=small_spec();T,_=build_T(tk,spec);m=np.isfinite(T.nl)&np.isfinite(T.ns)
    assert m.any();assert np.all((T.nl[m]+T.ns[m])<=0.0001)      # largo+corto por libro nunca gana en conjunto (spread de 2 ticks)

def test_null_calibration_false_positive_rate():
    rng=np.random.default_rng(1);D,nc=120,300;M=rng.standard_normal((D,nc)).astype(np.float32)*(rng.random((D,nc))<0.5);N=(M!=0).astype(np.float32)+1
    fp=C.false_positive_rate(M,N,10,reps=60,n_sims=500,seed=5);assert fp["false_positive_rate"]<=0.15      # esperado ~0,05; margen por 60 repeticiones

def test_planted_signal_is_detected_and_monotone():
    rng=np.random.default_rng(2);D,nc=150,200;M=rng.standard_normal((D,nc)).astype(np.float32);N=np.ones((D,nc),np.float32)
    pc=C.power_curve(M,N,10,[0.0,0.5],reps=12,n_sims=500,seed=3);assert pc[1]["detection_rate"]>=0.8;assert pc[0]["detection_rate"]<=0.35

def test_bh_and_holm():
    p=np.array([0.001,0.01,0.03,0.2,0.9]);assert np.all(S.holm(p)>=p);q=S.benjamini_hochberg(p);assert np.all(q>=p-1e-12) and np.all(np.diff(q[np.argsort(p)])>=-1e-12)

def test_backend_cpu_and_gpu_parity_if_available():
    cpu=get_backend("cpu");assert cpu.name=="cpu"
    try:
        gpu=get_backend("gpu")
    except RuntimeError:
        pytest.skip("sin GPU: la paridad CPU/GPU se verifica en Kaggle")
    rng=np.random.default_rng(0);A=rng.standard_normal((100,500)).astype(np.float32)
    assert np.allclose(S.max_null(A,512,7,cpu),S.max_null(A,512,7,gpu),atol=1e-3)

def test_end_to_end_synthetic_scan_runs():
    tk=synth_ticks(45);spec=small_spec();T,_=build_T(tk,spec);M,N=P.cell_matrices(T);r=S.scan(M,N,spec.min_trades,spec.n_sims,spec.seed)
    assert r["n_cells"]>0 and 0<r["p_max"]<=1 and r["real_max_abs_z"]>0;cut=int(0.7*len(T.dates));rep=S.replicate(M,N,np.arange(cut),np.arange(cut,len(T.dates)),spec.min_trades,3,1000,1);assert len(rep)==3

def test_blocked_null_is_identical_to_unblocked():
    """El bloqueo por memoria no cambia el resultado: mismos signos en todos los bloques."""
    rng=np.random.default_rng(4);A=(rng.standard_normal((90,5000))/np.sqrt(90)).astype(np.float32)
    a=S.max_null(A,300,11,max_matrix_bytes=2**31);b=S.max_null(A,300,11,max_matrix_bytes=2**18);c=S.max_null(A,300,11,max_matrix_bytes=2**16)
    assert np.allclose(a,b,atol=1e-5) and np.allclose(a,c,atol=1e-5)

def test_family_headlines_and_plateau():
    from edgelab.discovery import families as Fm
    S_,H_=6,3;keys=["none","mom_15:gt:0","absorb_30:zgt:1","mom_15:gt:0&absorb_30:zgt:1"];K=len(keys);cells=np.arange(S_*H_*K);z=np.random.default_rng(0).standard_normal(len(cells))*0.5
    c=(2*H_+1)*K+1;z[c]=4.0
    for ds,dh in((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)):z[((2+ds)*H_+(1+dh))*K+1]=2.0
    hs=Fm.headlines(z,cells,keys,S_,H_);top=hs[0];assert top["family"]=="mom" and top["cell"]==c and top["plateau"] is True
    assert Fm.family_of("a_15:gt:0&b_15:zgt:1")=="pair:a+b" and Fm.family_of("none")=="none"

def test_staged_scan_keeps_d2_sealed():
    from edgelab.funnel.splits import make_splits
    tk=synth_ticks(45);spec=small_spec();T,_=build_T(tk,spec);M,N=P.cell_matrices(T);split=make_splits(T.dates);r=S.staged_scan(M,N,T.dates,split,spec)
    assert r["D2_sealed"] is True and r["D0_sessions"]+r["D1_sessions"]<len(T.dates) and r["split_hash"]==split.split_hash
    d2=np.isin(T.dates,np.array(split.d2_dates));assert d2.sum()>0 and not r["D0_mask"][d2].any()

def test_pool_cells_aligns_dates_and_sums():
    a=(np.array([1,2,3]),np.ones((3,4),np.float32),np.ones((3,4),np.float32));b=(np.array([2,3,4]),2*np.ones((3,4),np.float32),np.ones((3,4),np.float32))
    d,M,N=P.pool_cells([a,b]);assert list(d)==[1,2,3,4] and np.allclose(M[:,0],[1,3,3,2]) and np.allclose(N[:,0],[1,2,2,1])

def test_power_curve_ignores_real_structure_in_base():
    """Si la base real ya contiene una señal fuerte, el efecto plantado 0 NO debe detectarse (la base se neutraliza con signos al azar)."""
    rng=np.random.default_rng(9);D,nc=150,200;M=rng.standard_normal((D,nc)).astype(np.float32);M[:,7]+=2.0;N=np.ones((D,nc),np.float32)
    pc=C.power_curve(M,N,10,[0.0],reps=15,n_sims=500,seed=3);assert pc[0]["detection_rate"]<=0.35

def _write_parquet(tk,path,contract="X_03-26"):
    import pandas as pd
    n=len(tk["ts_utc_ns"]);df=pd.DataFrame({"ts_utc_ns":tk["ts_utc_ns"],"ts_local_ns":tk["ts_utc_ns"],"sequence":np.arange(n),"price_ticks":tk["price_ticks"],"bid_ticks":tk["bid_ticks"],"ask_ticks":tk["ask_ticks"],
        "volume":tk["volume"],"aggressor":np.where(tk["aggressor"]>0,"buy","sell"),"tick_type":"trade","instrument":"X","contract":contract,"source_file":"s","source_row":np.arange(n)})
    df.to_parquet(path,row_group_size=50_000)

def _asset(tmp_path,contract="X_03-26"):
    return {"root":"X","order":[contract],"tick_size":0.25,"tick_value_usd":5.0,"commission_usd_rt":0.0,"cut_ns":None,"path_template":str(tmp_path/"{contract}.parquet")}

def test_cache_path_is_identical_to_direct_build(tmp_path):
    """Armar con filas/barras del caché da exactamente los mismos tensores y máscaras que leer los ticks."""
    from edgelab.discovery import cache as CA
    tk=synth_ticks(10,seed=4,start="2026-03-16");spec=small_spec();_write_parquet(tk,tmp_path/"X_03-26.parquet");asset=_asset(tmp_path)
    T0,_=build_T(tk,spec);assert not CA.cache_ok(asset,spec,tmp_path/"c");CA.build_cache(asset,spec,tmp_path/"c",log=lambda *_:None);assert CA.cache_ok(asset,spec,tmp_path/"c")
    bars,rows,order,segs,elig,aud,_=CA.load_cache(asset,tmp_path/"c");T1=P.build(spec,None,bars,order,segs,elig,rows=rows)
    for k in("rt","nl","ns"):assert np.array_equal(getattr(T0,k),getattr(T1,k),equal_nan=True),k
    assert np.array_equal(T0.masks,T1.masks) and T0.meta["dropped"]==T1.meta["dropped"] and np.array_equal(T0.dates,T1.dates)
    spec2=GridSpec(**{**spec.__dict__,"commission_ticks":1.0});assert not CA.cache_ok(asset,spec2,tmp_path/"c")      # cambiar un parámetro invalida el caché

def test_cache_reused_across_families_with_different_conditions(tmp_path):
    """Dos familias con condiciones distintas comparten filas y barras: los tensores de resultado son iguales y solo difieren las máscaras."""
    from edgelab.discovery import cache as CA
    tk=synth_ticks(10,seed=5,start="2026-03-16");sA=small_spec();sB=GridSpec(**{**sA.__dict__,"conditions":(Condition("vwapdev_30","gt",0.),Condition("emadev_20","lt",0.)),"pairs":()})
    _write_parquet(tk,tmp_path/"X_03-26.parquet");asset=_asset(tmp_path);CA.build_cache(asset,sA,tmp_path/"c",log=lambda *_:None);assert CA.cache_ok(asset,sB,tmp_path/"c")
    bars,rows,order,segs,elig,_,_=CA.load_cache(asset,tmp_path/"c");TA=P.build(sA,None,bars,order,segs,elig,rows=rows);TB=P.build(sB,None,bars,order,segs,elig,rows=rows);TBd,_=build_T(tk,sB)
    assert np.array_equal(TA.rt,TB.rt,equal_nan=True) and np.array_equal(TB.masks,TBd.masks) and np.array_equal(TB.rt,TBd.rt,equal_nan=True)

def test_audit_flags_planted_defects(tmp_path):
    """La auditoría cuenta los defectos plantados (libro cruzado, hueco en horario líquido, filas repetidas, sesión que termina temprano) y no cambia los datos."""
    from edgelab.discovery import audit as A
    import pandas as pd
    tk=synth_ticks(8,seed=6);tk={k:v.copy() for k,v in tk.items()};ts=tk["ts_utc_ns"]
    tk["bid_ticks"][100:105]=tk["ask_ticks"][100:105]+2                                   # 5 libros cruzados
    d=pd.Timestamp("2026-03-05",tz="America/Chicago")+pd.Timedelta(hours=10);g0=d.tz_convert("UTC").value
    keep=~((ts>=g0)&(ts<g0+30*60*10**9));tk={k:v[keep] for k,v in tk.items()}                # hueco de 30 min a las 10:00 CT
    for k in tk:tk[k][2001]=tk[k][2000]                                                    # una fila idéntica a la anterior
    before={k:v.copy() for k,v in tk.items()};tl=A.tick_level(tk,None);assert tl["crossed_book"]>=5 and tl["consecutive_identical_rows"]>=1
    bars=Dd.minute_bars(tk);sl=A.session_level(bars);assert any(any(f.startswith("hueco_") for f in x["flags"]) for x in sl["flagged"])
    assert all(np.array_equal(before[k],tk[k]) for k in tk)                                # descriptiva: no modifica
