"""Fail-closed readiness, strict join, and interaction tools for BT2A Gate L2."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable
import numpy as np
import pandas as pd

STATES={"calm","normal","volatile","toxic"}
STATE_GROUP={"calm":"G-operable","normal":"G-operable","volatile":"G-stress","toxic":"G-stress"}
GROUPS=("G-operable","G-stress")

@dataclass(frozen=True)
class L2Readiness:
    n_labels:int; n_sessions:int; coverage:float
    rows_by_state:dict[str,int]; sessions_by_group:dict[str,int]
    monotone_source_rows:bool; state_group_mapping_ok:bool
    coverage_ok:bool; minimum_sessions_ok:bool; ready_for_outcomes:bool
    def to_dict(self): return asdict(self)

def _require(frame:pd.DataFrame,columns:Iterable[str],name:str):
    missing=sorted(set(columns)-set(frame.columns))
    if missing: raise ValueError(f"{name} missing columns: {missing}")

def validate_context_labels(contexts:pd.DataFrame,*,coverage_min=.99,minimum_sessions_per_group=40):
    required={"contract","cme_session","available_source_row","context_state","context_group","context_as_of_ok"}
    _require(contexts,required,"contexts")
    if contexts.empty: raise ValueError("contexts are empty")
    f=contexts.copy(); ok=f.context_as_of_ok.astype(bool); f.context_state=f.context_state.astype("string").str.lower(); f.context_group=f.context_group.astype("string")
    unknown=sorted(set(f.loc[ok,"context_state"].dropna())-STATES)
    if unknown: raise ValueError(f"unknown context states: {unknown}")
    if f.duplicated(["contract","cme_session","available_source_row"]).any(): raise ValueError("duplicate context publication coordinate")
    monotone=True
    for _,rows in f.groupby(["contract","cme_session"],sort=False):
        src=rows.available_source_row.to_numpy(dtype=np.int64)
        if len(src)>1 and np.any(src[1:]<=src[:-1]): monotone=False; break
    mapping=bool((f.loc[ok,"context_state"].map(STATE_GROUP)==f.loc[ok,"context_group"]).all())
    coverage=float(ok.mean())
    rows_by_state={s:int(((f.context_state==s)&ok).sum()) for s in sorted(STATES)}
    sessions_by_group={g:int(f.loc[(f.context_group==g)&ok,["contract","cme_session"]].drop_duplicates().shape[0]) for g in GROUPS}
    minimum=all(n>=int(minimum_sessions_per_group) for n in sessions_by_group.values()); coverage_ok=coverage>=float(coverage_min)
    return L2Readiness(len(f),int(f[["contract","cme_session"]].drop_duplicates().shape[0]),coverage,rows_by_state,sessions_by_group,monotone,mapping,coverage_ok,minimum,bool(monotone and mapping and coverage_ok and minimum))

def attach_context_strict(events:pd.DataFrame,contexts:pd.DataFrame):
    _require(events,{"contract","cme_session","event_source_row"},"events")
    _require(contexts,{"contract","cme_session","available_source_row","context_state","context_group","context_as_of_ok"},"contexts")
    if events.empty: return events.copy(),{"n_events":0,"n_as_of_ok":0,"coverage":0.}
    groups={(str(c),str(s)):g.sort_values("available_source_row",kind="stable").reset_index(drop=True) for (c,s),g in contexts.groupby(["contract","cme_session"],sort=False)}
    out=events.copy().reset_index(drop=True); states=[]; labels=[]; models=[]; available=[]; flags=[]; has_model="context_model_id" in contexts
    for row in out.itertuples(index=False):
        g=groups.get((str(row.contract),str(row.cme_session))); chosen=None
        if g is not None and len(g):
            src=g.available_source_row.to_numpy(dtype=np.int64); pos=int(np.searchsorted(src,int(row.event_source_row),side="left")-1)
            if pos>=0 and bool(g.iloc[pos].context_as_of_ok): chosen=g.iloc[pos]
        if chosen is None: states.append(None); labels.append(None); models.append(None); available.append(None); flags.append(False)
        else:
            states.append(str(chosen.context_state).lower()); labels.append(str(chosen.context_group)); models.append(chosen.context_model_id if has_model else None); available.append(int(chosen.available_source_row)); flags.append(True)
    out["context_state"]=states; out["context_group"]=labels; out["context_model_id"]=models; out["context_available_source_row"]=available; out["context_as_of_ok"]=flags
    n=int(sum(flags)); return out,{"n_events":len(out),"n_as_of_ok":n,"n_missing":len(out)-n,"coverage":n/len(out),"strict_inequality":True,"timestamp_fallback":False}

def context_width_correlation(joined:pd.DataFrame,*,width_column="zone_width_ticks"):
    _require(joined,{"context_group",width_column,"context_as_of_ok"},"joined")
    f=joined[joined.context_as_of_ok.astype(bool)&joined.context_group.isin(GROUPS)].copy(); numeric=pd.to_numeric(f[width_column],errors="coerce"); f=f[np.isfinite(numeric)]
    if len(f)<3 or f.context_group.nunique()<2: return {"n":len(f),"correlation":float("nan"),"passes":False}
    corr=float(np.corrcoef((f.context_group=="G-stress").astype(float),f[width_column].astype(float))[0,1]); return {"n":len(f),"correlation":corr,"passes":bool(abs(corr)<.2)}

def _deltas(rows,score_column,abs_arm,control_arm):
    cell=rows.groupby(["cme_session","context_group","arm"],sort=False)[score_column].mean().unstack("arm")
    if abs_arm not in cell or control_arm not in cell: raise ValueError("both arms required")
    cell=cell.dropna(subset=[abs_arm,control_arm]); cell["delta"]=cell[abs_arm]-cell[control_arm]; out={g:{} for g in GROUPS}
    for (session,group),row in cell.iterrows():
        if group in out: out[group][str(session)]=float(row.delta)
    return out

def context_interaction_test(rows:pd.DataFrame,*,score_column="score_fp",abs_arm="K_ABS",control_arm="N_RAND",minimum_sessions_per_group=40,replications=10000,seed=20260826):
    _require(rows,{"cme_session","context_group","arm",score_column},"interaction rows")
    d=_deltas(rows[rows.context_group.isin(GROUPS)],score_column,abs_arm,control_arm); counts={g:len(v) for g,v in d.items()}
    if not all(n>=minimum_sessions_per_group for n in counts.values()): return {"status":"CONTEXT_INCONCLUSIVE_LOW_POWER","n_sessions_by_group":counts,"minimum_sessions_per_group":minimum_sessions_per_group,"outcomes_interpreted":False}
    op=np.asarray(list(d["G-operable"].values())); st=np.asarray(list(d["G-stress"].values())); point=float(op.mean()-st.mean()); rng=np.random.default_rng(seed)
    draws=np.array([rng.choice(op,len(op),replace=True).mean()-rng.choice(st,len(st),replace=True).mean() for _ in range(replications)])
    pooled=np.r_[op,st]; labels=np.r_[np.zeros(len(op),dtype=np.int8),np.ones(len(st),dtype=np.int8)]; null=np.empty(replications)
    for b in range(replications):
        perm=rng.permutation(labels); null[b]=pooled[perm==0].mean()-pooled[perm==1].mean()
    return {"status":"CONTEXT_INTERACTION_ESTIMATED","estimand":"((K_ABS-N_RAND)|G-operable)-((K_ABS-N_RAND)|G-stress)","point":point,"lower":float(np.quantile(draws,.025)),"upper":float(np.quantile(draws,.975)),"p_two_sided":float((1+np.sum(np.abs(null)>=abs(point)))/(replications+1)),"n_sessions_by_group":counts,"minimum_sessions_per_group":minimum_sessions_per_group,"replications":replications,"seed":seed,"outcomes_interpreted":True,"edge_declared":False}

def validate_run_identity(manifest:dict,model:dict,report:dict,*,require_clean=True):
    ids=[x for x in (manifest.get("model_id"),model.get("model_id"),report.get("model_id")) if x is not None]; model_ok=bool(ids) and len(set(map(str,ids)))==1
    outcomes=manifest.get("CAMPAIGN_OUTCOMES_OPENED") is False; edge=manifest.get("EDGE_DECLARED") is False
    commits=bool(manifest.get("code_commit_start")) and manifest.get("code_commit_start")==manifest.get("code_commit_end")
    clean=(not manifest.get("dirty_start") and not manifest.get("dirty_end")) or not require_clean; status=manifest.get("status")=="COMPLETE_TARGET_FREE_CONTEXT_EXTRACTION"; ready=all((model_ok,outcomes,edge,commits,clean,status))
    return {"model_identity_ok":model_ok,"outcomes_closed":outcomes,"edge_not_declared":edge,"commit_stable":commits,"clean_worktree":bool(clean),"status_ok":status,"identity_ready":ready}
