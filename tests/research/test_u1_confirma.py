"""U1-CONFIRMA: clasificación de la confirmación cruzada, causalidad del confirmador (también en el tiempo) y cableado del runner."""
import numpy as np
import pytest

from edgelab.research import grilla_generica as GG, indicadores as I, sintetico, u1_confirma as X
from edgelab.research.embudo_runners import KaggleRunner


@pytest.fixture(scope="module")
def ctx():
    c = GG.contexto_m1(sintetico.bloques(dias=70, planta=False, seed=4), tick=0.25)
    c["conf"] = GG.contexto_m1(sintetico.bloques(dias=70, planta=False, seed=5), tick=0.25)
    return c


def test_clasificar():
    rs = np.array([1.0, 1.0, 1.0, 1.0, np.nan]); rc = np.array([0.8, 0.2, -1.0, 1.0, 1.0])
    rs_p = np.array([0.0, 0.0, 0.0, 0.1, 0.0]); rc_p = np.array([0.0, 0.0, 0.0, 0.9, 0.0])
    out = X.clasificar(rs, rc, rs_p, rc_p)
    assert out[:4].tolist() == [0, 1, 1, 2] and np.isnan(out[4])


def test_sin_confirmador_falla(ctx):
    with pytest.raises(ValueError, match="confirmador"):
        X.disparos({k: v for k, v in ctx.items() if k != "conf"})


def test_disparos_son_los_de_u1_cfd_con_conf(ctx, monkeypatch):
    monkeypatch.setattr(X, "_disparos", lambda c: __import__("edgelab.research.u1_cfd", fromlist=["x"]).disparos(c, r_ref=1.0))
    D = X.disparos(ctx)
    assert len(D) and set(np.unique(D.conf[np.isfinite(D.conf)])) <= {0, 1, 2}


def test_causal_tambien_en_el_confirmador(ctx, monkeypatch):
    from edgelab.research import u1_cfd
    monkeypatch.setattr(X, "_disparos", lambda c: u1_cfd.disparos(c, r_ref=1.0))
    assert I.causal(X.disparos, ctx, columnas=["k", "lado", "esc", "conf"]) == []
    def con_futuro(c):                                                    # control: mirar el confirmador futuro debe detectarse
        D = X.disparos(c); return D.assign(conf=float(len(c["conf"]["c"])))
    assert I.causal(con_futuro, ctx, columnas=["k", "conf"]) != []


def test_runner_agrega_dataset_y_entorno(monkeypatch):
    r = KaggleRunner.__new__(KaggleRunner); r.dataset_sellado = None; r.owner = "x"
    monkeypatch.setattr(r, "_construir", lambda spec: "k.py", raising=False)
    spec = dict(cid="C", experimento="edgelab.research.u1_confirma", sensor="DK:EURUSD", ejecucion="DK:EURUSD", confirmador="DK:GBPUSD", cuenta_kaggle="x")
    a = r.argumentos(spec, "DESC", {}, [20240102, 20240131])
    assert "nicolasbuttaro/edgelab-dukascopy-6b-gbpusd" in a and "CONFIRMADOR=DK:GBPUSD" in a
