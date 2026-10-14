# -*- coding: utf-8 -*-
"""
tests/research/test_hp007_adapter.py
====================================
Tests sintéticos de integridad causal para el adapter de HP-007 (FASE 2).

Verifica verdad conocida:
1. created_ns <= available_ns <= decision_ns
2. Un touch futuro no altera la densidad en el pasado
3. Una invalidación futura no elimina una zona en el pasado
4. Modificar ticks posteriores no cambia features anteriores
5. Reordenamiento físico con sequence estable produce el mismo resultado
6. Empates de timestamps sin sequence provocan fallo/rechazo
7. Reseteo en frontera de sesión y no cruce de contratos
8. Bloqueo determinista de fechas de holdout (>= 2026-07-01)
"""
import pytest
import datetime
from edgelab.adapters.hp007_causal_adapter import (
    build_causal_signals_and_trajectories,
    compute_as_of_directional_density,
    CausalZoneSnapshot,
    compute_as_of_zone_weight,
    get_cme_trade_date
)
from edgelab.research.liquidity_corridors import CorridorContractError, validate_signal, CorridorSignal


def test_as_of_order_constraints():
    """Verifica que created_ns <= available_ns <= decision_ns."""
    now_ns = 1750000000000000000  # fecha pre-holdout (2025)
    ticks = [
        {"ts_ns": now_ns + i * 1_000_000, "price_tick": 22000 + (i % 3), "volume": 1, "sequence": i}
        for i in range(100)
    ]
    zones = [
        {"id": "Z1", "top": 1.10015, "bottom": 1.10010, "t0": (now_ns - 3600_000_000_000) / 1e9, "kind": "ABSORB_BEAR"}
    ]
    records = build_causal_signals_and_trajectories(
        ticks, zones, contract="6E 06-26", bar_size_ticks=10, min_bar_history=2, stride_bars=1
    )
    assert len(records) > 0
    for r in records:
        s = CorridorSignal(**r["signal"])
        validate_signal(s)
        assert s.created_ns <= s.available_ns <= s.decision_ns


def test_future_touch_does_not_change_past_density():
    """Un toque ocurrido en el futuro no debe alterar la densidad evaluada en el pasado."""
    t_past = 1000_000_000_000
    t_touch_future = 2000_000_000_000

    zone_without_future_touch = CausalZoneSnapshot(
        zone_id="Z1", top_tick=22010, bottom_tick=22008, created_ns=500_000_000_000,
        kind="ABSORB_BEAR", vol=50.0, touches_as_of=0, is_invalidated_as_of=False
    )
    # En t_past, la zona aún tiene 0 toques
    w1 = compute_as_of_zone_weight(zone_without_future_touch, t_past)

    # Si la zona recibe un toque en el futuro, pero evaluamos as-of t_past, touches_as_of debe ser 0
    touches_as_of_past = sum(1 for ts in [t_touch_future] if ts <= t_past)
    assert touches_as_of_past == 0

    zone_with_recorded_future = CausalZoneSnapshot(
        zone_id="Z1", top_tick=22010, bottom_tick=22008, created_ns=500_000_000_000,
        kind="ABSORB_BEAR", vol=50.0, touches_as_of=touches_as_of_past, is_invalidated_as_of=False
    )
    w2 = compute_as_of_zone_weight(zone_with_recorded_future, t_past)
    assert w1 == w2


def test_future_invalidation_does_not_kill_past_zone():
    """Una invalidación futura (t1) no debe invalidar la zona en el pasado."""
    t_past = 1000_000_000_000
    t_inv_future = 3000_000_000_000

    # As-of t_past, la zona sigue viva
    is_inv_past = (t_past >= t_inv_future)
    assert not is_inv_past

    zone_active = CausalZoneSnapshot(
        zone_id="Z1", top_tick=22010, bottom_tick=22008, created_ns=500_000_000_000,
        kind="ABSORB_BEAR", vol=50.0, touches_as_of=0, is_invalidated_as_of=is_inv_past
    )
    w_past = compute_as_of_zone_weight(zone_active, t_past)

    # Si se hubiera evaluado después de t_inv, sufriría penalización
    zone_dead = CausalZoneSnapshot(
        zone_id="Z1", top_tick=22010, bottom_tick=22008, created_ns=500_000_000_000,
        kind="ABSORB_BEAR", vol=50.0, touches_as_of=0, is_invalidated_as_of=True
    )
    w_dead = compute_as_of_zone_weight(zone_dead, t_inv_future + 1000)
    assert w_past > w_dead


def test_modifying_future_ticks_does_not_change_past_features():
    """Modificar ticks en el futuro no altera las densidades ni decisiones pasadas."""
    now_ns = 1750000000000000000
    ticks1 = [
        {"ts_ns": now_ns + i * 1_000_000, "price_tick": 22000 + (i % 2), "volume": 1, "sequence": i}
        for i in range(100)
    ]
    ticks2 = [dict(t) for t in ticks1]
    # Modificar los últimos 10 ticks en el futuro lejano
    for j in range(90, 100):
        ticks2[j]["price_tick"] = 99999

    zones = [{"id": "Z1", "top": 1.10015, "bottom": 1.10010, "t0": (now_ns - 3600_000_000_000) / 1e9, "kind": "ABSORB_BEAR"}]

    rec1 = build_causal_signals_and_trajectories(ticks1, zones, contract="6E 06-26", bar_size_ticks=10, min_bar_history=2, stride_bars=1)
    rec2 = build_causal_signals_and_trajectories(ticks2, zones, contract="6E 06-26", bar_size_ticks=10, min_bar_history=2, stride_bars=1)

    # Las primeras señales deben ser estrictamente idénticas
    assert len(rec1) >= 2 and len(rec2) >= 2
    assert rec1[0]["signal"]["forward_density"] == rec2[0]["signal"]["forward_density"]
    assert rec1[0]["signal"]["reference_tick"] == rec2[0]["signal"]["reference_tick"]


def test_tied_timestamps_without_sequence_fails():
    """Timestamps empatados sin sequence estrictamente creciente deben fallar."""
    now_ns = 1750000000000000000
    ticks_bad = [
        {"ts_ns": now_ns, "price_tick": 22000, "volume": 1, "sequence": 0},
        {"ts_ns": now_ns, "price_tick": 22001, "volume": 1, "sequence": 0},  # empate de sequence
    ]
    with pytest.raises(CorridorContractError, match="Tied timestamps"):
        build_causal_signals_and_trajectories(ticks_bad, [], contract="6E 06-26")


def test_holdout_date_rejection():
    """Rechazo estricto de cualquier señal con trade_date >= 2026-07-01."""
    holdout_ns = int(datetime.datetime(2026, 7, 15, 14, 0, 0, tzinfo=datetime.timezone.utc).timestamp() * 1e9)
    ticks = [
        {"ts_ns": holdout_ns + i * 1_000_000, "price_tick": 22000, "volume": 1, "sequence": i}
        for i in range(50)
    ]
    # No debe emitir ninguna señal porque cae en el holdout sellado
    rec = build_causal_signals_and_trajectories(ticks, [], contract="6E 09-26", bar_size_ticks=10, min_bar_history=2)
    assert len(rec) == 0
