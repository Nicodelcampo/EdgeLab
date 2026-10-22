import json, subprocess, time
from pathlib import Path
from edgelab.autopilot import auditoria
from edgelab.autopilot.ledger import RunLedger
from edgelab.autopilot.spec import RunSpec

ENV = {"STUDY_CFG": json.dumps({"x": 1}, sort_keys=True)}


def _repo(tmp):
    r = tmp / "repo"; (r / "tools").mkdir(parents=True); (r / "docs").mkdir()
    (r / "tools/s.py").write_text("print(1)\n")
    (r / "docs/pre.md").write_text(f"# pre\n```json\n{ENV['STUDY_CFG']}\n```\n")
    for a in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"]):
        subprocess.run(["git", *a], cwd=r, check=True)
    return r


def _spec(rid, needs="ES:2025-01-01:2025-06-30"):
    return RunSpec(run_id=rid, kind="study", family="SLOT", group="ES", script="tools/s.py", prereg="docs/pre.md", n_trials=4, needs=[needs], env=ENV)


def _ledger(tmp, specs_res):
    led = RunLedger(tmp / "runs.sqlite")
    for sp, res in specs_res:
        led.add(sp, "h-" + sp.run_id); led.finish(sp.run_id, "ANALYZED", res)
    return led


class Fake:
    def __init__(self, aud="CONFORME", grav="baja"): self.aud, self.grav, self.roles = aud, grav, []
    def call(self, role, payload):
        self.roles.append(role)
        if role == "auditor": return {"status": "OK", "output": {"veredicto": self.aud, "desvios": [], "razon": "x"}}
        return {"status": "OK", "output": {"explicacion_alternativa": "rebote bid-ask", "tipo": "artefacto", "prueba_refutadora": "mid", "gravedad": self.grav}}


DEC_OK = {"hit": False, "n_planned": 4, "n_evaluable": 4, "top": [], "invalid_p_tests": []}
DEC_HIT = {"hit": True, "n_planned": 4, "n_evaluable": 4, "rejections": 1, "top": [{"test": "a", "p": .001}], "invalid_p_tests": []}


def test_mecanico_sin_llm_y_no_reaudita(tmp_path):
    r = _repo(tmp_path); led = _ledger(tmp_path, [(_spec("a"), DEC_OK)]); log = tmp_path / "aud.jsonl"
    assert auditoria.auditar(led, r, log) == [("a", "MECANICO_OK_SIN_LLM")]
    assert auditoria.auditar(led, r, log) == []                                    # ya auditada


def test_pruebas_no_planeadas_bloquean_sin_gastar_llm(tmp_path):
    r = _repo(tmp_path); f = Fake()
    led = _ledger(tmp_path, [(_spec("b"), dict(DEC_OK, n_evaluable=9))])
    assert auditoria.auditar(led, r, tmp_path / "aud.jsonl", runner=f) == [("b", "BLOQUEADA")] and f.roles == []


def test_hit_pasa_por_auditor_y_abogado(tmp_path):
    r = _repo(tmp_path); f = Fake(grav="alta")
    led = _ledger(tmp_path, [(_spec("c"), DEC_HIT)]); log = tmp_path / "aud.jsonl"
    assert auditoria.auditar(led, r, log, runner=f) == [("c", "EN_DUDA")] and f.roles == ["auditor", "abogado"]
    assert auditoria.estados(log) == {"c": "EN_DUDA"}


def test_sospecha_de_fuga_bloquea(tmp_path):
    r = _repo(tmp_path); led = _ledger(tmp_path, [(_spec("d"), DEC_OK)])
    assert auditoria.auditar(led, r, tmp_path / "aud.jsonl", runner=Fake(aud="SOSPECHA_FUGA")) == [("d", "BLOQUEADA")]


def test_prereg_cambiado_despues_del_lanzamiento(tmp_path):
    r = _repo(tmp_path); led = _ledger(tmp_path, [(_spec("e"), DEC_OK)])
    led.db.execute("UPDATE runs SET launched_at=? WHERE run_id='e'", (time.time() - 3600,)); led.db.commit()
    time.sleep(1.1); (r / "docs/pre.md").write_text((r / "docs/pre.md").read_text(encoding="utf-8") + "cambio\n")
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "y"], cwd=r, check=True)
    row = None
    auditoria.auditar(led, r, tmp_path / "aud.jsonl")
    row = json.loads((tmp_path / "aud.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert row["estado"] == "BLOQUEADA" and any("después del lanzamiento" in m for m in row["mecanicos"])
