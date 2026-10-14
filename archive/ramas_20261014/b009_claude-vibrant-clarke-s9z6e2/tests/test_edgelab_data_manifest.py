import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"docs/data_catalog"))
import edgelab_data as ed

def test_manifest_ok_and_mismatch(tmp_path):
    (tmp_path/"ds").mkdir();(tmp_path/"ds"/"a.bin").write_bytes(b"x"*10);ed.ROOTS=[tmp_path]
    ok={"files":[{"dataset":"ds","file":"a.bin","bytes":10}],"versions":{"ds":3}};assert ed.verify_launch_manifest(ok)==[]
    with pytest.raises(RuntimeError,match="10 bytes montados, 11 al lanzar"):ed.verify_launch_manifest({"files":[{"dataset":"ds","file":"a.bin","bytes":11}]})
    with pytest.raises(RuntimeError,match="no montado"):ed.verify_launch_manifest({"files":[{"dataset":"ds","file":"falta.bin","bytes":1}]})

def test_no_manifest_is_noop(monkeypatch):
    monkeypatch.delenv("EDGELAB_LAUNCH_MANIFEST",raising=False);assert ed.verify_launch_manifest()==[]

def test_path_never_picks_between_same_named_files(tmp_path):
    for sub in ("p","q"):(tmp_path/"ds"/sub).mkdir(parents=True);(tmp_path/"ds"/sub/"f.parquet").write_bytes(b"1")
    ed.ROOTS=[tmp_path]
    with pytest.raises(FileNotFoundError,match="ambiguo"):ed._path("ds","f.parquet")
    assert ed._path("ds","p/f.parquet").parent.name=="p"                                   # ruta exacta: sin ambigüedad
