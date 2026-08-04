from __future__ import annotations
import pytest
from tools.audit_censo_gate import IntegrityGateError,audit

def row(name="a.parquet",duplicates=None,**extra):
 value={"archivo":name,"duplicaciones_de_bloque":[] if duplicates is None else duplicates}; value.update(extra); return value

def test_limpio_habilita_censo_de_senales():
 report=audit([row(),row("b.parquet")]); assert report["status"]=="PASS"; assert report["may_run_signal_census"]; assert report["total_duplicate_blocks"]==0

def test_un_duplicado_bloquea_todo():
 report=audit([row(duplicates=[{}])]); assert report["status"]=="BLOCKED_SOURCE_INTEGRITY"; assert not report["may_run_signal_census"]; assert report["total_duplicate_blocks"]==1

def test_error_o_schema_incompleto_fallan_cerrado():
 assert not audit([row(error="ilegible")])["may_run_signal_census"]
 assert not audit([{"archivo":"a.parquet"}])["may_run_signal_census"]
 with pytest.raises(IntegrityGateError): audit([])
