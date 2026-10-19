"""Tests del kernel EspejoImpulsos (registro ESPEJO-IND §3.6): determinismo, anti-lookahead, estados y censo cerrado."""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.bridge.indicators import espejo_impulsos as K

P = dict(max_bars=10, min_w=17.0, ref_min=3)


def _bars(path, session=None, vol=None):
    """Velas desde una secuencia de cierres (ticks): O = cierre anterior, H/L = max/min de O y C."""
    C = np.asarray(path, float)
    O = np.r_[C[0], C[:-1]]
    H = np.maximum(O, C); L = np.minimum(O, C)
    t = np.arange(len(C)) * 60.0
    V = np.ones(len(C)) * 10 if vol is None else np.asarray(vol, float)
    s = np.array(["s1"] * len(C)) if session is None else np.asarray(session)
    return t, O, H, L, C, V, s


def _ruta(*tramos, start=108.0):
    out = [start]
    for dest, n in tramos:
        out += list(np.linspace(out[-1], dest, n + 1)[1:])
    return out


def _key(e):
    return {k: ("nan" if isinstance(v, float) and v != v else (round(float(v), 9) if isinstance(v, float) else v))
            for k, v in e.items()}


def _kinds(res, iid=0):
    return [e["kind"] for e in res["events"] if e["imp_id"] == iid]


def test_espejo_completo():
    # calma, impulso 100→130, vuelta que llega a 100
    r = _ruta((100, 12), (130, 6), (100, 10), (101, 5))
    res = K.run(*_bars(r), params=P)
    k = _kinds(res)
    assert k[0] == "IMP_CONFIRMED" and "MIRROR_CANDIDATE" in k and k[-1] == "MIRROR_COMPLETED"


def test_extremo_nuevo():
    r = _ruta((100, 12), (130, 6), (120, 3), (140, 4), (138, 3))
    res = K.run(*_bars(r), params=P)
    assert _kinds(res)[-1] == "MIRROR_FAILED"
    assert [e for e in res["events"] if e["kind"] == "MIRROR_FAILED"][0]["reason"] == "new_extreme"


def test_vencimiento_por_horizonte():
    # la vuelta llega a 0,5 y se queda quieta: vence por 3 × duración
    r = _ruta((100, 12), (130, 6), (115, 4), (115, 60))
    res = K.run(*_bars(r), params=P)
    ev = [e for e in res["events"] if e["imp_id"] == 0]
    assert ev[-1]["kind"] == "MIRROR_EXPIRED" and ev[-1]["reason"] == "horizon"


def test_vuelta_que_no_llega_a_x025():
    # retrocede 0,3 (confirma) pero no llega a 0,25? 0,3 ≥ 0,25: forzamos vuelta mínima con retr 0,3 y x 0,35
    r = _ruta((100, 12), (130, 6), (121, 2), (121, 60))
    res = K.run(*_bars(r), params=dict(P, xs=(0.35, 0.5, 0.75)))
    ev = [e for e in res["events"] if e["imp_id"] == 0]
    assert ev[-1]["kind"] == "IMP_NO_MIRROR"


def test_fin_de_sesion_y_serie_cortada():
    r = _ruta((100, 12), (130, 6), (115, 4), (115, 5))
    b = _bars(r)
    res = K.run(*b, params=P)                       # sin calendario: última vela del arreglo queda abierta
    assert res["impulses"][0]["estado_final"] is None
    last = np.zeros(len(r), bool); last[-1] = True
    res2 = K.run(*b, last_of_session=last, params=P)
    ev = [e for e in res2["events"] if e["imp_id"] == 0]
    assert ev[-1]["kind"] == "MIRROR_EXPIRED" and ev[-1]["reason"] == "session_end"


def _serie_larga(seed=7, n_ses=6, n=400):
    rng = np.random.default_rng(seed)
    C = []; S = []
    for s in range(n_ses):
        x = np.cumsum(rng.standard_t(3, n) * 2.0) + 1000
        C += list(np.round(x)); S += [f"d{s}"] * n
    C = np.asarray(C)
    O = np.r_[C[0], C[:-1]]
    H = np.maximum(O, C) + rng.integers(0, 3, len(C)); L = np.minimum(O, C) - rng.integers(0, 3, len(C))
    t = np.arange(len(C)) * 60.0
    V = rng.integers(5, 50, len(C)).astype(float)
    return t, O, H, L, C, V, np.asarray(S)


def test_determinismo():
    b = _serie_larga()
    r1 = K.run(*b, params=P); r2 = K.run(*b, params=P)
    assert [_key(e) for e in r1["events"]] == [_key(e) for e in r2["events"]] and len(r1["impulses"]) > 5


@pytest.mark.parametrize("j", [450, 1300, 2011])
def test_anti_lookahead(j):
    b = _serie_larga()
    full = K.run(*b, params=P)
    cut = K.run(*(x[:j] for x in b), params=P)
    assert [_key(e) for e in full["events"] if e["bar"] < j] == [_key(e) for e in cut["events"] if e["bar"] < j]


def test_censo_cerrado():
    b = _serie_larga()
    last = np.zeros(len(b[0]), bool); last[:-1] = b[6][1:] != b[6][:-1]; last[-1] = True
    res = K.run(*b, last_of_session=last, params=P)
    for imp in res["impulses"]:
        finales = [e for e in res["events"] if e["imp_id"] == imp["imp_id"] and e["kind"] in K.FINAL]
        assert len(finales) == 1 and imp["estado_final"] == finales[0]["kind"]


def test_zona_no_lista_marca_el_tramo_sin_volumen():
    # impulso 100→130: el tramo 110→122 se cruza en una sola vela con volumen mínimo
    r = list(np.linspace(108, 100, 12)) + [103, 106, 110, 122, 125, 128, 130] + list(np.linspace(130, 105, 8)[1:])
    vol = [10.0] * len(r)
    vol[15] = 0.1                                   # la vela 110→122
    res = K.run(*_bars(r, vol=vol), params=P)
    imp = res["impulses"][0]
    assert imp["no_lista_lo"] is not None and imp["no_lista_lo"] >= 109 and imp["no_lista_hi"] <= 123
    assert imp["no_lista_frac"] > 0.2


def test_paridad_con_detect_var():
    """El detector portado da exactamente los mismos impulsos que `tools/espejo_macro.py::detect_var`."""
    pytest.importorskip("numba")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import espejo_macro as EM
    t, O, H, L, C, V, _ = _serie_larga(seed=3, n_ses=1, n=3000)
    for e0 in (0.3, 0.6):
        thr = np.full(len(C), 17.0)
        ref = EM.detect_var(t, H, L, C, 10, thr, e0, 0.3)
        got = K.detect(t, H, L, C, V, thr, K.params_of(dict(P, e_min=e0)))
        assert len(got) == len(ref) > 10
        for g, r in zip(got, ref):
            assert (g["d"], g["a"], g["ext"], g["i0"], g["iext"], g["jconf"], g["why"]) == \
                (r[0], r[1], r[2], r[3], r[4], r[5], r[8])


def test_impulso_que_termina_con_la_sesion():
    # el impulso y su confirmación caen en la última vela de la sesión: no puede quedar abierto
    r = _ruta((100, 12), (130, 6)) + [121.0]
    b = _bars(r)
    last = np.zeros(len(r), bool); last[-1] = True
    res = K.run(*b, last_of_session=last, params=P)
    assert res["impulses"] and all(m["estado_final"] is not None for m in res["impulses"])


# ---------------------------------------------------------------- semejanza v2 por niveles
def _ultimo_evento(r, vol=None):
    res = K.run(*_bars(r, vol=vol), params=dict(P, max_bars=16))
    ev = [e for e in res["events"] if e["imp_id"] == 0 and e["kind"] in ("MIRROR_CANDIDATE", "MIRROR_PROGRESS")]
    return ev[-1]


IMPULSO = list(np.linspace(108, 100, 8)) + [103, 106, 109, 111, 111, 111, 111, 114, 118, 122, 126, 130]


def test_espejo_exacto_es_casi_identico():
    vuelta = [126, 122, 118, 114, 111, 111, 111, 111, 109, 106, 103, 100]
    e = _ultimo_evento(IMPULSO + vuelta)
    assert e["x"] == 0.75
    assert e["sim_t"] > 0.85 and e["sim_v"] > 0.85 and e["sim_vel"] > 0.8


def test_pausa_en_otro_nivel_baja_la_semejanza_por_nivel():
    espejo = [126, 122, 118, 114, 111, 111, 111, 111, 109, 106, 103, 100]
    otra = [126, 122, 120, 120, 120, 120, 117, 114, 110, 106, 103, 100]   # misma duración, pausa en 120 y no en 111
    e1, e2 = _ultimo_evento(IMPULSO + espejo), _ultimo_evento(IMPULSO + otra)
    assert e1["sim_vel"] == pytest.approx(e2["sim_vel"], abs=0.2)     # misma velocidad media
    assert e1["sim_t"] - e2["sim_t"] > 0.15                            # la forma por nivel las separa


def test_vuelta_de_una_vela_marca_forma_no_fiable_pero_mide_por_nivel():
    e = _ultimo_evento(IMPULSO + [100, 100])
    assert e["velas_vuelta"] <= 2 and e["forma_fiable"] is False
    assert e["sim_t"] == e["sim_t"] and e["sim_vel"] < 0.3               # definida, y rapidísima frente al impulso
