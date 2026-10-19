from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from edgelab.data.nt8_contract import GC, INSTRUMENT_SPECS
from edgelab.bridge.ticks import instrument_spec


def test_gc_contract_geometry():
    assert GC.symbol == "GC"
    assert GC.tick_size == 0.1
    assert GC.multiplier == 100.0
    assert GC.tick_value == 10.0
    assert GC.tick_size * GC.multiplier == GC.tick_value


def test_gc_is_available_through_bridge_catalog():
    assert INSTRUMENT_SPECS["GC"] is GC
    assert instrument_spec("GC") == GC


if __name__ == "__main__":
    test_gc_contract_geometry(); print("PASS test_gc_contract_geometry")
    test_gc_is_available_through_bridge_catalog(); print("PASS test_gc_is_available_through_bridge_catalog")
