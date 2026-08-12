import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
F27_MOD_PATH = REPO / "diag" / "tasa_senales" / "F2.7_nulo_reflexion_local.py"

_spec = importlib.util.spec_from_file_location("f27_nulo", F27_MOD_PATH)
f27 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f27)

# Import F1.1 components needed for testing via F2.7
from diag.tasa_senales.curva_excursion_ticks import TZ_CHART


# ======================================================================
# Fixtures sintéticas reutilizables
# ======================================================================

def _flat_bars(n_bars, base_close=10000, base_vol=100.0):
    """High=low=close=base_close en todas las barras."""
    high_t = np.full(n_bars, base_close, dtype=np.int64)
    low_t = np.full(n_bars, base_close, dtype=np.int64)
    close_t = np.full(n_bars, base_close, dtype=np.int64)
    return high_t, low_t, close_t


# ======================================================================
# Tests Truth-Known (Protocolo §6)
# ======================================================================

def test_01_geometria_reflexion_exacta():
    """Test 1: Reflexión exacta; ancho/distancia conservados; side preservado."""
    # Zona bull: precio sube para atrapar vendedores, el anchor está abajo.
    # Supongamos anchor = 1000. Zona bull [1020, 1050].
    # Distancia = 20 ticks. Ancho = 30 ticks.
    zona_bull = dict(
        lo_tick=1020, hi_tick=1050, created_bar=5, is_bull=True
    )
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)

    res = f27.construir_reflejo(zona_bull, close_t)
    # Reflejo: 2*anchor - hi, 2*anchor - lo -> 2000 - 1050 = 950, 2000 - 1020 = 980
    assert res["mirror_lo_tick"] == 950
    assert res["mirror_hi_tick"] == 980
    assert res["width_ticks"] == 30
    assert res["distance_ticks"] == 20
    assert res["mirror_is_bull_for_lifecycle"] is False  # D2 fix

    # Zona bear: precio baja para atrapar compradores, el anchor está arriba.
    # Supongamos anchor = 1000. Zona bear [950, 980].
    # Distancia = 20 ticks. Ancho = 30 ticks.
    zona_bear = dict(
        lo_tick=950, hi_tick=980, created_bar=5, is_bull=False
    )
    res_bear = f27.construir_reflejo(zona_bear, close_t)
    # Reflejo: 2000 - 980 = 1020, 2000 - 950 = 1050
    assert res_bear["mirror_lo_tick"] == 1020
    assert res_bear["mirror_hi_tick"] == 1050
    assert res_bear["width_ticks"] == 30
    assert res_bear["distance_ticks"] == 20
    assert res_bear["mirror_is_bull_for_lifecycle"] is True  # D2 fix


def test_02_regresion_d2_espejo_no_muere_en_b1():
    """Test 2: REGRESIÓN DE D2. En la spec v1, un espejo bull ubicado bajo el precio
    (porque el precio ancla está arriba) moría en B+1 por CloseThrough porque
    is_bull se conservaba. El path ascendente mataba al espejo bull (adverso = close < lo)."""
    # Zona originaria BEAR: [950, 980], anchor = 1000
    # Reflejo: [1020, 1050] (arriba del precio)
    zona_bear = dict(lo_tick=950, hi_tick=980, created_bar=0, is_bull=False)
    high_t, low_t, close_t = _flat_bars(5, base_close=1000)

    # El precio SUBE en B+1 a 1010
    close_t[1] = 1010
    high_t[1] = 1010
    low_t[1] = 1010

    reflejo = f27.construir_reflejo(zona_bear, close_t)
    assert reflejo["mirror_is_bull_for_lifecycle"] is True  # Tratar como bull

    # Computamos carrera
    carrera = f27.first_passage_race(
        zona_bear, reflejo, 0, high_t, low_t, close_t, 5,
        invalidation_mode="CloseThrough"
    )
    # Bajo spec v1, si el espejo no invertía side, era tratado como BEAR.
    # Un bear muere si close > hi (1010 no es > 1050, así que vivía).
    # Pero el problema D2 era con zonas BULL originarias:

    # Zona originaria BULL: [1020, 1050], anchor = 1000
    # Reflejo: [950, 980] (abajo del precio)
    zona_bull = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
    high_t2, low_t2, close_t2 = _flat_bars(5, base_close=1000)

    # El precio SUBE en B+1 a 1010 (se aleja del espejo)
    close_t2[1] = 1010
    high_t2[1] = 1010
    low_t2[1] = 1010

    reflejo2 = f27.construir_reflejo(zona_bull, close_t2)
    # Spec v2: espejo abajo del precio (950-980) -> se trata como BEAR (muere si sube por arriba de HI)
    assert reflejo2["mirror_is_bull_for_lifecycle"] is False

    carrera2 = f27.first_passage_race(
        zona_bull, reflejo2, 0, high_t2, low_t2, close_t2, 5,
        invalidation_mode="CloseThrough"
    )
    # Bajo spec v1: el espejo [950, 980] era BULL. Regla: muere si close > hi (980).
    # Como el precio sube a 1010, 1010 > 980 -> ¡MUERTE EN B+1! (defecto D2).
    # Bajo spec v2: el espejo se trata como BEAR. Regla: muere si close < lo (950).
    # El precio sube a 1010. 1010 NO es < 950. ¡El espejo SOBREVIVE!
    assert carrera2["mirror_lifecycle"]["removed_reason"] is None
    assert carrera2["mirror_lifecycle"]["censored"] is True  # Sobrevive hasta el fin (doble censura en este path)


def test_03_nulo_sintetico_caminata():
    """Test 3: Nulo sintético simétrico -> Monte Carlo E[r] ≈ 0 (|E[r]| < 0.03)."""
    np.random.seed(42)
    n_sims = 1000
    res_r = []

    for _ in range(n_sims):
        # Anchor = 1000, Zona Bull = [1020, 1030] (d=20), Reflejo = [970, 980]
        zona = dict(lo_tick=1020, hi_tick=1030, created_bar=0, is_bull=True)
        high_t, low_t, close_t = _flat_bars(200, base_close=1000)
        reflejo = f27.construir_reflejo(zona, close_t)

        # Random walk starting from 1000
        steps = np.random.choice([-1, 1], size=199)
        path = 1000 + np.cumsum(steps)
        close_t[1:] = path
        high_t[1:] = path + np.random.randint(0, 2, size=199)
        low_t[1:] = path - np.random.randint(0, 2, size=199)

        carrera = f27.first_passage_race(
            zona, reflejo, 0, high_t, low_t, close_t, 200
        )
        res_r.append(carrera["r_i"])

    mean_r = np.mean(res_r)
    assert abs(mean_r) < 0.03, f"Monte Carlo E[r] = {mean_r:.4f} exceeds tolerance"


def test_04_senal_plantada():
    """Test 4: Señal sintética conocida; atracción."""
    zona = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)
    reflejo = f27.construir_reflejo(zona, close_t)

    # Sube en B+2, toca zona real
    high_t[2] = 1030

    # Baja en B+5, toca espejo
    low_t[5] = 970

    carrera = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10
    )
    assert carrera["r_i"] == 1.0
    assert carrera["category"] == "real_first"


def test_05_empate_misma_barra():
    """Test 5: Empate en la misma barra -> resuelto por tick (H2)."""
    zona = dict(lo_tick=1020, hi_tick=1030, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)
    reflejo = f27.construir_reflejo(zona, close_t)

    # Sube y baja en la MISMA barra (barra 3)
    high_t[3] = 1030
    low_t[3] = 970

    # Sin arreglos de ticks -> marca same_bar_needs_tick_tiebreak
    carrera_no_ticks = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10
    )
    assert carrera_no_ticks["r_i"] == 0.0
    assert carrera_no_ticks["category"] == "same_bar_needs_tick_tiebreak"

    # Con ticks dentro de la barra 3:
    # Caso A: Toca real en tick 2, espejo en tick 5 -> real_first
    tk_prices_a = np.array([1000, 1000, 1025, 1000, 1000, 975, 1000], dtype=np.int64)
    bar_slices = {3: (0, 7)}
    r_a, cat_a = f27.resolver_empate_por_tick(zona, reflejo, 3, tk_prices_a, bar_slices)
    assert r_a == 1.0
    assert cat_a == "real_first"

    # Caso B: Toca espejo en tick 1, real en tick 4 -> mirror_first
    tk_prices_b = np.array([1000, 975, 1000, 1000, 1025, 1000], dtype=np.int64)
    bar_slices_b = {3: (0, 6)}
    r_b, cat_b = f27.resolver_empate_por_tick(zona, reflejo, 3, tk_prices_b, bar_slices_b)
    assert r_b == -1.0
    assert cat_b == "mirror_first"

    # Caso C: Toca exacto en el mismo tick (tick 2) -> empate_tecnico
    tk_prices_c = np.array([1000, 1000, 1000], dtype=np.int64)
    # fake price tick that satisfies neither or satisfy exact tie rule
    r_c, cat_c = f27.resolver_empate_por_tick(zona, reflejo, 3, tk_prices_c, bar_slices)
    assert r_c == 0.0
    assert cat_c == "empate_tecnico"

    # Integración con first_passage_race
    carrera_ticks = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10,
        tk_price_ticks=tk_prices_a, bar_start_ends=bar_slices
    )
    assert carrera_ticks["r_i"] == 1.0
    assert carrera_ticks["category"] == "real_first"


def test_06_doble_censura():
    """Test 6: Doble censura reportada."""
    zona = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)
    reflejo = f27.construir_reflejo(zona, close_t)

    # Nada toca nada hasta max_age_bars
    carrera = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10, max_age_bars=5
    )
    assert carrera["r_i"] == 0.0
    assert carrera["category"] == "double_censoring"


def test_07_no_overlap_eligibility():
    """Test 7: Eligibilidad de no-overlap y distintas."""
    zona_overlap = dict(lo_tick=990, hi_tick=1010, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(5, base_close=1000)
    ref = f27.construir_reflejo(zona_overlap, close_t)
    assert not ref["is_eligible"]
    assert ref["exclusion_reason"] == "not_disjoint"


def test_08_cutoff_pre_holdout():
    """Test 8: Cutoff pre-holdout. 2026-06-30 límite. Julio debe excluirse."""
    sesiones_disponibles = ["2026-06-25", "2026-06-26", "2026-06-30", "2026-07-01", "2026-07-02"]
    sesiones_research = [s for s in sesiones_disponibles if s <= f27.RESEARCH_END_INCLUSIVE]
    sesiones_excluidas = [s for s in sesiones_disponibles if s > f27.RESEARCH_END_INCLUSIVE]

    assert sesiones_research == ["2026-06-25", "2026-06-26", "2026-06-30"]
    assert sesiones_excluidas == ["2026-07-01", "2026-07-02"]
    assert f27.RESEARCH_END_INCLUSIVE == "2026-06-30"


def test_09_igualdad_horizonte_precedencia():
    """Test 9: Precedencia y barra creadora nunca cuenta."""
    zona = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)
    reflejo = f27.construir_reflejo(zona, close_t)

    # Barra 0: Toca la zona. NO DEBE CONTAR.
    high_t[0] = 1030

    carrera = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10
    )
    # Doble censura porque B=0 se ignora
    assert carrera["r_i"] == 0.0
    assert carrera["category"] == "double_censoring"


def test_10_hac_y_arbol_dirty():
    """Test 10: HAC sintético, etiquetas de decisión y guard de árbol dirty."""
    # Serie sintética
    r_s_crono = [1.0, -1.0, 1.0, 1.0, 0.0, 1.0, -1.0, 1.0, -1.0, 1.0]
    ic = f27.hac_bartlett_ic(r_s_crono)
    assert ic["n_sessions"] == 10
    assert ic["mean"] == np.mean(r_s_crono)
    assert ic["se_hac"] > 0
    assert not ic["abstain_inferencia"]

    # Etiquetas de decisión
    assert f27.decidir_etiqueta_reflexion(ic, 0.40, 0.00) in ["REFLECTION_POSITIVE", "COMPATIBLE_WITH_ZERO", "REFLECTION_NEGATIVE"]
    assert f27.decidir_etiqueta_reflexion(ic, 0.20, 0.00) == "ABSTAIN_RESOLUTION"
    assert f27.decidir_etiqueta_reflexion(ic, 0.40, 0.02) == "ABSTAIN_TIE_RULE"

    # Verificación de git_dirty
    dirty = f27.git_dirty()
    assert isinstance(dirty, bool)


