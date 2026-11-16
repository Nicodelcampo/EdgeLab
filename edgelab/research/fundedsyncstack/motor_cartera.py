"""Portfolio state machine, sizing tables, risk gates, and chronological simulator for FUNDEDSYNCSTACK.

Faithfully translates the portfolio architecture extracted from ``FUNDEDSYNCSTACK5.dll`` IL:
- ``PortfolioConfig``: exact defaults from ``OnStateChange(State.SetDefaults)``.
- ``RollingValues``: circular statistics buffer with sample standard deviation (``count - 1``).
- ``ModuleState``: per-sleeve runtime, position, order, cooldown, and virtual ledger state.
- Sizing tables & rules: ``TryGetOptimizedEvaluationQuantity``, ``FastPass50KBaseQuantity``,
  ``SmoothBaseQuantity``, ``NormalLucidQuantity``, ``SelectedStageTier``, ``ProfileBaseQuantity``,
  ``NewModuleLucidQuantity``, ``SelectedFtmStageQuantity``, ``AddedExecutionQuantity``,
  ``ActiveLucidMicroContractCap``, and ``RampartQuantity``.
- Portfolio gates: ``StrategySelectionAllows``, ``IsBundleA`` / ``IsBundleB``,
  ``HalfDrawdownEntryRotation`` (3-of-5 rotation across ``S, P, C, R, E`` in Minimum Participation),
  ``ConsumeLossCooldown`` / ``ConfiguredLossCooldown``, ``IsDailyFuturesCloseBlocked``
  (``DAILY_FUTURES_CLOSE``), restricted news window ``[-before, +after]`` minutes CT
  (``restricted-news-days.csv``), ``PortfolioDailyLossLimit`` (``PORT_RISK``), and
  side-by-side reconciliation of Virtual Ledger vs Netting Broker execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
from enum import IntEnum
import inspect
import math
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    from .contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_MNQ,
        POINT_VALUE_NQ,
        TRADE_COLUMNS,
        TradeRecord,
        round_tick,
        trades_to_df,
    )
except ImportError:  # pragma: no cover - direct import fallback
    from contracts import (
        BarSeries,
        MultiSeriesContext,
        POINT_VALUE_MNQ,
        POINT_VALUE_NQ,
        TRADE_COLUMNS,
        TradeRecord,
        round_tick,
        trades_to_df,
    )

_TZ_CT = ZoneInfo("America/Chicago")
_TZ_UTC = ZoneInfo("UTC")
_NS_PER_MIN: int = 60 * 1_000_000_000
_INT32_MAX: int = 2_147_483_647

# Exact module dispatch order verified in OnBarUpdate & VirtualAggregateNet
TAGS_ALL: tuple[str, ...] = (
    "A1", "A20", "F", "S", "P", "C", "V", "O", "W", "N", "T", "R", "Z", "E", "Q",
)
BUNDLE_A_TAGS: frozenset[str] = frozenset({"A1", "S", "V", "W", "T", "Z", "E"})
BUNDLE_B_TAGS: frozenset[str] = frozenset({"A20", "F", "P", "C", "O", "R", "Q"})

# Exact BIP mapped to each module inside OnBarUpdate
MODULE_SIGNAL_BIP: dict[str, int] = {
    "A1": 1,
    "A20": 4,
    "F": 3,
    "S": 2,
    "P": 1,
    "C": 5,
    "V": 6,
    "O": 1,
    "W": 1,
    "N": 1,
    "T": 1,
    "R": 9,
    "Z": 1,
    "E": 10,
    "Q": 3,
}

HALF_DRAWDOWN_ROTATION_OFFSETS: dict[str, int] = {
    "S": 0,
    "P": 1,
    "C": 2,
    "R": 3,
    "E": 4,
}


class ExecMode(IntEnum):
    NQ = 0
    MNQ = 1


class SizingProfile(IntEnum):
    PropSmoothBalanced = 0
    LongTermPortfolio = 1
    Lucid25K = 2
    Lucid50K = 3
    Lucid100K = 4
    Lucid150K = 5
    Custom = 6
    Lucid25KFastEvaluation = 7
    Lucid25KHighestProbabilityEvaluation = 8
    Lucid50KFastEvaluation = 9
    Lucid50KHighestProbabilityEvaluation = 10
    Lucid150KFastEvaluation = 11
    Lucid150KHighestProbabilityEvaluation = 12
    PropFirm50KFastPass = 13
    MinimumParticipation = 14


class AccountStage(IntEnum):
    Evaluation = 0
    FundedBelowBuffer = 1
    FundedAboveBuffer = 2


class EvaluationSizingMode(IntEnum):
    Existing = 0
    Fast = 1
    HighestProbability = 2


class EntryTiming(IntEnum):
    MatchStandaloneNextSignalBar = 0
    ExecuteOnNextMinute = 1


class StrategySelection(IntEnum):
    AllStrategies = 0
    Absorb1Minute = 1
    Absorb20Minute = 2
    FabioOrb = 3
    Swas = 4
    NqPullback = 5
    CapstoneGap = 6
    VaultBreak = 7
    Overnight = 8
    VwapCross = 9
    NDayLong = 10
    FtmOrb = 11
    AtrPhase = 12
    ZetaTrendDay = 13
    EmaDivergence = 14
    Rampart5Minute = 15


class BundleSelection(IntEnum):
    BothBundles = 0
    BundleAOnly = 1
    BundleBOnly = 2


class ExecutionIntentKind(IntEnum):
    Entry = 0
    Exit = 1
    CancelEntry = 2


STRATEGY_SELECTION_TAG: dict[int, str] = {
    StrategySelection.Absorb1Minute: "A1",
    StrategySelection.Absorb20Minute: "A20",
    StrategySelection.FabioOrb: "F",
    StrategySelection.Swas: "S",
    StrategySelection.NqPullback: "P",
    StrategySelection.CapstoneGap: "C",
    StrategySelection.VaultBreak: "V",
    StrategySelection.Overnight: "O",
    StrategySelection.VwapCross: "W",
    StrategySelection.NDayLong: "N",
    StrategySelection.FtmOrb: "T",
    StrategySelection.AtrPhase: "R",
    StrategySelection.ZetaTrendDay: "Z",
    StrategySelection.EmaDivergence: "E",
    StrategySelection.Rampart5Minute: "Q",
}


# ---------------------------------------------------------------------------
# Sizing Tables verified verbatim from sizing_license_news_risk.txt & mod_Q.txt
# ---------------------------------------------------------------------------

_OPTIMIZED_EVAL_TABLES: dict[tuple[str, bool], dict[str, int]] = {
    # (account_tier_bucket, is_fast) -> {tag: mnq_qty}
    ("25K", True): {"F": 10, "O": 7, "T": 3},
    ("25K", False): {"P": 1, "C": 1, "T": 1, "E": 1, "R": 2, "Z": 3},
    ("50K", True): {"F": 6, "P": 2, "R": 2, "O": 9, "T": 7},
    ("50K", False): {"P": 3, "R": 3, "C": 2, "O": 2, "T": 2, "Z": 4},
    ("150K", True): {"O": 39, "T": 21, "Z": 31},
    ("150K", False): {"P": 8, "E": 8, "C": 7, "T": 6, "O": 5, "R": 5, "Z": 5},
}

_FAST_PASS_50K_BASE_TABLE: dict[str, int] = {
    "A20": 2, "F": 2, "V": 2, "S": 1, "P": 1, "C": 1, "O": 3,
}

_SMOOTH_BASE_TABLE: dict[str, int] = {
    "A1": 1, "A20": 2, "F": 1, "S": 1, "P": 1, "C": 1, "W": 1, "V": 3, "O": 2,
}

_LONG_TERM_PORTFOLIO_TABLE: dict[str, int] = {
    "A1": 2, "A20": 1, "F": 1, "S": 1, "P": 1, "C": 1, "V": 7, "O": 5, "W": 2, "N": 9,
}

_NORMAL_LUCID_TABLES: dict[int, dict[str, int]] = {
    SizingProfile.MinimumParticipation: {"A20": 1, "F": 1, "S": 1, "P": 1, "C": 1, "V": 1, "O": 1},
    SizingProfile.Lucid25K: {"A20": 2, "F": 2, "V": 2, "S": 1, "P": 1, "C": 1, "O": 3},
    SizingProfile.Lucid50K: {"A1": 1, "S": 1, "P": 1, "W": 1, "F": 3, "C": 3, "V": 3, "A20": 5, "O": 7},
    SizingProfile.Lucid100K: {"A1": 1, "W": 1, "S": 2, "P": 2, "C": 4, "F": 5, "V": 5, "A20": 7, "O": 10},
    SizingProfile.Lucid150K: {"A1": 2, "W": 2, "S": 3, "P": 4, "C": 8, "F": 10, "V": 10, "A20": 14, "O": 20},
}

_NEW_MODULE_LUCID_TUPLES: dict[str, tuple[int, int, int, int, str]] = {
    "R": (1, 2, 3, 6, "BaseQtyAtrPhase"),
    "Z": (2, 4, 6, 12, "BaseQtyZeta"),
    "E": (1, 1, 2, 3, "BaseQtyEmaDivergence"),
}


@dataclass
class PortfolioConfig:
    """Configuration mirroring all default NinjaScript properties in ``FUNDEDSYNCSTACK.OnStateChange(SetDefaults)``."""

    # Runtime / Execution / Safety / News
    FreshLiveStart: bool = True
    FundedSyncLicenseKey: str = ""
    MinimalLiveSafety: bool = True
    FlattenBeforeDailyFuturesClose: bool = True
    DailyFuturesFlattenTimeCentral: int = 154400
    DailyFuturesResumeTimeCentral: int = 170100
    FundedSyncStackBlockRestrictedNewsDays: bool = True
    FundedSyncStackRestrictedNewsCsvPath: str = r"FundedSync\restricted-news-days.csv"
    FundedSyncStackMinutesBeforeNews: int = 5
    FundedSyncStackMinutesAfterNews: int = 5
    ExecMode: int = ExecMode.MNQ
    MnqContract: str = "MNQ 12-26"
    SizingProfile: int = SizingProfile.Lucid50K
    LucidAccountStage: int = AccountStage.Evaluation
    LucidEvaluationSizing: int = EvaluationSizingMode.Existing

    # Stage tier multipliers & FTM overrides
    Lucid25KEvaluationTier: int = 1
    Lucid25KBelowBufferTier: int = 1
    Lucid25KAboveBufferTier: int = 1
    Lucid50KEvaluationTier: int = 2
    Lucid50KBelowBufferTier: int = 2
    Lucid50KAboveBufferTier: int = 2
    Lucid100KEvaluationTier: int = 3
    Lucid100KBelowBufferTier: int = 3
    Lucid100KAboveBufferTier: int = 3
    Lucid150KEvaluationTier: int = 6
    Lucid150KBelowBufferTier: int = 5
    Lucid150KAboveBufferTier: int = 6

    Ftm25KEvaluationQty: int = 1
    Ftm25KBelowQty: int = 1
    Ftm25KAboveQty: int = 1
    Ftm50KEvaluationQty: int = 3
    Ftm50KBelowQty: int = 3
    Ftm50KAboveQty: int = 3
    Ftm100KEvaluationQty: int = 4
    Ftm100KBelowQty: int = 4
    Ftm100KAboveQty: int = 4
    Ftm150KEvaluationQty: int = 8
    Ftm150KBelowQty: int = 8
    Ftm150KAboveQty: int = 8

    EntryTiming: int = EntryTiming.ExecuteOnNextMinute
    SizeLevel: int = 1
    StrategySelection: int = StrategySelection.AllStrategies
    BundleGroups: int = BundleSelection.BothBundles

    # Custom / Base Quantities
    BaseQtyAbsorb1m: int = 1
    BaseQtyAbsorb20m: int = 2
    BaseQtyFabio: int = 1
    BaseQtySwas: int = 1
    BaseQtyPullback: int = 1
    BaseQtyCapstone: int = 1
    BaseQtyVault: int = 3
    BaseQtyOvernight: int = 2
    BaseQtyVwapCross: int = 1
    BaseQtyNDay: int = 0
    BaseQtyFtm: int = 15
    BaseQtyAtrPhase: int = 1
    BaseQtyZeta: int = 2
    BaseQtyEmaDivergence: int = 1
    BaseRampartRiskUsd: float = 500.0
    BaseRampartMaxContracts: int = 60

    # Module Enable Toggles
    EnableAbsorb1m: bool = True
    EnableAbsorb20m: bool = True
    EnableFabio: bool = True
    EnableSwas: bool = True
    EnablePullback: bool = True
    EnableCapstone: bool = True
    EnableVault: bool = True
    EnableOvernight: bool = True
    EnableVwapCross: bool = True
    EnableNDay: bool = False
    EnableFtm: bool = False
    EnableAtrPhase: bool = True
    EnableZeta: bool = True
    EnableEmaDivergence: bool = True
    EnableRampart: bool = False

    # Rampart tier parameters
    Rampart25KRiskUsd: float = 100.0
    Rampart25KMaxContracts: int = 14
    Rampart50KRiskUsd: float = 200.0
    Rampart50KMaxContracts: int = 28
    Rampart100KRiskUsd: float = 350.0
    Rampart100KMaxContracts: int = 42
    Rampart150KRiskUsd: float = 700.0
    Rampart150KMaxContracts: int = 84

    CustomStockHoursTemplate: str = "US STOCK"
    ConvertAddedMnqSizingInNqMode: bool = False
    VirtualRoundTurnCommission: float = 4.36
    PrintVirtualLedger: bool = True
    PortfolioDailyLossLimit: float = 0.0
    FlattenOnPortfolioDailyLoss: bool = False
    PrintPortfolioRiskLedger: bool = True

    # Module-specific NinjaScript properties (exact SetDefaults values)
    Ab_VpLength: int = 10
    Ab_VpResolution: int = 24
    Ab_AbsorbVolMult: float = 2.5
    Ab_AbsorbPriceThresh: float = 1.9
    Ab_DeltaLookback: int = 5
    Ab_UseVWAP: bool = True
    Ab_VwapBand: float = 0.5
    Ab_MaxDailyLosses: int = 3
    Ab_OrbMinutes: int = 30
    Ab_UseORB: bool = True
    Ab_UseRolloverFilter: bool = True
    Ab_RolloverDaysBefore: int = 10
    Ab_RolloverDaysAfter: int = 1
    Ab_UseVolatilityFilter: bool = True
    Ab_VolBaselineLookback: int = 100
    Ab_VolRegimeMultiplier: float = 2.9
    Ab_UseHardStop: bool = True
    Ab_HardStopATRMult: float = 1.5
    Ab_FlattenAtSessionEnd: bool = True
    Ab_SessionStartHour: int = 5
    Ab_SessionStartMinute: int = 30
    Ab_SessionEndHour: int = 15
    Ab_SessionEndMinute: int = 0
    A1_STPeriod: int = 4
    A1_STMult: float = 2.7
    A20_STPeriod: int = 7
    A20_STMult: float = 2.0
    A1_AllowLongs: bool = True
    A1_AllowShorts: bool = True
    A20_AllowLongs: bool = False
    A20_AllowShorts: bool = True
    A1_UseEarlyEntryBlock: bool = True
    A1_BlockStartHour: int = 5
    A1_BlockStartMinute: int = 30
    A1_BlockEndHour: int = 6
    A1_BlockEndMinute: int = 0
    A20_BlockMondayEntries: bool = True
    V_BlockEntryHourEnabled: bool = True
    V_BlockedEntryHour: int = 9
    S_BlockLongEntryHourEnabled: bool = True
    S_BlockedLongEntryHour: int = 7
    S_BlockShortEntryHourEnabled: bool = True
    S_BlockedShortEntryHour: int = 13
    Ab_RequireSuperTrendEntryAlignment: bool = False
    A1_LossCooldownBars: int = 14
    A20_LossCooldownBars: int = 0

    F_StartH: int = 8
    F_StartM: int = 30
    F_DurMin: int = 30
    F_EndH: int = 14
    F_EndM: int = 0
    F_TPRR: float = 1.0
    F_DeltaThreshold: int = 200
    F_UseCumDelta: bool = False
    F_CumDeltaThreshold: int = 500
    F_DisableDeltaFilter: bool = False
    F_MaxInitialRiskATR: float = 0.0
    F_MaxInitialRiskPoints: float = 125.0
    F_LossCooldownBars: int = 0

    Q_RangeStartHour: int = 9
    Q_RangeStartMinute: int = 15
    Q_RangeEndHour: int = 9
    Q_RangeEndMinute: int = 50
    Q_BreakMarginTicks: int = 6
    Q_StopBufferTicks: int = 1
    Q_RiskReward: float = 0.3
    Q_LastEntryHour: int = 12
    Q_LastEntryMinute: int = 0
    Q_ForceCloseHour: int = 16
    Q_ForceCloseMinute: int = 0
    Q_OneTradePerSide: bool = True
    Q_MinBarsBetweenTrades: int = 1

    S_AtrLength: int = 14
    S_UseTimeFilter: bool = True
    S_NyOpenHour: int = 9
    S_NyOpenMinute: int = 30
    S_PreBlockMin: int = 10
    S_PostBlockMin: int = 30
    S_UseEODClose: bool = True
    S_CloseHour: int = 15
    S_CloseMinute: int = 55
    S_STPeriod: int = 10
    S_STMult: float = 3.2
    S_UseHardStop: bool = False
    S_HardStopATRMult: float = 3.0
    S_UseADXFilter: bool = True
    S_ADXPeriod: int = 14
    S_ADXThreshold: float = 20.0
    S_UseVwapEmaBias: bool = True
    S_BiasEMAPeriod: int = 21
    S_UseRegimeFilter: bool = True
    S_RegimeATRLookback: int = 100
    S_RegimeATRMultiplier: float = 2.9
    S_AllowLongs: bool = True
    S_AllowShorts: bool = True
    S_RequireSuperTrendEntryAlignment: bool = False
    S_MinEmaSlopeATR: float = 0.05
    S_LossCooldownBars: int = 1

    P_UseVolatilitySizing: bool = True
    P_PositionSize: int = 1
    P_CapitalUsd: float = 500000.0
    P_RiskPercent: float = 2.0
    P_RiskFilterPercent: float = 2.0
    P_SlippageTicks: int = 1
    P_MaxContracts: int = 20
    P_MaxMarginPercent: float = 50.0
    P_MarginPerContractUsd: float = 0.0
    P_MarginRatePercent: float = 10.0
    P_TradeLongs: bool = True
    P_TradeShorts: bool = False
    P_MinimumRewardRisk: float = 0.0
    P_MaxStopPoints: float = 0.0
    P_RetestMode: int = 1
    P_StopMode: int = 1
    P_MaxTradesPerDay: int = 1
    P_StopSwingLength: int = 30
    P_TargetSwingLength: int = 5
    P_BufferMode: int = 2
    P_BufferAmount: float = 0.0
    P_OpeningRangeStart: int = 83000
    P_OpeningRangeEnd: int = 90000
    P_VwapStart: int = 83000
    P_VwapEnd: int = 170000
    P_EntryStart: int = 90000
    P_EntryEnd: int = 170000
    P_DayResetTime: int = 230000
    P_UseEndOfDayFlat: bool = False
    P_EndOfDayFlatTime: int = 155500

    C_StopLossAmount: float = 1500.0
    C_ProfitTargetAmount: float = 2500.0
    C_MinimumGapPoints: float = 2.0
    C_EnableLongEntries: bool = True
    C_EnableShortEntries: bool = False

    V_NoiseMultiplier: float = 0.4
    V_DailyAtrLength: int = 252
    V_EarliestEntryEastern: int = 94500
    V_LatestEntryEastern: int = 150000
    V_FlattenTimeEastern: int = 155000
    V_MaximumTradesPerDay: int = 3
    V_VwapExitBars: int = 2
    V_ProfitTargetUsdPerContract: float = 1400.0
    V_StopLossUsdPerContract: float = 2000.0

    O_MovingAverageLength: int = 20
    O_UseTrendFilter: bool = True
    O_EntryTimeCentral: int = 150000
    O_ExitTimeCentral: int = 83000
    O_UsePostMaintenanceEntry: bool = True
    O_PostMaintenanceEntryTimeCentral: int = 170100
    O_VolatilityLookback: int = 20
    O_TargetRiskUsd: float = 1500.0
    O_MinimumContracts: int = 1
    O_MaximumContracts: int = 50
    O_CapitalUsd: float = 100000.0
    O_MaximumMarginPercent: float = 50.0
    O_MarginPerContractUsd: float = 0.0
    O_MarginRatePercent: float = 10.0
    O_UseDownRthDayFilter: bool = False
    O_UseRisingMaSlopeFilter: bool = True
    O_MaSlopeLookback: int = 5
    O_UseRthRangeFilter: bool = True
    O_RangeAtrLength: int = 20
    O_MaximumRthRangeToAtr: float = 1.5
    O_AllowFridayEntries: bool = False

    W_VwapStartTimeCentral: int = 83000
    W_VwapEndTimeCentral: int = 150000
    W_InitialEntryBoundaryCentral: int = 83100
    W_UseLastEntryTimeFilter: bool = True
    W_LastEntryTimeCentral: int = 140000
    W_AllowReentries: bool = True
    W_UseVwapSlopeFilter: bool = False
    W_VwapSlopeLookbackBars: int = 20
    W_MinimumVwapSlopeTicks: float = 0.0
    W_UseVwapDistanceFilter: bool = False
    W_MinimumVwapDistanceTicks: float = 4.0
    W_UseConfirmationFilter: bool = False
    W_ConfirmationBars: int = 2
    W_UseCooldownFilter: bool = True
    W_CooldownBars: int = 5
    W_UsePriorRthRangeFilter: bool = False
    W_RthRangeLookbackSessions: int = 20
    W_MinimumPriorRangeRatio: float = 0.75
    W_MaximumPriorRangeRatio: float = 0.0

    N_NumDays: int = 5
    N_LastEntryTime: int = 154500
    N_FlattenTime: int = 160000
    N_TreatMarketableStopAsMarket: bool = True
    N_UseDailyEfficiencyFilter: bool = False
    N_EfficiencyLookbackDays: int = 10
    N_MinimumDailyEfficiency: float = 0.3
    N_UseRthVwapAcceptanceFilter: bool = True
    N_VwapSlopeLookbackMinutes: int = 15
    N_UseBreakoutAcceptanceFilter: bool = True
    N_AcceptanceBufferPoints: float = 4.0
    N_AcceptanceConfirmationBars: int = 2
    N_UseVolatilityScaledLossExit: bool = True
    N_MaximumLossPriorRangeFraction: float = 1.0
    N_UseDollarRiskGate: bool = False
    N_MaximumEstimatedLossUsd: float = 10000.0
    N_UseVolatilityPositionSizing: bool = False
    N_TargetRiskUsd: float = 3000.0
    N_MaximumContracts: int = 20
    N_UseFailedBreakoutExit: bool = True
    N_FailureBufferPoints: float = 0.0
    N_FailureConfirmationBars: int = 6
    N_UseChoppyHighVolatilityFilter: bool = False
    N_RegimeShortRangeLength: int = 5
    N_RegimeLongRangeLength: int = 20
    N_MinimumVolatilityExpansionRatio: float = 1.25
    N_MaximumRegimeEfficiency: float = 0.25

    # Simulator control options (non-NT8 extensions)
    scale_qty_from_config: bool = True
    execution_point_value: float | None = None
    missing_news_calendar_blocks: bool = True
    news_calendar_override: dict[int, list[int]] | None = None

    def apply_configure_clamp(self) -> "PortfolioConfig":
        """Mirror ``State.Configure`` UI safety clamping (forces ``EnableFtm=False``, ``EnableRampart=False``)."""
        allowed = {
            SizingProfile.Lucid25K,
            SizingProfile.Lucid50K,
            SizingProfile.Lucid100K,
            SizingProfile.Lucid150K,
            SizingProfile.PropFirm50KFastPass,
            SizingProfile.MinimumParticipation,
        }
        if int(self.SizingProfile) not in allowed:
            self.SizingProfile = int(SizingProfile.Lucid50K)
        self.EnableFtm = False
        self.EnableRampart = False
        return self


# ---------------------------------------------------------------------------
# RollingValues & ModuleState (exact IL structures)
# ---------------------------------------------------------------------------

class RollingValues:
    """Exact translation of ``FUNDEDSYNCSTACK+RollingValues`` circular buffer."""

    def __init__(self, size: int) -> None:
        capacity = max(1, int(size))
        self.values: np.ndarray = np.zeros(capacity, dtype=np.float64)
        self.count: int = 0
        self.next: int = 0

    @property
    def capacity(self) -> int:
        return int(len(self.values))

    def __len__(self) -> int:
        return self.count

    def push(self, value: float) -> None:
        self.values[self.next] = float(value)
        self.next = (self.next + 1) % len(self.values)
        if self.count < len(self.values):
            self.count += 1

    # Alias matching C# method name
    Push = push

    def __getitem__(self, bars_ago: int) -> float:
        if bars_ago < 0 or bars_ago >= self.count:
            return 0.0
        idx = (self.next - 1 - bars_ago) % len(self.values)
        return float(self.values[idx])

    def mean(self) -> float:
        if self.count <= 0:
            return 0.0
        return float(np.sum(self.values[: self.count]) / self.count)

    Mean = mean

    def standard_deviation(self) -> float:
        """Sample standard deviation (divides squared deviations by ``count - 1``; 0 if ``count < 2``)."""
        if self.count < 2:
            return 0.0
        slice_vals = self.values[: self.count]
        avg = float(np.sum(slice_vals) / self.count)
        var = float(np.sum((slice_vals - avg) ** 2) / (self.count - 1))
        return math.sqrt(max(0.0, var))

    StandardDeviation = standard_deviation


@dataclass
class ModuleState:
    """Exact translation of ``FUNDEDSYNCSTACK+ModuleState`` plus simulation position tracking."""

    tag: str
    net: int = 0
    pending_delta: int = 0
    expected_entry_quantity: int = 0
    entry_filled_quantity: int = 0
    average_entry_price: float = 0.0
    pending_stop: float = float("nan")
    pending_target: float = float("nan")
    pending_stop_distance: float = float("nan")
    pending_target_distance: float = float("nan")
    has_entry_order: bool = False
    has_exit_order: bool = False
    has_stop_order: bool = False
    has_target_order: bool = False
    oco: str = ""
    has_queued_entry: bool = False
    queued_minute_bars_remaining: int = 0
    queued_signed_quantity: int = 0
    queued_stop: float = float("nan")
    queued_target: float = float("nan")
    has_queued_exit: bool = False
    queued_exit_minute_bars_remaining: int = 0
    queued_exit_reason: str = ""
    daily_losses: int = 0
    virtual_entry_count: int = 0
    virtual_closed_trade_count: int = 0
    current_trade_profit: float = 0.0
    virtual_net_profit: float = 0.0
    pending_daily_losses: int = 0
    loss_cooldown_bars_remaining: int = 0
    entry_counted: bool = False
    deferred_exit_after_protection_cancel: bool = False
    deferred_exit_reason: str = ""
    protection_mutation_in_progress: bool = False
    protection_resync_requested: bool = False
    protection_emergency_exit_pending: bool = False
    protection_emergency_exit_attempts: int = 0
    protection_emergency_reason: str = ""
    has_execution_intent: bool = False
    entry_cancel_requested: bool = False
    close_settlement_pending: bool = False
    closed_trade_accounted: bool = False

    # Simulator trade bookkeeping metadata
    entry_time_utc: int = 0
    entry_name: str = ""
    stop_price: float = float("nan")
    target_price: float = float("nan")
    active_trade_uid: int | None = None
    last_exit_sig_idx: int = -1
    mae_usd: float = 0.0
    mfe_usd: float = 0.0
    bars_held: int = 0
    skipped_entries: int = 0

    @property
    def position(self) -> int:
        """Return ``+1`` (Long), ``-1`` (Short), or ``0`` (Flat), matching ``ModuleState.get_Position``."""
        if self.net > 0:
            return 1
        if self.net < 0:
            return -1
        return 0

    @property
    def can_enter(self) -> bool:
        """Exact translation of ``ModuleState.get_CanEnter()`` (all 13 state guards)."""
        return (
            self.net == 0
            and self.pending_delta == 0
            and not self.has_entry_order
            and not self.has_exit_order
            and not self.has_stop_order
            and not self.has_target_order
            and not self.has_queued_entry
            and not self.has_queued_exit
            and not self.has_execution_intent
            and not self.entry_cancel_requested
            and not self.deferred_exit_after_protection_cancel
            and not self.protection_emergency_exit_pending
            and not self.close_settlement_pending
        )

    def reset_unfilled_entry(self) -> None:
        """Mirror ``ResetUnfilledEntryState`` clearing pending/queued/unfilled entry flags."""
        self.pending_delta = 0
        self.expected_entry_quantity = 0
        self.entry_filled_quantity = 0
        self.pending_stop = float("nan")
        self.pending_target = float("nan")
        self.pending_stop_distance = float("nan")
        self.pending_target_distance = float("nan")
        self.has_entry_order = False
        self.has_queued_entry = False
        self.queued_minute_bars_remaining = 0
        self.queued_signed_quantity = 0
        self.queued_stop = float("nan")
        self.queued_target = float("nan")
        self.has_execution_intent = False
        self.entry_cancel_requested = False
        self.entry_counted = False


# ---------------------------------------------------------------------------
# Pure Bundle / Selection / Sizing / Cooldown / Rotation / Maintenance helpers
# ---------------------------------------------------------------------------

def is_bundle_a(tag: str) -> bool:
    """Return True if ``tag`` belongs to Bundle A (``{A1, S, V, W, T, Z, E}``)."""
    return tag in BUNDLE_A_TAGS


def is_bundle_b(tag: str) -> bool:
    """Return True if ``tag`` belongs to Bundle B (``{A20, F, P, C, O, R, Q}``). Note ``N`` is in neither."""
    return tag in BUNDLE_B_TAGS


_ENABLE_ATTR_BY_TAG: dict[str, str] = {
    "A1": "EnableAbsorb1m",
    "A20": "EnableAbsorb20m",
    "F": "EnableFabio",
    "S": "EnableSwas",
    "P": "EnablePullback",
    "C": "EnableCapstone",
    "V": "EnableVault",
    "O": "EnableOvernight",
    "W": "EnableVwapCross",
    "N": "EnableNDay",
    "T": "EnableFtm",
    "R": "EnableAtrPhase",
    "Z": "EnableZeta",
    "E": "EnableEmaDivergence",
    "Q": "EnableRampart",
}


def is_module_enabled(tag: str, config: PortfolioConfig) -> bool:
    attr = _ENABLE_ATTR_BY_TAG.get(tag)
    if attr is None:
        return False
    return bool(getattr(config, attr, False))


def strategy_selection_allows(tag: str, config: PortfolioConfig, *, check_enable_flag: bool = True) -> bool:
    """Exact translation of ``StrategySelectionAllows(tag)`` (+ optional module ``Enable*`` toggle check)."""
    if check_enable_flag and not is_module_enabled(tag, config):
        return False
    sel = int(config.StrategySelection)
    if sel != int(StrategySelection.AllStrategies):
        return STRATEGY_SELECTION_TAG.get(sel) == tag
    grp = int(config.BundleGroups)
    if grp == int(BundleSelection.BundleAOnly):
        return is_bundle_a(tag)
    if grp == int(BundleSelection.BundleBOnly):
        return is_bundle_b(tag)
    return True


def is_lucid_sizing_profile(profile: int) -> bool:
    p = int(profile)
    return p in {2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14}


def is_fast_pass_50k_profile(profile: int) -> bool:
    return int(profile) == int(SizingProfile.PropFirm50KFastPass)


def is_minimum_participation_profile(profile: int) -> bool:
    return int(profile) == int(SizingProfile.MinimumParticipation)


def is_explicit_optimized_evaluation_profile(profile: int) -> bool:
    return int(profile) in {7, 8, 9, 10, 11, 12}


def is_fast_optimized_evaluation_profile(profile: int) -> bool:
    return int(profile) in {7, 9, 11}


def is_optimized_25k_profile(profile: int) -> bool:
    return int(profile) in {2, 7, 8}


def is_optimized_50k_profile(profile: int) -> bool:
    return int(profile) in {3, 9, 10}


def is_optimized_150k_profile(profile: int) -> bool:
    return int(profile) in {5, 11, 12}


def uses_optimized_evaluation_layout(config: PortfolioConfig) -> bool:
    p = int(config.SizingProfile)
    if is_explicit_optimized_evaluation_profile(p):
        return True
    return (
        int(config.LucidAccountStage) == int(AccountStage.Evaluation)
        and int(config.LucidEvaluationSizing) != int(EvaluationSizingMode.Existing)
        and p in {int(SizingProfile.Lucid25K), int(SizingProfile.Lucid50K), int(SizingProfile.Lucid150K)}
    )


def active_size_level(config: PortfolioConfig) -> int:
    return 1 if is_lucid_sizing_profile(config.SizingProfile) else int(config.SizeLevel)


def selected_stage_tier(stage: int, evaluation_tier: int, below_tier: int, above_tier: int) -> int:
    s = int(stage)
    if s == int(AccountStage.FundedBelowBuffer):
        return max(1, int(below_tier))
    if s == int(AccountStage.FundedAboveBuffer):
        return max(1, int(above_tier))
    return max(1, int(evaluation_tier))


def selected_ftm_stage_quantity(stage: int, evaluation_qty: int, below_qty: int, above_qty: int) -> int:
    s = int(stage)
    if s == int(AccountStage.FundedBelowBuffer):
        return max(0, int(below_qty))
    if s == int(AccountStage.FundedAboveBuffer):
        return max(0, int(above_qty))
    return max(0, int(evaluation_qty))


def active_lucid_tier(config: PortfolioConfig) -> int:
    p = int(config.SizingProfile)
    s = int(config.LucidAccountStage)
    if p == int(SizingProfile.Lucid25K):
        return selected_stage_tier(s, config.Lucid25KEvaluationTier, config.Lucid25KBelowBufferTier, config.Lucid25KAboveBufferTier)
    if p == int(SizingProfile.Lucid50K):
        return selected_stage_tier(s, config.Lucid50KEvaluationTier, config.Lucid50KBelowBufferTier, config.Lucid50KAboveBufferTier)
    if p == int(SizingProfile.Lucid100K):
        return selected_stage_tier(s, config.Lucid100KEvaluationTier, config.Lucid100KBelowBufferTier, config.Lucid100KAboveBufferTier)
    if p == int(SizingProfile.Lucid150K):
        return selected_stage_tier(s, config.Lucid150KEvaluationTier, config.Lucid150KBelowBufferTier, config.Lucid150KAboveBufferTier)
    return 0


def fast_pass_50k_multiplier(stage: int) -> int:
    s = int(stage)
    if s == int(AccountStage.Evaluation):
        return 4
    if s == int(AccountStage.FundedBelowBuffer):
        return 1
    return 3


def fast_pass_50k_base_quantity(tag: str) -> int:
    return _FAST_PASS_50K_BASE_TABLE.get(tag, 0)


def smooth_base_quantity(tag: str) -> int:
    return _SMOOTH_BASE_TABLE.get(tag, 0)


def normal_lucid_quantity(tag: str, profile: int) -> int:
    p = int(profile)
    table = _NORMAL_LUCID_TABLES.get(p)
    if table is None:
        return -1
    return table.get(tag, 0)


def try_get_optimized_evaluation_quantity(tag: str, config: PortfolioConfig) -> tuple[bool, int]:
    """Exact translation of ``TryGetOptimizedEvaluationQuantity(tag, out quantity)``."""
    if not uses_optimized_evaluation_layout(config):
        return False, 0

    p = int(config.SizingProfile)
    if is_explicit_optimized_evaluation_profile(p):
        is_fast = is_fast_optimized_evaluation_profile(p)
    else:
        is_fast = int(config.LucidEvaluationSizing) == int(EvaluationSizingMode.Fast)

    if is_optimized_25k_profile(p):
        bucket = "25K"
    elif is_optimized_50k_profile(p):
        bucket = "50K"
    elif is_optimized_150k_profile(p):
        bucket = "150K"
    else:
        return True, 0

    qty = _OPTIMIZED_EVAL_TABLES[(bucket, is_fast)].get(tag, 0)
    return True, qty


def profile_base_quantity(tag: str, custom_value: int, config: PortfolioConfig) -> int:
    """Exact translation of ``ProfileBaseQuantity(tag, customValue)``."""
    found, opt_qty = try_get_optimized_evaluation_quantity(tag, config)
    if found:
        return opt_qty

    p = int(config.SizingProfile)
    if is_fast_pass_50k_profile(p):
        return fast_pass_50k_base_quantity(tag) * fast_pass_50k_multiplier(config.LucidAccountStage)
    if p == int(SizingProfile.Custom):
        return max(0, int(custom_value))
    if p == int(SizingProfile.PropSmoothBalanced):
        return smooth_base_quantity(tag)
    if p == int(SizingProfile.LongTermPortfolio):
        if tag in _LONG_TERM_PORTFOLIO_TABLE:
            return _LONG_TERM_PORTFOLIO_TABLE[tag]

    norm_qty = normal_lucid_quantity(tag, p)
    if norm_qty >= 0:
        return norm_qty

    tier = active_lucid_tier(config)
    if tier > 0:
        return smooth_base_quantity(tag) * tier
    return max(0, int(custom_value))


def new_module_lucid_quantity(
    tag: str,
    qty_25k: int,
    qty_50k: int,
    qty_100k: int,
    qty_150k: int,
    custom_base: int,
    config: PortfolioConfig,
) -> int:
    """Exact translation of ``NewModuleLucidQuantity(tag, q25, q50, q100, q150, customBase)``."""
    found, opt_qty = try_get_optimized_evaluation_quantity(tag, config)
    if found:
        return opt_qty

    p = int(config.SizingProfile)
    if is_fast_pass_50k_profile(p):
        return max(0, int(qty_25k) * fast_pass_50k_multiplier(config.LucidAccountStage))
    if is_minimum_participation_profile(p):
        return 1 if int(qty_50k) > 0 else 0
    if p == int(SizingProfile.Lucid25K):
        return max(0, int(qty_25k))
    if p == int(SizingProfile.Lucid50K):
        return max(0, int(qty_50k))
    if p == int(SizingProfile.Lucid100K):
        return max(0, int(qty_100k))
    if p == int(SizingProfile.Lucid150K):
        return max(0, int(qty_150k))
    return max(0, int(custom_base) * active_size_level(config))


def added_execution_quantity(planned_mnq_base_quantity: int, config: PortfolioConfig) -> int:
    """Exact translation of ``AddedExecutionQuantity(int plannedMnqBaseQuantity)``."""
    if is_minimum_participation_profile(config.SizingProfile):
        return 1 if int(planned_mnq_base_quantity) > 0 else 0
    return max(0, int(planned_mnq_base_quantity) * active_size_level(config))


def active_lucid_micro_contract_cap(config: PortfolioConfig) -> int:
    """Exact translation of ``ActiveLucidMicroContractCap`` (MNQ net contract ceiling)."""
    if int(config.ExecMode) != int(ExecMode.MNQ):
        return _INT32_MAX
    p = int(config.SizingProfile)
    if is_minimum_participation_profile(p):
        return _INT32_MAX
    if is_optimized_25k_profile(p):
        return 20
    if is_optimized_50k_profile(p):
        return 40
    if p == int(SizingProfile.Lucid100K):
        return 60
    if is_optimized_150k_profile(p):
        return 100
    return _INT32_MAX


def active_rampart_params(config: PortfolioConfig) -> tuple[float, int]:
    """Return exact ``(ActiveRampartRiskUsd, ActiveRampartMaxContracts)`` per ``mod_Q.txt``."""
    if (
        not config.EnableRampart
        or uses_optimized_evaluation_layout(config)
        or is_fast_pass_50k_profile(config.SizingProfile)
    ):
        return 0.0, 0

    p = int(config.SizingProfile)
    if p == int(SizingProfile.Lucid25K):
        return max(0.0, float(config.Rampart25KRiskUsd)), max(0, int(config.Rampart25KMaxContracts))
    if p == int(SizingProfile.Lucid50K):
        return max(0.0, float(config.Rampart50KRiskUsd)), max(0, int(config.Rampart50KMaxContracts))
    if p == int(SizingProfile.Lucid100K):
        return max(0.0, float(config.Rampart100KRiskUsd)), max(0, int(config.Rampart100KMaxContracts))
    if p == int(SizingProfile.Lucid150K):
        return max(0.0, float(config.Rampart150KRiskUsd)), max(0, int(config.Rampart150KMaxContracts))

    lvl = active_size_level(config)
    return (
        max(0.0, float(config.BaseRampartRiskUsd) * lvl),
        max(0, int(config.BaseRampartMaxContracts) * lvl),
    )


def rampart_quantity(
    stop_distance_points: float,
    config: PortfolioConfig,
    chart_point_value: float = POINT_VALUE_NQ,
) -> int:
    """Exact translation of ``RampartQuantity(double stopDistancePoints)`` from ``mod_Q.txt``."""
    risk_usd, max_contracts = active_rampart_params(config)
    if stop_distance_points <= 0.0 or not math.isfinite(stop_distance_points) or risk_usd <= 0.0 or max_contracts <= 0:
        return 0
    mnq_pv = float(chart_point_value) / 10.0 if chart_point_value >= 10.0 else float(chart_point_value)
    if mnq_pv <= 0.0:
        mnq_pv = POINT_VALUE_MNQ
    risk_per_contract = float(stop_distance_points) * mnq_pv
    raw_qty = math.floor(risk_usd / risk_per_contract)
    return min(max(1, int(raw_qty)), max_contracts)


_BASE_CUSTOM_ATTR_BY_TAG: dict[str, str] = {
    "A1": "BaseQtyAbsorb1m",
    "A20": "BaseQtyAbsorb20m",
    "F": "BaseQtyFabio",
    "S": "BaseQtySwas",
    "P": "BaseQtyPullback",
    "C": "BaseQtyCapstone",
    "V": "BaseQtyVault",
    "O": "BaseQtyOvernight",
    "W": "BaseQtyVwapCross",
    "N": "BaseQtyNDay",
}


def resolve_module_quantity(
    tag: str,
    config: PortfolioConfig,
    *,
    native_qty: int = 1,
    stop_distance_points: float | None = None,
    chart_point_value: float = POINT_VALUE_NQ,
) -> int:
    """Compute exact execution contract quantity for any module tag ``A1..Q`` under ``config``."""
    if tag in {"A1", "A20", "F", "S"}:
        custom_val = int(getattr(config, _BASE_CUSTOM_ATTR_BY_TAG[tag]))
        return max(0, profile_base_quantity(tag, custom_val, config) * active_size_level(config))

    if tag in {"C", "V", "O", "W", "N"}:
        custom_val = int(getattr(config, _BASE_CUSTOM_ATTR_BY_TAG[tag]))
        return added_execution_quantity(profile_base_quantity(tag, custom_val, config), config)

    if tag == "P":
        base_p = profile_base_quantity("P", config.BaseQtyPullback, config)
        return added_execution_quantity(max(0, int(native_qty)) * base_p, config)

    if tag == "T":
        p = int(config.SizingProfile)
        if is_fast_pass_50k_profile(p) or is_minimum_participation_profile(p):
            return 0
        found, opt_qty = try_get_optimized_evaluation_quantity("T", config)
        if found:
            return opt_qty
        s = int(config.LucidAccountStage)
        if p == int(SizingProfile.Lucid25K):
            return selected_ftm_stage_quantity(s, config.Ftm25KEvaluationQty, config.Ftm25KBelowQty, config.Ftm25KAboveQty)
        if p == int(SizingProfile.Lucid50K):
            return selected_ftm_stage_quantity(s, config.Ftm50KEvaluationQty, config.Ftm50KBelowQty, config.Ftm50KAboveQty)
        if p == int(SizingProfile.Lucid100K):
            return selected_ftm_stage_quantity(s, config.Ftm100KEvaluationQty, config.Ftm100KBelowQty, config.Ftm100KAboveQty)
        if p == int(SizingProfile.Lucid150K):
            return selected_ftm_stage_quantity(s, config.Ftm150KEvaluationQty, config.Ftm150KBelowQty, config.Ftm150KAboveQty)
        return max(0, int(config.BaseQtyFtm) * active_size_level(config))

    if tag in _NEW_MODULE_LUCID_TUPLES:
        q25, q50, q100, q150, attr = _NEW_MODULE_LUCID_TUPLES[tag]
        return new_module_lucid_quantity(tag, q25, q50, q100, q150, int(getattr(config, attr)), config)

    if tag == "Q":
        if stop_distance_points is not None and math.isfinite(stop_distance_points) and stop_distance_points > 0.0:
            return rampart_quantity(stop_distance_points, config, chart_point_value=chart_point_value)
        risk_usd, max_c = active_rampart_params(config)
        return max_c if (risk_usd > 0.0 and max_c > 0) else 0

    raise ValueError(f"Unknown module tag: {tag!r}")


def uses_half_drawdown_entry_rotation(tag: str) -> bool:
    """Exact translation of ``UsesHalfDrawdownEntryRotation(tag)``."""
    return tag in HALF_DRAWDOWN_ROTATION_OFFSETS


def half_drawdown_rotation_offset(tag: str) -> int:
    """Exact translation of ``HalfDrawdownRotationOffset(tag)``."""
    return HALF_DRAWDOWN_ROTATION_OFFSETS.get(tag, 0)


def configured_loss_cooldown(tag: str, config: PortfolioConfig) -> int:
    """Exact translation of ``ConfiguredLossCooldown(module)``."""
    if tag == "A1":
        return max(0, int(config.A1_LossCooldownBars))
    if tag == "A20":
        return max(0, int(config.A20_LossCooldownBars))
    if tag == "F":
        return max(0, int(config.F_LossCooldownBars))
    if tag == "S":
        return max(0, int(config.S_LossCooldownBars))
    return 0


def is_daily_futures_close_blocked(hhmmss_ct: int, dow_ct: int, config: PortfolioConfig) -> bool:
    """Exact translation of ``IsDailyFuturesCloseBlocked(DateTime centralTime)``.

    Uses Python ``BarSeries.dow_ct`` convention (``0=Mon .. 4=Fri, 5=Sat, 6=Sun``):
    - Saturday (``5``): blocked all day.
    - Friday (``4``): blocked when ``hhmmss_ct >= DailyFuturesFlattenTimeCentral`` (``154400``).
    - Sunday (``6``): blocked when ``hhmmss_ct < DailyFuturesResumeTimeCentral`` (``170100``).
    - Mon..Thu (``0..3``): blocked when ``154400 <= hhmmss_ct < 170100``.
    """
    if not config.FlattenBeforeDailyFuturesClose:
        return False
    t = int(hhmmss_ct)
    d = int(dow_ct)
    flat_t = int(config.DailyFuturesFlattenTimeCentral)
    res_t = int(config.DailyFuturesResumeTimeCentral)

    if d == 5:  # Saturday
        return True
    if d == 4:  # Friday
        return t >= flat_t
    if d == 6:  # Sunday
        return t < res_t
    return flat_t <= t < res_t


def _resolve_news_csv_path(csv_path: str | Path | None) -> Path | None:
    """Locate ``restricted-news-days.csv`` following NT8 template fallback locations."""
    if csv_path is None:
        return None
    raw = str(csv_path).strip().replace("\\", os.sep).replace("/", os.sep)
    if not raw:
        return None
    p = Path(raw)
    if p.exists():
        return p

    home = Path.home()
    candidates = [
        Path.cwd() / raw,
        home / "Documents" / "NinjaTrader 8" / "templates" / raw,
        home / "OneDrive" / "Documents" / "NinjaTrader 8" / "templates" / raw,
        home / "OneDrive" / "Documentos" / "NinjaTrader 8" / "templates" / raw,
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def _resolve_legacy_news_time(event_name: str, date_obj: datetime.date) -> dt_time | None:
    """Exact translation of ``FundedSyncStackTryResolveLegacyNewsTime``."""
    ev = event_name.strip().lower()
    if ev == "fomc emergency":
        ds = date_obj.strftime("%Y-%m-%d")
        if ds == "2020-03-03":
            return dt_time(9, 0, 0)
        if ds == "2020-03-15":
            return dt_time(16, 0, 0)
        return None
    if ev.startswith("fomc"):
        return dt_time(13, 0, 0)
    if ev in {"cpi", "ppi", "employment situation"}:
        return dt_time(7, 30, 0)
    return None


def load_restricted_news_calendar(csv_path: str | Path | None = None) -> tuple[dict[int, list[int]], bool]:
    """Load restricted news calendar mapping Central ``YYYYMMDD -> list[utc_ns]``.

    Returns ``(calendar_dict, ready_flag)``. Parses both explicit ``HH:mm`` / ``HH:mm:ss`` second
    columns and the legacy event names (``FOMC*``, ``FOMC emergency``, ``CPI``, ``PPI``,
    ``Employment Situation``) in ``America/Chicago`` wall time.
    """
    resolved = _resolve_news_csv_path(csv_path)
    if resolved is None or not resolved.exists():
        return {}, False

    cal: dict[int, list[int]] = {}
    with open(resolved, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = [p.strip() for p in stripped.split(",")]
            if len(parts) < 2:
                continue
            try:
                d_obj = datetime.strptime(parts[0], "%Y-%m-%d").date()
            except ValueError:
                continue

            t_obj: dt_time | None = None
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    t_obj = datetime.strptime(parts[1], fmt).time()
                    break
                except ValueError:
                    pass
            if t_obj is None:
                t_obj = _resolve_legacy_news_time(parts[1], d_obj)
            if t_obj is None:
                continue

            dt_ct = datetime.combine(d_obj, t_obj, tzinfo=_TZ_CT)
            utc_ns = int(dt_ct.astimezone(_TZ_UTC).timestamp() * 1_000_000_000)
            date_key = d_obj.year * 10000 + d_obj.month * 100 + d_obj.day
            cal.setdefault(date_key, []).append(utc_ns)

    for key in cal:
        cal[key].sort()
    return cal, True


def is_restricted_news_entry_blocked(
    ts_ns: int,
    cal_date_ct: int,
    calendar: Mapping[int, list[int]],
    calendar_ready: bool,
    config: PortfolioConfig,
) -> bool:
    """Exact translation of ``FundedSyncStackIsRestrictedNewsEntryBlocked``."""
    if not config.FundedSyncStackBlockRestrictedNewsDays:
        return False
    if not calendar_ready:
        return bool(config.missing_news_calendar_blocks)
    events = calendar.get(int(cal_date_ct))
    if not events:
        return False
    before_ns = max(0, int(config.FundedSyncStackMinutesBeforeNews)) * _NS_PER_MIN
    after_ns = max(0, int(config.FundedSyncStackMinutesAfterNews)) * _NS_PER_MIN
    for ev_ns in events:
        if (ev_ns - before_ns) <= ts_ns <= (ev_ns + after_ns):
            return True
    return False


# ---------------------------------------------------------------------------
# PortfolioEngine state machine & Broker vs Virtual accounting
# ---------------------------------------------------------------------------

class PortfolioEngine:
    """Chronological stateful execution, risk, sizing, and netting engine for FUNDEDSYNCSTACK."""

    def __init__(
        self,
        config: PortfolioConfig | None = None,
        ms: MultiSeriesContext | None = None,
    ) -> None:
        self.config: PortfolioConfig = config if config is not None else PortfolioConfig()
        self.ms: MultiSeriesContext | None = ms
        self.modules: dict[str, ModuleState] = {tag: ModuleState(tag=tag) for tag in TAGS_ALL}
        self.half_drawdown_seq: dict[str, int] = {}

        if self.config.news_calendar_override is not None:
            self.news_calendar: dict[int, list[int]] = {
                int(k): sorted(int(v) for v in vs)
                for k, vs in self.config.news_calendar_override.items()
            }
            self.news_calendar_ready: bool = True
        elif self.config.FundedSyncStackBlockRestrictedNewsDays:
            self.news_calendar, self.news_calendar_ready = load_restricted_news_calendar(
                self.config.FundedSyncStackRestrictedNewsCsvPath
            )
        else:
            self.news_calendar = {}
            self.news_calendar_ready = True

        # Portfolio risk & maintenance state
        self.portfolio_risk_date: int = -1
        self.portfolio_daily_closed_pnl: float = 0.0
        self.portfolio_closed_pnl: float = 0.0
        self.portfolio_peak_closed_pnl: float = 0.0
        self.portfolio_max_closed_drawdown: float = 0.0
        self.portfolio_daily_locked: bool = False
        self.portfolio_flatten_submitted: bool = False
        self.portfolio_maintenance_entry_blocked: bool = False
        self.news_entry_blocked: bool = False
        self.port_risk_lockouts: int = 0
        self.daily_flatten_closes: int = 0

        # Ledgers
        self.virtual_trades: list[TradeRecord] = []
        self.skipped_signals: list[dict[str, Any]] = []
        self.daily_pnl_by_ct_date: dict[int, float] = {}
        self.max_gross_contracts: int = 0

        # Broker netting state (single real futures account offsetting opposing virtual sleeves)
        self.broker_net: int = 0
        self.broker_avg_price: float = 0.0
        self.broker_entry_ts: int = 0
        self.broker_closed_pnl: float = 0.0
        self.broker_gross_pnl: float = 0.0
        self.broker_commission_total: float = 0.0
        self.broker_peak_closed_pnl: float = 0.0
        self.broker_max_closed_drawdown: float = 0.0
        self.min_broker_net: int = 0
        self.max_broker_net: int = 0
        self.max_abs_broker_net: int = 0
        self.broker_fills: list[dict[str, Any]] = []
        self.broker_trades: list[dict[str, Any]] = []

        # Bar-index cursor per BIP when advancing chronologically
        self._current_sig_idx: dict[int, int] = {}
        self._last_eval_price: float = float("nan")
        self._next_trade_uid: int = 1

    @property
    def point_value(self) -> float:
        """Return dollar value per point for P&L on the execution contract (NQ=20, MNQ=2)."""
        if self.config.execution_point_value is not None:
            return float(self.config.execution_point_value)
        if int(self.config.ExecMode) == int(ExecMode.MNQ):
            return POINT_VALUE_MNQ
        if self.ms is not None:
            return float(self.ms.point_value)
        return POINT_VALUE_NQ

    @property
    def chart_point_value(self) -> float:
        return float(self.ms.point_value) if self.ms is not None else POINT_VALUE_NQ

    @property
    def tick_size(self) -> float:
        return float(self.ms.tick_size) if self.ms is not None else 0.25

    def module_of(self, tag: str) -> ModuleState:
        return self.modules[tag]

    def virtual_aggregate_net(self) -> int:
        """Exact sum of ``Net`` across all 15 modules in ``TAGS_ALL``."""
        return sum(self.modules[t].net for t in TAGS_ALL)

    def virtual_pending_delta(self) -> int:
        return sum(self.modules[t].pending_delta for t in TAGS_ALL)

    def virtual_gross_contracts(self) -> int:
        return sum(abs(self.modules[t].net) for t in TAGS_ALL)

    def active_lucid_micro_cap(self) -> int:
        return active_lucid_micro_contract_cap(self.config)

    def startup_allows_orders(self) -> bool:
        return (not self.portfolio_maintenance_entry_blocked) and (not self.news_entry_blocked)

    def strategy_selection_allows(self, tag: str, *, check_enable_flag: bool = True) -> bool:
        return strategy_selection_allows(tag, self.config, check_enable_flag=check_enable_flag)

    def can_enter(self, tag: str) -> bool:
        mod = self.modules.get(tag)
        return (
            self.startup_allows_orders()
            and self.strategy_selection_allows(tag)
            and mod is not None
            and mod.can_enter
            and not self.portfolio_daily_locked
        )

    def consume_loss_cooldown(self, tag: str) -> bool:
        """Exact translation of ``ConsumeLossCooldown(ModuleState)``."""
        mod = self.modules.get(tag)
        if mod is None or mod.loss_cooldown_bars_remaining <= 0:
            return True
        mod.loss_cooldown_bars_remaining -= 1
        return False

    def admit_half_drawdown_entry(self, tag: str) -> bool:
        """Exact translation of ``AdmitHalfDrawdownEntry(tag)``: ``((seq + offset) % 5) < 3``."""
        if (not is_minimum_participation_profile(self.config.SizingProfile)) or (
            not uses_half_drawdown_entry_rotation(tag)
        ):
            return True
        seq = self.half_drawdown_seq.get(tag, 0)
        offset = half_drawdown_rotation_offset(tag)
        admitted = ((seq + offset) % 5) < 3
        self.half_drawdown_seq[tag] = (seq + 1) % 5
        return admitted

    def resolve_qty(
        self,
        tag: str,
        *,
        native_qty: int = 1,
        stop_distance_points: float | None = None,
    ) -> int:
        return resolve_module_quantity(
            tag,
            self.config,
            native_qty=native_qty,
            stop_distance_points=stop_distance_points,
            chart_point_value=self.chart_point_value,
        )

    def _ct_date_from_ns(self, ts_ns: int) -> int:
        dt = datetime.fromtimestamp(ts_ns / 1_000_000_000.0, tz=_TZ_UTC).astimezone(_TZ_CT)
        return dt.year * 10000 + dt.month * 100 + dt.day

    def _ct_fields_from_ns(self, ts_ns: int) -> tuple[int, int, int]:
        dt = datetime.fromtimestamp(ts_ns / 1_000_000_000.0, tz=_TZ_UTC).astimezone(_TZ_CT)
        cal_date = dt.year * 10000 + dt.month * 100 + dt.day
        hhmmss = dt.hour * 10000 + dt.minute * 100 + dt.second
        return cal_date, hhmmss, dt.weekday()

    def advance_portfolio_risk_day(self, ts_ns: int, cal_date_ct: int | None = None) -> None:
        """Reset daily closed P&L and ``PORT_RISK`` lock whenever Central calendar date changes."""
        d = int(cal_date_ct) if cal_date_ct is not None else self._ct_date_from_ns(ts_ns)
        if self.portfolio_risk_date != d:
            self.portfolio_risk_date = d
            self.portfolio_daily_closed_pnl = 0.0
            self.portfolio_daily_locked = False
            self.portfolio_flatten_submitted = False

    def enforce_daily_futures_close(
        self,
        ts_ns: int,
        hhmmss_ct: int | None = None,
        dow_ct: int | None = None,
        flatten_price: float | None = None,
    ) -> bool:
        """Enforce CME daily/weekend close: block entries and flatten open modules with ``DAILY_FUTURES_CLOSE``."""
        if hhmmss_ct is None or dow_ct is None:
            _, hhmmss_ct, dow_ct = self._ct_fields_from_ns(ts_ns)
        blocked = is_daily_futures_close_blocked(hhmmss_ct, dow_ct, self.config)
        self.portfolio_maintenance_entry_blocked = blocked
        if blocked:
            for mod in self.modules.values():
                if mod.has_queued_entry or mod.has_entry_order or mod.pending_delta != 0:
                    mod.reset_unfilled_entry()
                if mod.net != 0:
                    px = flatten_price if (flatten_price is not None and math.isfinite(flatten_price)) else self._last_eval_price
                    if math.isfinite(px):
                        self.close_module(mod.tag, px, ts_ns, exit_name="DAILY_FUTURES_CLOSE")
                        self.daily_flatten_closes += 1
        return blocked

    def enforce_restricted_news_day(self, ts_ns: int, cal_date_ct: int | None = None) -> bool:
        """Block new entries & clear pending entry intents during configured news lock windows."""
        d = int(cal_date_ct) if cal_date_ct is not None else self._ct_date_from_ns(ts_ns)
        blocked = is_restricted_news_entry_blocked(
            ts_ns, d, self.news_calendar, self.news_calendar_ready, self.config
        )
        self.news_entry_blocked = blocked
        if blocked:
            for mod in self.modules.values():
                if mod.has_queued_entry or mod.has_entry_order or mod.pending_delta != 0:
                    mod.reset_unfilled_entry()
        return blocked

    def _record_skip(self, tag: str, ts_ns: int, reason: str, detail: str = "") -> None:
        self.modules[tag].skipped_entries += 1
        self.skipped_signals.append(
            {
                "module": tag,
                "ts_ns": int(ts_ns),
                "reason": reason,
                "detail": detail,
            }
        )

    def _apply_broker_fill(
        self,
        tag: str,
        signed_qty: int,
        price: float,
        ts_ns: int,
        reason: str,
    ) -> None:
        """Maintain single-account broker netted position and FIFO/avg-cost round-trip P&L."""
        if signed_qty == 0:
            return
        pv = self.point_value
        comm_per_rt = float(self.config.VirtualRoundTurnCommission)
        self.broker_fills.append(
            {
                "ts_ns": int(ts_ns),
                "module": tag,
                "signed_qty": int(signed_qty),
                "price": float(price),
                "reason": reason,
                "net_before": self.broker_net,
            }
        )

        if self.broker_net == 0:
            self.broker_net = signed_qty
            self.broker_avg_price = float(price)
            self.broker_entry_ts = int(ts_ns)
        elif (self.broker_net > 0 and signed_qty > 0) or (self.broker_net < 0 and signed_qty < 0):
            old_abs = abs(self.broker_net)
            add_abs = abs(signed_qty)
            self.broker_avg_price = (old_abs * self.broker_avg_price + add_abs * float(price)) / (old_abs + add_abs)
            self.broker_net += signed_qty
        else:
            pos_sign = 1 if self.broker_net > 0 else -1
            close_qty = min(abs(self.broker_net), abs(signed_qty))
            gross = pos_sign * (float(price) - self.broker_avg_price) * pv * close_qty
            comm = comm_per_rt * close_qty
            net_pnl = gross - comm

            self.broker_gross_pnl += gross
            self.broker_commission_total += comm
            self.broker_closed_pnl += net_pnl
            if self.broker_closed_pnl > self.broker_peak_closed_pnl:
                self.broker_peak_closed_pnl = self.broker_closed_pnl
            dd = self.broker_closed_pnl - self.broker_peak_closed_pnl
            if dd < self.broker_max_closed_drawdown:
                self.broker_max_closed_drawdown = dd

            self.broker_trades.append(
                {
                    "entry_time_utc": self.broker_entry_ts,
                    "exit_time_utc": int(ts_ns),
                    "side": pos_sign,
                    "qty": close_qty,
                    "entry_price": self.broker_avg_price,
                    "exit_price": float(price),
                    "gross_pnl": gross,
                    "commission": comm,
                    "net_pnl": net_pnl,
                    "trigger_module": tag,
                    "exit_reason": reason,
                }
            )

            rem = abs(signed_qty) - close_qty
            if rem == 0:
                self.broker_net += signed_qty
                if self.broker_net == 0:
                    self.broker_avg_price = 0.0
                    self.broker_entry_ts = 0
            else:
                self.broker_net = (-pos_sign) * rem
                self.broker_avg_price = float(price)
                self.broker_entry_ts = int(ts_ns)

        self.broker_fills[-1]["net_after"] = self.broker_net
        if self.broker_net < self.min_broker_net:
            self.min_broker_net = self.broker_net
        if self.broker_net > self.max_broker_net:
            self.max_broker_net = self.broker_net
        if abs(self.broker_net) > self.max_abs_broker_net:
            self.max_abs_broker_net = abs(self.broker_net)

    def try_enter_module(
        self,
        tag: str,
        side: int,
        qty: int,
        price: float,
        ts_ns: int,
        *,
        stop_price: float = float("nan"),
        target_price: float = float("nan"),
        entry_name: str = "",
        signal_bars_elapsed_since_exit: int | None = None,
        consume_cooldown_if_blocked: bool = True,
        check_enable_flag: bool = True,
    ) -> int | None:
        """Evaluate every portfolio gate in IL order and open ``tag`` if admitted.

        Returns the assigned ``trade_uid`` on fill, or ``None`` if gated/skipped.
        """
        self.advance_portfolio_risk_day(ts_ns)
        mod = self.modules.get(tag)
        if mod is None:
            raise ValueError(f"Unknown module tag: {tag!r}")

        side_sign = 1 if side > 0 else (-1 if side < 0 else 0)
        if side_sign == 0 or qty <= 0:
            self._record_skip(tag, ts_ns, "ZERO_QTY", f"qty={qty}")
            return None

        if not self.strategy_selection_allows(tag, check_enable_flag=check_enable_flag):
            self._record_skip(tag, ts_ns, "STRATEGY_FILTER")
            return None

        if self.portfolio_maintenance_entry_blocked:
            self._record_skip(tag, ts_ns, "MAINTENANCE_CLOSE")
            return None

        if self.news_entry_blocked:
            self._record_skip(tag, ts_ns, "NEWS_WINDOW")
            return None

        if self.portfolio_daily_locked:
            self._record_skip(tag, ts_ns, "PORT_RISK_LOCKED")
            return None

        if not mod.can_enter:
            self._record_skip(tag, ts_ns, "MODULE_BUSY")
            return None

        # Cooldown gate: either advance elapsed signal bars (event stream) or step-by-step (bar runner)
        if mod.loss_cooldown_bars_remaining > 0:
            if signal_bars_elapsed_since_exit is not None:
                if signal_bars_elapsed_since_exit <= mod.loss_cooldown_bars_remaining:
                    mod.loss_cooldown_bars_remaining = max(
                        0, mod.loss_cooldown_bars_remaining - max(1, signal_bars_elapsed_since_exit)
                    )
                    self._record_skip(
                        tag,
                        ts_ns,
                        "LOSS_COOLDOWN",
                        f"elapsed={signal_bars_elapsed_since_exit}",
                    )
                    return None
                mod.loss_cooldown_bars_remaining = 0
            elif consume_cooldown_if_blocked:
                if not self.consume_loss_cooldown(tag):
                    self._record_skip(tag, ts_ns, "LOSS_COOLDOWN")
                    return None
            else:
                self._record_skip(tag, ts_ns, "LOSS_COOLDOWN")
                return None

        # ActiveLucidMicroContractCap gate (verified in SubmitModuleEntryOrder IL_0032..IL_0131)
        signed_qty = side_sign * int(qty)
        cap = self.active_lucid_micro_cap()
        if cap < _INT32_MAX:
            projected_abs_net = abs(self.virtual_aggregate_net() + self.virtual_pending_delta() + signed_qty)
            if projected_abs_net > cap:
                self._record_skip(
                    tag,
                    ts_ns,
                    "LUCID_MNQ_CAP",
                    f"projected={projected_abs_net} > cap={cap}",
                )
                return None

        # HalfDrawdownEntryRotation gate (verified in SubmitModuleEntryOrder IL_02c6)
        if not self.admit_half_drawdown_entry(tag):
            self._record_skip(tag, ts_ns, "HALF_DRAWDOWN_ROTATION")
            return None

        # Admit entry and fill both Virtual Ledger & Broker Netting Ledger
        px = round_tick(float(price), self.tick_size) if math.isfinite(price) else float(price)
        self._last_eval_price = px
        uid = self._next_trade_uid
        self._next_trade_uid += 1

        mod.net = signed_qty
        mod.pending_delta = 0
        mod.expected_entry_quantity = int(qty)
        mod.entry_filled_quantity = int(qty)
        mod.average_entry_price = px
        mod.current_trade_profit = 0.0
        mod.close_settlement_pending = False
        mod.closed_trade_accounted = False
        mod.entry_counted = True
        mod.virtual_entry_count += 1
        mod.entry_time_utc = int(ts_ns)
        mod.entry_name = entry_name or f"{tag}_{'L' if side_sign > 0 else 'S'}"
        mod.stop_price = float(stop_price) if stop_price is not None else float("nan")
        mod.target_price = float(target_price) if target_price is not None else float("nan")
        mod.active_trade_uid = uid
        mod.mae_usd = 0.0
        mod.mfe_usd = 0.0
        mod.bars_held = 1

        gross_open = self.virtual_gross_contracts()
        if gross_open > self.max_gross_contracts:
            self.max_gross_contracts = gross_open

        self._apply_broker_fill(tag, signed_qty, px, ts_ns, mod.entry_name)
        return uid

    def close_module(
        self,
        tag: str,
        price: float,
        ts_ns: int,
        *,
        exit_name: str = "EXIT",
        mae_usd: float | None = None,
        mfe_usd: float | None = None,
        bars: int | None = None,
    ) -> TradeRecord | None:
        """Close open module position, account commissions/cooldown/PORT_RISK, and update broker netting."""
        mod = self.modules.get(tag)
        if mod is None or mod.net == 0:
            return None

        side = 1 if mod.net > 0 else -1
        qty = abs(mod.net)
        exit_px = round_tick(float(price), self.tick_size) if math.isfinite(price) else float(price)
        self._last_eval_price = exit_px
        pv = self.point_value

        pnl_pts = side * (exit_px - mod.average_entry_price)
        gross_usd = pnl_pts * pv * qty
        comm_usd = float(self.config.VirtualRoundTurnCommission) * qty
        net_usd = gross_usd - comm_usd

        # Update virtual module ledger (exact RecordClosedModuleTradeOnce order)
        mod.current_trade_profit = gross_usd
        mod.closed_trade_accounted = True
        mod.virtual_net_profit += net_usd
        mod.virtual_closed_trade_count += 1

        if net_usd < 0.0:
            mod.daily_losses += 1
            cd = configured_loss_cooldown(tag, self.config)
            if cd > 0:
                mod.loss_cooldown_bars_remaining = cd

        if self.ms is not None:
            sig_bip = MODULE_SIGNAL_BIP[tag]
            sig_ts = self.ms.get(sig_bip).ts_ns
            if len(sig_ts) > 0:
                mod.last_exit_sig_idx = int(np.searchsorted(sig_ts, ts_ns, side="right") - 1)

        rec = TradeRecord(
            module=tag,
            side=side,
            qty=qty,
            entry_time_utc=mod.entry_time_utc,
            exit_time_utc=int(ts_ns),
            entry_price=mod.average_entry_price,
            exit_price=exit_px,
            stop_price=mod.stop_price,
            target_price=mod.target_price,
            entry_name=mod.entry_name,
            exit_name=exit_name,
            pnl_pts=pnl_pts,
            pnl_usd=net_usd,
            mae_usd=float(mae_usd) if mae_usd is not None else mod.mae_usd,
            mfe_usd=float(mfe_usd) if mfe_usd is not None else mod.mfe_usd,
            bars=int(bars) if bars is not None else mod.bars_held,
        )
        self.virtual_trades.append(rec)

        # Broker netting exit fill (opposite signed_qty)
        self._apply_broker_fill(tag, -side * qty, exit_px, ts_ns, exit_name)

        # Reset module runtime position BEFORE potential PORT_RISK cascade
        mod.net = 0
        mod.pending_delta = 0
        mod.expected_entry_quantity = 0
        mod.entry_filled_quantity = 0
        mod.average_entry_price = 0.0
        mod.current_trade_profit = 0.0
        mod.active_trade_uid = None
        mod.close_settlement_pending = False
        mod.has_queued_exit = False
        mod.queued_exit_reason = ""
        mod.deferred_exit_after_protection_cancel = False
        mod.deferred_exit_reason = ""
        mod.has_entry_order = False
        mod.has_exit_order = False
        mod.has_stop_order = False
        mod.has_target_order = False

        # Portfolio risk accounting (triggers PORT_RISK across remaining open sleeves if limit breached)
        self.record_portfolio_closed_trade(net_usd, ts_ns, flatten_price=exit_px)
        return rec

    def record_portfolio_closed_trade(
        self,
        net_trade_profit: float,
        ts_ns: int,
        flatten_price: float | None = None,
    ) -> None:
        """Exact translation of ``RecordPortfolioClosedTrade(netTradeProfit, time)``."""
        self.advance_portfolio_risk_day(ts_ns)
        ct_date = self.portfolio_risk_date
        self.daily_pnl_by_ct_date[ct_date] = self.daily_pnl_by_ct_date.get(ct_date, 0.0) + net_trade_profit

        self.portfolio_daily_closed_pnl += net_trade_profit
        self.portfolio_closed_pnl += net_trade_profit
        if self.portfolio_closed_pnl > self.portfolio_peak_closed_pnl:
            self.portfolio_peak_closed_pnl = self.portfolio_closed_pnl
        dd = self.portfolio_closed_pnl - self.portfolio_peak_closed_pnl
        if dd < self.portfolio_max_closed_drawdown:
            self.portfolio_max_closed_drawdown = dd

        limit = float(self.config.PortfolioDailyLossLimit)
        if limit > 0.0 and self.portfolio_daily_closed_pnl <= -limit:
            if not self.portfolio_daily_locked:
                self.port_risk_lockouts += 1
            self.portfolio_daily_locked = True
            if self.config.FlattenOnPortfolioDailyLoss and not self.portfolio_flatten_submitted:
                self.portfolio_flatten_submitted = True
                px = flatten_price if (flatten_price is not None and math.isfinite(flatten_price)) else self._last_eval_price
                if math.isfinite(px):
                    for t in TAGS_ALL:
                        if self.modules[t].net != 0:
                            self.close_module(t, px, ts_ns, exit_name="PORT_RISK")


# ---------------------------------------------------------------------------
# Chronological Simulation & Performance Metrics
# ---------------------------------------------------------------------------

def _is_bar_runner(runner: Any) -> bool:
    return hasattr(runner, "on_bar") or hasattr(runner, "step")


def _invoke_trade_producer(tag: str, runner: Any, ms: MultiSeriesContext | None, config: PortfolioConfig) -> Any:
    if isinstance(runner, (list, tuple, pd.DataFrame)):
        return runner
    if callable(runner):
        sig = inspect.signature(runner)
        params = list(sig.parameters.values())
        pos_params = [
            p
            for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        # Support sibling module runners ``run_*(ms, qty=..., cfg=...)`` directly
        if len(pos_params) >= 2 and pos_params[1].name == "qty":
            if not config.scale_qty_from_config:
                return runner(ms)
            if tag == "P" and pos_params[1].default is None:
                return runner(ms, qty=None)
            return runner(ms, qty=1)
        if has_var or len(pos_params) >= 2:
            return runner(ms, config)
        if len(pos_params) == 1:
            return runner(ms)
        return runner()
    raise TypeError(f"Unsupported runner object: {type(runner).__name__}")


def _normalize_trades_list(tag: str, raw: Any) -> list[TradeRecord]:
    """Convert DataFrame, dicts, or TradeRecord iterable into normalized ``TradeRecord`` list."""
    if raw is None:
        return []
    if isinstance(raw, pd.DataFrame):
        if len(raw) == 0:
            return []
        rows = raw.to_dict("records")
    elif isinstance(raw, Iterable):
        rows = list(raw)
    else:
        raise TypeError(f"Runner output for {tag!r} must be DataFrame or iterable, got {type(raw).__name__}")

    out: list[TradeRecord] = []
    for item in rows:
        if isinstance(item, TradeRecord):
            tr = item if item.module == tag else TradeRecord(
                module=tag,
                side=item.side,
                qty=item.qty,
                entry_time_utc=item.entry_time_utc,
                exit_time_utc=item.exit_time_utc,
                entry_price=item.entry_price,
                exit_price=item.exit_price,
                stop_price=item.stop_price,
                target_price=item.target_price,
                entry_name=item.entry_name,
                exit_name=item.exit_name,
                pnl_pts=item.pnl_pts,
                pnl_usd=item.pnl_usd,
                mae_usd=item.mae_usd,
                mfe_usd=item.mfe_usd,
                bars=item.bars,
            )
            out.append(tr)
        elif isinstance(item, Mapping):
            ep = float(item["entry_price"])
            xp = float(item["exit_price"])
            side = int(item["side"])
            qty = int(item.get("qty", 1))
            pts = float(item.get("pnl_pts", (1 if side > 0 else -1) * (xp - ep)))
            out.append(
                TradeRecord(
                    module=str(item.get("module", tag)),
                    side=side,
                    qty=qty,
                    entry_time_utc=int(item["entry_time_utc"]),
                    exit_time_utc=int(item["exit_time_utc"]),
                    entry_price=ep,
                    exit_price=xp,
                    stop_price=float(item.get("stop_price", float("nan"))),
                    target_price=float(item.get("target_price", float("nan"))),
                    entry_name=str(item.get("entry_name", "")),
                    exit_name=str(item.get("exit_name", "EXIT")),
                    pnl_pts=pts,
                    pnl_usd=float(item.get("pnl_usd", 0.0)),
                    mae_usd=float(item.get("mae_usd", 0.0)),
                    mfe_usd=float(item.get("mfe_usd", 0.0)),
                    bars=int(item.get("bars", 1)),
                )
            )
        else:
            raise TypeError(f"Unsupported trade row type for {tag!r}: {type(item).__name__}")
    return out


def _compute_series_stats(pnls_net: np.ndarray, commissions: np.ndarray) -> dict[str, Any]:
    """Compute core trade count, win rate, PF, expectancy, and closed max drawdown metrics."""
    n = int(len(pnls_net))
    if n == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "gross_pnl_usd": 0.0,
            "commission_usd": 0.0,
            "net_pnl_usd": 0.0,
            "profit_factor": 0.0,
            "expectancy_usd": 0.0,
            "max_closed_dd_usd": 0.0,
            "peak_closed_pnl_usd": 0.0,
        }
    wins = int(np.sum(pnls_net > 0.0))
    losses = int(np.sum(pnls_net < 0.0))
    pos_sum = float(np.sum(pnls_net[pnls_net > 0.0]))
    neg_sum = float(np.sum(pnls_net[pnls_net < 0.0]))
    if neg_sum < 0.0:
        pf = pos_sum / abs(neg_sum)
    elif pos_sum > 0.0:
        pf = float("inf")
    else:
        pf = 0.0
    comm_sum = float(np.sum(commissions))
    net_sum = float(np.sum(pnls_net))
    gross_sum = net_sum + comm_sum
    eq = np.cumsum(pnls_net)
    peaks = np.maximum.accumulate(np.maximum(0.0, eq))
    dd = float(np.min(eq - peaks))
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / n,
        "gross_pnl_usd": gross_sum,
        "commission_usd": comm_sum,
        "net_pnl_usd": net_sum,
        "profit_factor": pf,
        "expectancy_usd": net_sum / n,
        "max_closed_dd_usd": dd,
        "peak_closed_pnl_usd": float(peaks[-1]),
    }


def _build_news_window_events(
    calendar: Mapping[int, list[int]],
    t_min: int,
    t_max: int,
    config: PortfolioConfig,
) -> list[tuple[int, int, int, str, str, Any]]:
    """Create chronological news block-start and block-end trigger events intersecting ``[t_min, t_max]``."""
    if (not config.FundedSyncStackBlockRestrictedNewsDays) or (not calendar):
        return []
    before_ns = max(0, int(config.FundedSyncStackMinutesBeforeNews)) * _NS_PER_MIN
    after_ns = max(0, int(config.FundedSyncStackMinutesAfterNews)) * _NS_PER_MIN
    out: list[tuple[int, int, int, str, str, Any]] = []
    seq = 0
    for date_key in sorted(calendar):
        for ev_ns in calendar[date_key]:
            start_ns = ev_ns - before_ns
            end_ns = ev_ns + after_ns + 1
            if end_ns < t_min or start_ns > t_max:
                continue
            out.append((start_ns, -2, seq, "__NEWS__", "NEWS_SYNC", None))
            seq += 1
            out.append((end_ns, -2, seq, "__NEWS__", "NEWS_SYNC", None))
            seq += 1
    return out


def _build_maintenance_events(
    ms: MultiSeriesContext | None,
    t_min: int,
    t_max: int,
    config: PortfolioConfig,
) -> list[tuple[int, int, int, str, str, Any]]:
    """Find ``bip1`` transitions into daily/weekend maintenance close within ``[t_min, t_max]``."""
    if (not config.FlattenBeforeDailyFuturesClose) or ms is None or len(ms.bip1.ts_ns) == 0:
        return []
    b1 = ms.bip1
    in_range = (b1.ts_ns >= t_min) & (b1.ts_ns <= t_max)
    idxs = np.flatnonzero(in_range)
    if len(idxs) == 0:
        return []

    flat_t = int(config.DailyFuturesFlattenTimeCentral)
    res_t = int(config.DailyFuturesResumeTimeCentral)
    t_arr = b1.hhmmss_ct[idxs]
    d_arr = b1.dow_ct[idxs]
    blocked = (
        (d_arr == 5)
        | ((d_arr == 4) & (t_arr >= flat_t))
        | ((d_arr == 6) & (t_arr < res_t))
        | ((d_arr <= 3) & (t_arr >= flat_t) & (t_arr < res_t))
    )

    transitions = np.empty(len(blocked), dtype=bool)
    transitions[0] = bool(blocked[0])
    transitions[1:] = blocked[1:] != blocked[:-1]

    out: list[tuple[int, int, int, str, str, Any]] = []
    for k, bi in enumerate(idxs[transitions]):
        out.append(
            (
                int(b1.ts_ns[bi]),
                -1,
                k,
                "__MAINT__",
                "MAINT_SYNC",
                (int(b1.hhmmss_ct[bi]), int(b1.dow_ct[bi]), float(b1.close[bi])),
            )
        )
    return out


def _run_bar_driven_simulation(
    ms: MultiSeriesContext,
    bar_runners: dict[str, Any],
    engine: PortfolioEngine,
) -> None:
    """Drive stateful bar-by-bar runners chronologically across ``bip1 .. bip10``."""
    events: list[tuple[int, int, int]] = []
    for bip in range(1, 11):
        s = ms.get(bip)
        ts = s.ts_ns
        for idx in range(len(ts)):
            events.append((int(ts[idx]), bip, idx))
    events.sort(key=lambda x: (x[0], x[1], x[2]))

    b1 = ms.bip1
    runners_by_bip: dict[int, list[tuple[str, Any]]] = {}
    for tag in TAGS_ALL:
        if tag in bar_runners and engine.strategy_selection_allows(tag):
            runners_by_bip.setdefault(MODULE_SIGNAL_BIP[tag], []).append((tag, bar_runners[tag]))

    for ts_ns, bip, idx in events:
        s = ms.get(bip)
        if bip == 1:
            engine.advance_portfolio_risk_day(ts_ns, int(b1.cal_date_ct[idx]))
            engine._last_eval_price = float(b1.close[idx])
            engine.enforce_daily_futures_close(
                ts_ns,
                hhmmss_ct=int(b1.hhmmss_ct[idx]),
                dow_ct=int(b1.dow_ct[idx]),
                flatten_price=float(b1.close[idx]),
            )
            engine.enforce_restricted_news_day(ts_ns, cal_date_ct=int(b1.cal_date_ct[idx]))

        for tag, r in runners_by_bip.get(bip, ()):
            if hasattr(r, "on_bar"):
                r.on_bar(bip, idx, ms, engine)
            else:
                r.step(bip, idx, ms, engine)

            # Update MAE/MFE/bars_held on open module position if on its signal BIP
            mod = engine.modules[tag]
            if mod.net != 0:
                mod.bars_held += 1
                sign = 1 if mod.net > 0 else -1
                qty = abs(mod.net)
                pv = engine.point_value
                hi_pnl = sign * (float(s.high[idx]) - mod.average_entry_price) * pv * qty
                lo_pnl = sign * (float(s.low[idx]) - mod.average_entry_price) * pv * qty
                favorable = max(hi_pnl, lo_pnl)
                adverse = min(hi_pnl, lo_pnl)
                if favorable > mod.mfe_usd:
                    mod.mfe_usd = favorable
                if adverse < mod.mae_usd:
                    mod.mae_usd = adverse


def _run_trade_event_simulation(
    ms: MultiSeriesContext | None,
    trade_runners: dict[str, Any],
    engine: PortfolioEngine,
    config: PortfolioConfig,
) -> None:
    """Replay pre-generated module trades/intents in strict chronological order with all portfolio gates."""
    events: list[tuple[int, int, int, str, str, Any]] = []
    seq = 0
    min_ts = 2**62
    max_ts = -(2**62)
    tag_order = {t: i for i, t in enumerate(TAGS_ALL)}

    for tag in TAGS_ALL:
        if tag not in trade_runners or not engine.strategy_selection_allows(tag):
            continue
        raw = _invoke_trade_producer(tag, trade_runners[tag], ms, config)
        trades = _normalize_trades_list(tag, raw)
        for tr in trades:
            uid_local = seq
            seq += 1
            if tr.entry_time_utc < min_ts:
                min_ts = tr.entry_time_utc
            if tr.exit_time_utc > max_ts:
                max_ts = tr.exit_time_utc
            # Exit priority 0 before entry priority 1 at identical timestamp; break ties by tag order
            events.append((tr.entry_time_utc, 1, tag_order[tag] * 1_000_000 + uid_local, tag, "ENTRY", (uid_local, tr)))
            events.append((tr.exit_time_utc, 0, tag_order[tag] * 1_000_000 + uid_local, tag, "EXIT", (uid_local, tr)))

    if not events:
        return

    events.extend(_build_maintenance_events(ms, min_ts, max_ts, config))
    events.extend(_build_news_window_events(engine.news_calendar, min_ts, max_ts, config))
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    active_source_uid: dict[str, int] = {}
    sig_ts_cache: dict[str, np.ndarray] = {}
    if ms is not None:
        for t in TAGS_ALL:
            sig_ts_cache[t] = ms.get(MODULE_SIGNAL_BIP[t]).ts_ns

    for ts_ns, _, _, tag, kind, payload in events:
        if kind == "MAINT_SYNC":
            hhmm, dow, px = payload
            engine.advance_portfolio_risk_day(ts_ns)
            engine.enforce_daily_futures_close(ts_ns, hhmmss_ct=hhmm, dow_ct=dow, flatten_price=px)
            continue
        if kind == "NEWS_SYNC":
            engine.advance_portfolio_risk_day(ts_ns)
            engine.enforce_restricted_news_day(ts_ns)
            continue

        uid_local, tr = payload
        engine.advance_portfolio_risk_day(ts_ns)
        engine.enforce_daily_futures_close(ts_ns, flatten_price=tr.exit_price if kind == "EXIT" else tr.entry_price)
        engine.enforce_restricted_news_day(ts_ns)

        if kind == "EXIT":
            if active_source_uid.get(tag) == uid_local and engine.modules[tag].net != 0:
                engine.close_module(
                    tag,
                    tr.exit_price,
                    ts_ns,
                    exit_name=tr.exit_name or "EXIT",
                    mae_usd=tr.mae_usd,
                    mfe_usd=tr.mfe_usd,
                    bars=tr.bars,
                )
                active_source_uid.pop(tag, None)
        elif kind == "ENTRY":
            if config.scale_qty_from_config:
                stop_dist = (
                    abs(tr.entry_price - tr.stop_price)
                    if (tr.stop_price is not None and math.isfinite(tr.stop_price) and abs(tr.entry_price - tr.stop_price) > 0.0)
                    else None
                )
                qty = engine.resolve_qty(tag, native_qty=max(1, int(tr.qty)), stop_distance_points=stop_dist)
            else:
                qty = int(tr.qty)

            elapsed_bars: int | None = None
            mod = engine.modules[tag]
            if mod.loss_cooldown_bars_remaining > 0 and mod.last_exit_sig_idx >= 0 and ms is not None:
                sig_ts = sig_ts_cache[tag]
                if len(sig_ts) > 0:
                    entry_idx = int(np.searchsorted(sig_ts, ts_ns, side="right") - 1)
                    elapsed_bars = max(0, entry_idx - mod.last_exit_sig_idx)

            admitted_uid = engine.try_enter_module(
                tag=tag,
                side=tr.side,
                qty=qty,
                price=tr.entry_price,
                ts_ns=ts_ns,
                stop_price=tr.stop_price,
                target_price=tr.target_price,
                entry_name=tr.entry_name,
                signal_bars_elapsed_since_exit=elapsed_bars,
            )
            if admitted_uid is not None:
                active_source_uid[tag] = uid_local


def simular_cartera(
    ms: MultiSeriesContext | None,
    runners_dict: Mapping[str, Any],
    config: PortfolioConfig | None = None,
) -> dict[str, Any]:
    """Simulate multiple FUNDEDSYNCSTACK strategy sleeves chronologically on a unified portfolio ledger.

    Supports both:
    - Trade/intent producers (DataFrame, ``list[TradeRecord]``, ``list[dict]``, or ``fn(ms, config)``)
    - Stateful bar-by-bar runners exposing ``on_bar(bip, idx, ms, engine)`` or ``step(...)``

    Enforces ``PortfolioDailyLossLimit`` (``PORT_RISK``), ``FlattenBeforeDailyFuturesClose``
    (``DAILY_FUTURES_CLOSE``), ``FundedSyncStackBlockRestrictedNewsDays`` (``restricted-news-days.csv``),
    ``HalfDrawdownEntryRotation`` (3-of-5 rotation in Minimum Participation), ``ConsumeLossCooldown``,
    ``ActiveLucidMicroContractCap``, and computes consolidated Virtual Ledger vs Netting Broker metrics.
    """
    cfg = config if config is not None else PortfolioConfig()
    for tag in runners_dict:
        if tag not in TAGS_ALL:
            raise ValueError(f"Unknown module tag in runners_dict: {tag!r}")

    engine = PortfolioEngine(config=cfg, ms=ms)
    bar_runners = {t: r for t, r in runners_dict.items() if _is_bar_runner(r)}
    trade_runners = {t: r for t, r in runners_dict.items() if not _is_bar_runner(r)}

    if bar_runners and trade_runners:
        raise ValueError("Cannot mix bar-driven runners and pre-generated trade producers in one call.")

    if bar_runners:
        if ms is None:
            raise ValueError("MultiSeriesContext ms is required when running bar-driven runners.")
        _run_bar_driven_simulation(ms, bar_runners, engine)
    elif trade_runners:
        _run_trade_event_simulation(ms, trade_runners, engine, cfg)

    # Assemble DataFrames and metrics
    trades_df = trades_to_df(engine.virtual_trades)
    comm_rt = float(cfg.VirtualRoundTurnCommission)

    # Per-module breakdown
    per_module: dict[str, dict[str, Any]] = {}
    per_mod_rows: list[dict[str, Any]] = []
    for tag in TAGS_ALL:
        if tag not in runners_dict and engine.modules[tag].virtual_closed_trade_count == 0 and engine.modules[tag].skipped_entries == 0:
            continue
        mod = engine.modules[tag]
        mod_trades = [t for t in engine.virtual_trades if t.module == tag]
        pnls = np.array([t.pnl_usd for t in mod_trades], dtype=np.float64)
        comms = np.array([comm_rt * t.qty for t in mod_trades], dtype=np.float64)
        st = _compute_series_stats(pnls, comms)
        skip_reasons: dict[str, int] = {}
        for sk in engine.skipped_signals:
            if sk["module"] == tag:
                r = sk["reason"]
                skip_reasons[r] = skip_reasons.get(r, 0) + 1
        row = {
            "module": tag,
            "enabled": engine.strategy_selection_allows(tag),
            **st,
            "skipped_count": mod.skipped_entries,
            "skipped_reasons": skip_reasons,
            "final_net": mod.net,
        }
        per_module[tag] = row
        per_mod_rows.append(row)

    per_module_df = pd.DataFrame(per_mod_rows)

    all_pnls = np.array([t.pnl_usd for t in engine.virtual_trades], dtype=np.float64)
    all_comms = np.array([comm_rt * t.qty for t in engine.virtual_trades], dtype=np.float64)
    virt_stats = _compute_series_stats(all_pnls, all_comms)

    # Daily CT Sharpe (annualized sqrt(252)) over CT trading days that had activity
    daily_vals = np.array(list(engine.daily_pnl_by_ct_date.values()), dtype=np.float64)
    if len(daily_vals) >= 2 and float(np.std(daily_vals, ddof=1)) > 0.0:
        sharpe_daily = float(np.mean(daily_vals) / np.std(daily_vals, ddof=1) * math.sqrt(252.0))
    else:
        sharpe_daily = 0.0

    virtual_ledger = {
        **virt_stats,
        "sharpe_daily": sharpe_daily,
        "max_gross_contracts": engine.max_gross_contracts,
        "port_risk_lockouts": engine.port_risk_lockouts,
        "daily_flatten_closes": engine.daily_flatten_closes,
        "skipped_total": len(engine.skipped_signals),
    }

    broker_trades_df = pd.DataFrame(engine.broker_trades)
    if len(engine.broker_trades) > 0:
        b_pnls = broker_trades_df["net_pnl"].to_numpy(dtype=np.float64)
        b_comms = broker_trades_df["commission"].to_numpy(dtype=np.float64)
    else:
        b_pnls = np.empty(0, dtype=np.float64)
        b_comms = np.empty(0, dtype=np.float64)
    b_stats = _compute_series_stats(b_pnls, b_comms)

    max_gross = max(0, engine.max_gross_contracts)
    max_abs_net = max(0, engine.max_abs_broker_net)
    offset_savings = max(0, max_gross - max_abs_net)
    eff_pct = (offset_savings / max_gross * 100.0) if max_gross > 0 else 0.0

    broker_netting = {
        "fills_count": len(engine.broker_fills),
        "closed_round_trips": b_stats["trades"],
        "broker_gross_pnl_usd": b_stats["gross_pnl_usd"],
        "broker_commission_usd": b_stats["commission_usd"],
        "broker_net_pnl_usd": b_stats["net_pnl_usd"],
        "broker_max_closed_dd_usd": b_stats["max_closed_dd_usd"],
        "broker_profit_factor": b_stats["profit_factor"],
        "min_net_contracts": engine.min_broker_net,
        "max_net_contracts": engine.max_broker_net,
        "max_abs_net_contracts": max_abs_net,
        "final_broker_net": engine.broker_net,
        "max_gross_virtual_contracts": max_gross,
        "contract_offset_savings": offset_savings,
        "netting_efficiency_pct": eff_pct,
        "broker_trades_df": broker_trades_df,
    }

    comparison = {
        "virtual_net_pnl_usd": virtual_ledger["net_pnl_usd"],
        "broker_net_pnl_usd": broker_netting["broker_net_pnl_usd"],
        "net_pnl_diff_usd": broker_netting["broker_net_pnl_usd"] - virtual_ledger["net_pnl_usd"],
        "gross_pnl_diff_usd": broker_netting["broker_gross_pnl_usd"] - virtual_ledger["gross_pnl_usd"],
        "commission_diff_usd": broker_netting["broker_commission_usd"] - virtual_ledger["commission_usd"],
        "virtual_max_closed_dd_usd": virtual_ledger["max_closed_dd_usd"],
        "broker_max_closed_dd_usd": broker_netting["broker_max_closed_dd_usd"],
        "max_gross_virtual_contracts": max_gross,
        "max_abs_broker_net_contracts": max_abs_net,
        "netting_efficiency_pct": eff_pct,
    }

    skipped_df = pd.DataFrame(engine.skipped_signals) if engine.skipped_signals else pd.DataFrame(
        columns=["module", "ts_ns", "reason", "detail"]
    )

    return {
        "config": cfg,
        "trades": engine.virtual_trades,
        "trades_df": trades_df if len(trades_df) > 0 else pd.DataFrame(columns=TRADE_COLUMNS),
        "per_module": per_module,
        "per_module_df": per_module_df,
        "virtual_ledger": virtual_ledger,
        "broker_netting": broker_netting,
        "comparison": comparison,
        "skipped_df": skipped_df,
        "engine": engine,
    }


__all__ = [
    "TAGS_ALL",
    "BUNDLE_A_TAGS",
    "BUNDLE_B_TAGS",
    "MODULE_SIGNAL_BIP",
    "HALF_DRAWDOWN_ROTATION_OFFSETS",
    "STRATEGY_SELECTION_TAG",
    "ExecMode",
    "SizingProfile",
    "AccountStage",
    "EvaluationSizingMode",
    "EntryTiming",
    "StrategySelection",
    "BundleSelection",
    "ExecutionIntentKind",
    "PortfolioConfig",
    "RollingValues",
    "ModuleState",
    "PortfolioEngine",
    "simular_cartera",
    "is_bundle_a",
    "is_bundle_b",
    "is_module_enabled",
    "strategy_selection_allows",
    "is_lucid_sizing_profile",
    "is_fast_pass_50k_profile",
    "is_minimum_participation_profile",
    "is_explicit_optimized_evaluation_profile",
    "is_fast_optimized_evaluation_profile",
    "is_optimized_25k_profile",
    "is_optimized_50k_profile",
    "is_optimized_150k_profile",
    "uses_optimized_evaluation_layout",
    "active_size_level",
    "selected_stage_tier",
    "selected_ftm_stage_quantity",
    "active_lucid_tier",
    "fast_pass_50k_multiplier",
    "fast_pass_50k_base_quantity",
    "smooth_base_quantity",
    "normal_lucid_quantity",
    "try_get_optimized_evaluation_quantity",
    "profile_base_quantity",
    "new_module_lucid_quantity",
    "added_execution_quantity",
    "active_lucid_micro_contract_cap",
    "active_rampart_params",
    "rampart_quantity",
    "resolve_module_quantity",
    "uses_half_drawdown_entry_rotation",
    "half_drawdown_rotation_offset",
    "configured_loss_cooldown",
    "is_daily_futures_close_blocked",
    "load_restricted_news_calendar",
    "is_restricted_news_entry_blocked",
]
