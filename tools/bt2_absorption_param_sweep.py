#!/usr/bin/env python3
"""Barrido target-free, reanudable y fail-closed de BigTrap2Absorption.

No calcula MFE, MAE, retornos, P&L, hit-rate ni d_hat. Procesa las 152 sesiones
para conservar el estado causal del abs_ring, pero reporta/selecciona solamente
las 133 de Puerta 1; las 19 selladas nunca aportan métricas.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

NORTH_STAR_SHA256 = "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"
DEFAULT_SPEC = REPO_ROOT / "specs" / "bt2_absorption_target_free_sweep_v1.json"
DEFAULT_SPLIT = REPO_ROOT / "specs" / "bt2_absorption_gate1_split_v1.json"
DEFAULT_CHAIN = REPO_ROOT / "docs" / "research" / "CADENA_FRONTMONTH_GC.json"
CONTRACTS = ("GC 02-26", "GC 04-26", "GC 06-26", "GC 08-26")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def clean_commit() -> str:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain"):
        raise RuntimeError("worktree dirty: la medición formal exige árbol limpio")
    return head


def config_id(params: dict[str, Any]) -> str:
    return "bt2a_" + digest(params)[:16]


def _validate_value(name: str, value: Any, rule: dict[str, Any]) -> None:
    kind = rule["type"]
    if kind == "bool":
        if type(value) is not bool: raise ValueError(f"{name}: se esperaba bool")
    elif kind == "enum":
        if value not in rule["choices"]: raise ValueError(f"{name}: enum inválido")
    elif kind == "int":
        if type(value) is not int or not rule["min"] <= value <= rule["max"]: raise ValueError(f"{name}: entero fuera de rango")
    elif kind == "float":
        if not isinstance(value, (int, float)) or type(value) is bool or not float(rule["min"]) <= float(value) <= float(rule["max"]): raise ValueError(f"{name}: número fuera de rango")
    else:
        raise ValueError(f"{name}: tipo PARAM_SPEC desconocido {kind}")


def validate_campaign_spec(spec: dict[str, Any], defaults: dict[str, Any], param_spec: dict[str, Any]) -> None:
    if spec.get("schema") != "bt2_absorption_target_free_sweep_v1": raise ValueError("schema inesperado")
    if spec["firewall"]["outcomes_opened"] is not False: raise ValueError("outcomes abiertos")
    roles = spec["parameter_space"]["roles"]
    flattened = [name for names in roles.values() for name in names]
    if len(flattened) != len(set(flattened)): raise ValueError("parámetro repetido entre roles")
    if set(flattened) != set(defaults) or set(defaults) != set(param_spec):
        raise ValueError(f"inventario no coincide: faltan={sorted(set(defaults)-set(flattened))}, sobran={sorted(set(flattened)-set(defaults))}")
    levels = spec["oat_levels"]
    if set(levels) != set(defaults): raise ValueError("oat_levels debe declarar 21 parámetros")
    for name, values in levels.items():
        if defaults[name] not in values: raise ValueError(f"{name}: baseline ausente")
        for value in values: _validate_value(name, value, param_spec[name])
    if spec["north_star_sha256"] != NORTH_STAR_SHA256: raise ValueError("hash NORTH_STAR incorrecto")


def _balanced_levels(values: list[Any], n: int, rng: np.random.Generator) -> list[Any]:
    out = (values * math.ceil(n / len(values)))[:n]
    order = rng.permutation(n)
    return [out[int(i)] for i in order]


def build_configs(spec: dict[str, Any], defaults: dict[str, Any], *, stage: str = "all") -> list[dict[str, Any]]:
    configs, seen = [], set()
    def add(params: dict[str, Any], source: str, axis: str | None = None) -> None:
        full = dict(defaults); full.update(params); cid = config_id(full)
        if cid not in seen:
            seen.add(cid); configs.append({"config_id": cid, "stage": source, "axis": axis, "params": full})
    add(dict(defaults), "headline")
    for name, values in spec["oat_levels"].items():
        for value in values:
            if value != defaults[name]: add({name: value}, "oat", name)
    if stage == "oat": return configs
    if stage != "all": raise ValueError("stage debe ser oat o all")
    design = spec["interaction_design"]; n = int(design["n_rows"]); axes = list(design["axes"])
    rng = np.random.default_rng(int(design["seed"]))
    columns = {name: _balanced_levels(list(spec["oat_levels"][name]), n, rng) for name in axes}
    for row in range(n):
        params = {name: columns[name][row] for name in axes}
        if not params.get("UseWickFilter", defaults["UseWickFilter"]): params["WickZonePct"] = defaults["WickZonePct"]
        if params["MinHistoryBuckets"] > params["AbsorptionLookback"]: params["MinHistoryBuckets"] = params["AbsorptionLookback"]
        add(params, "interaction")
    return configs


def derive_universe(chain: dict[str, Any], split: dict[str, Any]):
    base = split["universo_base"]
    assignment = {str(day): str(contract) for day, contract in chain["asignacion"].items() if base["rango"][0] <= str(day) <= base["rango"][1]}
    sessions = sorted(assignment); rule = split["regla_de_particion"]
    sealed = [day for i, day in enumerate(sessions) if i % 8 == 7]
    p1 = [day for i, day in enumerate(sessions) if i % 8 != 7]
    if len(sessions) != int(base["sesiones"]): raise ValueError("universo no reproduce 152")
    if len(p1) != int(rule["n_puerta1"]) or len(sealed) != int(rule["n_sellado"]): raise ValueError("split no reproduce 133/19")
    if set(p1) & set(sealed) or set(p1) | set(sealed) != set(sessions): raise AssertionError("partición inválida")
    return assignment, sessions, p1, sealed


def session_dates_from_ns(ts_ns: Iterable[int]) -> np.ndarray:
    from edgelab.bridge.bars import session_ids
    arr = np.asarray(list(ts_ns) if not isinstance(ts_ns, np.ndarray) else ts_ns, dtype=np.int64)
    if arr.size == 0: return np.asarray([], dtype="U8")
    days = session_ids(arr); unique = np.unique(days)
    mapping = {int(day): datetime.fromtimestamp(int(day) * 86400, tz=timezone.utc).strftime("%Y%m%d") for day in unique}
    return np.asarray([mapping[int(day)] for day in days], dtype="U8")


def _parse_iso_ns(text: str) -> int:
    return int(np.datetime64(text, "ns").astype(np.int64))


def _payload(text: str) -> dict[str, str]:
    out = {}
    for item in text.split(";"):
        if "=" in item:
            key, value = item.split("=", 1); out[key] = value
    return out


def _q(values: list[float], q: float) -> float | None:
    return float(np.quantile(np.asarray(values, dtype=float), q)) if values else None


def summarize_run(result: dict[str, Any], *, contract: str, report_sessions: set[str], assignment: dict[str, str], tick_size: float) -> dict[str, Any]:
    score_rows = []
    for line in result.get("events", []):
        if "|ABS_SCORE|" in line:
            data = _payload(line.split("|", 3)[3]); score_rows.append((_parse_iso_ns(data["t_start"]), data))
    score_sessions = session_dates_from_ns(np.asarray([row[0] for row in score_rows], dtype=np.int64))
    by_session = {}; buffers = defaultdict(lambda: {"score": [], "threshold": []})
    empty = lambda: {"n_buckets":0,"n_residual":0,"n_pass":0,"n_zones":0,"n_long":0,"n_short":0,"n_active":0,"n_invalidated":0,"n_expired":0,"touches_sum":0}
    for session, (_, data) in zip(score_sessions, score_rows):
        session = str(session)
        if session not in report_sessions or assignment.get(session) != contract: continue
        rec = by_session.setdefault(session, empty()); rec["n_buckets"] += 1
        rec["n_residual"] += int(data.get("residual", "False") == "True")
        rec["n_pass"] += int(data.get("a_pass", "False") == "True")
        buffers[session]["score"].append(float(data["a_score"]))
        if data.get("a_thr", "NaN") not in {"NaN","nan",""}: buffers[session]["threshold"].append(float(data["a_thr"]))
    zones = list(result.get("zones", []))
    zone_sessions = session_dates_from_ns(np.asarray([int(z["sig_ts"]) for z in zones], dtype=np.int64))
    event_keys = []; geometry = defaultdict(lambda: {"width":[],"rows":[],"frac":[],"volume":[]})
    for session, zone in zip(zone_sessions, zones):
        session = str(session)
        if session not in report_sessions or assignment.get(session) != contract: continue
        rec = by_session.setdefault(session, empty()); direction = str(zone["dir"])
        rec["n_zones"] += 1; rec["n_long"] += int(direction == "long"); rec["n_short"] += int(direction == "short")
        state = str(zone.get("state", "ACTIVE")).lower(); key = "n_" + state
        if key in rec: rec[key] += 1
        rec["touches_sum"] += int(zone.get("touches", 0))
        geometry[session]["width"].append(float(zone["hi"] - zone["lo"]) / tick_size)
        geometry[session]["rows"].append(float(zone["nrows"])); geometry[session]["frac"].append(float(zone["frac"])); geometry[session]["volume"].append(float(zone["vol"]))
        lo2 = int(round(float(zone["lo"]) / tick_size * 2)); hi2 = int(round(float(zone["hi"]) / tick_size * 2))
        event_keys.append(f"{contract}|{session}|{direction}|{int(zone['sig_ts'])}|{lo2}|{hi2}")
    for session, rec in by_session.items():
        score, threshold, geom = buffers[session]["score"], buffers[session]["threshold"], geometry[session]
        rec.update({"pass_rate":rec["n_pass"]/rec["n_buckets"] if rec["n_buckets"] else None,"score_p10":_q(score,.1),"score_p50":_q(score,.5),"score_p90":_q(score,.9),"threshold_p10":_q(threshold,.1),"threshold_p50":_q(threshold,.5),"threshold_p90":_q(threshold,.9),"zone_width_ticks_p50":_q(geom["width"],.5),"zone_rows_p50":_q(geom["rows"],.5),"trap_frac_p50":_q(geom["frac"],.5),"trap_volume_p50":_q(geom["volume"],.5)})
    return {"contract":contract,"sessions":dict(sorted(by_session.items())),"event_keys":sorted(set(event_keys))}


def exact_jaccard(a: set[str], b: set[str]) -> float:
    union = len(a | b); return len(a & b) / union if union else 1.0


def _decode_event(key: str):
    contract, session, direction, ts, lo2, hi2 = key.split("|")
    return contract, session, direction, int(ts), (int(lo2) + int(hi2)) / 4.0


def tolerant_jaccard(a: set[str], b: set[str], *, time_tolerance_seconds: float, price_tolerance_ticks: float) -> float:
    ga, gb = defaultdict(list), defaultdict(list)
    for key in a:
        c,s,d,ts,px=_decode_event(key); ga[(c,s,d)].append((ts,px))
    for key in b:
        c,s,d,ts,px=_decode_event(key); gb[(c,s,d)].append((ts,px))
    tol_ns=int(time_tolerance_seconds*1e9); matches=0
    for group in set(ga)|set(gb):
        left,right=sorted(ga.get(group,[])),sorted(gb.get(group,[])); used=set()
        for ts,px in left:
            best=best_cost=None
            for j,(ots,opx) in enumerate(right):
                if j in used or ots < ts-tol_ns: continue
                if ots > ts+tol_ns: break
                if abs(opx-px)>price_tolerance_ticks: continue
                cost=(abs(ots-ts),abs(opx-px))
                if best_cost is None or cost<best_cost: best,best_cost=j,cost
            if best is not None: used.add(best); matches+=1
    union=len(a)+len(b)-matches; return matches/union if union else 1.0


def _aggregate(records):
    sessions={}
    for record in records:
        overlap=set(sessions)&set(record["sessions"])
        if overlap: raise ValueError(f"sesiones duplicadas: {sorted(overlap)[:3]}")
        sessions.update(record["sessions"])
    fields=("n_buckets","n_residual","n_pass","n_zones","n_long","n_short","n_active","n_invalidated","n_expired","touches_sum")
    out={name:int(sum(int(row.get(name,0)) for row in sessions.values())) for name in fields}
    out["n_sessions"]=len(sessions); out["n_sessions_with_zones"]=sum(row.get("n_zones",0)>0 for row in sessions.values())
    for field in ("pass_rate","score_p50","threshold_p50","zone_width_ticks_p50","zone_rows_p50","trap_frac_p50","trap_volume_p50","n_zones"):
        values=[float(row[field]) for row in sessions.values() if row.get(field) is not None]
        for label,q in (("p10",.1),("p50",.5),("p90",.9)): out[f"{field}_session_{label}"]=_q(values,q)
    return {"aggregate":out,"sessions":dict(sorted(sessions.items()))}


def _partial_path(output, cfg, contract):
    return output/"partials"/f"{cfg['config_id']}__{contract.replace(' ','_')}.json"


def finalize(output, configs, input_manifest, *, head_start, spec, p1_sessions, contracts=CONTRACTS):
    by_config=defaultdict(list)
    contracts=tuple(contracts)
    partial_commits=set()
    for cfg in configs:
        for contract in contracts:
            path=_partial_path(output,cfg,contract)
            if not path.exists(): raise FileNotFoundError(path)
            record=load_json(path)
            if record["input_sha256"]!=input_manifest[contract]["sha256"] or record["config_id"]!=cfg["config_id"]: raise ValueError(f"partial incompatible: {path}")
            by_config[cfg["config_id"]].append(record["result"])
            partial_commits.add(record.get("code_commit","?"))
    summaries={}; events={}; session_rows=[]
    for cfg in configs:
        cid=cfg["config_id"]; aggregate=_aggregate(by_config[cid])
        got=set(aggregate["sessions"]); want=set(p1_sessions)
        if got!=want:
            faltan=sorted(want-got); sobran=sorted(got-want)
            raise ValueError(f"{cid}: cobertura de sesiones incorrecta: {len(got)}/{len(want)}; "
                             f"faltan {len(faltan)} {faltan[:5]}; sobran {len(sobran)} {sobran[:5]}")
        ev={key for part in by_config[cid] for key in part["event_keys"]}; events[cid]=ev
        summaries[cid]={"stage":cfg["stage"],"axis":cfg["axis"],"params":cfg["params"],**aggregate["aggregate"],"event_set_sha256":digest(sorted(ev)),"target_free_fingerprint":digest({"sessions":aggregate["sessions"],"events":sorted(ev)})}
        for session,metrics in aggregate["sessions"].items(): session_rows.append({"config_id":cid,"session":session,**metrics})
    headline=configs[0]["config_id"]; tol=spec["overlap"]
    for cid,summary in summaries.items():
        summary["exact_jaccard_vs_headline"]=exact_jaccard(events[headline],events[cid])
        summary["tolerant_jaccard_vs_headline"]=tolerant_jaccard(events[headline],events[cid],time_tolerance_seconds=float(tol["time_tolerance_seconds"]),price_tolerance_ticks=float(tol["price_tolerance_ticks"]))
    matrix={a:{b:exact_jaccard(events[a],events[b]) for b in events} for a in events}
    headline_fp=summaries[headline]["target_free_fingerprint"]
    identical=sorted({str(s["axis"]) for cid,s in summaries.items() if cid!=headline and s["stage"]=="oat" and s["target_free_fingerprint"]==headline_fp})
    head_end=_git("rev-parse","HEAD"); dirty_end=bool(_git("status","--porcelain"))
    # Procedencia de los parciales. "?" (commit desconocido) invalida igual que
    # una mezcla: no se puede afirmar de que codigo salio la medicion.
    provenance_ok = (len(partial_commits)==1 and "?" not in partial_commits
                     and sorted(partial_commits)==[head_start])
    if not provenance_ok:
        status="DIAGNOSTIC_REAGGREGATION_MIXED_CODE"
    elif head_end!=head_start or dirty_end:
        status="INVALID_PROVENANCE"
    elif set(contracts)==set(CONTRACTS):
        status="COMPLETE_TARGET_FREE"
    else:
        status="COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS"
    result={"schema":"bt2_absorption_target_free_sweep_result_v1","status":status,
        "promotion_eligible":bool(provenance_ok and head_end==head_start and not dirty_end
                                  and set(contracts)==set(CONTRACTS)),"target_free":True,"outcomes_opened":False,"sealed_outcomes_opened":False,"head_start":head_start,"head_end":head_end,
        "partials_code_commit":sorted(partial_commits),
        "partials_uniform_commit":len(partial_commits)==1,
        "finalize_matches_partials":provenance_ok,"worktree_clean_start":True,"worktree_clean_end":not dirty_end,"north_star_sha256":NORTH_STAR_SHA256,"contracts_measured":list(contracts),"contracts_omitted":[c for c in CONTRACTS if c not in contracts],"full_contract_coverage":set(contracts)==set(CONTRACTS),"n_configs":len(configs),"headline_config_id":headline,"input_manifest":input_manifest,"identical_to_headline_oat_axes":identical,"warning":"event overlap is descriptive; it is not an effective test count","summaries":summaries}
    _atomic_json(output/"summary.json",result); _atomic_json(output/"exact_overlap_matrix.json",matrix)
    with (output/"session_metrics.jsonl").open("w",encoding="utf-8") as handle:
        for row in session_rows: handle.write(json.dumps(row,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n")
    return result


def plan(spec_path, split_path, chain_path, output, stage):
    from edgelab.bridge.indicators.bigtrap2absorption import DEFAULTS, PARAM_SPEC
    spec,split,chain=load_json(spec_path),load_json(split_path),load_json(chain_path)
    validate_campaign_spec(spec,DEFAULTS,PARAM_SPEC); assignment,sessions,p1,sealed=derive_universe(chain,split); configs=build_configs(spec,DEFAULTS,stage=stage)
    expanded={"schema":"bt2_absorption_target_free_expanded_grid_v1","target_free":True,"outcomes_opened":False,"spec_sha256":file_sha256(spec_path),"stage":stage,"n_configs":len(configs),"configs":configs}; expanded["grid_sha256"]=digest(expanded)
    universe={"assignment":assignment,"all_152":sessions,"puerta1_133":p1,"sealed_19":sealed,"sealed_used_for_metrics":False,"sealed_target_free_history_processed":True}
    output.mkdir(parents=True,exist_ok=True); _atomic_json(output/"expanded_grid.json",expanded); _atomic_json(output/"universe.json",universe)
    return spec,configs,universe


def run_campaign(args):
    spec,configs,universe=plan(args.spec,args.split,args.chain,args.output,args.stage); head=clean_commit(); started=time.monotonic(); max_seconds=float(args.max_hours)*3600 if args.max_hours else None
    assignment=universe["assignment"]; report_sessions=set(universe["puerta1_133"]); expected_all=set(universe["all_152"]); input_manifest={}
    from tools.sweep_bigtrap2_tickframes import load_canonical_ticks
    from edgelab.bridge.indicators.bigtrap2absorption import run as run_abs
    contracts=tuple(getattr(args,'contracts',None) or CONTRACTS)
    for contract in contracts:
        path=args.data_dir/f"{contract}.Last.txt"
        if not path.exists(): raise FileNotFoundError(path)
        input_sha=file_sha256(path); ticks,*_=load_canonical_ticks(path,tick_size=float(args.tick_size),max_ticks=None); ticks.instrument="GC"; ticks.contract=contract; ticks.source=str(path)
        available=set(map(str,session_dates_from_ns(ticks.ts_ns))); expected_contract={d for d in expected_all if assignment[d]==contract}; missing=sorted(expected_contract-available)
        if missing: raise RuntimeError(f"{contract}: cobertura incompleta; faltan {missing}")
        input_manifest[contract]={"path":str(path),"sha256":input_sha,"bytes":path.stat().st_size,"n_ticks":len(ticks),"first_ts_ns":int(ticks.ts_ns[0]),"last_ts_ns":int(ticks.ts_ns[-1]),"expected_chain_sessions":len(expected_contract),"available_chain_sessions":len(expected_contract&available)}; _atomic_json(args.output/"input_manifest.json",input_manifest)
        for cfg in configs:
            partial=_partial_path(args.output,cfg,contract)
            if args.resume and partial.exists():
                prev=load_json(partial)
                if prev.get("input_sha256")==input_sha and prev.get("config_id")==cfg["config_id"] and prev.get("code_commit")==head: continue
            t0=time.monotonic(); result=run_abs(ticks,params=cfg["params"]); reduced=summarize_run(result,contract=contract,report_sessions=report_sessions,assignment=assignment,tick_size=float(args.tick_size))
            record={"schema":"bt2_absorption_target_free_partial_v1","target_free":True,"outcomes_opened":False,"config_id":cfg["config_id"],"params_sha256":digest(cfg["params"]),"contract":contract,"input_sha256":input_sha,"code_commit":head,"elapsed_seconds":time.monotonic()-t0,"result":reduced}; _atomic_json(partial,record)
            print(f"[{contract}] {cfg['config_id']} {cfg['stage']} zones={len(reduced['event_keys'])} {record['elapsed_seconds']:.1f}s",flush=True)
            if max_seconds and time.monotonic()-started>=max_seconds:
                _atomic_json(args.output/"run_status.json",{"status":"PAUSED_BY_MAX_HOURS","head_start":head,"elapsed_seconds":time.monotonic()-started,"outcomes_opened":False}); return 2
        del ticks
    result=finalize(args.output,configs,input_manifest,head_start=head,spec=spec,p1_sessions=[d for d in universe["puerta1_133"] if assignment[d] in contracts],contracts=contracts); _atomic_json(args.output/"run_status.json",{"status":result["status"],"head_start":head,"elapsed_seconds":time.monotonic()-started,"outcomes_opened":False})
    print(json.dumps({"status":result["status"],"n_configs":result["n_configs"],"identical_to_headline_oat_axes":result["identical_to_headline_oat_axes"],"outcomes_opened":False},indent=2,ensure_ascii=False)); return 0 if result["status"]=="COMPLETE_TARGET_FREE" else 3


def parser():
    out=argparse.ArgumentParser(description=__doc__); sub=out.add_subparsers(dest="command",required=True)
    for name in ("plan","run"):
        p=sub.add_parser(name); p.add_argument("--spec",type=Path,default=DEFAULT_SPEC); p.add_argument("--split",type=Path,default=DEFAULT_SPLIT); p.add_argument("--chain",type=Path,default=DEFAULT_CHAIN); p.add_argument("--output",type=Path,required=True); p.add_argument("--stage",choices=("oat","all"),default="all")
        if name=="run":
            p.add_argument("--data-dir",type=Path,required=True); p.add_argument("--tick-size",type=float,default=.10); p.add_argument("--resume",action="store_true"); p.add_argument("--max-hours",type=float,default=8.5); p.add_argument("--contracts",nargs="+",default=list(CONTRACTS),choices=list(CONTRACTS),help="Subconjunto de contratos a medir. Por defecto los cuatro. Un subconjunto marca el resultado como cobertura parcial y NUNCA como COMPLETE_TARGET_FREE.")
    return out


def main():
    args=parser().parse_args()
    if args.command=="plan":
        _,configs,universe=plan(args.spec,args.split,args.chain,args.output,args.stage); print(json.dumps({"status":"PLAN_TARGET_FREE","n_configs":len(configs),"n_all":len(universe["all_152"]),"n_report":len(universe["puerta1_133"]),"n_sealed":len(universe["sealed_19"]),"outcomes_opened":False},indent=2)); return
    raise SystemExit(run_campaign(args))


if __name__=="__main__": main()
