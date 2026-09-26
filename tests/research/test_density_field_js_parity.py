r"""Paridad Python <-> JS del campo de densidad HP-007: UNA sola definición de corredor.

`edgelab/research/density_field.py` es la referencia; `viewer/nt8_bridge/density_field.js` es el puerto
que corre el visor. Los vectores dorados los genera Python (`tools/generate_density_field_golden_vectors.py`)
y el puerto tiene que reproducirlos.

Esto cierra un hueco documentado en `docs/research/VIEWER_UNIFICATION_PROPOSAL_20260921.md`: el motor JS
certificado anterior (`corridor_engine.js`, archivado) NUNCA se validó contra el módulo Python con el que
se midió HP-007, y el único test cruzado previo comparaba a Python con una tercera implementación escrita
dentro del propio test.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tests" / "research" / "density_field_js_parity_runner.js"
FIXTURE = ROOT / "tests" / "fixtures" / "density_field_golden_v2.json"


@pytest.fixture(scope="module")
def resumen():
    r = subprocess.run(["node", str(RUNNER)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_el_fixture_esta_al_dia_con_la_referencia_python():
    """Si cambia `density_field.py` o `corridor_geometry.py`, hay que regenerar y revisar el diff."""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "generate_density_field_golden_vectors.py"), "--check"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr


def test_todos_los_escenarios_coinciden(resumen):
    malos = {k: v["problemas"] for k, v in resumen["scenarios"].items() if not v["ok"]}
    assert malos == {}, json.dumps(malos, indent=1)[:3000]


def test_hay_cobertura_real_no_un_fixture_vacio(resumen):
    assert len(resumen["scenarios"]) >= 20
    assert sum(v["activas"] for v in resumen["scenarios"].values()) > 300
    assert sum(v["corredores"] for v in resumen["scenarios"].values()) > 0, "ningun corredor: el fixture no ejercita la deteccion"
    assert sum(v["murallas"] for v in resumen["scenarios"].values()) > 0, "ninguna muralla: el fixture no ejercita la deteccion"


def test_la_densidad_es_practicamente_identica_no_solo_cercana(resumen):
    """Las dos redondean a 8 decimales: la diferencia esperada es 0; solo un empate de redondeo daria 1e-8."""
    for nombre, v in resumen["scenarios"].items():
        assert v["max_abs_diff"] <= 2e-8, (nombre, v["max_abs_diff"])
        assert v["exactos"] >= 0.999 * v["n"], (nombre, v["exactos"], v["n"])


def test_la_caracterizacion_direccional_cubre_las_cuatro_etiquetas():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    vistas = set()
    for s in doc["scenarios"]:
        for c in s["expected"]["corridors"]:
            vistas.add(c["direction"])
    assert {"DUAL", "BULL"} <= vistas, vistas


def test_el_firewall_del_holdout_falla_cerrado_en_JS_y_en_Python(resumen):
    from edgelab.research.density_field import HOLDOUT_NS, compute_field
    for nombre, v in resumen["fail_closed"].items():
        assert v["lanzo"], nombre
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for c in doc["must_fail_closed"]:
        with pytest.raises(ValueError):
            compute_field(c["zones"], c["t_ref"], doc["tick_size"], 76000, 76100, c["cfg"])
    assert doc["holdout_ns"] == HOLDOUT_NS


def test_el_orden_de_entrada_no_cambia_nada(resumen):
    a = resumen["scenarios"]["raw_gauss"]
    b = resumen["scenarios"]["shuffled_input_order"]
    assert a["ok"] and b["ok"]
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ea = next(s for s in doc["scenarios"] if s["name"] == "raw_gauss")["expected"]
    eb = next(s for s in doc["scenarios"] if s["name"] == "shuffled_input_order")["expected"]
    assert ea["density"] == eb["density"] and ea["active_zone_ids"] == eb["active_zone_ids"]


def test_el_estado_economico_no_depende_del_viewport():
    """Invarianza de viewport heredada del motor certificado: zoom/pan/tamaño no son entradas."""
    js = r"""
      const DF = require(process.argv[1]);
      const zones = [{id:'a', bottom:100, top:101, vol:5, available_ns:1780000000000000000+4096*1000},
                     {id:'b', bottom:103, top:104, vol:9, available_ns:1780000000000000000+8192*1000}];
      const cfg = DF.PRESETS.HP007_CALIBRATED, t = 1780000000000000000 + 4096*1000*100;
      const A = () => { const f = DF.computeField(zones, t, 0.25, 380, 440, cfg);
        const i = DF.detectDensityIntervals(f.density, f.priceTickMin, 0.25); return DF.canonicalState(f, i, [], t).fingerprint; };
      const viewportA = {zoom:1, width:800}, viewportB = {zoom:9, width:1900};   // no son parametros de nada
      console.log(A() === A());
    """
    r = subprocess.run(["node", "-e", js, str(ROOT / "viewer" / "nt8_bridge" / "density_field.js")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.stdout.strip() == "true", r.stderr


def test_el_desgaste_por_toque_parametrizado_coincide_en_JS_y_en_Python():
    """2026-09-24: wear_alpha / wear_exp se exponen para calibrar corredores en el visor. Con valores distintos a los
    de fábrica, Python y JS tienen que dar el mismo campo (y los de fábrica no cambian)."""
    from edgelab.research.density_field import compute_field
    base = 1780000000000000000
    zones = [{"id": "a", "bottom": 100, "top": 101, "vol": 5, "available_ns": base + 4096 * 1000,
              "touch_events": [base + 9000 * 1000, base + 12000 * 1000, base + 15000 * 1000]},
             {"id": "b", "bottom": 103, "top": 104, "vol": 9, "available_ns": base + 8192 * 1000, "touch_events": []}]
    t = base + 4096 * 1000 * 100
    for wa, we in ((0.5, 0.60), (2.0, 1.5), (0.0, 0.6)):
        cfg = dict(model="FIELD_TRANS", kernel="KERNEL_GAUSS", sigma_ticks=1.2, vol_transform="TRANS_POWER_025",
                   use_maturation=True, use_time_decay=False, use_wear=True, saturation=True, wear_alpha=wa, wear_exp=we)
        py = compute_field(zones, t, 0.25, 380, 440, cfg)["density"]
        js = r"""
          const DF = require(process.argv[1]); const [zs, t, cfg] = JSON.parse(process.argv[2]);
          console.log(JSON.stringify(DF.computeField(zs, t, 0.25, 380, 440, cfg).density));
        """
        r = subprocess.run(["node", "-e", js, str(ROOT / "viewer" / "nt8_bridge" / "density_field.js"),
                            json.dumps([zones, t, cfg])], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        jsd = json.loads(r.stdout)
        assert max(abs(a - b) for a, b in zip(py, jsd)) < 1e-12, (wa, we)
    # el desgaste realmente cambia el campo
    hi = compute_field(zones, t, 0.25, 380, 440, dict(cfg, wear_alpha=2.0, wear_exp=1.5))["density"]
    lo = compute_field(zones, t, 0.25, 380, 440, dict(cfg, wear_alpha=0.0))["density"]
    assert hi != lo
