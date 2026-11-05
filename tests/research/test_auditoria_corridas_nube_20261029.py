"""Tests unitarios y de integración para la auditoría de las corridas de las Olas 1–10 (`auditar_corridas_nube_20261029.py`)."""

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
        "edgelab.research.tori_trend_toque3",
        "edgelab.research.asia_bos_gaps",
        "edgelab.research.confluencia_cvgap_racimos",
    }
    for mod, info in rep["modulos"].items():
        assert info["ok"] is True, f"Módulo {mod} falló preflight: {info['errores']}"
        assert info["errores"] == []
        assert len(info["sha12"]) == 12


def test_auditoria_28_campanas_y_directiva_6() -> None:
    res = ACN.ejecutar_auditoria_completa(dinamico=False, escribir_reportes=False)
    assert res["ok_global"] is True, f"Hallazgos en auditoría de campañas: {json.dumps(res['campanas'], indent=2)}"
    assert res["n_campanas_auditadas"] == 28
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
        "CONF-CVR-NQ",
        "CONF-CVR-CFD-NQ",
        "CONF-CVR-CFD-ES",
        "TORI-NQ",
        "TORI-GC",
        "TORI-CFD-NQ",
        "ASIA-NQ",
        "ASIA-ES",
        "ASIA-GC",
        "ASIA-CFD-NQ",
    }
    assert len(res["campanas_ola10_desc"]) == 0
    for cid in res["campanas"]:
        if cid != "U1-6E-GRILLA":
            assert res["campanas"][cid]["holdout_desde"] == 20261001, f"{cid} incumple Directiva #6"
