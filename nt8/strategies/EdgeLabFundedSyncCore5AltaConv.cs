#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    /// <summary>
    /// Core5_AltaConv FUNDEDSYNC Strategy: 5 high-conviction modules (R + Z + T + N + SOMEOD)
    /// without V or W. Lowest REP drawdown profile (-11.8 R DD, Calmar 5.04, 93% positive months)
    /// suitable for tight prop funded scaling or conservative intraday trailing limits.
    /// Requires >= 500 trading days (~2y) of 1-Minute ETH data on NQ/MNQ.
    /// </summary>
    public class EdgeLabFundedSyncCore5AltaConv : Strategy
    {
        private FundedSyncNt8Adapter _adapter;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Core5_AltaConv FUNDEDSYNC (R+Z+T+N+SOMEOD, without V or W).";
                Name = "EdgeLabFundedSyncCore5AltaConv";
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

                PropProfile = FundedSyncPropProfile.LucidFlex_150K_Equilibrado;
                AccountMode = FundedSyncAccountMode.Evaluation;
                EvalRisk1R_USD = 450.0;
                FundedRisk1R_USD = 450.0;
                MaxOpenR = 3.0;
                MaxMicroContracts = 100;
                CollisionPolicy = FundedSyncCollisionPolicy.Netting;
                SecondaryMnqSymbol = string.Empty;
                HardFlattenHHMM_ET = 1640;
                EnforceEvalDailyCap = true;
                EvalDailyCapUSD = 3420.0;
                DailyLossLimitUSD = 2700.0;
                EnableParityCsvLog = false;
                ParityCsvFileName = "EdgeLab_Core5AltaConv_ParityTrades.csv";
            }
            else if (State == State.Configure)
            {
                if (!string.IsNullOrWhiteSpace(SecondaryMnqSymbol))
                    AddDataSeries(SecondaryMnqSymbol.Trim(), BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                _adapter = FundedSyncNt8Adapter.CreateFromPreset(
                    this,
                    "Core5_AltaConv",
                    FundedSyncPortfolioPreset.Core5_AltaConv,
                    PropProfile,
                    AccountMode,
                    EvalRisk1R_USD,
                    FundedRisk1R_USD,
                    MaxOpenR,
                    MaxMicroContracts,
                    CollisionPolicy,
                    HardFlattenHHMM_ET,
                    EnforceEvalDailyCap,
                    EvalDailyCapUSD,
                    DailyLossLimitUSD,
                    false,
                    SecondaryMnqSymbol,
                    EnableParityCsvLog,
                    ParityCsvFileName,
                    null,
                    null);
                Print("EdgeLabFundedSyncCore5AltaConv initialized (>= 500 trading days M1 ETH required).");
            }
        }

        protected override void OnBarUpdate()
        {
            if (_adapter != null)
                _adapter.OnBarUpdate();
        }

        #region NinjaScript Properties
        [NinjaScriptProperty] [Display(Name = "Prop Firm Profile", Order = 1, GroupName = "01. Prop Account")] public FundedSyncPropProfile PropProfile { get; set; }
        [NinjaScriptProperty] [Display(Name = "Account Mode", Order = 2, GroupName = "01. Prop Account")] public FundedSyncAccountMode AccountMode { get; set; }
        [NinjaScriptProperty] [Range(50.0, 2500.0)] [Display(Name = "Eval Risk 1R USD (Custom)", Order = 3, GroupName = "01. Prop Account")] public double EvalRisk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(50.0, 2500.0)] [Display(Name = "Funded Risk 1R USD (Custom)", Order = 4, GroupName = "01. Prop Account")] public double FundedRisk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(0.5, 10.0)] [Display(Name = "Max Concurrent Open R", Order = 5, GroupName = "01. Prop Account")] public double MaxOpenR { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max Micros Cap (Custom)", Order = 6, GroupName = "01. Prop Account")] public int MaxMicroContracts { get; set; }
        [NinjaScriptProperty] [Display(Name = "Collision Policy (Custom)", Order = 7, GroupName = "01. Prop Account")] public FundedSyncCollisionPolicy CollisionPolicy { get; set; }
        [NinjaScriptProperty] [Display(Name = "Secondary MNQ Symbol (Hybrid)", Order = 8, GroupName = "01. Prop Account")] public string SecondaryMnqSymbol { get; set; }

        [NinjaScriptProperty] [Range(1500, 2400)] [Display(Name = "Hard Flatten HHMM ET (Custom)", Order = 10, GroupName = "02. Compliance")] public int HardFlattenHHMM_ET { get; set; }
        [NinjaScriptProperty] [Display(Name = "Enforce Eval Daily Cap (Custom)", Order = 11, GroupName = "02. Compliance")] public bool EnforceEvalDailyCap { get; set; }
        [NinjaScriptProperty] [Range(0.0, 50000.0)] [Display(Name = "Eval Daily Cap USD (Custom)", Order = 12, GroupName = "02. Compliance")] public double EvalDailyCapUSD { get; set; }
        [NinjaScriptProperty] [Range(0.0, 50000.0)] [Display(Name = "Daily Loss Limit USD (Custom)", Order = 13, GroupName = "02. Compliance")] public double DailyLossLimitUSD { get; set; }

        [NinjaScriptProperty] [Display(Name = "Enable Parity CSV Log", Order = 20, GroupName = "03. Parity Logger")] public bool EnableParityCsvLog { get; set; }
        [NinjaScriptProperty] [Display(Name = "Parity CSV File Name", Order = 21, GroupName = "03. Parity Logger")] public string ParityCsvFileName { get; set; }
        #endregion
    }
}
