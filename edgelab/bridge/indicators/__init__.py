"""Registro de kernels traducidos desde NT8.

Contrato común: run(ticks, bars[, footprints], params=None, chart_tz="UTC")
-> dict(indicator, params, header, csv_lines, events, zones, params_line).

- Gaps2, HFTZones2 y BigTrap2Absorption son tick-driven.
- VolTicksPOC2, aVolCellPOI2 y BigTrap2 son bar-driven y consumen footprint.
- BigTrap2Absorption se registra mediante un adaptador de forma que su kernel
  histórico conserve semántica y cumpla el contrato uniforme del Store v2.
"""
from . import (
    aacloseopendiffs,
    avolcellpoi2,
    bigtrap2,
    bigtrap2absorption_adapter,
    gaps2,
    hftzones2,
    voltickspoc2,
)

REGISTRY = {
    "Gaps2": gaps2,
    "VolTicksPOC2": voltickspoc2,
    "BigTrap2": bigtrap2,
    "BigTrap2Absorption": bigtrap2absorption_adapter,
    "HFTZones2": hftzones2,
    "aVolCellPOI2": avolcellpoi2,
    "AACloseOpenDiffs": aacloseopendiffs,
}

M1_DRIVEN = {"AACloseOpenDiffs"}
TICK_DRIVEN = {"Gaps2", "HFTZones2", "BigTrap2Absorption"}
BAR_DRIVEN = {"VolTicksPOC2", "aVolCellPOI2", "BigTrap2"}
