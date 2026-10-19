import numpy as np
from edgelab.research import ema_zone_desc as D, ema_zones as Z


def _fake_rows(n=120, seed=1):
    rng = np.random.default_rng(seed); rows = []
    for i in range(n):
        t = i % 3; L = [150, 300, 600][t] + int(rng.integers(-20, 20))
        rows.append(dict(contract="C", session=f"2026-0{1 + i // 40}-{1 + i % 28:02d}", dir=1 if rng.random() < .5 else -1, start_hour=int(rng.integers(0, 24)), weekday=int(rng.integers(0, 5)), len=L, minutes=L / 3, move_atr=10 + t * 8 + rng.random(), move_pts=30.0,
                         slope_atr_bar=0.05 + 0.02 * t + rng.random() * 0.005, touches=3 + t, touch_per_100=1.0, gap_mean_atr=2 + t + rng.random(), near_far_ratio=0.3 + 0.1 * t, far_cv=.3, near_cv=.4, atr_pts=5 + rng.random() * 5, activity=3.0, rth_frac=0.5,
                         bars_last_touch_to_end=20, end_reason="ruptura", range_pos_start=.5, start_bar=i * 1000, end_bar=i * 1000 + L))
    return rows


def test_summarize_recovers_planted_types_and_is_json_safe():
    import json
    s = D.summarize(_fake_rows(), k=3); json.dumps(s, default=float)
    assert s["n_zones"] == 120 and s["direction"]["up"] + s["direction"]["down"] == 120 and sum(t["n"] for t in s["typology_kmeans"]["types"].values()) == 120
    lens = sorted(t["len_median"] for t in s["typology_kmeans"]["types"].values()); assert lens[0] < 200 < lens[1] < 400 < lens[2]                                 # recupera los 3 tipos sembrados
    assert 0 <= s["sequence"]["same_direction_share"] <= 1 and s["distributions"]["len"]["n"] == 120


def test_window_stats_bands_and_reach():
    n = 50; c = np.arange(n, dtype=float); h = c + 1; l = c - 1; sd = np.array(["d"] * n); bar_start = np.arange(n + 1) * 2
    price = np.repeat(np.arange(n * 2 // 2, dtype=float), 2)[: n * 2]; vol = np.ones(len(price))                                             # 2 ticks por barra, precio = índice de barra
    w = D._window_stats(10.0, 4.0, +1, 10, 20, bar_start, price, vol, h, l, sd, n)
    assert w is not None and w[2] == 1.0 and w[3] == 0.0                                                                                       # tendencia alcista: llegó más allá, no volvió adentro
    assert w[0] > 0 and w[1] == 0 and D._window_stats(10.0, 4.0, +1, 45, 20, bar_start, price, vol, h, l, sd, n) is None                       # sin barras suficientes → None
