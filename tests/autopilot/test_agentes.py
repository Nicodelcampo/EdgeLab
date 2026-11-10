"""Fuente única de agentes (config/autopilot/AGENTES.json) y núcleo de contexto que nunca se recorta."""
import json
import re
from pathlib import Path

import pytest

from edgelab.autopilot import agentes as A, contexto as C
from edgelab.autopilot.roles import ROLES, sanitize

ROOT = Path(__file__).resolve().parents[2]


def test_roles_y_tabla_coinciden():
    assert set(ROLES) | {"programador"} == set(A.tabla()["roles"])
    for r, spec in ROLES.items():
        d = A.rol(r); assert spec["model"] == d["modelo"] and spec["daily_cap"] == d["tope_diario"]


def test_separacion_de_poderes_y_fable_en_el_arquitecto():
    assert A.modelo("proponente") == "claude-fable-5-2" == A.modelo("meta_analista") == A.modelo("abogado")
    assert A.modelo("revisor") != A.modelo("proponente") and A.modelo("revisor2") != A.modelo("revisor")
    assert A.modelo("auditor") != A.modelo("proponente")


def test_ningun_modelo_escrito_a_mano_fuera_de_la_tabla():
    patron = re.compile(r"claude-(opus|sonnet|haiku|fable)-\d")
    malos = []
    for f in list((ROOT / "edgelab/autopilot").glob("*.py")) + [ROOT / "deploy/debian/autopilot.example.json", ROOT / "tools/autopilot_generate.py"]:
        if f.name == "agentes.py": continue
        if patron.search(f.read_text(encoding="utf-8")): malos.append(f.name)
    assert not malos, f"modelo escrito a mano (va en config/autopilot/AGENTES.json): {malos}"


def test_documentacion_y_topologia_generadas_al_dia():
    from edgelab.autopilot.orquestador_multiagente import TOPOLOGIA_DEBIAN_V2
    assert (ROOT / "docs/autopilot/AGENTES.md").read_text(encoding="utf-8") == A.markdown(), "correr: python tools/agentes.py --write"
    assert json.loads((ROOT / "config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json").read_text(encoding="utf-8")) == TOPOLOGIA_DEBIAN_V2


def test_nucleo_completo_entra_y_pasa_el_saneado():
    for r in ROLES:
        n = C.nucleo(r); sanitize(n)
        if not A.rol(r)["nucleo"]: assert n == {}; continue
        for clave, ruta, quien in C.NUCLEO_FUENTES:
            f = ROOT / ruta
            if f.exists() and (quien == "todos" or (quien == "diseño" and r in C.ROLES_DISENO) or (quien == "codigo" and r == "programador")):
                assert n[clave] == C.redactar(f.read_text(encoding="utf-8")), f"{clave} recortado para {r}"
        assert len(json.dumps(n, ensure_ascii=False)) < 0.75 * A.rol(r)["contexto_max_chars"], f"el núcleo de {r} deja < 25 % para la tarea"


def test_paquete_del_proponente_trae_el_nucleo_y_recorta_solo_lo_rotativo():
    p = C.armar_paquete(tablero={}, vacios=["v" * 4000] * 40, fichas=["f" * 4000] * 40, retiradas=[], lente=next(iter(C.LENTES)))
    assert "12. **Memoria de ideas" in p["directivas_de_nico"]                      # directivas completas
    assert {"errores_y_guardas", "aprendizajes_espiral", "decisiones_de_validacion"} <= set(p["nucleo_proyecto"])
    assert len(json.dumps(p, ensure_ascii=False)) <= A.rol("proponente")["contexto_max_chars"]
    assert len(p["fichas"]) < 40                                                     # lo que cedió fue lo rotativo


def test_con_nucleo_falla_en_vez_de_recortar():
    with pytest.raises(ValueError):
        C.con_nucleo("revisor2", {"relleno": "x" * 200000})
    assert "errores_y_guardas" in C.con_nucleo("auditor", {"preregistro": "p"})["nucleo_proyecto"]


def test_redactar_deja_pasar_documentos_con_rutas():
    t = C.redactar("ver /opt/edgelab/x y E:\\EdgeLab y la password"); sanitize({"t": t})


def test_el_bloque_modelos_del_servidor_se_ignora_y_la_excepcion_vale(monkeypatch, capsys):
    from edgelab.autopilot import roles as R
    antes = R.ROLES["proponente"]["model"]; monkeypatch.setitem(R.ROLES["revisor2"], "model", R.ROLES["revisor2"]["model"])
    R.configurar_modelos({"proponente": "modelo-viejo"}, {"revisor2": "modelo-x"})
    assert R.ROLES["proponente"]["model"] == antes and R.ROLES["revisor2"]["model"] == "modelo-x" and "se ignora" in capsys.readouterr().out


def test_respaldo_si_el_cli_no_conoce_el_modelo(tmp_path):
    from edgelab.autopilot.roles import RoleRunner
    bueno = {"is_error": False, "structured_output": {"familia": "f", "mecanismo": "m", "prediccion": "p", "refutacion": "r", "parametros_libres": [], "refs": []}}
    vistos = []
    def cli(prompt, *, model, schema, system, timeout=600):
        vistos.append(model)
        return {"is_error": True, "result": "API Error: model not found"} if model == A.modelo("proponente") else bueno
    r = RoleRunner(tmp_path / "l.sqlite", cli=cli)
    assert r.call("proponente", {"x": 1})["status"] == "OK" and vistos == [A.modelo("proponente"), A.respaldo("proponente")]
