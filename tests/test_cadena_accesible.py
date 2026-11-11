"""La cadena estándar de una corrida es inconfundible y accesible para cualquier agente (pedido de Nico, 2026-11-11): está en el
núcleo de contexto de todos los roles, en las directivas, en las consignas del programador y del revisor, en el mapa de módulos, en
el catálogo de herramientas, en CLAUDE.md, y la búsqueda de reutilización la encuentra."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULOS = ["edgelab/research/ejecucion.py", "edgelab/research/tablas.py", "edgelab/research/analizar_tabla.py", "edgelab/research/plantilla_tabla.py",
           "edgelab/research/curva.py"]
HERRAMIENTAS = ["tools/tablas.py", "tools/antecedentes.py", "tools/cierre.py"]


def test_en_nucleo_directivas_consignas_y_claude():
    from edgelab.autopilot import contexto
    assert any(c == "cadena_de_corrida" and q == "todos" for c, _, q in contexto.NUCLEO_FUENTES)
    assert "tools/tablas.py" in (ROOT / "config/autopilot/DIRECTIVAS.md").read_text(encoding="utf-8")
    assert "edgelab/research/tablas.py" in (ROOT / "edgelab/autopilot/programador.py").read_text(encoding="utf-8")
    assert "cadena_de_corrida" in (ROOT / "edgelab/autopilot/roles.py").read_text(encoding="utf-8")
    assert "tools/tablas.py" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "tools/tablas.py" in (ROOT / "docs/autopilot/PROMPT_ARRANQUE_DEBIAN_20261111.md").read_text(encoding="utf-8")


def test_en_mapa_de_modulos_y_catalogo():
    mods = json.loads((ROOT / "config/modules.json").read_text(encoding="utf-8"))["modules"]
    rutas = {p for m in mods for p in m["paths"]}
    assert set(MODULOS + HERRAMIENTAS) <= rutas
    cat = (ROOT / "docs/HERRAMIENTAS.md").read_text(encoding="utf-8")
    assert all(Path(h).name in cat for h in HERRAMIENTAS)
    guia = (ROOT / "docs/research/CADENA_DE_CORRIDA.md").read_text(encoding="utf-8")
    assert all(x in guia for x in ("preflight", "lanzar", "traer", "explorar", "curva", "congelar", "confirmar", "holdout", "antecedentes", "cierre"))


def test_la_busqueda_de_reutilizacion_la_encuentra():
    sys.path.insert(0, str(ROOT / "tools"))
    from existente import buscar
    refs = lambda q: " ".join(r["ref"] for r in buscar(q, k=12))
    assert "ejecucion.py" in refs("simular operación stop objetivo parcial break even ticks")
    assert "tablas.py" in refs("tabla de eventos lanzar kernel kaggle traer")
