"""Calibración de las reglas de cuenta de tools/lucid_canastas._sim (K28) con casos que se calculan a mano."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "tools"))


def _corre(x, cons=0.5, dll=0.0, pol_max=True, dias=60):
    import lucid_canastas as LC
    cob, pas, pg, de, df = LC._sim(np.asarray(x, np.float64), float(np.mean(x)), 1, 1, dll, cons, pol_max, dias)
    return cob[0], pas[0], pg[0], de[0], df[0]


def test_K28_calibracion_reglas_de_la_cuenta():
    cob, pas, pg, de, df = _corre([300.0] * 10)          # +300 fijos: evaluación en 5 días (1.500 ≥ 1.250, mayor día 20 %)
    assert pas == 1 and de == 5
    assert pg == 5 and abs(cob - 5 * 900.0) < 1e-6        # fondeada: retira 1.000 cada vez que el saldo llega a 2.000 con 5 días ≥ 100
    cob, pas, pg, de, df = _corre([-300.0] * 10)         # −300 fijos: −1.200 ≤ −1.000 al día 4
    assert pas == 0 and de == 4 and cob == 0
    cob, pas, pg, de, df = _corre([1300.0, 0.0, 0.0, 0.0, 0.0] * 2, dias=4)   # un solo día de 1.300 = 100 % > 50 %: no pasa en 4 días
    assert pas == 0
    cob, pas, pg, de, df = _corre([-900.0] * 10, dll=600.0)                 # DLL blando: cada día pierde 600, se pierde la cuenta al 2.º
    assert pas == 0 and de == 2
    cob_min, _, pg_min, _, df_min = _corre([300.0] * 40, pol_max=False)    # retirar en cuanto se puede: 750 el día 5, después 1.000 cada 5 días
    assert pg_min == 5 and df_min == 25 and abs(cob_min - 0.9 * (750 + 4 * 1000)) < 1e-6 and df_min < 27          # la política «máximo» termina el día 27 (7, 12, 17, 22, 27)
