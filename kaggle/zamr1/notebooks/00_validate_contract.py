# -*- coding: utf-8 -*-
"""ZAMR-1 Notebook 00: valida Z0 sintético o Z1 derivado, fail-closed."""
from __future__ import annotations
import hashlib,importlib,json,os,platform,sys
from pathlib import Path
import pandas as pd
EXPECTED_SCHEMA="zamr1_structural_contract_v0"
BASE_REQUIRED=("dataset_manifest.json","contract.json","parameter_registry.json","instrument_manifest.json","hashes.sha256","structural_contract.py")
WORKING_ROOT=Path(os.environ.get("EDGELAB_KAGGLE_WORKING","/kaggle/working"))
def sha256_file(path,chunk=1<<20):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(chunk),b""):h.update(b)
 return h.hexdigest()
def find_input_root():
 explicit=os.environ.get("EDGELAB_KAGGLE_INPUT")
 if explicit:
  p=Path(explicit)
  if not p.is_dir():raise RuntimeError("input inexistente: %s"%p)
  return p
 roots=[]
 for c in Path("/kaggle/input").glob("*/contract.json"):
  try:d=json.loads(c.read_text("utf-8"))
  except Exception:continue
  if d.get("schema_version")==EXPECTED_SCHEMA:roots.append(c.parent)
 if len(roots)!=1:raise RuntimeError("se esperaba un input ZAMR-1; encontrados=%d"%len(roots))
 return roots[0]
def verify_hashes(root):
 violations=[];checked=0
 for n,line in enumerate((root/"hashes.sha256").read_text("utf-8").splitlines(),1):
  if not line.strip() or line.lstrip().startswith("#"):continue
  expected,sep,name=line.partition("  ")
  if not sep or len(expected)!=64:violations.append("linea %d malformada"%n);continue
  target=(root/name.strip()).resolve()
  try:target.relative_to(root.resolve())
  except ValueError:violations.append("path fuera del dataset: %s"%name.strip());continue
  if not target.is_file():violations.append("faltante: %s"%name.strip());continue
  checked+=1
  if sha256_file(target)!=expected.lower():violations.append("hash mismatch: %s"%name.strip())
 if checked==0:violations.append("cero archivos verificados")
 return {"passed":not violations,"checked":checked,"violations":violations}
def load_tables(root,manifest):
 fmt=manifest.get("transport_format","parquet")
 if fmt=="csv_truth_known":
  if manifest.get("pilot_stage")!="Z0_SYNTHETIC_ENVIRONMENT":raise RuntimeError("CSV permitido solo para Z0 sintético")
  for name in ("events_long.csv","zones_long.csv"):
   if not (root/name).is_file():raise RuntimeError("faltante: %s"%name)
  return pd.read_csv(root/"events_long.csv"),pd.read_csv(root/"zones_long.csv"),fmt
 if fmt=="parquet":
  for name in ("events_long.parquet","zones_long.parquet"):
   if not (root/name).is_file():raise RuntimeError("faltante: %s"%name)
  return pd.read_parquet(root/"events_long.parquet"),pd.read_parquet(root/"zones_long.parquet"),fmt
 raise RuntimeError("transport_format no permitido: %s"%fmt)
def main():
 report={"stage":"ZAMR1_00_VALIDATE_CONTRACT","expected_schema":EXPECTED_SCHEMA,"outcomes_accessed":False,"pnl_accessed":False,"holdout_accessed":False,"environment":{"python":sys.version.split()[0],"platform":platform.platform(),"pandas":pd.__version__,"internet_expected":False,"accelerator_expected":"None/CPU"}}
 try:
  root=find_input_root();report["input_root"]=str(root)
  missing=[n for n in BASE_REQUIRED if not (root/n).is_file()]
  if missing:raise RuntimeError("faltan archivos base: %r"%missing)
  report["hashes"]=verify_hashes(root)
  contract=json.loads((root/"contract.json").read_text("utf-8"));manifest=json.loads((root/"dataset_manifest.json").read_text("utf-8"))
  report["contract_schema"]=contract.get("schema_version")
  if report["contract_schema"]!=EXPECTED_SCHEMA:raise RuntimeError("schema incorrecto")
  events,zones,fmt=load_tables(root,manifest);report["transport_format"]=fmt
  sys.path.insert(0,str(root));module=importlib.import_module("structural_contract")
  validation=module.validate_structural_dataset(manifest=manifest,events=events,zones=zones,contract=contract)
  report["contract"]=validation.to_dict();report["counts"]={"events":len(events),"zones":len(zones),"sessions":len(set(events.session_key)|set(zones.session_key)),"bar_specs":sorted(set(events.bar_spec)|set(zones.bar_spec)),"indicators":sorted(set(events.indicator_id)|set(zones.indicator_id))}
  report["passed"]=bool(report["hashes"]["passed"] and report["contract"]["passed"])
 except Exception as e:report["passed"]=False;report["fatal_error"]="%s: %s"%(type(e).__name__,e)
 WORKING_ROOT.mkdir(parents=True,exist_ok=True);out=WORKING_ROOT/"contract_validation_report.json";out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8");print("Reporte:",out)
 if not report["passed"]:print("FAIL — no continuar con EDA, barridos ni modelos");return 1
 print("PASS — contrato ZAMR-1 verificado");print(json.dumps(report["counts"],indent=2,ensure_ascii=False));return 0
if __name__=="__main__":raise SystemExit(main())
