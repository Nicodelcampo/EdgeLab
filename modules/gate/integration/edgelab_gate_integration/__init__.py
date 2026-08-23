"""EdgeLab ↔ GATE integration package."""
from .column_map import normalize_events
from .pipeline import run_integration_pipeline

__all__ = ["normalize_events", "run_integration_pipeline"]
