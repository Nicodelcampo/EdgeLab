"""CONTRACT_SESSION_ELIGIBILITY_GATE_V2 - Universal Causal Session Eligibility Gate.

Evaluates trade session eligibility across all asset classes (Equity Index, FX, Metals, Rates, Crypto)
in a strictly causal, target-free manner.

Eligibility states:
- PASS: Session is fully eligible (approved official calendar, sufficient liquidity/volume, pre-roll, complete source).
- FAIL: Session is excluded (scheduled market closure, holiday early close, low volume/ticks, post-roll).
- ABSTAIN: Session cannot be certified (missing official calendar evidence, unknown/incomplete source capture).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_EQUITY_INDEX_CALENDAR = (
    Path("E:/EdgeLab")
    / "docs"
    / "research"
    / "cme_equity_index_calendar_20260902"
    / "cme_equity_index_session_calendar_v1.json"
)

# Product root classifications
EQUITY_INDEX_ROOTS = {"ES", "MES", "NQ", "MNQ", "YM"}
FX_ROOTS = {"6B", "6E", "6J"}
METALS_ROOTS = {"GC"}
RATES_ROOTS = {"ZB"}
CRYPTO_ROOTS = {"MBT"}

# Default thresholds by asset group
DEFAULT_MIN_VOLUME_RATIOS: dict[str, float] = {
    "EQUITY_INDEX": 0.50,
    "FX": 0.40,
    "METALS": 0.40,
    "RATES": 0.40,
    "CRYPTO": 0.30,
}

DEFAULT_MIN_TICKS: dict[str, int] = {
    "NQ": 50_000,
    "MNQ": 50_000,
    "ES": 50_000,
    "MES": 50_000,
    "YM": 10_000,
    "6E": 10_000,
    "6B": 5_000,
    "6J": 5_000,
    "GC": 10_000,
    "ZB": 5_000,
    "MBT": 1_000,
}


@dataclass(frozen=True)
class SessionEligibilityResultV2:
    root: str
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


class ContractSessionEligibilityGateV2:
    """Universal causal session gate for all futures products."""

    def __init__(
        self,
        calendars: Mapping[str, Path | str] | None = None,
        min_volume_ratios: Mapping[str, float] | None = None,
        min_ticks: Mapping[str, int] | None = None,
    ) -> None:
        self._calendars_by_group: dict[str, dict[int, dict[str, Any]]] = {}
        self._min_volume_ratios = dict(DEFAULT_MIN_VOLUME_RATIOS)
        if min_volume_ratios:
            self._min_volume_ratios.update(min_volume_ratios)

        self._min_ticks = dict(DEFAULT_MIN_TICKS)
        if min_ticks:
            self._min_ticks.update(min_ticks)

        # Load calendars
        cal_map = dict(calendars or {})
        if "EQUITY_INDEX" not in cal_map and DEFAULT_EQUITY_INDEX_CALENDAR.exists():
            cal_map["EQUITY_INDEX"] = DEFAULT_EQUITY_INDEX_CALENDAR

        for group, path in cal_map.items():
            self._load_calendar(group, Path(path))

    def _load_calendar(self, group: str, path: Path) -> None:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sessions: dict[int, dict[str, Any]] = {}
        for s in data.get("sessions", []):
            td = int(s["trade_date"])
            sessions[td] = s
        self._calendars_by_group[group] = sessions

    @staticmethod
    def get_asset_group(root: str) -> str:
        r = root.upper().strip()
        if r in EQUITY_INDEX_ROOTS:
            return "EQUITY_INDEX"
        if r in FX_ROOTS:
            return "FX"
        if r in METALS_ROOTS:
            return "METALS"
        if r in RATES_ROOTS:
            return "RATES"
        if r in CRYPTO_ROOTS:
            return "CRYPTO"
        return "UNKNOWN"

    def get_min_volume_ratio(self, root: str) -> float:
        group = self.get_asset_group(root)
        return self._min_volume_ratios.get(group, 0.50)

    def get_min_ticks(self, root: str) -> int:
        r = root.upper().strip()
        return self._min_ticks.get(r, 10_000)

    @staticmethod
    def is_maintenance_window_ct(hour: int, minute: int) -> bool:
        """CME daily maintenance halt is 16:00 to 17:00 CT (Monday-Thursday)."""
        return 16 <= hour < 17

    def evaluate_session(
        self,
        root: str,
        trade_date: int | date | str,
        contract: str,
        contract_median_volume: float,
        volume: float,
        tick_count: int,
        roll_state: str = "PRE_ROLL",
        first_ts_utc: int | None = None,
        last_ts_utc: int | None = None,
        completeness: str = "COMPLETE",
    ) -> SessionEligibilityResultV2:
        clean_root = str(root).upper().strip()
        group = self.get_asset_group(clean_root)

        if isinstance(trade_date, date):
            td_int = trade_date.year * 10000 + trade_date.month * 100 + trade_date.day
        elif isinstance(trade_date, str):
            clean = trade_date.replace("-", "")
            td_int = int(clean)
        else:
            td_int = int(trade_date)

        cal_group = self._calendars_by_group.get(group)
        if cal_group is None:
            return SessionEligibilityResultV2(
                root=clean_root,
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
                completeness=completeness,
                eligibility="ABSTAIN",
                exclusion_reason=f"NO_OFFICIAL_CALENDAR_EVIDENCE_FOR_{group}",
            )

        cal_session = cal_group.get(td_int)
        if cal_session is None:
            return SessionEligibilityResultV2(
                root=clean_root,
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
                exclusion_reason=f"TRADE_DATE_NOT_IN_{group}_CALENDAR",
            )

        session_class = str(cal_session.get("session_class", "UNKNOWN"))
        holiday_name = cal_session.get("holiday_name")
        has_data = tick_count > 0
        ratio_vs_median = (volume / contract_median_volume) if contract_median_volume > 0 else 0.0

        if session_class == "CLOSED":
            return SessionEligibilityResultV2(
                root=clean_root,
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
            return SessionEligibilityResultV2(
                root=clean_root,
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
                exclusion_reason=f"EARLY_CLOSE_HOLIDAY_{holiday_name or 'UNSPECIFIED'}",
            )

        min_ticks = self.get_min_ticks(clean_root)
        if not has_data or tick_count < min_ticks:
            return SessionEligibilityResultV2(
                root=clean_root,
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
                exclusion_reason=f"INSUFFICIENT_TICKS_{tick_count}_LT_{min_ticks}",
            )

        if roll_state.upper() == "POST_ROLL":
            return SessionEligibilityResultV2(
                root=clean_root,
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

        min_ratio = self.get_min_volume_ratio(clean_root)
        if ratio_vs_median < min_ratio:
            return SessionEligibilityResultV2(
                root=clean_root,
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
                exclusion_reason=f"LOW_VOLUME_RATIO_{ratio_vs_median:.3f}_LT_{min_ratio:.3f}",
            )

        if completeness == "INCOMPLETE":
            return SessionEligibilityResultV2(
                root=clean_root,
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
            return SessionEligibilityResultV2(
                root=clean_root,
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

        return SessionEligibilityResultV2(
            root=clean_root,
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
