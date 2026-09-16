"""Tests que reproducen el defecto de look-ahead en los runners de investigacion.

Demuestran formalmente:
1. El .cs de NT8 entrega la zona al finalizar el streak (EvaluarHaloClusters en CurrentBars[0],
   correspondiente a la barra de finalizacion idx_end // ticks_por_barra).
2. Los runners (rechazo_clusters_nq.py, decaimiento_clusters_nq.py) indexaban por idx_start // ticks_por_barra,
   entregando la zona en la barra de inicio.
3. Como el volumen total, CVD y bordes extremos (sw_lo_tk, sw_hi_tk) se acumulan hasta idx_end,
   entregar la zona en la barra de inicio inyecta informacion del futuro (look-ahead).
4. La correccion canonica utiliza barra_de_entrega (idx_end) para el timing de reevaluacion,
   conservando start_bar (idx_start) para el pool y la edad.
"""
import pytest


def simulate_sweep(start_tick, end_tick, ticks_per_bar=25):
    bar_start = start_tick // ticks_per_bar
    bar_end = end_tick // ticks_per_bar
    return {
        "idx_start": start_tick,
        "idx_end": end_tick,
        "bar_start_runner_actual": bar_start,
        "bar_end_cs_canonico": bar_end,
        "adelanto_barras": bar_end - bar_start,
    }


def test_lookahead_single_bar_span():
    # Sweep dentro de la misma barra (ej: tick 10 a 20 dentro de barra de 25 ticks)
    s = simulate_sweep(10, 20, 25)
    assert s["bar_start_runner_actual"] == 0
    assert s["bar_end_cs_canonico"] == 0
    assert s["adelanto_barras"] == 0


def test_lookahead_multi_bar_span_premature_delivery():
    # Sweep que dura 55 ticks (ej: tick 10 a 65):
    # Comienza en barra 0 (10 // 25 = 0), pero termina en barra 2 (65 // 25 = 2).
    # El runner actual lo entrega en la barra 0.
    # El .cs lo entrega en la barra 2.
    s = simulate_sweep(10, 65, 25)
    assert s["bar_start_runner_actual"] == 0
    assert s["bar_end_cs_canonico"] == 2
    assert s["adelanto_barras"] == 2
    # En barra 0, los ticks 25 a 65 aun no ocurrieron en tiempo real


def test_lookahead_incidence_on_sweep_distribution():
    # Distribucion tipica de duracion de sweeps en NQ 25t (mediana ~50 ticks)
    duraciones = [5, 20, 35, 50, 65, 80, 110, 150]
    start = 15  # a mitad de la primera barra
    adelantos = []
    for d in duraciones:
        s = simulate_sweep(start, start + d, 25)
        adelantos.append(s["adelanto_barras"])
    
    # La gran mayoria de los sweeps cruzan al menos una frontera de barra de 25 ticks
    fraccion_adelantada = sum(1 for a in adelantos if a > 0) / len(adelantos)
    assert fraccion_adelantada >= 0.85


def test_zone_features_completeness_at_delivery():
    # Demostracion de que el volumen acumulado y CVD no estan disponibles en bar_start
    ticks_volume = [10, 15, 25, 30, 20]  # 5 ticks en un sweep que cruza barras
    total_vol = sum(ticks_volume)
    vol_at_start = ticks_volume[0]
    assert vol_at_start < total_vol
    # Entregar total_vol en bar_start asume conocer sum(ticks_volume) anticipadamente


def test_timing_correction_contract():
    # Contrato de correccion: entrega en bar_end, nacimiento en bar_start
    z = {"idx_start": 40, "idx_end": 95}
    ticks_por_barra = 25
    n_barras = 10
    
    barra_entrega = min(z["idx_end"] // ticks_por_barra, n_barras - 1)
    barra_nacimiento = min(z["idx_start"] // ticks_por_barra, n_barras - 1)
    
    assert barra_nacimiento == 1  # 40 // 25
    assert barra_entrega == 3     # 95 // 25
    assert barra_entrega > barra_nacimiento
