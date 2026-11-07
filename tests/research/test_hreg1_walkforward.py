"""La regla de H-REG-1 elige la racha reciente y no se deja ganar el desempate por el nombre."""
from tools.hreg1_walkforward import _dedup, evaluar


def _regla(nombre, familia, instrumento, dias):
    return {"regla": nombre, "familia": familia, "instrumento": instrumento, "celdas": dias}


def test_dedup_se_queda_con_el_mayor_puntaje():
    a = _regla("A", "F", "NQ", {})
    b = _regla("B", "F", "NQ", {})
    c = _regla("C", "G", "ES", {})
    quedan = _dedup([(1.0, 10, "A", a), (3.0, 4, "B", b), (2.0, 9, "C", c)])
    nombres = {r["regla"] for r in quedan}
    assert nombres == {"B", "C"}


def test_evaluar_devuelve_el_contrato():
    dias = {}
    for mes in ("202508", "202509", "202510", "202511"):
        for dia in ("01", "02", "03", "04", "05", "08", "09", "10"):
            dias[mes + dia] = {"m": 0.1, "r": 0.1, "n": 1}
    reglas = [_regla(f"S{i}", f"F{i}", "NQ", dias) for i in range(4)]
    out = evaluar(reglas, 3, "202511", "202511", semilla=1)
    assert set(out) >= {"ventanas", "delta_azar", "delta_estatica", "pasa", "semilla", "B"}
    assert out["ventanas"][0]["h"] == "202511"
    assert out["ventanas"][0]["valida"] is True
    assert len(out["ventanas"][0]["elegidas"]) == 3
