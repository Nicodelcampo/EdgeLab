import numpy as np
import pandas as pd

from edgelab.research import sqx_calidad as Q


def _trades(n, media, sd=1.0, seed=0, anios=10):
    rng = np.random.default_rng(seed); t = pd.date_range("2012-01-02", periods=n, freq=f"{int(anios * 365 * 24 / n)}h")
    return pd.DataFrame(dict(openTime=t.strftime("%Y.%m.%d %H:%M:%S"), closeTime=(t + pd.Timedelta(hours=5)).strftime("%Y.%m.%d %H:%M:%S"),
                             pl=1000 * np.clip(rng.normal(media, sd, n), -1.0, None)))   # stop real: pérdidas hasta −1 R


def test_sin_nulo_queda_pendiente_y_ruido_no_vale():
    r = Q.evaluar(_trades(400, 0.3), 1000, otros_mercados=[0.1, 0.2, 0.3], reciente_r=0.2)
    assert r["veredicto"] == "PENDIENTE" and r["pendientes"] == ["nulo_busqueda"]
    assert Q.evaluar(_trades(400, 0.0, seed=1), 1000, t_nulo_p95=4.0)["veredicto"] == "NO_VALE"


def test_vale_sólo_con_todo():
    r = Q.evaluar(_trades(600, 0.35, seed=2), 1000, t_nulo_p95=3.0, reciente_r=0.2, otros_mercados=[0.1, 0.2, -0.1])
    assert r["veredicto"] == "VALE", r
    assert Q.evaluar(_trades(150, 0.35, seed=2), 1000, t_nulo_p95=1.0, reciente_r=0.2, otros_mercados=[0.1])["fallos"] == ["ops"]
