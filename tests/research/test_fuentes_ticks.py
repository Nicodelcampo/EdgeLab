"""Los kernels no cargan config/costos: la copia de la fricción en fuentes_ticks debe valer lo mismo que edgelab.costos."""
import pytest

from edgelab import costos as C
from edgelab.research import fuentes_ticks as F


def test_friccion_de_los_kernels_es_la_canonica():
    _, tick, base, extra = F.FUENTES["NQ"]
    assert tick == C.tick_size("NQ")
    assert base == pytest.approx(C.friccion_rt_puntos("NQ", "base"), abs=1e-9)
    assert base + extra == pytest.approx(C.friccion_rt_puntos("NQ", "adverso"), abs=1e-9)
    assert F.FUENTES["USATECH"][2:] == F.FUENTES["NQ"][2:]                 # CFD: referencia con los costos de NQ


def test_ventana_que_toca_el_holdout_falla():
    with pytest.raises(ValueError):
        next(F.bloques_nq(20260901, 20261001, entrada="/no/existe"))
