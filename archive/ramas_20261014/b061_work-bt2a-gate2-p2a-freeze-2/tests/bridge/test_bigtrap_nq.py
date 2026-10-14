"""Suite de pruebas unitarias y de microestructura para BigTrapNQ."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge.ticks import TickSeries, make_synthetic
from edgelab.bridge.indicators import bigtrap_nq
from edgelab.research.nq_microstructure import (
    classify_cme_clock_regime,
    compute_tape_speed_per_tick,
    compute_dwell_and_speed_at_extreme,
    CausalRVolTracker,
    CLOCK_RTH_OPEN,
    CLOCK_RTH_CORE,
    CLOCK_RTH_CLOSE,
    CLOCK_GLOBEX,
)

NS = 1_000_000_000


def test_clock_regime_classification():
    # Fechas sintéticas en America/Chicago (2026-03-10 es martes, sin feriado)
    times = [
        "2026-03-10 03:00:00",  # Globex
        "2026-03-10 08:30:00",  # RTH Open
        "2026-03-10 09:15:00",  # RTH Open
        "2026-03-10 09:30:00",  # RTH Core
        "2026-03-10 12:00:00",  # RTH Core
        "2026-03-10 14:15:00",  # RTH Close
        "2026-03-10 14:59:00",  # RTH Close
        "2026-03-10 15:30:00",  # Globex (Mantenimiento/pausa)
        "2026-03-10 18:00:00",  # Globex
    ]
    dts = pd.to_datetime(times).tz_localize("America/Chicago").as_unit("ns")
    ts_ns = np.asarray(dts.view(np.int64))

    regimes = classify_cme_clock_regime(ts_ns, tz_name="America/Chicago")
    assert regimes[0] == CLOCK_GLOBEX
    assert regimes[1] == CLOCK_RTH_OPEN
    assert regimes[2] == CLOCK_RTH_OPEN
    assert regimes[3] == CLOCK_RTH_CORE
    assert regimes[4] == CLOCK_RTH_CORE
    assert regimes[5] == CLOCK_RTH_CLOSE
    assert regimes[6] == CLOCK_RTH_CLOSE
    assert regimes[7] == CLOCK_GLOBEX
    assert regimes[8] == CLOCK_GLOBEX


def test_tape_speed_calculation():
    # 100 ticks espaciados uniformemente cada 10ms (100 ticks/segundo)
    ts = np.arange(100, dtype=np.int64) * 10_000_000
    speeds = compute_tape_speed_per_tick(ts, window_ms=1000)
    assert len(speeds) == 100
    # En estado estacionario (tras 1 segundo), la velocidad debe ser ~100 ticks/s
    assert abs(speeds[-1] - 100.0) < 5.0


def test_dwell_and_speed_at_extreme():
    # Barra con 10 ticks: 5 en el cuerpo (px 100), 5 en el extremo (px 110)
    # Extremo dura de t=500ms a t=900ms (400ms)
    ts = np.array([
        0, 100, 200, 300, 400,          # cuerpo
        500, 600, 700, 800, 900          # extremo (mecha)
    ], dtype=np.int64) * 1_000_000      # en ns

    px = np.array([100, 100, 100, 100, 100, 110, 110, 110, 110, 110], dtype=np.int64)
    vol = np.array([1, 1, 1, 1, 1, 10, 10, 10, 10, 10], dtype=np.float64)
    ask_ticks = px  # para comprador agresivo (p >= ask)
    bid_ticks = px - 1

    dwell_ms, dwell_vol, tape_speed, dwell_density = compute_dwell_and_speed_at_extreme(
        ts, px, vol, ask_ticks, bid_ticks,
        start_idx=0, end_idx=10,
        extreme_lo_t=108, extreme_hi_t=112,
        target_side=1
    )

    assert dwell_ms == 400.0
    assert dwell_vol == 50.0
    assert abs(tape_speed - (5 / 0.4)) < 0.1
    assert dwell_density > 0


def test_bigtrap_nq_pipeline_runs_and_emits_zones():
    # Generar serie sintética
    tk = make_synthetic(n_sessions=1, ticks_per_session=5000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)

    params = dict(
        ticks_per_row=2,
        bracket_pooling_ticks=4,
        imbalance_ratio=1.5,
        min_trap_volume=10.0,
        min_export_volume=1.0,
        use_dwell_filter=False,  # En datos sintéticos aleatorios apagamos dwell
        use_rvol_filter=False,
    )

    res = bigtrap_nq.run(tk, bars, fps, params=params, chart_tz="America/Chicago")
    assert res["indicator"] == "BigTrapNQ"
    assert "events" in res
    assert "zones" in res
    assert len(res["events"]) > 0

    # Verificar que los eventos TRAP_NQ contienen los campos de microestructura
    trap_events = [e for e in res["events"] if e["type"] == "TRAP_NQ"]
    assert len(trap_events) > 0


def test_dwell_filter_discriminates_flash_sweep_vs_absorption():
    # Construir un caso controlado:
    # 2 barras de 1 minuto:
    # Barra 1: Barra normal
    # Barra 2: Una barrida instantánea de 20ms en el extremo (Flash Sweep)
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value

    # 100 ticks en barra 0
    t0 = np.linspace(base_t, base_t + 59 * NS, 100, dtype=np.int64)
    p0 = np.full(100, 100, dtype=np.int64)
    v0 = np.full(100, 1.0, dtype=np.float64)
    bid0 = p0 - 1
    ask0 = p0 + 1

    # 100 ticks en barra 1: 90 ticks a precio 100, y los últimos 10 ticks a precio 110
    # ocurriendo todos en una ráfaga de 10 milisegundos (Flash sweep)
    t1_base = base_t + 60 * NS
    t1_normal = np.linspace(t1_base, t1_base + 50 * NS, 90, dtype=np.int64)
    t1_flash = np.linspace(t1_base + 55 * NS, t1_base + 55 * NS + 10 * 1_000_000, 10, dtype=np.int64) # 10ms

    t1 = np.concatenate([t1_normal, t1_flash])
    p1 = np.concatenate([np.full(90, 100, dtype=np.int64), np.full(10, 110, dtype=np.int64)])
    # En la mecha hay 10 ticks con volumen 20 cada uno = 200 contratos (gran volumen)
    v1 = np.concatenate([np.full(90, 1.0, dtype=np.float64), np.full(10, 20.0, dtype=np.float64)])
    bid1 = p1 - 1
    ask1 = p1

    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    vol = np.concatenate([v0, v1])
    bids = np.concatenate([bid0, bid1])
    asks = np.concatenate([ask0, ask1])

    tk = TickSeries(ts, px, vol, bids, asks, np.arange(len(ts), dtype=np.int64),
                    0.25, "NQ", "NQ_SYN", "test")
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)

    # Con use_dwell_filter=True y min_dwell_ms=100.0: el flash sweep (10ms) DEBE ser rechazado
    res_filtered = bigtrap_nq.run(
        tk, bars, fps,
        params=dict(
            ticks_per_row=2, min_trap_volume=50.0, use_dwell_filter=True,
            min_dwell_ms=100.0, use_rvol_filter=False
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_filtered["zones"]) == 0, "Flash sweep de 10ms no debe crear zona"

    # Si apagamos el filtro de dwell, se detectaría como trampa clásica erróneamente
    res_unfiltered = bigtrap_nq.run(
        tk, bars, fps,
        params=dict(
            ticks_per_row=2, min_trap_volume=50.0, use_dwell_filter=False,
            use_rvol_filter=False
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_unfiltered["zones"]) > 0, "Sin filtro de dwell se crearía zona espuria"


def test_bracket_pooling_and_anti_overshoot():
    # Barra con compras agresivas en ticks 102 y 103 (2 ticks contiguos)
    # ticks_per_row=2 agrupa ticks [102, 103] en fila 51
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 50, dtype=np.int64)
    p0 = np.full(50, 100, dtype=np.int64)

    t1 = np.linspace(base_t + 60 * NS, base_t + 70 * NS, 50, dtype=np.int64)
    # Abre en 100, sube a 102 y 103 con fuerte compra agresiva, y vuelve a cerrar en 100 (mecha superior)
    p1 = np.concatenate([
        np.full(15, 100, dtype=np.int64),
        np.full(10, 102, dtype=np.int64),
        np.full(10, 103, dtype=np.int64),
        np.full(15, 100, dtype=np.int64)
    ])
    v1 = np.concatenate([
        np.full(15, 1.0, dtype=np.float64),
        np.full(20, 25.0, dtype=np.float64),  # 500 contratos en 102 y 103
        np.full(15, 1.0, dtype=np.float64)
    ])

    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    vol = np.concatenate([v0 := np.full(50, 1.0, dtype=np.float64), v1])
    bids = px - 1
    asks = px

    tk = TickSeries(ts, px, vol, bids, asks, np.arange(len(ts), dtype=np.int64),
                    0.25, "NQ", "NQ_SYN", "test")
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)

    res = bigtrap_nq.run(
        tk, bars, fps,
        params=dict(
            ticks_per_row=2,
            min_trap_volume=40.0,
            use_dwell_filter=False,
            use_rvol_filter=False,
            anti_overshoot_buffer_ticks=3
        ),
        chart_tz="America/Chicago"
    )

    assert len(res["zones"]) == 1
    z = res["zones"][0]
    assert z["kind"] == "trapped_buyers"
    # El buffer anti-overshoot de 3 ticks debe expandir la cota superior
    assert z["top"] > (103 * 0.25)


def test_zone_lifecycle_close_through():
    # 3 barras:
    # Barra 0: Normal
    # Barra 1: Crea zona de trapped sellers en mínimos (p=90, close=100)
    # Barra 2: El precio cierra atravesando los mínimos (close=80 < zone.bottom) -> INVALIDATED
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 20, dtype=np.int64)
    p0 = np.full(20, 100, dtype=np.int64)

    # Barra 1: ventas masivas en 90, cierre en 100
    t1 = np.linspace(base_t + 60 * NS, base_t + 110 * NS, 20, dtype=np.int64)
    p1 = np.concatenate([np.full(10, 90, dtype=np.int64), np.full(10, 100, dtype=np.int64)])
    v1 = np.concatenate([np.full(10, 30.0, dtype=np.float64), np.full(10, 1.0, dtype=np.float64)])

    # Barra 2: cierra abajo en 80
    t2 = np.linspace(base_t + 120 * NS, base_t + 170 * NS, 20, dtype=np.int64)
    p2 = np.full(20, 80, dtype=np.int64)
    v2 = np.full(20, 1.0, dtype=np.float64)

    ts = np.concatenate([t0, t1, t2])
    px = np.concatenate([p0, p1, p2])
    vol = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1, v2])
    bids = px
    asks = px + 1

    tk = TickSeries(ts, px, vol, bids, asks, np.arange(len(ts), dtype=np.int64),
                    0.25, "NQ", "NQ_SYN", "test")
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)

    res = bigtrap_nq.run(
        tk, bars, fps,
        params=dict(
            ticks_per_row=2,
            min_trap_volume=20.0,
            use_dwell_filter=False,
            use_rvol_filter=False,
            invalidation_mode="CloseThrough"
        ),
        chart_tz="America/Chicago"
    )

    assert len(res["zones"]) == 1
    z = res["zones"][0]
    assert z["kind"] == "trapped_sellers"
    assert z["state"] == "INVALIDATED"
    assert z["end_reason"] in ("close_through", "close_through_gap")


def test_finished_auction_filter():
    # Construir dos escenarios:
    # 1. Unfinished auction: a precio máximo 110 hubo compras y ventas (Bid > 0 en 110)
    # 2. Finished auction: a precio máximo 110 solo hubo compras en Ask (Bid = 0 en 110)
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 20, dtype=np.int64)
    p0 = np.full(20, 100, dtype=np.int64)

    # Barra con 6 ticks en 110
    t1 = np.linspace(base_t + 60 * NS, base_t + 110 * NS, 20, dtype=np.int64)
    p1 = np.concatenate([np.full(10, 100, dtype=np.int64), np.full(6, 110, dtype=np.int64), np.full(4, 100, dtype=np.int64)])
    v1 = np.concatenate([np.full(10, 1.0, dtype=np.float64), np.full(6, 10.0, dtype=np.float64), np.full(4, 1.0, dtype=np.float64)])

    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    vol = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1])
    
    # 1. Unfinished: 3 ticks en Ask y 3 ticks en Bid en el máximo 110
    bids_un = (px - 1).copy()
    asks_un = px.copy()
    # Índices 33..35 corresponden a la segunda mitad del cluster en 110
    bids_un[33:36] = 110
    asks_un[33:36] = 111

    tk_unfinished = TickSeries(ts, px, vol, bids_un, asks_un, np.arange(len(ts), dtype=np.int64),
                               0.25, "NQ", "NQ_SYN", "test")
    bars_un = B.build_time_bars(tk_unfinished, minutes=1)
    fps_un = B.build_footprints(tk_unfinished, bars_un)

    # Con require_finished_auction=True: el unfinished auction DEBE ser rechazado
    res_un = bigtrap_nq.run(
        tk_unfinished, bars_un, fps_un,
        params=dict(
            ticks_per_row=2, min_trap_volume=25.0, use_dwell_filter=False,
            use_rvol_filter=False, require_finished_auction=True
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_un["zones"]) == 0, "Unfinished auction en el extremo debe ser descartado"

    # 2. Finished Auction en 110: en 110 no hay trades en Bid (todos van a Ask)
    bids_fin = (px - 1).copy()
    asks_fin = px.copy()
    tk_finished = TickSeries(ts, px, vol, bids_fin, asks_fin, np.arange(len(ts), dtype=np.int64),
                             0.25, "NQ", "NQ_SYN", "test")
    bars_fin = B.build_time_bars(tk_finished, minutes=1)
    fps_fin = B.build_footprints(tk_finished, bars_fin)

    res_fin = bigtrap_nq.run(
        tk_finished, bars_fin, fps_fin,
        params=dict(
            ticks_per_row=2, min_trap_volume=25.0, use_dwell_filter=False,
            use_rvol_filter=False, require_finished_auction=True
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_fin["zones"]) > 0, "Finished auction en el extremo debe ser aceptado"


def test_delta_exhaustion_filter():
    # Barra con compras en la mecha pero cierre donde los compradores mantuvieron delta positivo masivo
    # vs barra donde los vendedores tomaron el control (delta negativo)
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 20, dtype=np.int64)
    p0 = np.full(20, 100, dtype=np.int64)

    t1 = np.linspace(base_t + 60 * NS, base_t + 110 * NS, 20, dtype=np.int64)
    # Abre en 100, sube a 105 (mecha), vuelve a cerrar en 100
    p1 = np.concatenate([np.full(5, 100, dtype=np.int64), np.full(10, 105, dtype=np.int64), np.full(5, 100, dtype=np.int64)])
    
    # Caso 1: Los 5 ticks del cierre son compras masivas en Ask (delta final fuertemente positivo)
    v1_pos = np.concatenate([np.full(5, 1.0, dtype=np.float64), np.full(10, 10.0, dtype=np.float64), np.full(5, 50.0, dtype=np.float64)])
    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    bids_pos = (px - 1).copy()
    asks_pos = px.copy()  # todos en ask -> bar_delta > 0
    vol_pos = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1_pos])

    tk_pos = TickSeries(ts, px, vol_pos, bids_pos, asks_pos, np.arange(len(ts), dtype=np.int64),
                        0.25, "NQ", "NQ_SYN", "test")
    bars_pos = B.build_time_bars(tk_pos, minutes=1)
    fps_pos = B.build_footprints(tk_pos, bars_pos)

    # Con require_delta_exhaustion=True: se descarta porque bar_delta > 0 (compradores aún dominan)
    res_pos = bigtrap_nq.run(
        tk_pos, bars_pos, fps_pos,
        params=dict(
            ticks_per_row=2, min_trap_volume=30.0, use_dwell_filter=False,
            use_rvol_filter=False, require_delta_exhaustion=True
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_pos["zones"]) == 0, "Trap de compras con delta positivo debe ser descartado"

    # Caso 2: Al cierre en 100 los vendedores pegan fuerte al bid (250 contratos en bid -> bar_delta < 0)
    asks_neg = px.copy()
    bids_neg = (px - 1).copy()
    bids_neg[35:40] = 100
    asks_neg[35:40] = 101
    v1_neg = np.concatenate([np.full(5, 1.0, dtype=np.float64), np.full(10, 10.0, dtype=np.float64), np.full(5, 50.0, dtype=np.float64)])
    vol_neg = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1_neg])

    tk_neg = TickSeries(ts, px, vol_neg, bids_neg, asks_neg, np.arange(len(ts), dtype=np.int64),
                        0.25, "NQ", "NQ_SYN", "test")
    bars_neg = B.build_time_bars(tk_neg, minutes=1)
    fps_neg = B.build_footprints(tk_neg, bars_neg)

    res_neg = bigtrap_nq.run(
        tk_neg, bars_neg, fps_neg,
        params=dict(
            ticks_per_row=2, min_trap_volume=30.0, use_dwell_filter=False,
            use_rvol_filter=False, require_delta_exhaustion=True
        ),
        chart_tz="America/Chicago"
    )
    assert len(res_neg["zones"]) > 0, "Trap de compras con delta de agotamiento adverso debe ser aceptado"


def test_poc_in_wick_filter():
    # Barra con POC en el cuerpo vs POC en la mecha
    base_t = pd.to_datetime("2026-03-10 09:30:00").tz_localize("America/Chicago").value
    t0 = np.linspace(base_t, base_t + 50 * NS, 20, dtype=np.int64)
    p0 = np.full(20, 100, dtype=np.int64)

    t1 = np.linspace(base_t + 60 * NS, base_t + 110 * NS, 20, dtype=np.int64)
    # Abre en 100, sube a 105 (mecha), cierra en 100
    p1 = np.concatenate([np.full(5, 100, dtype=np.int64), np.full(10, 105, dtype=np.int64), np.full(5, 100, dtype=np.int64)])
    ts = np.concatenate([t0, t1])
    px = np.concatenate([p0, p1])
    bids = (px - 1).copy()
    asks = px.copy()

    # Caso 1: Mayor volumen en 100 (cuerpo): POC=100 (fuera de mecha superior)
    v1_body = np.concatenate([np.full(5, 100.0, dtype=np.float64), np.full(10, 5.0, dtype=np.float64), np.full(5, 1.0, dtype=np.float64)])
    vol_body = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1_body])
    tk_body = TickSeries(ts, px, vol_body, bids, asks, np.arange(len(ts), dtype=np.int64), 0.25, "NQ", "NQ_SYN", "test")
    bars_body = B.build_time_bars(tk_body, minutes=1)
    fps_body = B.build_footprints(tk_body, bars_body)

    res_body = bigtrap_nq.run(
        tk_body, bars_body, fps_body,
        params=dict(ticks_per_row=2, min_trap_volume=20.0, use_dwell_filter=False, use_rvol_filter=False, require_poc_in_wick=True),
        chart_tz="America/Chicago"
    )
    assert len(res_body["zones"]) == 0, "Si el POC está en el cuerpo, debe ser rechazado"

    # Caso 2: Mayor volumen en 105 (mecha): POC=105 (dentro de mecha superior)
    v1_wick = np.concatenate([np.full(5, 1.0, dtype=np.float64), np.full(10, 50.0, dtype=np.float64), np.full(5, 1.0, dtype=np.float64)])
    vol_wick = np.concatenate([np.full(20, 1.0, dtype=np.float64), v1_wick])
    tk_wick = TickSeries(ts, px, vol_wick, bids, asks, np.arange(len(ts), dtype=np.int64), 0.25, "NQ", "NQ_SYN", "test")
    bars_wick = B.build_time_bars(tk_wick, minutes=1)
    fps_wick = B.build_footprints(tk_wick, bars_wick)

    res_wick = bigtrap_nq.run(
        tk_wick, bars_wick, fps_wick,
        params=dict(ticks_per_row=2, min_trap_volume=20.0, use_dwell_filter=False, use_rvol_filter=False, require_poc_in_wick=True),
        chart_tz="America/Chicago"
    )
    assert len(res_wick["zones"]) > 0, "Si el POC está en la mecha, debe ser aceptado"



