"""Tests unitarios, de causalidad y de paridad lote/escalar para las 3 nuevas familias en espiral (`tori_trend_toque3`, `asia_bos_gaps`, `confluencia_cvgap_racimos`)."""

from __future__ import annotations

import numpy as np

from edgelab.research import (
    asia_bos_gaps as ABG,
    confluencia_cvgap_racimos as CCR,
    grilla_generica as GG,
    indicadores as IND,
    preflight as PF,
    sintetico,
    tori_trend_toque3 as TTT,
)

_CTX_CACHE: dict | None = None


def _ctx():
    global _CTX_CACHE
    if _CTX_CACHE is None:
        _CTX_CACHE = GG.contexto_m1(sintetico.bloques(dias=45, planta=False, seed=21), tick=0.25)
    return _CTX_CACHE


def test_preflight_estatico_tres_nuevas_familias() -> None:
    for mod in (TTT, ABG, CCR):
        err = PF.estatico(mod)
        assert err == [], f"Errores estáticos en {mod.NOMBRE}: {err}"


def test_causal_tori() -> None:
    ctx = _ctx()
    dif = IND.causal(TTT.disparos, ctx)
    assert dif == [], f"Diferencias de causalidad en TORI-TREND-TOQUE3: {dif}"


def test_causal_asia() -> None:
    ctx = _ctx()
    dif = IND.causal(ABG.disparos, ctx)
    assert dif == [], f"Diferencias de causalidad en ASIA-BOS-GAPS: {dif}"


def test_causal_confluencia() -> None:
    ctx = _ctx()
    dif = IND.causal(CCR.disparos, ctx)
    assert dif == [], f"Diferencias de causalidad en CONFLUENCIA-CVGAP-RACIMOS: {dif}"


def test_niveles_lote_identico_a_niveles_tres_familias() -> None:
    ctx = _ctx()
    for mod in (TTT, ABG, CCR):
        D = mod.disparos(ctx)
        assert len(D) > 0, f"{mod.NOMBRE} no generó disparos en 45 días sintéticos"
        O1 = GG.ops_por_fila(mod, D, ctx)
        O2 = GG._ops_lote(mod, D, ctx)
        assert O1.shape == O2.shape and np.array_equal(O1, O2, equal_nan=True), f"Desajuste niveles_lote en {mod.NOMBRE}"
