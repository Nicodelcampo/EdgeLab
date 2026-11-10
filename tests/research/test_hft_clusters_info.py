"""HFT-CLUSTERS-INFO: carrera tras el toque, placebo, causalidad por prefijo y elección mecánica de la definición."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import hft_clusters_info as H

S = 1_000_000_000


def _camino(precios, paso_s=1.0, t0=1_700_000_000 * S):
    px = np.asarray(precios, float); ts = t0 + (np.arange(len(px)) * paso_s * S).astype(np.int64)
    return ts, px


def test_carrera_rebote_y_atraviesa_solo_con_ticks_posteriores():
    # cluster [100, 102]; sube a 113 (se aleja 10), vuelve a 102 (toca), rebota a 122
    ts, px = _camino([101, 105, 113, 108, 102, 110, 122, 130])
    assert H.carrera(ts, px, int(ts[0]), 100.0, 102.0, 10.0, 20.0) == (1, 1)
    # mismo camino hasta el toque y después lo atraviesa hasta 82
    ts, px = _camino([101, 105, 113, 108, 102, 95, 82, 70])
    assert H.carrera(ts, px, int(ts[0]), 100.0, 102.0, 10.0, 20.0) == (1, -1)
    # sin alejamiento no hay evento; y un cluster detectado DESPUÉS del alejamiento no lo puede usar
    ts, px = _camino([101, 103, 104, 103, 102, 101])
    assert H.carrera(ts, px, int(ts[0]), 100.0, 102.0, 10.0, 20.0) is None
    ts, px = _camino([101, 105, 113, 108, 102, 110, 122, 130])
    assert H.carrera(ts, px, int(ts[3]), 100.0, 102.0, 10.0, 20.0) is None      # desde t3 nunca se aleja 10 antes de tocar


def test_carrera_no_cambia_al_agregar_futuro_mas_alla_del_horizonte():
    base = [101, 105, 113, 108, 102, 110, 122]
    ts, px = _camino(base); r = H.carrera(ts, px, int(ts[0]), 100.0, 102.0, 10.0, 20.0)
    ts2, px2 = _camino(base + [50.0] * 20)                                       # futuro agregado después de resuelta la carrera
    assert H.carrera(ts2, px2, int(ts2[0]), 100.0, 102.0, 10.0, 20.0) == r == (1, 1)


def test_barrera_cumple_la_friccion_maxima():
    for fr, tk in ((1.5455, 0.25), (0.8877, 0.25), (5.052, 1.0), (0.605, 0.1)):
        X = H.barrera(fr, tk); assert fr / X <= H.FRICCION_R_MAX + 1e-9 and abs(X / tk - round(X / tk)) < 1e-9


def test_contraste_detecta_un_efecto_plantado_y_no_inventa_uno():
    rng = np.random.default_rng(1); filas = []
    for f in range(120):
        for _ in range(3): filas.append(dict(fecha=20250801 + f, placebo=0, resultado=1 if rng.random() < 0.65 else -1))
        for _ in range(12): filas.append(dict(fecha=20250801 + f, placebo=1, resultado=1 if rng.random() < 0.5 else -1))
    c = H.contraste(pd.DataFrame(filas), n_boot=2000)
    assert c["diferencia"] > 0.15 and c["p_unilateral"] < 0.01
    nulo = pd.DataFrame([dict(fecha=20250801 + f, placebo=k % 2, resultado=1 if rng.random() < 0.5 else -1) for f in range(120) for k in range(10)])
    assert H.contraste(nulo, n_boot=2000)["p_unilateral"] > 0.05


def test_elegir_definicion_es_mecanica_y_sin_retornos():
    f = lambda inst, ck, n: [dict(inst=inst, fecha=20250800 + 100 * m + d, zona="Z_CERT", cluster=ck, n=n(m, d)) for m in range(4) for d in range(1, 21)]
    E0 = pd.DataFrame(f("NQ", "estable_2", lambda m, d: 2) + f("NQ", "estable_6", lambda m, d: 6) + f("NQ", "inestable", lambda m, d: 8 if m == 0 else 0)
                      + f("ES", "rara", lambda m, d: 1 if d == 1 else 0))
    e = H.elegir_definicion(E0)
    assert e["NQ"]["cluster"] == "estable_2" and "ES" not in e                   # ES: < 0,5 por sesión → afuera
    assert "resultado" not in E0.columns


def test_clusters_del_dia_es_causal_por_prefijo():
    """Lo detectado hasta el tick N no cambia al agregar ticks después (la guarda que faltaba en la propuesta original)."""
    spec = importlib.util.spec_from_file_location("t", Path(__file__).resolve().parents[1] / "bridge/test_hftzones_nq_rangos_pct_v2.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    ts, pt, vol = m._stream_sintetico_complejo(seed=7, n=6000); px = pt * 0.25; ses = np.zeros(len(ts), np.int64)
    largo = H.clusters_del_dia(ts, px, vol, ses, 0.25); n = 4000; corto = H.clusters_del_dia(ts[:n], px[:n], vol[:n], ses[:n], 0.25)
    assert largo, "el stream sintético tiene que producir algún cluster"
    for k, C in largo.items():
        antes = C[C.t_ns < ts[n - 50]].reset_index(drop=True)                    # margen: la última racha del prefijo queda censurada
        c2 = corto.get(k, pd.DataFrame(columns=C.columns)); c2 = c2[c2.t_ns < ts[n - 50]].reset_index(drop=True)
        pd.testing.assert_frame_equal(antes, c2, check_dtype=False)
