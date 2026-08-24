"""El tick historico se resuelve por anuncio oficial, y falla cerrado sin cobertura."""
from __future__ import annotations

from decimal import Decimal

import pytest

from edgelab.crypto.tick_history import (TickHistoryUnavailable, load_history, tick_size_on)


def test_btc_en_2024_03_usa_el_tick_posterior_al_cambio_de_2022():
    t, prov = tick_size_on("BTCUSDT", "2024-03-30")
    assert t == Decimal("0.1")
    assert prov["status"] == "OFFICIAL_ANNOUNCEMENT"
    assert "binance.com" in prov["source_url"]


def test_sol_en_2024_03_usa_0_001_no_el_vigente():
    """El caso que motivo el modulo: el vigente 0.01 daria 85% de falsos off-tick."""
    t, _ = tick_size_on("SOLUSDT", "2024-03-30")
    assert t == Decimal("0.001")


def test_sol_despues_del_cambio_usa_0_01():
    t, prov = tick_size_on("SOLUSDT", "2024-10-15")
    assert t == Decimal("0.01")
    assert prov["basis"].startswith("posterior")


def test_el_borde_del_cambio_es_el_dia_efectivo():
    assert tick_size_on("SOLUSDT", "2024-10-13")[0] == Decimal("0.001")
    assert tick_size_on("SOLUSDT", "2024-10-14")[0] == Decimal("0.01")


def test_simbolo_sin_cobertura_falla_cerrado():
    with pytest.raises(TickHistoryUnavailable, match="sin metadata historica"):
        tick_size_on("DOGEUSDT", "2024-03-30")


def test_simbolo_sin_anuncios_falla_cerrado_y_no_cae_al_vigente():
    """ETH no tiene anuncio hallado. NO devolver 0.01 por defecto."""
    with pytest.raises(TickHistoryUnavailable, match="Ausencia de evidencia"):
        tick_size_on("ETHUSDT", "2024-03-30")


def test_el_artefacto_declara_sus_propios_huecos():
    h = load_history()
    assert h["known_gaps"], "el artefacto debe declarar que NO cubre"
    assert any("LOT_SIZE" in g for g in h["known_gaps"])
    assert "NO exhaustiva" in h["warning"]


def test_la_unidad_de_cantidad_esta_declarada_como_incompleta():
    """El hueco de LOT_SIZE historico debe estar escrito, no implicito."""
    h = load_history()
    q = h["quantity_unit_history"]
    assert q["status"].startswith("INCOMPLETO")
    assert any(e["symbol"] == "SOLUSDT" for e in q["evidence"])
    assert "PROVISIONAL_EXCHANGE_STEP_SIZE" in q["policy"]
    assert "BTCUSDT" in q["not_covered"] and "ETHUSDT" in q["not_covered"]


def test_el_inventario_de_fuentes_no_presenta_bookdepth_como_bbo():
    h = load_history()
    s = h["sources_measured_2026_08_24"]
    assert "NO es BBO" in s["binance_um_daily"]["bookDepth"]
    assert "DISCONTINUADO" in s["binance_um_daily"]["bookTicker"]
    assert s["l2_bulk_gratis"] == "NO ENCONTRADO por HTTP plano"
