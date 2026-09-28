"""AGOT-EXT: la construcción de eventos no mira el futuro (manifiesto §8).

Se arma una sesión sintética; después se alteran los precios a partir de un instante T y se recalcula. Los eventos con
entrada anterior a T tienen que ser idénticos en su DEFINICIÓN (momento, instante, lado, tramo, riesgo, divergencias).
Los resultados de esos eventos sí pueden cambiar, porque miran hacia adelante a propósito."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import agotamiento as AG  # noqa: E402

NS = 1_000_000_000
KEYS = ["res", "moment", "side", "mult", "t_event", "tramo", "risk", "div14", "div7", "div21", "div_delta", "entry"]


def _session(seed=7, n=60_000):
    r = np.random.default_rng(seed)
    ts = (1_700_000_000 * NS + np.cumsum(r.integers(200_000_000, 2_500_000_000, n))).astype(np.int64)  # ~23 h
    steps = r.choice([-1, 0, 1], size=n, p=[0.35, 0.3, 0.35])
    drift = np.sin(np.arange(n) / 2500.0) * 0.08                   # ondas para que haya tramos y extremos
    px = (100_000 + np.cumsum(steps + (r.random(n) < np.abs(drift)) * np.sign(drift))).astype(np.int64)
    vol = r.integers(1, 6, n).astype(float)
    ag = np.where(r.random(n) < 0.5, 1, -1).astype(np.int8)
    bid, ask = px - (ag == 1), px + (ag == -1)
    return ts, px, vol, bid.astype(np.int64), ask.astype(np.int64), ag


def _defs(rows, t_cut):
    return sorted(tuple(r[k] for k in KEYS) for r in rows if r["t_event"] + AG.LAT_NS < t_cut)


def test_los_eventos_previos_a_T_no_cambian_si_cambia_el_futuro():
    ts, px, vol, bid, ask, ag = _session()
    end = int(ts[-1]) + NS
    cfg = dict(comm=0.5, delta_ok=True)
    base = AG.compute_events(ts, px, vol, bid, ask, ag, end, cfg)
    assert len(base) > 20, "el fixture tiene que producir eventos"
    # varios cortes a lo largo de la sesión: una filtración de pocas velas tiene que caer cerca de alguno
    for frac in np.linspace(0.15, 0.9, 16):
        t_cut = int(ts[int(len(ts) * frac)])
        k = int(np.searchsorted(ts, t_cut))
        for kind in ("salto", "espejo"):
            px2, bid2, ask2 = px.copy(), bid.copy(), ask.copy()
            if kind == "salto":                                      # un salto enorme después de T
                px2[k:] += 500; bid2[k:] += 500; ask2[k:] += 500
            else:                                                    # el futuro al revés: cada paso con el signo cambiado
                ref = px[k - 1]
                px2[k:] = 2 * ref - px[k:]; bid2[k:] = px2[k:] - (ag[k:] == 1); ask2[k:] = px2[k:] + (ag[k:] == -1)
            ag2 = ag.copy(); ag2[k:] *= -1                           # y el agresor invertido
            alt = AG.compute_events(ts, px2, vol, bid2, ask2, ag2, end, cfg)
            assert _defs(base, t_cut) == _defs(alt, t_cut), f"el corte {frac:.2f} ({kind}) cambió eventos anteriores"


def test_cada_pivote_se_confirma_en_la_primera_vela_que_cumple_la_regla():
    """Propiedad directa del zigzag: la confirmación ocurre en la PRIMERA vela posterior al extremo cuyo retroceso
    alcanza max(2, 0,3*tramo) con tramo >= max(4, 1,5*ATR). Confirmar antes sería usar el futuro; después, perder
    eventos. Atrapa mutaciones de tiempo que el test de caja negra puede no ver."""
    ts, px, vol, bid, ask, ag = _session(seed=11)
    B = AG.time_bars(ts, px, vol, ag, 60)
    atr = AG.atr_wilder(B["h"], B["l"], B["c"])
    piv = AG.zigzag_adaptive(B, atr)
    assert len(piv) > 10
    H, L = B["h"].astype(int), B["l"].astype(int)
    for p in piv:
        d, piv_p, ext_p, tot = p["dir"], p["a"], p["b"], p["tot"]
        assert tot == abs(ext_p - piv_p)
        for j in range(p["i_ext"] + 1, p["i_conf"] + 1):
            retr = (ext_p - L[j]) if d == 1 else (H[j] - ext_p)
            mn = max(AG.MIN_TICKS, AG.K_ATR * atr[j]) if np.isfinite(atr[j]) else np.inf
            cumple = tot >= mn and retr >= max(2, AG.R_RETR * tot)
            if j < p["i_conf"]:
                assert not cumple, f"el pivote {p} ya cumplía la regla en la vela {j}"
            else:
                assert cumple, f"el pivote {p} no cumple la regla en su vela de confirmación"
