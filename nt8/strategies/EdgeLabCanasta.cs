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

// EdgeLabCanasta (version=1.0, 2026-11-20) — une en una sola estrategia y una sola cuenta:
//   1. RQ5 (misma regla que EdgeLabRQ5.cs) en el instrumento del gráfico (NQ/MNQ) y, opcional, en otros índices (Extras: «ES 12-26;YM 12-26»).
//      Por defecto sólo NQ: CANASTA-CORRELACION (docs/research/canasta_correlacion_20261120/RESULTADO.md) mostró que RQ5 en ES/YM/RTY suma
//      varianza (peor mes −21 R) más que R por mes.
//   2. Guarda de CUENTA para una cuenta prop (Lucid): mira el P&L de TODA la cuenta —incluidas las operaciones de otras estrategias en la
//      misma cuenta, p. ej. T, Z, R y A20 corriendo en FundedSync con su licencia— y:
//        - DLL: si el P&L del día (realizado desde las 18:00 ET + abierto) ≤ −PerdidaDiariaUSD, cierra todas las posiciones de la cuenta y
//          no abre más RQ5 ese día (y vuelve a cerrar si otra estrategia reabre);
//        - piso de cuenta: si el valor líquido ≤ PisoCuentaUSD + MargenPisoUSD, cierra todo y se bloquea hasta reiniciar;
//        - plano obligatorio: a las HoraPlano ET (Lucid: 16:45) cierra todo lo de la cuenta.
// T, Z y A20 NO se reimplementan acá: su lógica sale del IL desensamblado de un producto comercial con licencia (FundedSync). Se corren en
// el producto original. R de FundedSync con stop de catástrofe ya existía en EdgeLabAtrPhaseStop.cs.
// Tamaño de referencia a 1 R por operación. A20 NO va en la canasta a 1 R: no cubre y cuadruplica la caída máxima (−23 → −90 R).
// No es un edge promovido. Paper/forward. Operar con dinero real lo decide Nico.
// Gráfico de 1 minuto del instrumento principal, Calculate = OnBarClose.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabCanasta : Strategy
    {
        private class Rq5
        {
            public string Sig;
            public DateTime Fecha = DateTime.MinValue;
            public bool HayDia, HayPrevio, SenalHoy;
            public double Ab, Hi, Lo, Cl, SumTp, Atr = double.NaN, PrevCierre = double.NaN, PrevHi, PrevLo, Stop, Obj;
            public int NTp, Lado;
            public readonly Queue<double> Trs = new Queue<double>();
            public readonly Dictionary<int, List<double>> Hist = new Dictionary<int, List<double>>();
        }

        private static readonly int[] Slots = { 600, 630, 660, 690, 720 };
        private TimeZoneInfo et;
        private readonly List<Rq5> est = new List<Rq5>();
        private DateTime diaGuarda = DateTime.MinValue;
        private double realizadoBase;
        private bool bloqueoDia, bloqueoTotal;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabCanasta";
                Description = "RQ5 en NQ (+ índices opcionales) con guarda de cuenta (DLL, piso, plano 16:45 ET). Paper/forward.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 1;
                Extras = "";
                L = 60; M = 1.0; CorteHHMM = 1130; S = 0.45; Tp = 2.0;
                RiesgoUSD = 200; MaxContratos = 10;
                PerdidaDiariaUSD = 600; PisoCuentaUSD = 0; MargenPisoUSD = 100; HoraPlano = 1645;
            }
            else if (State == State.Configure)
            {
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                foreach (string x in (Extras ?? "").Split(';').Select(s => s.Trim()).Where(s => s.Length > 0))
                    AddDataSeries(x, BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
            {
                for (int i = 0; i < BarsArray.Length; i++)
                {
                    var r = new Rq5 { Sig = "RQ5_" + i };
                    foreach (int s in Slots) r.Hist[s] = new List<double>();
                    est.Add(r);
                }
            }
        }

        private DateTime AEt(DateTime t) { return TimeZoneInfo.ConvertTime(t, Core.Globals.GeneralOptions.TimeZoneInfo, et); }

        // ---------------------------------------------------------------- guarda de cuenta
        private double PnlDia()
        {
            double abierto = 0;
            lock (Account.Positions)
                foreach (Position p in Account.Positions)
                    if (p.MarketPosition != MarketPosition.Flat) abierto += p.GetUnrealizedProfitLoss(PerformanceUnit.Currency);
            return Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar) - realizadoBase + abierto;
        }

        private void AplanarCuenta(string motivo)
        {
            var ins = new List<Instrument>();
            lock (Account.Positions)
                foreach (Position p in Account.Positions)
                    if (p.MarketPosition != MarketPosition.Flat) ins.Add(p.Instrument);
            if (ins.Count == 0) return;
            Print(string.Format("CANASTA;APLANAR;{0};{1}", motivo, string.Join(",", ins.Select(i => i.FullName))));
            Account.Flatten(ins);
        }

        private void Guarda(DateTime t)
        {
            if (State != State.Realtime) return;                               // la guarda usa la cuenta real: sólo en tiempo real
            DateTime diaCme = t.Hour >= 18 ? t.Date.AddDays(1) : t.Date;       // el día de trading empieza a las 18:00 ET
            if (diaCme != diaGuarda)
            {
                diaGuarda = diaCme; bloqueoDia = false;
                realizadoBase = Account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
            }
            if (PerdidaDiariaUSD > 0 && PnlDia() <= -PerdidaDiariaUSD) { bloqueoDia = true; AplanarCuenta("DLL"); }
            else if (bloqueoDia) AplanarCuenta("DLL (reapertura de otra estrategia)");
            if (PisoCuentaUSD > 0 && Account.Get(AccountItem.NetLiquidation, Currency.UsDollar) <= PisoCuentaUSD + MargenPisoUSD)
            { bloqueoTotal = true; AplanarCuenta("PISO"); }
            int hp = (HoraPlano / 100) * 60 + HoraPlano % 100, m = t.Hour * 60 + t.Minute;
            if (HoraPlano > 0 && m >= hp && m < 18 * 60) AplanarCuenta("PLANO " + HoraPlano);
        }

        // ---------------------------------------------------------------- RQ5 por instrumento
        private static void CerrarDia(Rq5 r)
        {
            if (!r.HayDia) return;
            double tr = r.HayPrevio ? Math.Max(r.Hi - r.Lo, Math.Max(Math.Abs(r.Hi - r.PrevCierre), Math.Abs(r.Lo - r.PrevCierre))) : r.Hi - r.Lo;
            r.Trs.Enqueue(tr); while (r.Trs.Count > 20) r.Trs.Dequeue();
            r.PrevCierre = r.Cl; r.PrevHi = r.Hi; r.PrevLo = r.Lo; r.HayPrevio = true; r.HayDia = false;
        }

        protected override void OnBarUpdate()
        {
            int b = BarsInProgress;
            if (b >= est.Count) return;
            Rq5 r = est[b];
            DateTime t = AEt(Times[b][0]);
            int minCierre = t.Hour * 60 + t.Minute;
            if (b == 0) Guarda(t);

            if (Positions[b].MarketPosition != MarketPosition.Flat && (minCierre == 960 || BarsArray[b].IsLastBarOfSession || minCierre > 960))
            {
                if (Positions[b].MarketPosition == MarketPosition.Long) ExitLong(b, Positions[b].Quantity, "RQ5_cierre", r.Sig);
                else ExitShort(b, Positions[b].Quantity, "RQ5_cierre", r.Sig);
            }
            if (minCierre < 571 || minCierre > 960) return;

            if (t.Date != r.Fecha)
            {
                CerrarDia(r);
                r.Fecha = t.Date; r.HayDia = true; r.SenalHoy = false;
                r.Ab = Opens[b][0]; r.Hi = Highs[b][0]; r.Lo = Lows[b][0]; r.SumTp = 0; r.NTp = 0;
                r.Atr = r.Trs.Count >= 3 ? r.Trs.Average() : (r.HayPrevio ? r.PrevHi - r.PrevLo : double.NaN);
            }
            r.Hi = Math.Max(r.Hi, Highs[b][0]); r.Lo = Math.Min(r.Lo, Lows[b][0]); r.Cl = Closes[b][0];
            r.SumTp += (Highs[b][0] + Lows[b][0] + Closes[b][0]) / 3.0; r.NTp++;
            double vwap = r.SumTp / r.NTp;

            if (!r.Hist.ContainsKey(minCierre)) return;
            List<double> h = r.Hist[minCierre];
            double ck = Closes[b][0], mv = Math.Abs(ck - r.Ab);
            int corte = (CorteHHMM / 100) * 60 + CorteHHMM % 100;
            if (!r.SenalHoy && minCierre <= corte && h.Count >= 10 && !double.IsNaN(r.Atr) && r.Atr > 0
                && Positions[b].MarketPosition == MarketPosition.Flat)
            {
                double banda = h.Skip(Math.Max(0, h.Count - L)).Average();
                int ld = ck > r.Ab ? 1 : -1;
                bool vwOk = (ld == 1 && ck >= vwap) || (ld == -1 && ck <= vwap);
                if (banda > 0 && mv >= M * banda && vwOk)
                {
                    r.SenalHoy = true;
                    double d = Math.Max(S * r.Atr, 0.5 * banda);
                    r.Lado = ld; r.Stop = ck - ld * d; r.Obj = Tp > 0 ? ck + ld * Tp * d : double.NaN;
                    Print(string.Format("RQ5;SEÑAL;{0};{1:yyyy-MM-dd};{1:HH:mm};{2};{3:F4};{4:F4};{5:F4}",
                        Instruments[b].FullName, t, ld, ck, r.Stop, r.Obj));
                    int q = Math.Min(MaxContratos, (int)Math.Floor(RiesgoUSD / (d * Instruments[b].MasterInstrument.PointValue)));
                    if (bloqueoDia || bloqueoTotal) Print("RQ5;OMITIDA;guarda de cuenta");
                    else if (q < 1) Print("RQ5;OMITIDA;tamaño < 1 contrato");
                    else if (ld == 1) EnterLong(b, q, r.Sig); else EnterShort(b, q, r.Sig);
                }
            }
            h.Add(mv); if (h.Count > 90) h.RemoveAt(0);
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                                  MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            int b = est.FindIndex(x => x.Sig == execution.Order.Name);
            if (b < 0) return;
            Rq5 r = est[b];
            double e = execution.Order.AverageFillPrice; int q = execution.Order.Filled;
            if (r.Lado * (e - r.Stop) <= 0 || (!double.IsNaN(r.Obj) && r.Lado * (r.Obj - e) <= 0))
            {
                Print(string.Format("RQ5;INVALIDA;{0};{1:F2}", Instruments[b].FullName, e));
                if (r.Lado == 1) ExitLong(b, q, "RQ5_invalida", r.Sig); else ExitShort(b, q, "RQ5_invalida", r.Sig);
                return;
            }
            Print(string.Format("RQ5;ENTRADA;{0};{1};{2:F2};riesgo {3:F2} pts", Instruments[b].FullName, r.Lado, e, Math.Abs(e - r.Stop)));
            if (r.Lado == 1)
            {
                ExitLongStopMarket(b, true, q, r.Stop, "RQ5_stop", r.Sig);
                if (!double.IsNaN(r.Obj)) ExitLongLimit(b, true, q, r.Obj, "RQ5_obj", r.Sig);
            }
            else
            {
                ExitShortStopMarket(b, true, q, r.Stop, "RQ5_stop", r.Sig);
                if (!double.IsNaN(r.Obj)) ExitShortLimit(b, true, q, r.Obj, "RQ5_obj", r.Sig);
            }
        }

        #region Properties
        [NinjaScriptProperty, Display(Name = "Índices extra (p. ej. «ES 12-26;YM 12-26»; vacío = sólo el gráfico)", Order = 0, GroupName = "Canasta")]
        public string Extras { get; set; }
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
        [NinjaScriptProperty, Range(1, 100000), Display(Name = "Riesgo USD por operación (1 R)", Order = 6, GroupName = "Tamaño")]
        public double RiesgoUSD { get; set; }
        [NinjaScriptProperty, Range(1, 1000), Display(Name = "Máx. contratos", Order = 7, GroupName = "Tamaño")]
        public int MaxContratos { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Pérdida diaria de la cuenta (USD; 0 = sin DLL)", Order = 8, GroupName = "Guarda de cuenta")]
        public double PerdidaDiariaUSD { get; set; }
        [NinjaScriptProperty, Range(0, 10000000), Display(Name = "Piso de la cuenta (USD; 0 = sin piso)", Order = 9, GroupName = "Guarda de cuenta")]
        public double PisoCuentaUSD { get; set; }
        [NinjaScriptProperty, Range(0, 100000), Display(Name = "Margen sobre el piso (USD)", Order = 10, GroupName = "Guarda de cuenta")]
        public double MargenPisoUSD { get; set; }
        [NinjaScriptProperty, Display(Name = "Hora de plano (HHMM ET; 0 = no)", Order = 11, GroupName = "Guarda de cuenta")]
        public int HoraPlano { get; set; }
        #endregion
    }
}
