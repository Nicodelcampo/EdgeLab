import numpy as np
from edgelab.bridge.bars import BarSeries, TotalFootprintCSR
from edgelab.research import violet_zones as V


def make(n, hi, lo, cl, fp_cells):
    """fp_cells: {bar: [(tick, vol), ...]}; todas las demás barras sin volumen."""
    off, ticks, vols = [0], [], []
    for b in range(n):
        for t, v in sorted(fp_cells.get(b, [])): ticks.append(t); vols.append(v)
        off.append(len(ticks))
    z = np.zeros(n, dtype=np.int64)
    bars = BarSeries(start_ns=z, end_ns=z, open_t=np.asarray(cl, dtype=np.int64), high_t=np.asarray(hi, dtype=np.int64), low_t=np.asarray(lo, dtype=np.int64), close_t=np.asarray(cl, dtype=np.int64),
                     volume=np.zeros(n), tick_size=0.1, kind="tick", param=25, tick_bar_idx=z)
    return bars, TotalFootprintCSR(offsets=np.array(off, dtype=np.int64), ticks=np.array(ticks, dtype=np.int64), vols=np.array(vols, dtype=np.float64))


def zone(bar, lo, hi, score=1000.0): return dict(bar=bar, low_tick=lo, high_tick=hi, score=score)


def path(n, ups):  # cierre/high/low planos en 100 y saltos indicados {bar: precio}
    p = np.full(n, 100); [p.__setitem__(slice(b, None), v) for b, v in sorted(ups.items())]; return p


def test_quick_far_low_volume_departure_is_purple():
    n = 10; p = path(n, {3: 150}); b, f = make(n, p + 1, p - 1, p, {})                  # la zona 90-95 queda abajo; el precio sube a 150 (alejamiento 55 ≥ 40) sin volumen dentro
    v = V.violet([zone(0, 90, 95)], b, f); assert v.direction[0] == 1 and v.departed[0] and v.purple[0] and v.decision_bar[0] == 3 and v.ratio[0] == 0.0


def test_departure_with_much_traded_volume_is_not_purple():
    n = 10; p = path(n, {4: 150}); b, f = make(n, p + 1, p - 1, p, {1: [(92, 900.0)], 2: [(93, 900.0)]})              # ratio 1,8 > 0,35 de calentamiento
    v = V.violet([zone(0, 90, 95)], b, f); assert v.departed[0] and not v.purple[0] and v.ratio[0] > 1.0


def test_slow_departure_and_close_through_are_not_purple():
    n = 60; p = path(n, {45: 150}); b, f = make(n, p + 1, p - 1, p, {}); v = V.violet([zone(0, 90, 95)], b, f)
    assert v.decided[0] and not v.departed[0] and not v.purple[0] and v.decision_bar[0] == 30                               # no se alejó en 30 barras
    q = path(10, {2: 80, 5: 150}); b2, f2 = make(10, q + 1, q - 1, q, {}); w = V.violet([zone(0, 90, 95)], b2, f2); assert not w.departed[0] and not w.purple[0]  # cierre por debajo de la zona antes de alejarse


def test_adaptive_threshold_keeps_about_target_share():
    n = 4000; ups, cells, zs = {}, {}, []
    for k in range(60):                                                                                   # 60 zonas que se alejan, con ratios crecientes 0,0 ... 5,9
        b0 = k * 60; zs.append(zone(b0, 90, 95, 100.0)); ups[b0 + 2] = 150; ups[b0 + 20] = 100; cells[b0 + 1] = [(92, 10.0 * k)]
    p = path(n, ups); b, f = make(n, p + 1, p - 1, p, cells); v = V.violet(zs, b, f)
    assert v.departed.sum() == 60 and v.purple[:4].all() and not v.purple[-10:].any() and v.purple.sum() <= 0.2 * 60 + 4        # calentamiento (ratio ≤ 0,35) y luego ≈ 20 % de las alejadas como máximo


def test_zone_events_symmetric_barriers_and_death():
    n = 8; p = path(n, {2: 150, 4: 140}); b, f = make(n, p + 1, p - 1, p, {}); v = V.violet([zone(0, 90, 95)], b, f)
    price = np.array([100, 100, 100, 150, 150, 150, 130, 118, 100, 95, 95, 95], dtype=np.int64); bar_start = np.array([0, 3, 4, 5, 6, 7, 8, 12, 12]); cl = np.array([100, 100, 150, 150, 150, 130, 95, 95])
    zn = zone(0, 90, 95); rows = V.zone_events(zn, 1, 2, price, bar_start[:9], np.full(8, 7), cl, [20], lambda D: [(20, 20), (10, 20)])
    assert rows[0][3] == 1 and rows[0][4] == 20.0                                                         # D=20 (dist 25 → 20): llega al borde de la zona antes que +20 alejándose
