//+------------------------------------------------------------------+
//|                                       EdgeLabFundedSyncCore6.mq5 |
//|       P_OPT_Core6 EA (R+Z+T+V+W+N, 6 NQ modules without SOMEOD)  |
//+------------------------------------------------------------------+
#property copyright "EdgeLab"
#property strict

#include <EdgeLabFundedSync\FS_CoordinatorAndAdapter.mqh>

input group "01. Prop Account & Risk"
input ENUM_FS_PROP_PROFILE     InpPropProfile        = FS_PROP_FTMO_SWING_100K;
input ENUM_FS_ACCOUNT_MODE     InpAccountMode        = FS_MODE_EVALUATION;
input ENUM_FS_RISK_SIZING_MODE InpCustomSizingMode   = FS_SIZE_PCT_INITIAL;
input double                   InpEvalRiskPct        = 0.75;
input double                   InpFundedRiskPct      = 0.75;
input double                   InpEvalRisk1R_USD     = 750.0;
input double                   InpFundedRisk1R_USD   = 750.0;
input double                   InpMaxOpenR           = 3.0;
input double                   InpMaxLotsPerSleeve   = 50.0;
input double                   InpMaxTotalNetLots    = 100.0;
input ENUM_FS_COLLISION_POLICY InpCollisionPolicy    = FS_COL_NETTING;

input group "02. Compliance & Protections"
input int                      InpHardFlattenHHMM_ET = 1640;
input bool                     InpEnforceEvalDailyCap= false;
input double                   InpEvalDailyCapPct    = 0.0;
input double                   InpDailyLossLimitPct  = 3.80;
input bool                     InpEnableFundedDdBrake= false;
input double                   InpDdBrakeThreshPct   = 5.0;
input double                   InpDdBrakeScale       = 0.50;
input bool                     InpEnableNewsGuard    = false;
input int                      InpNewsBlackoutMin    = 2;
input string                   InpNewsHoursEtCsv     = "0830,1000,1400";

input group "03. Broker Timezone, Execution & Warmup"
input ENUM_FS_TZ_MODE          InpTzMode             = FS_TZ_NY_PLUS_7_ALL_YEAR;
input double                   InpFixedUtcOffsetHrs  = 2.0;
input double                   InpOverrideUsdPerPtLot= 0.0;
input double                   InpFrictionPts        = 1.50;
input double                   InpSignalTickSize     = 0.25;
input bool                     InpCheckStopsOnTick   = true;
input bool                     InpUseBrokerProtSL    = true;
input int                      InpWarmupBars         = 350000;
input bool                     InpAllowMidSyncOnStart= false;
input ulong                    InpMagicNumber        = 910103;
input bool                     InpEnableCsvLog       = false;
input string                   InpCsvFileName        = "EdgeLab_MT5_Core6_Parity.csv";

CFundedSyncMt5Adapter g_adapter;

int OnInit()
{
   bool dummyEn[7] = { true, true, true, true, true, true, true };
   double dummyW[7] = { 0, 0, 0, 0, 0, 0, 0 };
   return g_adapter.InitFromPreset(
      "FS_Core6", InpMagicNumber, FS_PRESET_P_OPT_CORE6, InpPropProfile, InpAccountMode, InpCustomSizingMode,
      InpEvalRiskPct, InpFundedRiskPct, InpEvalRisk1R_USD, InpFundedRisk1R_USD, InpMaxOpenR,
      InpMaxLotsPerSleeve, InpMaxTotalNetLots, InpCollisionPolicy, InpHardFlattenHHMM_ET,
      InpEnforceEvalDailyCap, InpEvalDailyCapPct, InpDailyLossLimitPct,
      InpEnableFundedDdBrake, InpDdBrakeThreshPct, InpDdBrakeScale,
      InpEnableNewsGuard, InpNewsBlackoutMin, InpNewsHoursEtCsv,
      InpTzMode, InpFixedUtcOffsetHrs, InpOverrideUsdPerPtLot, InpFrictionPts, InpSignalTickSize,
      InpCheckStopsOnTick, InpUseBrokerProtSL, InpWarmupBars, InpAllowMidSyncOnStart,
      false, InpEnableCsvLog, InpCsvFileName,
      dummyEn, dummyW, false);
}

void OnTick()   { g_adapter.OnTick(); }
double OnTester() { return g_adapter.OnTesterScore(); }
//+------------------------------------------------------------------+
