"""NQ_SESSION_ELIGIBILITY_GATE_V1 - Compuerta Causal Reutilizable de Sesiones NQ.

Opera EXCLUSIVAMENTE con datos target-free. Debe ejecutarse antes de cualquier
runner de investigación sobre NQ para evitar sesgos por días feriados, sesiones truncadas
o contratos post-roll ilíquidos.

Estados permitidos:
- PASS: Sesión operable con calendario normal, volumen y ticks suficientes, pre-roll y datos completos.
- FAIL: Sesión excluida (feriado, fin de semana, ilíquida, post-roll o truncada).
- ABSTAIN: Sesión no certificable por falta de evidencia de calendario o completitud.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

# Repo-relative default: an absolute workstation path made every CI runner
# resolve zero sessions and forced ABSTAIN on the whole regression suite.
DEFAULT_CALENDAR_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "research"
    / "cme_equity_index_calendar_20260902"
    / "cme_equity_index_session_calendar_v1.json"
)

MIN_VOLUME_RATIO_DEFAULT = 0.50
MIN_TICKS_DEFAULT = 50_000


@dataclass(frozen=True)
class SessionEligibilityResult:
    trade_date: int
    contract: str
    calendar_valid: bool
    session_class: str
    holiday_name: str | None
    has_data: bool
    first_ts_utc: int | None
    last_ts_utc: int | None
    tick_count: int
    volume: float
    ratio_vs_median: float
    roll_state: str
    completeness: str
    eligibility: str
    exclusion_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NQSessionEligibilityGateV1:
    def __init__(
        self,
        calendar_path: Path | str = DEFAULT_CALENDAR_PATH,
        min_volume_ratio: float = MIN_VOLUME_RATIO_DEFAULT,
        min_ticks: int = MIN_TICKS_DEFAULT,
    ) -> None:
        self.calendar_path = Path(calendar_path)
        self.min_volume_ratio = min_volume_ratio
        self.min_ticks = min_ticks
        self._sessions_by_date: dict[int, dict[str, Any]] = {}
        self._load_calendar()

    def _load_calendar(self) -> None:
        if not self.calendar_path.exists():
            return
        with open(self.calendar_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("sessions", []):
            td = int(s["trade_date"])
            self._sessions_by_date[td] = s

    def evaluate_session(
        self,
        trade_date: int | date | str,
        contract: str,
        contract_median_volume: float,
        volume: float,
        tick_count: int,
        roll_state: str = "PRE_ROLL",
        first_ts_utc: int | None = None,
        last_ts_utc: int | None = None,
        completeness: str = "COMPLETE",
    ) -> SessionEligibilityResult:
        if isinstance(trade_date, date):
            td_int = trade_date.year * 10000 + trade_date.month * 100 + trade_date.day
        elif isinstance(trade_date, str):
            clean = trade_date.replace("-", "")
            td_int = int(clean)
        else:
            td_int = int(trade_date)

        cal_session = self._sessions_by_date.get(td_int)
        if cal_session is None:
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=False,
                session_class="UNKNOWN",
                holiday_name=None,
                has_data=tick_count > 0,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=(volume / contract_median_volume) if contract_median_volume > 0 else 0.0,
                roll_state=roll_state,
                completeness="UNKNOWN",
                eligibility="ABSTAIN",
                exclusion_reason="TRADE_DATE_NOT_IN_CME_CALENDAR",
            )

        session_class = str(cal_session.get("session_class", "UNKNOWN"))
        holiday_name = cal_session.get("holiday_name")
        has_data = tick_count > 0
        ratio_vs_median = (volume / contract_median_volume) if contract_median_volume > 0 else 0.0

        if session_class == "CLOSED":
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason=f"MARKET_CLOSED_{holiday_name or 'SCHEDULED'}",
            )

        if session_class == "EARLY_CLOSE":
            reason = f"EARLY_CLOSE_HOLIDAY_{holiday_name or 'UNSPECIFIED'}"
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason=reason,
            )

        if not has_data or tick_count < self.min_ticks:
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason=f"INSUFFICIENT_TICKS_{tick_count}_LT_{self.min_ticks}",
            )

        if roll_state.upper() == "POST_ROLL":
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason="POST_ROLL_CONTRACT_EXPIRED_OR_ILLIQUID",
            )

        if ratio_vs_median < self.min_volume_ratio:
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason=f"LOW_VOLUME_RATIO_{ratio_vs_median:.3f}_LT_{self.min_volume_ratio}",
            )

        if completeness == "INCOMPLETE":
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="FAIL",
                exclusion_reason="INCOMPLETE_SOURCE_CAPTURE",
            )
        if completeness == "UNKNOWN":
            return SessionEligibilityResult(
                trade_date=td_int,
                contract=contract,
                calendar_valid=True,
                session_class=session_class,
                holiday_name=holiday_name,
                has_data=has_data,
                first_ts_utc=first_ts_utc,
                last_ts_utc=last_ts_utc,
                tick_count=tick_count,
                volume=volume,
                ratio_vs_median=ratio_vs_median,
                roll_state=roll_state,
                completeness=completeness,
                eligibility="ABSTAIN",
                exclusion_reason="SOURCE_CAPTURE_COMPLETENESS_UNKNOWN",
            )

        return SessionEligibilityResult(
            trade_date=td_int,
            contract=contract,
            calendar_valid=True,
            session_class=session_class,
            holiday_name=holiday_name,
            has_data=has_data,
            first_ts_utc=first_ts_utc,
            last_ts_utc=last_ts_utc,
            tick_count=tick_count,
            volume=volume,
            ratio_vs_median=ratio_vs_median,
            roll_state=roll_state,
            completeness=completeness,
            eligibility="PASS",
            exclusion_reason=None,
        )
