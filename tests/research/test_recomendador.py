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
    assert _c(diferencia=0.05, por_activo={"NQ": {"diferencia": 0.12, "se": 0.03}, "ES": {"diferencia": -0.10, "se": 0.03}})["categoria"] == "INCONSISTENTE"
    r = _c(diferencia=0.05, compuerta_ok=False, n_min=60, mde80=0.30)
    assert r["categoria"] == "SIN_MUESTRA" and "más" in r["proximo_paso"]


def test_prioridad_y_orden():
    rec = RC.recomendar([dict(B, nombre="a", diferencia=0.05), dict(B, nombre="b", diferencia=0.12, ic90=[0.07, 0.17], media_a=0.15),
                         dict(B, nombre="c", diferencia=0.0, ic90=[-0.04, 0.04])])
    assert [x.split(" ")[0] for x in rec["que_hacer_despues"]] == ["b", "a"]               # c descartada no aparece
    assert "umbral económico" in [r for r in rec["items"] if r["nombre"] == "b"][0]["lectura"]
    assert "Qué hacer después" in RC.markdown("t", rec, "x.json")


def test_signo_y_error_por_activo_caso_real_20261110():
    """El primer resultado real (HFTC_info.json): real PEOR que el control, y un activo chico y ruidoso de signo opuesto."""
    reb = dict(B, nombre="rebote", diferencia=-0.021, ic90=[-0.043, 0.001], se=0.0134, mde80=0.033, por_activo={
        "ES": {"diferencia": -0.004, "se": 0.036}, "GC": {"diferencia": -0.020, "se": 0.019}, "NQ": {"diferencia": -0.027, "se": 0.023},
        "YM": {"diferencia": -0.007, "se": 0.10}})
    assert RC.clasificar(reb)["categoria"] == "DESCARTAR"                                   # con potencia, lo esperado no aparece
    iman = dict(B, nombre="iman", diferencia=-0.014, ic90=[-0.033, 0.004], se=0.011, mde80=0.028, por_activo={
        "NQ": {"diferencia": -0.027, "se": 0.023}, "YM": {"diferencia": 0.091, "se": 0.072}})
    assert RC.clasificar(iman)["categoria"] == "DESCARTAR"                                  # YM no es firme con su propio error
    assert RC.clasificar(dict(reb, ic90=[-0.05, -0.01]))["categoria"] == "EN_CONTRA"
    assert RC.clasificar(dict(reb, diferencia=0.05, ic90=[-0.01, 0.10], signo_esperado=0))["categoria"] == "INDAGAR"


def test_inconsistente_va_antes_que_en_contra():
    it = dict(B, nombre="D6", diferencia=-0.104, ic90=[-0.18, -0.027], se=0.047, mde80=0.116,
              por_activo={"NQ": {"diferencia": -0.122, "se": 0.05}, "ES": {"diferencia": 0.515, "se": 0.15}})
    assert RC.clasificar(it)["categoria"] == "INCONSISTENTE"
