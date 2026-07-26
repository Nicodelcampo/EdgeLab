"""Registro de kernels traducidos desde NT8.

Contrato común: run(ticks, bars[, footprints], params=None, chart_tz="UTC")
-> dict(indicator, params, header, csv_lines, events, zones, params_line).

- Gaps2 y HFTZones2 son tick-driven (no requieren footprints).
- VolTicksPOC2, aVolCellPOI2 y BigTrap2 son bar-driven y consumen el footprint
  reconstruido (bars.build_footprints), equivalente a la subserie 1-tick de NT8.

Los kernels aún no portados se agregan al REGISTRY cuando pasan su smoke
sintético (protocolo F5+); el REGISTRY es la única fuente de verdad de qué
indicadores existen para la CLI.
"""
from . import (aacloseopendiffs, avolcellpoi2, bigtrap2, gaps2, hftzones2,
               voltickspoc2)

REGISTRY = {
    "Gaps2": gaps2,
    "VolTicksPOC2": voltickspoc2,
    "BigTrap2": bigtrap2,
    "HFTZones2": hftzones2,
    "aVolCellPOI2": avolcellpoi2,
    "AACloseOpenDiffs": aacloseopendiffs,
}

# AACloseOpenDiffs es SUBSERIE-DRIVEN: arma sus propias barras M1 y NO usa
# las del chart primario, asi que su salida es independiente del bar_spec.
M1_DRIVEN = {"AACloseOpenDiffs"}
TICK_DRIVEN = {"Gaps2", "HFTZones2"}
BAR_DRIVEN = {"VolTicksPOC2", "aVolCellPOI2", "BigTrap2"}
