"""Cortes congelados de PRERANGE-ZONAS: `CORTES` se escribe desde el E0 sin desenlaces, antes de mirar P&L."""
_D = {"sup": [1.0, 3.0], "inf": [1.0, 3.0], "den": [1.0, 3.0]}
_C = {"sup": [[1.0, 3.0]] * 2, "inf": [[1.0, 3.0]] * 2, "den": [[1.0, 3.0]] * 2}
CORTES_PRUEBA = dict(conjuntos=["A", "B", "A+B"], dist={"A": _D, "B": _D}, cant={"A": _C, "B": _C, "A+B": _C})
CORTES = {}
