"""Regresión: el reloj L2 debe conservar indexación posicional NumPy."""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.data.l2 import _a_microsegundos


def test_a_microsegundos_devuelve_ndarray_y_admite_indice_negativo():
    ts = pd.Series(["20260609090000", "20260609090001"])
    usec = pd.Series([100, 200])

    result = _a_microsegundos(ts, usec)

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.dtype(np.int64)
    assert int(result[0] % 1_000_000) == 100
    assert int(result[-1] % 1_000_000) == 200
    assert int(result[-1] - result[0]) == 1_000_100
