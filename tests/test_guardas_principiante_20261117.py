"""Guardas K27–K31 (2026-11-17, pedido de Nico: «opera demasiado poco; revisá los errores de principiante y estandarizá que no se
cometan»). Ver docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md §E5."""
import json, re
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
    turtles = HV.plan_potencia("e_proceso", 0.166, 0.62, ops_por_mes=0.44)    # Turtles en oro: 5,3 operaciones por año
    assert any("demasiado poco" in p for p in turtles["problemas"])
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


def test_K30_preregistros_nuevos_declaran_potencia_previa():
    base = set(json.loads((ROOT / "config/preregistros_baseline.json").read_text(encoding="utf-8")))
    faltan = [p.relative_to(ROOT).as_posix() for p in ROOT.glob("docs/research/**/PREREGISTRO*.md")
              if p.relative_to(ROOT).as_posix() not in base and "Potencia previa:" not in p.read_text(encoding="utf-8")]
    assert not faltan, f"pre-registros sin la línea «Potencia previa:» de tools/potencia_previa.py (K30): {faltan}"
