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
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabRQ5 (version=1.1, 2026-11-25) - banda de ruido intradia (Zarattini, Aziz y Barbon 2024), fabrica de RQ5-REGIMEN.
// Actualizada con selector de Activo (FundedSyncActivo), veto de noticias tier-1 (NewsVetoCalendar) y export CSV a EdgeLab\candidatas\.
namespace NinjaTrader.NinjaScript.Strategies
{
    using EdgeLabFundedSync;

    public class EdgeLabRQ5 : Strategy
    {
        private static readonly int[] Slots = { 600, 630, 660, 690, 720 };   // minuto ET del CIERRE de la vela (10:00 ... 12:00)
        private TimeZoneInfo _chartTz, et;
        private NewsVetoCalendar _newsCal;
        private FundedSyncAssetSpec _spec;
        private string _csvPath;
        private bool _csvHeaderWritten, _blocked;

        private DateTime rthFecha = DateTime.MinValue;
        private bool hayDia, hayPrevio;
        private double ab, hi, lo, cl, sumTp, atrDia = double.NaN;
        private int nTp;
        private double prevCierre = double.NaN, prevHi, prevLo;
        private readonly Queue<double> trs = new Queue<double>();
        private readonly Dictionary<int, List<double>> hist = new Dictionary<int, List<double>>();
        private bool senalHoy;
        private int lado, _activeQty;
        private double stopPx, objPx, _entryPx, _activeRiskPts;
        private DateTime _entryNy;
        private string _exitReasonHint;
        private const string SigL = "RQ5L", SigS = "RQ5S";

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
                Name = "EdgeLabRQ5";
                Description = "RQ5 (banda de ruido intradia, fabrica de RQ5-REGIMEN). Selector de activo, veto noticias y log CSV.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true; ExitOnSessionCloseSeconds = 1200;   // plano 20 min antes del fin de sesion (16:40 ET; 12:40 en cierres tempranos): Lucid no admite noches
                BarsRequiredToTrade = 1;
                L = 60; M = 1.0; CorteHHMM = 1130; S = 0.45; Tp = 2.0;
                Activo = FundedSyncActivo.MNQ;
                Cantidad = 1; RiesgoUSD = 0; MaxContratos = 10;
                FriccionPuntos = 0; FriccionMaxR = 0.08;
                EnableNewsVeto = true;
                NewsBeforeMin = 2.0; NewsAfterMin = 2.0; FomcBeforeMin = 5.0; FomcAfterMin = 5.0;
                EnableCsvLog = true;
            }
            else if (State == State.Configure)
            {
                et = FundedSyncMath.ResolveTz("Eastern Standard Time");
                _chartTz = Core.Globals.GeneralOptions.TimeZoneInfo ?? TimeZoneInfo.Local;
                foreach (int s in Slots) hist[s] = new List<double>();
            }
            else if (State == State.DataLoaded)
            {
                _spec = FundedSyncAssets.Get(Activo);
                string master = (Instrument != null && Instrument.MasterInstrument != null) ? Instrument.MasterInstrument.Name : "";
                if (!FundedSyncAssets.ChartMatches(Activo, master))
                {
                    _blocked = true;
                    Print("EdgeLabRQ5 BLOQUEADA: grafico=" + master + ", Activo=" + _spec.Root);
                    return;
                }
                if (Activo == FundedSyncActivo.YM || Activo == FundedSyncActivo.MYM)
                {
                    if (!EsCuentaSimulada(Account))
                    {
                        _blocked = true;
                        Print("EdgeLabRQ5 BLOQUEADA: YM negativo en RQ5-REGIMEN; solo Sim/Playback.");
                        return;
                    }
                }
                if (FriccionPuntos <= 0) FriccionPuntos = _spec.FrictionPts;

                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "candidatas");
                Directory.CreateDirectory(dir);
                _csvPath = Path.Combine(dir, "RQ5_" + _spec.Root + ".csv");
                if (EnableCsvLog && File.Exists(_csvPath)) File.Delete(_csvPath);

                if (EnableNewsVeto)
                {
                    _newsCal = new NewsVetoCalendar(
                        Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "noticias", "calendario_usd_tier1.csv"),
                        NewsBeforeMin, NewsAfterMin, FomcBeforeMin, FomcAfterMin);
                    Print("EdgeLabRQ5 news veto: " + _newsCal.Status);
                }
            }
        }

        private DateTime AEt(DateTime t, out DateTime utc)
        {
            DateTime chartLocal = DateTime.SpecifyKind(t, DateTimeKind.Unspecified);
            utc = _chartTz.Id == TimeZoneInfo.Utc.Id
                ? DateTime.SpecifyKind(chartLocal, DateTimeKind.Utc)
                : TimeZoneInfo.ConvertTimeToUtc(chartLocal, _chartTz);
            return TimeZoneInfo.ConvertTimeFromUtc(utc, et);
        }

        private void CerrarDia()
        {
            if (!hayDia) return;
            double tr = hayPrevio ? Math.Max(hi - lo, Math.Max(Math.Abs(hi - prevCierre), Math.Abs(lo - prevCierre))) : hi - lo;
            trs.Enqueue(tr); while (trs.Count > 20) trs.Dequeue();
            prevCierre = cl; prevHi = hi; prevLo = lo; hayPrevio = true; hayDia = false;
        }

        protected override void OnBarUpdate()
        {
            if (_blocked || BarsInProgress != 0 || BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1) return;
            DateTime utc;
            DateTime t = AEt(Time[0], out utc);
            int minCierre = t.Hour * 60 + t.Minute;
            bool rth = minCierre >= 571 && minCierre <= 960;
            bool inNews = EnableNewsVeto && _newsCal != null && _newsCal.BlocksAt(utc);

            if (Position.MarketPosition != MarketPosition.Flat)
            {
                if (inNews)
                {
                    _exitReasonHint = "NEWS_VETO";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("RQ5_news", SigL); else ExitShort("RQ5_news", SigS);
                    return;
                }
                if (minCierre == 960 || Bars.IsLastBarOfSession || (rthFecha != DateTime.MinValue && t.Date != rthFecha && minCierre > 960))
                {
                    _exitReasonHint = "EOD_CLOSE";
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong("RQ5_cierre", SigL); else ExitShort("RQ5_cierre", SigS);
                }
            }
            if (!rth) return;

            if (t.Date != rthFecha)
            {
                CerrarDia();
                rthFecha = t.Date; hayDia = true; senalHoy = false;
                ab = Open[0]; hi = High[0]; lo = Low[0]; sumTp = 0; nTp = 0;
                atrDia = trs.Count >= 3 ? trs.Average() : (hayPrevio ? prevHi - prevLo : double.NaN);
            }
            hi = Math.Max(hi, High[0]); lo = Math.Min(lo, Low[0]); cl = Close[0];
            sumTp += (High[0] + Low[0] + Close[0]) / 3.0; nTp++;
            double vwap = sumTp / nTp;

            if (!hist.ContainsKey(minCierre)) return;
            List<double> h = hist[minCierre];
            double ck = Close[0], mv = Math.Abs(ck - ab);
            int corte = (CorteHHMM / 100) * 60 + CorteHHMM % 100;
            if (!inNews && !senalHoy && minCierre <= corte && h.Count >= 10 && !double.IsNaN(atrDia) && atrDia > 0
                && Position.MarketPosition == MarketPosition.Flat)
            {
                double banda = h.Skip(Math.Max(0, h.Count - L)).Average();
                int ld = ck > ab ? 1 : -1;
                bool vwOk = (ld == 1 && ck >= vwap) || (ld == -1 && ck <= vwap);
                if (banda > 0 && mv >= M * banda && vwOk)
                {
                    senalHoy = true;
                    double d = Math.Max(S * atrDia, 0.5 * banda);
                    lado = ld; stopPx = ck - lado * d; objPx = Tp > 0 ? ck + lado * Tp * d : double.NaN;
                    int q = Cantidad;
                    if (RiesgoUSD > 0) q = Math.Min(MaxContratos, (int)Math.Floor(RiesgoUSD / (d * _spec.PointValue)));
                    if (q < 1) { Print("RQ5;OMITIDA;tamano < 1 contrato"); }
                    else if (FriccionPuntos > 0 && FriccionPuntos / d > FriccionMaxR) { Print(string.Format("RQ5;OMITIDA;friccion {0:F3} R", FriccionPuntos / d)); }
                    else
                    {
                        _exitReasonHint = null;
                        if (lado == 1) EnterLong(q, SigL); else EnterShort(q, SigS);
                    }
                }
            }
            h.Add(mv); if (h.Count > 90) h.RemoveAt(0);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (_blocked || execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            DateTime utc;
            DateTime ny = AEt(time, out utc);
            string n = execution.Order.Name;
            if (n == SigL || n == SigS)
            {
                double e = execution.Order.AverageFillPrice;
                bool invalida = lado * (e - stopPx) <= 0 || (!double.IsNaN(objPx) && lado * (objPx - e) <= 0);
                if (invalida)
                {
                    _activeQty = execution.Order.Filled;
                    _entryPx = e;
                    _entryNy = ny;
                    _activeRiskPts = Math.Max(Math.Abs(e - stopPx), _spec.Tick);
                    _exitReasonHint = "INVALIDA";
                    if (lado == 1) ExitLong("RQ5_invalida", SigL); else ExitShort("RQ5_invalida", SigS);
                    return;
                }
                _activeQty = execution.Order.Filled;
                _entryPx = e;
                _entryNy = ny;
                _activeRiskPts = Math.Abs(e - stopPx);
                if (lado == 1)
                {
                    ExitLongStopMarket(0, true, _activeQty, FundedSyncMath.RoundTick(stopPx, _spec.Tick), "RQ5_stop", SigL);
                    if (!double.IsNaN(objPx)) ExitLongLimit(0, true, _activeQty, FundedSyncMath.RoundTick(objPx, _spec.Tick), "RQ5_obj", SigL);
                }
                else
                {
                    ExitShortStopMarket(0, true, _activeQty, FundedSyncMath.RoundTick(stopPx, _spec.Tick), "RQ5_stop", SigS);
                    if (!double.IsNaN(objPx)) ExitShortLimit(0, true, _activeQty, FundedSyncMath.RoundTick(objPx, _spec.Tick), "RQ5_obj", SigS);
                }
            }
            else if (Position.MarketPosition == MarketPosition.Flat && _activeQty > 0)
            {
                double exPx = execution.Order.AverageFillPrice;
                double pnlPts = lado * (exPx - _entryPx);
                double rBruto = pnlPts / Math.Max(_activeRiskPts, 1e-6);
                double rNet = (pnlPts - _spec.FrictionPts) / Math.Max(_activeRiskPts, 1e-6);
                string reason = !string.IsNullOrEmpty(_exitReasonHint) ? _exitReasonHint
                    : (n == "RQ5_stop" ? "STOP" : (n == "RQ5_obj" ? "TARGET" : n));
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
                double rObjUsd = RiesgoUSD > 0 ? RiesgoUSD : rRealUsd;
                string line = string.Format(CultureInfo.InvariantCulture,
                    "{0},LIVE,RQ5,1.000000,{1},{2},{3},{4:F2},{5:F4},{6:F4},{7:F4},{8:F2},{9:F6},{10:F6},{11},{12},{13:F2},{14:F2},{15:F2}",
                    fechaInt, lado,
                    _entryNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    exitNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    _entryPx, stopPx, exitPx, _activeRiskPts, pnlPts, rBruto, rNet, reason,
                    _activeQty, _spec.PointValue, rRealUsd, rObjUsd);
                File.AppendAllText(_csvPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        #region Properties
        [NinjaScriptProperty] [Display(Name = "Activo", Order = 0, GroupName = "RQ5")] public FundedSyncActivo Activo { get; set; }
        [NinjaScriptProperty, Range(10, 90), Display(Name = "L (sesiones de la banda)", Order = 1, GroupName = "RQ5")] public int L { get; set; }
        [NinjaScriptProperty, Range(0.1, 5), Display(Name = "m (ancho de banda)", Order = 2, GroupName = "RQ5")] public double M { get; set; }
        [NinjaScriptProperty, Display(Name = "Corte (HHMM ET, cierre de vela)", Order = 3, GroupName = "RQ5")] public int CorteHHMM { get; set; }
        [NinjaScriptProperty, Range(0.05, 5), Display(Name = "s (stop en ATR)", Order = 4, GroupName = "RQ5")] public double S { get; set; }
        [NinjaScriptProperty, Range(0, 10), Display(Name = "tp (objetivo en d; 0 = solo cierre)", Order = 5, GroupName = "RQ5")] public double Tp { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Cantidad fija", Order = 6, GroupName = "Tamano")] public int Cantidad { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Riesgo USD por operacion (0 = cantidad fija)", Order = 7, GroupName = "Tamano")] public double RiesgoUSD { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Max. contratos", Order = 8, GroupName = "Tamano")] public int MaxContratos { get; set; }
        [NinjaScriptProperty, Range(0, 100), Display(Name = "Friccion por viaje (puntos; 0 = auto activo)", Order = 9, GroupName = "Tamano")] public double FriccionPuntos { get; set; }
        [NinjaScriptProperty, Range(0, 1), Display(Name = "Friccion max. (R)", Order = 10, GroupName = "Tamano")] public double FriccionMaxR { get; set; }
        [NinjaScriptProperty] [Display(Name = "Veto de noticias", Order = 11, GroupName = "Noticias")] public bool EnableNewsVeto { get; set; }
        [NinjaScriptProperty, Range(0, 60)] [Display(Name = "Minutos antes", Order = 12, GroupName = "Noticias")] public double NewsBeforeMin { get; set; }
        [NinjaScriptProperty, Range(0, 60)] [Display(Name = "Minutos despues", Order = 13, GroupName = "Noticias")] public double NewsAfterMin { get; set; }
        [NinjaScriptProperty, Range(0, 60)] [Display(Name = "Minutos antes FOMC", Order = 14, GroupName = "Noticias")] public double FomcBeforeMin { get; set; }
        [NinjaScriptProperty, Range(0, 60)] [Display(Name = "Minutos despues FOMC", Order = 15, GroupName = "Noticias")] public double FomcAfterMin { get; set; }
        [NinjaScriptProperty] [Display(Name = "Guardar CSV en candidatas", Order = 20, GroupName = "Salida")] public bool EnableCsvLog { get; set; }
        #endregion
    }
}
