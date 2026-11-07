"""El índice que el tablero llama 3R y NR es la tupla de EJECUCIONES, no el texto viejo."""
from edgelab.research.absorcion_climax import EJECUCIONES as ABS
from edgelab.research.compresion_nr import EJECUCIONES as NR


def test_absorcion_indice_3_es_stop_1_3_y_objetivo_3_5():
    assert ABS[3] == ("ATR", 1.3, 3.5)
    assert ("ATR", 1.3, 3.0) not in ABS


def test_compresion_indice_1_es_caja_1_y_objetivo_4():
    assert NR[1] == ("CAJA", 1.0, 4.0)
