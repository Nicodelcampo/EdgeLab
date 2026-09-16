"""Tests sinteticos obligatorios para el comparador de paridad V2.

Cubre las 11 condiciones de compuerta exigidas:
1. Dos zonas con el mismo start_ms y distinta direccion.
2. Dos zonas con start_ms, end_ms y direccion iguales (colision ambigua).
3. Zona Python adicional con start_ms inexistente en NT8.
4. Zona NT8 adicional (NT8_WITHOUT_PYTHON).
5. Intento de reutilizar una pareja (matching 1-a-1).
6. Diferencia de un tick en geometria (MATCHED_FIELD_DIFF).
7. Diferencia de timestamp sub-ms (dentro de ms vs fuera de ms).
8. Duracion 0 ms sin colision.
9. INSERT OR IGNORE simulado.
10. Orden alterado de las listas de entrada.
11. Igualdad completa (PASS).
"""
import pytest
from tools.paridad_hftzones_nq_v2 import comparar_zonas_simetrico, FIELD_SPECS


def _make_oracle_row(start_ms=1000, end_ms=1100, direction=1, px_lo=100.0, px_hi=105.0,
                      valid_steps=10, pasos=12, avg_ms=8.0, total_ms=96.0, vol_rate=120.0,
                      total_vol=120.0, height_ticks=20.0, max_retro=2.0, cvd=50.0,
                      buy_vol=85.0, sell_vol=35.0, slope=0.5, d_first=20.0, d_second=30.0,
                      max_tick_vol=15.0, no_move_ticks=2, no_move_vol=20.0, max_level_ticks=4):
    """Crea una fila con el schema de columnas de hft_zones."""
    return (
        start_ms, end_ms, direction, px_lo, px_hi, valid_steps, pasos, avg_ms,
        total_ms, vol_rate, total_vol, height_ticks, max_retro, cvd, buy_vol,
        sell_vol, slope, d_first, d_second, max_tick_vol, no_move_ticks,
        no_move_vol, max_level_ticks
    )


def _make_python_zone(start_ms=1000, end_ms=1100, direction=1, px_lo=100.0, px_hi=105.0,
                       valid_steps=10, pasos=12, avg_ms=8.0, total_ms=96.0, vol_rate=120.0,
                       total_vol=120.0, height_ticks=20.0, max_retro=2.0, cvd=50.0,
                       buy_vol=85.0, sell_vol=35.0, slope=0.5, d_first=20.0, d_second=30.0,
                       max_tick_vol=15.0, no_move_ticks=2, no_move_vol=20.0, max_level_ticks=4,
                       tick_size=0.25):
    """Crea un diccionario representativo de la zona emitida por el espejo Python."""
    return {
        "ts_start": start_ms * 1_000_000,
        "ts_end": end_ms * 1_000_000,
        "direction": direction,
        "sw_lo_tk": int(round(px_lo / tick_size)),
        "sw_hi_tk": int(round(px_hi / tick_size)),
        "valid_steps": valid_steps,
        "pasos": pasos,
        "avg_ms": avg_ms,
        "total_ms": total_ms,
        "vol_rate": vol_rate,
        "total_vol": total_vol,
        "height_ticks": height_ticks,
        "max_retro_ticks": max_retro,
        "cvd": cvd,
        "buy_vol": buy_vol,
        "sell_vol": sell_vol,
        "delta_slope": slope,
        "delta_first": d_first,
        "delta_second": d_second,
        "max_tick_vol": max_tick_vol,
        "no_move_ticks": no_move_ticks,
        "no_move_vol": no_move_vol,
        "max_level_ticks": max_level_ticks,
    }


def test_1_mismo_start_ms_distinta_direccion():
    """Dos zonas que inician en el mismo start_ms pero con dir opuesta se separan limpiamente."""
    o1 = _make_oracle_row(start_ms=5000, end_ms=5100, direction=1)
    o2 = _make_oracle_row(start_ms=5000, end_ms=5150, direction=-1)

    p1 = _make_python_zone(start_ms=5000, end_ms=5100, direction=1)
    p2 = _make_python_zone(start_ms=5000, end_ms=5150, direction=-1)

    res = comparar_zonas_simetrico([o1, o2], [p1, p2])
    assert res["matched_exact_count"] == 2
    assert res["ambiguous_collisions_count"] == 0
    assert res["is_perfect_pass"] is True


def test_2_colision_ambigua_misma_clave():
    """Dos zonas con start_ms, end_ms y direccion exactamente iguales disparan AMBIGUOUS_COLLISION."""
    o1 = _make_oracle_row(start_ms=5000, end_ms=5100, direction=1, px_lo=100.0)
    o2 = _make_oracle_row(start_ms=5000, end_ms=5100, direction=1, px_lo=102.0)

    p1 = _make_python_zone(start_ms=5000, end_ms=5100, direction=1, px_lo=100.0)
    p2 = _make_python_zone(start_ms=5000, end_ms=5100, direction=1, px_lo=102.0)

    res = comparar_zonas_simetrico([o1, o2], [p1, p2])
    assert res["ambiguous_collisions_count"] == 1
    assert res["is_perfect_pass"] is False


def test_3_zona_python_adicional_inexistente_en_nt8():
    """Zona en Python cuyo start_ms no existe en NT8 debe clasificarse como PYTHON_WITHOUT_NT8."""
    o1 = _make_oracle_row(start_ms=1000)
    p1 = _make_python_zone(start_ms=1000)
    p_extra = _make_python_zone(start_ms=2000)

    res = comparar_zonas_simetrico([o1], [p1, p_extra])
    assert res["matched_exact_count"] == 1
    assert res["python_without_nt8_count"] == 1
    assert res["nt8_without_python_count"] == 0
    assert res["is_perfect_pass"] is False


def test_4_zona_nt8_adicional():
    """Zona en NT8 sin contraparte Python debe clasificarse como NT8_WITHOUT_PYTHON."""
    o1 = _make_oracle_row(start_ms=1000)
    o_extra = _make_oracle_row(start_ms=2000)
    p1 = _make_python_zone(start_ms=1000)

    res = comparar_zonas_simetrico([o1, o_extra], [p1])
    assert res["matched_exact_count"] == 1
    assert res["nt8_without_python_count"] == 1
    assert res["python_without_nt8_count"] == 0
    assert res["is_perfect_pass"] is False


def test_5_no_reutilizacion_de_pareja():
    """Una zona Python no puede emparejarse dos veces con distintas zonas NT8."""
    o1 = _make_oracle_row(start_ms=1000, end_ms=1050, direction=1)
    o2 = _make_oracle_row(start_ms=1000, end_ms=1060, direction=1)
    p1 = _make_python_zone(start_ms=1000, end_ms=1050, direction=1)

    res = comparar_zonas_simetrico([o1, o2], [p1])
    assert res["total_matched_pairs"] == 1
    assert res["nt8_without_python_count"] == 1
    assert res["duplicate_match_reuse_count"] == 0
    assert res["is_perfect_pass"] is False


def test_6_diferencia_de_un_tick():
    """Una diferencia de 1 tick en geometria genera MATCHED_FIELD_DIFF con campos_comparados contados."""
    o1 = _make_oracle_row(start_ms=1000, px_hi=105.0)
    # 105.25 es 1 tick mas alto
    p1 = _make_python_zone(start_ms=1000, px_hi=105.25)

    res = comparar_zonas_simetrico([o1], [p1])
    assert res["matched_exact_count"] == 0
    assert res["matched_field_diff_count"] == 1
    assert "price_upper" in res["diferencias_por_campo"]
    assert res["fields_compared_total"] == 20
    assert res["is_perfect_pass"] is False


def test_7_diferencia_de_timestamp_sub_ms():
    """Si dos zonas ocurren dentro del mismo ms en ns pero redondean al mismo ms, empatan en clave."""
    # Ambas mapean a start_ms = 1000
    p1 = _make_python_zone(start_ms=1000)
    p1["ts_start"] = 1_000_250_000  # 1000.25 ms -> 1000 ms
    o1 = _make_oracle_row(start_ms=1000)

    res = comparar_zonas_simetrico([o1], [p1])
    assert res["matched_exact_count"] == 1
    assert res["is_perfect_pass"] is True


def test_8_duracion_0ms_sin_colision():
    """Una zona con start_ms == end_ms (duracion 0 ms) empareja limpiamente si es 1-a-1."""
    o1 = _make_oracle_row(start_ms=2000, end_ms=2000, avg_ms=0.0, total_ms=0.0)
    p1 = _make_python_zone(start_ms=2000, end_ms=2000, avg_ms=0.0, total_ms=0.0)

    res = comparar_zonas_simetrico([o1], [p1])
    assert res["matched_exact_count"] == 1
    assert res["duracion_0ms_nt8"] == 1
    assert res["duracion_0ms_python"] == 1
    assert res["is_perfect_pass"] is True


def test_9_insert_or_ignore_simulado():
    """Simular cuando NT8 descarto la segunda zona por INSERT OR IGNORE sobre start_ms."""
    # Python tiene dos zonas en start_ms=3000 con distinto end_ms
    p1 = _make_python_zone(start_ms=3000, end_ms=3020, direction=1)
    p2 = _make_python_zone(start_ms=3000, end_ms=3080, direction=1)
    # NT8 solo tiene una porque descarto p2
    o1 = _make_oracle_row(start_ms=3000, end_ms=3020, direction=1)

    res = comparar_zonas_simetrico([o1], [p1, p2])
    assert res["matched_exact_count"] == 1
    assert res["python_without_nt8_count"] == 1
    assert res["is_perfect_pass"] is False


def test_10_orden_alterado():
    """El comparador es invariante al orden en que se presenten las filas."""
    o1 = _make_oracle_row(start_ms=1000)
    o2 = _make_oracle_row(start_ms=2000)
    p1 = _make_python_zone(start_ms=1000)
    p2 = _make_python_zone(start_ms=2000)

    res = comparar_zonas_simetrico([o2, o1], [p1, p2])
    assert res["matched_exact_count"] == 2
    assert res["is_perfect_pass"] is True


def test_11_igualdad_completa():
    """Conjuntos identicos producen PASS_CERTIFIED con is_perfect_pass == True."""
    rows_o = [_make_oracle_row(start_ms=1000 * i, end_ms=1000 * i + 100) for i in range(1, 10)]
    rows_p = [_make_python_zone(start_ms=1000 * i, end_ms=1000 * i + 100) for i in range(1, 10)]

    res = comparar_zonas_simetrico(rows_o, rows_p)
    assert res["matched_exact_count"] == 9
    assert res["matched_field_diff_count"] == 0
    assert res["nt8_without_python_count"] == 0
    assert res["python_without_nt8_count"] == 0
    assert res["fields_compared_total"] == 9 * 20
    assert res["is_perfect_pass"] is True
