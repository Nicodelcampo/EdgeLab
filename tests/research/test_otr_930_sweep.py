"""Tests unitarios de paridad horaria NY (EDT/EST), causalidad, oráculo niveles vs niveles_lote y preflight para OTR-930-SWEEP."""
from __future__ import annotations

import numpy as np

from edgelab.research import grilla_generica as GG, indicadores as I, otr_930_sweep as OTR, preflight as PF, sintetico


def test_offset_ny_dst_exacto():
    """Verifica el cambio exacto entre EST (UTC-5 = -18000s) y EDT (UTC-4 = -14400s) en marzo y noviembre."""
    # 2026-03-08 06:59:59 UTC (antes de las 02:00 EST del segundo domingo de marzo) -> EST (-18000)
    assert OTR._offset_ny_seg_nb(1772953199) == -18000
    # 2026-03-08 07:00:01 UTC (después del cambio a EDT) -> EDT (-14400)
    assert OTR._offset_ny_seg_nb(1772953201) == -14400
    # 2026-11-01 05:59:59 UTC (antes de las 02:00 EDT del primer domingo de noviembre) -> EDT (-14400)
    assert OTR._offset_ny_seg_nb(1793512799) == -14400
    # 2026-11-01 06:00:01 UTC (después del regreso a EST) -> EST (-18000)
    assert OTR._offset_ny_seg_nb(1793512801) == -18000


def test_causal():
    """Verifica que disparos(ctx) de OTR-930-SWEEP sea estrictamente causal (sin look-ahead)."""
    ctx = GG.contexto_m1(sintetico.bloques(dias=35, planta=False, seed=17), tick=0.25)
    dif = I.causal(OTR.disparos, ctx)
    assert dif == [], f"Violación de causalidad en OTR-930-SWEEP: {dif}"


def test_niveles_lote_identico_a_niveles():
    """Verifica que niveles_lote coincida exactamente con el oráculo fila por fila."""
    ctx = GG.contexto_m1(sintetico.bloques(dias=35, planta=True, seed=23), tick=0.25)
    D = OTR.disparos(ctx)
    assert len(D) > 0
    O1 = GG.ops_por_fila(OTR, D, ctx)
    O2 = GG._ops_lote(OTR, D, ctx)
    assert O1.shape == O2.shape
    assert np.array_equal(O1, O2, equal_nan=True)


def test_preflight_estatico():
    """Verifica el contrato estático de OTR-930-SWEEP y el conteo de celdas (1.119.744 por canal)."""
    assert PF.estatico(OTR) == []
    assert GG.n_celdas(OTR) == 1119744
