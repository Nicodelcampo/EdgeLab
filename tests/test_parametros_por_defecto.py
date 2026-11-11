"""Un parámetro nuevo no se ata a una constante del módulo al importar (AUTOMATIZACION_PROCESOS_20261111 I2). El 2026-11-11
`luximb_grilla.marcas_segmento(..., amp=AMP)` rompió el oráculo: los tests cambian `AMP` con monkeypatch y el valor por defecto
seguía siendo el viejo. Regla: `param=None` y resolver la constante en la llamada. Línea base: config/defaults_baseline.json."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "config/defaults_baseline.json"


def atados() -> list:
    out = []
    for f in (ROOT / "edgelab").rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8-sig")); consts = set()
        for n in tree.body:
            if isinstance(n, ast.Assign):
                consts |= {t.id for t in n.targets if isinstance(t, ast.Name) and t.id.isupper() and len(t.id) > 1}
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in n.args.defaults + [x for x in n.args.kw_defaults if x is not None]:
                    if isinstance(d, ast.Name) and d.id in consts: out.append(f"{f.relative_to(ROOT).as_posix()}:{n.name}:{d.id}")
    return sorted(set(out))


def test_sin_parametros_nuevos_atados_a_constantes():
    base = set(json.loads(BASE.read_text(encoding="utf-8"))) if BASE.exists() else set()
    nuevos = [x for x in atados() if x not in base]
    assert not nuevos, f"usar param=None y resolver la constante en la llamada: {nuevos}"
