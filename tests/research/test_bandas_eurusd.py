"""BANDAS-EURUSD: el port numba del detector de bandas da exactamente lo mismo que la referencia, y los eventos cumplen el contrato."""
import numpy as np

from edgelab.bridge.indicators import bandas_concentracion as REF
from edgelab.research import bandas_eurusd as B, grilla_generica as GG, sintetico


def _zonas(seed, n=1500, dias=3):
    rng = np.random.default_rng(seed); t0 = np.sort(rng.integers(0, dias * 86400, n)) // 60 * 60
    base = 1.10 + np.cumsum(rng.normal(0, 0.0002, n)); alto = rng.uniform(0.00005, 0.0006, n)
    return [dict(t0=int(a), t1=int(a + REF.VIDA_S), bottom=float(b), top=float(b + h)) for a, b, h in zip(t0, base, alto)], dias


def test_port_igual_a_la_referencia():
    for seed in (1, 2, 3):
        Z, dias = _zonas(seed); tiempos = list(range(0, dias * 86400, 60))
        ref = REF.detectar(Z, tiempos, alto=8 * B.PIP, umbral=8)
        zt0 = np.array([z["t0"] for z in Z], np.int64)
        bt0, bpi, bn0, eb, et = B._bandas_nb(np.array(tiempos, np.int64), zt0, zt0 + REF.VIDA_S, np.array([z["bottom"] for z in Z]),
                                             np.array([z["top"] for z in Z]), 8 * B.PIP, 8, REF.VIDA_S)
        assert len(ref) == len(bt0) and len(ref) > 3
        for i, r in enumerate(ref):
            t1 = max([r.t0] + et[eb == i].tolist()) + REF.VIDA_S
            assert (r.t0, round(r.piso, 10), r.n0, r.t1) == (int(bt0[i]), round(float(bpi[i]), 10), int(bn0[i]), int(t1))


def test_eventos_contrato_y_definiciones():
    bl = list(sintetico.bloques(dias=10, planta=False, seed=4, tick=0.00001))
    for b in bl: b["px"] = 1.10 + (b.px - b.px.iloc[0]) * 0.00001 / 0.25     # escala FX
    ctx = GG.contexto_m1(bl, tick=0.00001)
    E = B.eventos(ctx)
    assert set(["k", "lado", "ref", "ext", "rg"]) <= set(E.columns) and all(d in E for d in B.DEFINICIONES)
    if len(E):
        r = E[E.rol == "real"]; e = E[E.rol == "esp"]
        assert (np.sign(r.ref - r.ext) == r.lado).all() and (np.sign(e.ref - e.ext) == e.lado).all()
