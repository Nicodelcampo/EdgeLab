"""Configuración portable: raíz derivada del repo, precedencia
local.toml > EDGELAB_* env > default.toml, externos opcionales, y NO se
crean directorios al importar. Fixtures sintéticos, sin rutas de máquina."""
from pathlib import Path
import pytest


def test_root_is_portable_from_file():
    import edgelab.config as cfg
    assert cfg.ROOT == Path(cfg.__file__).resolve().parents[1]


def test_internal_paths_root_relative(tmp_path):
    from edgelab.config import resolve_settings
    s = resolve_settings(env={}, local_toml=tmp_path / "none.toml", default_toml=tmp_path / "none.toml")
    assert s.data_dir == s.root / "data"
    assert s.manifests_dir == s.root / "manifests"


def test_precedence_local_over_env_over_default(tmp_path):
    from edgelab.config import resolve_settings
    default = tmp_path / "default.toml"
    default.write_text('[paths]\nvectorbt_ecosystem_root = "D:/from_default"\n', encoding="utf-8")
    local = tmp_path / "local.toml"
    local.write_text('[paths]\nvectorbt_ecosystem_root = "D:/from_local"\n', encoding="utf-8")
    env = {"EDGELAB_VECTORBT_ROOT": "D:/from_env"}

    s_local = resolve_settings(env=env, default_toml=default, local_toml=local)
    assert Path(s_local.vectorbt_ecosystem_root).as_posix() == "D:/from_local"

    s_env = resolve_settings(env=env, default_toml=default, local_toml=tmp_path / "missing.toml")
    assert Path(s_env.vectorbt_ecosystem_root).as_posix() == "D:/from_env"

    s_default = resolve_settings(env={}, default_toml=default, local_toml=tmp_path / "missing.toml")
    assert Path(s_default.vectorbt_ecosystem_root).as_posix() == "D:/from_default"


def test_external_optional_none_when_unset(tmp_path):
    from edgelab.config import resolve_settings
    s = resolve_settings(env={}, default_toml=tmp_path / "none.toml", local_toml=tmp_path / "none.toml")
    assert s.nt8_export_root is None
    assert s.vectorbt_ecosystem_root is None
    # internos siempre resuelven (root-relativos)
    assert s.data_dir == s.root / "data"
    assert s.manifests_dir == s.root / "manifests"


def test_import_does_not_create_dirs(tmp_path):
    """Importar config no debe tocar el filesystem.

    El invariante es 'importar no crea directorios', NO 'repo/manifests no existe
    jamas': ese directorio puede existir legitimamente porque hay artefactos
    versionados adentro. Se verifica en un sandbox, reimportando el modulo con
    Path.mkdir saboteado: si el import crea un solo directorio, falla.
    """
    import importlib
    import edgelab.config as cfg

    creados = []
    real_mkdir = Path.mkdir

    def mkdir_espia(self, *a, **kw):
        creados.append(str(self))
        return real_mkdir(self, *a, **kw)

    Path.mkdir = mkdir_espia
    try:
        importlib.reload(cfg)
    finally:
        Path.mkdir = real_mkdir

    assert creados == [], f"importar config creo directorios: {creados}"


def test_resolver_no_materializa_rutas_internas(tmp_path):
    """Resolver rutas es puro: devuelve Paths, no los crea."""
    from edgelab.config import resolve_settings
    s = resolve_settings(env={}, default_toml=tmp_path / "none.toml",
                         local_toml=tmp_path / "none.toml")
    assert s.manifests_dir == s.root / "manifests"
    assert s.data_dir == s.root / "data"
    # sobre una raiz sintetica, resolver no debe materializar nada
    inexistente = tmp_path / "repo_fantasma"
    assert not (inexistente / "manifests").exists()
    assert not (inexistente / "data").exists()
