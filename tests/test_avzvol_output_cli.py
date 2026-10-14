import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "avzvol_cli", Path(__file__).resolve().parents[1]/"tools/audit_avzvol_outputs.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_output_cannot_overwrite_original(tmp_path, monkeypatch):
    source = tmp_path/"original.json"; source.write_text('{"original":"immutable"}')
    inv = tmp_path/"inventory.json"; inv.write_text("[]")
    monkeypatch.setattr(mod, "audit_inventory", lambda x: {"status": "REQUIRES_REVIEW"})
    assert mod.main(["--inventory", str(inv), "--out", str(source),
                     "--allow-preholdout-covariate-audit"]) == 2
    assert source.read_text() == '{"original":"immutable"}'


def test_baseline_arguments_cannot_be_partial(tmp_path, monkeypatch):
    inv = tmp_path/"inventory.json"; inv.write_text("[]")
    def forbid(x):
        raise AssertionError("must stop before reading any covariates")
    monkeypatch.setattr(mod, "audit_inventory", forbid)
    assert mod.main(["--inventory", str(inv), "--out", str(tmp_path/"new.json"),
                     "--published-baseline", str(tmp_path/"baseline.json"),
                     "--allow-preholdout-covariate-audit"]) == 2


def test_every_partition_checked_before_any_payload(tmp_path, monkeypatch):
    pq = pytest.importorskip("pyarrow.parquet")
    names = [c+"_avzp2racgrid.parquet" for c in mod.DISCOVERY + mod.CONFIRMATION]
    schema_names = ["contract", "cell", "kind", "session", "occ", "amp", *mod.ACTIVITY]
    from types import SimpleNamespace
    class File:
        def __init__(self, path):
            self.path = path
            self.schema_arrow = SimpleNamespace(names=schema_names)
            self.metadata = SimpleNamespace(num_rows=1, row_group=self.group)
            self.num_row_groups = 1
        def group(self, _):
            maximum = 20261001 if self.path.name == names[-1] else 20250901
            stat = SimpleNamespace(has_min_max=True, null_count=0, max=maximum)
            return SimpleNamespace(column=lambda _: SimpleNamespace(statistics=stat))
        def read(self, **kw):
            raise AssertionError("no payload read before all partition checks")
    monkeypatch.setattr(pq, "ParquetFile", File)
    inv = [{"file": str(tmp_path/n), "sha256": "a"*64} for n in names]
    with pytest.raises(mod.AVZVOLAuditError, match="reserved"):
        mod.audit_inventory(inv)