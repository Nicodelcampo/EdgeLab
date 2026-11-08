import json
from pathlib import Path
from edgelab.autopilot import guard, holdout_apertura as H
from edgelab.autopilot.ledger import RunLedger
from edgelab.autopilot.spec import RunSpec

ENV = {"STUDY_CFG": "{\"x\": 1}"}


def _spec(rid, kind="study", needs="ES:2025-07-01:2026-03-31", env=ENV, origin=None, family="SLOT"):
    return RunSpec(run_id=rid, kind=kind, family=family, group="ES", script="tools/s.py", prereg="docs/p.md", n_trials=1,
                   needs=[needs], env=dict(env), origin=origin or {})


def _setup(tmp, hit=True, audit="CONFORME"):
    led = RunLedger(tmp / "runs.sqlite"); c = _spec("cand")
    led.add(c, "h"); led.finish("cand", "ANALYZED", {"hit": hit})
    (tmp / "auditorias.jsonl").write_text(json.dumps({"run_id": "cand", "estado": audit}) + "\n")
    return led


def test_guard_separa_corridas_normales_y_apertura():
    assert guard.check_holdout(_spec("a", needs="ES:2026-09-01:2026-10-15"))                       # normal: bloqueada
    assert guard.check_holdout(_spec("b", kind="holdout", needs="ES:2026-10-01:2026-12-31")) == []  # apertura: sólo holdout
    assert guard.check_holdout(_spec("c", kind="holdout", needs="ES:2026-09-01:2026-12-31"))       # apertura que mezcla desarrollo


def test_apertura_valida_y_una_sola_por_familia(tmp_path):
    led = _setup(tmp_path)
    s = _spec("ho", kind="holdout", needs="ES:2026-10-01:2026-12-31", origin={"candidato": "cand"})
    assert H.requisitos(s, led, tmp_path) == []
    H.registrar(s, tmp_path, "abc")
    assert any("única apertura" in e for e in H.requisitos(_spec("ho2", kind="holdout", needs="ES:2026-10-01:2026-12-31", origin={"candidato": "cand"}), led, tmp_path))


def test_apertura_rechazada_sin_hallazgo_auditado_o_con_regla_cambiada(tmp_path):
    led = _setup(tmp_path, hit=False, audit="EN_DUDA")
    s = _spec("ho", kind="holdout", needs="ES:2026-10-01:2026-12-31", env={"STUDY_CFG": "{\"x\": 2}"}, origin={"candidato": "cand"})
    errs = " ".join(H.requisitos(s, led, tmp_path))
    assert "hit=false" in errs and "CONFORME" in errs and "congelada" in errs
    assert H.requisitos(_spec("ho3", kind="holdout", needs="ES:2026-10-01:2026-12-31"), led, tmp_path)   # sin candidato


def test_apertura_exploratoria(tmp_path):
    """Modo exploratorio (Nico, 2026-11-08): sin candidato confirmado, pero con p de desarrollo, combinación y pre-registro; sigue
    una por familia y sólo holdout; deshabilitado por defecto."""
    from types import SimpleNamespace
    from edgelab.autopilot import holdout_apertura as H
    led = SimpleNamespace(db=SimpleNamespace(execute=lambda *a: SimpleNamespace(fetchone=lambda: None)))
    def sp(**o):
        return SimpleNamespace(origin=dict(modo="exploratoria", **o), prereg="docs/x.md", family="F", needs=[f"NQ:{H.HOLDOUT_FIRST_TRADE_DATE}:2026-11-07"],
                               env={}, run_id="r1")
    assert H.requisitos(sp(p_desarrollo=0.37, combinacion="fisher"), led, tmp_path) != []                       # no habilitado
    assert H.requisitos(sp(p_desarrollo=0.37, combinacion="fisher"), led, tmp_path, permitir_exploratoria=True) == []
    assert H.requisitos(sp(combinacion="fisher"), led, tmp_path, permitir_exploratoria=True)                      # falta p
    malo = sp(p_desarrollo=0.37, combinacion="fisher"); malo.needs = ["NQ:2026-01-01:2026-11-07"]
    assert H.requisitos(malo, led, tmp_path, permitir_exploratoria=True)                                         # mezcla desarrollo
    H.registrar(sp(p_desarrollo=0.37, combinacion="fisher"), tmp_path)
    assert any("única apertura" in x for x in H.requisitos(sp(p_desarrollo=0.37, combinacion="fisher"), led, tmp_path, permitir_exploratoria=True))
