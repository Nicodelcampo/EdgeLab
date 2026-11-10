"""Recomendador: cada patrón de resultado cae en su categoría y deja un próximo paso concreto."""
from edgelab.research import recomendador as RC

B = dict(se=0.03, mde80=0.075, ic90=[-0.02, 0.08], compuerta_ok=True, n_min=500, por_activo={}, sugerencia="mirar X")


def _c(**k): return RC.clasificar(dict(B, nombre="v", **k))


def test_categorias():
    assert _c(diferencia=0.15, ic90=[0.10, 0.20], nominada=True, por_activo={"NQ": 0.14, "ES": 0.16})["categoria"] == "CONFIRMAR"
    assert _c(diferencia=0.05)["categoria"] == "INDAGAR"                                   # ≥ MDE/2 sin confirmar
    assert _c(diferencia=0.01, ic90=[-0.03, 0.05])["categoria"] == "DESCARTAR"            # con potencia y chico
    assert _c(diferencia=0.01, mde80=0.20, se=0.08, ic90=[-0.1, 0.12])["categoria"] == "NO_CONCLUYENTE"
    assert _c(diferencia=0.10, control_diferencia=0.08)["categoria"] == "ESTRUCTURA_DE_PRECIO"
    assert _c(diferencia=0.05, por_activo={"NQ": 0.12, "ES": -0.10})["categoria"] == "INCONSISTENTE"
    r = _c(diferencia=0.05, compuerta_ok=False, n_min=60, mde80=0.30)
    assert r["categoria"] == "SIN_MUESTRA" and "más" in r["proximo_paso"]


def test_prioridad_y_orden():
    rec = RC.recomendar([dict(B, nombre="a", diferencia=0.05), dict(B, nombre="b", diferencia=0.12, ic90=[0.07, 0.17], media_a=0.15),
                         dict(B, nombre="c", diferencia=0.0, ic90=[-0.04, 0.04])])
    assert [x.split(" ")[0] for x in rec["que_hacer_despues"]] == ["b", "a"]               # c descartada no aparece
    assert "umbral económico" in [r for r in rec["items"] if r["nombre"] == "b"][0]["lectura"]
    assert "Qué hacer después" in RC.markdown("t", rec, "x.json")
