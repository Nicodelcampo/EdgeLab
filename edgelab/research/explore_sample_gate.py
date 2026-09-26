"""Gate de tamaño mínimo para EXPLORE-001, previo a outcomes."""
from __future__ import annotations
from datetime import date

EXPLORE_MIN_SESSIONS=200
class ExploreSampleGateError(ValueError): pass

def audit_explore_sample(eligible_dates,*,minimum=EXPLORE_MIN_SESSIONS):
 if not isinstance(eligible_dates,list): raise ExploreSampleGateError("eligible_dates debe ser lista")
 if isinstance(minimum,bool) or not isinstance(minimum,int) or minimum<=0: raise ExploreSampleGateError("minimum debe ser entero positivo")
 seen=set()
 for index,value in enumerate(eligible_dates):
  if not isinstance(value,str) or not value: raise ExploreSampleGateError("eligible_dates[%d] invalida"%index)
  try: date.fromisoformat(value)
  except ValueError as exc: raise ExploreSampleGateError("fecha no ISO: %s"%value) from exc
  if value in seen: raise ExploreSampleGateError("sesion duplicada: %s"%value)
  seen.add(value)
 observed=len(seen); deficit=max(0,minimum-observed); passed=deficit==0
 return {"status":"PASS" if passed else "BLOCKED_INSUFFICIENT_SESSIONS","may_start_explore":passed,"minimum_sessions":minimum,"observed_sessions":observed,"deficit_sessions":deficit,"prohibited_fillers":["holdout","quarantine","duplicate_sessions"],"outcomes_accessed":False}
