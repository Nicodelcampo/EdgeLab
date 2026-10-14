from pathlib import Path
import pytest
from edgelab.config import resolve_settings


def resolve(tmp_path, env=None, content=None):
    local = tmp_path / "local.toml"
    if content is not None:
        local.write_text(content)
    return resolve_settings(env=env or {}, local_toml=local, default_toml=tmp_path/"absent.toml")

@pytest.mark.parametrize("canonical,alias,key", [
    ("EDGELAB_DATA_ROOT","EDGELAB_DATA_DIR","data_dir"),
    ("EDGELAB_RUNS_ROOT","EDGELAB_RUNS_DIR","runs_dir"),
    ("EDGELAB_NQ_RAW_ROOT","EDGELAB_NQ_RAW_DIR","nq_raw_dir"),
])
def test_legacy_and_product_aliases(canonical,alias,key,tmp_path):
    path=tmp_path/"target"
    assert getattr(resolve(tmp_path,{canonical:str(path)}),key)==path
    assert getattr(resolve(tmp_path,{alias:str(path)}),key)==path
    with pytest.raises(ValueError,match="Conflicting"):
        resolve(tmp_path,{canonical:str(path),alias:str(path/"other")})

def test_explicit_source_and_external_optional(tmp_path):
    s=resolve(tmp_path,{"EDGELAB_ES_TICKS":str(tmp_path/"es.parquet")})
    assert s.es_ticks == tmp_path/"es.parquet"
    assert s.vectorbt_ecosystem_root is None
    assert s.nq_raw_dir is None

def test_unknown_toml_key_rejected(tmp_path):
    with pytest.raises(ValueError,match="Unknown configuration"):
        resolve(tmp_path,content='[paths]\ndata_dri="typo"\n')

def test_local_config_wins(tmp_path):
    s=resolve(tmp_path,{"EDGELAB_DATA_ROOT":str(tmp_path/"env")}, '[paths]\ndata_dir="local"\n')
    assert s.data_dir==Path("local")
