//+------------------------------------------------------------------+
//|                                   EdgeLabFundedSyncPortfolio.mq5 |
//|     P_OPT_SF_v2 Unified Portfolio EA (CFD US100 / NAS100)        |
//+------------------------------------------------------------------+
#property copyright "EdgeLab"
#property strict

#include <EdgeLabFundedSync\FS_CoordinatorAndAdapter.mqh>

input group "01. Prop Account & Risk"
input ENUM_FS_PORTFOLIO_PRESET InpPreset             = FS_PRESET_P_OPT_SF_V2;
input ENUM_FS_PROP_PROFILE     InpPropProfile        = FS_PROP_FTMO_SWING_100K;
input ENUM_FS_ACCOUNT_MODE     InpAccountMode        = FS_MODE_EVALUATION;
input ENUM_FS_RISK_SIZING_MODE InpCustomSizingMode   = FS_SIZE_PCT_INITIAL;
input double                   InpEvalRiskPct        = 0.45;
input double                   InpFundedRiskPct      = 0.45;
input double                   InpEvalRisk1R_USD     = 450.0;
input double                   InpFundedRisk1R_USD   = 450.0;
input double                   InpMaxOpenR           = 3.0;
input double                   InpMaxLotsPerSleeve   = 50.0;
input double                   InpMaxTotalNetLots    = 100.0;
input ENUM_FS_COLLISION_POLICY InpCollisionPolicy    = FS_COL_NETTING;

input group "02. Compliance & Protections"
input int                      InpHardFlattenHHMM_ET = 1640;
input bool                     InpEnforceEvalDailyCap= false;
input double                   InpEvalDailyCapPct    = 0.0;
input double                   InpDailyLossLimitPct  = 3.80;
input bool                     InpEnableFundedDdBrake= true;
input double                   InpDdBrakeThreshPct   = 4.5;
input double                   InpDdBrakeScale       = 0.50;
input bool                     InpEnableNewsGuard    = false;
input int                      InpNewsBlackoutMin    = 2;
input string                   InpNewsHoursEtCsv     = "0830,1000,1400";
input bool                     InpEnableWTrail       = false;
input double                   InpRSlAtrK            = 0.50;

input group "03. Modules & Custom Weights"
input bool                     InpEnableR            = true;
input bool                     InpEnableZ            = true;
input bool                     InpEnableT            = true;
input bool                     InpEnableV            = true;
input bool                     InpEnableW            = true;
input bool                     InpEnableN            = true;
input bool                     InpEnableSOMEOD       = true;
input double                   InpWeightR            = 1.653354;
input double                   InpWeightZ            = 1.965598;
input double                   InpWeightT            = 0.768284;
input double                   InpWeightV            = 1.019769;
input double                   InpWeightW            = 0.915674;
input double                   InpWeightN            = 1.252428;
input double                   InpWeightSOMEOD       = 0.911410;

input group "04. Broker Timezone, Execution & Warmup"
input ENUM_FS_TZ_MODE          InpTzMode             = FS_TZ_NY_PLUS_7_ALL_YEAR;
input double                   InpFixedUtcOffsetHrs  = 2.0;
input double                   InpOverrideUsdPerPtLot= 0.0;
input double                   InpFrictionPts        = 1.50;
input double                   InpSignalTickSize     = 0.25;
input bool                     InpCheckStopsOnTick   = true;
input bool                     InpUseBrokerProtSL    = true;
input int                      InpWarmupBars         = 350000;
input bool                     InpAllowMidSyncOnStart= false;
input ulong                    InpMagicNumber        = 910101;
input bool                     InpEnableCsvLog       = false;
input string                   InpCsvFileName        = "EdgeLab_MT5_Portfolio_Parity.csv";

CFundedSyncMt5Adapter g_adapter;

int OnInit()
{
   bool enables[7];
   enables[0] = InpEnableR; enables[1] = InpEnableZ; enables[2] = InpEnableT;
   enables[3] = InpEnableV; enables[4] = InpEnableW; enables[5] = InpEnableN; enables[6] = InpEnableSOMEOD;

   double weights[7];
   weights[0] = InpWeightR; weights[1] = InpWeightZ; weights[2] = InpWeightT;
   weights[3] = InpWeightV; weights[4] = InpWeightW; weights[5] = InpWeightN; weights[6] = InpWeightSOMEOD;

   return g_adapter.InitFromPreset(
      "FS_Port", InpMagicNumber, InpPreset, InpPropProfile, InpAccountMode, InpCustomSizingMode,
      InpEvalRiskPct, InpFundedRiskPct, InpEvalRisk1R_USD, InpFundedRisk1R_USD, InpMaxOpenR,
      InpMaxLotsPerSleeve, InpMaxTotalNetLots, InpCollisionPolicy, InpHardFlattenHHMM_ET,
      InpEnforceEvalDailyCap, InpEvalDailyCapPct, InpDailyLossLimitPct,
      InpEnableFundedDdBrake, InpDdBrakeThreshPct, InpDdBrakeScale,
      InpEnableNewsGuard, InpNewsBlackoutMin, InpNewsHoursEtCsv,
      InpTzMode, InpFixedUtcOffsetHrs, InpOverrideUsdPerPtLot, InpFrictionPts, InpSignalTickSize,
      InpCheckStopsOnTick, InpUseBrokerProtSL, InpWarmupBars, InpAllowMidSyncOnStart,
      InpEnableWTrail, InpEnableCsvLog, InpCsvFileName,
      enables, weights, true,
      3.0, 660, InpRSlAtrK);
}

void OnTick()   { g_adapter.OnTick(); }
double OnTester() { return g_adapter.OnTesterScore(); }
//+------------------------------------------------------------------+
