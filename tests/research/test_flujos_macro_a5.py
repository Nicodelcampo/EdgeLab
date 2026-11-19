"""Tests para FLUJOS-MACRO (`edgelab/research/flujos_macro_a5.py`): contrato, causalidad estricta, CBOE/cal y pre-registro."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from edgelab.research import flujos_macro_a5 as FM, indicadores as I, preflight as PF, sintetico, tablas as TB

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _ctx_sint() -> dict:
    return TB.contexto(FM, list(sintetico.bloques(dias=80, planta=False, seed=29)), 0.25)


def test_contrato_y_causalidad_estricta_flujos_macro():
    assert TB.contrato(FM) == []
    ctx = _ctx_sint()
    E = FM.eventos(ctx)
    assert len(E) > 0
    for col in FM.DEFINICIONES:
        assert int(E[col].sum()) > 0, f"{col} no disparó en 80 días sintéticos"
    for ctrl in FM.CONTROL.values():
        assert int(E[ctrl].sum()) > 0, f"control {ctrl} no disparó en 80 días sintéticos"
    assert (E["fin"] >= E["k"]).all()
    assert (E["rg"] > 0).all()
    assert I.causal_por_disparo(FM.eventos, ctx, n=15) == []


def test_cboe_y_calendario_causal_reales():
    assert all(np.isnan(x) for x in FM._rasgos_dia(0))
    p_vol = ROOT / "data/m1nt8/cboe_volatility_daily.parquet"
    p_cal = ROOT / "data/m1nt8/us_market_events_calendar_2006_2026.parquet"
    if p_vol.exists() and p_cal.exists():
        FM._cargar_cboe_cal.cache_clear()
        vo, vp, ivr, v9, slope, vxn, gvz, ec, fomc, opex = FM._rasgos_dia(20200316)
        assert all(np.isfinite(x) for x in (vo, vp, ivr, v9, slope, vxn, gvz))
        assert ec in (0.0, 1.0) and fomc in (0.0, 1.0) and opex in (0.0, 1.0)


def test_preregistro_y_campana_flujos_macro_validos():
    pre = ROOT / "docs/research/flujos_macro_20261119/PREREGISTRO.md"
    errs = PF.validar_preregistro(pre, ROOT, exigir_commit=False)
    assert errs == [], errs
    camp = json.loads((ROOT / "docs/research/flujos_macro_20261119/CAMPANA.json").read_text(encoding="utf-8"))
    assert camp["modulo"] == "edgelab.research.flujos_macro_a5"
    assert set(camp["definiciones"]) == set(FM.DEFINICIONES)
    assert camp["control"] == FM.CONTROL


def test_fm6_dispara_con_sesiones_reales_que_cruzan_medianoche():
    """K53 (2026-11-19): FM6/FM6N no disparaban nunca en datos reales (la sesión CME empieza 18:00 del día previo y `mo >= 495` tomaba esa
    vela). El sintético no cruza la medianoche, así que el test usa M1 real si está la copia local."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    if not (ROOT / "data/m1nt8/GC_M1_nonadj_utc.parquet").exists():
        return
    from a5_campana import _ctx
    E = FM.eventos(_ctx("GC", None, 20240102, 20240329))
    assert int(E["FM6"].sum() + E["FM6N"].sum()) > 0
