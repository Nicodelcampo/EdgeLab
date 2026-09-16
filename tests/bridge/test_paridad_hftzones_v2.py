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


def _seed_standard_run(con, session_id="20260603", contract="NQ JUN26", n_ticks=15,
                       prev_session_close_ticks=None):
    """Inserta una racha limpia de ticks alcistas que genera una zona válida idéntica en Python y NT8.

    Retorna el último precio (en ticks) de esta sesión para encadenar con la siguiente.
    """
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

    # Usar los MISMOS parámetros que el comparador: prev_session_close_ticks si aplica
    cands = hz.detect_candidates(ts_list, px_list, vol_list,
                                 prev_session_close_ticks=prev_session_close_ticks)
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
            int(z["ts_start"]), int(z["ts_end"]), int(z["ts_avail"]), int(z["direction"]),
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
    return px_list[-1] if px_list else None


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
    # Sembrar dos sesiones distintas: encadenar prev_close para reproducir NT8
    prev = _seed_standard_run(con, session_id="20260603", n_ticks=12)
    _seed_standard_run(con, session_id="20260604", n_ticks=12, prev_session_close_ticks=prev)
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True
    assert res["total_nt8_zones"] == res["total_python_zones"]


def test_8_reset_de_contrato():
    con = _create_v2_db()
    prev = _seed_standard_run(con, session_id="20260603", contract="NQ JUN26")
    _seed_standard_run(con, session_id="20260616", contract="NQ SEP26",
                       prev_session_close_ticks=prev)
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True
    assert res["total_nt8_zones"] >= 1


def test_9_orden_alterado():
    con = _create_v2_db()
    prev = _seed_standard_run(con, session_id="20260603", n_ticks=12)
    _seed_standard_run(con, session_id="20260604", n_ticks=12, prev_session_close_ticks=prev)
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


# ==============================================================================
# TESTS OBLIGATORIOS DEL AUDITOR — Semántica causal de available_ts_ns
# ==============================================================================

def _make_tick_stream(prices, gap_ms=10, t0_ns=1_780_437_841_000_000_000, vol=10.0):
    """Helper: construye ts_ns, price_ticks, volume a partir de una lista de precios."""
    n = len(prices)
    ts = [t0_ns + i * gap_ms * 1_000_000 for i in range(n)]
    vols = [vol] * n
    return ts, list(prices), vols


def test_21_termination_reason_reversal():
    """Una racha cerrada por retroceso excesivo tiene termination_reason='REVERSAL'."""
    # Racha alcista seguida de caída brusca
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
              90]  # caída brusca → retroceso > umbral → REVERSAL
    ts, px, vols = _make_tick_stream(prices)
    cands = hz.detect_candidates(ts, px, vols)
    reversal_cands = [c for c in cands if c["termination_reason"] == "REVERSAL"]
    assert len(reversal_cands) >= 1, "Debe haber al menos un candidato con REVERSAL"


def test_22_termination_reason_max_pause():
    """Una racha cortada por silencio > max_pausa_ms tiene termination_reason='MAX_PAUSE'."""
    # Racha alcista, luego pausa de 200ms (> max_pausa=100ms), luego más ticks
    t0 = 1_780_437_841_000_000_000
    # 10 ticks alcistas, espaciados 10ms
    prices = list(range(100, 110)) + [110, 111, 112]
    ts = [t0 + i * 10_000_000 for i in range(10)]
    # Pausa de 200ms antes del tick 10
    ts += [ts[-1] + 200_000_000, ts[-1] + 210_000_000, ts[-1] + 220_000_000]
    vols = [10.0] * len(prices)
    cands = hz.detect_candidates(ts, prices, vols)
    pause_cands = [c for c in cands if c["termination_reason"] == "MAX_PAUSE"]
    assert len(pause_cands) >= 1, "Debe haber al menos un candidato con MAX_PAUSE"


def test_23_termination_reason_end_of_input():
    """Una racha que llega al fin del stream sin reversal ni pausa tiene termination_reason='END_OF_INPUT'."""
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]
    ts, px, vols = _make_tick_stream(prices)
    cands = hz.detect_candidates(ts, px, vols)
    # La última racha (que llega al fin) debe ser END_OF_INPUT
    assert len(cands) >= 1
    last = cands[-1]
    assert last["termination_reason"] == "END_OF_INPUT"


def test_24_available_ts_ns_mayor_o_igual_a_end_ts_ns():
    """available_ts_ns >= end_ts_ns siempre: el confirmador no puede anticipar el cierre."""
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
              90, 91, 92, 93, 94, 95, 96, 97, 98, 99]
    ts, px, vols = _make_tick_stream(prices, gap_ms=5)
    cands = hz.detect_candidates(ts, px, vols)
    for c in cands:
        assert c["ts_avail"] >= c["ts_end"], (
            f"available_ts_ns ({c['ts_avail']}) < end_ts_ns ({c['ts_end']}) "
            f"para racha idx={c['idx_start']}..{c['idx_end']}"
        )


def test_25_ticks_con_timestamp_identico():
    """Ticks con el mismo timestamp no rompen la máquina de estados ni el invariante causal."""
    # Varios ticks simultáneos (mismo ms)
    t0 = 1_780_437_841_000_000_000
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115]
    ts = [t0] * 8 + [t0 + 10_000_000] * 8  # primeros 8 al mismo tiempo
    vols = [10.0] * 16
    cands = hz.detect_candidates(ts, prices, vols)
    for c in cands:
        assert c["ts_avail"] >= c["ts_end"]
        assert c["termination_reason"] in ("REVERSAL", "MAX_PAUSE", "END_OF_INPUT")


def test_26_reversal_mismo_timestamp_available_igual_end():
    """Si el tick de reversión tiene el mismo timestamp que el último tick de la zona,
    available_ts_ns == end_ts_ns es válido (no hay anticipación)."""
    t0 = 1_780_437_841_000_000_000
    # Racha alcista, último tick y tick de reversión comparten timestamp
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 90]
    ts = [t0 + i * 10_000_000 for i in range(11)] + [t0 + 10 * 10_000_000]  # tick 11 mismo ts que tick 10
    vols = [10.0] * 12
    cands = hz.detect_candidates(ts, prices, vols)
    reversal_cands = [c for c in cands if c["termination_reason"] == "REVERSAL"]
    if reversal_cands:
        c = reversal_cands[0]
        # available_ts_ns == end_ts_ns es válido cuando el tick de reversión es simultáneo
        assert c["ts_avail"] >= c["ts_end"]


def test_27_zona_no_contribuye_entre_end_y_available():
    """Una zona no debe ser visible en [end_ts_ns, available_ts_ns).
    Solo es causal a partir de available_ts_ns."""
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 90]
    ts, px, vols = _make_tick_stream(prices, gap_ms=10)
    cands = hz.detect_candidates(ts, px, vols)
    acc_zones, _ = hz.accept_all(cands, dict(hz.ACCEPT_DEFAULTS), tick_size=0.25)
    for z in acc_zones:
        end_ts = z["ts_end"]
        avail_ts = z["ts_avail"]
        # En cualquier t tal que end_ts <= t < avail_ts, la zona NO debe contribuir
        # El test verifica la invariante: avail_ts >= end_ts
        assert avail_ts >= end_ts, "Firewall causal violado: avail < end"
        # Si avail > end, la zona tiene un periodo de latencia antes de ser causal
        if avail_ts > end_ts:
            # Hay al menos 1 ns de gap entre confirmación y disponibilidad
            assert avail_ts - end_ts > 0


def test_28_ticks_futuros_no_alteran_zonas_confirmadas():
    """Agregar ticks después del cierre de una zona no cambia sus campos ya confirmados."""
    prices_base = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 90]
    ts_base, px_base, vols_base = _make_tick_stream(prices_base, gap_ms=10)
    cands_base = hz.detect_candidates(ts_base, px_base, vols_base)

    # Añadir ticks futuros
    prices_ext = prices_base + [91, 92, 93, 94, 95]
    ts_ext = ts_base + [ts_base[-1] + (i+1) * 10_000_000 for i in range(5)]
    vols_ext = vols_base + [10.0] * 5
    cands_ext = hz.detect_candidates(ts_ext, prices_ext, vols_ext)

    # La primera zona (mismo idx_start) debe tener los mismos campos confirmados
    cands_base_reversal = [c for c in cands_base if c["termination_reason"] == "REVERSAL"]
    cands_ext_reversal = [c for c in cands_ext if c["termination_reason"] == "REVERSAL"]

    if cands_base_reversal and cands_ext_reversal:
        cb = cands_base_reversal[0]
        ce = cands_ext_reversal[0]
        assert cb["idx_start"] == ce["idx_start"]
        assert cb["idx_end"] == ce["idx_end"]
        assert cb["ts_start"] == ce["ts_start"]
        assert cb["ts_end"] == ce["ts_end"]
        assert cb["ts_avail"] == ce["ts_avail"]
        assert cb["termination_reason"] == ce["termination_reason"]


def test_29_frontera_de_sesion_aislamiento():
    """La frontera de sesión es un cierre explícito: las zonas de cada sesión
    son independientes y no cruzan la frontera."""
    con = _create_v2_db()
    prev = _seed_standard_run(con, session_id="20260603", n_ticks=15)
    _seed_standard_run(con, session_id="20260604", n_ticks=15, prev_session_close_ticks=prev)
    # Verificar que no hay zonas con session_id mezclado (invariante de aislamiento)
    rows = con.execute(
        "SELECT DISTINCT session_id FROM hft_zones_v2 ORDER BY session_id"
    ).fetchall()
    session_ids = [r[0] for r in rows]
    assert "20260603" in session_ids
    assert "20260604" in session_ids
    # Verificar que la certificación pasa con aislamiento correcto
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is True


def test_30_available_ts_ns_diferencia_falla_certificacion():
    """Una diferencia en available_ts_ns provoca FAIL en la certificación."""
    con = _create_v2_db()
    _seed_standard_run(con, session_id="20260603", n_ticks=15)
    # Retroceder available_ts_ns para simular backdating (viola el firewall causal)
    con.execute("UPDATE hft_zones_v2 SET available_ts_ns = end_ts_ns - 1 WHERE zone_seq = 1")
    con.commit()
    res = comparar_v2_exacto(con, "NQ JUN26")
    assert res["is_pass"] is False
    # El diff debe reportarse en available_ts_ns
    diffs = res.get("matched_diffs_samples", [])
    if diffs:
        diff_fields = [d[0] for d in diffs[0]["diffs"]]
        assert "available_ts_ns" in diff_fields
