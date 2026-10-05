import sys
from pathlib import Path
import numpy as np,pandas as pd,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"docs/data_catalog"))
import edgelab_data as ed

def _make(tmp_path):
    rng=np.random.default_rng(3);start=int(pd.Timestamp("2026-03-16 22:00",tz="UTC").value);n=400_000
    ts=start+np.cumsum(rng.integers(1,2_500_000_000,n)).astype(np.int64)                    # ~ días de ticks, con varios segundos entre ellos
    px=(20000+np.cumsum(rng.integers(-2,3,n))).astype(np.int64);vol=rng.integers(1,6,n).astype(np.int32);ag=rng.choice(["buy","sell","unclassified"],n)
    df=pd.DataFrame({"ts_utc_ns":ts,"price_ticks":px,"volume":vol,"aggressor":ag,"tick_type":"trade","contract":"TST 06-26"})
    d=tmp_path/"dsx";d.mkdir();df.to_parquet(d/"f.parquet",row_group_size=997)               # grupos chicos: un minuto queda partido entre grupos
    sd=pd.Series(ed._session_date(ts)).unique().tolist()
    ed.RESOLVER["instruments"]["TST"]={"tick_size":0.25,"sessions":[{"date":x,"contract":"TST_06-26","dataset":"dsx","file":"f.parquet","approved":True,"reason":None,"caveat":None} for x in sd]}
    ed.ROOTS=[tmp_path];return sd

def test_fast_m1_equals_slow_m1_and_caches(tmp_path,monkeypatch):
    monkeypatch.setenv("EDGELAB_M1_CACHE",str(tmp_path/"cache"));sd=_make(tmp_path);a,b=min(sd),max(sd)
    slow=ed._load_m1_slow("TST",a,b);slow["buy_volume"]=slow["buy_volume"].astype("float64");fast=ed.load_m1("TST",a,b);pd.testing.assert_frame_equal(slow,fast)   # buy_volume: la original salía int64 o float64 según los datos; ahora siempre float64
    assert any((tmp_path/"cache").glob("*.m1.parquet"));pd.testing.assert_frame_equal(fast,ed.load_m1("TST",a,b))   # segunda vez: desde el caché

def test_fast_m1_respects_the_session_filter(tmp_path,monkeypatch):
    monkeypatch.setenv("EDGELAB_M1_CACHE",str(tmp_path/"cache"));sd=sorted(_make(tmp_path))
    ed.RESOLVER["instruments"]["TST"]["sessions"]=[s for s in ed.RESOLVER["instruments"]["TST"]["sessions"] if s["date"]!=sd[1]]
    f=ed.load_m1("TST",sd[0],sd[-1]);assert sd[1] not in set(f.session_date) and sd[0] in set(f.session_date)

def test_check_inputs_fails_fast_listing_missing_datasets(tmp_path):
    ed.RESOLVER["instruments"]["TSM"]={"tick_size":1.0,"sessions":[{"date":"2026-01-05","contract":"X","dataset":"falta-este","file":"a.parquet","approved":True,"reason":None,"caveat":None}]};ed.ROOTS=[tmp_path]
    with pytest.raises(FileNotFoundError,match="falta-este"):ed.load_m1("TSM","2026-01-01","2026-01-31")

def test_alternative_source_used_when_primary_is_not_mounted(tmp_path,monkeypatch):
    monkeypatch.setenv("EDGELAB_M1_CACHE",str(tmp_path/"cache"));sd=sorted(_make(tmp_path))
    rows=ed.RESOLVER["instruments"]["TST"]["sessions"]
    for r in rows:r.update(dataset="primario-ausente",file="p.parquet",alts=[{"dataset":"dsx","file":"f.parquet","consistent":True}])
    s=ed.resolve_sources("TST",sd[0],sd[-1]);assert set(s.dataset)=={"dsx"} and set(s.source_note)=={"alternativa de primario-ausente"}
    m=ed.load_m1("TST",sd[0],sd[-1]);assert len(m)>0
    for r in rows:r["alts"]=[{"dataset":"dsx","file":"f.parquet","consistent":False}]                      # alternativa inconsistente: no se usa
    with pytest.raises(FileNotFoundError,match="primario-ausente"):ed.load_m1("TST",sd[0],sd[-1])
