from __future__ import annotations
import pytest
from edgelab.research.first_touch_decongestion import FirstTouchDecongestionError,decongest_first_touch_events

def event(zone,touch,created): return {"zone_id":zone,"first_touch_ms":touch,"created_ms":created,"outcomes_accessed":False}
def session(ms): return "d1" if ms<10_000_000 else "d2"

def test_sep_se_aplica_al_toque_y_reinicia_por_sesion():
 rows=[event("a",1_000_000,10),event("b",2_000_000,20),event("c",10_000_000,30)]
 report=decongest_first_touch_events(rows,session_date_of_ms=session,sep_minutes=120)
 assert [x["zone_id"] for x in report["events"]]==["a","c"]
 assert report["raw_count"]==3 and report["kept_count"]==2
 assert report["policy"]["anchor"]=="first_touch_ms" and report["policy"]["outcomes_accessed"] is False

def test_empate_elige_zona_mas_antigua_sin_mirar_resultados():
 rows=[event("new",1_000_000,500),event("old",1_000_000,100)]
 report=decongest_first_touch_events(rows,session_date_of_ms=lambda _:"d")
 assert [x["zone_id"] for x in report["events"]]==["old"]
 assert report["policy"]["tie_break"]=="oldest_created_then_zone_id"

def test_zone_id_duplicado_y_timestamps_invalidos_fallan_cerrado():
 with pytest.raises(FirstTouchDecongestionError,match="duplicado"):
  decongest_first_touch_events([event("a",100,1),event("a",200,2)],session_date_of_ms=lambda _:"d")
 with pytest.raises(FirstTouchDecongestionError,match="no posterior"):
  decongest_first_touch_events([event("a",100,100)],session_date_of_ms=lambda _:"d")
