#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    /// <summary>
    /// EdgeLab candidata: ES5N (control de EXTERNAS_ESTRUCTURALES_A5).
    /// Regla Python exact: edgelab/research/externas_estructurales_a5.py (lines 260-279).
    /// A las 10:00 NY (cierre barra 09:59): si RSI(10) diario RTH previo esta en [40, 60] y |C(09:59) - Open_0930| >= 0.12 * ATR20_RTH,
    /// entra en direccion del impulso de 30m con stop = 0.45 * ATR20_RTH y salida al cierre 16:00 NY.
    /// CSV: Documents\NinjaTrader 8\EdgeLab\candidatas\ES5N_<Activo>.csv.
    /// </summary>
    public class EdgeLabCandidataES5N : Strategy
    {
        private TimeZoneInfo _chartTz, _nyTz;
        private NewsVetoCalendar _newsCal;
        private FundedSyncAssetSpec _spec;
        private string _csvPath;
        private bool _csvHeaderWritten, _blocked;

        // Estado diario causal RTH
        private DateTime _rthDate = DateTime.MinValue;
        private bool _hasRthDay;
        private double _rthOpen, _rthHi, _rthLo, _rthCl;
        private double _prevRthClose = double.NaN;
        private readonly Queue<double> _atr20 = new Queue<double>();
        private double _avgG = double.NaN, _avgL = double.NaN, _rsi10 = 50.0;
        private double _dayAtr = double.NaN, _dayRsi10 = 50.0;
        private bool _tradedToday;

        // Posicion
        private int _pendingSide;
        private double _pendingRiskPts;
        private int _activeSide, _activeQty;
        private DateTime _entryNy;
        private double _entryPx, _activeStopPx, _activeRiskPts;
        private string _exitReasonHint;

        private const string SigL = "ES5N_L", SigS = "ES5N_S";

        private static bool EsCuentaSimulada(Account acc)
        {
            if (acc == null) return true;
            string n = acc.Name ?? "";
            return n.StartsWith("Sim", StringComparison.OrdinalIgnoreCase)
                || n.StartsWith("Playback", StringComparison.OrdinalIgnoreCase)
                || n.StartsWith("Backtest", StringComparison.OrdinalIgnoreCase);
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "EdgeLab candidata: ES5N (continuacion 10:00 NY con RSI10 diario neutro 40..60).";
                Name = "EdgeLabCandidataES5N";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
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

                Activo = FundedSyncActivo.ES;
                Risk1R_USD = 2000.0;
                MaxContracts = 20;
                ContratosFijos = 1;
                EnableNewsVeto = true;
                NewsBeforeMin = 2.0; NewsAfterMin = 2.0; FomcBeforeMin = 5.0; FomcAfterMin = 5.0;
                EnableCsvLog = true;
            }
            else if (State == State.DataLoaded)
            {
                _nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
                _chartTz = Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
                _spec = FundedSyncAssets.Get(Activo);
                string master = (Instrument != null && Instrument.MasterInstrument != null) ? Instrument.MasterInstrument.Name : "";
                if (!FundedSyncAssets.ChartMatches(Activo, master))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataES5N BLOQUEADA: grafico=" + master + ", Activo=" + _spec.Root);
                    return;
                }
                if (Activo != FundedSyncActivo.ES && Activo != FundedSyncActivo.MES
                    && Activo != FundedSyncActivo.NQ && Activo != FundedSyncActivo.MNQ && !EsCuentaSimulada(Account))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataES5N BLOQUEADA: bajo revision en ES/NQ; resto solo Sim/Playback.");
                    return;
                }

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "candidatas");
                Directory.CreateDirectory(dir);
                _csvPath = Path.Combine(dir, "ES5N_" + _spec.Root + ".csv");
                if (EnableCsvLog && File.Exists(_csvPath)) File.Delete(_csvPath);

                if (EnableNewsVeto)
                {
                    _newsCal = new NewsVetoCalendar(
                        Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    Print("EdgeLabCandidataES5N news veto: " + _newsCal.Status);
                }
            }
        }

        private void ClosePrevRthDay()
        {
            if (!_hasRthDay) return;
            double tr = !double.IsNaN(_prevRthClose)
                ? Math.Max(_rthHi - _rthLo, Math.Max(Math.Abs(_rthHi - _prevRthClose), Math.Abs(_rthLo - _prevRthClose)))
                : (_rthHi - _rthLo);
            _atr20.Enqueue(tr);
            if (_atr20.Count > 20) _atr20.Dequeue();

            if (!double.IsNaN(_prevRthClose))
            {
                double d = _rthCl - _prevRthClose;
                double g = d > 0.0 ? d : 0.0;
                double lVal = d < 0.0 ? -d : 0.0;
                if (double.IsNaN(_avgG)) { _avgG = g; _avgL = lVal; }
                else
                {
                    const double alpha = 1.0 / 10.0;
                    _avgG = (1.0 - alpha) * _avgG + alpha * g;
                    _avgL = (1.0 - alpha) * _avgL + alpha * lVal;
                }
                double tot = _avgG + _avgL;
                _rsi10 = tot > 1e-12 ? (100.0 * _avgG / tot) : 50.0;
            }
            _prevRthClose = _rthCl;
            _hasRthDay = false;
        }

        private int ComputeContracts(double riskPts)
        {
            if (ContratosFijos > 0) return ContratosFijos;
            double r1Usd = Math.Max(riskPts * _spec.PointValue, 1e-6);
            int q = (int)Math.Min(MaxContracts, Math.Max(0, Math.Round(Risk1R_USD / r1Usd)));
            if (q == 0 && Risk1R_USD >= 0.55 * r1Usd) q = 1;
            return q;
        }

        protected override void OnBarUpdate()
        {
            if (_blocked || BarsInProgress != 0 || BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                return;

            DateTime chartLocal = DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified);
            DateTime closeUtc = _chartTz.Id == TimeZoneInfo.Utc.Id
                ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc)
                : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            DateTime closeNy = TimeZoneInfo.ConvertTimeFromUtc(closeUtc, _nyTz);
            DateTime openNy = closeNy.AddMinutes(-1);
            int openMin = openNy.Hour * 60 + openNy.Minute;
            bool inNews = EnableNewsVeto && _newsCal != null && _newsCal.BlocksAt(closeUtc);

            if (Position.MarketPosition != MarketPosition.Flat)
            {
                if (inNews)
                {
                    _exitReasonHint = "NEWS_VETO";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("ES5N_news", SigL);
                    else ExitShort("ES5N_news", SigS);
                    return;
                }
                if (openMin >= 959 || Bars.IsLastBarOfSession || (openNy.Date != _rthDate && _rthDate != DateTime.MinValue))
                {
                    _exitReasonHint = "EOD_CLOSE";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("ES5N_eod", SigL);
                    else ExitShort("ES5N_eod", SigS);
                    return;
                }
            }

            if (openMin < 570 || openMin >= 960) return;

            if (openNy.Date != _rthDate)
            {
                ClosePrevRthDay();
                _rthDate = openNy.Date;
                _hasRthDay = true;
                _rthOpen = Open[0];
                _rthHi = High[0];
                _rthLo = Low[0];
                _rthCl = Close[0];
                _tradedToday = false;
                _dayAtr = _atr20.Count >= 4 ? _atr20.Average() : double.NaN;
                _dayRsi10 = _rsi10;
            }
            _rthHi = Math.Max(_rthHi, High[0]);
            _rthLo = Math.Min(_rthLo, Low[0]);
            _rthCl = Close[0];

            if (openMin == 599 && !_tradedToday && Position.MarketPosition == MarketPosition.Flat)
            {
                _tradedToday = true;
                if (inNews || double.IsNaN(_dayAtr) || !(_dayAtr > 0) || double.IsNaN(_prevRthClose)) return;

                double ret30m = Close[0] - _rthOpen;
                if (Math.Abs(ret30m) < 0.12 * _dayAtr) return;
                if (_dayRsi10 < 40.0 || _dayRsi10 > 60.0) return;

                int side = ret30m > 0.0 ? 1 : -1;
                double riskPts = 0.45 * _dayAtr;
                int q = ComputeContracts(riskPts);
                if (q < 1) return;

                _pendingSide = side;
                _pendingRiskPts = riskPts;
                _exitReasonHint = null;
                if (side == 1) EnterLong(q, SigL);
                else EnterShort(q, SigS);
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (_blocked || execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            DateTime chartLocal = DateTime.SpecifyKind(time, DateTimeKind.Unspecified);
            DateTime utc = _chartTz.Id == TimeZoneInfo.Utc.Id ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc) : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            DateTime ny = TimeZoneInfo.ConvertTimeFromUtc(utc, _nyTz);
            string oname = execution.Order.Name;

            if (oname == SigL || oname == SigS)
            {
                _activeSide = _pendingSide;
                _activeQty = execution.Order.Filled;
                _entryPx = execution.Order.AverageFillPrice;
                _entryNy = ny;
                _activeRiskPts = _pendingRiskPts;
                _activeStopPx = FundedSyncMath.RoundTick(_entryPx - _activeSide * _activeRiskPts, _spec.Tick);
                if (_activeSide == 1) ExitLongStopMarket(0, true, _activeQty, _activeStopPx, "ES5N_stop", SigL);
                else ExitShortStopMarket(0, true, _activeQty, _activeStopPx, "ES5N_stop", SigS);
            }
            else if (Position.MarketPosition == MarketPosition.Flat && _activeQty > 0)
            {
                double exPx = execution.Order.AverageFillPrice;
                double pnlPts = _activeSide * (exPx - _entryPx);
                double rBruto = pnlPts / Math.Max(_activeRiskPts, 1e-6);
                double rNet = (pnlPts - _spec.FrictionPts) / Math.Max(_activeRiskPts, 1e-6);
                string reason = !string.IsNullOrEmpty(_exitReasonHint) ? _exitReasonHint : (oname == "ES5N_stop" ? "STOP" : oname);
                WriteCsvRow(ny, exPx, pnlPts, rBruto, rNet, reason);
                _activeQty = 0;
                _exitReasonHint = null;
            }
        }

        private void WriteCsvRow(DateTime exitNy, double exitPx, double pnlPts, double rBruto, double rNet, string reason)
        {
            if (!EnableCsvLog || string.IsNullOrEmpty(_csvPath)) return;
            try
            {
                if (!_csvHeaderWritten)
                {
                    if (!File.Exists(_csvPath) || new FileInfo(_csvPath).Length == 0)
                        File.WriteAllText(_csvPath, "fecha_int,a5,modulo,w_w5,side,en_ny,ex_ny,entry_price,stop_price,exit_price,riesgo_pts,pnl_pts,R_bruto,R_neto_mini,exit_name,contratos,valor_punto,riesgo_usd_real,riesgo_usd_objetivo" + Environment.NewLine, Encoding.UTF8);
                    _csvHeaderWritten = true;
                }
                int fechaInt = _entryNy.Year * 10000 + _entryNy.Month * 100 + _entryNy.Day;
                double rRealUsd = _activeRiskPts * _activeQty * _spec.PointValue;
                double rObjUsd = ContratosFijos > 0 ? rRealUsd : Risk1R_USD;
                string line = string.Format(CultureInfo.InvariantCulture,
                    "{0},LIVE,ES5N,1.000000,{1},{2},{3},{4:F2},{5:F4},{6:F4},{7:F4},{8:F2},{9:F6},{10:F6},{11},{12},{13:F2},{14:F2},{15:F2}",
                    fechaInt, _activeSide,
                    _entryNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    exitNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    _entryPx, _activeStopPx, exitPx, _activeRiskPts, pnlPts, rBruto, rNet, reason,
                    _activeQty, _spec.PointValue, rRealUsd, rObjUsd);
                File.AppendAllText(_csvPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        #region NinjaScript Properties
        [NinjaScriptProperty] [Display(Name = "Activo", Order = 1, GroupName = "01. Estrategia y activo")] public FundedSyncActivo Activo { get; set; }
        [NinjaScriptProperty] [Range(10.0, 10000.0)] [Display(Name = "Riesgo 1R USD", Order = 2, GroupName = "02. Riesgo")] public double Risk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max contratos", Order = 3, GroupName = "02. Riesgo")] public int MaxContracts { get; set; }
        [NinjaScriptProperty] [Range(0, 50)] [Display(Name = "Contratos fijos (0 = por riesgo)", Order = 4, GroupName = "02. Riesgo")] public int ContratosFijos { get; set; }
        [NinjaScriptProperty] [Display(Name = "Veto de noticias", Order = 10, GroupName = "03. Noticias")] public bool EnableNewsVeto { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes", Order = 11, GroupName = "03. Noticias")] public double NewsBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues", Order = 12, GroupName = "03. Noticias")] public double NewsAfterMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes FOMC", Order = 13, GroupName = "03. Noticias")] public double FomcBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues FOMC", Order = 14, GroupName = "03. Noticias")] public double FomcAfterMin { get; set; }
        [NinjaScriptProperty] [Display(Name = "Guardar CSV en candidatas", Order = 20, GroupName = "04. Salida")] public bool EnableCsvLog { get; set; }
        #endregion
    }
}
