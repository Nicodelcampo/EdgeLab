from __future__ import annotations
import pytest
from edgelab.research.explore_sample_gate import ExploreSampleGateError,audit_explore_sample

def dates(n): return [( __import__('datetime').date(2025,1,1)+__import__('datetime').timedelta(days=i)).isoformat() for i in range(n)]

def test_193_bloquea_y_declara_deficit_siete():
 report=audit_explore_sample(dates(193)); assert report["status"]=="BLOCKED_INSUFFICIENT_SESSIONS"; assert not report["may_start_explore"]; assert report["deficit_sessions"]==7; assert report["outcomes_accessed"] is False

def test_200_habilita_sin_reducir_minimo():
 report=audit_explore_sample(dates(200)); assert report["status"]=="PASS"; assert report["may_start_explore"] and report["deficit_sessions"]==0

def test_duplicados_no_inflan_n():
 with pytest.raises(ExploreSampleGateError,match="duplicada"): audit_explore_sample(["2025-01-01","2025-01-01"])
