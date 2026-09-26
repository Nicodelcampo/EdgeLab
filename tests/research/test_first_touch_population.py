from __future__ import annotations
import pytest
from edgelab.research.first_touch_population import FirstTouchPopulationError,extract_first_touch_events

def created(zone="1_B",bar=1,ms=1000): return {"type":"ZONE_CREATED","zone_id":zone,"bar_index":bar,"unix_ms":ms,"touch_count":0}
def touched(zone="1_B",bar=2,ms=2000,count=1): return {"type":"ZONE_TOUCHED","zone_id":zone,"bar_index":bar,"unix_ms":ms,"touch_count":count}
def result(events): return {"events":events,"zones":[{"id":"1_B","kind":"trapped_buyers"}]}

def test_extrae_solo_primer_toque_y_no_outcomes():
 rows=extract_first_touch_events(result([created(),touched(),touched(bar=3,ms=3000,count=2)]))
 assert rows==[{"zone_id":"1_B","created_bar":1,"first_touch_bar":2,"created_ms":1000,"first_touch_ms":2000,"kind":"trapped_buyers","outcomes_accessed":False}]

def test_zona_sin_toque_no_entra():
 assert extract_first_touch_events(result([created()]))==[]

def test_toque_en_barra_creadora_falla_anti_lookahead():
 with pytest.raises(FirstTouchPopulationError,match="no posterior"):
  extract_first_touch_events(result([created(),touched(bar=1)]))

def test_primer_toque_sin_creacion_o_duplicado_falla_cerrado():
 with pytest.raises(FirstTouchPopulationError,match="sin creación"):
  extract_first_touch_events(result([touched()]))
 with pytest.raises(FirstTouchPopulationError,match="duplicado"):
  extract_first_touch_events(result([created(),touched(),touched()]))
