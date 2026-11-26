#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    /// <summary>
    /// Isolated Strategy Analyzer auditor and live executor for any single FUNDEDSYNC module
    /// (R, Z, T, V, W, N, or SOMEOD) with all core tunable parameters exposed in NinjaTrader 8.
    /// Requires >= 500 trading days (~2y) of 1-Minute ETH data on NQ/MNQ (especially for T KNN and V 252d).
    /// SOMEOD_ext_NQ computes ATR(14) on M5 NY+7h using SMA of True Range.
    /// </summary>
    public class EdgeLabFundedSyncSingleModule : Strategy
    {
        private FundedSyncNt8Adapter _adapter;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Single-Module FUNDEDSYNC Strategy Analyzer Auditor & Tunable Executor.";
                Name = "EdgeLabFundedSyncSingleModule";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 2;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsInstantiatedOnEachOptimizationIteration = true;

                TargetModule = FundedSyncModuleId.R_osc30_end660_ATR50;
                Risk1R_USD = 450.0;
                MaxMicroContracts = 40;
                SecondaryMnqSymbol = string.Empty;
                HardFlattenHHMM_ET = 1640;

                ROscAtrMult = 3.0;
                REndMinEt = 660;
                RSlAtrK = 0.50;

                ZBucketMin = 15;
                ZEmaPeriod = 20;
                ZMinEffPct = 40.0;
                ZSlAtrK = 0.50;

                TStopOrbMult = 1.0;
                TBeTriggerR = 1.5;

                VNoiseMult = 0.25;
                VSlAtrK = 0.30;

                WSlAtrK = 0.25;
                EnableWTrail = false;

                NDays = 5;
                NSlAtrK = 0.25;

                EnableParityCsvLog = true;
                ParityCsvFileName = "EdgeLab_SingleModule_ParityTrades.csv";
            }
            else if (State == State.Configure)
            {
                if (!string.IsNullOrWhiteSpace(SecondaryMnqSymbol))
                    AddDataSeries(SecondaryMnqSymbol.Trim(), BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                int idx = (int)TargetModule;
                var weights = new Dictionary<string, double>();
                bool[] flags = new bool[FundedSyncMath.ModuleOrder.Length];
                for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
                {
                    string modId = FundedSyncMath.ModuleOrder[i];
                    weights[modId] = (i == idx) ? 1.0 : 0.0;
                    flags[i] = (i == idx);
                }

                var coord = new PortfolioCoordinator(
                    weights, flags, enableWTrail: EnableWTrail,
                    rOscMult: ROscAtrMult, rEndEt: REndMinEt, rSlAtr: RSlAtrK,
                    zBucketMin: ZBucketMin, zEmaPeriod: ZEmaPeriod, zMinEffPct: ZMinEffPct, zSlAtr: ZSlAtrK,
                    tStopOrbMult: TStopOrbMult, tBeTrigR: TBeTriggerR,
                    vNoiseMult: VNoiseMult, vSlAtr: VSlAtrK,
                    wSlAtr: WSlAtrK, nDays: NDays, nSlAtr: NSlAtrK)
                {
                    MicroPointValue = 2.0,
                    FrictionMiniPts = 1.545,
                    AccountMode = FundedSyncAccountMode.Evaluation,
                    EvalRisk1R_USD = Risk1R_USD,
                    FundedRisk1R_USD = Risk1R_USD,
                    MaxOpenR = 3.0,
                    MaxMicroContracts = MaxMicroContracts,
                    CollisionPolicy = FundedSyncCollisionPolicy.Independent,
                    HardFlattenHHMM_ET = HardFlattenHHMM_ET,
                    EnforceEvalDailyCap = false,
                    EvalDailyCapUSD = 0.0,
                    DailyLossLimitUSD = 0.0
                };

                bool hasSec = !string.IsNullOrWhiteSpace(SecondaryMnqSymbol);
                _adapter = new FundedSyncNt8Adapter(
                    this, coord, TargetModule.ToString(), hasSec, EnableParityCsvLog, ParityCsvFileName);
                Print("EdgeLabFundedSyncSingleModule initialized for " + TargetModule + " (>= 500 trading days M1 ETH recommended).");
            }
        }

        protected override void OnBarUpdate()
        {
            if (_adapter != null)
                _adapter.OnBarUpdate();
        }

        #region NinjaScript Properties
        [NinjaScriptProperty] [Display(Name = "Target Module", Order = 1, GroupName = "01. Module & Sizing")] public FundedSyncModuleId TargetModule { get; set; }
        [NinjaScriptProperty] [Range(50.0, 5000.0)] [Display(Name = "Risk 1R USD", Order = 2, GroupName = "01. Module & Sizing")] public double Risk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max Micros Cap", Order = 3, GroupName = "01. Module & Sizing")] public int MaxMicroContracts { get; set; }
        [NinjaScriptProperty] [Display(Name = "Secondary MNQ Symbol (Hybrid)", Order = 4, GroupName = "01. Module & Sizing")] public string SecondaryMnqSymbol { get; set; }
        [NinjaScriptProperty] [Range(1500, 2400)] [Display(Name = "Hard Flatten HHMM ET", Order = 5, GroupName = "01. Module & Sizing")] public int HardFlattenHHMM_ET { get; set; }

        [NinjaScriptProperty] [Range(0.5, 10.0)] [Display(Name = "R Osc ATR Mult", Order = 10, GroupName = "02. Module Params")] public double ROscAtrMult { get; set; }
        [NinjaScriptProperty] [Range(570, 960)] [Display(Name = "R Entry End Min ET", Order = 11, GroupName = "02. Module Params")] public int REndMinEt { get; set; }
        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "R SL ATR K", Order = 12, GroupName = "02. Module Params")] public double RSlAtrK { get; set; }

        [NinjaScriptProperty] [Range(5, 60)] [Display(Name = "Z Bucket Minutes", Order = 13, GroupName = "02. Module Params")] public int ZBucketMin { get; set; }
        [NinjaScriptProperty] [Range(5, 100)] [Display(Name = "Z EMA Period", Order = 14, GroupName = "02. Module Params")] public int ZEmaPeriod { get; set; }
        [NinjaScriptProperty] [Range(0.0, 100.0)] [Display(Name = "Z Min Efficiency Pct", Order = 15, GroupName = "02. Module Params")] public double ZMinEffPct { get; set; }
        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "Z SL ATR K", Order = 16, GroupName = "02. Module Params")] public double ZSlAtrK { get; set; }

        [NinjaScriptProperty] [Range(0.25, 3.0)] [Display(Name = "T Stop ORB Mult", Order = 17, GroupName = "02. Module Params")] public double TStopOrbMult { get; set; }
        [NinjaScriptProperty] [Range(0.0, 5.0)] [Display(Name = "T BE Trigger R", Order = 18, GroupName = "02. Module Params")] public double TBeTriggerR { get; set; }

        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "V Noise Mult", Order = 19, GroupName = "02. Module Params")] public double VNoiseMult { get; set; }
        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "V SL ATR K", Order = 20, GroupName = "02. Module Params")] public double VSlAtrK { get; set; }

        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "W SL ATR K", Order = 21, GroupName = "02. Module Params")] public double WSlAtrK { get; set; }
        [NinjaScriptProperty] [Display(Name = "W Enable Trail", Order = 22, GroupName = "02. Module Params")] public bool EnableWTrail { get; set; }

        [NinjaScriptProperty] [Range(1, 30)] [Display(Name = "N Lookback Days", Order = 23, GroupName = "02. Module Params")] public int NDays { get; set; }
        [NinjaScriptProperty] [Range(0.05, 2.0)] [Display(Name = "N SL ATR K", Order = 24, GroupName = "02. Module Params")] public double NSlAtrK { get; set; }

        [NinjaScriptProperty] [Display(Name = "Enable Parity CSV Log", Order = 30, GroupName = "03. Parity Logger")] public bool EnableParityCsvLog { get; set; }
        [NinjaScriptProperty] [Display(Name = "Parity CSV File Name", Order = 31, GroupName = "03. Parity Logger")] public string ParityCsvFileName { get; set; }
        #endregion
    }
}
