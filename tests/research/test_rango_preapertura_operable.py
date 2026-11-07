"""La orden de preapertura no se queda con un tercil de ancho que nadie archivó."""
from edgelab.research.rango_preapertura_operable import COORD_ES, COORD_NQ, especificar


def test_es_es_el_primer_quiebre_y_nq_la_reentrada():
    es = especificar(COORD_ES)
    nq = especificar(COORD_NQ)
    assert es["intento"] == 0 and es["stop"] == "OPUESTO" and es["objetivo"] == "SALIDA"
    assert nq["intento"] == 1 and nq["stop"] == "OPUESTO" and nq["salida_forzada_et"] == "15:55"
    assert es["ancho_en_la_orden"] is False and nq["ancho_en_la_orden"] is False
    assert es["ancho_tercil_publicado"] == "alto"
    assert nq["ancho_tercil_publicado"] == "bajo"


def test_otra_celda_no_pasa_por_esta_traduccion():
    try:
        especificar((0, 0, 1, 0, 0, 5))
    except ValueError:
        return
    raise AssertionError("una celda distinta no puede usar esta orden")
