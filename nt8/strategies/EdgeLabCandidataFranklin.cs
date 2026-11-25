#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    /// <summary>
    /// EdgeLab candidate: Franklin (1000|rango|ninguno) + opcional Veto PREAPERTURA-ES (noche == "alto").
    /// Regla Python: edgelab/research/estrategias_scrapeadas.py::franklin_variantes ("1000|rango|ninguno")
    /// y tools/fundedsync_mecanismos.py::contexto (rango nocturno 18:00-09:30 NY / cierre RTH previo, tercil 251d).
    /// CSV: Documents\NinjaTrader 8\EdgeLab\candidatas\Franklin[_Preap]_<Activo>.csv.
    /// </summary>
    public class EdgeLabCandidataFranklin : Strategy
    {
        private TimeZoneInfo _chartTz, _nyTz;
        private NewsVetoCalendar _newsCal;
        private FundedSyncAssetSpec _spec;
        private string _csvPath;
        private bool _csvHeaderWritten, _blocked;

        // Sesion CME (18:00 NY) para VWAP y rango Londres/noche
        private DateTime _sesDate = DateTime.MinValue;
        private double _cumPv, _cumVol;
        private double _lonHi = double.NaN, _lonLo = double.NaN;
        private double _nightHi = double.NaN, _nightLo = double.NaN;
        private bool _nightEvaluated;
        private bool _nightHighToday;

        // Rango apertura NY (09:30-10:00) y cierre RTH previo para veto PREAPERTURA
        private DateTime _rthDate = DateTime.MinValue;
        private double _orHi = double.NaN, _orLo = double.NaN;
        private double _curRthClose = double.NaN, _prevRthClose = double.NaN;
        private readonly Queue<double> _nightHist = new Queue<double>();
        private bool _tradedToday;

        // Estado de orden/posicion activa
        private int _pendingSide;
        private double _pendingStopPx, _pendingRiskPts;
        private int _activeSide, _activeQty;
        private DateTime _entryNy;
        private double _entryPx, _activeStopPx, _activeTargetPx, _activeRiskPts;
        private string _exitReasonHint;

        private const string SigL = "FR_L", SigS = "FR_S";

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
                Description = "EdgeLab candidata: Franklin (10:00 NY vs Londres + VWAP sesion) + opcional Veto PREAPERTURA.";
                Name = "EdgeLabCandidataFranklin";
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

                Activo = FundedSyncActivo.NQ;
                EnableVetoPreapertura = false;
                TpR = 0.0;
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
                    Print("EdgeLabCandidataFranklin BLOQUEADA: grafico=" + master + ", Activo=" + _spec.Root);
                    return;
                }
                if (Activo != FundedSyncActivo.NQ && Activo != FundedSyncActivo.MNQ
                    && Activo != FundedSyncActivo.ES && Activo != FundedSyncActivo.MES && !EsCuentaSimulada(Account))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataFranklin BLOQUEADA: sin evidencia en " + _spec.Root + " para cuenta real.");
                    return;
                }

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "candidatas");
                Directory.CreateDirectory(dir);
                string tag = EnableVetoPreapertura ? "Franklin_VetoPreap" : "Franklin";
                _csvPath = Path.Combine(dir, tag + "_" + _spec.Root + ".csv");
                if (EnableCsvLog && File.Exists(_csvPath)) File.Delete(_csvPath);

                if (EnableNewsVeto)
                {
                    _newsCal = new NewsVetoCalendar(
                        Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    Print("EdgeLabCandidataFranklin news veto: " + _newsCal.Status);
                }
                Print("EdgeLabCandidataFranklin lista en " + _spec.Root + " | VetoPreapertura=" + EnableVetoPreapertura + " | CSV=" + _csvPath);
            }
        }

        private int ComputeContracts(double riskPts)
        {
            if (ContratosFijos > 0) return ContratosFijos;
            double r1Usd = Math.Max(riskPts * _spec.PointValue, 1e-6);
            int q = (int)Math.Min(MaxContracts, Math.Max(0, Math.Round(Risk1R_USD / r1Usd)));
            if (q == 0 && Risk1R_USD >= 0.55 * r1Usd) q = 1;
            return q;
        }

        private void EvalPreaperturaVetoIfNeeded()
        {
            if (_nightEvaluated) return;
            _nightEvaluated = true;
            _nightHighToday = false;
            if (double.IsNaN(_nightHi) || double.IsNaN(_nightLo) || double.IsNaN(_prevRthClose) || _prevRthClose <= 0) return;
            double val = (_nightHi - _nightLo) / _prevRthClose;
            if (_nightHist.Count >= 120)
            {
                int below = 0;
                foreach (double x in _nightHist) if (x < val) below++;
                double rank = (double)below / _nightHist.Count;
                if (rank > 2.0 / 3.0) _nightHighToday = true;
            }
            _nightHist.Enqueue(val);
            if (_nightHist.Count > 250) _nightHist.Dequeue();
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
            DateTime tradingSes = openNy.AddHours(6).Date;

            if (tradingSes != _sesDate)
            {
                _sesDate = tradingSes;
                _cumPv = 0.0; _cumVol = 0.0;
                _lonHi = double.NaN; _lonLo = double.NaN;
                _nightHi = double.NaN; _nightLo = double.NaN;
                _nightEvaluated = false; _nightHighToday = false;
            }

            double tp = (High[0] + Low[0] + Close[0]) / 3.0;
            double vol = Math.Max(Volume[0], 1e-9);
            _cumPv += tp * vol;
            _cumVol += vol;
            double vwap = _cumVol > 0 ? (_cumPv / _cumVol) : Close[0];

            // Rango nocturno (18:00..09:30 NY open) y Londres (03:00..09:30 NY open)
            if (openMin >= 1080 || openMin < 570)
            {
                _nightHi = double.IsNaN(_nightHi) ? High[0] : Math.Max(_nightHi, High[0]);
                _nightLo = double.IsNaN(_nightLo) ? Low[0] : Math.Min(_nightLo, Low[0]);
            }
            if (openMin >= 180 && openMin < 570)
            {
                _lonHi = double.IsNaN(_lonHi) ? High[0] : Math.Max(_lonHi, High[0]);
                _lonLo = double.IsNaN(_lonLo) ? Low[0] : Math.Min(_lonLo, Low[0]);
            }

            bool inNews = EnableNewsVeto && _newsCal != null && _newsCal.BlocksAt(closeUtc);

            // Salida por veto de noticias o cierre RTH (16:00 NY = vela open 15:59) o fin de sesion
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                if (inNews)
                {
                    _exitReasonHint = "NEWS_VETO";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("FR_news", SigL);
                    else ExitShort("FR_news", SigS);
                    return;
                }
                if (openMin >= 959 || Bars.IsLastBarOfSession || (openNy.Date != _rthDate && _rthDate != DateTime.MinValue))
                {
                    _exitReasonHint = "EOD_CLOSE";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("FR_eod", SigL);
                    else ExitShort("FR_eod", SigS);
                    return;
                }
            }

            bool inRth = openMin >= 570 && openMin < 960;
            if (!inRth) return;

            if (openNy.Date != _rthDate)
            {
                if (!double.IsNaN(_curRthClose)) _prevRthClose = _curRthClose;
                _rthDate = openNy.Date;
                _orHi = double.NaN; _orLo = double.NaN;
                _tradedToday = false;
                EvalPreaperturaVetoIfNeeded();
            }
            _curRthClose = Close[0];

            if (openMin < 600)
            {
                _orHi = double.IsNaN(_orHi) ? High[0] : Math.Max(_orHi, High[0]);
                _orLo = double.IsNaN(_orLo) ? Low[0] : Math.Min(_orLo, Low[0]);
            }

            // Decision al cierre de la vela 09:59 -> 10:00 NY (openMin == 599)
            if (openMin == 599 && !_tradedToday && Position.MarketPosition == MarketPosition.Flat)
            {
                _tradedToday = true;
                if (inNews) return;
                if (EnableVetoPreapertura && _nightHighToday) return;
                if (double.IsNaN(_lonHi) || double.IsNaN(_lonLo) || double.IsNaN(_orHi) || double.IsNaN(_orLo)) return;

                double p = Close[0];
                int d = (p > _lonHi && p > vwap) ? 1 : ((p < _lonLo && p < vwap) ? -1 : 0);
                if (d == 0) return;

                double st = d == 1 ? _orLo : _orHi;
                double riskPts = d * (p - st);
                if (!(riskPts > 0)) return;

                int q = ComputeContracts(riskPts);
                if (q < 1) return;

                _pendingSide = d;
                _pendingStopPx = st;
                _pendingRiskPts = riskPts;
                _exitReasonHint = null;
                if (d == 1) EnterLong(q, SigL);
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
                _activeStopPx = _pendingStopPx;
                _activeRiskPts = _activeSide * (_entryPx - _activeStopPx);
                if (_activeRiskPts <= 0)
                {
                    _activeRiskPts = Math.Max(_pendingRiskPts, _spec.Tick);
                    _exitReasonHint = "INVALIDA";
                    if (_activeSide == 1) ExitLong("FR_inv", SigL); else ExitShort("FR_inv", SigS);
                    return;
                }
                _activeTargetPx = TpR > 0 ? (_entryPx + _activeSide * TpR * _activeRiskPts) : double.NaN;
                if (_activeSide == 1)
                {
                    ExitLongStopMarket(0, true, _activeQty, FundedSyncMath.RoundTick(_activeStopPx, _spec.Tick), "FR_stop", SigL);
                    if (!double.IsNaN(_activeTargetPx))
                        ExitLongLimit(0, true, _activeQty, FundedSyncMath.RoundTick(_activeTargetPx, _spec.Tick), "FR_obj", SigL);
                }
                else
                {
                    ExitShortStopMarket(0, true, _activeQty, FundedSyncMath.RoundTick(_activeStopPx, _spec.Tick), "FR_stop", SigS);
                    if (!double.IsNaN(_activeTargetPx))
                        ExitShortLimit(0, true, _activeQty, FundedSyncMath.RoundTick(_activeTargetPx, _spec.Tick), "FR_obj", SigS);
                }
            }
            else if (Position.MarketPosition == MarketPosition.Flat && _activeQty > 0)
            {
                double exPx = execution.Order.AverageFillPrice;
                double pnlPts = _activeSide * (exPx - _entryPx);
                double rBruto = pnlPts / Math.Max(_activeRiskPts, 1e-6);
                double rNet = (pnlPts - _spec.FrictionPts) / Math.Max(_activeRiskPts, 1e-6);
                string reason = !string.IsNullOrEmpty(_exitReasonHint) ? _exitReasonHint
                    : (oname == "FR_stop" ? "STOP" : (oname == "FR_obj" ? "TARGET" : oname));
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
                string mod = EnableVetoPreapertura ? "Franklin_VetoPreap" : "Franklin";
                int fechaInt = _entryNy.Year * 10000 + _entryNy.Month * 100 + _entryNy.Day;
                double rRealUsd = _activeRiskPts * _activeQty * _spec.PointValue;
                double rObjUsd = ContratosFijos > 0 ? rRealUsd : Risk1R_USD;
                string line = string.Format(CultureInfo.InvariantCulture,
                    "{0},LIVE,{1},1.000000,{2},{3},{4},{5:F2},{6:F4},{7:F4},{8:F4},{9:F2},{10:F6},{11:F6},{12},{13},{14:F2},{15:F2},{16:F2}",
                    fechaInt, mod, _activeSide,
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
        [NinjaScriptProperty] [Display(Name = "Veto PREAPERTURA (noche alta)", Order = 2, GroupName = "01. Estrategia y activo")] public bool EnableVetoPreapertura { get; set; }
        [NinjaScriptProperty] [Range(0.0, 10.0)] [Display(Name = "Objetivo TP en R (0 = cierre 16:00)", Order = 3, GroupName = "01. Estrategia y activo")] public double TpR { get; set; }
        [NinjaScriptProperty] [Range(10.0, 10000.0)] [Display(Name = "Riesgo 1R USD", Order = 4, GroupName = "02. Riesgo")] public double Risk1R_USD { get; set; }
        [NinjaScriptProperty] [Range(1, 200)] [Display(Name = "Max contratos", Order = 5, GroupName = "02. Riesgo")] public int MaxContracts { get; set; }
        [NinjaScriptProperty] [Range(0, 50)] [Display(Name = "Contratos fijos (0 = por riesgo)", Order = 6, GroupName = "02. Riesgo")] public int ContratosFijos { get; set; }
        [NinjaScriptProperty] [Display(Name = "Veto de noticias", Order = 10, GroupName = "03. Noticias")] public bool EnableNewsVeto { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes", Order = 11, GroupName = "03. Noticias")] public double NewsBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues", Order = 12, GroupName = "03. Noticias")] public double NewsAfterMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos antes FOMC", Order = 13, GroupName = "03. Noticias")] public double FomcBeforeMin { get; set; }
        [NinjaScriptProperty] [Range(0, 60)] [Display(Name = "Minutos despues FOMC", Order = 14, GroupName = "03. Noticias")] public double FomcAfterMin { get; set; }
        [NinjaScriptProperty] [Display(Name = "Guardar CSV en candidatas", Order = 20, GroupName = "04. Salida")] public bool EnableCsvLog { get; set; }
        #endregion
    }
}
