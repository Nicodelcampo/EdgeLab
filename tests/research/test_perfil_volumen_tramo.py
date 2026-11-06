"""Tests del filtro `PERFIL-TP`: rangos A/B, ventana causal de `n_barras` y sesión."""
from __future__ import annotations

import numpy as np

from edgelab.research import perfil_volumen_tramo as PV


def _perfil():
    # 6 velas M1; cada una negocia niveles 100.0..104.0 (paso 1.0). Sesión cambia en la vela 3.
    px, vol, start = [], [], [0]
    for k in range(6):
        for p in (100.0, 101.0, 102.0, 103.0, 104.0):
            px.append(p)
            vol.append(10.0 * (k + 1) if p >= 103.0 else 1.0)   # más volumen arriba y creciente en el tiempo
        start.append(len(px))
    ses = np.array([1, 1, 1, 2, 2, 2], np.int64)
    return dict(vp_px=np.array(px), vp_vol=np.array(vol), vp_start=np.array(start, np.int64), ses=ses)


def test_rangos_a_y_b_compra():
    ctx = _perfil()
    # compra e=100, tp=102 (D=2): A=[100,102], B=(102,104] -> 103 y 104. Ventana 1 vela (k=5): A=3*1, B=2*60
    va, vb = PV.vol_rangos(ctx, [5], [1], [100.0], [102.0], 1)
    assert va[0] == 3.0 and vb[0] == 120.0
    assert PV.pasa_perfil(va, vb, 2.0)[0]


def test_venta_y_ventana_causal():
    ctx = _perfil()
    # venta e=104, tp=102: A=[102,104] (102,103,104), B=[100,102) (100,101). k=2 con 2 velas (k=1,2): sólo mira hasta k=2
    va, vb = PV.vol_rangos(ctx, [2], [-1], [104.0], [102.0], 2)
    assert va[0] == 102.0
    assert vb[0] == 4.0                                   # 2 niveles x 2 velas x 1
    assert not PV.pasa_perfil(va, vb, 2.0)[0]


def test_sesion_y_b_sin_volumen():
    ctx = _perfil()
    # k=4 sesión 2 = velas 3,4: n_barras=0 equivale a 2 velas; con 6 velas llegaría a las de otra sesión
    va0, vb0 = PV.vol_rangos(ctx, [4], [1], [100.0], [101.0], 0)
    va2, vb2 = PV.vol_rangos(ctx, [4], [1], [100.0], [101.0], 2)
    assert va0[0] == va2[0] and vb0[0] == vb2[0]
    # B fuera del rango negociado (tp=104 -> B=(104,108]) => vol 0, no pasa
    va, vb = PV.vol_rangos(ctx, [4], [1], [100.0], [104.0], 0)
    assert vb[0] == 0.0 and not PV.pasa_perfil(va, vb, 2.0)[0]
