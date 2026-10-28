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
    monkeypatch.setattr(R.subprocess, "run", salida('{"code":403,"message":"Permission \\u0027kernels.get\\u0027 was denied"}'))
    assert k.estado("nicobuttaro/x") == "error", "O14: un kernel que esta cuenta no puede ver se relanza, no se espera 14 h"


def test_campana_con_cuenta_kaggle_lanza_en_esa_cuenta(tmp_path):
    k = R.KaggleRunner(carpeta=tmp_path)
    spec = dict(cid="X5", experimento="edgelab.research.u1_zonas", sensor="ES", cuenta_kaggle="nicobuttaro")
    a = k.argumentos(spec, "DESC", dict(cortes=None), [20250801, 20260331])
    assert a[a.index("--slug") + 1].startswith("nicobuttaro/embudo-x5-desc")


def test_cuenta_auto_elige_la_menos_ocupada(tmp_path, monkeypatch):
    import json
    monkeypatch.setenv("EDGELAB_KAGGLE_CUENTAS", "nicolasbuttaro,nicobuttaro")
    raiz = tmp_path / "estado"
    for cid, h in (("A", "nicolasbuttaro/embudo-a-desc-1"), ("B", "nicolasbuttaro/embudo-b-desc-1"), ("C", "nicobuttaro/embudo-c-desc-1")):
        (raiz / cid).mkdir(parents=True); (raiz / cid / "estado.json").write_text(json.dumps(dict(fase="CORRIENDO", handle=h)))
    k = R.KaggleRunner(carpeta=tmp_path, raiz=raiz)
    assert k.ocupacion() == {"nicolasbuttaro": 2, "nicobuttaro": 1} and k.elegir_cuenta() == "nicobuttaro"
    spec = dict(cid="X6", experimento="edgelab.research.u1_zonas", sensor="ES", cuenta_kaggle="auto")
    a = k.argumentos(spec, "DESC", dict(cortes=None), [20250801, 20260331])
    assert a[a.index("--slug") + 1].startswith("nicobuttaro/embudo-x6-desc")
    assert k._env("nicobuttaro")["EDGELAB_KAGGLE_OWNER"] == "nicobuttaro"


def test_cabecera_por_cuenta(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(R.ROOT / "tools"))
    import kaggle_auth as KA
    base = tmp_path / ".kaggle_auth_header"; base.write_text("x"); (tmp_path / ".kaggle_auth_header.nicobuttaro").write_text("y")
    monkeypatch.setenv("KAGGLE_AUTH_HEADER_FILE", str(base))
    monkeypatch.setenv("EDGELAB_KAGGLE_OWNER", "nicobuttaro"); assert KA.header_file().name.endswith(".nicobuttaro")
    monkeypatch.setenv("EDGELAB_KAGGLE_OWNER", "nicolasbuttaro"); assert KA.header_file() == base


def test_slug_largo_pasa_validate_push(tmp_path):
    """2026-10-27: U1-RACIMOS-GRILLA-ES/NQ en HOLDOUT_CONTEO y AN_ANALIZAR_REGLA armaban slugs de 51-54 chars que validate_push (<=49) rechazaba."""
    import sys
    sys.path.insert(0, str(R.ROOT / "tools"))
    from kaggle_kernel import validate_push
    k = R.KaggleRunner(carpeta=tmp_path, dataset_sellado="nicolasbuttaro/edgelab-holdout-sellado")
    spec = dict(cid="U1-RACIMOS-GRILLA-ES", experimento="tests.research.exp_u1_sin_be", sensor="ES", ejecucion="ES")
    for etapa in ("HOLDOUT_CONTEO", "AN_ANALIZAR_REGLA"):
        a = k.argumentos(spec, etapa, dict(celdas=[[0]], acta=dict(cid="U1-RACIMOS-GRILLA-ES")), [20261023, 20261026])
        slug = a[a.index("--slug") + 1]
        assert len(slug.split("/")[1]) <= 49 and not slug.endswith("-")
        assert validate_push(slug, ["nicolasbuttaro/edgelab-holdout-sellado"], "nicolasbuttaro") == "nicolasbuttaro"
