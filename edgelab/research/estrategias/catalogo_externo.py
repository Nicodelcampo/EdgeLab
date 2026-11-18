"""Registro y ejecutor por lotes de las 28 estrategias traducidas del catálogo externo para `analizador.py`."""
from __future__ import annotations

from typing import Any

from edgelab.research import analizador as A
from edgelab.research.estrategias import (
    alphatrend_mfi,
    avellaneda_stoikov_skew,
    bollinger_rsi_double,
    coinrule_ifttt_ride_surge,
    composer_symphony_rotator,
    connors_rsi2_atr_mr,
    donchian_turtle_breakout,
    dual_thrust_chalek,
    dynamic_breakout_ii,
    fisher_aroon_psar_qc,
    freqtrade_binh_cluc_scalp,
    gaussian_supertrend_3r,
    grid_dca_martingale_envelope,
    intraday_first_last_momentum,
    kalman_zscore_statarb,
    london_asian_box_breakout,
    macd_adx_trend,
    optionalpha_expected_move_wall,
    orb_rvol_intradia,
    pmax_explorer,
    qfl_base_crack_scanner,
    smc_fvg_ob_retest,
    squeeze_bollinger_keltner,
    ssl_hybrid_nnfx,
    supertrend_atr,
    ut_bot_chandelier,
    vwap_stdev_rebound,
    wavetrend_lazybear,
)

ESTRATEGIAS_EXTERNAS: list[Any] = [
    supertrend_atr,
    gaussian_supertrend_3r,
    pmax_explorer,
    alphatrend_mfi,
    ut_bot_chandelier,
    ssl_hybrid_nnfx,
    donchian_turtle_breakout,
    macd_adx_trend,
    orb_rvol_intradia,
    dual_thrust_chalek,
    dynamic_breakout_ii,
    squeeze_bollinger_keltner,
    london_asian_box_breakout,
    intraday_first_last_momentum,
    connors_rsi2_atr_mr,
    bollinger_rsi_double,
    wavetrend_lazybear,
    vwap_stdev_rebound,
    coinrule_ifttt_ride_surge,
    freqtrade_binh_cluc_scalp,
    qfl_base_crack_scanner,
    smc_fvg_ob_retest,
    kalman_zscore_statarb,
    fisher_aroon_psar_qc,
    composer_symphony_rotator,
    grid_dca_martingale_envelope,
    avellaneda_stoikov_skew,
    optionalpha_expected_move_wall,
]

MAPA_ESTRATEGIAS: dict[str, Any] = {m.NOMBRE: m for m in ESTRATEGIAS_EXTERNAS}


def listar_catalogo() -> list[dict]:
    """Devuelve metadatos de todas las estrategias traducidas del catálogo externo."""
    return [
        dict(
            modulo=m.__name__,
            nombre=m.NOMBRE,
            familia=m.FAMILIA,
            instrumento=m.INSTRUMENTO,
            n_variantes=len(A.variantes(m)),
        )
        for m in ESTRATEGIAS_EXTERNAS
    ]


def correr_todas(
    desde: int = 20250303,
    hasta: int = 20250430,
    *,
    registro=None,
    B=None,
    tick: float = 0.25,
    friccion_pts: float = 1.0,
    resolucion: str = "m1",
    entrada: str = "/kaggle/input",
) -> list[dict]:
    """Corre las 28 estrategias a través de `analizador.analizar` y devuelve la lista de reportes."""
    return [
        A.analizar(
            m,
            desde,
            hasta,
            entrada=entrada,
            registro=registro,
            B=B,
            tick=tick,
            friccion_pts=friccion_pts,
            resolucion=resolucion,
        )
        for m in ESTRATEGIAS_EXTERNAS
    ]
