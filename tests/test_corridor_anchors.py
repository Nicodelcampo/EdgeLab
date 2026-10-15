import importlib.util
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parents[1] / "tools" / "corridor_anchors.py"
spec = importlib.util.spec_from_file_location("corridor_anchors", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_banda_del_sector_suba_y_baja():
    assert m.sector_band(100.0, 140.0, +1) == (130.0, 150.0)     # ultimo 25 % del alto + 25 % mas alla del maximo
    assert m.sector_band(100.0, 140.0, -1) == (90.0, 110.0)      # simetrico en una baja


def test_poc_y_area_de_valor_en_un_perfil_conocido():
    tick = 0.25
    px = np.array([100.00] * 10 + [100.25] * 40 + [100.50] * 30 + [100.75] * 15 + [101.00] * 5)    # POC en 100.25
    vol = np.ones_like(px)
    r = m.sector_anchors(px, vol, tick, 100.0, 101.0, +1)
    assert r["poc"] == 100.25 and r["total"] == 100.0
    assert r["va_low"] <= 100.25 <= r["va_high"]
    assert r["va_edge"] == r["va_low"]                              # suba: borde del interior = VAL
    r2 = m.sector_anchors(px, vol, tick, 100.0, 101.0, -1)
    assert r2["va_edge"] == r2["va_high"]                           # baja: VAH


def test_area_de_valor_cubre_al_menos_el_70_por_ciento():
    rng = np.random.default_rng(3)
    px = np.round(rng.normal(100.5, 0.4, 3000) / 0.25) * 0.25
    vol = rng.integers(1, 6, 3000).astype(float)
    r = m.sector_anchors(px, vol, 0.25, 98.0, 103.0, +1)
    inside = vol[(px >= r["va_low"]) & (px <= r["va_high"])].sum()
    assert inside >= 0.70 * r["total"] - 1e-9


def test_empate_de_poc_elige_el_mas_cercano_al_centro_y_barra_de_maximo_volumen():
    px = np.array([100.0, 100.0, 101.0, 101.0])
    r = m.sector_anchors(px, np.ones(4), 0.25, 100.0, 101.0, +1,
                         bar_high=[101.0, 102.0], bar_low=[100.0, 100.0], bar_close=[100.5, 101.5], bar_volume=[10, 30])
    assert r["poc"] in (100.0, 101.0) and r["hv_bar"] == 101.0          # barra 2 = (102 + 100) / 2
    r = m.sector_anchors(px, np.ones(4), 0.25, 100.0, 101.0, +1, bar_high=[101.0, 102.0], bar_low=[100.0, 100.0], bar_close=[100.5, 101.5],
                         bar_volume=[10, 30], use_close=True)
    assert r["hv_bar"] == 101.5


def test_sin_ticks_en_la_banda_no_hay_anclas():
    assert m.sector_anchors([105.0], [3.0], 0.25, 100.0, 101.0, +1) is None
