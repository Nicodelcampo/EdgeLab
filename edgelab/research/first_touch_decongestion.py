"""Contrato outcome-free de decongestión para primeros toques."""
from __future__ import annotations
from collections import defaultdict

FIRST_TOUCH_SEP_MINUTES = 120
FIRST_TOUCH_SEP_SCOPE = "session"
FIRST_TOUCH_TIEBREAK = "oldest_created_then_zone_id"

class FirstTouchDecongestionError(ValueError): pass

def _integer(row,key,index):
 value=row.get(key)
 if isinstance(value,bool) or not isinstance(value,int): raise FirstTouchDecongestionError("events[%d].%s debe ser entero"%(index,key))
 return value

def decongest_first_touch_events(events,*,session_date_of_ms,sep_minutes=FIRST_TOUCH_SEP_MINUTES):
 """Greedy por sesión sobre first_touch_ms; empates por zona más antigua."""
 if not isinstance(events,list): raise FirstTouchDecongestionError("events debe ser lista")
 if isinstance(sep_minutes,bool) or not isinstance(sep_minutes,int) or sep_minutes<=0: raise FirstTouchDecongestionError("sep_minutes debe ser entero positivo")
 grouped=defaultdict(list); seen=set()
 for index,row in enumerate(events):
  if not isinstance(row,dict): raise FirstTouchDecongestionError("events[%d] debe ser objeto"%index)
  zone_id=row.get("zone_id")
  if not isinstance(zone_id,str) or not zone_id: raise FirstTouchDecongestionError("events[%d].zone_id invalido"%index)
  if zone_id in seen: raise FirstTouchDecongestionError("zone_id duplicado: %s"%zone_id)
  seen.add(zone_id)
  touch_ms=_integer(row,"first_touch_ms",index); created_ms=_integer(row,"created_ms",index)
  if touch_ms<=created_ms: raise FirstTouchDecongestionError("toque no posterior a creacion: %s"%zone_id)
  session=session_date_of_ms(touch_ms)
  if not isinstance(session,str) or not session: raise FirstTouchDecongestionError("fecha de sesion invalida: %s"%zone_id)
  grouped[session].append((touch_ms,created_ms,zone_id,row))
 sep_ms=sep_minutes*60*1000; kept=[]; rejected=[]; by_session={}
 for session,rows in sorted(grouped.items()):
  rows.sort(key=lambda item:(item[0],item[1],item[2]))
  last_kept=None; kept_n=0
  for touch_ms,created_ms,zone_id,row in rows:
   if last_kept is None or touch_ms-last_kept>=sep_ms:
    enriched=dict(row); enriched.update({"session_date":session,"decongestion_policy":"first_touch_session_greedy_v1","sep_minutes":sep_minutes,"tie_break":FIRST_TOUCH_TIEBREAK})
    kept.append(enriched); last_kept=touch_ms; kept_n+=1
   else:
    rejected.append({"zone_id":zone_id,"session_date":session,"first_touch_ms":touch_ms,"reason":"within_sep_minutes","previous_kept_ms":last_kept})
  by_session[session]={"raw":len(rows),"kept":kept_n,"rejected":len(rows)-kept_n}
 return {"policy":{"anchor":"first_touch_ms","scope":FIRST_TOUCH_SEP_SCOPE,"sep_minutes":sep_minutes,"tie_break":FIRST_TOUCH_TIEBREAK,"outcomes_accessed":False},"events":kept,"rejected":rejected,"by_session":by_session,"raw_count":len(events),"kept_count":len(kept)}
