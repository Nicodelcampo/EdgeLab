"""Analizador: usa el simulador sellado, cobra la fricción canónica una vez, registra cada variante antes de correr, frena el
holdout y una estrategia que mira adelante."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import analizador as A
from edgelab.research.estrategias import ejemplo_ruptura_rango as EJ


class Reg:
    def __init__(self): self.filas = []
    def ensure(self, cid, fam, n, nota=""): self.filas.append((cid, fam, n)); return True


def _barras(dias=30, seed=0):
    r = np.random.default_rng(seed); filas = []
    t0 = pd.Timestamp("2025-03-03 14:30", tz="UTC")
    for d in range(dias):
        p = 20000 + r.normal() * 50
        for m in range(390):
            o = p; p = p + r.normal() * 3; h, l = max(o, p) + abs(r.normal()), min(o, p) - abs(r.normal())
            ts = t0 + pd.Timedelta(days=d, minutes=m + 1)
            filas.append(dict(ts=int(ts.value // 10**6), o=o, h=h, l=l, c=p, v=1.0, ses=d))
    return pd.DataFrame(filas)


def test_ejemplo_corre_registra_y_cobra_friccion():
    reg = Reg(); B = _barras()
    out = A.analizar(EJ, 20250303, 20250430, registro=reg, B=B, tick=0.01)
    assert reg.filas and reg.filas[0][2] == 4 and out["variantes"] == 4                 # 2 x 2 variantes, registradas antes
    r = out["resultados"][0]
    assert r["n"] > 0 and "EXPLORATORIO" in out["aviso"]
    T = A.simular(B, EJ.senales(B, **out["resultados"][0]["parametros"]), 0.01, out["friccion_pts"])
    assert np.allclose(T.neto_pts, T.bruto_pts - out["friccion_pts"])                  # la fricción una sola vez


def test_holdout_y_sin_registro_no_corren():
    with pytest.raises(ValueError): A.analizar(EJ, 20260901, 20261015, registro=Reg(), B=_barras(5), tick=0.01)
    with pytest.raises(ValueError): A.analizar(EJ, 20250303, 20250430, registro=None, B=_barras(5), tick=0.01)


class MiraAdelante:
    NOMBRE, FAMILIA, INSTRUMENTO = "TRAMPA", "TEST", "DK:USATECHIDXUSD"
    @staticmethod
    def senales(barras):
        fin = barras.c.iloc[-1]                                                       # usa el último precio del período
        return [dict(available_at=int(t), dir=1 if fin > c else -1, target_pts=5, stop_pts=5) for t, c in zip(barras.ts[::500], barras.c[::500])]


def test_look_ahead_se_detecta():
    out = A.analizar(MiraAdelante, 20250303, 20250430, registro=Reg(), B=_barras(10), tick=0.01)
    assert out["error"] == "NO CAUSAL"
