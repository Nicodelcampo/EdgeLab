import json
from edgelab.research import holdout_ventanas as HV


def _libro(tmp):
    p = tmp / "v.jsonl"
    p.write_text(json.dumps({"tipo": "consumida", "familia": "A", "desde": 20261001, "hasta": 20261022, "relacionadas": ["B"]}) + "\n")
    return p


def test_ventana_consumida_bloquea_a_la_familia_y_a_las_derivadas(tmp_path):
    p = _libro(tmp_path)
    assert HV.problemas("A", 20261001, "c1", p) and HV.problemas("B", 20261022, "c1", p)
    assert HV.problemas("A", 20261023, "c1", p) == [] and HV.problemas("Z", 20261001, "c1", p) == []


def test_una_sola_apertura_por_familia(tmp_path):
    p = _libro(tmp_path)
    HV.registrar_apertura("B", "camp-1", 20261023, 150, p)
    assert HV.registrar_apertura("B", "camp-1", 20261023, 150, p) == {}                # idempotente
    assert HV.problemas("B", 20261023, "camp-1", p) == []
    assert any("única apertura" in e for e in HV.problemas("B", 20261023, "camp-2", p))


def test_libro_del_repo_tiene_las_dos_miradas_exploratorias():
    fams = {r["familia"]: r for r in HV.leer() if r["tipo"] == "consumida"}
    assert fams["AREAS_EXP_1_CRUZADO"]["hasta"] == 20261022 and "EXPANSION_ZONAS" in fams["LUXIMB_FADE_VISOR"]["relacionadas"]
    assert HV.ultima_consumida("EXPANSION_ZONAS") == 20261022


def test_reuso_autorizado_solo_con_e_proceso(tmp_path):
    p = _libro(tmp_path)
    with p.open("a") as f: f.write(json.dumps({"tipo": "reuso_autorizado", "familia": "A", "desde": 20261001}) + "\n")
    assert HV.problemas("A", 20261001, "c1", p, estadistico="e_proceso") == []
    assert any("e_proceso" in e for e in HV.problemas("A", 20261001, "c1", p))
    assert HV.problemas("B", 20261001, "c1", p, estadistico="e_proceso")           # la derivada no hereda el reuso
