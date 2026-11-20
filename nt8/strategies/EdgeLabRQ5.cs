#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabRQ5 (version=1.0, 2026-11-20) — banda de ruido intradía (Zarattini, Aziz y Barbon 2024), fábrica de RQ5-REGIMEN.
// No es un edge promovido: REGIMEN_ROBUSTO en desarrollo 2018–2025 (+0,050 R, p 0,045), holdout A5 NO_CONCLUYENTE (+0,027 R, p 0,23).
// Sirve para paper/forward. Operar con dinero real lo decide Nico.
//
// Especificación: edgelab/research/rq5_regimen.py (eventos + FABRICA) y edgelab/research/ejecucion.py (PRECIOS con fin).
//   Sesión RTH de NY: velas M1 que ABREN en [09:30, 16:00) ET (en NT8, Time = cierre: [09:31, 16:00]).
//   ab = apertura de la primera vela RTH. VWAP «típico» = media simple acumulada de (H+L+C)/3 de las velas RTH (sin volumen).
//   ATR del día = media de los True Range diarios RTH de las 20 sesiones previas (≥ 3; si no, rango del día previo).
//   Al cierre de las velas de las 10:00, 10:30, 11:00 y 11:30 ET (y 12:00, que sólo alimenta su historia):
//     mv = |cierre − ab|; banda = media de los últimos L mv de ESE mismo horario (≥ 10 sesiones de historia).
//     Señal si mv ≥ m × banda y el cierre está del lado del VWAP (largo: cierre ≥ VWAP; corto: cierre ≤ VWAP); la primera del día.
//     El mv de cada horario se agrega a su historia todos los días, haya señal o no.
//   Entrada a mercado en la apertura de la vela siguiente. d = max(s × ATR, 0,5 × banda); stop = cierre − lado·d; objetivo = cierre + lado·tp·d.
//   Si el llenado ya pasó el stop o el objetivo, Python descarta la operación: acá se cierra en el acto y se registra INVALIDA.
//   Salida por reloj: cierre de la vela de las 16:00 ET (en Python, cierre de la vela que abre 15:59 — mismo precio).
//   Fábrica: L 60, m 1,0, corte 11:30, s 0,45, tp 2. 1 R = |entrada − stop|.
// Tamaño: RiesgoUSD > 0 → contratos = piso(RiesgoUSD / (d × PointValue)) entre 1 y MaxContratos (omite si da 0); si no, Cantidad.
// Fricción (opcional, CLAUDE.md M1): no opera si FriccionPuntos / d > FriccionMaxR. Canónicas (edgelab/costos.py): NQ 1,5455, MNQ 1,9775,
// ES 0,8877, MES 1,155, YM 5,052, MYM 7,49, RTY 0,4436 puntos por viaje.
//
// Gráfico de 1 minuto (ETH o RTH), Calculate = OnBarClose, zona horaria cualquiera (convierte a ET).
// Paridad: docs/research/nt8_rq5_20261120/RQ5_NQ_REFERENCIA_PARIDAD.csv (señales de Python, NQ 2025-01 → 2025-07). La ventana Output
// imprime una línea «RQ5;SEÑAL;…» por señal para compararla (fecha, hora de cierre ET, lado, cierre, stop, objetivo).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabRQ5 : Strategy
    {
        private static readonly int[] Slots = { 600, 630, 660, 690, 720 };   // minuto ET del CIERRE de la vela (10:00 … 12:00)
        private TimeZoneInfo et;
        private DateTime rthFecha = DateTime.MinValue;
        private bool hayDia, hayPrevio;
        private double ab, hi, lo, cl, sumTp, atrDia = double.NaN;
        private int nTp;
        private double prevCierre = double.NaN, prevHi, prevLo;
        private readonly Queue<double> trs = new Queue<double>();
        private readonly Dictionary<int, List<double>> hist = new Dictionary<int, List<double>>();
        private bool senalHoy;
        private int lado;
        private double stopPx, objPx;
        private const string SigL = "RQ5L", SigS = "RQ5S";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabRQ5";
                Description = "RQ5 (banda de ruido intradía, fábrica de RQ5-REGIMEN). Paper/forward. No es un edge promovido.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 1;
                L = 60; M = 1.0; CorteHHMM = 1130; S = 0.45; Tp = 2.0;
                Cantidad = 1; RiesgoUSD = 0; MaxContratos = 10;
                FriccionPuntos = 0; FriccionMaxR = 0.08;
            }
            else if (State == State.Configure)
            {
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                foreach (int s in Slots) hist[s] = new List<double>();
            }
        }

        private DateTime AEt(DateTime t) { return TimeZoneInfo.ConvertTime(t, Core.Globals.GeneralOptions.TimeZoneInfo, et); }

        private void CerrarDia()
        {
            if (!hayDia) return;
            double tr = hayPrevio ? Math.Max(hi - lo, Math.Max(Math.Abs(hi - prevCierre), Math.Abs(lo - prevCierre))) : hi - lo;
            trs.Enqueue(tr); while (trs.Count > 20) trs.Dequeue();
            prevCierre = cl; prevHi = hi; prevLo = lo; hayPrevio = true; hayDia = false;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1) return;
            DateTime t = AEt(Time[0]);
            int minCierre = t.Hour * 60 + t.Minute;
            bool rth = minCierre >= 571 && minCierre <= 960;

            // salida por reloj: la vela que cierra a las 16:00 ET; en días de cierre anticipado, la última vela de la sesión (Python sale
            // con la última vela del tramo continuo); y nunca de un día para otro.
            if (Position.MarketPosition != MarketPosition.Flat && (minCierre == 960 || Bars.IsLastBarOfSession || (rthFecha != DateTime.MinValue && t.Date != rthFecha && minCierre > 960)))
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("RQ5_cierre", SigL); else ExitShort("RQ5_cierre", SigS);
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
            if (!senalHoy && minCierre <= corte && h.Count >= 10 && !double.IsNaN(atrDia) && atrDia > 0
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
                    Print(string.Format("RQ5;SEÑAL;{0:yyyy-MM-dd};{0:HH:mm};{1};{2};{3:F4};{4:F4};{5:F4}", t, lado, ck, stopPx, objPx, atrDia));
                    int q = Cantidad;
                    if (RiesgoUSD > 0) q = Math.Min(MaxContratos, (int)Math.Floor(RiesgoUSD / (d * Instrument.MasterInstrument.PointValue)));
                    if (q < 1) { Print("RQ5;OMITIDA;tamaño < 1 contrato"); }
                    else if (FriccionPuntos > 0 && FriccionPuntos / d > FriccionMaxR) { Print(string.Format("RQ5;OMITIDA;fricción {0:F3} R", FriccionPuntos / d)); }
                    else if (lado == 1) EnterLong(q, SigL); else EnterShort(q, SigS);
                }
            }
            h.Add(mv); if (h.Count > 90) h.RemoveAt(0);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            string n = execution.Order.Name;
            if (n != SigL && n != SigS) return;
            double e = execution.Order.AverageFillPrice;
            bool invalida = lado * (e - stopPx) <= 0 || (!double.IsNaN(objPx) && lado * (objPx - e) <= 0);
            if (invalida)
            {
                Print(string.Format("RQ5;INVALIDA;{0:F2}", e));
                if (lado == 1) ExitLong("RQ5_invalida", SigL); else ExitShort("RQ5_invalida", SigS);
                return;
            }
            Print(string.Format("RQ5;ENTRADA;{0};{1:F2};riesgo {2:F2} pts", lado, e, Math.Abs(e - stopPx)));
            int q = execution.Order.Filled;
            if (lado == 1)
            {
                ExitLongStopMarket(0, true, q, stopPx, "RQ5_stop", SigL);
                if (!double.IsNaN(objPx)) ExitLongLimit(0, true, q, objPx, "RQ5_obj", SigL);
            }
            else
            {
                ExitShortStopMarket(0, true, q, stopPx, "RQ5_stop", SigS);
                if (!double.IsNaN(objPx)) ExitShortLimit(0, true, q, objPx, "RQ5_obj", SigS);
            }
        }

        #region Properties
        [NinjaScriptProperty, Range(10, 90), Display(Name = "L (sesiones de la banda)", Order = 1, GroupName = "RQ5")]
        public int L { get; set; }
        [NinjaScriptProperty, Range(0.1, 5), Display(Name = "m (ancho de banda)", Order = 2, GroupName = "RQ5")]
        public double M { get; set; }
        [NinjaScriptProperty, Display(Name = "Corte (HHMM ET, cierre de vela)", Order = 3, GroupName = "RQ5")]
        public int CorteHHMM { get; set; }
        [NinjaScriptProperty, Range(0.05, 5), Display(Name = "s (stop en ATR)", Order = 4, GroupName = "RQ5")]
        public double S { get; set; }
        [NinjaScriptProperty, Range(0, 10), Display(Name = "tp (objetivo en d; 0 = sólo cierre)", Order = 5, GroupName = "RQ5")]
        public double Tp { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Cantidad fija", Order = 6, GroupName = "Tamaño")]
        public int Cantidad { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Riesgo USD por operación (0 = cantidad fija)", Order = 7, GroupName = "Tamaño")]
        public double RiesgoUSD { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Máx. contratos", Order = 8, GroupName = "Tamaño")]
        public int MaxContratos { get; set; }
        [NinjaScriptProperty, Range(0, 100), Display(Name = "Fricción por viaje (puntos; 0 = no filtra)", Order = 9, GroupName = "Tamaño")]
        public double FriccionPuntos { get; set; }
        [NinjaScriptProperty, Range(0, 1), Display(Name = "Fricción máx. (R)", Order = 10, GroupName = "Tamaño")]
        public double FriccionMaxR { get; set; }
        #endregion
    }
}
