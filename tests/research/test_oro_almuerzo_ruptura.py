"""Tests unitarios de paridad horaria Europe/Madrid (CET/CEST), causalidad, oráculo niveles vs niveles_lote y preflight para ORO-ALMUERZO-RUPTURA."""
from __future__ import annotations

import numpy as np

from edgelab.research import grilla_generica as GG, indicadores as I, oro_almuerzo_ruptura as OALM, preflight as PF, sintetico


def test_offset_madrid_dst_exacto():
    """Verifica el cambio exacto entre CET (UTC+1 = +3600s) y CEST (UTC+2 = +7200s) el último domingo de marzo y octubre a las 01:00 UTC."""
    # 2026-03-29 00:59:59 UTC (antes del cambio de verano en España) -> CET (+3600)
    assert OALM._offset_madrid_seg_nb(1774745999) == 3600
    # 2026-03-29 01:00:01 UTC (después del cambio a CEST) -> CEST (+7200)
    assert OALM._offset_madrid_seg_nb(1774746001) == 7200
    # 2026-10-25 00:59:59 UTC (antes del regreso a horario de invierno en España) -> CEST (+7200)
    assert OALM._offset_madrid_seg_nb(1792889999) == 7200
    # 2026-10-25 01:00:01 UTC (después del regreso a CET) -> CET (+3600)
    assert OALM._offset_madrid_seg_nb(1792890001) == 3600


def test_causal():
    """Verifica que disparos(ctx) de ORO-ALMUERZO-RUPTURA sea estrictamente causal (sin look-ahead)."""
    ctx = GG.contexto_m1(sintetico.bloques(dias=35, planta=False, seed=19), tick=0.10)
    dif = I.causal(OALM.disparos, ctx)
    assert dif == [], f"Violación de causalidad en ORO-ALMUERZO-RUPTURA: {dif}"


def test_niveles_lote_identico_a_niveles():
    """Verifica que niveles_lote coincida exactamente con el oráculo fila por fila."""
    ctx = GG.contexto_m1(sintetico.bloques(dias=35, planta=True, seed=29), tick=0.10)
    D = OALM.disparos(ctx)
    assert len(D) > 0
    O1 = GG.ops_por_fila(OALM, D, ctx)
    O2 = GG._ops_lote(OALM, D, ctx)
    assert O1.shape == O2.shape
    assert np.array_equal(O1, O2, equal_nan=True)


def test_preflight_estatico():
    """Verifica el contrato estático de ORO-ALMUERZO-RUPTURA y el conteo de celdas (1.259.712 por canal)."""
    assert PF.estatico(OALM) == []
    assert GG.n_celdas(OALM) == 1259712
