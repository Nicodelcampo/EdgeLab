"""Guardas K27–K31 (2026-11-17, pedido de Nico: «opera demasiado poco; revisá los errores de principiante y estandarizá que no se
cometan»). Ver docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md §E5."""
import json
import re, re
from pathlib import Path

import pytest

from edgelab.funnel.escalera import separar_por_n
from edgelab.research import holdout_ventanas as HV

ROOT = Path(__file__).resolve().parents[1]


def test_K27_ninguna_apertura_sin_plan_de_potencia(tmp_path):
    lib = tmp_path / "v.jsonl"
    with pytest.raises(ValueError, match="sin plan"):
        HV.registrar_apertura("F", "C", 20261001, 0, lib)
    malo = HV.plan_potencia("fijo", 0.04, 0.98, n=29)                       # el holdout de SOM tal como se abrió el 2026-11-16
    assert malo["problemas"] and malo["potencia"] < 0.2
    with pytest.raises(ValueError, match="no se abre"):
        HV.registrar_apertura("F", "C", 20261001, 29, lib, plan=malo)
    bueno = HV.plan_potencia("fijo", 0.2, 1.0, n=200)
    assert not bueno["problemas"] and HV.registrar_apertura("F", "C", 20261001, 200, lib, plan=bueno)["plan"]["potencia"] >= 0.8


def test_K27_frecuencia_minima_y_horizonte_del_forward():
    turtles = HV.plan_potencia("e_proceso", 0.166, 0.62, ops_por_mes=0.44)    # Turtles en oro: 5,3 operaciones por año, 196 meses
    assert any("demasiado poco" in p for p in turtles["problemas"])
    rara_y_fuerte = HV.plan_potencia("e_proceso", 1.0, 1.0, ops_por_mes=0.5)  # poca frecuencia pero mucho efecto: decide en 13 meses
    assert not rara_y_fuerte["problemas"]
    som = HV.plan_potencia("e_proceso", 0.079, 0.98, ops_por_mes=19.7)       # SOM 2020+: 49 meses, pasa
    assert not som["problemas"] and som["meses_para_decidir"] <= HV.MESES_MAX_DECISION
    assert HV.plan_potencia("e_proceso", 0.1, 1.0)["problemas"]              # sin frecuencia declarada no se abre


def test_K29_pruebas_sin_n_fuera_de_la_familia_bh():
    dentro, fuera = separar_por_n({"COT1|GC": 4, "DOUBLE7|NQ": 174, "MR_B|YM": 0, "BUY_DIPS|ES": 81})
    assert dentro == ["BUY_DIPS|ES", "DOUBLE7|NQ"] and fuera == ["COT1|GC", "MR_B|YM"]


def test_K28_ningun_simulador_nuevo_sin_calibracion():
    base = json.loads((ROOT / "config/simuladores_baseline.json").read_text(encoding="utf-8"))
    pat = re.compile(r"^\s*def (simular\w*|_simular\w*|_sim\w*|sim_\w*)\(", re.M); nuevos = []
    for p in sorted(list(ROOT.glob("edgelab/**/*.py")) + list(ROOT.glob("tools/**/*.py"))):
        for m in pat.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            k = f"{p.relative_to(ROOT).as_posix()}::{m.group(1)}"
            if k not in base: nuevos.append(k)
    assert not nuevos, ("motor/simulador nuevo: usar el motor único edgelab/research/ejecucion.py (cadena estándar, K23) o, si hace falta "
                        f"un motor de barras, registrarlo en config/simuladores_baseline.json con su test de calibración (K28): {nuevos}")
    for k, v in base.items():
        if not v.startswith("legacy"):
            archivo, _, test = v.partition("::")
            assert (ROOT / archivo).exists() and f"def {test}(" in (ROOT / archivo).read_text(encoding="utf-8"), f"{k}: calibración {v} no existe"


def test_K30_K32_preregistros_nuevos_cumplen_lo_que_pide_edgelab():
    """Todo PREREGISTRO*.md nuevo: hash del North Star, Estado, justificación económica, cómo podría refutarse, etapa EF, Antecedentes y
    Potencia previa (preflight.validar_preregistro). Línea base: config/preregistros_baseline.json."""
    from edgelab.research.preflight import validar_preregistro
    base = set(json.loads((ROOT / "config/preregistros_baseline.json").read_text(encoding="utf-8")))
    mal = {p.relative_to(ROOT).as_posix(): validar_preregistro(p, ROOT, exigir_commit=False) for p in ROOT.glob("docs/research/**/PREREGISTRO*.md")
           if p.relative_to(ROOT).as_posix() not in base}
    assert not {k: v for k, v in mal.items() if v}, mal


def test_K32_toda_prueba_nueva_del_contador_pasa_por_edgelab():
    """Filas nuevas del contador global: o las escribió la maquinaria estándar (embudo, banco, analizador, autopilot…, con su preflight), o
    citan un pre-registro válido (tools/registro_global.py preregistrado). Una corrida ad hoc sin eso no se puede commitear."""
    import sys; sys.path.insert(0, str(ROOT / "tools"))
    from registro_global import PREFIJOS_MAQUINARIA
    from edgelab.research.preflight import validar_preregistro
    n0 = json.loads((ROOT / "config/registro_global_baseline.json").read_text(encoding="utf-8"))["filas"]
    filas = [json.loads(x) for x in (ROOT / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()][n0:]
    mal = {}
    for r in filas:
        if r["campaign_id"].startswith(PREFIJOS_MAQUINARIA) or "/confirmacion_" in r["campaign_id"]: continue
        nota = r.get("note", "")
        e = validar_preregistro(nota, ROOT, exigir_commit=False) if nota.endswith(".md") else ["la nota no es un pre-registro (.md)"]
        if e: mal[r["campaign_id"]] = e
    assert not mal, f"pruebas contadas por fuera de EdgeLab (K32): {mal}"


def test_K32_el_validador_pide_lo_de_claude_md(tmp_path):
    from edgelab.research.preflight import north_star_sha256, validar_preregistro
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/NORTH_STAR.md").write_bytes((ROOT / "docs/NORTH_STAR.md").read_bytes())
    malo = tmp_path / "P.md"; malo.write_text("# x\n\nEstado: PRE-REGISTRO\n")
    e = validar_preregistro(malo, tmp_path, exigir_commit=False)
    assert len(e) == 8 and any("NORTH_STAR" in x for x in e) and any("Lectura previa" in x for x in e) and any("Diagnóstico de mecanismo" in x for x in e)
    bueno = tmp_path / "Q.md"
    bueno.write_text(f"# x\nEstado: PRE-REGISTRO\nNorth Star {north_star_sha256(ROOT)}. Etapa EF3.\nAntecedentes: «x» — ...\n"
                     "Potencia previa: ops.csv: 20 ops/mes ... OK\nLectura previa: LEER_ANTES_DE_CADA_CORRIDA v1 — §0–§5\n"
                     "Diagnóstico de mecanismo: no aplica — una sola regla\n"
                     "## Justificación económica / cómo podría refutarse\n")
    assert validar_preregistro(bueno, tmp_path, exigir_commit=False) == []


def test_K33_spread_estimado_no_es_medido():
    from edgelab import costos
    with pytest.raises(costos.CostoNoMedido, match="ESTIMADO"):
        costos.friccion_rt_puntos("ZB")
    with costos.estimados_permitidos("pre-registro de prueba"):
        assert costos.friccion_rt_puntos("ZB") > 0
    with pytest.raises(costos.CostoNoMedido):
        costos.friccion_rt_puntos("ZB")                                          # fuera del bloque vuelve a frenar
    assert costos.friccion_rt_puntos("GC") > 0                                   # lo medido no cambia


def test_indice_de_lectura_obligatorio_existe_y_la_exencion_es_cerrada():
    """Nico, 2026-11-18: un índice obligatorio de lectura por corrida. Los pre-registros anteriores quedan exentos sólo de esa línea; la
    lista no crece (todo pre-registro nuevo la lleva)."""
    idx = (ROOT / "docs/research/LEER_ANTES_DE_CADA_CORRIDA.md").read_text(encoding="utf-8")
    assert "Estado: VIGENTE" in idx and re.search(r"\(v\d+, ", idx)
    for ref in re.findall(r"`(docs/[^`]+\.(?:md|jsonl|json))`", idx):
        assert (ROOT / ref).exists(), f"el índice cita un documento que no existe: {ref}"
    exentos = json.loads((ROOT / "config/preregistros_sin_lectura_previa.json").read_text(encoding="utf-8"))
    assert len(exentos) <= 139, "la exención es cerrada: un pre-registro nuevo lleva «Lectura previa:»"
