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
    bad = dict(rs, env={"STUDY_CFG": '{"otra": "config"}'}); assert any("estructuralmente" in e for e in guard.all_checks(RunSpec.from_dict(bad), allow_internet={rs["script"]}, repo=repo))
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


def test_idm2_candidate_is_wired_to_the_gc_lead():
    from edgelab.autopilot.generate import generate, to_runspec
    c = next(x for x in generate([]) if x.cid == "IDM-2"); rs = to_runspec(c)
    assert rs["origin"]["GC_LH_MOMENTUM"]["tests"] == ["idmj/GC_spot_old"] and any(n.startswith("GC:") for n in rs["needs"])        # la referencia (GC futuro) también necesita datos
    assert c.cfg["n_planned"] == 8 and "GC" in c.cfg["reference_sources"] and "GC" not in c.cfg["sources"]                        # la referencia no cuenta en Holm
    assert any(x.cid == "WAIT-GC_LH_MOMENTUM" and x.score == 0.0 for x in generate([])) and any(x.cid == "DATA-METALS" for x in generate([]))


def test_mandate_pass_probability_and_viability():
    from edgelab.autopilot import mandate
    rng = __import__("numpy").random.default_rng(1); rules = mandate.load()["challenge_reference"]
    flat = rng.normal(0, 150, 300); good = rng.normal(40, 150, 300)
    assert mandate.pass_probability(flat, rules, 800)["p_pass"] < mandate.pass_probability(good, rules, 800)["p_pass"]          # más edge, más probabilidad de pase
    ok = dict(daily_pnl_usd=list(rng.normal(60, 120, 250)), quarterly_pnl_usd=[2000, 1500, 1800, 900, 2200], trades_per_month=30, net_pnl_stress_usd=9000, corr_with_portfolio=[0.1], max_drawdown_usd=1500)
    v = mandate.viability(ok); assert "no_depende_de_5_dias" in v["criteria"] and isinstance(v["useful"], bool)
    bad = dict(ok, quarterly_pnl_usd=[9000, -500, -300, -200], corr_with_portfolio=[0.8], trades_per_month=3)                      # un trimestre, correlada, poco frecuente
    vb = mandate.viability(bad); assert not vb["useful"] and {"trimestres_positivos", "diversifica", "frecuencia"} <= set(vb["failed"])
    assert mandate.tier(True, True, v if v["useful"] else None) in ("A", "B") and mandate.tier(True, False, None) == "C" and mandate.tier(True, True, vb) == "B" and mandate.tier(True, True, vb, artifact=True) == "D"


def test_utility_weight_changes_ranking():
    from edgelab.autopilot.generate import Candidate, score
    base = dict(cid="X", title="t", rule="r", gap_kind="NO_PRIOR_EVIDENCE", evidence=[], power=0.5, est_seconds=600, group="G", family="F")
    a = score(Candidate(utility_class="tradeable", **base), [], {}); b = score(Candidate(utility_class="info", **base), [], {}); assert a.score > b.score


def test_fetch_failure_does_not_crash_the_cycle(repo, tmp_path):
    class Boom(FakeExecutor):
        def fetch(self, handle, filename): raise FileNotFoundError("nada")
    ap = Autopilot(tmp_path / "root", Boom({}), _cfg(tmp_path), repo=repo, registry=Reg()); ap.tick([spec()])
    t = ap.tick([spec("r2", grp="Z")]); assert t["blocked"] and ap.ledger.running()                  # sigue RUNNING, se reintentará


def test_challenge_simulator_models_consistency_lock_and_no_time_limit():
    import numpy as np
    from edgelab.autopilot import mandate
    r = mandate.load()["challenge_reference"]; assert r["max_days"] is None and r["consistency_max_best_day_share"] == 0.5 and r["lock_profit_usd"] == 2100
    steady = mandate.pass_probability(np.full(50, 100.0), r, 100, block=1); assert steady["p_pass"] == 1.0 and steady["median_days_to_pass"] == 30      # +100 por día: 3.000 en 30 días, consistencia 1/30
    rng = np.random.default_rng(3); weak = rng.normal(15, 130, 500)
    base = mandate.pass_probability(weak, r, 800); strict = mandate.pass_probability(weak, dict(r, consistency_max_best_day_share=0.15), 800)
    assert 0.0 < base["p_pass"] < 1.0 and strict["p_pass"] <= base["p_pass"] + 0.03 and strict["median_days_to_pass"] >= base["median_days_to_pass"]        # consistencia más dura: pasa menos o más tarde
    assert mandate.pass_probability(weak, dict(r, lock_profit_usd=None), 800)["p_pass"] <= base["p_pass"] + 0.03                                          # sin bloqueo del piso no mejora
    assert mandate.pass_probability(np.full(50, -10.0), r, 50)["p_fail_dd"] == 1.0                                                                        # solo pérdidas: rompe el piso


def test_lucid_catalog_loads_and_is_marked_unverified():
    from edgelab.propfirm.rules import load_catalog
    c = {x.plan: x for x in load_catalog(REPO / "config/propfirms/catalogo_lucid_50k.json")}
    f = c["LucidFlex_50K"]; assert (f.profit_target, f.max_loss, f.consistency_cap, f.lock_at_profit) == (3000, 2000, 0.5, 2100) and not f.verified and f.flat_by.startswith("16:45")
    assert c["LucidPro_50K"].daily_loss_limit == 1200 and c["LucidPro_50K"].funded_consistency_cap == 0.4


def test_universe_thresholds_and_matching():
    from edgelab.autopilot import universe as U
    cat = [r for r in U.catalog() if r.plan == "LucidFlex_50K"]; assert cat and all(r.eval_fee > 0 for r in U.catalog())      # sin cuota no hay umbral válido
    cheap = U.threshold_usd(cat[0], 250, 0.02, n_paths=800, eval_days=200); costly = U.threshold_usd(cat[0], 250, 0.15, n_paths=800, eval_days=200)
    assert 0 < cheap["z_bruto_min"] < costly["z_bruto_min"] < 1                                                              # más costo relativo ⇒ más ventaja requerida
    assert U.cost_ratio("GC", 40) > U.cost_ratio("GC", 160) and "6E" in U.INSTRUMENTS and "GC" in U.INSTRUMENTS
    m = U.best_accounts("GC", 40, 0.30, cat, n_paths=800); assert m and m[0]["ev"] > 0                                      # con z bruto alto la cuenta deja EV positivo


def test_thresholds_prioritise_but_never_exclude():
    from edgelab.autopilot.generate import Candidate, score, FEAS_FLOOR
    base = dict(cid="X", title="t", rule="r", gap_kind="NO_PRIOR_EVIDENCE", evidence=[], power=0.5, est_seconds=600, group="G", family="F")
    easy = score(Candidate(required_rho=0.05, **base), [], {}); hard = score(Candidate(required_rho=2.0, **base), [], {})
    assert hard.score > 0 and hard.score_parts["feasibility"] == FEAS_FLOOR and easy.score > hard.score >= 0.25 * easy.score - 1e-12              # prioridad más baja, nunca cero


def test_scan1_candidate_is_ready_and_counts_cells_not_just_tests():
    from edgelab.autopilot.generate import generate, to_runspec
    c = next(x for x in generate([]) if x.cid == "SCAN-1"); rs = to_runspec(c)
    assert c.template == "slot_scan" and rs["n_trials"] == 495 and rs["n_tests_holm"] == 20 and rs["kind"] == "study" and not rs["internet"]
    assert {"ES", "GC", "NQ", "YM", "6E"} <= {n.split(":")[0] for n in rs["needs"]} and rs["origin"]["UNIVERSE_SCAN_1"]["sample"] == "scan_1"


def test_adding_a_spec_field_does_not_relaunch_old_specs_and_run_ids_are_unique(repo, tmp_path):
    ex = FakeExecutor({}); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=Reg()); a = spec("same")
    ap.tick([a]); ap.tick([a]); assert ex.launched == ["same"]
    renamed_hash = spec("same", grp="OTRO"); ap.tick([renamed_hash]); assert ex.launched == ["same"]            # mismo run_id con otro hash: no se relanza ni revienta
    assert spec("x").spec_hash() == RunSpec(**{k: v for k, v in spec("x").__dict__.items() if k != "n_tests_holm"}).spec_hash()


def test_scan_hit_requires_replication():
    res = {"results_flat": [{"test": "scan/A/max_disc", "p": 0.0005, "evaluable": True}, {"test": "scan/A/rep/c1", "p": 0.6, "evaluable": True}, {"test": "scan/A/rep/c2", "p": 0.4, "evaluable": True}]}
    d = analyze.decide(res, 0.02, 3); assert d["hit"] is False and d["rejections"] == 0 and d["discovery_only_passes"] == ["scan/A/max_disc"]
    ok = {"results_flat": res["results_flat"][:1] + [{"test": "scan/A/rep/c1", "p": 0.0001, "evaluable": True}]}; assert analyze.decide(ok, 0.02, 3)["hit"] is True


def test_pnl1_candidate_needs_futures_for_rules():
    from edgelab.autopilot.generate import generate, to_runspec
    c = next(x for x in generate([]) if x.cid == "PNL-1"); rs = to_runspec(c)
    assert {n.split(":")[0] for n in rs["needs"]} == {"GC", "ES"} and rs["n_trials"] == 5 and rs["n_tests_holm"] == 2 and rs["origin"]["PNL_EVAL_1"]["tests"] == ["pnl/"]


# --- endurecimiento tras la revisión del otro agente (sondas sobre fdr/analyze/daemon/guard) ---
def test_decide_rejects_nonfinite_and_out_of_range_p():
    r = dict(results_flat=[dict(test="a", p=-0.5, evaluable=True), dict(test="b", p=float("nan"), evaluable=True), dict(test="c", p=1.7, evaluable=True), dict(test="d", p=0.3, evaluable=True)])
    d = analyze.decide(r, 0.05, 4); assert d["hit"] is False and d["rejections"] == 0 and d["n_evaluable"] == 1 and d["n_planned"] == 4 and set(d["invalid_p_tests"]) == {"a", "b", "c"}
    from edgelab.autopilot.fdr import holm_rejections
    assert holm_rejections([-1.0, float("nan"), 0.001], 0.05, 3) == 1                                  # el p inválido no cuenta y el denominador planeado se mantiene


def test_alpha_investing_two_stale_objects_cannot_overspend(tmp_path):
    from edgelab.autopilot.fdr import AlphaInvesting
    a, b = AlphaInvesting(tmp_path / "a.json"), AlphaInvesting(tmp_path / "a.json")                    # dos procesos con estado inicial obsoleto
    a.bid("c1", 4); b.bid("c2", 4)
    s = AlphaInvesting(tmp_path / "a.json"); assert set(s.state["open"]) == {"c1", "c2"}              # no se pierde ninguna reserva
    cost = sum(x["alpha"] / (1 - x["alpha"]) for x in s.state["open"].values()); assert cost <= s.wealth + 1e-12
    assert not (tmp_path / "a.json.tmp").exists()                                                       # escritura atómica: sin residuo
    a.release("c1", "prueba"); assert "c1" not in AlphaInvesting(tmp_path / "a.json").state["open"] and AlphaInvesting(tmp_path / "a.json").wealth == 0.05


def test_failed_run_releases_bid_and_crash_between_steps_is_reconciled(repo, tmp_path):
    ex = FakeExecutor({}, fail={"r1"}); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=Reg())
    ap.tick([spec()]); assert "r1" in ap.fdr.state["open"]; ap.tick([spec("r2", grp="H")]); assert "r1" not in ap.fdr.state["open"] and ap.fdr.wealth == 0.05          # ERROR devuelve la apuesta
    # caída entre «cerrar libro» y «liquidar alfa»: la corrida queda ANALYZED con apuesta abierta; el siguiente ciclo la liquida con el resultado guardado
    ap.ledger.finish("r2", "ANALYZED", dict(hit=False, rejections=0)); assert "r2" in ap.fdr.state["open"]
    t = ap.tick([]); assert ("r2", "settled") in t.get("reconciled", []) and "r2" not in ap.fdr.state["open"]


def test_launch_write_ahead_and_uncertain_send_is_never_resent(repo, tmp_path):
    from edgelab.autopilot.executor import LaunchRejected
    class Boom(FakeExecutor):
        def __init__(self, exc): super().__init__({}); self.exc = exc; self.calls = 0
        def launch(self, s): self.calls += 1; raise self.exc
    ex = Boom(TimeoutError("sin respuesta")); ap = Autopilot(tmp_path / "root", ex, _cfg(tmp_path), repo=repo, registry=Reg())
    t = ap.tick([spec()]); assert ap.ledger.uncertain() == ["r1"] and "envío incierto" in t["blocked"][0][1][0] and "r1" in ap.fdr.state["open"]
    ap.tick([spec()]); ap.tick([spec()]); assert ex.calls == 1                                         # ni reenvía ni libera la apuesta sola
    ex2 = Boom(LaunchRejected("rechazado")); ap2 = Autopilot(tmp_path / "root2", ex2, _cfg(tmp_path), repo=repo, registry=Reg())
    ap2.tick([spec()]); assert ap2.ledger.uncertain() == [] and "r1" not in ap2.fdr.state["open"]       # rechazo explícito: sin corrida, apuesta devuelta, puede reintentarse
    ap2.tick([spec()]); assert ex2.calls == 2


def test_only_one_controller_per_state_dir(repo, tmp_path):
    import fcntl
    ap = Autopilot(tmp_path / "root", FakeExecutor({}), _cfg(tmp_path), repo=repo, registry=Reg())
    with open(tmp_path / "root" / ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX); assert ap.tick([spec()])["event"] == "locked_by_other_controller"


def test_env_binding_is_structural(repo):
    import json as J
    cfg = {"mode": "x", "D": [10, 20]}; (repo / "docs/pre.md").write_text("cfg:\n```\n" + J.dumps(cfg, sort_keys=True) + "\n```\n"); _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "p")
    ok = spec(env={"CFG": J.dumps({"D": [10, 20], "mode": "x"})}); assert guard.check_env_in_prereg(ok, repo) == []                         # mismo contenido, otro orden de claves
    sneaky = spec(env={"CFG": J.dumps({"mode": "x", "D": [10, 20], "extra": 1})}); assert guard.check_env_in_prereg(sneaky, repo)           # antes pasaba por substring si el texto contenía los valores
    sub = spec(env={"CFG": '"mode"'}); assert guard.check_env_in_prereg(sub, repo) == []                                                      # valores no JSON: texto
