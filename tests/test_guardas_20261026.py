"""Guardas que salen de los errores del 2026-10-26 (docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md)."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import embudo_correr as EC  # noqa: E402
import holdout_canasta as HC  # noqa: E402
from edgelab.research import embudo as EM  # noqa: E402


def test_E1_no_se_cierra_como_refutada_sin_refutacion(tmp_path):
    em = EM.Embudo(tmp_path, {}, log=lambda s: None, ahora=lambda: 1.0)
    st = dict(etapa="PISTAS", historial=[], pistas_replica=dict(lord=dict(nivel=0.003), veredicto=dict(veredicto="SIN_RECHAZO")))
    st = em._cerrar(dict(cid="X"), st, "SIN_CANDIDATAS", "0 de 20")
    assert st["fase"] == "PISTAS_VIVAS" and "guarda" in st["motivo"]
    st2 = dict(etapa="PISTAS", historial=[], pistas_replica=dict(lord=dict(nivel=0.003), veredicto=dict(veredicto="REFUTADA")))
    assert em._cerrar(dict(cid="Y"), st2, "SIN_CANDIDATAS", "en contra")["fase"] == "SIN_CANDIDATAS"


def test_E4_conductor_con_raiz_equivocada_o_duplicado(tmp_path):
    repo = tmp_path / "repo"; buena = repo / "docs/research/a/embudo"; mala = repo / "docs/research/b/embudo"
    (buena / "C1").mkdir(parents=True); (buena / "C1" / "estado.json").write_text("{}"); mala.mkdir(parents=True)
    assert EC.problemas_conduccion([dict(cid="C1")], mala, repo) and not EC.problemas_conduccion([dict(cid="C1")], buena, repo)
    (buena / "C1" / ".conductor.pid").write_text(str(os.getppid()))            # un proceso vivo que no es éste
    assert any("conductor vivo" in e for e in EC.problemas_conduccion([dict(cid="C1")], buena, repo))


def test_E8_acta_de_canasta_sin_potencia_se_niega(tmp_path):
    raiz = tmp_path / "embudo"; (raiz / "Z").mkdir(parents=True)
    st = dict(fase="PISTAS_VIVAS", spec=dict(familia="F", experimento="e", sensor="NQ"), cortes={},
              pistas_replica=dict(celdas=[[1]], canasta=dict(media=2.6, ic90=[-1.4, 7.0], n_sesiones=118)))
    (raiz / "Z" / "estado.json").write_text(json.dumps(st))
    assert HC.potencia_planeada(st, 250, 0.002) < 0.8 < HC.potencia_planeada(st, 5000, 0.002)
    with pytest.raises(SystemExit): HC.acta(raiz, "Z", 250, ventanas=tmp_path / "v.jsonl")
    assert not (raiz / "Z" / "ACTA_HOLDOUT_CANASTA.json").exists()
