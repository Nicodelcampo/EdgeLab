from edgelab.funnel.libro_lord import LibroLord


def test_un_paso_por_lote_idempotente_y_por_familia(tmp_path):
    L = LibroLord(tmp_path / "lord.json")
    a = L.probar("F1", "r1", [("x", 0.5), ("y", 0.7)])
    assert a["rechazo"] is False and L.probar("F1", "r1", [("x", 0.0)]) == a        # no se vuelve a gastar
    n2 = L.nivel("F1"); assert n2 < a["nivel"]                                        # el paso 2 pide más
    assert L.nivel("F2") == a["nivel"]                                                # otra familia arranca de cero
    L2 = LibroLord(tmp_path / "lord.json"); assert L2.nivel("F1") == n2               # persistente
    r = L2.probar("F1", "r2", [("z", 1e-6)]); assert r["rechazo"] and r["confirmadas"][0]["test"] == "z"
