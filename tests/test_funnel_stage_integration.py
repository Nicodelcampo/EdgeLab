"""Real CPU/Numba/Parquet integration with invented arrays only."""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pyarrow.parquet as pq
import pytest
from edgelab.funnel.isolation import stage_window
from edgelab.funnel.runner import FunnelRunner
from edgelab.funnel.screen import cheap_screen, iter_screen_batches
from edgelab.funnel.splits import make_splits, validate_split, load_frozen_split, to_dict
from edgelab.funnel.ledger import FunnelLedger

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("independent_funnel_oracle",ROOT/"tools/verify_funnel_cpu_gpu.py")
parity=importlib.util.module_from_spec(spec);spec.loader.exec_module(parity)


def inputs():
    n=24*8
    return dict(trade_dates=np.repeat(np.arange(20260101,20260125,dtype=np.int32),8),
                signal_idx=np.arange(n,dtype=np.int64),signal_dir=np.ones(n,np.int8),
                high=np.full(n,110,np.float64),low=np.full(n,100,np.float64),
                bid_open=np.full(n,99,np.float64),ask_open=np.full(n,101,np.float64))


def configs(direction="normal",count=1):
    return [dict(candidate_id=f"synthetic-{i}",family_id="synthetic",direction=direction,sl_ticks=3+i,tp_ticks=4+i) for i in range(count)]


def run_case(tmp_path,name,raw=None,cs=None,hold=2):
    raw=raw or inputs();split=make_splits(raw["trade_dates"])
    runner=FunnelRunner(**raw,configs=cs or configs(),out_dir=tmp_path/name,backend="cpu",frozen_split=split)
    return runner,runner.run_e1_e3(min_trades=1,max_hold_bars=hold)


def test_real_runner_parquet_ledger_and_stage_routes(tmp_path,monkeypatch):
    import edgelab.funnel.screen as screen
    seen=[];original=screen._screen_inputs
    def checked(*args,**kw):
        seen.append(np.asarray(args[2]).copy())
        return original(*args,**kw)
    monkeypatch.setattr(screen,"_screen_inputs",checked)
    runner,result=run_case(tmp_path,"first",cs=configs(count=2))
    assert seen and all(len(x) in (96,48) and np.all(x==110) for x in seen)
    assert result["isolation"]["boundary_excluded"]=={"D0":2,"D1":2}
    assert result["multiplicity"]["status"]=="COMPLETE_DIAGNOSTIC_ONLY"
    assert not result["multiplicity"]["promotion_allowed"] and not result["promotion_allowed"]
    assert result["runner_d2_outcomes_read"] is False
    assert result["holdout_opened"] is None  # upstream access must not be guessed
    for artifact in (result["trial_artifact"],result["survivor_artifact"]):
        path=Path(artifact["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==artifact["sha256"]
        assert pq.read_table(path).num_rows==2
    assert FunnelLedger(runner.out/"edge_brain.jsonl").verify()["valid"]
    assert json.loads((runner.out/"summary.json").read_text())["split_source"]=="FROZEN_SUPPLIED"


def test_d2_poison_does_not_change_stage_results_or_artifacts(tmp_path):
    raw=inputs();_,before=run_case(tmp_path,"before",raw=raw)
    split=make_splits(raw["trade_dates"]);d2=np.isin(raw["trade_dates"],split.d2_dates)
    for key in ("high","low","bid_open","ask_open"):raw[key][d2]=np.nan
    _,after=run_case(tmp_path,"after",raw=raw)
    for key in ("headlines","tested","survivors","multiplicity","isolation"):
        assert before[key]==after[key]
    for key in ("trial_artifact","survivor_artifact"):
        assert before[key]["sha256"]==after[key]["sha256"]


def test_empty_eligible_stage_has_explicit_counts(tmp_path):
    _,result=run_case(tmp_path,"none",hold=10_000)
    assert result["survivors"]==0
    assert result["isolation"]["eligible_signals"]=={"D0":0,"D1":0}
    assert result["devices"]=={}
    assert result["device"] is None


def test_reuse_does_not_overwrite_prior_evidence(tmp_path):
    runner,_=run_case(tmp_path,"once")
    path=runner.out/"summary.json";before=path.read_bytes()
    with pytest.raises(FileExistsError):runner.run_e1_e3(min_trades=1,max_hold_bars=2)
    assert path.read_bytes()==before


@pytest.mark.parametrize("direction",["inverse","reverse"])
def test_direction_aliases_are_exactly_inverted(tmp_path,direction):
    _,normal=run_case(tmp_path,"normal")
    _,inverse=run_case(tmp_path,direction,cs=configs(direction))
    assert normal["headlines"][0]["d0_mean"]==3.5
    rows=pq.read_table(inverse["trial_artifact"]["path"]).to_pylist()
    assert rows[0]["d0_mean"]==-3.5
    assert inverse["survivors"]==0


@pytest.mark.parametrize("backend",["auto","gpu"])
def test_runner_gpu_route_is_closed_without_silent_fallback(tmp_path,backend):
    with pytest.raises(RuntimeError,match="CPU-only"):
        FunnelRunner(**inputs(),configs=configs(),out_dir=tmp_path/"blocked",backend=backend)
    assert not (tmp_path/"blocked").exists()


def test_split_hash_is_not_permission_to_open_d2(tmp_path):
    runner=FunnelRunner(**inputs(),configs=configs(),out_dir=tmp_path/"no")
    with pytest.raises(PermissionError):runner.d2_mask(unlock_token=runner.split.split_hash)


def test_changed_split_labels_and_hash_fail_closed(tmp_path):
    td=inputs()["trade_dates"];split=make_splits(td)
    with pytest.raises(ValueError,match="hash"):validate_split(replace(split,split_hash="0"*64),td)
    with pytest.raises(ValueError,match="coverage"):validate_split(split,td[:-8])
    with pytest.raises(ValueError,match="overlap"):validate_split(replace(split,d1_dates=split.d0_dates),td)
    with pytest.raises(PermissionError):validate_split(replace(split,d2_opened=True),td)
    path=tmp_path/"split.json";path.write_text(json.dumps(to_dict(split)))
    assert validate_split(load_frozen_split(path),td)==split


def small_arrays():
    return (np.array([0,2],np.int64),np.array([1,-1],np.int8),
            np.array([100,100,112,100,100,100]),np.array([100,99,99,88,100,100]),
            np.full(6,99),np.full(6,101),np.array([10,10,10]),np.array([10,11,12]))


def test_public_batcher_has_real_float64_budget(monkeypatch):
    import edgelab.funnel.screen as screen
    calls=[];original=screen._screen_inputs
    def counted(*a,**kw):calls.append(1);return original(*a,**kw)
    monkeypatch.setattr(screen,"_screen_inputs",counted)
    batches=list(iter_screen_batches(*small_arrays(),max_hold_bars=2,backend="cpu",max_matrix_bytes=16))
    assert [(a,b) for a,b,_,_ in batches]==[(0,1),(1,2),(2,3)]
    assert all(x.dtype==np.float64 and x.nbytes<=16 for _,_,x,_ in batches)
    assert len(calls)==1  # do not reread/validate the same stage prices for each config batch
    with pytest.raises(ValueError,match="one float64 column"):
        list(iter_screen_batches(*small_arrays(),backend="cpu",max_matrix_bytes=8))


@pytest.mark.parametrize("name,raw",list(parity.cases()))
def test_cpu_matches_independent_oracle(name,raw):
    sig,d,h,l,bo,ao,sl,tp,m,hold,fee=raw
    result,dev=cheap_screen(sig,d,h,l,bo,ao,sl,tp,m,hold,fee,"cpu")
    np.testing.assert_allclose(result,parity.oracle(*raw),rtol=0,atol=1e-10,equal_nan=True)
    assert dev.backend=="cpu"


@pytest.mark.parametrize("kind",["fractional_signal","fractional_price","out_of_range_signal","crossed_quote","overflow","invalid_direction"])
def test_unsafe_numerical_inputs_rejected(kind):
    args=list(small_arrays())
    if kind=="fractional_signal":args[0]=np.array([0.5,2.])
    if kind=="fractional_price":args[2]=args[2].astype(float)+.25
    if kind=="out_of_range_signal":args[0]=np.array([-2,2])
    if kind=="crossed_quote":args[4]=np.full(6,102)
    if kind=="overflow":args[4]=np.full(6,np.iinfo(np.int32).max)
    if kind=="invalid_direction":args[1]=np.array([0,1])
    with pytest.raises(ValueError):cheap_screen(*args,backend="cpu")


def test_stage_horizons_and_reindexing():
    td=np.repeat([1,2,3],5)
    w=stage_window(td,np.arange(15),[2],1)
    assert w.signal_positions.tolist()==[4,5,6,7]
    assert w.local_signals(np.arange(15)).tolist()==[-1,0,1,2]
    with pytest.raises(ValueError):stage_window([1,2,3],[0],[1,3],1)
    with pytest.raises(ValueError):stage_window(td,[.5],[1],1)
    with pytest.raises(ValueError):stage_window(td,[0],[1],True)
    with pytest.raises(ValueError):stage_window(td,[0],[1],10**30)


def test_cli_requires_split_before_any_array_load(tmp_path):
    p=subprocess.run([sys.executable,str(ROOT/"tools/run_funnel_arrays.py"),"--arrays",str(tmp_path/"missing"),"--registry",str(tmp_path/"missing.json"),"--out",str(tmp_path/"out")],capture_output=True,text=True)
    assert p.returncode==2 and "--split" in p.stderr
    assert not (tmp_path/"out").exists()


def test_cli_frozen_split_and_real_synthetic_arrays(tmp_path):
    raw=inputs();arrays=tmp_path/"arrays";arrays.mkdir()
    names={"trade_dates":"trade_date","signal_idx":"signal_bar_idx","signal_dir":"signal_dir","high":"high_ticks","low":"low_ticks","bid_open":"bid_open_ticks","ask_open":"ask_open_ticks"}
    for key,name in names.items():np.save(arrays/f"{name}.npy",raw[key],allow_pickle=False)
    split=tmp_path/"split.json";split.write_text(json.dumps(to_dict(make_splits(raw["trade_dates"]))))
    registry=tmp_path/"registry.json";registry.write_text(json.dumps(configs()))
    command=[sys.executable,str(ROOT/"tools/run_funnel_arrays.py"),"--arrays",str(arrays),"--registry",str(registry),"--split",str(split),"--out",str(tmp_path/"cli"),"--max-hold-bars","2"]
    proc=subprocess.run(command,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    result=json.loads(proc.stdout)
    assert result["split_source"]=="FROZEN_SUPPLIED"
    assert result["runner_d2_outcomes_read"] is False
    assert result["promotion_allowed"] is False


def test_auto_gpu_rejects_overflow_before_cupy_import(monkeypatch):
    from types import SimpleNamespace
    import edgelab.funnel.screen as screen
    monkeypatch.setattr(screen,"detect_device",lambda *a:SimpleNamespace(backend="gpu"))
    with pytest.raises(ValueError,match="GPU launch/index"):
        cheap_screen(*small_arrays(),max_hold_bars=np.iinfo(np.int32).max-2,backend="auto")


def test_cli_changed_days_fail_before_price_file_open(tmp_path):
    raw=inputs();arrays=tmp_path/"metadata-only";arrays.mkdir()
    np.save(arrays/"trade_date.npy",raw["trade_dates"][:-8],allow_pickle=False)
    split=tmp_path/"split.json";split.write_text(json.dumps(to_dict(make_splits(raw["trade_dates"]))))
    proc=subprocess.run([sys.executable,str(ROOT/"tools/run_funnel_arrays.py"),"--arrays",str(arrays),"--registry",str(tmp_path/"not-opened.json"),"--split",str(split),"--out",str(tmp_path/"out")],capture_output=True,text=True)
    assert proc.returncode!=0 and "coverage differs" in proc.stderr
    assert "FileNotFoundError" not in proc.stderr
    assert not (tmp_path/"out").exists()
