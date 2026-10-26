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


def _oraculo(steps, senales, tick):
    from edgelab.research import sim
    sig = [dict(signal_id=f"s{i}", available_at=int(s["available_at"]), dir=int(s["dir"]),
                target_ticks=max(1, int(round(s["target_pts"] / tick))), stop_ticks=max(1, int(round(s["stop_pts"] / tick))),
                time_stop_ms=int(float(s.get("time_stop_min") or 0) * 60_000)) for i, s in enumerate(senales)]
    return pd.DataFrame(sim.simulate(sig, steps, scenario="ideal", tick_size=tick, tick_value=1.0).trades)


@pytest.mark.parametrize("modo", ["ticks", "barras"])
def test_nucleo_compilado_identico_a_sim(modo):
    r = np.random.default_rng(7); tick = 0.25
    t0 = pd.Timestamp("2025-03-03 14:30", tz="UTC").value // 10**6
    n = 6000; ts = t0 + np.cumsum(r.integers(1, 4000, n)); ses = 20250303 + np.arange(n) // 1500   # 4 sesiones
    px = 20000 + np.round(np.cumsum(r.normal(0, 1, n)) / tick) * tick
    if modo == "ticks":
        lo = hi = px; steps = [dict(ts=int(a), last=b, bid=b, ask=b, session_id=int(c)) for a, b, c in zip(ts, px, ses)]
    else:
        hi = px + np.round(r.uniform(0, 3, n) / tick) * tick; lo = px - np.round(r.uniform(0, 3, n) / tick) * tick
        steps = [dict(ts=int(a), last=b, bid=b, ask=b, low=l, high=h, session_id=int(c)) for a, b, l, h, c in zip(ts, px, lo, hi, ses)]
    av = np.sort(r.choice(ts, 400)); av[::7] = av[::7] - 1                     # empates y bordes
    sen = [dict(available_at=int(a), dir=int(r.choice([1, -1])), target_pts=float(r.integers(1, 30)) * tick, stop_pts=float(r.integers(1, 30)) * tick,
                time_stop_min=float(r.choice([0, 5, 30]))) for a in av]
    T = A.Mercado(ts, px, lo, hi, ses, tick).simular(sen, 0.0)
    O = _oraculo(steps, sen, tick)
    assert len(T) == len(O) > 50
    for c in ("signal_id", "entry_ts", "exit_ts", "exit_reason", "dir"): assert (T[c].to_numpy() == O[c].to_numpy()).all(), c
    for c in ("bruto_ticks", "mae_ticks", "mfe_ticks"): assert np.allclose(T[c].to_numpy(float), O[c].to_numpy(float)), c
    assert np.allclose(T.entry_px, O.entry_px) and np.allclose(T.exit_px, O.exit_px)


def test_barras_vectorizadas_iguales_a_contexto_m1():
    from edgelab.research import grilla_generica as GG
    bl = _ticks()
    B0 = A.barras_de_contexto(GG.contexto_m1(bl, 0.25))
    _, B1 = A.Mercado.de_ticks(bl, 0.25, con_barras=True)
    pd.testing.assert_frame_equal(B0.reset_index(drop=True)[["ts", "o", "h", "l", "c", "ses"]], B1[["ts", "o", "h", "l", "c", "ses"]], check_dtype=False)
    assert np.allclose(B0.v.to_numpy(), B1.v.to_numpy())
