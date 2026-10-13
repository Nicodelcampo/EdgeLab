import numpy as np
from edgelab.research import ema_zones as Z


def _series(n=6000, seed=3):
    rng = np.random.default_rng(seed); c = np.cumsum(rng.standard_normal(n) * 0.4); c[2000:3200] -= np.linspace(0, 120, 1200) + 0 * c[2000:3200]; c[3200:] -= 120    # tramo bajista sostenido
    return c, c + 1.0, c - 1.0


def test_state_flags_sustained_trend_not_noise():
    c, h, l = _series(); P = Z.precompute(c, h, l, 200, 100); st = Z.state(P, M=150, K=100, f=0.9, er=0.5, dmin=1, cv=0.5, hold=30, drift_atr=0.5)
    assert (st[2400:3100] == -1).mean() > 0.5 and (st[:1500] != 0).mean() < 0.2 and set(np.unique(st)) <= {-1, 0, 1}


def test_score_and_match_roundtrip():
    c, h, l = _series(); P = Z.precompute(c, h, l, 200, 100); st = Z.state(P, M=150, K=100, f=0.9, er=0.5, dmin=1, cv=0.5, hold=30, drift_atr=0.5)
    s = Z.score(st, [(2400, 3100, -1)]); assert s["recall_mean"] > 0.5 and 0 <= s["flagged"] < 0.6
    x = np.arange(400); t = dict(hi=(-(c[2300:2700]) - 1).tolist(), lo=(-(c[2300:2700]) + 1).tolist(), ema=(-P["e"][2300:2700]).tolist(), blue=dict(x0=50, x1=300))
    m = Z.match(t, c, P["e"], scales=[1.0], topk=1)[0]; assert abs(m["start"] - 2300) <= 3 and Z.target_range(t, m)[0] - 2350 <= 3


def test_trendline_is_a_tangent_mostly_not_crossed_by_price():
    rng = np.random.default_rng(7); n = 400; base = 100 - 0.2 * np.arange(n) + np.cumsum(rng.standard_normal(n) * 0.3); hi = base + 0.5 + rng.random(n); lo = base - 0.5
    r = Z.fit_trendline(hi, lo, -1, p=5, tol=0.8, vmax=0.05, min_touches=3)
    assert r is not None and r["slope"] < 0 and r["touches"] >= 3 and r["violations"] <= 0.02 * (n - r["i"])
    up = Z.fit_trendline(200 - hi, 200 - lo, 1, p=5, tol=0.8, min_touches=3)                               # espejo: soporte por mínimos
    assert up is not None and up["slope"] < 0 or up is None
    flat = Z.fit_trendline(np.full(200, 10.0) + rng.random(200) * 0.1, np.full(200, 9.0), -1, p=5, tol=0.05, min_touches=3); assert flat is None or flat["slope"] < 0


def test_gap_envelope_constant_channel_vs_converging():
    n = 600; t = np.arange(n); e = 100 - 0.1 * t
    rng = np.random.default_rng(2); chan = e - (20 + 6 * np.sin(t / 12.0)) + rng.standard_normal(n) * 0.2                    # canal paralelo a la EMA: distancias extremas constantes
    conv = e - (40 * (1 - t / n) + 5 + 4 * np.sin(t / 12.0))                                                                 # el precio converge hacia la EMA: la distancia cae
    a, b = Z.gap_envelope(chan, e, -1), Z.gap_envelope(conv, e, -1)
    assert Z.envelope_ok(a, 0.3, 0.4) and not Z.envelope_ok(b, 0.3, 0.4) and a["far_cv"] < b["far_cv"]


def test_rolling_r2_straight_vs_curved_ema():
    t = np.arange(400.0); straight = 100 - 0.1 * t + np.random.default_rng(0).standard_normal(400) * 0.01; curved = 100 - 0.00045 * (t - 200) ** 2
    r1, r2 = Z.rolling_r2(straight, 100), Z.rolling_r2(curved, 100)
    assert np.nanmin(r1[99:]) > 0.995 and np.nanmin(r2[99:]) < np.nanmin(r1[99:]) and np.isnan(r1[98])
    sl = np.polyfit(np.arange(100.0), straight[:100], 1); ref = 1 - np.sum((straight[:100] - np.polyval(sl, np.arange(100.0))) ** 2) / np.sum((straight[:100] - straight[:100].mean()) ** 2)
    assert abs(r1[99] - ref) < 1e-9                                                                                          # coincide con el R² clásico
