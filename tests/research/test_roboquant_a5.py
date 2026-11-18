"""Tests para ROBOQUANT (`edgelab/research/roboquant_a5.py`): contrato, causalidad estricta y pre-registro."""
import json
from functools import lru_cache
from pathlib import Path

from edgelab.research import indicadores as I, preflight as PF, roboquant_a5 as RQ, sintetico, tablas as TB

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _ctx_sint() -> dict:
    return TB.contexto(RQ, list(sintetico.bloques(dias=55, planta=False, seed=19)), 0.25)


def test_contrato_y_causalidad_estricta_roboquant():
    assert TB.contrato(RQ) == []
    ctx = _ctx_sint()
    E = RQ.eventos(ctx)
    assert len(E) > 0
    for col in RQ.DEFINICIONES:
        assert int(E[col].sum()) > 0, f"{col} no disparó en 55 días sintéticos"
    for ctrl in RQ.CONTROL.values():
        assert int(E[ctrl].sum()) > 0, f"control {ctrl} no disparó en 55 días sintéticos"
    assert (E["fin"] >= E["k"]).all()
    assert (E["rg"] > 0).all()
    assert I.causal_por_disparo(RQ.eventos, ctx, n=15) == []


def test_preregistro_y_campana_roboquant_validos():
    pre = ROOT / "docs/research/roboquant_20261118/PREREGISTRO.md"
    errs = PF.validar_preregistro(pre, ROOT, exigir_commit=False)
    assert errs == [], errs
    camp = json.loads((ROOT / "docs/research/roboquant_20261118/CAMPANA.json").read_text(encoding="utf-8"))
    assert camp["modulo"] == "edgelab.research.roboquant_a5"
    assert set(camp["definiciones"]) == set(RQ.DEFINICIONES)
    assert camp["control"] == RQ.CONTROL
