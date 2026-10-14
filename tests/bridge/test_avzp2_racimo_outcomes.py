"""Prueba sintética de `outcomes` (stage1 de la réplica AVZP2) con la carrera O6 de reversión interna agregada por la auditoría externa.
No usa datos de mercado: barras construidas a mano. Carga el script por ruta (no es un paquete)."""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def _load_stage1():
    os.environ.setdefault("AVCL_OUT", tempfile.mkdtemp(prefix="avzp2_test_"))
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("avzp2_stage1_under_test", ROOT / "tools" / "avzp2_racimo_replica_stage1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S1 = _load_stage1()


def bars(closes, highs=None, lows=None):
    cl = np.asarray(closes, np.int64)
    hi = np.asarray(highs if highs is not None else closes, np.int64)
    lo = np.asarray(lows if lows is not None else closes, np.int64)
    return hi, lo, cl, np.zeros(len(cl), np.int64)          # send constante = misma sesión


class OutcomesO6(unittest.TestCase):
    # caja [100, 110], centro 105. Sale por arriba en te=3 con cierre 115 -> d_in = 10: revertir a 105 vs continuar a 125.
    BASE = [105, 106, 107, 115]

    def run_case(self, tail_hi, tail_lo):
        closes = self.BASE + [112] * len(tail_hi)
        highs = self.BASE + list(tail_hi)
        lows = self.BASE + list(tail_lo)
        hi, lo, cl, send = bars(closes, highs, lows)
        return S1.outcomes(hi, lo, cl, send, 0, 100, 110, len(cl))

    def test_devuelve_siete_valores_y_sale_por_arriba(self):
        r = self.run_case([116], [112])
        self.assertEqual(len(r), 7)
        self.assertEqual((r[0], r[1]), (3, 1))                 # te=3, dir=+1

    def test_reversion_al_centro_primero(self):
        self.assertEqual(self.run_case([116, 117], [112, 104])[6], 1)     # el mínimo toca 105 antes de que el máximo llegue a 125

    def test_continuacion_externa_primero(self):
        self.assertEqual(self.run_case([116, 126], [112, 111])[6], 0)

    def test_mismo_bar_es_ambiguo(self):
        self.assertEqual(self.run_case([126], [104])[6], -2)

    def test_sin_salida_devuelve_menos_uno(self):
        r = S1.outcomes(*bars([105] * 10), 0, 100, 110, 10)
        self.assertEqual((r[0], r[6]), (-1, -1))

    def test_corta_en_el_cambio_de_sesion(self):
        closes = self.BASE + [112, 112]
        hi, lo, cl, send = bars(closes, self.BASE + [116, 126], self.BASE + [112, 104])
        send[5:] = 1                                           # el cambio de sesión ocurre antes de que se cumpla cualquier barrera
        self.assertEqual(S1.outcomes(hi, lo, cl, send, 0, 100, 110, len(cl))[6], -1)


if __name__ == "__main__":
    unittest.main()
