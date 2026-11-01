"""Tests unitarios para la infraestructura multi-agente Debian v2 (`sincronizador_ramas`, `catalogo_espiral`, `orquestador_multiagente`, `auditor_alineacion`)."""

from __future__ import annotations

import json
from pathlib import Path

from edgelab.autopilot import (
    auditor_alineacion as AA,
    orquestador_multiagente as OM,
    sincronizador_ramas as SR,
)
from edgelab.research import catalogo_espiral as CE


def test_catalogo_espiral_y_resumen_rapido() -> None:
    cat = CE.catalogo_completo()
    assert cat["schema"] == "edgelab_catalogo_modulos_espiral_v2"
    assert len(cat["modulos"]) >= 14
    ids = {m["id_modulo"] for m in cat["modulos"]}
    for req in ("corredor_vol_gaps", "zonas_gaps", "otr_930_sweep", "oro_almuerzo_ruptura", "tori_trend_toque3", "asia_bos_gaps", "confluencia_cvgap_racimos"):
        assert req in ids, f"Falta {req} en el catálogo en espiral"
    resumen = CE.resumen_rapido_para_agente(max_chars=8000)
    assert len(resumen) <= 8000
    assert "confluencia_cvgap_racimos" in resumen


def test_orquestador_multiagente_velocidad_cuidado_y_contexto() -> None:
    ev_rapida = OM.evaluar_velocidad_cuidado(
        usa_detector_nuevo_numba=False,
        reutiliza_primitivas_l1_l2=["corredor_vol_gaps", "u1_racimos_grilla"],
        n_celdas_por_canal=314928,
    )
    assert ev_rapida.via == "VIA_RAPIDA_COMPOSICION"

    ev_cuidada = OM.evaluar_velocidad_cuidado(
        usa_detector_nuevo_numba=True,
        reutiliza_primitivas_l1_l2=["zonas_gaps"],
        n_celdas_por_canal=1119744,
    )
    assert ev_cuidada.via == "VIA_CUIDADA_PARIDAD"
    assert ev_cuidada.requiere_oraculo_numba is True

    paq = OM.armar_contexto_amplio_espiral(
        directivas_texto="Directivas 1..7",
        resumen_catalogo=CE.resumen_rapido_para_agente(),
        aprendizajes_espiral="Aprendizaje 1\n" * 500,
        tablero={"activas": 12},
        cartas_gramatica=[{"id": f"G-{i}"} for i in range(10)],
        vacios=[f"vacio_{i}" for i in range(50)],
        fichas_existentes=[{"ref": f"mod_{i}"} for i in range(50)],
        max_chars=25000,
    )
    assert len(json.dumps(paq, ensure_ascii=False)) <= 25000
    assert len(paq["fichas_codigo_reutilizable"]) >= 10
    assert len(paq["vacios_cobertura"]) >= 10


def test_fusion_jsonl_y_verificacion_o16(tmp_path: Path) -> None:
    f1 = tmp_path / "a.jsonl"
    f2 = tmp_path / "b.jsonl"
    f1.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
    f2.write_text('{"id": 2}\n{"id": 3}\n', encoding="utf-8")
    nuevas = SR.fusionar_jsonl_sin_perdida(f1, f2)
    assert nuevas == 1
    assert len(f2.read_text(encoding="utf-8").splitlines()) == 3

    reg = OM.registrar_reapertura_o16(tmp_path, "CVGAP-NQ", "fc1b9443", "fix O13")
    assert reg["estado_o16"] == "VERIFICANDO_O16"
    reg2 = OM.verificar_cierre_o16(tmp_path, "CVGAP-NQ", "complete", "Todo OK sin errores")
    assert reg2["estado_o16"] == "VERIFICADA_OK"
    assert reg2["primer_kernel_verificado"] is True
