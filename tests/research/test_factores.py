"""Registro de factores con ventaja y cierre de ciclo (campaña cerrada → meta-analista → registro)."""
import json
import re
from pathlib import Path

import pytest

from edgelab.research import factores as F

ROOT = Path(__file__).resolve().parents[2]


def test_documento_generado_al_dia_y_evidencia_existe():
    assert F.SALIDA.read_text(encoding="utf-8") == F.markdown(), "correr: python tools/factores.py --write"
    es = F.cargar(); assert es and len({e["id"] for e in es}) == len(es)
    for e in es:
        assert e["estado"] in F.ESTADOS and e["siguiente"].strip()
        for p in e["evidencia"]: assert (ROOT / p).exists(), f"{e['id']}: falta {p}"


def test_registrar_valida_y_reemplaza(tmp_path):
    libro = tmp_path / "f.jsonl"; base = dict(fecha="2026-11-09", estado="PISTA_VIVA", factor="x", efecto="+0,1 R", donde="NQ", evidencia=["CLAUDE.md"], siguiente="réplica", libro=libro)
    F.registrar(id="A", **base)
    with pytest.raises(ValueError): F.registrar(id="A", **base)                                  # id repetido
    with pytest.raises(ValueError): F.registrar(id="B", **dict(base, evidencia=["no/existe.md"]))  # evidencia inexistente
    with pytest.raises(ValueError): F.registrar(id="B", **dict(base, estado="GANADORA"))           # estado inventado
    F.registrar(id="B", reemplaza="A", **dict(base, estado="NO_REPETIR"))
    assert [e["id"] for e in F.cargar(libro)] == ["B"] and "NO_REPETIR" in F.markdown(libro)


def test_cierre_de_ciclo_toda_carpeta_de_resultado_nueva_esta_en_el_registro():
    """Desde el 2026-11-09, una carpeta docs/research/*_AAAAMMDD con RESULTADO* tiene que estar citada en el registro (aunque sea como
    SIN_FACTOR): es la forma de que lo aprendido no quede suelto."""
    citadas = {p for e in F.cargar() for p in e["evidencia"]}
    faltan = []
    for d in sorted((ROOT / "docs/research").iterdir()):
        m = re.search(r"_(20\d{6})$", d.name)
        if d.is_dir() and m and m.group(1) >= "20261109" and any(d.glob("RESULTADO*")):
            if not any(c.startswith(f"docs/research/{d.name}/") for c in citadas): faltan.append(d.name)
    assert not faltan, f"resultados sin asentar en docs/research/FACTORES.jsonl (python tools/factores.py agregar): {faltan}"


def test_el_embudo_deja_pendiente_y_el_meta_analista_lo_asienta(tmp_path):
    from edgelab.autopilot import meta_analisis as MA
    raiz = tmp_path / "embudo"; (raiz / "ZGAP-NQ").mkdir(parents=True)
    (raiz / "ZGAP-NQ" / "META_PENDIENTE.json").write_text(json.dumps(dict(cid="ZGAP-NQ", final="PISTAS_VIVAS", motivo="sin potencia", ts=0)))
    (raiz / "ZGAP-NQ" / "estado.json").write_text(json.dumps(dict(etapa="FIN", fase="PISTAS_VIVAS", historial=[], spec={"cid": "ZGAP-NQ"})))
    (raiz / "ZGAP-NQ" / "RECOMENDACIONES_rebotes.md").write_text("1. D1 (INDAGAR, prioridad 2.1): dosis-respuesta por visita")

    class Runner:
        def __init__(self): self.entradas = []
        def call(self, rol, entrada):
            self.entradas.append((rol, entrada))
            return dict(status="OK", output=dict(factores=[dict(factor="gap chico", evidencia="celda 3", efecto_r="+0,04 R", donde="NQ", confianza="baja",
                                                                 siguiente_indagacion="réplica abr–sep")], que_no_repetir=[], prioridad_siguiente="réplica"))
    r = Runner(); libro = tmp_path / "prop.jsonl"
    hechos = MA.procesar(r, raiz, libro=libro, hoy="2026-11-09")
    assert hechos == [dict(cid="ZGAP-NQ", estado="ASENTADO", factores=1)] and not MA.pendientes(raiz)
    rol, entrada = r.entradas[0]
    assert rol == "meta_analista" and "errores_y_guardas" in entrada["nucleo_proyecto"] and entrada["factores_vigentes"] == []
    assert "INDAGAR" in entrada["recomendaciones"]["RECOMENDACIONES_rebotes.md"]
    assert "metodo_de_investigacion" in entrada["nucleo_proyecto"]
    e = F.cargar(libro)[0]; assert e["estado"] == "PROPUESTO_META" and e["origen"] == "meta_analista" and e["evidencia"] == ["config/autopilot/grillas/campanas/ZGAP-NQ.json"]


def test_la_lente_prioriza_lo_ya_descubierto():
    from edgelab.autopilot.contexto import elegir_lente
    assert elegir_lente([], pistas_vivas=2) == "indagar_factor"
    assert elegir_lente([{"lente": "indagar_factor"}], pistas_vivas=2) != "indagar_factor"      # alterna: no deja de explorar
    assert elegir_lente([], pistas_vivas=0) != "indagar_factor"
    assert elegir_lente([{"lente": "indagar_factor"}], pistas_vivas=2, remediciones=5) == "remedir"   # re-medir entra en la rotación
    assert elegir_lente([{"lente": "remedir"}, {"lente": "indagar_factor"}], pistas_vivas=2, remediciones=5) != "remedir"


def test_ninguna_entrada_se_reemplaza_a_si_misma():
    """Una entrada con `reemplaza` igual a su propio id desaparecería del registro (cargar filtra los ids reemplazados)."""
    import json
    from pathlib import Path
    es = [json.loads(l) for l in (Path(__file__).resolve().parents[2] / "docs/research/FACTORES.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert not [e["id"] for e in es if e.get("reemplaza") == e["id"]]
