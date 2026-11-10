"""Tests de paridad y causalidad para `edgelab.bridge.indicators.hftzones_nq_rangos_pct_v2`.

Verifica:
  1. Paridad exacta (24/24 campos por candidato y 7/7 compuertas de rechazo) entre el motor
     Numba (`detectar_candidatos_nb` + `filtrar_zonas_nb`) y el motor base certificado
     `edgelab.bridge.indicators.hftzones_nq`.
  2. Causalidad estricta (0 look-ahead) y detección por densidad de solapamiento (`packing`)
     en `evaluar_clusters_causales_nb`, incluyendo pilas de zonas de 4-6 puntos de alto.
  3. Actualización in-place sin desfase ni superposición en `evaluar_expansiones_causales_nb`.
  4. Generación en una sola pasada del almacén multi-definición `almacen_clusters_hft_grilla`.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.bridge.indicators import hftzones_nq as hz_base
from edgelab.bridge.indicators import hftzones_nq_rangos_pct_v2 as hzv2

MS = 1_000_000  # ns por milisegundo


def _stream_sintetico_complejo(seed: int = 42, n: int = 2500):
    """Genera un stream 1-tick con rachas rápidas, pausas, absorciones y reversiones."""
    rng = np.random.default_rng(seed)
    ts = np.zeros(n, dtype=np.int64)
    px = np.zeros(n, dtype=np.int64)
    vol = np.zeros(n, dtype=np.float64)

    cur_t = 1_700_000_000_000_000_000
    cur_p = 80_000  # 20,000.00 en NQ
    for i in range(n):
        # Insertar pausas ocasionales > 100ms
        if i > 0 and i % 180 == 0:
            dt_ms = float(rng.uniform(120.0, 400.0))
        else:
            dt_ms = float(rng.uniform(0.5, 12.0))
        cur_t += int(dt_ms * MS)
        ts[i] = cur_t

        # Alternar bloques direccionales, bloques planos (absorb) y ruido
        bloque = (i // 25) % 4
        if bloque == 0:
            step = int(rng.choice([0, 1, 1, 1, -1]))
        elif bloque == 1:
            step = int(rng.choice([0, -1, -1, -1, 1]))
        elif bloque == 2:
            step = 0  # absorción pura en el mismo precio
        else:
            step = int(rng.choice([-2, -1, 0, 1, 2]))
        cur_p += step
        px[i] = cur_p
        vol[i] = float(rng.integers(1, 25))

    return ts, px, vol


def test_paridad_exacta_candidatos_y_zonas_contra_hftzones_nq():
    """El motor Numba debe producir exactamente los mismos 24 campos por candidato y las mismas
    zonas/motivos de rechazo que `hftzones_nq.detect_candidates` + `accept_all`."""
    ts, px, vol = _stream_sintetico_complejo(seed=101, n=3000)

    cands_ref = hz_base.detect_candidates(ts.tolist(), px.tolist(), vol.tolist())
    cands_v2 = hzv2.detect_candidates(ts, px, vol)

    assert len(cands_v2) == len(cands_ref) > 50

    for c_ref, c_v2 in zip(cands_ref, cands_v2):
        assert c_v2.keys() == c_ref.keys()
        for k in c_ref:
            v_r = c_ref[k]
            v_2 = c_v2[k]
            if isinstance(v_r, float):
                assert v_2 == pytest.approx(v_r, rel=1e-9, abs=1e-9), f"Diferencia en campo {k}"
            else:
                assert v_2 == v_r, f"Diferencia en campo {k}: {v_2} != {v_r}"

    # Verificar también con prev_session_close_ticks
    cands_ref_prev = hz_base.detect_candidates(
        ts.tolist(), px.tolist(), vol.tolist(), prev_session_close_ticks=int(px[0] + 2)
    )
    cands_v2_prev = hzv2.detect_candidates(
        ts, px, vol, prev_session_close_ticks=int(px[0] + 2)
    )
    assert len(cands_v2_prev) == len(cands_ref_prev)
    for c_ref, c_v2 in zip(cands_ref_prev[:30], cands_v2_prev[:30]):
        for k in ("idx_start", "idx_end", "ts_avail", "direction", "pasos", "valid_steps", "cvd"):
            assert c_v2[k] == pytest.approx(c_ref[k])

    # Verificar paridad en filtrado de zonas y conteo de compuertas
    ses = np.zeros(len(ts), dtype=np.int64)
    pbar = np.arange(len(ts), dtype=np.int64)
    c_int, c_flt = hzv2.detectar_candidatos_nb(ts, px, vol, ses, pbar)
    acc_idx, b_codes, gate_counts = hzv2.filtrar_zonas_nb(c_int, c_flt)

    zonas_ref, motivos_ref = hz_base.accept_all(cands_ref)
    assert len(acc_idx) == len(zonas_ref) > 0

    for idx_z, b_code, z_ref in zip(acc_idx, b_codes, zonas_ref):
        assert int(c_int[idx_z, 0]) == z_ref["idx_start"]
        assert int(c_int[idx_z, 1]) == z_ref["idx_end"]
        assert hzv2.BUCKET_CODE_TO_STR[int(b_code)] == z_ref["bucket"]

    for gate_i, gate_name in enumerate(hz_base.GATE_ORDER):
        assert int(gate_counts[gate_i]) == motivos_ref.get(gate_name, 0)


def test_corte_de_sesion_emite_end_of_session():
    """Cuando cambia `session_ids`, una racha abierta debe cerrarse con `END_OF_SESSION`
    sin mezclar ticks entre sesiones."""
    ts = np.arange(20, dtype=np.int64) * (2 * MS)
    px = np.arange(1000, 1020, dtype=np.int64)
    vol = np.full(20, 10.0, dtype=np.float64)
    ses = np.array([0] * 10 + [1] * 10, dtype=np.int64)
    pbar = np.arange(20, dtype=np.int64)

    c_int, _ = hzv2.detectar_candidatos_nb(ts, px, vol, ses, pbar)
    assert len(c_int) == 2
    assert c_int[0, 6] == hzv2.REASON_END_OF_SESSION
    assert c_int[0, 1] == 9
    assert c_int[1, 0] == 10
    assert c_int[1, 6] == hzv2.REASON_CENSORED_END_OF_INPUT


def test_cluster_causal_detecta_pilas_de_zonas_altas_por_packing_sin_lookahead():
    """Un apilamiento de 4 zonas HFT de 20 ticks (5 puntos NQ) cada una que se solapan
    en una banda de 48 ticks (12 puntos) tiene `packing = 80 / 48 = 1.67` y debe ser
    detectado exactamente en `detect_bar` de la 4ta zona (sin look-ahead)."""
    z_detect_bar = np.array([10, 18, 25, 33], dtype=np.int64)
    z_detect_ts = np.array([10, 18, 25, 33], dtype=np.int64) * 1_000_000_000
    # 4 zonas de 20 ticks de alto apiladas entre 80000 y 80048
    z_lower_tk = np.array([80000, 80008, 80018, 80028], dtype=np.int64)
    z_upper_tk = np.array([80020, 80028, 80038, 80048], dtype=np.int64)
    z_vol = np.array([80.0, 95.0, 110.0, 90.0], dtype=np.float64)
    z_dir = np.array([-1, -1, -1, 1], dtype=np.int64)
    z_bucket = np.array([hzv2.BUCKET_ULTRA] * 4, dtype=np.int64)
    z_ses = np.zeros(4, dtype=np.int64)
    z_escala = np.full(4, 24.0, dtype=np.float64)

    clus_int, clus_flt = hzv2.evaluar_clusters_causales_nb(
        z_detect_bar,
        z_detect_ts,
        z_lower_tk,
        z_upper_tk,
        z_vol,
        z_dir,
        z_bucket,
        z_ses,
        z_escala,
        tick_size=0.25,
        min_zonas_cluster=4,
        modo_compresion=hzv2.MODO_V2_HIBRIDO,
    )

    assert len(clus_int) == 1
    # Nace estrictamente en la barra 33 (cuando se confirma la 4ta zona), nunca en la barra 10
    assert int(clus_int[0, 0]) == 33
    assert int(clus_int[0, 3]) == 4
    assert int(clus_int[0, 4]) == -1  # predominio bajista en volumen
    assert clus_flt[0, 0] == pytest.approx(80000 * 0.25)
    assert clus_flt[0, 1] == pytest.approx(80048 * 0.25)
    assert clus_flt[0, 3] == pytest.approx(48.0)
    assert clus_flt[0, 4] == pytest.approx(80.0 / 48.0)


def test_expansion_causal_actualiza_in_place_sin_apilar_ni_superponer():
    """En un impulso limpio sin zonas HFT que sigue extendiéndose barra a barra,
    `evaluar_expansiones_causales_nb` debe actualizar la frontera líder in-place
    manteniendo `detect_bar` fijo y sin crear múltiples expansiones superpuestas."""
    n_bars = 120
    bar_ts = np.arange(n_bars, dtype=np.int64) * 1_000_000_000
    bar_ses = np.zeros(n_bars, dtype=np.int64)
    bar_hi = np.zeros(n_bars, dtype=np.float64)
    bar_lo = np.zeros(n_bars, dtype=np.float64)
    bar_cl = np.zeros(n_bars, dtype=np.float64)

    # Generar piernas de zig-zag previas para poblar histScoreExp (>= 8 piernas)
    px = 20000.0
    for b in range(n_bars):
        if b < 84:
            leg = b // 6
            step = 5.0 if (leg % 2 == 0) else -5.0
            px += step
        else:
            # Gran expansión alcista limpia desde b=84 hasta b=119 (+6 puntos por barra)
            px += 6.0
        bar_cl[b] = px
        bar_hi[b] = px + 0.5
        bar_lo[b] = px - 0.5

    z_empty_i = np.empty(0, dtype=np.int64)
    exp_int, exp_flt, _ = hzv2.evaluar_expansiones_causales_nb(
        bar_ts,
        bar_hi,
        bar_lo,
        bar_cl,
        bar_ses,
        z_empty_i,
        z_empty_i,
        z_empty_i,
        z_empty_i,
        tick_size=0.25,
        pct_min_historia=6,
        min_exp_ticks=24.0,
    )

    assert len(exp_int) >= 1
    # Verificar que en la última pierna (b >= 84) sólo hay UNA expansión (actualizada in-place)
    exp_ultima_pierna = [i for i in range(len(exp_int)) if exp_int[i, 0] >= 84]
    assert len(exp_ultima_pierna) == 1
    idx_u = exp_ultima_pierna[0]
    assert exp_flt[idx_u, 3] > 100.0  # creció in-place hasta el final del impulso


def test_almacen_clusters_hft_grilla_una_pasada():
    """`almacen_clusters_hft_grilla` extrae candidatos una sola vez y genera el DataFrame
    multi-definición con el esquema esperado."""
    ts, px, vol = _stream_sintetico_complejo(seed=7, n=1500)
    gz_mini = {
        "Z_LAXO": dict(
            min_pasos=4,
            min_absorb_pasos=4,
            detect_absorb=True,
            min_sweep_ticks=2,
            max_avg_ms=50.0,
            max_total_ms=1000.0,
            min_volume_rate=10.0,
            min_total_volume=5.0,
            max_retroceso_ticks=3.0,
            retroceso_pct_height=60.0,
        )
    }
    gc_mini = {
        "C_K3_PK07": dict(
            min_zonas_cluster=3,
            min_packing=0.70,
            extension_dibujo=400,
            pct_extension_bars=300,
            max_span_mult=4.0,
            min_span_floor_ticks=120.0,
            modo_compresion=hzv2.MODO_PACKING_PURO,
        )
    }
    df = hzv2.almacen_clusters_hft_grilla(
        ts, px, vol, grilla_zona=gz_mini, grilla_cluster=gc_mini
    )
    expected_cols = {
        "t_ns",
        "detect_bar",
        "visual_end_bar",
        "lo",
        "hi",
        "poc",
        "n_zonas",
        "net_dir",
        "width_ticks",
        "packing",
        "score",
        "polaridad",
        "def_zona",
        "def_cluster",
        "def",
    }
    assert expected_cols.issubset(set(df.columns))
    assert len(df) > 0
    assert (df["hi"] > df["lo"]).all()
    assert (df["n_zonas"] >= 3).all()
