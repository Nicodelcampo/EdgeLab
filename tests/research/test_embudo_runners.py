"""Runner de Kaggle: datasets y fricción correctos para cualquier activo; sin costo medido no se lanza; el kernel corre."""
import pytest

from edgelab import costos as C
from edgelab.research import embudo_runners as R


def test_argumentos_cruzado_dukascopy_a_nq(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path)
    spec = dict(cid="X1", experimento="tests.research.exp_u1_sin_be", sensor="DK:USATECHIDXUSD", ejecucion="NQ")
    a = k.argumentos(spec, "DESC", dict(cortes=None), [20250805, 20260331])
    assert "--need" in a and a[a.index("--need") + 1] == "NQ:2025-08-05:2026-03-31"
    assert "nicolasbuttaro/edgelab-dukascopy-nq-usatech" in a
    env = {x.split("=", 1)[0]: x.split("=", 1)[1] for x in a[a.index("--env"):][1::2]}
    assert float(env["FRICCION"]) == pytest.approx(C.friccion_rt_puntos("NQ")) and env["SENSOR"] == "DK:USATECHIDXUSD"
    assert (tmp_path / "kernel_x1.py").exists()


def test_sin_costo_medido_no_se_lanza():
    with pytest.raises(Exception): R.friccion("ZB")
    assert R.friccion("ES")[0] == pytest.approx(C.friccion_rt_puntos("ES"))
    assert R.friccion("DK:USATECHIDXUSD")[0] == pytest.approx(C.friccion_rt_puntos("NQ"))    # spot: costo de su futuro
