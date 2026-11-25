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

    public enum Carril2Modulo { C2_VZ = 0, C2_EVRP = 1 }

    /// <summary>
    /// EdgeLab candidata: CARRIL2-LOTE2 (C2_VZ y C2_EVRP), Swing multi-dia en ES/NQ.
    /// Regla Python exacta: tools/carril2.py::_senales2.
    /// Requiere Documents\NinjaTrader 8\EdgeLab\datos\cboe_vol_diario.csv (generado con tools/exportar_vix_nt8.py).
    /// CSV: Documents\NinjaTrader 8\EdgeLab\candidatas\<C2_VZ|C2_EVRP>_<Activo>.csv.
    /// </summary>
    public class EdgeLabCandidataCarril2 : Strategy
    {
        private struct VolRow { public double Vix, Vxn, Vix9d; }

        private TimeZoneInfo _chartTz, _nyTz;
        private NewsVetoCalendar _newsCal;
        private FundedSyncAssetSpec _spec;
        private string _csvPath;
        private bool _csvHeaderWritten, _blocked;

        // Volatilidad CBOE ordenada por fecha
        private readonly List<DateTime> _volDates = new List<DateTime>();
        private readonly List<VolRow> _volRows = new List<VolRow>();

        // Barra D1 CME en curso (18:00 NY -> 17:00 NY dia habil siguiente)
        private DateTime _curDay = DateTime.MinValue;
        private DateTime _lastClosedDay = DateTime.MinValue;
        private double _dHi = double.NaN, _dLo = double.NaN, _dCl = double.NaN;
        private double _prevDailyClose = double.NaN;
        private readonly Queue<double> _tr20 = new Queue<double>();
        private readonly Queue<double> _logRets10 = new Queue<double>();
        private readonly Queue<double> _iv6 = new Queue<double>();
        private readonly Queue<double> _v9_6 = new Queue<double>();

        // Posicion y conteo de barras diarias en posicion
        private int _barsHeld;
        private double _pendingRiskPts;
        private int _activeQty;
        private DateTime _entryNy;
        private double _entryPx, _activeStopPx, _activeRiskPts;
        private string _exitReasonHint;

        private const string SigL = "C2_L";

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
                Description = "EdgeLab candidata: CARRIL2 C2_VZ (compresion VIX z-score) y C2_EVRP (prima de riesgo vol).";
                Name = "EdgeLabCandidataCarril2";
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

                Modulo = Carril2Modulo.C2_VZ;
                Activo = FundedSyncActivo.NQ;
                Risk1R_USD = 2000.0;
                MaxContracts = 20;
                ContratosFijos = 1;
                EnableNewsVeto = true;
                NewsBeforeMin = 2.0; NewsAfterMin = 2.0; FomcBeforeMin = 5.0; FomcAfterMin = 5.0;
                EnableCsvLog = true;
                VolCsvPath = "";
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
                    Print("EdgeLabCandidataCarril2 BLOQUEADA: grafico=" + master + ", Activo=" + _spec.Root);
                    return;
                }
                if (Activo != FundedSyncActivo.NQ && Activo != FundedSyncActivo.MNQ
                    && Activo != FundedSyncActivo.ES && Activo != FundedSyncActivo.MES && !EsCuentaSimulada(Account))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataCarril2 BLOQUEADA: evidencia solo en ES/NQ; resto Sim/Playback.");
                    return;
                }

                string vp = string.IsNullOrWhiteSpace(VolCsvPath)
                    ? Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "datos", "cboe_vol_diario.csv")
                    : VolCsvPath.Trim();
                if (!LoadCboeCsv(vp))
                {
                    _blocked = true;
                    Print("EdgeLabCandidataCarril2 BLOQUEADA: falta CSV CBOE en " + vp + " (correr tools/exportar_vix_nt8.py)");
                    return;
                }

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "candidatas");
                Directory.CreateDirectory(dir);
                _csvPath = Path.Combine(dir, Modulo + "_" + _spec.Root + ".csv");
                if (EnableCsvLog && File.Exists(_csvPath)) File.Delete(_csvPath);

                if (EnableNewsVeto)
                {
                    _newsCal = new NewsVetoCalendar(
                        Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    Print("EdgeLabCandidataCarril2 news veto: " + _newsCal.Status);
                }
            }
        }

        private bool LoadCboeCsv(string path)
        {
            _volDates.Clear(); _volRows.Clear();
            if (!File.Exists(path)) return false;
            string[] lines = File.ReadAllLines(path);
            for (int i = 1; i < lines.Length; i++)
            {
                string[] c = lines[i].Split(',');
                if (c.Length < 4) continue;
                DateTime dt;
                if (!DateTime.TryParseExact(c[0].Trim(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out dt)) continue;
                double vix = ParseOrNaN(c[1]), vxn = ParseOrNaN(c[2]), v9 = ParseOrNaN(c[3]);
                _volDates.Add(dt);
                _volRows.Add(new VolRow { Vix = vix, Vxn = vxn, Vix9d = v9 });
            }
            return _volDates.Count > 0;
        }

        private static double ParseOrNaN(string s)
        {
            double v;
            return double.TryParse(s.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : double.NaN;
        }

        private bool LookupVol(DateTime sessionDate, out VolRow row)
        {
            row = default(VolRow);
            if (_volDates.Count == 0) return false;
            int idx = _volDates.BinarySearch(sessionDate);
            if (idx < 0) idx = (~idx) - 1;
            if (idx < 0) return false;
            row = _volRows[idx];
            return true;
        }

        private static double ZScore6(Queue<double> q)
        {
            if (q.Count < 6) return double.NaN;
            double sum = 0.0;
            foreach (double x in q) { if (double.IsNaN(x)) return double.NaN; sum += x; }
            double mean = sum / q.Count;
            double ss = 0.0, last = 0.0;
            foreach (double x in q) { ss += (x - mean) * (x - mean); last = x; }
            double sd = Math.Sqrt(ss / (q.Count - 1));
            return sd > 1e-12 ? (last - mean) / sd : double.NaN;
        }

        private int ComputeContracts(double riskPts)
        {
            if (ContratosFijos > 0) return ContratosFijos;
            double r1Usd = Math.Max(riskPts * _spec.PointValue, 1e-6);
            int q = (int)Math.Min(MaxContracts, Math.Max(0, Math.Round(Risk1R_USD / r1Usd)));
            if (q == 0 && Risk1R_USD >= 0.55 * r1Usd) q = 1;
            return q;
        }

        private void OnDailyBarClosed(DateTime closedDay, bool inNews)
        {
            if (closedDay == DateTime.MinValue || closedDay == _lastClosedDay || double.IsNaN(_dCl)) return;
            _lastClosedDay = closedDay;

            double tr = !double.IsNaN(_prevDailyClose)
                ? Math.Max(_dHi - _dLo, Math.Max(Math.Abs(_dHi - _prevDailyClose), Math.Abs(_dLo - _prevDailyClose)))
                : (_dHi - _dLo);
            _tr20.Enqueue(tr);
            if (_tr20.Count > 20) _tr20.Dequeue();

            if (!double.IsNaN(_prevDailyClose) && _prevDailyClose > 0 && _dCl > 0)
            {
                _logRets10.Enqueue(Math.Log(_dCl / _prevDailyClose));
                if (_logRets10.Count > 10) _logRets10.Dequeue();
            }
            _prevDailyClose = _dCl;

            VolRow vr;
            if (!LookupVol(closedDay, out vr)) return;
            bool isNq = Activo == FundedSyncActivo.NQ || Activo == FundedSyncActivo.MNQ;
            double iv = isNq ? vr.Vxn : vr.Vix;
            _iv6.Enqueue(iv); if (_iv6.Count > 6) _iv6.Dequeue();
            _v9_6.Enqueue(vr.Vix9d); if (_v9_6.Count > 6) _v9_6.Dequeue();

            if (_tr20.Count < 20) return;
            double atr20 = _tr20.Average();
            if (!(atr20 > 0)) return;

            bool sigCond = false;
            double slMult = 1.25;
            int topeBarras = 10;

            if (Modulo == Carril2Modulo.C2_VZ)
            {
                double zIv = ZScore6(_iv6), zV9 = ZScore6(_v9_6);
                if (double.IsNaN(zIv) || double.IsNaN(zV9)) return;
                double cz = 0.5 * (zIv + zV9);
                sigCond = cz < -1.0;
                slMult = 1.25;
                topeBarras = 10;
            }
            else
            {
                if (_logRets10.Count < 10 || double.IsNaN(iv) || double.IsNaN(vr.Vix) || double.IsNaN(vr.Vix9d) || vr.Vix <= 0) return;
                double sumR = 0.0; foreach (double r in _logRets10) sumR += r;
                double mR = sumR / _logRets10.Count;
                double ssR = 0.0; foreach (double r in _logRets10) ssR += (r - mR) * (r - mR);
                double rv10 = Math.Sqrt(ssR / (_logRets10.Count - 1)) * Math.Sqrt(252.0) * 100.0;
                double evrp = iv - rv10;
                double cont = vr.Vix9d / vr.Vix;
                sigCond = (evrp > 0.0) && (cont < 1.0);
                slMult = 2.0;
                topeBarras = 20;
            }

            if (Position.MarketPosition == MarketPosition.Long)
            {
                _barsHeld++;
                if (!sigCond || _barsHeld >= topeBarras)
                {
                    _exitReasonHint = !sigCond ? "SALIDA_COND" : "SALIDA_TOPE";
                    ExitLong("C2_exit", SigL);
                }
                return;
            }

            if (sigCond && !inNews && Position.MarketPosition == MarketPosition.Flat)
            {
                double riskPts = slMult * atr20;
                int q = ComputeContracts(riskPts);
                if (q < 1) return;
                _pendingRiskPts = riskPts;
                _barsHeld = 0;
                _exitReasonHint = null;
                EnterLong(q, SigL);
            }
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
            DateTime td = openNy.AddHours(6).Date;
            if (td.DayOfWeek == DayOfWeek.Saturday || td.DayOfWeek == DayOfWeek.Sunday) return;

            bool inNews = EnableNewsVeto && _newsCal != null && _newsCal.BlocksAt(closeUtc);
            if (Position.MarketPosition == MarketPosition.Long && inNews)
            {
                _exitReasonHint = "NEWS_VETO";
                ExitLong("C2_news", SigL);
                return;
            }

            // Si salto al siguiente dia sin haber cerrado el anterior (gap/feriado)
            if (_curDay != DateTime.MinValue && td != _curDay)
            {
                OnDailyBarClosed(_curDay, inNews);
                _curDay = DateTime.MinValue;
            }

            if (_curDay != td)
            {
                _curDay = td;
                _dHi = High[0]; _dLo = Low[0]; _dCl = Close[0];
            }
            else
            {
                _dHi = Math.Max(_dHi, High[0]);
                _dLo = Math.Min(_dLo, Low[0]);
                _dCl = Close[0];
            }

            // Cierre de barra diaria CME: 17:00 NY (o ultima vela de la sesion en cierres anticipados)
            int closeMinNy = closeNy.Hour * 60 + closeNy.Minute;
            if ((closeMinNy == 1020 && closeNy.Date == _curDay) || Bars.IsLastBarOfSession)
            {
                OnDailyBarClosed(_curDay, inNews);
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

            if (oname == SigL)
            {
                _activeQty = execution.Order.Filled;
                _entryPx = execution.Order.AverageFillPrice;
                _entryNy = ny;
                _activeRiskPts = _pendingRiskPts;
                _activeStopPx = FundedSyncMath.RoundTick(_entryPx - _activeRiskPts, _spec.Tick);
                ExitLongStopMarket(0, true, _activeQty, _activeStopPx, "C2_stop", SigL);
            }
            else if (marketPosition == MarketPosition.Flat && _activeQty > 0)
            {
                double exPx = execution.Order.AverageFillPrice;
                double pnlPts = exPx - _entryPx;
                double rBruto = pnlPts / Math.Max(_activeRiskPts, 1e-6);
                double rNet = (pnlPts - _spec.FrictionPts) / Math.Max(_activeRiskPts, 1e-6);
                string reason = !string.IsNullOrEmpty(_exitReasonHint) ? _exitReasonHint : (oname == "C2_stop" ? "STOP" : oname);
                WriteCsvRow(ny, exPx, pnlPts, rBruto, rNet, reason);
                _activeQty = 0;
                _barsHeld = 0;
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
                    "{0},LIVE,{1},1.000000,1,{2},{3},{4:F2},{5:F4},{6:F4},{7:F4},{8:F2},{9:F6},{10:F6},{11},{12},{13:F2},{14:F2},{15:F2}",
                    fechaInt, Modulo.ToString(),
                    _entryNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    exitNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    _entryPx, _activeStopPx, exitPx, _activeRiskPts, pnlPts, rBruto, rNet, reason,
                    _activeQty, _spec.PointValue, rRealUsd, rObjUsd);
                File.AppendAllText(_csvPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        #region NinjaScript Properties
        [NinjaScriptProperty] [Display(Name = "Modulo Carril2", Order = 1, GroupName = "01. Estrategia y activo")] public Carril2Modulo Modulo { get; set; }
        [NinjaScriptProperty] [Display(Name = "Activo", Order = 2, GroupName = "01. Estrategia y activo")] public FundedSyncActivo Activo { get; set; }
        [NinjaScriptProperty] [Display(Name = "CSV CBOE (vacio = defecto)", Order = 3, GroupName = "01. Estrategia y activo")] public string VolCsvPath { get; set; }
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
