"""Rol programador: zonas por ruta, controles obligatorios, tests, aplicación al checkout y rechazo de reglas."""
import json, subprocess, sys
from pathlib import Path

import pytest

from edgelab.autopilot import programador as P


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"; (r / "tests").mkdir(parents=True); (r / "edgelab/research").mkdir(parents=True)
    (r / "tests/test_base.py").write_text("def test_ok():\n    assert True\n")
    (r / "edgelab/research/motor.py").write_text("X = 1\n")
    _git(r, "init", "-q"); _git(r, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    _git(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return r


def _cli(archivos):
    def cli(prompt, *, cwd, model, python, timeout):
        for p, txt in archivos.items():
            f = Path(cwd) / p; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt)
        return {"result": "listo"}
    return cli


MOD = "def correr(x):\n    return x\n"
TEST = ("def test_control_ruido():\n    assert True\n\ndef test_control_plantado():\n    assert True\n")


def _run(repo, tmp_path, archivos, **k):
    root = tmp_path / "state"; root.mkdir(exist_ok=True)
    return P.programar(dict(id="cod-1", que="experimento nuevo", por_que="x"), repo=repo, root=root, cli=_cli(archivos),
                       python=sys.executable, tests=("tests",), push=False, **k), root


def test_zonas_por_ruta():
    assert P.zona("edgelab/research/agente/x.py") == "PERIMETRO"
    assert P.zona("tests/agente/test_x.py") == "PERIMETRO"
    assert P.zona("edgelab/research/grilla_masiva.py") == "PROPUESTA"
    for p in ("edgelab/autopilot/guard.py", "edgelab/autopilot/programador.py", "edgelab/holdout.py", "config/costos/costos_canonicos.json",
              ".gitattributes", "deploy/debian/update.sh", "MANDATO.md"):
        assert P.zona(p) == "SOLO_HUMANO", p
    assert P.zona("tools/x.py", protegidos=("tools/x.py",)) == "SOLO_HUMANO"
    assert P.clasificar(["edgelab/research/agente/a.py", "edgelab/research/motor.py"]) == "PROPUESTA"   # el más restrictivo
    assert P.clasificar(["tests/agente/t.py", "edgelab/costos.py"]) == "SOLO_HUMANO"


def test_aplica_en_perimetro_con_controles_y_tests(repo, tmp_path):
    row, root = _run(repo, tmp_path, {"edgelab/research/agente/exp.py": MOD, "tests/agente/test_exp.py": TEST})
    assert row["estado"] == "APLICADO", row
    assert (repo / "edgelab/research/agente/exp.py").exists() and _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "log", "-1", "--format=%s").startswith("agente(cod-1)")
    assert [json.loads(l)["estado"] for l in (root / P.LOG).read_text().splitlines()] == ["APLICADO"]
    assert P.pendientes(root) == []                                              # no se reprocesa


def test_sin_controles_no_se_aplica(repo, tmp_path):
    row, _ = _run(repo, tmp_path, {"edgelab/research/agente/exp.py": "import numba\n" + MOD, "tests/agente/test_exp.py": TEST})
    assert row["estado"] == "FALLA_CONTROLES" and any("test_oraculo" in d for d in row["detalle"])
    row, _ = _run(repo, tmp_path, {"edgelab/research/agente/otro.py": MOD})
    assert row["estado"] == "FALLA_CONTROLES"
    assert not (repo / "edgelab/research/agente").exists()


def test_tests_rojos_no_se_aplica(repo, tmp_path):
    row, _ = _run(repo, tmp_path, {"edgelab/research/agente/exp.py": MOD, "tests/agente/test_exp.py": TEST + "\ndef test_rojo():\n    assert False\n"})
    assert row["estado"] == "FALLA_TESTS" and not (repo / "edgelab/research/agente").exists()


def test_reglas_se_rechazan_y_motor_queda_como_propuesta(repo, tmp_path):
    row, _ = _run(repo, tmp_path, {"edgelab/autopilot/guard.py": "x=1\n"})
    assert row["estado"] == "RECHAZADO" and row["detalle"] == ["edgelab/autopilot/guard.py"]
    row, root = _run(repo, tmp_path, {"edgelab/research/motor.py": "X = 2\n"})
    assert row["estado"] == "PROPUESTA" and row["rama"].startswith("autopilot/propuesta/")
    assert (repo / "edgelab/research/motor.py").read_text() == "X = 1\n"           # el checkout vivo no cambia
    assert json.loads((root / "mejoras.jsonl").read_text().splitlines()[-1])["origen"] == "programador"


def test_escribir_fuera_de_la_worktree_es_incidente(repo, tmp_path):
    def cli(prompt, *, cwd, model, python, timeout):
        (repo / "intruso.txt").write_text("x"); return {}
    root = tmp_path / "state"; root.mkdir()
    row = P.programar(dict(id="cod-2", que="q"), repo=repo, root=root, cli=cli, python=sys.executable, push=False)
    assert row["estado"] == "INCIDENTE"


def test_ciclo_respeta_interruptor_y_cupo(repo, tmp_path):
    root = tmp_path / "state"; root.mkdir()
    P.pedir(root, "a", "x", pid="p1"); P.pedir(root, "b", "x", pid="p2")
    cli = _cli({"edgelab/research/agente/exp.py": MOD, "tests/agente/test_exp.py": TEST})
    assert P.ciclo(root, repo, {}, cli=cli) == []                                 # apagado por defecto
    out = P.ciclo(root, repo, {"programador": {"activo": True, "max_por_dia": 1, "push": False, "python": sys.executable}}, cli=cli)
    assert [r["pedido"] for r in out] == ["p1"]
    assert P.ciclo(root, repo, {"programador": {"activo": True, "max_por_dia": 1, "push": False}}, cli=cli) == []   # cupo del día usado
