"""Reutilizar antes de construir (tools/existente.py): el catálogo de tools/ está al día y no aparecen funciones copiadas."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("existente", ROOT / "tools" / "existente.py")
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)

ORIGINAL = '''
def one(d, ts, ask, bid):
    """Una sesión."""
    mid = (ask + bid) / 2
    b0 = d * 1000
    w = (ts >= b0) & (ts < b0 + 60)
    if w.sum() < 50:
        return None
    ie = ts.searchsorted(b0)
    ix = ts.searchsorted(b0 + 60)
    return (bid[ie] - ask[ix]) / 0.1, mid[ie]
'''
COPIA = ORIGINAL.replace("def one(d, ts, ask, bid)", "def una_sesion(dia, t, a, b)").replace("ts", "t").replace("ask", "a").replace("bid", "b").replace("mid", "m").replace('"""Una sesión."""', '"""Copiada con otros nombres."""')


def _repo(tmp, archivos):
    for rel, src in archivos.items():
        p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(src, encoding="utf-8")
    return tmp


def test_detecta_copia_con_otros_nombres(tmp_path):
    r = _repo(tmp_path, {"tools/a.py": ORIGINAL, "edgelab/research/b.py": COPIA, "tools/c.py": "def corta(x):\n    return x + 1\n"})
    g = E.clones(r)
    assert list(g.values()) == [["edgelab/research/b.py::una_sesion", "tools/a.py::one"]]
    assert E.clones_nuevos(g, {}) == g and E.clones_nuevos(g, g) == {}
    otra = dict(g); otra["x"] = g[next(iter(g))] + ["tools/d.py::otra_copia"]
    assert E.clones_nuevos(otra, g)                                     # sumar una copia a un grupo viejo también cuenta


def test_ignora_kernels_generados(tmp_path):
    r = _repo(tmp_path, {"tools/a.py": ORIGINAL, "tools/kaggle_grilla/kernel_x.py": E.GENERADO + " ...\n" + ORIGINAL})
    assert E.clones(r) == {}


def test_buscar_encuentra_por_docstring_y_nombre(tmp_path):
    r = _repo(tmp_path, {"tools/lector.py": '"""Lee ticks de Dukascopy del parquet de Kaggle."""\ndef bloques_spot(s):\n    """Spot por día."""\n',
                         "tools/otro.py": '"""Grafica la curva de capital."""\n'})
    res = E.buscar("lector de ticks dukascopy", k=3, root=r)
    assert res and res[0]["ref"].startswith("tools/lector.py")


def test_repo_sin_copias_nuevas():
    nuevos = E.clones_nuevos(E.clones(), json.loads(E.BASELINE.read_text(encoding="utf-8")))
    assert not nuevos, "función copiada (importá la original): " + "; ".join(" = ".join(v) for v in nuevos.values())


def test_catalogo_al_dia():
    assert E.CATALOGO.read_text(encoding="utf-8") == E.catalogo(), "script nuevo: python tools/existente.py catalogo --write (y mirá qué ya existía)"
