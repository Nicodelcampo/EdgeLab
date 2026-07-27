# -*- coding: utf-8 -*-
"""Gate de la regla de diseño: ningún umbral de precio se compara en `double`.

La familia de 1 ULP lleva **cinco** apariciones, cada una en una expresión
distinta, y las cinco se encontraron gastando un oráculo o midiendo a mano.
Estos tests convierten la regla en algo que falla solo.
"""
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))

import ulp_sweep  # noqa: E402

NT8 = os.path.join(REPO, "nt8")
CS = sorted(f for f in os.listdir(NT8) if f.endswith(".cs"))


def test_todo_candidato_actual_esta_triajeado():
    """Modo gate: verde mientras no aparezca una expresión sin clasificar."""
    assert ulp_sweep.main(["--baseline", NT8]) == 0


def test_el_gate_detecta_una_regresion(tmp_path):
    """Un gate que nunca se vio fallar no es un gate.

    Se inyecta la forma canónica del bug —la MISMA que tenía `AACloseOpenDiffs`
    v1.0— en un `.cs` sintético y se exige que el barrido la marque.
    """
    cs = tmp_path / "Regresion.cs"
    cs.write_text(
        "namespace X {\n"
        "  public class Regresion {\n"
        "    void F() {\n"
        "      double gapPts = Math.Abs(closePrev - openCurr);\n"
        "      if (gapPts < MinDiffTicks * TickSize) return;\n"
        "    }\n"
        "  }\n"
        "}\n", encoding="utf-8")
    hits = ulp_sweep.barrer(str(cs))
    exprs = [t for _, t, _ in hits]
    assert any("MinDiffTicks * TickSize" in e for e in exprs), exprs
    assert ulp_sweep.main(["--baseline", str(cs)]) == 1


def test_el_detector_ignora_lo_que_ya_esta_en_enteros():
    """La forma CORREGIDA no debe seguir apareciendo: si no, el gate es ruido."""
    hits = ulp_sweep.barrer(os.path.join(NT8, "AACloseOpenDiffs.cs"))
    exprs = " ".join(t for _, t, _ in hits)
    assert "MinDiffTicks * TickSize" not in exprs
    assert "gapTicks < MinDiffTicks" not in exprs   # comparación entre enteros


def test_hftzones2_compara_el_ciclo_de_vida_en_enteros():
    """v2.3: `inside` en enteros. En v2.2 quedó en doubles y costó 272 diffs."""
    src = open(os.path.join(NT8, "HFTZones2.cs"), encoding="utf-8-sig").read()
    assert "bool inside = priceTick >= z.LowerTick && priceTick <= z.UpperTick;" in src
    assert "bool inside = price >= z.Lower && price <= z.Upper;" not in src


@pytest.mark.parametrize("nombre", CS)
def test_cada_cs_declara_version_en_el_meta(nombre):
    """Cada corrección de `.cs` viaja con su versión — regla permanente de Nico."""
    src = open(os.path.join(NT8, nombre), encoding="utf-8-sig").read()
    assert "version=" in src, nombre


def test_el_baseline_no_tiene_veredictos_inventados():
    d = json.load(open(ulp_sweep.BASELINE, encoding="utf-8"))
    assert d["triaje"], "baseline vacío"
    for k, v in d["triaje"].items():
        assert v["veredicto"] in ulp_sweep.VEREDICTOS, (k, v["veredicto"])
        # Un veredicto sin evidencia es una opinión. AUDIT-001 fue exactamente eso.
        assert len(v["evidencia"]) > 40, k


def test_no_queda_ninguna_exposicion_sin_resolver():
    """Tras la Decisión A de Nico (2026-07-26) no hay `EXPUESTO_PENDIENTE`.

    El filtro de mecha de BigTrap2 —único caso que quedaba— se resolvió como
    `ESPEJADO_BIT_A_BIT`: no se convierte a enteros porque el umbral es
    intrínsecamente fraccionario, se exige el mismo orden de operaciones y se
    documenta el residual medido.
    """
    d = json.load(open(ulp_sweep.BASELINE, encoding="utf-8"))["triaje"]
    pend = [k for k, v in d.items() if v["veredicto"] == "EXPUESTO_PENDIENTE"]
    assert pend == [], pend


def test_los_umbrales_fraccionarios_declaran_su_residual_MEDIDO():
    """Un `ESPEJADO_BIT_A_BIT` sin el número medido sería una opinión.

    Es toda la diferencia entre esta clase y "lo dejamos así": la clase sólo se
    puede usar acompañada de la medición que prueba que la aritmética aporta 0.
    """
    d = json.load(open(ulp_sweep.BASELINE, encoding="utf-8"))["triaje"]
    esp = {k: v for k, v in d.items() if v["veredicto"] == "ESPEJADO_BIT_A_BIT"}
    assert len(esp) == 2, list(esp)
    assert all("wick" in k for k in esp), list(esp)
    for k, v in esp.items():
        assert "AUDIT-003" in v["evidencia"], k
        assert "0,024051%" in v["evidencia"] or "0.024051%" in v["evidencia"], k
        # La medición que la justifica: la aritmética aporta 0.
        assert "0,000000%" in v["evidencia"] or "0.000000%" in v["evidencia"], k
