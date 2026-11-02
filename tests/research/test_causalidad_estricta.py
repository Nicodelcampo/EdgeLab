"""Ninguna corrida puede mirar el futuro (2026-11-02, Nico). La prueba por disparo (cortar en la vela de cada disparo) detecta el
look-ahead de la versión vieja de `areas_expansion.disparos`, que los cortes fijos no veían; `disparos` es causal por defecto;
la versión vieja no se puede usar sin pedirlo explícitamente; y el lanzamiento se niega a correr un experimento no causal."""
import sys
import types

import numpy as np
import pandas as pd
import pytest

from edgelab.research import areas_expansion as AX, embudo_runners as ER, grilla_generica as GG, indicadores as I, preflight as PF
from edgelab.research import sintetico, u1_indaga as U

_C = {}


def _ctx():
    if "c" not in _C: _C["c"] = GG.contexto_m1(sintetico.bloques(dias=150, planta=False, seed=11), tick=0.25)
    return _C["c"]


def test_la_prueba_por_disparo_detecta_el_lookahead_viejo_y_aprueba_el_causal(monkeypatch):
    monkeypatch.setenv("EDGELAB_REPRODUCIR_LOOKAHEAD", "1")
    assert I.causal_por_disparo(lambda cx: U.disparos(cx, causal=False), _ctx())          # la vieja mira el futuro
    assert I.causal_por_disparo(lambda cx: U.disparos(cx), _ctx()) == []                   # la de siempre, no


def test_disparos_es_causal_y_la_vieja_esta_bloqueada(monkeypatch):
    assert AX.disparos.__doc__.lstrip().startswith("Desde el 2026-11-02 es la versión CAUSAL")
    monkeypatch.delenv("EDGELAB_REPRODUCIR_LOOKAHEAD", raising=False)
    with pytest.raises(ValueError, match="mira el futuro"):
        U.disparos(_ctx(), causal=False)


@pytest.mark.causalidad_real
def test_el_lanzamiento_se_niega_a_correr_un_experimento_que_mira_el_futuro(monkeypatch, tmp_path):
    monkeypatch.setattr(PF, "CERTIFICADOS", tmp_path / "cert.json")
    mod = types.ModuleType("exp_mira_futuro")

    def disparos(ctx):                                   # dispara en k si el cierre de 30 velas después es más alto: futuro puro
        c = np.asarray(ctx["c"]); k = np.flatnonzero(c[30:] > c[:-30] + 2.0)[::50]
        return pd.DataFrame(dict(k=k, lado=np.ones(len(k), int)))
    mod.disparos = disparos
    monkeypatch.setitem(sys.modules, "exp_mira_futuro", mod)
    with pytest.raises(ER.NoCausal, match="no se lanza"):
        ER.exigir_causalidad("exp_mira_futuro")
    mod2 = types.ModuleType("exp_sin_disparos"); monkeypatch.setitem(sys.modules, "exp_sin_disparos", mod2)
    with pytest.raises(ER.NoCausal, match="no expone"):
        ER.exigir_causalidad("exp_sin_disparos")


def test_runners_llaman_al_candado():
    import inspect
    assert "exigir_causalidad" in inspect.getsource(ER.KaggleRunner.lanzar)
    assert "exigir_causalidad" in inspect.getsource(ER.LocalRunner.lanzar)
