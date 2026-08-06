"""Integración outcome-free del censo primario de EXPLORE-001."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .first_touch_population import extract_first_touch_events
from .first_touch_decongestion import decongest_first_touch_events

CT=ZoneInfo("America/Chicago")
class FirstTouchCensusError(ValueError): pass

def session_date_ct(unix_ms):
 if isinstance(unix_ms,bool) or not isinstance(unix_ms,int): raise FirstTouchCensusError("unix_ms debe ser entero")
 return datetime.fromtimestamp(unix_ms/1000,tz=timezone.utc).astimezone(CT).strftime("%Y-%m-%d")

def build_first_touch_census(*,indicator_results_by_archive,eligible_days,session_date_of_ms=session_date_ct,sep_minutes=120):
 if not isinstance(indicator_results_by_archive,dict): raise FirstTouchCensusError("indicator_results_by_archive debe ser objeto")
 if not isinstance(eligible_days,list) or not eligible_days: raise FirstTouchCensusError("eligible_days debe ser lista no vacia")
 owner={}; expected_by_archive={}
 for index,day in enumerate(eligible_days):
  if not isinstance(day,dict): raise FirstTouchCensusError("eligible_days[%d] debe ser objeto"%index)
  archive,date=day.get("archivo"),day.get("fecha")
  if not isinstance(archive,str) or not archive or not isinstance(date,str) or not date: raise FirstTouchCensusError("dia elegible invalido")
  previous=owner.setdefault(date,archive)
  if previous!=archive: raise FirstTouchCensusError("sesion repetida entre contratos: %s"%date)
  expected_by_archive.setdefault(archive,set()).add(date)
 expected=set(expected_by_archive)
 observed=set(indicator_results_by_archive)
 if observed!=expected: raise FirstTouchCensusError("contratos esperados=%s observados=%s"%(sorted(expected),sorted(observed)))
 all_events=[]; outside=0
 for archive in sorted(expected):
  extracted=extract_first_touch_events(indicator_results_by_archive[archive])
  allowed=expected_by_archive[archive]
  for row in extracted:
   session=session_date_of_ms(row["first_touch_ms"])
   if session not in allowed:
    outside+=1; continue
   enriched=dict(row); enriched["source_zone_id"]=row["zone_id"]; enriched["zone_id"]=archive+"::"+row["zone_id"]; enriched["archive"]=archive
   all_events.append(enriched)
 decongested=decongest_first_touch_events(all_events,session_date_of_ms=session_date_of_ms,sep_minutes=sep_minutes)
 raw=Counter(session_date_of_ms(row["first_touch_ms"]) for row in all_events)
 kept=Counter(row["session_date"] for row in decongested["events"])
 dates=sorted(owner)
 return {"schema_version":"first_touch_census_v1","status":"COMPLETE","event_anchor_policy":"first_touch_after_creation_bar","session_timezone":"America/Chicago","session_count":len(dates),"contract_count":len(expected),"dates":dates,"raw_per_session":{d:raw.get(d,0) for d in dates},"post_sep_per_session":{d:kept.get(d,0) for d in dates},"raw_count":len(all_events),"post_sep_count":len(decongested["events"]),"outside_universe_count":outside,"zero_raw_sessions":sum(raw.get(d,0)==0 for d in dates),"zero_post_sep_sessions":sum(kept.get(d,0)==0 for d in dates),"decongestion":decongested["policy"],"outcomes_accessed":False}
