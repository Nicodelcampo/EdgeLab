import math

from edgelab.funnel.metaanalisis import _chi2_cdf, combinar


def test_iguales_suma_precision():
    f = [dict(instrumento=i, media=1.0, ic90=[0.0, 2.0], n=100) for i in ("ES", "NQ", "YM", "RTY")]
    r = combinar(f)
    assert r["I2"] == 0 and math.isclose(r["fijo"]["se"], (2 / (2 * 1.6448536)) / 2, rel_tol=1e-9)
    assert r["fijo"]["p_unilateral"] < combinar(f[:1])["fijo"]["p_unilateral"]


def test_signos_opuestos_heterogeneidad_y_aleatorio_mas_ancho():
    r = combinar([dict(media=3.0, ic90=[2.0, 4.0]), dict(media=-3.0, ic90=[-4.0, -2.0])])
    assert r["I2"] > 0.9 and r["decide"] == "aleatorio" and r["aleatorio"]["se"] > r["fijo"]["se"]


def test_chi2():
    assert math.isclose(_chi2_cdf(3.841458820694124, 1), 0.95, abs_tol=1e-6)


def test_desde_estados_del_embudo(tmp_path):
    import json, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import metaanalisis_embudo as ME
    for cid, m in (("A", 1.0), ("B", 2.0)):
        (tmp_path / cid).mkdir(); (tmp_path / cid / "estado.json").write_text(json.dumps(dict(atras=dict(veredictos=[dict(celda=[1], media=m, ic90=[m - 1, m + 1], n=50)]))))
    f = ME.filas(tmp_path, ["A:0", "B:0"], "atras")
    assert [x["media"] for x in f] == [1.0, 2.0] and combinar(f)["k"] == 2
