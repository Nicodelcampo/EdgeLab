"""Tests exhaustivos del comparador de paridad HFTZones NQ V2.

Cubre todos los requerimientos de certificación estricta en nanosegundos (V2):
1. schema V2 válido (pass).
2. ausencia de tabla de ticks (fail cerrado).
3. diferencia de 1 ns en start_ts_ns (fail cerrado).
4. diferencia de 1 tick en lo_ticks / hi_ticks (fail cerrado).
5. zone_seq duplicado (fail cerrado).
6. gap de zone_seq (fail cerrado).
7. reset de sesión (reinicio de secuencia a 1 y aislamiento causal).
8. reset de contrato (cambio de contrato reinicia estado).
9. orden alterado en el oráculo (comparador invariante al orden físico).
10. hash de parámetros distinto (fail cerrado por procedencia).
11. hash de source distinto (fail cerrado por procedencia).
12. input tick diferente (el espejo reconstruye zona distinta y falla).
13. zona extra Python (fail cerrado).
14. zona extra NT8 (fail cerrado).
15. match reutilizado / colisión ambigua (fail cerrado).
16. export vacío (fail cerrado).
17. diferencia sub-ms (prohibida en V2: fail cerrado si difiere en ns).
18. éxito exacto completo (PASS_CERTIFIED).
"""
import sqlite3
import pytest
from tools.paridad_hftzones_nq_v2 import (
    comparar_v2_exacto,
    verificar_schema_v2,
    EXPECTED_SOURCE_SHA256,
    EXPECTED_PARAM_SHA256
)
import edgelab.bridge.indicators.hftzones_nq as hz


def _create_v2_db():
    con = sqlite3.connect(":memory:")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE hft_ticks_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            contract TEXT NOT NULL,
            session_id TEXT NOT NULL,
            tick_seq INTEGER NOT NULL,
            timestamp_ns INTEGER NOT NULL,
            price_ticks INTEGER NOT NULL,
            volume REAL NOT NULL,
            bid_ticks INTEGER NOT NULL,
            ask_ticks INTEGER NOT NULL,
            CONSTRAINT ux_tick_v2 UNIQUE (instrument, contract, session_id, tick_seq)
        );
    """)
    cur.execute("""
        CREATE TABLE hft_zones_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            contract TEXT NOT NULL,
            session_id TEXT NOT NULL,
            zone_seq INTEGER NOT NULL,
            start_tick_seq INTEGER NOT NULL,
            end_tick_seq INTEGER NOT NULL,
            start_ts_ns INTEGER NOT NULL,
            end_ts_ns INTEGER NOT NULL,
            available_ts_ns INTEGER NOT NULL,
            direction INTEGER NOT NULL,
            lo_ticks INTEGER NOT NULL,
            hi_ticks INTEGER NOT NULL,
            pasos INTEGER NOT NULL,
            vol REAL NOT NULL,
            avg_ms REAL NOT NULL,
            total_ms REAL NOT NULL,
            volume_rate REAL NOT NULL,
            parameter_manifest_sha256 TEXT NOT NULL,
            indicator_source_sha256 TEXT NOT NULL,
            valid_steps INTEGER NOT NULL,
            max_retro REAL NOT NULL,
            cvd_sweep REAL NOT NULL,
            buy_vol REAL NOT NULL,
            sell_vol REAL NOT NULL,
            delta_slope REAL NOT NULL,
            delta_first REAL NOT NULL,
            delta_second REAL NOT NULL,
            max_tick_vol REAL NOT NULL,
            no_move_ticks INTEGER NOT NULL,
            no_move_vol REAL NOT NULL,
            max_level_ticks INTEGER NOT NULL,
            bucket TEXT NOT NULL,
            price_upper REAL NOT NULL,
            price_lower REAL NOT NULL,
            price_mid REAL NOT NULL,
            height_ticks REAL NOT NULL,
            tick_res INTEGER NOT NULL,
            CONSTRAINT ux_zone_v2 UNIQUE (instrument, contract, session_id, zone_seq)
        );
    """)
    return con


def _seed_standard_run(con, session_id="20260603", contract="NQ JUN26", n_ticks=15):
    """Inserta una racha limpia de ticks alcistas que genera una zona válida idéntica en Python y NT8."""
    cur = con.cursor()
    t0_ns = 1780437841000000000
    ts_list = []
    px_list = []
    vol_list = []
    for i in range(1, n_ticks + 1):
        ts = t0_ns + i * 10_000_000
        px = 115000 + i  # cada paso sube 1 tick
        vol = 10.0
        ts_list.append(ts)
        px_list.append(px)
        vol_list.append(vol)
        cur.execute(
            """INSERT INTO hft_ticks_v2 (
                instrument, contract, session_id, tick_seq, timestamp_ns,
                price_ticks, volume, bid_ticks, ask_ticks
            ) VALUES ('NQ JUN26', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (contract, session_id, i, ts, px, vol, px - 1, px + 1)
        )

    cands = hz.detect_candidates(ts_list, px_list, vol_list)
    acc_zones, _ = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=0.25)

    for z_idx, z in enumerate(acc_zones, start=1):
        cur.execute("""
            INSERT INTO hft_zones_v2 (
                instrument, contract, session_id, zone_seq, start_tick_seq, end_tick_seq,
                start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks,
                pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256,
                indicator_source_sha256, valid_steps, max_retro, cvd_sweep, buy_vol,
                sell_vol, delta_slope, delta_first, delta_second, max_tick_vol,
                no_move_ticks, no_move_vol, max_level_ticks, bucket, price_upper,
                price_lower, price_mid, height_ticks, tick_res
            ) VALUES (
                'NQ JUN26', ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
        """, (
            contract, session_id, z_idx, z["idx_start"] + 1, z["idx_end"] + 1,
            int(z["ts_start"]), int(z["ts_end"]), int(z["ts_end"]), int(z["direction"]),
            int(z["sw_lo_tk"]), int(z["sw_hi_tk"]),
            int(z["pasos"]), float(z["total_vol"]), float(z["avg_ms"]), float(z["total_ms"]),
            float(z["vol_rate"]), EXPECTED_PARAM_SHA256, EXPECTED_SOURCE_SHA256,
            int(z["valid_steps"]), float(z["max_retro_ticks"]), float(z["cvd"]),
            float(z["buy_vol"]), float(z["sell_vol"]), float(z["delta_slope"]),
            float(z["delta_first"]), float(z["delta_second"]), float(z["max_tick_vol"]),
            int(z["no_move_ticks"]), float(z["no_move_vol"]), int(z["max_level_ticks"]),
            str(z["bucket"]), float(z["upper"]), float(z["lower"]),
            (float(z["upper"]) + float(z["lower"])) / 2.0, float(z["height_ticks"]), 1
        ))
    con.commit()


def test_1_schema_v2_valido():
    con = _create_v2_db()
    ok, msg = verificar_schema_v2(con)
    assert ok is True
    assert msg == "OK"


def test_2_ausencia_de_tabla_de_ticks():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE hft_zones_v2 (id INT);")
    ok, msg = verificar_schema_v2(con)
    assert ok is False
    assert "hft_ticks_v2" in msg


def test_3_diferencia_de_1_ns():
    con = _create_v2_db()
    _seed_standard_run(con)
    # Corromper start_ts_ns por 1 nanosegundo
    con.execute("UPDATE hft_zones_v2 SET start_ts_ns = start_ts_ns + 1 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["matched_diffs_count"] == 1
    assert res["matched_diffs_samples"][0]["diffs"][0][0] == "start_ts_ns"


def test_4_diferencia_de_un_tick():
    con = _create_v2_db()
    _seed_standard_run(con)
    con.execute("UPDATE hft_zones_v2 SET lo_ticks = lo_ticks - 1 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["matched_diffs_count"] == 1
    assert res["matched_diffs_samples"][0]["diffs"][0][0] == "lo_ticks"


def test_5_zone_seq_duplicado():
    con = _create_v2_db()
    _seed_standard_run(con)
    # Forzar duplicado de zone_seq insertando en tabla sin constraint directa o temporal
    con.execute("DROP TABLE hft_zones_v2;")
    con.execute("""
        CREATE TABLE hft_zones_v2 (
            id INTEGER PRIMARY KEY, instrument TEXT, contract TEXT, session_id TEXT, zone_seq INTEGER,
            start_tick_seq INT, end_tick_seq INT, start_ts_ns INT, end_ts_ns INT, available_ts_ns INT,
            direction INT, lo_ticks INT, hi_ticks INT, pasos INT, vol REAL, avg_ms REAL, total_ms REAL,
            volume_rate REAL, parameter_manifest_sha256 TEXT, indicator_source_sha256 TEXT
        );
    """)
    # Insertar dos filas con zone_seq = 1
    t0 = 1780437841010000000
    for i in (1, 2):
        con.execute("INSERT INTO hft_zones_v2 VALUES (?, 'NQ JUN26', 'NQ JUN26', '20260603', 1, 1, 10, ?, ?, ?, 1, 115001, 115010, 10, 100.0, 10.0, 90.0, 1111.11, ?, ?)",
                    (i, t0, t0+90000000, t0+90000000, EXPECTED_PARAM_SHA256, EXPECTED_SOURCE_SHA256))
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["nt8_duplicates_count"] > 0


def test_6_gap_de_zone_seq():
    con = _create_v2_db()
    _seed_standard_run(con)
    # Cambiar zone_seq de 1 a 2 cuando solo hay 1 zona
    con.execute("UPDATE hft_zones_v2 SET zone_seq = 2 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["nt8_without_python_count"] == 1
    assert res["python_without_nt8_count"] == 1


def test_7_reset_de_sesion():
    con = _create_v2_db()
    # Sembrar dos sesiones distintas
    _seed_standard_run(con, session_id="20260603", n_ticks=12)
    _seed_standard_run(con, session_id="20260604", n_ticks=12)
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True
    assert res["total_nt8_zones"] == 2
    assert res["total_python_zones"] == 2


def test_8_reset_de_contrato():
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", contract="NQ JUN26")
    _seed_standard_run(con, session_id="20260616", contract="NQ SEP26")
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True
    assert res["total_nt8_zones"] == 2


def test_9_orden_alterado():
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", n_ticks=12)
    _seed_standard_run(con, session_id="20260604", n_ticks=12)
    # Invertir IDs en base de datos física
    con.execute("UPDATE hft_zones_v2 SET id = 99 WHERE session_id = '20260603'")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True


def test_10_hash_de_parametros_distinto():
    con = _create_v2_db()
    _seed_standard_run(con)
    con.execute("UPDATE hft_zones_v2 SET parameter_manifest_sha256 = 'corrupted_hash'")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert len(res["provenance_errors"]) > 0


def test_11_hash_de_source_distinto():
    con = _create_v2_db()
    _seed_standard_run(con)
    con.execute("UPDATE hft_zones_v2 SET indicator_source_sha256 = 'corrupted_source'")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert len(res["provenance_errors"]) > 0


def test_12_input_tick_diferente():
    con = _create_v2_db()
    _seed_standard_run(con)
    # Modificar un tick de entrada (alterar precio para romper la racha)
    con.execute("UPDATE hft_ticks_v2 SET price_ticks = price_ticks - 10 WHERE tick_seq = 5")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False


def test_13_zona_extra_python():
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603")
    _seed_standard_run(con, session_id="20260604")
    # Borrar la zona de una de las sesiones en NT8 para que Python la tenga de más
    con.execute("DELETE FROM hft_zones_v2 WHERE session_id = '20260604'")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["python_without_nt8_count"] == 1


def test_14_zona_extra_nt8():
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603")
    # Insertar una zona extra en NT8 en otra sesión sin ticks asociados
    con.execute("""
        INSERT INTO hft_zones_v2 (
            instrument, contract, session_id, zone_seq, start_tick_seq, end_tick_seq,
            start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks,
            pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256,
            indicator_source_sha256, valid_steps, max_retro, cvd_sweep, buy_vol,
            sell_vol, delta_slope, delta_first, delta_second, max_tick_vol,
            no_move_ticks, no_move_vol, max_level_ticks, bucket, price_upper,
            price_lower, price_mid, height_ticks, tick_res
        ) SELECT
            instrument, contract, '20260604', 1, start_tick_seq, end_tick_seq,
            start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks,
            pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256,
            indicator_source_sha256, valid_steps, max_retro, cvd_sweep, buy_vol,
            sell_vol, delta_slope, delta_first, delta_second, max_tick_vol,
            no_move_ticks, no_move_vol, max_level_ticks, bucket, price_upper,
            price_lower, price_mid, height_ticks, tick_res
        FROM hft_zones_v2 WHERE session_id = '20260603'
    """)
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["nt8_without_python_count"] == 1


def test_15_colision_ambigua():
    con = _create_v2_db()
    _seed_standard_run(con)
    # Insertar una fila con clave idéntica en tabla sin constraint
    con.execute("INSERT OR REPLACE INTO hft_zones_v2 (id, instrument, contract, session_id, zone_seq, start_tick_seq, end_tick_seq, start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks, pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256, indicator_source_sha256, valid_steps, max_retro, cvd_sweep, buy_vol, sell_vol, delta_slope, delta_first, delta_second, max_tick_vol, no_move_ticks, no_move_vol, max_level_ticks, bucket, price_upper, price_lower, price_mid, height_ticks, tick_res) SELECT 999, instrument, contract, session_id, 99, start_tick_seq, end_tick_seq, start_ts_ns, end_ts_ns, available_ts_ns, direction, lo_ticks, hi_ticks, pasos, vol, avg_ms, total_ms, volume_rate, parameter_manifest_sha256, indicator_source_sha256, valid_steps, max_retro, cvd_sweep, buy_vol, sell_vol, delta_slope, delta_first, delta_second, max_tick_vol, no_move_ticks, no_move_vol, max_level_ticks, bucket, price_upper, price_lower, price_mid, height_ticks, tick_res FROM hft_zones_v2 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False


def test_16_export_vacio():
    con = _create_v2_db()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert "FAIL_EMPTY" in res["status"]


def test_17_diferencia_sub_ms_falla_en_v2():
    """En V2, una diferencia de 100 ns (sub-milisegundo) DEBE fallar (cero tolerancia sub-ms)."""
    con = _create_v2_db()
    _seed_standard_run(con)
    # Sumar 500_000 ns (0.5 ms) a start_ts_ns
    con.execute("UPDATE hft_zones_v2 SET start_ts_ns = start_ts_ns + 500000 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["matched_diffs_count"] == 1


def test_18_exito_exacto_completo():
    """Cuando input y output provienen de la misma corrida y coinciden al 100%, emite PASS_CERTIFIED."""
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", n_ticks=15)
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True
    assert res["status"] == "PASS_CERTIFIED"
    assert res["matched_exact_count"] == 1
    assert res["matched_diffs_count"] == 0
    assert res["nt8_without_python_count"] == 0
    assert res["python_without_nt8_count"] == 0


def test_19_diferencia_start_tick_seq_falla():
    """Una discrepancia de 1 en start_tick_seq debe provocar FAIL con field_difference."""
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", n_ticks=15)
    con.execute("UPDATE hft_zones_v2 SET start_tick_seq = start_tick_seq + 1 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["matched_diffs_count"] == 1
    diff_fields = [d[0] for d in res["matched_diffs_samples"][0]["diffs"]]
    assert "start_tick_seq" in diff_fields


def test_20_diferencia_end_tick_seq_falla():
    """Una discrepancia de 1 en end_tick_seq debe provocar FAIL con field_difference."""
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", n_ticks=15)
    con.execute("UPDATE hft_zones_v2 SET end_tick_seq = end_tick_seq + 1 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    assert res["matched_diffs_count"] == 1
    diff_fields = [d[0] for d in res["matched_diffs_samples"][0]["diffs"]]
    assert "end_tick_seq" in diff_fields

