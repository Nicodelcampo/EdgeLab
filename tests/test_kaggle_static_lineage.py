import hashlib
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "static_lineage", Path(__file__).resolve().parents[1]/"tools/audit_kaggle_notebook_source.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_static_inspection_never_executes_or_exposes_source(tmp_path):
    marker = tmp_path / "MUST_NOT_EXIST"
    source = f'''import os
os.environ["AVCL_INST"] = "MNQ"
os.environ["AVCL_CONTRACTS"] = "MNQ_06-26"
SPEC = 50
open({str(marker)!r}, "w").write("PRIVATE_SOURCE")
seed = hash(c)
sess = ed.sessions(INST, DESDE, HASTA)
'''
    r = mod.inspect_source({"metadata": {"ref": "synthetic/kernel", "current_version_number": 1},
                            "blob": {"source": source}})
    assert not marker.exists()
    assert r["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert r["declared_constants"]["SPEC"] == 50
    assert r["declared_environment"]["AVCL_INST"] == "MNQ"
    assert "PROCESS_DEPENDENT_BUILTIN_HASH" in r["static_hints"]
    assert "PRIVATE_SOURCE" not in json.dumps(r)
    assert not r["research_authorized"] and not r["output_run_binding_verified"]


def test_comments_are_not_runtime_evidence():
    r = mod.inspect_source({"blob": {"source": '# hash(c)\nSPEC = 25\n'}})
    assert not r["static_hints"]
    assert r["declared_constants"]["SPEC"] == 25


def test_bad_source_fails_without_printing_private_payload(tmp_path, capsys):
    p = tmp_path/"info.json"; p.write_text('{"blob":{"source":"PRIVATE_SECRET @ @ @"}}')
    assert mod.main([str(p)]) == 2
    assert "PRIVATE_SECRET" not in capsys.readouterr().out