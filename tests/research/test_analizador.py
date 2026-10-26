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
    out = A.analizar(EJ, 20250303, 20250430, registro=reg, B=B, tick=0.01, resolucion="m1")
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


def _ticks():
    from edgelab.research import sintetico
    return list(sintetico.bloques(dias=12, planta=False, seed=4))


def test_ticks_y_m1_dan_las_mismas_senales_y_resultados_parecidos():
    from edgelab.research import grilla_generica as GG
    bl = _ticks(); B = A.barras_de_contexto(GG.contexto_m1(bl, 0.25))
    ot = A.analizar(EJ, 20250303, 20250430, registro=Reg(), B=B, tick=0.25, friccion_pts=1.0, fuente_ticks=lambda: iter(bl))
    om = A.analizar(EJ, 20250303, 20250430, registro=Reg(), B=B, tick=0.25, friccion_pts=1.0, resolucion="m1")
    assert ot["resolucion"] == "ticks" and om["resolucion"] == "m1"
    for rt, rm in zip(ot["resultados"], om["resultados"]):
        assert rt["n"] > 0 and abs(rt["n"] - rm["n"]) <= max(2, 0.2 * rm["n"])


def test_ticks_resuelven_la_barra_ambigua():
    """Objetivo y stop dentro del mismo minuto: con ticks sale por el que se tocó primero (en M1 esa barra sería ambigua y ganaría
    el adverso)."""
    t0 = pd.Timestamp("2025-03-03 15:00", tz="UTC").value
    ts = np.array([t0 + k * 1_000_000_000 for k in range(130)], np.int64)       # 1 tick por segundo
    px = np.r_[np.full(60, 100.0), [100.0, 100.0, 103.0, 98.0], np.full(66, 99.0)]   # entra a 100; en el mismo minuto 103 (objetivo) y 98 (stop)
    bl = [pd.DataFrame(dict(ts_ns=ts, px=px, vol=np.ones(130), sesion=np.full(130, 20250303), segmento=np.zeros(130, np.int64)))]
    from edgelab.research import grilla_generica as GG
    B = A.barras_de_contexto(GG.contexto_m1(bl, 0.25))
    sen = [dict(available_at=int(B.ts.iloc[0]), dir=1, target_pts=2.5, stop_pts=1.5)]
    Tt = A.simular_ticks(iter(bl), A._con_sesion(B, sen), 0.25, 0.0)
    assert Tt.entry_px.iloc[0] == 100.0 and Tt.exit_reason.iloc[0] == "target" and Tt.exit_ts.iloc[0] == ts[62] // 10**6
    assert Tt.neto_pts.iloc[0] == 2.5
