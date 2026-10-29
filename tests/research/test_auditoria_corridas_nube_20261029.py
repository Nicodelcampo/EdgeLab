"""Tests unitarios y de integración para la auditoría de las corridas de las Olas 1–9 (`auditar_corridas_nube_20261029.py`)."""

from __future__ import annotations

import json

from tools import auditar_corridas_nube_20261029 as ACN


def test_auditoria_modulos_estatica_y_causal() -> None:
    rep = ACN.auditar_modulos(dinamico=False)
    assert rep["ok"] is True, f"Errores en preflight de módulos nuevos: {rep}"
    assert set(rep["modulos"].keys()) == {
        "edgelab.research.corredor_vol_gaps",
        "edgelab.research.otr_930_sweep",
        "edgelab.research.oro_almuerzo_ruptura",
    }
    for mod, info in rep["modulos"].items():
        assert info["ok"] is True, f"Módulo {mod} falló preflight: {info['errores']}"
        assert info["errores"] == []
        assert len(info["sha12"]) == 12


def test_auditoria_16_campanas_y_directiva_6() -> None:
    res = ACN.ejecutar_auditoria_completa(dinamico=False, escribir_reportes=False)
    assert res["ok_global"] is True, f"Hallazgos en auditoría de campañas: {json.dumps(res['campanas'], indent=2)}"
    assert res["n_campanas_auditadas"] == 16
    assert set(res["actas_holdout_listas"]) == {
        "CVGAP-NQ",
        "CVGAP-CFD-NQ",
        "U1-RACIMOS-GRILLA-NQ",
        "U1-RACIMOS-GRILLA-ES",
        "U1-ZONAS-BT2-ES",
        "U1-ZONAS-BT2-NQ",
    }
    assert set(res["campanas_pistas_vivas"]) == {
        "CVGAP-ES",
        "CVGAP-CFD-ES",
        "OTR930-NQ",
        "OTR930-ES",
        "OTR930-CFD-NQ",
        "OTR930-CFD-ES",
        "ORO-ALM-GC",
        "ORO-ALM-CFD",
        "U1-6E-GRILLA",
    }
    for cid in [
        "CVGAP-NQ",
        "CVGAP-CFD-NQ",
        "CVGAP-ES",
        "CVGAP-CFD-ES",
        "OTR930-NQ",
        "OTR930-ES",
        "OTR930-CFD-NQ",
        "OTR930-CFD-ES",
        "ORO-ALM-GC",
        "ORO-ALM-CFD",
        "U1-RACIMOS-GRILLA-NQ",
        "U1-RACIMOS-GRILLA-ES",
        "U1-ZONAS-BT2-ES",
        "U1-ZONAS-BT2-NQ",
        "U1-ZONAS-GRILLA-YM",
    ]:
        assert res["campanas"][cid]["holdout_desde"] == 20261001, f"{cid} incumple Directiva #6"
