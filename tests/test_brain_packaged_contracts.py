import pytest
from edgelab.edge_brain.invalidation import DependencyEdge
from edgelab.edge_brain.retrieval import LedgerIndex
from edgelab.edge_brain.schema_validator import get_schema, SCHEMA_DIR
from edgelab.edge_brain.typed_registry import TYPED_RELATIONS

def test_every_packaged_schema_is_loadable():
    files=list(SCHEMA_DIR.glob("*.json"))
    assert len(files)==35
    for path in files:
        assert isinstance(get_schema(path.stem),dict)

def test_schema_path_traversal_rejected():
    with pytest.raises(FileNotFoundError):get_schema("../../config")

def test_dependency_relation_uses_real_typed_registry():
    assert "DEPENDS_ON" in TYPED_RELATIONS
    assert DependencyEdge("EXP-1","CLAIM-1","DEPENDS_ON").relation=="DEPENDS_ON"

def test_retrieval_in_memory_is_deterministic():
    rows=[("lesson_candidate",{"lesson_id":"L-1","statement":"synthetic custody clock inversion"}), ("lesson_candidate",{"lesson_id":"L-2","statement":"synthetic execution spread"})]
    index=LedgerIndex(rows)
    first=index.query("custody clock")
    assert first==index.query("custody clock")
    assert first[0].record_id=="L-1"
