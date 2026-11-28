import numpy as np
import pandas as pd
import pytest

from edgelab.research.alineacion_horaria import exigir_alineada, exigir_cierre_causal_diario, mejor_desfase


def _serie(seed=0, n=2000):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2026-07-01 13:30", periods=n, freq="1min", tz="UTC")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 1e-3, n))), index=t)


def test_detecta_desfase_de_una_hora():
    ref = _serie()
    fuente = ref.copy()
    fuente.index = fuente.index + pd.Timedelta(minutes=60)    # sello adelantado 1 h (el caso HistData en verano)
    k, c = mejor_desfase(fuente, ref)
    assert k == 60 and c > 0.99
    with pytest.raises(ValueError, match="K58"):
        exigir_alineada(fuente, ref)


def test_detecta_desfase_fino_un_minuto():
    ref = _serie()
    fuente = ref.copy()
    fuente.index = fuente.index + pd.Timedelta(minutes=1)
    with pytest.raises(ValueError, match="K58"):
        exigir_alineada(fuente, ref)


def test_exigir_cierre_causal_diario_asx_vs_vix():
    # ASX cierra 06:00 UTC; CBOE VIX cierra 20:15 UTC el mismo día (look-ahead)
    with pytest.raises(ValueError, match="K58-D1"):
        exigir_cierre_causal_diario(20.25, 6.0, "^VIX", "ASX200")
    # ^AXVI cierra simultáneo a las 06:00 UTC
    exigir_cierre_causal_diario(6.0, 6.0, "^AXVI", "ASX200")


def test_alineada_pasa_y_ruido_no():
    ref = _serie()
    assert exigir_alineada(ref, ref) > 0.99
    with pytest.raises(ValueError, match="K58"):
        exigir_alineada(_serie(seed=1), ref)
