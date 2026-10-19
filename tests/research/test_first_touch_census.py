from __future__ import annotations
import pytest
from edgelab.research.first_touch_census import FirstTouchCensusError,build_first_touch_census

def created(zone,bar,ms): return {"type":"ZONE_CREATED","zone_id":zone,"bar_index":bar,"unix_ms":ms,"touch_count":0}
def touched(zone,bar,ms,count=1): return {"type":"ZONE_TOUCHED","zone_id":zone,"bar_index":bar,"unix_ms":ms,"touch_count":count}
def result(events): return {"events":events,"zones":[]}
def day(ms): return "d1" if ms<10_000_000 else "d2"

def test_integra_poblacion_decongestion_ceros_y_cobertura():
 results={"a.parquet":result([created("z1",1,1),touched("z1",2,1_000_000),created("z2",1,2),touched("z2",2,2_000_000)])}
 report=build_first_touch_census(indicator_results_by_archive=results,eligible_days=[{"archivo":"a.parquet","fecha":"d1"},{"archivo":"a.parquet","fecha":"d2"}],session_date_of_ms=day,sep_minutes=120)
 assert report["status"]=="COMPLETE" and report["session_count"]==2
 assert report["raw_per_session"]=={"d1":2,"d2":0}
 assert report["post_sep_per_session"]=={"d1":1,"d2":0}
 assert report["zero_post_sep_sessions"]==1 and report["outcomes_accessed"] is False

def test_toque_fuera_del_universo_se_reporta_no_se_cuenta():
 results={"a":result([created("z",1,1),touched("z",2,10_000_000)])}
 report=build_first_touch_census(indicator_results_by_archive=results,eligible_days=[{"archivo":"a","fecha":"d1"}],session_date_of_ms=day)
 assert report["raw_count"]==0 and report["outside_universe_count"]==1

def test_contratos_faltantes_o_sesion_repetida_fallan_cerrado():
 with pytest.raises(FirstTouchCensusError,match="contratos esperados"):
  build_first_touch_census(indicator_results_by_archive={},eligible_days=[{"archivo":"a","fecha":"d1"}],session_date_of_ms=day)
 with pytest.raises(FirstTouchCensusError,match="repetida"):
  build_first_touch_census(indicator_results_by_archive={"a":result([]),"b":result([])},eligible_days=[{"archivo":"a","fecha":"d1"},{"archivo":"b","fecha":"d1"}],session_date_of_ms=day)
