"""Tests para OPTION-ALPHA (`edgelab/research/option_alpha_a5.py`): contrato, causalidad estricta y pre-registro."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from edgelab.research import indicadores as I, option_alpha_a5 as OA, preflight as PF, sintetico, tablas as TB

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _ctx_sint() -> dict:
    return TB.contexto(OA, list(sintetico.bloques(dias=45, planta=False, seed=11)), 0.25)


def test_contrato_y_causalidad_estricta():
    assert TB.contrato(OA) == []
    ctx = _ctx_sint()
    E = OA.eventos(ctx)
    assert len(E) > 0
    for col in OA.DEFINICIONES:
        assert int(E[col].sum()) > 0, f"{col} no disparó en 45 días sintéticos"
    for ctrl in OA.CONTROL.values():
        assert int(E[ctrl].sum()) > 0, f"control {ctrl} no disparó en 45 días sintéticos"
    assert (E["fin"] >= E["k"]).all()
    assert (E["rg"] > 0).all()
    assert I.causal_por_disparo(OA.eventos, ctx, n=15) == []


def test_macro_lookup_ignora_ids_sinteticos_y_lee_reales():
    assert all(np.isnan(x) for x in OA._macro_sesion(0))
    p_vol = ROOT / "data/m1nt8/cboe_volatility_daily.parquet"
    p_cal = ROOT / "data/m1nt8/us_market_events_calendar_2006_2026.parquet"
    if p_vol.exists() and p_cal.exists():
        OA._contexto_externo.cache_clear()
        vix_o, vix_p, ivr, ec, fomc = OA._macro_sesion(20200316)
        assert np.isfinite(vix_o) and np.isfinite(vix_p) and np.isfinite(ivr)
        assert ec in (0.0, 1.0) and fomc in (0.0, 1.0)


def test_preregistro_y_campana_validos():
    pre = ROOT / "docs/research/option_alpha_20261118/PREREGISTRO.md"
    errs = PF.validar_preregistro(pre, ROOT, exigir_commit=False)
    assert errs == [], errs
    camp = json.loads((ROOT / "docs/research/option_alpha_20261118/CAMPANA.json").read_text(encoding="utf-8"))
    assert camp["modulo"] == "edgelab.research.option_alpha_a5"
    assert set(camp["definiciones"]) == set(OA.DEFINICIONES)
    assert camp["control"] == OA.CONTROL
