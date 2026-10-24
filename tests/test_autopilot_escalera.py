"""Regla de decisión escalera_v1 dentro del ciclo autónomo (tamiz FDR + LORD++ en réplica), detrás del interruptor
`decision: escalera_v1`. Sin el interruptor el ciclo no cambia (lo cubren tests/test_autopilot.py)."""
import json
import subprocess
import sys
import types

import pytest

if "fcntl" not in sys.modules:                         # el ciclo usa fcntl (Debian); en Windows se sustituye por un lock nulo
    try:
        import fcntl  # noqa: F401
    except ImportError:
        f = types.ModuleType("fcntl"); f.LOCK_EX, f.LOCK_NB = 2, 4; f.flock = lambda *a, **k: None; sys.modules["fcntl"] = f

from edgelab.autopilot import holdout_apertura as H  # noqa: E402
from edgelab.autopilot.confirmacion import Confirmacion  # noqa: E402
from edgelab.autopilot.daemon import Autopilot  # noqa: E402
from edgelab.autopilot.executor import FakeExecutor  # noqa: E402
from edgelab.autopilot.spec import RunSpec  # noqa: E402


class Reg:
    def __init__(self): self.rows = []
    def ensure(self, cid, fam, n, note=""): self.rows.append((cid, fam, n))


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"; (r / "tools").mkdir(parents=True); (r / "docs").mkdir()
    (r / "tools/s.py").write_text("print(1)\n"); (r / "docs/pre.md").write_text("prereg\n")
    for a in (("init", "-q"), ("config", "user.email", "a@b"), ("config", "user.name", "t"), ("add", "-A"), ("commit", "-qm", "x")):
        subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)
    return r


def spec(rid="r1"):
    return RunSpec(run_id=rid, kind="study", family="F", group="G", script="tools/s.py", prereg="docs/pre.md", n_trials=200, needs=["ES:2025-07-01:2026-09-30"])


def _res(p_rep):
    flat = [dict(test=f"G/c{i}/disc", p=(1e-4 if i < 3 else 0.5), evaluable=True) for i in range(100)]
    flat += [dict(test=f"G/c{i}/rep/x", p=p, evaluable=True) for i, p in enumerate(p_rep)]
    return dict(results_flat=flat)


def test_ciclo_confirma_con_lordpp_aunque_el_alfa_viejo_este_agotado(repo, tmp_path):
    root = tmp_path / "root"; root.mkdir()
    (root / "alpha.json").write_text(json.dumps(dict(wealth=0.0025, history=[], open={})))      # el estado real del 15-oct
    ex, reg = FakeExecutor({"r1": _res([0.001, 0.4, 0.6])}), Reg()
    cfg = dict(mode="execute", max_concurrent=1, max_per_day=5, result_files={"F": "R.json"}, decision="escalera_v1", evidence_runtime=str(root / "ev.jsonl"))
    ap = Autopilot(root, ex, cfg, repo=repo, registry=reg)
    t1 = ap.tick([spec()]); assert t1["launched"][0] == "r1" and reg.rows == [("autopilot/r1", "F", 200)]
    assert ap.fdr.state["open"] == {}                                                          # no apuesta alfa
    t2 = ap.tick([spec()]); assert t2["closed"] == [("r1", True)]
    d = json.loads(ap.ledger.db.execute("SELECT result FROM runs WHERE run_id='r1'").fetchone()[0])
    assert d["regla"] == "escalera_v1" and [c["test"] for c in d["confirmadas"]] == ["G/c0/rep/x"] and len(d["nominadas"]) == 3
    assert ap.fdr.wealth == pytest.approx(0.0025)                                              # fdr.py y su estado, intactos
    ev = [json.loads(l) for l in (root / "ev.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(r["status"] == "WEAK_LEAD" for r in ev) == 3                                    # las nominadas abren pistas
    assert ap.status()["decision"] == "escalera_v1"


def test_decision_idempotente_no_gasta_dos_veces_la_secuencia(tmp_path):
    c = Confirmacion(tmp_path); a = c.decidir("r", _res([0.001]), 101); t = c.state["lord"]["t"]
    assert Confirmacion(tmp_path).decidir("r", _res([0.9]), 101) == a and Confirmacion(tmp_path).state["lord"]["t"] == t


def test_solo_descubrimiento_no_es_acierto_y_ruido_no_confirma(tmp_path):
    c = Confirmacion(tmp_path)
    assert c.decidir("a", _res([]), 100)["hit"] is False
    assert c.decidir("b", _res([0.3, 0.5, 0.7]), 103)["hit"] is False


def test_apertura_del_holdout_exige_veredicto_de_la_escalera(tmp_path):
    from edgelab.autopilot.ledger import RunLedger
    env = {"STUDY_CFG": "{\"x\": 1}"}
    mk = lambda rid, **k: RunSpec(run_id=rid, kind=k.get("kind", "study"), family="SLOT", group="ES", script="tools/s.py", prereg="docs/p.md", n_trials=1,
                                  needs=[k.get("needs", "ES:2025-07-01:2026-03-31")], env=dict(env), origin=k.get("origin", {}))
    led = RunLedger(tmp_path / "runs.sqlite"); led.add(mk("cand"), "h"); led.finish("cand", "ANALYZED", {"hit": True, "escalera": {"estado": "SIN_POTENCIA"}})
    (tmp_path / "auditorias.jsonl").write_text(json.dumps({"run_id": "cand", "estado": "CONFORME"}) + "\n")
    s = mk("ho", kind="holdout", needs="ES:2026-10-01:2026-12-31", origin={"candidato": "cand"})
    assert H.requisitos(s, led, tmp_path) == []                                                # regla vieja: no mira la escalera
    assert any("LISTA_PARA_HOLDOUT" in e for e in H.requisitos(s, led, tmp_path, exigir_escalera=True))
    t2 = tmp_path / "b"; t2.mkdir(); led2 = RunLedger(t2 / "runs.sqlite")
    led2.add(mk("cand"), "h"); led2.finish("cand", "ANALYZED", {"hit": True, "escalera": {"estado": "LISTA_PARA_HOLDOUT"}})
    (t2 / "auditorias.jsonl").write_text(json.dumps({"run_id": "cand", "estado": "CONFORME"}) + "\n")
    assert H.requisitos(s, led2, t2, exigir_escalera=True) == []


def test_activacion_en_dos_pasos_prueba_sobre_copia_y_aplica_con_respaldo(tmp_path, monkeypatch):
    import importlib.util
    spec_ = importlib.util.spec_from_file_location("activar", __import__("pathlib").Path(__file__).resolve().parents[1] / "tools/autopilot_activar_escalera.py")
    act = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(act)
    root = tmp_path / "estado"; root.mkdir(); (root / "alpha.json").write_text(json.dumps(dict(wealth=0.0025, history=[], open={})))
    cand = tmp_path / "candidates.json"; cand.write_text("[]")
    cfg_p = tmp_path / "autopilot.json"; cfg_p.write_text(json.dumps(dict(mode="execute", result_files={})), encoding="utf-8")
    import edgelab.autopilot.executor as exm
    monkeypatch.setattr(exm, "KaggleExecutor", lambda owner: FakeExecutor({}))
    r = act.prueba(cfg_p, root, cand)
    assert r["status"]["decision"] == "escalera_v1" and r["status"]["mode"] == "propose"
    assert sorted(p.name for p in root.iterdir()) == ["alpha.json"]                     # el estado real no se tocó
    assert json.loads(cfg_p.read_text(encoding="utf-8")) == dict(mode="execute", result_files={})
    a = act.aplicar(cfg_p); c = json.loads(cfg_p.read_text(encoding="utf-8"))
    assert a["aplicado"] and c["decision"] == "escalera_v1" and c["mode"] == "execute" and (tmp_path / "autopilot.json.antes_escalera").exists()
    assert act.aplicar(cfg_p) == dict(ya_estaba=True)


def test_familia_nueva_del_agente_usa_el_archivo_estandar(repo, tmp_path):
    """Una familia que inventó el agente no está en result_files de /etc: antes quedaba en fetch_failed para siempre."""
    class Ex(FakeExecutor):
        def fetch(self, handle, filename):
            self.pedidos = getattr(self, "pedidos", []) + [filename]; return super().fetch(handle, filename)
    root = tmp_path / "root"; root.mkdir()
    ex = Ex({"r1": _res([0.001])})
    cfg = dict(mode="execute", max_concurrent=1, max_per_day=5, result_files={"OTRA": "X.json"}, decision="escalera_v1")
    ap = Autopilot(root, ex, cfg, repo=repo, registry=Reg())
    ap.tick([spec()]); t2 = ap.tick([spec()])
    assert t2["closed"] == [("r1", True)] and ex.pedidos == ["STUDY_RESULTS.json"]
