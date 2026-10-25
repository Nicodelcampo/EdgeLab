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


def test_runner_sellado_solo_adjunta_el_dataset_sellado_y_exige_acta(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path, dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado")
    spec = dict(cid="X2", experimento="tests.research.exp_u1_sin_be", sensor="DK:USATECHIDXUSD", ejecucion="NQ")
    with pytest.raises(ValueError): k.argumentos(spec, "HOLDOUT_CONTEO", dict(celdas=[[0]]), [20261001, 20261020])
    a = k.argumentos(spec, "HOLDOUT_CONTEO", dict(celdas=[[0]], acta=dict(cid="X2")), [20261001, 20261020])
    assert "--need" not in a and a.count("--extra-dataset") == 1 and "nicolasbuttaro/edgelab-holdout-sellado" in a and "SELLADO=1" in a


def test_datasets_extra_de_la_campana_se_adjuntan(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path)
    spec = dict(cid="X4", experimento="edgelab.research.u1_zonas", sensor="ES", datasets_extra=["nicolasbuttaro/edgelab-zonas-avzp2"])
    a = k.argumentos(spec, "DESC", dict(cortes=None), [20250701, 20260331])
    assert "nicolasbuttaro/edgelab-zonas-avzp2" in a and a[a.index("--need") + 1] == "ES:2025-07-01:2026-03-31"


def test_kernel_sin_corridas_es_error_y_no_espera_para_siempre(monkeypatch, tmp_path):
    import subprocess
    k = R.KaggleRunner(carpeta=tmp_path)
    salida = lambda txt: (lambda *a, **kw: subprocess.CompletedProcess(a, 0, stdout=txt, stderr=""))
    monkeypatch.setattr(R.subprocess, "run", salida('{"code":404,"message":"No runs found for kernel"}'))
    assert k.estado("nicolasbuttaro/x") == "error"
    monkeypatch.setattr(R.subprocess, "run", salida('{"status":"running","failureMessage":""}'))
    assert k.estado("nicolasbuttaro/x") == "running"
