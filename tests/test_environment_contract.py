"""Synthetic environment checks. No market-data reads or research execution."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def load_config(monkeypatch, root):
    for name in list(os.environ):
        if name.startswith("EDGELAB_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("EDGELAB_ROOT", str(root))
    spec = importlib.util.spec_from_file_location("isolated_config", ROOT / "edgelab/config.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

def test_import_config_never_creates_workspace(tmp_path, monkeypatch):
    root = tmp_path / "not_created"
    m = load_config(monkeypatch, root)
    assert m.ROOT == root
    assert not root.exists()
    assert m.ES_TICKS is None

def test_explicit_workspace_setup(tmp_path, monkeypatch):
    m = load_config(monkeypatch, tmp_path / "workspace")
    m.prepare_workspace()
    assert m.DATA_DIR.is_dir() and m.RUNS_DIR.is_dir()

def test_explicit_source_override(tmp_path, monkeypatch):
    m = load_config(monkeypatch, tmp_path)
    monkeypatch.setenv("EDGELAB_ES_TICKS", str(tmp_path / "source.parquet"))
    spec = importlib.util.spec_from_file_location("overridden_config", ROOT / "edgelab/config.py")
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
    assert m.ES_TICKS == tmp_path / "source.parquet"
    assert not m.ES_TICKS.exists()

def test_empty_root_fails_closed(tmp_path, monkeypatch):
    load_config(monkeypatch, tmp_path)
    monkeypatch.setenv("EDGELAB_ROOT", " ")
    import pytest
    with pytest.raises(ValueError, match="must not be empty"):
        spec = importlib.util.spec_from_file_location("bad_config", ROOT / "edgelab/config.py")
        m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)

def test_runtime_metadata_scope():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["requires-python"] == ">=3.12,<3.13"
    assert "validation*" in data["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "*.json" in data["tool"]["setuptools"]["package-data"]["edgelab.bridge.indicators"]
    assert data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]

def test_config_defaults_use_cwd_without_writes(monkeypatch):
    env = {k:v for k,v in os.environ.items() if not k.startswith("EDGELAB_")}
    with tempfile.TemporaryDirectory() as d:
        code = f"import importlib.util, sys; from pathlib import Path; s=importlib.util.spec_from_file_location('cfg', {str(ROOT / 'edgelab/config.py')!r}); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m); assert m.ROOT==Path.cwd(); assert not list(Path.cwd().iterdir())"
        subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, check=True)
