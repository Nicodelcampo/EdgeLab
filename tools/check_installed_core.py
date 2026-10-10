"""Core-only installed-wheel smoke; no Arrow, CUDA, network or market data."""
import importlib
import importlib.util
import json

MODULES = (
    "edgelab.data.research_data_gate", "edgelab.data.research_session", "edgelab.engine", "edgelab.config", "edgelab.data.nt8_contract",
    "edgelab.data.nt8_reader", "edgelab.data.nt8_timezone",
    "edgelab.data.event_identity", "edgelab.edge_brain.hippocampus_store",
    "edgelab.edge_brain.retrieval", "edgelab.edge_brain.typed_registry",
    "edgelab.edge_brain.schema_validator", "edgelab.edge_brain.triangulation",
)


def main():
    for optional in ("pyarrow", "duckdb", "scipy", "cupy"):
        if importlib.util.find_spec(optional) is not None:
            raise RuntimeError("Core-only smoke requires optional dependencies absent")
    for module in MODULES:
        importlib.import_module(module)
    from edgelab.edge_brain.invalidation import DependencyEdge
    from edgelab.edge_brain.schema_validator import get_schema
    from edgelab.edge_brain.retrieval import LedgerIndex
    DependencyEdge("SYNTHETIC-EXP", "SYNTHETIC-CLAIM", "DEPENDS_ON")
    assert get_schema("dependency_edge")
    assert LedgerIndex([]).query("synthetic missing") == []
    print(json.dumps({"status": "PASS_CORE_ONLY_IMPORTS", "modules": len(MODULES), "research_authorized": False, "optional_dependencies_present": False}))

if __name__ == "__main__":
    main()
