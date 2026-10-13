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
    r = Z.fit_trendline(hi, lo, -1, p=5, tol=0.8, min_touches=3)
    assert r is not None and r["slope"] < 0 and r["touches"] >= 3 and r["violations"] <= 0.10 * (n - r["i"])
    up = Z.fit_trendline(200 - hi, 200 - lo, 1, p=5, tol=0.8, min_touches=3)                               # espejo: soporte por mínimos
    assert up is not None and up["slope"] < 0 or up is None
    flat = Z.fit_trendline(np.full(200, 10.0) + rng.random(200) * 0.1, np.full(200, 9.0), -1, p=5, tol=0.05, min_touches=3); assert flat is None or flat["slope"] < 0
