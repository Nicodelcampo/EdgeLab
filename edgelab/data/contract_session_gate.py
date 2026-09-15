"""CONTRACT_SESSION_ELIGIBILITY_GATE_V2 - Universal Causal Session Eligibility Gate.

Evaluates trade session eligibility across all asset classes (Equity Index, FX, Metals, Rates, Crypto)
in a strictly causal, target-free manner.

Architectural Guarantees:
1. Strict Causal Separation:
   - contract_selection_D: determined exclusively by volume leader in session D-1.
   - capture_quality_D: post-session diagnostic of data integrity for session D.
   - eligible_for_research_D: target-free filtering for downstream studies.
2. Fail-Closed Default:
   - completeness defaults strictly to UNKNOWN (requires explicit verified capture evidence to PASS).
3. CME Maintenance Window Exclusion:
   - Ticks between 16:00:00 and 16:59:59.999 CT are identified, segregated, and excluded from regular session volume.
4. Portable Root-Relative Paths:
   - Default calendars are located dynamically relative to the repository root.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

# Dynamic repository-relative path resolution
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EQUITY_INDEX_CALENDAR = (
    REPO_ROOT
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
    maintenance_tick_count: int = 0
    maintenance_volume: float = 0.0

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
    def is_maintenance_window_ct(hour: int, minute: int = 0) -> bool:
        """CME daily maintenance halt is 16:00 to 17:00 CT (Monday-Thursday)."""
        return 16 <= hour < 17

    @staticmethod
    def aggregate_session_ticks(
        ts_utc_ns: Sequence[int],
        volume: Sequence[int | float],
    ) -> dict[str, Any]:
        """Classify and aggregate ticks, excluding CME daily maintenance (16:00-17:00 CT)."""
        import pandas as pd
        ts_series = pd.to_datetime(list(ts_utc_ns), utc=True).tz_convert("America/Chicago")
        is_maint = (ts_series.hour == 16)

        reg_ticks = int((~is_maint).sum())
        maint_ticks = int(is_maint.sum())

        vol_arr = pd.Series(list(volume))
        reg_vol = float(vol_arr[~is_maint].sum()) if reg_ticks > 0 else 0.0
        maint_vol = float(vol_arr[is_maint].sum()) if maint_ticks > 0 else 0.0

        reg_ts = [ts for ts, m in zip(ts_utc_ns, is_maint) if not m]
        first_reg_ts = reg_ts[0] if reg_ts else None
        last_reg_ts = reg_ts[-1] if reg_ts else None

        return {
            "regular_volume": reg_vol,
            "regular_tick_count": reg_ticks,
            "maintenance_volume": maint_vol,
            "maintenance_tick_count": maint_ticks,
            "first_regular_ts_utc": first_reg_ts,
            "last_regular_ts_utc": last_reg_ts,
        }

    def evaluate_session_from_ticks(
        self,
        root: str,
        trade_date: int | date | str,
        contract: str,
        contract_median_volume: float,
        ts_utc_ns: Sequence[int],
        volume: Sequence[int | float],
        roll_state: str = "PRE_ROLL",
        completeness: str = "UNKNOWN",
    ) -> SessionEligibilityResultV2:
        """Evaluate session after filtering out maintenance window ticks deterministically."""
        agg = self.aggregate_session_ticks(ts_utc_ns, volume)
        return self.evaluate_session(
            root=root,
            trade_date=trade_date,
            contract=contract,
            contract_median_volume=contract_median_volume,
            volume=agg["regular_volume"],
            tick_count=agg["regular_tick_count"],
            roll_state=roll_state,
            first_ts_utc=agg["first_regular_ts_utc"],
            last_ts_utc=agg["last_regular_ts_utc"],
            completeness=completeness,
            maintenance_tick_count=agg["maintenance_tick_count"],
            maintenance_volume=agg["maintenance_volume"],
        )

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
        completeness: str = "UNKNOWN",
        maintenance_tick_count: int = 0,
        maintenance_volume: float = 0.0,
    ) -> SessionEligibilityResultV2:
        """Evaluate session eligibility in a fail-closed manner.
        
        completeness defaults to UNKNOWN. If not explicitly verified, returns ABSTAIN.
        """
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
                maintenance_tick_count=maintenance_tick_count,
                maintenance_volume=maintenance_volume,
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
            maintenance_tick_count=maintenance_tick_count,
            maintenance_volume=maintenance_volume,
        )
