"""Tests para BAJA-FRICCION (`edgelab/research/baja_friccion_a5.py`): contrato, causalidad estricta y pre-registro."""
import json
from functools import lru_cache
from pathlib import Path

from edgelab.research import baja_friccion_a5 as BF, indicadores as I, preflight as PF, sintetico, tablas as TB

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _ctx_sint() -> dict:
    return TB.contexto(BF, list(sintetico.bloques(dias=55, planta=False, seed=23)), 0.25)


def test_contrato_y_causalidad_estricta_baja_friccion():
    assert TB.contrato(BF) == []
    ctx = _ctx_sint()
    E = BF.eventos(ctx)
    assert len(E) > 0
    for col in BF.DEFINICIONES:
        assert int(E[col].sum()) > 0, f"{col} no disparó en 55 días sintéticos"
    for ctrl in BF.CONTROL.values():
        assert int(E[ctrl].sum()) > 0, f"control {ctrl} no disparó en 55 días sintéticos"
    assert (E["fin"] >= E["k"]).all()
    assert (E["rg"] > 0).all()
    assert I.causal_por_disparo(BF.eventos, ctx, n=15) == []


def test_preregistro_y_campana_baja_friccion_validos():
    pre = ROOT / "docs/research/baja_friccion_20261119/PREREGISTRO.md"
    errs = PF.validar_preregistro(pre, ROOT, exigir_commit=False)
    assert errs == [], errs
    camp = json.loads((ROOT / "docs/research/baja_friccion_20261119/CAMPANA.json").read_text(encoding="utf-8"))
    assert camp["modulo"] == "edgelab.research.baja_friccion_a5"
    assert set(camp["definiciones"]) == set(BF.DEFINICIONES)
    assert camp["control"] == BF.CONTROL
