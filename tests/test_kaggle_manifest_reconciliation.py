"""Regression invariants for the rectified Kaggle manifest."""
import json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT/"artifacts/audit/EDGELAB_KAGGLE_CANONICAL_MANIFEST.json").read_text())
I = json.loads((ROOT/"artifacts/audit/EDGELAB_KAGGLE_REMOTE_INVENTORY.json").read_text())
R = M["CANONICAL_RAW_TICKS"]

def test_summary_rows(): assert M["summary"]["total_catalogued_rows"] == sum(r["row_count"] for r in R)
def test_summary_bytes(): assert M["summary"]["total_catalogued_size_bytes"] == sum(r["size_bytes"] for r in R)
def test_instrument_rows():
 for n,a in M["PER_INSTRUMENT_DERIVED"]["instruments"].items(): assert a["rows"] == sum(r["row_count"] for r in R if r["instrument"]==n)
def test_instrument_contract_count():
 for n,a in M["PER_INSTRUMENT_DERIVED"]["instruments"].items(): assert a["contract_count"] == sum(r["instrument"]==n for r in R)
def test_download_hash_requires_provenance():
 for r in R:
  if r.get("download_evidence") in (None,"NONE_LISTING_ONLY"): assert "downloaded_sha256" not in r
def test_remote_verified_implies_remote_file():
 for r in R:
  if r.get("custody_status")=="REMOTE_VERIFIED": assert r["file_name"] in I["datasets"][r["kaggle_dataset"]]["files"]
def test_remote_verified_implies_download_provenance():
 for r in R:
  if r.get("custody_status")=="REMOTE_VERIFIED":
   assert r.get("download_evidence") not in (None,"NONE_LISTING_ONLY")
   assert r.get("downloaded_sha256") == r["source_sha256"]
def test_absent_files_are_blocked():
 for r in R:
  if r["file_name"] not in I["datasets"][r["kaggle_dataset"]]["files"]:
   assert r["custody_status"]=="BLOCKED_BY_CUSTODY" and r["remote_status"]=="REMOTE_ABSENT_OR_UNPROVEN"
def test_nq_0926():
 r=next(x for x in R if x["instrument"]=="NQ" and x["contract_id"]=="NQ_09-26")
 assert not r["remote_listed"] and r["right_censored_by_holdout"] and r["coverage_end_reason"]=="HOLDOUT_BOUNDARY"
 assert M["summary"]["remote_listed_rows"]+r["row_count"]==M["summary"]["total_catalogued_rows"]
def test_not_declared_complete():
 assert M["summary"]["migration_status"]=="MIGRATION_CANONICAL_RAW_COMPLETE_EXCEPT_NQ_09_26"
 assert M["summary"]["reconciliation_status"]=="MIGRATION_MANIFEST_RECONCILIATION_REQUIRED"
def test_no_ambiguous_mb_fields():
 bad=[]
 def walk(x,p=""):
  if isinstance(x,dict):
   for k,v in x.items():
    if k.lower().endswith("_mb"): bad.append(p+"/"+k)
    walk(v,p+"/"+k)
  elif isinstance(x,list):
   for i,v in enumerate(x): walk(v,f"{p}[{i}]")
 walk(M); assert not bad,bad
def test_size_triplets():
 for p in ("total_catalogued","remote_listed"):
  b=M["summary"][p+"_size_bytes"]
  assert M["summary"][p+"_size_gb_decimal"]==pytest.approx(b/1e9)
  assert M["summary"][p+"_size_gib_binary"]==pytest.approx(b/2**30)
def test_holdout():
 for r in R: assert r["max_timestamp_ns"] < 1782856800000000000
def test_mandatory_semantics():
 assert M["mandatory_semantics"]["artifact_role"]=="AUXILIARY_VERSIONED_VIEWER_SNAPSHOT"
 assert M["mandatory_semantics"]["canonical_source"] is False
def test_viewer_authorization():
 assert "VIEWER_ONLY_NOT_MIGRATED" not in M
 s=M["viewer_bundle_snapshot"]
 assert s["status"]=="AUTHORIZED_PENDING_BUILD_AND_UPLOAD" and s["bundle_count"]==147
 assert s["format"]=="json.zst" and not s["js_uploaded"] and not s["continuous_files_uploaded"]
