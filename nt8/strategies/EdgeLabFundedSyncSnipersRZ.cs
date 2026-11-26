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
    /// Tier1_Snipers_RZ Strategy: High-Sharpe low-frequency sleeve pair (R_osc30_end660_ATR50 + Z_b15_e20_eff40_ATR50,
    /// ~5 ops/month, ~20% active days, DD -3.3 R DESC / -4.4 R REP). Designed for personal capital accounts or
    /// already-funded cushion accounts without monthly evaluation time pressure.
    /// Requires >= 60 trading days (500 recommended) of 1-Minute ETH data on NQ/MNQ.
    /// </summary>
    public class EdgeLabFundedSyncSnipersRZ : Strategy
    {
        private FundedSyncNt8Adapter _adapter;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Tier1_Snipers_RZ FUNDEDSYNC (R+Z low-frequency ~5 ops/mo sniper portfolio).";
                Name = "EdgeLabFundedSyncSnipersRZ";
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

                PropProfile = FundedSyncPropProfile.Personal_Custom;
                AccountMode = FundedSyncAccountMode.Funded;
                EvalRisk1R_USD = 450.0;
                FundedRisk1R_USD = 450.0;
                MaxOpenR = 3.0;
                MaxMicroContracts = 100;
                CollisionPolicy = FundedSyncCollisionPolicy.Netting;
                SecondaryMnqSymbol = string.Empty;
                HardFlattenHHMM_ET = 1640;
                EnforceEvalDailyCap = false;
                EvalDailyCapUSD = 0.0;
                DailyLossLimitUSD = 0.0;
                EnableParityCsvLog = false;
                ParityCsvFileName = "EdgeLab_SnipersRZ_ParityTrades.csv";
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
                    "Tier1_Snipers_RZ",
                    FundedSyncPortfolioPreset.Tier1_Snipers_RZ,
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
                Print("EdgeLabFundedSyncSnipersRZ initialized (500 trading days M1 ETH recommended).");
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
        [NinjaScriptProperty] [Range(50.0, 5000.0)] [Display(Name = "Eval Risk 1R USD (Custom)", Order = 3, GroupName = "01. Prop Account")] public double EvalRisk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(50.0, 5000.0)] [Display(Name = "Funded Risk 1R USD (Custom)", Order = 4, GroupName = "01. Prop Account")] public double FundedRisk1R_USD { get; set; }
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
