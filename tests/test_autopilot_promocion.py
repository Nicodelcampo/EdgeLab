"""Promoción automática: repo git temporal, revisor falso, sin red."""
import json, subprocess
from pathlib import Path
from edgelab.autopilot.generate import Candidate
from edgelab.autopilot.promocion import promover_auto

CFG = {"inst": "ES", "desde": "2025-07-01", "hasta": "2026-03-31", "x": 1, "mov_esperado_ticks": 20}


def repo(tmp_path):
    r = tmp_path / "repo"; (r / "tools").mkdir(parents=True)
    (r / "tools/study.py").write_text("print('ok')\n")
    for a in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        subprocess.run(["git", *a], cwd=r, check=True)
    return r


def cand(cid, template="slot", trials=10, title=None):
    return Candidate(cid=cid, title=title or f"estudio {cid} de reversión horaria", rule="R1", gap_kind="NO_PRIOR_EVIDENCE", evidence=["E1"],
                     template=template, cfg=CFG, n_trials=trials, why="pista débil en muestra no usada", score=0.3)


def to_rs(c):
    if not c.template: return None
    return dict(run_id=c.cid.lower(), kind="study", family="SLOT", group="MES", script="tools/study.py", prereg=f"docs/research/autopilot/drafts/{c.cid}.md",
                n_trials=c.n_trials, needs=["ES:2025-07-01:2026-03-31"], env={"STUDY_CFG": json.dumps(c.cfg, sort_keys=True)})


def draft(c):
    return f"# {c.cid}\n\nPre-registro.\n\n```json\n{json.dumps(c.cfg, sort_keys=True)}\n```\n"


class Rev:
    def __init__(self, decision): self.decision, self.calls = decision, 0
    def call(self, role, payload):
        assert role == "revisor" and "borrador" in payload; self.calls += 1
        return {"status": "OK", "output": {"decision": self.decision, "razon": "x", "regla_nueva": ""}}


def run(tmp_path, cands, decision="PROMOTE", **kw):
    r = repo(tmp_path); cp = tmp_path / "candidates.json"; log = tmp_path / "promociones.jsonl"; rev = Rev(decision)
    out = promover_auto(cands, draft_fn=draft, to_runspec=to_rs, runner=rev, repo=r, candidates_path=cp, log_path=log, **kw)
    rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []   # el jsonl se escribe en UTF-8; sin esto falla en Windows
    return out, r, cp, rows, rev


def test_promote_commits_prereg_before_and_adds_candidate(tmp_path):
    out, r, cp, rows, _ = run(tmp_path, [cand("SLOT-9")])
    assert out == [("SLOT-9", "PROMOVIDA")]
    assert json.loads(cp.read_text())[0]["run_id"] == "slot-9"
    msg = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=r, capture_output=True, text=True).stdout
    assert "SLOT-9" in msg and rows[-1]["prereg_commit"]

def test_reviewer_kill_blocks_and_nothing_is_committed(tmp_path):
    out, r, cp, rows, _ = run(tmp_path, [cand("SLOT-9")], decision="KILL")
    assert out == [("SLOT-9", "RECHAZADA_REVISOR")] and not cp.exists()
    assert not (r / "docs/research/autopilot/drafts/SLOT-9.md").exists()

def test_mechanical_checks_run_before_any_llm_call(tmp_path):
    out, _, _, rows, rev = run(tmp_path, [cand("NS-1", template=None), cand("BIG-1", trials=5000),
                                          cand("RET-1", title="bigtrap2 imán zona")], retiradas=["bigtrap2 imán zona revisita"])
    assert [o[1] for o in out] == ["RECHAZADA_MECANICO"] * 3 and rev.calls == 0
    assert any("NEEDS_SCRIPT" in m for m in rows[0]["motivos"])

def test_one_promotion_per_cycle(tmp_path):
    out, *_ = run(tmp_path, [cand("A-1"), cand("B-1")])
    assert out == [("A-1", "PROMOVIDA")]

def test_guards_still_apply_after_promotion(tmp_path):
    bad = cand("HO-1"); bad.cfg = dict(CFG, hasta="2026-10-15")
    def to_rs_holdout(c):
        d = to_rs(c); d["needs"] = ["ES:2025-07-01:2026-10-15"]; return d
    r = repo(tmp_path); cp = tmp_path / "c.json"; log = tmp_path / "p.jsonl"
    out = promover_auto([bad], draft_fn=draft, to_runspec=to_rs_holdout, runner=Rev("PROMOTE"), repo=r, candidates_path=cp, log_path=log)
    assert out == [("HO-1", "RECHAZADA_GUARDAS")] and not cp.exists()


def test_friction_blocks_where_friction_likely_wins_and_orders_by_it(tmp_path):
    caro = cand("MNQ-1"); caro.cfg = dict(CFG, inst="MNQ", mov_esperado_ticks=12)        # 12 / 7,91 = 1,5 < 3
    sin = cand("YM-1"); sin.cfg = dict(CFG, inst="YM")                                   # sin fricción medida
    info = cand("INFO-1"); info.cfg = dict(CFG, inst="MNQ", mov_esperado_ticks=5); info.utility_class = "info"
    out, _, _, rows, rev = run(tmp_path, [caro, sin, info], max_por_ciclo=3)
    d = dict(out)
    assert d["MNQ-1"] == "RECHAZADA_MECANICO" and d["YM-1"] == "RECHAZADA_MECANICO" and d["INFO-1"] == "PROMOVIDA"
    motivos = {r["cid"]: r.get("motivos", []) for r in rows}
    assert any("fricción" in m for m in motivos["MNQ-1"]) and any("no se transporta" in m for m in motivos["YM-1"])

def test_low_friction_candidate_goes_first(tmp_path):
    barato = cand("ES-1"); barato.score = 0.2                                             # ratio 20/3,55 = 5,6
    caro = cand("NQ-1"); caro.score = 0.3; caro.cfg = dict(CFG, inst="NQ", mov_esperado_ticks=9)   # ratio 1,46: peso 0,49
    out, *_ = run(tmp_path, [caro, barato])
    assert out[0] == ("ES-1", "PROMOVIDA")


def test_tecnica_sin_paridad_rechaza_en_mecanico(tmp_path):
    c = cand("T-1"); c.cfg = dict(CFG, tecnicas=["encoder_tri_franja_film"])
    ok = cand("T-2"); ok.cfg = dict(CFG, tecnicas=["corredores_densidad_hp007"])
    out, _, _, rows, _ = run(tmp_path, [c, ok], max_por_ciclo=2)
    d = dict(out); assert d["T-1"] == "RECHAZADA_MECANICO" and d["T-2"] == "PROMOVIDA"
    assert (tmp_path / "herramientas.jsonl").exists()
