"""Tests de la arquitectura fail-closed de persistencia de contexto (Capas 1-4)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.edge_brain.invalidation import DependencyEdge  # noqa: E402
from edgelab.research import contexto_vivo as CV  # noqa: E402
from edgelab.research import memoria_activa as MA  # noqa: E402
from edgelab.research import puerta_corrida as PC  # noqa: E402
from edgelab.research import puerta_kernel as PK  # noqa: E402
from edgelab.research.preflight import north_star_sha256, validar_preregistro  # noqa: E402


def _mini_repo(tmp_path: Path, n_no_repetir: int = 2) -> Path:
    (tmp_path / "docs" / "research").mkdir(parents=True)
    (tmp_path / "docs" / "cartera").mkdir(parents=True)
    (tmp_path / "EDGES_DISCOVERED.md").write_text("# Edges\n## Estado actual: ninguno\n", encoding="utf-8")
    (tmp_path / "docs" / "NORTH_STAR.md").write_bytes((ROOT / "docs" / "NORTH_STAR.md").read_bytes())
    (tmp_path / "docs" / "research" / "LEER_ANTES_DE_CADA_CORRIDA.md").write_text(
        "# Leer antes (v4, 2026-11-19)\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "cartera" / "CANASTAS_VIGENTES.md").write_text(
        "# Canastas\n## Cartera v2 — papel\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "research" / "HOLDOUT_VENTANAS.jsonl").write_text(
        json.dumps({"tipo": "consumida", "familia": "LUXIMB_FADE", "hasta": 20261021}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl").write_text(
        json.dumps({"campaign_id": "camp/1", "family_id": "FAM", "n_trials": 5, "note": "docs/research/p.md"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "research" / "LINAJES.jsonl").write_text(
        json.dumps({"familia": "HIJA_NO_REP", "padres": ["PADRE_NO_REP"]}) + "\n",
        encoding="utf-8",
    )
    rows = [
        {
            "id": "F-PISTA-DEMO",
            "fecha": "2026-11-20",
            "estado": "PISTA_VIVA",
            "factor": "Ruptura NY con stop amplio en ATR",
            "efecto": "+0.2 R",
            "donde": "NQ",
            "evidencia": ["EDGES_DISCOVERED.md"],
            "siguiente": "Confirmar en REP",
            "origen": "humano",
        }
    ]
    for i in range(n_no_repetir):
        rows.append(
            {
                "id": f"F-NR-{i}",
                "fecha": "2026-11-19",
                "estado": "NO_REPETIR",
                "factor": f"VWAP dual iman limite sin filtro con stop ajustado en NQ caso {i}",
                "efecto": "-0.1 R",
                "donde": "NQ",
                "evidencia": ["EDGES_DISCOVERED.md"],
                "siguiente": "No repetir igual",
                "origen": "humano",
            }
        )
    (tmp_path / "docs" / "research" / "FACTORES.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    return tmp_path


def test_estado_vivo_acotado_y_determinista(tmp_path):
    repo = _mini_repo(tmp_path, n_no_repetir=110)
    out = CV.escribir_estado_vivo(repo)
    txt = out.read_text(encoding="utf-8")
    assert len(txt.splitlines()) <= CV.MAX_LINEAS
    assert len(txt) <= CV.MAX_CHARS
    assert "Estado: VIGENTE" in txt
    assert CV.verificar_estado_vivo(repo) == []

    # Deriva detectada cuando alguien modifica el archivo manualmente
    out.write_text(txt + "\nextra\n", encoding="utf-8")
    errs = CV.verificar_estado_vivo(repo)
    assert errs and any("desactualizado" in e for e in errs)


def test_memoria_activa_bloquea_no_repetir_y_exige_cambio_estructural(tmp_path):
    repo = _mini_repo(tmp_path)
    sha = north_star_sha256(repo)
    prereg_malo = tmp_path / "docs" / "research" / "PREREGISTRO_MALO.md"
    prereg_malo.write_text(
        f"# Test\nEstado: PRE-REGISTRO\nNorth Star {sha}\nEtapa EF3\n"
        "Justificación económica: probar vwap dual iman limite sin filtro con stop ajustado en NQ\n"
        "Cómo podría refutarse: R <= 0 en REP\n"
        "Antecedentes: x\nPotencia previa: 20 ops/mes OK\n"
        "Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0\n"
        "Diagnóstico de mecanismo: una regla\n",
        encoding="utf-8",
    )
    errs = validar_preregistro(prereg_malo, repo, exigir_commit=False)
    assert any("memoria activa" in e and "F-NR-0" in e for e in errs)

    # Si solo aparece en la linea Antecedentes y el cuerpo trata otro tema, no bloquea
    solo_antecedente = (
        "# Otro experimento\n"
        "Mecanismo: compresion semanal en oro con stop de volatilidad\n"
        "Antecedentes: similar a nada; NO_REPETIR: F-NR-0\n"
    )
    assert MA.verificar_memoria_activa(solo_antecedente, root=repo) == []

    # Si declara Cambio respecto a falla previa, pasa
    prereg_bueno = prereg_malo.read_text(encoding="utf-8") + "\nCambio respecto a falla previa: agrega filtro de volatilidad ATR y stop amplio\n"
    prereg_malo.write_text(prereg_bueno, encoding="utf-8")
    assert validar_preregistro(prereg_malo, repo, exigir_commit=False) == []

    # Propagacion de invalidaciones desde edge_brain
    edges = [DependencyEdge("HIJA_NO_REP", "BASE_ROTA", "DEPENDS_ON")]
    e_inv = MA.verificar_memoria_activa(
        "Usando HIJA_NO_REP",
        familia="HIJA_NO_REP",
        root=repo,
        dependencias=edges,
        ids_invalidados=["BASE_ROTA"],
    )
    assert any("STALE_BY_DEPENDENCY" in x for x in e_inv)


def test_puerta_kernel_y_puerta_corrida_fail_closed(tmp_path):
    # AST invalido
    assert any("sintaxis" in e for e in PK.validar_script_kernel("def f(:\n  pass\n"))
    # Holdout sellado
    assert any("HOLDOUT-A4" in e for e in PK.validar_script_kernel("ds = 'nicolasbuttaro/edgelab-holdout-sellado'\n"))
    # Script de datos sin guarda de holdout ni preregistro
    crudo = "import pandas as pd\ndf = pd.read_parquet('/kaggle/input/nq.parquet')\n"
    errs = PK.validar_script_kernel(crudo)
    assert len(errs) >= 2
    # Script canonico valido pasa
    canonico = (
        "import pandas as pd\n"
        "from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT\n"
        "MODULO = 'edgelab.research.demo'\n"
        "PREREGISTRO = 'docs/research/PREREGISTRO.md'\n"
        "df = pd.read_parquet('/kaggle/input/nq.parquet')\n"
    )
    assert PK.validar_script_kernel(canonico, require_canonical=True) == []

    # Puerta completa L1-L4
    repo = _mini_repo(tmp_path)
    CV.escribir_estado_vivo(repo)
    sha = north_star_sha256(repo)
    pr = repo / "docs" / "research" / "p.md"
    pr.write_text(
        f"# P\nEstado: PRE-REGISTRO\nNorth Star {sha}\nEF3\nJustificación económica: test\n"
        "Cómo podría refutarse: R<=0\nAntecedentes: x\nPotencia previa: OK\n"
        "Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0\nDiagnóstico de mecanismo: no aplica\n",
        encoding="utf-8",
    )
    sc = repo / "kernel_ok.py"
    sc.write_text(canonico, encoding="utf-8")
    ok = PC.verificar_corrida(prereg="docs/research/p.md", script="kernel_ok.py", exigir_contada=False, root=repo)
    assert ok["ok"] and ok["errores"] == []

    bad = PC.verificar_corrida(
        prereg="docs/research/p.md",
        modulo="edgelab.research.fundedsyncstack",
        script="kernel_ok.py",
        root=repo,
    )
    assert not bad["ok"] and any("no expone" in e for e in bad["errores"])


def test_repo_estado_vivo_y_puerta_corrida_en_verde():
    assert CV.verificar_estado_vivo(ROOT) == []
    res = PC.verificar_corrida(verificar_estado=True, root=ROOT)
    assert res["ok"], res
    ex_ma = json.loads((ROOT / "config/preregistros_sin_memoria_activa.json").read_text(encoding="utf-8"))
    assert len(ex_ma) <= 37, "lista cerrada de exencion de memoria activa no puede crecer"
