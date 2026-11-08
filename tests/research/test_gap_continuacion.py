import numpy as np
import pandas as pd

from edgelab.research import gap_continuacion as X


def _ctx(gap_dia, toca):
    t, c = [], []
    dias = pd.bdate_range("2025-07-01", periods=18)
    for k, d in enumerate(dias):
        base = 100.0 + (gap_dia if k == len(dias) - 1 else 0.0)
        for m in range(9 * 60 + 29, 16 * 60):
            ts = pd.Timestamp(d.date()).tz_localize("America/New_York") + pd.Timedelta(minutes=m + 1)
            p = base + (0.01 * (m - 600) if k == len(dias) - 1 else 0.0)
            if toca and k == len(dias) - 1 and m == 9 * 60 + 45: p = 100.0
            t.append(int(ts.timestamp())); c.append(p)
    c = np.array(c); t = np.array(t)
    return dict(t=t, c=c, h=c + 1, l=c - 1, tstart=np.arange(len(c) + 1), tpx=c.copy())


def test_continuacion_largo_y_riesgo():
    R = X.operaciones(_ctx(10.0, False))
    assert len(R) and (R.lado == 1).all()
    r = R[R.celda.apply(lambda c: c[1] == "cierre")]
    assert np.allclose(r.riesgo, r.bruto * 0 + r.riesgo) and (r.riesgo > 9).all()
    fin = R[R.celda.apply(lambda c: c[2] == 999)]
    assert (fin.bruto > 0).all()                       # el precio sube hasta el cierre


def test_gap_tocado_no_opera():
    R = X.operaciones(_ctx(10.0, True))
    assert not len(R)
