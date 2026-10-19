"""Tests obligatorios de regresión para NQ_SESSION_ELIGIBILITY_GATE_V1.

Casos de prueba obligatorios:
1. 2026-05-25 (Memorial Day) debe quedar excluida (FAIL o ABSTAIN con motivo explícito).
2. 2026-06-15 de NQ 06-26 no debe pasar (FAIL por post-roll y volumen al 26.9% de la mediana).
3. 2026-06-16 de NQ 06-26 no debe pasar (FAIL por post-roll y volumen al 13.7% de la mediana).
4. Las sesiones 2026-06-03 -> 2026-06-11 deben pasar todas (PASS, 113% a 192% del volumen mediano).
5. Fin de semana (2026-06-06) debe ser FAIL.
6. Fecha fuera de calendario debe resultar en ABSTAIN (nunca PASS automático).
"""
import pytest
from edgelab.data.nq_session_gate import NQSessionEligibilityGateV1

MEDIAN_NQ0626 = 549_918.0


@pytest.fixture
def gate():
    return NQSessionEligibilityGateV1()


def test_regression_20260525_memorial_day(gate):
    # Memorial Day: EARLY_CLOSE en CME, volumen 125,160 (22.8% de mediana)
    res = gate.evaluate_session(
        trade_date=20260525,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=125_160,
        tick_count=113_739,
        roll_state="PRE_ROLL",
        completeness="COMPLETE",
    )
    assert res.eligibility in ("FAIL", "ABSTAIN")
    assert res.exclusion_reason is not None
    assert "EARLY_CLOSE" in res.exclusion_reason or "Memorial Day" in res.exclusion_reason


def test_regression_20260615_post_roll_illiquid(gate):
    # 2026-06-15: NQ 06-26 ya post-roll, volumen 147,791 (26.9% de mediana)
    res = gate.evaluate_session(
        trade_date=20260615,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=147_791,
        tick_count=130_671,
        roll_state="POST_ROLL",
        completeness="COMPLETE",
    )
    assert res.eligibility == "FAIL"
    assert res.exclusion_reason in (
        "POST_ROLL_CONTRACT_EXPIRED_OR_ILLIQUID",
        "LOW_VOLUME_RATIO_0.269_LT_0.5",
    ) or "POST_ROLL" in res.exclusion_reason


def test_regression_20260616_post_roll_illiquid(gate):
    # 2026-06-16: NQ 06-26 ya post-roll, volumen 75,069 (13.7% de mediana)
    res = gate.evaluate_session(
        trade_date=20260616,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=75_069,
        tick_count=66_393,
        roll_state="POST_ROLL",
        completeness="COMPLETE",
    )
    assert res.eligibility == "FAIL"
    assert "POST_ROLL" in res.exclusion_reason or "LOW_VOLUME" in res.exclusion_reason


@pytest.mark.parametrize("t_date, vol, ticks", [
    (20260603, 621_284, 572_504),
    (20260604, 668_884, 624_032),
    (20260605, 1_001_875, 913_751),
    (20260608, 822_988, 763_008),
    (20260609, 1_057_079, 979_278),
    (20260610, 745_136, 687_811),
    (20260611, 689_278, 623_828),
])
def test_regression_20260603_to_20260611_all_pass(gate, t_date, vol, ticks):
    # Sesiones canónicas de alta liquidez pre-roll de NQ 06-26
    res = gate.evaluate_session(
        trade_date=t_date,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=vol,
        tick_count=ticks,
        roll_state="PRE_ROLL",
        completeness="COMPLETE",
    )
    assert res.eligibility == "PASS"
    assert res.exclusion_reason is None
    assert res.ratio_vs_median >= 1.0


def test_weekend_session_fails(gate):
    res = gate.evaluate_session(
        trade_date=20260606,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=0,
        tick_count=0,
    )
    assert res.eligibility == "FAIL"
    assert "MARKET_CLOSED" in res.exclusion_reason


def test_unknown_date_abstains_never_pass(gate):
    res = gate.evaluate_session(
        trade_date=20990101,
        contract="NQ 06-26",
        contract_median_volume=MEDIAN_NQ0626,
        volume=500_000,
        tick_count=400_000,
    )
    assert res.eligibility == "ABSTAIN"
    assert res.exclusion_reason == "TRADE_DATE_NOT_IN_CME_CALENDAR"
