import json

from edgelab.research import ideas as I


def _f(i, clase, prior="medio", estado="PROPUESTA", mec=None):
    return dict(id=i, titulo=f"idea {i}", fuente_tipo="literatura", fuentes=["x"], clase=clase, mecanismo=mec or f"mecanismo único {i} {clase}",
                justificacion_economica="j", como_refutarla="r", traduccion="t", activos=["A"], horizonte="días", prior=prior, estado=estado)


def test_valida_y_rechaza_repetida(tmp_path):
    p = tmp_path / "b.jsonl"
    assert I.agregar(_f("A", "tendencia", mec="momentum serie tiempo indices bonos monedas"), p)["agregada"]
    r = I.agregar(_f("B", "tendencia", mec="momentum serie tiempo indices bonos monedas"), p)
    assert not r["agregada"] and r["similitud"] >= 0.6
    assert I.validar(dict(_f("C", "inexistente"))) and len(I.leer(p)) == 1


def test_lote_balancea_clases_y_prior():
    B = [_f("T1", "tendencia", "alto"), _f("T2", "tendencia", "alto"), _f("R1", "reversion", "bajo"), _f("E1", "estacionalidad", "medio"),
         _f("X", "evento", estado="EN_PRUEBA")]
    ids = [x["id"] for x in I.lote(3, B)]
    assert len(set(x["clase"] for x in I.lote(3, B))) == 3 and "X" not in ids and ids.count("T1") + ids.count("T2") == 1


def test_banco_real_valido():
    for f in I.leer(): assert not I.validar(f), f["id"]
    assert json.dumps(I.resumen_para_agente())
