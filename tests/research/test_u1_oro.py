"""U1-ORO-GRILLA: escala causal por mes, igualdad con U1 cuando la escala es 1, causalidad y controles del preflight."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, indicadores as I, sintetico, u1_indaga as U, u1_oro as X


@pytest.fixture(scope="module")
def ctx():
    return GG.contexto_m1(sintetico.bloques(dias=70, planta=True, seed=4), tick=0.25)


def _ref(ctx):
    return float(np.median(ctx["h"] - ctx["l"]))


def test_escala_es_del_mes_anterior_y_el_primero_no_dispara(ctx):
    mes, f = X.escala_por_mes(ctx, _ref(ctx)); meses = sorted(f)
    assert np.isnan(f[meses[0]]) and all(np.isfinite(f[m]) for m in meses[1:])
    r = pd.Series(ctx["h"] - ctx["l"]).groupby(mes).median()
    assert np.isclose(f[meses[1]], r.loc[meses[0]] / _ref(ctx))
    D = X.disparos(ctx, r_ref=_ref(ctx))
    assert len(D) and not np.isin(mes[D.k.to_numpy()], [meses[0]]).any()


def test_escala_1_con_factor_1_es_u1_por_mes(ctx):
    mes, f = X.escala_por_mes(ctx, _ref(ctx))
    cx = dict(ctx, seg=mes, escala_seg={m: (1.0 if np.isfinite(v) else np.nan) for m, v in f.items()})
    a = U.disparos(cx); b = U.disparos(dict(ctx, seg=mes))
    b = b[mes[b.k.to_numpy()] != sorted(f)[0]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b, check_dtype=False)


def test_cada_escala_multiplica_el_factor_del_mes(ctx, monkeypatch):
    vistos = []
    monkeypatch.setattr(X.U, "disparos", lambda cx: vistos.append(cx["escala_seg"]) or pd.DataFrame(dict(k=[1])))
    D = X.disparos(ctx, r_ref=_ref(ctx)); _, f = X.escala_por_mes(ctx, _ref(ctx)); m = sorted(f)[1]
    assert [v[m] for v in vistos] == pytest.approx([f[m] * e for e in X.ESCALAS]) and sorted(D.esc) == [0, 1, 2]


def test_causal(ctx, monkeypatch):
    monkeypatch.setattr(X, "R_USATECH", _ref(ctx))
    assert I.causal(X.disparos, ctx, columnas=["k", "lado", "ni", "xi", "A_H", "esc"]) == []


def test_control_ruido(monkeypatch):
    from edgelab.research.preflight import dinamico
    monkeypatch.setattr(X, "R_USATECH", 1.0)
    err, _ = dinamico(X, dias=150)
    assert err == [], err
