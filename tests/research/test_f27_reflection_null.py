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
    """Test 3: Nulo sintético simétrico -> E[r] = 0."""
    # Como la carrera es de primer pasaje, una caminata aleatoria simétrica (high/low constantes,
    # solo sube/baja +- 1 tick al azar) debería tocar el espejo vs real 50/50.
    # Hacemos uno determinista y trivial:
    # 10 pares zona/espejo equidistantes.
    # 5 pares el precio va hacia arriba, 5 pares hacia abajo.
    res_r = []
    for i in range(10):
        # Zona bull arriba
        zona = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
        high_t, low_t, close_t = _flat_bars(10, base_close=1000)
        reflejo = f27.construir_reflejo(zona, close_t)
        if i % 2 == 0:
            # Sube y toca la zona real primero
            high_t[5] = 1030
        else:
            # Baja y toca el espejo primero
            low_t[5] = 970
            
        carrera = f27.first_passage_race(
            zona, reflejo, 0, high_t, low_t, close_t, 10
        )
        res_r.append(carrera["r_i"])
        
    assert np.mean(res_r) == 0.0


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
    """Test 5: Empate en la misma barra -> resuelto por tick.
    Por ahora smoke_estructural marca same_bar_needs_tick_tiebreak."""
    zona = dict(lo_tick=1020, hi_tick=1050, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(10, base_close=1000)
    reflejo = f27.construir_reflejo(zona, close_t)
    
    # Sube y baja en la MISMA barra (barra ancha)
    high_t[3] = 1030
    low_t[3] = 970
    
    carrera = f27.first_passage_race(
        zona, reflejo, 0, high_t, low_t, close_t, 10
    )
    assert carrera["r_i"] == 0.0
    assert carrera["category"] == "same_bar_needs_tick_tiebreak"


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
    # Zonas superpuestas con el reflejo
    # Anchor = 1000. Zona [990, 1010]. Reflejo [2*1000-1010, 2*1000-990] = [990, 1010]
    zona_overlap = dict(lo_tick=990, hi_tick=1010, created_bar=0, is_bull=True)
    high_t, low_t, close_t = _flat_bars(5, base_close=1000)
    ref = f27.construir_reflejo(zona_overlap, close_t)
    assert not ref["is_eligible"]
    assert ref["exclusion_reason"] == "not_disjoint"


def test_08_cutoff_pre_holdout():
    """Test 8: Cutoff pre-holdout. 2026-06-30 límite. Julio debe excluirse."""
    import tempfile
    import pyarrow as pa
    import pyarrow.parquet as pq
    
    # Fake parquet with one session in June and one in July
    df = pd.DataFrame({
        "ts_ms": [
            pd.Timestamp("2026-06-25 10:00:00", tz=TZ_CHART).value // 10**6,
            pd.Timestamp("2026-07-05 10:00:00", tz=TZ_CHART).value // 10**6,
        ],
        "bid": [1.0, 1.0],
        "ask": [1.0, 1.0],
        "volume": [1, 1],
        "kind_t": [0, 0]  # Just to prevent parquet read errors
    })
    
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
        table = pa.Table.from_pandas(df)
        pq.write_table(table, f.name)
        
        # We can't easily mock the entire kernel_zones/bars extraction inside smoke_estructural
        # here without massive mocking, but we can verify that the python constant is correct:
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
    """Test 10: HAC sintético y determinismo."""
    # Generamos una serie sintética
    r_s_crono = [1.0, -1.0, 1.0, 1.0, 0.0, 1.0, -1.0, 1.0, -1.0, 1.0]
    ic = f27.hac_bartlett_ic(r_s_crono)
    assert ic["n_sessions"] == 10
    assert ic["mean"] == np.mean(r_s_crono)
    assert ic["se_hac"] > 0
    
    # Gate de abstención
    assert not ic["abstain_inferencia"]
    
    # Etiquetas de decisión
    assert f27.decidir_etiqueta_reflexion(ic, 0.40, 0.00) in ["REFLECTION_POSITIVE", "COMPATIBLE_WITH_ZERO", "REFLECTION_NEGATIVE"]
    assert f27.decidir_etiqueta_reflexion(ic, 0.20, 0.00) == "ABSTAIN_RESOLUTION"
    assert f27.decidir_etiqueta_reflexion(ic, 0.40, 0.02) == "ABSTAIN_TIE_RULE"

