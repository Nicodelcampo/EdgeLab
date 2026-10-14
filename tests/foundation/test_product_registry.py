"""El registro de modulos y el indice de documentacion deben estar al dia con el arbol real (ver docs/DOCUMENTATION_PROTOCOL.md)."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_modules = _load("check_modules")
docs_index = _load("docs_index")


def test_registro_de_modulos_valido():
    assert check_modules.validate(check_modules.load()) == []


def test_modules_md_esta_al_dia():
    esperado = check_modules.render(check_modules.load())
    actual = (ROOT / "docs" / "MODULES.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == esperado, "docs/MODULES.md desactualizado: python tools/check_modules.py --write"


def test_indice_de_docs_al_dia_y_sin_documentos_nuevos_sin_estado():
    rows = docs_index.collect(ROOT)
    assert docs_index.violations(rows) == []
    assert (ROOT / "docs" / "INDEX.csv").read_text(encoding="utf-8").replace("\r\n", "\n") == docs_index.render_csv(rows)
    assert (ROOT / "docs" / "INDEX.md").read_text(encoding="utf-8").replace("\r\n", "\n") == docs_index.render_md(rows)


def test_detecta_dependencia_hacia_capa_superior_y_ciclos(tmp_path):
    reg = json.loads((ROOT / "config" / "modules.json").read_text(encoding="utf-8"))
    for m in reg["modules"]:
        if m["id"] == "config-core":
            m["depends_on"] = ["viewer"]            # capa 1 -> capa 7
    errs = check_modules.validate(reg, ROOT)
    assert any("capa superior" in e for e in errs)
    assert any("ciclo" in e for e in errs)


def test_detecta_archivo_sin_dueno(tmp_path):
    (tmp_path / "edgelab").mkdir()
    (tmp_path / "edgelab" / "huerfano.py").write_text("x = 1\n", encoding="utf-8")
    reg = {"layers": {"1": "x"}, "status_values": ["core"], "modules": [], "unowned_ok": []}
    assert any("sin modulo" in e for e in check_modules.validate(reg, tmp_path))


def test_indice_exige_estado_en_documentos_nuevos(tmp_path):
    d = tmp_path / "docs" / "research"
    d.mkdir(parents=True)
    (d / "NUEVO_20261020.md").write_text("# Nuevo\n\ncuerpo\n", encoding="utf-8")
    (d / "VIEJO_20260101.md").write_text("# Viejo\n\ncuerpo\n", encoding="utf-8")
    (d / "OK_20261020.md").write_text("# Ok\n\nEstado: VIGENTE\nFecha: 2026-10-20\n", encoding="utf-8")
    (d / "CAMP_MANIFIESTO_20261020.md").write_text("# Manifiesto inmutable\n", encoding="utf-8")
    v = docs_index.violations(docs_index.collect(tmp_path))
    assert len(v) == 1 and "NUEVO_20261020.md" in v[0]
