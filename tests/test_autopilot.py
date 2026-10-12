import json
import subprocess
from pathlib import Path

import pytest

from edgelab.autopilot import analyze, guard, optimizer
from edgelab.autopilot.daemon import Autopilot
from edgelab.autopilot.executor import FakeExecutor
from edgelab.autopilot.fdr import AlphaInvesting, holm_rejections
from edgelab.autopilot.ledger import RunLedger
from edgelab.autopilot.selector import rank
from edgelab.autopilot.spec import RunSpec

REPO = Path(__file__).resolve().parents[1]


def _git(repo, *a):
    subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"; (r / "tools").mkdir(parents=True); (r / "docs").mkdir()
    (r / "tools/s.py").write_text("print(1)\n"); (r / "docs/pre.md").write_text("prereg\n")
    _git(r, "init", "-q"); _git(r, "config", "user.email", "a@b"); _git(r, "config", "user.name", "t"); _git(r, "add", "-A"); _git(r, "commit", "-qm", "x")
    return r


def spec(rid="r1", fam="F", grp="G", needs=("ES:2025-07-01:2026-09-30",), **k):
    return RunSpec(run_id=rid, kind="study", family=fam, group=grp, script="tools/s.py", prereg="docs/pre.md", n_trials=4, needs=list(needs), **k)


def test_guards(repo):
    assert guard.all_checks(spec(), repo=repo) == []
    assert any("holdout" in e for e in guard.all_checks(spec(needs=("ES:2026-09-01:2026-10-05",)), repo=repo))
    (repo / "docs/pre.md").write_text("cambiado\n"); assert any("sin commitear" in e for e in guard.all_checks(spec(), repo=repo))
    assert any("internet" in e for e in guard.all_checks(spec(internet=True), repo=repo))
    assert guard.all_checks(spec(internet=True), allow_internet={"tools/s.py"}, repo=repo)[0].startswith("pre-registro")   # (el cambio local de arriba sigue bloqueando)


def test_protected_manifest(repo, tmp_path):
    m = tmp_path / "p.json"; m.write_text(json.dumps(guard.snapshot_protected(["docs/pre.md"], repo))); assert guard.check_protected(m, repo) == []
    (repo / "docs/pre.md").write_text("x"); assert "modificado" in guard.check_protected(m, repo)[0]


def test_alpha_investing_never_negative_and_recharges(tmp_path):
    a = AlphaInvesting(tmp_path / "a.json"); w0 = a.wealth
    for i in range(200):
        a.bid(f"c{i}", 10); a.settle(f"c{i}", 0); assert a.wealth >= 0
    assert a.wealth < w0
    w = a.wealth; a.bid("hit", 5); a.settle("hit", 1); assert a.wealth == pytest.approx(w + a.payout)
    with pytest.raises(KeyError): a.settle("no-apostada", 0)


def test_holm():
    assert holm_rejections([0.001, 0.2, 0.9], 0.05, 3) == 1
    assert holm_rejections([0.03, 0.04], 0.05, 2) == 0 and holm_rejections([0.01, 0.012], 0.05, 2) == 2


def test_selector_prefers_hit_arms_and_skips_seen(tmp_path):
    led = RunLedger(tmp_path / "l.sqlite"); good, bad = spec("g", grp="A"), spec("b", grp="B")
    outs = [("F", "A", True)] * 6 + [("F", "B", False)] * 6; wins = sum(rank([good, bad], outs, led, seed=s)[0][1].run_id == "g" for s in range(200))
    assert wins > 150
    led.add(good, "h"); assert [x[1].run_id for x in rank([good, bad], outs, led, seed=1)] == ["b"]


def test_optimizer_accepts_identical_faster_and_rejects_others():
    import time
    slow = lambda: (time.sleep(0.02), {"x": 1.0000000000001, "seconds": 5})[1]
    fast = lambda: {"x": 1.0, "seconds": 1}
    assert optimizer.compare(slow, fast)["decision"] == "ACEPTAR"
    assert "distinta" in optimizer.compare(slow, lambda: {"x": 2.0})["reason"]
    assert "ganancia" in optimizer.compare(fast, fast)["reason"]


def _cfg(tmp_path, **k):
    return dict(mode="execute", max_concurrent=1, max_per_day=5, result_files={"F": "R.json"}, **k)


class Reg:
    def __init__(self): self.rows = []
    def ensure(self, cid, fam, n, note=""): self.rows.append((cid, fam, n))


def test_autopilot_cycle(repo, tmp_path):
    res = {"r1": {"results": [{"source": "S", "tests": {"a": {"p": 0.0001, "p_holm": 0.001, "evaluable": True, "obs": 1.0}, "b": {"p": 0.5, "evaluable": True, "obs": 0}}}]}}
    ex, reg = FakeExecutor(res), Reg(); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=reg)
    t1 = ap.tick([spec()]); assert t1["launched"][0] == "r1" and reg.rows == [("autopilot/r1", "F", 4)] and ex.launched == ["r1"]
    t2 = ap.tick([spec()]); assert t2["closed"] == [("r1", True)] and ap.ledger.outcomes() == [("F", "G", True)] and ap.fdr.wealth > 0.05
    assert ap.tick([spec()])["event"] == "tick"                                       # el mismo spec_hash no se relanza
    assert ex.launched == ["r1"]


def test_autopilot_propose_mode_does_not_launch(repo, tmp_path):
    ex = FakeExecutor({}); ap = Autopilot(tmp_path / "root", ex, dict(_cfg(tmp_path), mode="propose"), repo=repo, registry=Reg())
    t = ap.tick([spec()]); assert t["proposed"][0] == "r1" and ex.launched == []


def test_autopilot_failure_kill_switch_and_protected(repo, tmp_path):
    ex = FakeExecutor({}, fail={"r1"}); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=Reg())
    ap.tick([spec()]); assert ap.tick([spec("r2", grp="H")])["closed"] == [("r1", "FAILED")]
    (tmp_path / "root/PAUSE").write_text(""); assert ap.tick([spec("r3", grp="Z")])["event"] == "paused"
    (tmp_path / "root/PAUSE").unlink(); m = tmp_path / "p.json"; m.write_text(json.dumps(guard.snapshot_protected(["docs/pre.md"], repo)))
    ap.cfg["protected"] = str(m); (repo / "docs/pre.md").write_text("tocado"); assert ap.tick([spec("r4", grp="Y")])["event"] == "STOP_protected_changed"


def test_analyze_reads_real_result_files():
    ou = json.load(open(REPO / "docs/research/ou_20261012/OU1_RESULTADOS.json")); d = analyze.decide(ou, 0.05, 42)
    assert d["n_evaluable"] == 42 and d["hit"] is True and d["rejections"] >= 3
    gex = json.load(open(REPO / "docs/research/GEX1_USA500_2018_COMPLETO_20261006.json")); assert analyze.decide(gex, 0.05, 12)["hit"]


def test_brain_sink_records_hit_and_miss(tmp_path):
    from edgelab.autopilot.brain import brain_sink
    s = brain_sink(tmp_path / "h.jsonl"); top = [{"test": "a", "p": 0.001}]
    s(spec("h1"), dict(hit=True, rejections=1, family_alpha=0.02, n_planned=4, top=top))
    s(spec("m1"), dict(hit=False, rejections=0, family_alpha=0.02, n_planned=4, top=top)); s(spec("h1"), dict(hit=True, rejections=1, family_alpha=0.02, n_planned=4, top=top))   # idempotente
    from edgelab.edge_brain import DurableHippocampus
    h = DurableHippocampus(tmp_path / "h.jsonl"); assert {"AUTOPILOT-h1", "AUTOPILOT-m1"} <= set(h.memory.episodes)


def test_generator_scores_learns_and_drafts_match_env(repo, tmp_path):
    from edgelab.autopilot import evidence
    from edgelab.autopilot.generate import draft_prereg, generate, load_json, research_gaps, to_runspec
    cs = generate([]); ids = [c.cid for c in cs]; assert {"IDM-1", "SLOT-1", "OU-2", "GEX-2", "AVCL-2"} <= set(ids) and cs[0].score >= cs[-1].score
    lits = load_json("config/autopilot/literature_leads.json"); c = next(x for x in cs if x.cid == "IDM-1"); assert len(c.pro) == 2 and len(c.contra) == 1     # procedencia a favor y en contra
    base = c.score; boosted = next(x for x in generate([("IDM", "MULTI", True)] * 4) if x.cid == "IDM-1").score; assert boosted > base                          # aprende de aciertos de su familia
    # el borrador contiene la configuración textual: el guard acepta el RunSpec una vez committeado
    rs = to_runspec(c); (repo / "docs/research/autopilot/drafts").mkdir(parents=True); (repo / rs["prereg"]).write_text(draft_prereg(c, lits)); (repo / "tools/study_slot_effect.py").write_text("x=1\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "d"); assert guard.all_checks(RunSpec.from_dict(rs), allow_internet={rs["script"]}, repo=repo) == []
    bad = dict(rs, env={"STUDY_CFG": '{"otra": "config"}'}); assert any("no figura textualmente" in e for e in guard.all_checks(RunSpec.from_dict(bad), allow_internet={rs["script"]}, repo=repo))
    assert research_gaps(c)["public_query_reviewed"] is False
    # evidencia viva: un fracaso degrada la pista y consume la muestra; la candidata deja de proponerse
    rt = tmp_path / "ev.jsonl"; spec_ = RunSpec.from_dict(rs); evidence.record_outcome(rt, spec_, dict(hit=False, rejections=0, top=[]), evidence.current_states(rt))
    assert "IDM-1" not in [x.cid for x in generate([], runtime=rt)]
    assert next(e for e in evidence.apply_runtime(load_json("config/autopilot/evidence_seed.json"), rt)["entries"] if e["id"] == "GEX_I2D_ROD_LH")["status"] == "FAILED_REPLICATION"


def test_benchmark_kind_spends_no_alpha_and_is_not_counted(repo, tmp_path):
    ex = FakeExecutor({"bm": {}}); reg = Reg(); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=reg)
    b = RunSpec(run_id="bm", kind="benchmark", family="INFRA", group="X", script="tools/s.py", prereg="docs/pre.md", n_trials=0, needs=[]); w = ap.fdr.wealth
    ap.tick([b]); assert reg.rows == [] and "bm" not in ap.fdr.state["open"]; assert ap.tick([b])["closed"] == [("bm", "BENCHMARK")] and ap.fdr.wealth == w


def test_concurrent_bids_never_overdraw(tmp_path):
    a = AlphaInvesting(tmp_path / "a.json", spend_fraction=1.0)
    for i in range(30): a.bid(f"c{i}", 5)
    assert sum(b["alpha"] / (1 - b["alpha"]) for b in a.state["open"].values()) <= a.wealth + 1e-12


def test_missing_protected_manifest_stops(repo, tmp_path):
    assert "ausente" in guard.check_protected(tmp_path / "nada.json", repo)[0]


def test_hit_is_attributed_per_lead_and_new_leads_are_opened(tmp_path):
    from edgelab.autopilot import evidence
    sp = RunSpec(run_id="x", kind="study", family="IDM", group="G", script="tools/s.py", prereg="docs/pre.md", n_trials=3, needs=["ES:2025-07-01:2026-09-30"],
                 origin={"LEAD": {"sample": "s1", "tests": ["idm/ES_spot"]}})
    res = {"results_flat": [{"test": "idm/ES_spot", "p": 0.4, "evaluable": True}, {"test": "idm/GC", "p": 0.0001, "evaluable": True}, {"test": "idm/NQ", "p": 0.6, "evaluable": True}]}
    d = analyze.decide(res, 0.05, 3); assert d["hit"]                                            # la campaña tuvo un hallazgo...
    recs = evidence.record_outcome(tmp_path / "e.jsonl", sp, d, {}, result=res)
    lead = next(r for r in recs if r["evidence_id"] == "LEAD"); assert lead["hit"] is False and lead["status"] == "FAILED_REPLICATION"   # ...pero NO es de la pista de origen
    new = next(r for r in recs if r["evidence_id"] == "x:idm/GC"); assert new["status"] == "WEAK_LEAD" and new["new_entry"]["unused_samples"] == ["new_data_after_holdout"]
