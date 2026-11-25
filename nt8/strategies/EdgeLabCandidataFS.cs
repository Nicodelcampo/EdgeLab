#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    /// <summary>
    /// EdgeLab candidate tester (2026-11-25): ONE FundedSync module on ONE asset, to verify in NT8 parity, news veto,
    /// sizing across eras/volatility and trade frequency. Selecting "Activo" loads that asset's parameters, point value,
    /// tick and canonical friction (edgelab/costos.py); the strategy refuses to trade if the chart is another instrument.
    /// Sizing is computed directly in chart contracts (no micro->mini conversion). Evidence per (module, asset) comes from
    /// docs/research/FACTORES.jsonl and the 2026-11-25 amendment: combinations without evidence only run on Sim/Playback.
    /// Trades log: Documents\NinjaTrader 8\EdgeLab\candidatas\<module>_<asset>.csv (risk real vs target, exit reason).
    /// NOTE: indicators need warm-up (ATR20 session, KNN, 252d); the first months of a run do not reproduce history.
    /// </summary>
    public class EdgeLabCandidataFS : Strategy
    {
        private FundedSyncNt8Adapter _adapter;
        private bool _blocked;

        // Evidence (registry) per module and asset. PISTA_VIVA / BAJO_REVISION may run anywhere (decision of Nico is
        // still needed for real money); SIN_EVIDENCIA / NO_REPETIR only on simulation accounts.
        public static string Evidencia(FundedSyncModuleId m, FundedSyncActivo a)
        {
            bool nq = a == FundedSyncActivo.NQ || a == FundedSyncActivo.MNQ;
            bool es = a == FundedSyncActivo.ES || a == FundedSyncActivo.MES;
            if (m == FundedSyncModuleId.Z_b15_e20_eff40_ATR50 && a == FundedSyncActivo.RTY) return "NO_REPETIR";   // F-Z-RTY-REP-COLAPSA
            switch (m)
            {
                case FundedSyncModuleId.T_stop100_BE15R_calFalse:
                case FundedSyncModuleId.R_osc30_end660_ATR50:
                case FundedSyncModuleId.Z_b15_e20_eff40_ATR50:
                case FundedSyncModuleId.V_nm25_noCap_mae30:
                    return nq ? "PISTA_VIVA" : (es ? "BAJO_REVISION" : "SIN_EVIDENCIA");
                case FundedSyncModuleId.SOMEOD_ext_NQ:
                    return nq ? "BAJO_REVISION" : (es ? "BAJO_REVISION" : "SIN_EVIDENCIA");
                case FundedSyncModuleId.W_slope_allowReFalse_ATR25:
                case FundedSyncModuleId.N_d5_fbTrue_ATR25:
                    return (nq || es) ? "BAJO_REVISION" : "SIN_EVIDENCIA";   // F-FUNDEDSYNC-SIN-VENTAJA: W tal cual NO_REPETIR
                default:
                    return "SIN_EVIDENCIA";
            }
        }

        private static bool EsCuentaSimulada(Account acc)
        {
            if (acc == null) return true;
            string n = acc.Name ?? "";
            return n.StartsWith("Sim", StringComparison.OrdinalIgnoreCase) || n.StartsWith("Playback", StringComparison.OrdinalIgnoreCase)
                || n.StartsWith("Backtest", StringComparison.OrdinalIgnoreCase);
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "EdgeLab: un modulo FundedSync en un activo (paridad, veto de noticias, sizing y frecuencia).";
                Name = "EdgeLabCandidataFS";
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

                Modulo = FundedSyncModuleId.T_stop100_BE15R_calFalse;
                Activo = FundedSyncActivo.MNQ;
                Risk1R_USD = 200.0;
                MaxContratosPorModulo = 20;
                MaxContratosNetos = 20;
                ContratosFijos = 1;                   // por defecto: 1 contrato (paridad en puntos)
                HardFlattenHHMM_ET = 1640;
                EnableNewsVeto = true;
                NewsBeforeMin = 2.0; NewsAfterMin = 2.0; FomcBeforeMin = 5.0; FomcAfterMin = 5.0;
            }
            else if (State == State.DataLoaded)
            {
                FundedSyncAssetSpec spec = FundedSyncAssets.Get(Activo);
                string master = (Instrument != null && Instrument.MasterInstrument != null) ? Instrument.MasterInstrument.Name : "";
                string ev = Evidencia(Modulo, Activo);
                if (!FundedSyncAssets.ChartMatches(Activo, master))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataFS BLOQUEADA: el grafico es " + master + " y el activo elegido es " + spec.Root + ".");
                    return;
                }
                if ((ev == "SIN_EVIDENCIA" || ev == "NO_REPETIR") && !EsCuentaSimulada(Account))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataFS BLOQUEADA: " + Modulo + " en " + spec.Root + " es " + ev + "; solo en cuentas Sim/Playback.");
                    return;
                }

                int idx = (int)Modulo;
                var weights = new Dictionary<string, double>();
                bool[] flags = new bool[FundedSyncMath.ModuleOrder.Length];
                for (int i = 0; i < FundedSyncMath.ModuleOrder.Length; i++)
                {
                    weights[FundedSyncMath.ModuleOrder[i]] = (i == idx) ? 1.0 : 0.0;
                    flags[i] = (i == idx);
                }

                // Parametros por activo: NQ/MNQ = vendedor FundedSync (paridad IL); ES/MES = preset ES_Core_US500;
                // YM/MYM/RTY = parametros NQ (exploratorio, sin evidencia).
                bool es = Activo == FundedSyncActivo.ES || Activo == FundedSyncActivo.MES;
                PortfolioCoordinator coord = es
                    ? new PortfolioCoordinator(weights, flags, enableWTrail: false,
                        rOscMult: 2.0, rEndEt: 660, rSlAtr: 0.50,
                        zBucketMin: 15, zEmaPeriod: 20, zMinEffPct: 35.0, zSlAtr: 0.50,
                        tStopOrbMult: 1.0, tBeTrigR: 0.0,
                        vNoiseMult: 0.30, vSlAtr: 0.35,
                        wSlAtr: 0.35, nDays: 5, nSlAtr: 0.25,
                        tStopMinPts: 0.6, tStopMaxPts: 29.0, vTpPts: 15.7, wUseSlopeFilter: false, nAcceptBufPts: 0.9)
                    : new PortfolioCoordinator(weights, flags);

                coord.MicroPointValue = spec.PointValue;          // contratos del grafico, no micros
                coord.FrictionMiniPts = spec.FrictionPts;          // friccion canonica de edgelab/costos.py
                coord.AccountMode = FundedSyncAccountMode.Evaluation;
                coord.EvalRisk1R_USD = Risk1R_USD;
                coord.FundedRisk1R_USD = Risk1R_USD;
                coord.MaxOpenR = 1.0;
                coord.MaxMicroContracts = MaxContratosPorModulo;
                coord.MaxNetContracts = MaxContratosNetos;
                coord.FixedContracts = ContratosFijos;
                coord.CollisionPolicy = FundedSyncCollisionPolicy.Independent;
                coord.HardFlattenHHMM_ET = HardFlattenHHMM_ET;
                coord.EnforceEvalDailyCap = false;
                coord.EvalDailyCapUSD = 0.0;
                coord.DailyLossLimitUSD = 0.0;

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "candidatas");
                Directory.CreateDirectory(dir);
                string csv = Path.Combine(dir, Modulo + "_" + spec.Root + ".csv");
                if (File.Exists(csv)) File.Delete(csv);            // una corrida = un archivo
                _adapter = new FundedSyncNt8Adapter(this, coord, Modulo + "_" + spec.Root, false, true, csv);
                _adapter.ChartUnits = true;
                if (EnableNewsVeto)
                {
                    var cal = new NewsVetoCalendar(Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    _adapter.SetNewsVeto(cal);
                    Print("EdgeLab news veto: " + cal.Status);
                }
                if (ContratosFijos == 0)
                    Print("EdgeLabCandidataFS AVISO: sizing por riesgo con 1R=$" + Risk1R_USD + " y $" + spec.PointValue
                          + "/punto: una operacion con stop mayor a " + (Risk1R_USD / 0.55 / spec.PointValue).ToString("F1")
                          + " pts NO entra (0 contratos). En NQ/ES enteros usar 1R >= $2000 o contratos fijos.");
                Print("EdgeLabCandidataFS " + Modulo + " en " + spec.Root + " (" + ev + "), 1R=$" + Risk1R_USD + ", PV=" + spec.PointValue
                      + ", friccion " + spec.FrictionPts + " pts, CSV " + csv);
            }
        }

        protected override void OnBarUpdate()
        {
            if (_blocked || _adapter == null) return;
            _adapter.OnBarUpdate();
        }

        #region NinjaScript Properties
        [NinjaScriptProperty] [Display(Name = "Modulo", Order = 1, GroupName = "01. Estrategia y activo")] public FundedSyncModuleId Modulo { get; set; }
        [NinjaScriptProperty] [Display(Name = "Activo", Order = 2, GroupName = "01. Estrategia y activo")] public FundedSyncActivo Activo { get; set; }
        [NinjaScriptProperty] [Range(10.0, 5000.0)] [Display(Name = "Riesgo 1R USD", Order = 3, GroupName = "02. Riesgo")] public double Risk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max contratos por modulo", Order = 4, GroupName = "02. Riesgo")] public int MaxContratosPorModulo { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max contratos netos", Order = 5, GroupName = "02. Riesgo")] public int MaxContratosNetos { get; set; }
        [NinjaScriptProperty] [Range(0, 50)] [Display(Name = "Contratos fijos (0 = por riesgo)", Order = 7, GroupName = "02. Riesgo")] public int ContratosFijos { get; set; }
        [NinjaScriptProperty] [Range(1500, 2400)] [Display(Name = "Cierre forzado HHMM ET", Order = 6, GroupName = "02. Riesgo")] public int HardFlattenHHMM_ET { get; set; }
        [NinjaScriptProperty] [Display(Name = "Veto de noticias", Order = 10, GroupName = "03. Noticias")] public bool EnableNewsVeto { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes", Order = 11, GroupName = "03. Noticias")] public double NewsBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues", Order = 12, GroupName = "03. Noticias")] public double NewsAfterMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes FOMC", Order = 13, GroupName = "03. Noticias")] public double FomcBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues FOMC", Order = 14, GroupName = "03. Noticias")] public double FomcAfterMin { get; set; }
        #endregion
    }
}
