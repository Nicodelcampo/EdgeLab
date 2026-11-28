//+------------------------------------------------------------------+
//|                                EdgeLabFundedSyncSingleModule.mq5 |
//|   Single-Module Strategy Tester Auditor & Optimizer (Any 1 Mod)  |
//+------------------------------------------------------------------+
#property copyright "EdgeLab"
#property strict

#include <EdgeLabFundedSync\FS_CoordinatorAndAdapter.mqh>

input group "01. Module & Sizing"
input ENUM_FS_MODULE_ID        InpTargetModule       = FS_MOD_R;
input ENUM_FS_RISK_SIZING_MODE InpSizingMode         = FS_SIZE_PCT_INITIAL;
input double                   InpRisk1R_Pct         = 0.75;
input double                   InpRisk1R_USD         = 750.0;
input double                   InpMaxLots            = 50.0;
input int                      InpHardFlattenHHMM_ET = 1640;

input group "02. Tunable Module Parameters"
input double                   InpROscAtrMult        = 3.0;
input int                      InpREndMinEt          = 660;
input double                   InpRSlAtrK            = 0.50;
input int                      InpZBucketMin         = 15;
input int                      InpZEmaPeriod         = 20;
input double                   InpZMinEffPct         = 40.0;
input double                   InpZSlAtrK            = 0.50;
input double                   InpTStopOrbMult       = 1.0;
input double                   InpTBeTriggerR        = 1.5;
input double                   InpVNoiseMult         = 0.25;
input double                   InpVSlAtrK            = 0.30;
input double                   InpWSlAtrK            = 0.25;
input bool                     InpEnableWTrail       = false;
input int                      InpNDays              = 5;
input double                   InpNSlAtrK            = 0.25;

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
input ulong                    InpMagicNumber        = 910105;
input bool                     InpEnableCsvLog       = true;
input string                   InpCsvFileName        = "EdgeLab_MT5_SingleModule_Parity.csv";

CFundedSyncMt5Adapter g_adapter;

int OnInit()
{
   int idx = (int)InpTargetModule;
   bool enables[7];
   double weights[7];
   for(int i = 0; i < 7; i++)
   {
      enables[i] = (i == idx);
      weights[i] = (i == idx) ? 1.0 : 0.0;
   }

   return g_adapter.InitFromPreset(
      "FS_Single_" + IntegerToString(idx), InpMagicNumber,
      FS_PRESET_CUSTOM_WEIGHTS, FS_PROP_PERSONAL_CUSTOM, FS_MODE_EVALUATION, InpSizingMode,
      InpRisk1R_Pct, InpRisk1R_Pct, InpRisk1R_USD, InpRisk1R_USD, 3.0,
      InpMaxLots, InpMaxLots, FS_COL_INDEPENDENT, InpHardFlattenHHMM_ET,
      false, 0.0, 0.0,
      false, 5.0, 0.50,
      false, 2, "0830,1000,1400",
      InpTzMode, InpFixedUtcOffsetHrs, InpOverrideUsdPerPtLot, InpFrictionPts, InpSignalTickSize,
      InpCheckStopsOnTick, InpUseBrokerProtSL, InpWarmupBars, InpAllowMidSyncOnStart,
      InpEnableWTrail, InpEnableCsvLog, InpCsvFileName,
      enables, weights, true,
      InpROscAtrMult, InpREndMinEt, InpRSlAtrK,
      InpZBucketMin, InpZEmaPeriod, InpZMinEffPct, InpZSlAtrK,
      InpTStopOrbMult, InpTBeTriggerR,
      InpVNoiseMult, InpVSlAtrK,
      InpWSlAtrK, InpNDays, InpNSlAtrK);
}

void OnTick()   { g_adapter.OnTick(); }
double OnTester() { return g_adapter.OnTesterScore(); }
//+------------------------------------------------------------------+
