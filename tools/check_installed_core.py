"""Core-only installed-wheel smoke; no Arrow, CUDA, network or market data."""
import importlib
import importlib.util
import json

MODULES = (
    "edgelab.data.research_data_gate", "edgelab.data.research_session", "edgelab.kaggle.aggregate_audit", "edgelab.kaggle.research_access", "edgelab.kaggle.coverage_inventory", "edgelab.kaggle.raw_tick_audit", "edgelab.engine", "edgelab.config", "edgelab.data.nt8_contract",
    "edgelab.data.nt8_reader", "edgelab.data.nt8_timezone",
    "edgelab.data.event_identity", "edgelab.edge_brain.hippocampus_store",
    "edgelab.edge_brain.retrieval", "edgelab.edge_brain.typed_registry",
    "edgelab.edge_brain.schema_validator", "edgelab.edge_brain.triangulation",
    "edgelab.edge_brain.result_lineage",
    "edgelab.kaggle.avzvol_audit",
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
    from edgelab.edge_brain.result_lineage import review_result_evidence
    result = review_result_evidence({})
    assert result["status"] == "REQUIRES_REVIEW" and not result["research_authorized"]
    from edgelab.kaggle.avzvol_audit import assign_frozen_bins
    assert assign_frozen_bins([1., 1.], [1.]) == [0, 0]
    print(json.dumps({"status": "PASS_CORE_ONLY_IMPORTS", "modules": len(MODULES), "research_authorized": False, "optional_dependencies_present": False}))

if __name__ == "__main__":
    main()
