#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeReplica - reimplementacion independiente (modelo empirico validado 577/577 DEC26
// y 337/337 SEP26 en Python). NO usa ni carga la DLL original ni ninguna licencia.
// Requisitos: MNQ, grafico de 1 minuto, Trading hours "CME US Index Futures ETH",
// Calculate = On bar close (el valor por defecto de esta estrategia).
// Reglas (60): dia, hora base (Chicago), direccion, hold (min), COND (signo del cambio
// de close de los 15 min previos; 0 = sin filtro).
// Nombres de ordenes identicos a los del export original (EXPERIMENT-n / EXPERIMENT-nx)
// para poder comparar el Grid directamente con el original.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeReplica : Strategy
    {
        private sealed class RuleDef
        {
            public readonly int Id, Dow, Hhmm, Dir, Hold, Cond;
            public RuleDef(int id, int dow, int hhmm, int dir, int hold, int cond)
            { Id = id; Dow = dow; Hhmm = hhmm; Dir = dir; Hold = hold; Cond = cond; }
        }

        private sealed class Pos
        {
            public RuleDef Rule;
            public DateTime Submission;   // hora de la barra donde se envio la entrada (inicio de HOLD)
        }

        private sealed class Order_
        {
            public bool IsExit;
            public RuleDef Rule;
            public DateTime Signal;
        }

        private static readonly RuleDef[] Rules = new RuleDef[]
        {
            new RuleDef(1, 4, 115, 1, 15, -1),
            new RuleDef(2, 4, 1015, -1, 15, 1),
            new RuleDef(3, 1, 445, 1, 30, -1),
            new RuleDef(4, 1, 1700, -1, 60, 0),
            new RuleDef(5, 2, 1030, 1, 30, -1),
            new RuleDef(6, 4, 400, 1, 30, -1),
            new RuleDef(7, 1, 1715, -1, 30, -1),
            new RuleDef(8, 1, 145, 1, 60, 0),
            new RuleDef(9, 4, 100, 1, 30, 0),
            new RuleDef(10, 4, 815, -1, 30, 0),
            new RuleDef(11, 5, 1500, -1, 30, 0),
            new RuleDef(12, 3, 1830, 1, 60, 0),
            new RuleDef(13, 4, 745, -1, 60, 1),
            new RuleDef(14, 2, 730, -1, 15, 1),
            new RuleDef(15, 1, 200, 1, 60, 0),
            new RuleDef(16, 0, 1445, 1, 60, -1),
            new RuleDef(17, 3, 915, 1, 15, 1),
            new RuleDef(18, 4, 1445, 1, 60, -1),
            new RuleDef(19, 5, 330, -1, 15, 0),
            new RuleDef(20, 1, 1730, -1, 60, -1),
            new RuleDef(21, 1, 130, 1, 60, 1),
            new RuleDef(22, 0, 45, 1, 60, 1),
            new RuleDef(23, 3, 1845, 1, 60, -1),
            new RuleDef(24, 2, 2215, 1, 60, -1),
            new RuleDef(25, 1, 700, 1, 60, 0),
            new RuleDef(26, 3, 1145, 1, 15, 0),
            new RuleDef(27, 0, 1145, 1, 60, 1),
            new RuleDef(28, 3, 1945, 1, 60, -1),
            new RuleDef(29, 2, 2030, 1, 15, -1),
            new RuleDef(30, 1, 230, 1, 15, -1),
            new RuleDef(31, 1, 715, 1, 60, 1),
            new RuleDef(32, 4, 645, -1, 15, 1),
            new RuleDef(33, 1, 1430, 1, 30, 1),
            new RuleDef(34, 0, 1345, -1, 60, 1),
            new RuleDef(35, 2, 1830, 1, 15, 0),
            new RuleDef(36, 3, 1900, 1, 60, 0),
            new RuleDef(37, 4, 1330, -1, 60, 1),
            new RuleDef(38, 2, 1230, 1, 30, 1),
            new RuleDef(39, 1, 730, 1, 30, -1),
            new RuleDef(40, 1, 1415, 1, 60, -1),
            new RuleDef(41, 4, 800, -1, 30, 0),
            new RuleDef(42, 5, 1145, 1, 60, 1),
            new RuleDef(43, 1, 415, 1, 15, 1),
            new RuleDef(44, 3, 1315, 1, 30, -1),
            new RuleDef(45, 1, 215, 1, 30, 0),
            new RuleDef(46, 1, 645, -1, 15, 1),
            new RuleDef(47, 2, 1745, 1, 60, 0),
            new RuleDef(48, 5, 1515, -1, 15, 0),
            new RuleDef(49, 2, 2145, -1, 15, -1),
            new RuleDef(50, 3, 600, 1, 15, 1),
            new RuleDef(51, 1, 630, -1, 30, 1),
            new RuleDef(52, 4, 2230, -1, 15, 1),
            new RuleDef(53, 4, 2330, -1, 30, -1),
            new RuleDef(54, 5, 315, -1, 30, 1),
            new RuleDef(55, 5, 1300, -1, 60, 1),
            new RuleDef(56, 4, 30, 1, 60, 0),
            new RuleDef(57, 0, 1300, -1, 15, 1),
            new RuleDef(58, 5, 430, 1, 15, -1),
            new RuleDef(59, 2, 1800, 1, 60, 1),
            new RuleDef(60, 5, 445, -1, 30, -1)
        };

        private readonly Dictionary<int, List<RuleDef>> schedule = new Dictionary<int, List<RuleDef>>();
        private readonly Dictionary<int, Pos> positions = new Dictionary<int, Pos>();   // regla -> posicion "logica"
        private readonly List<RuleDef> pendingEntries = new List<RuleDef>();            // senal en b1, envio en b2
        private readonly List<Order_> submitted = new List<Order_>();                   // enviadas en la barra previa
        private readonly HashSet<string> lastFired = new HashSet<string>();
        private static readonly DateTime DataFloor = new DateTime(2024, 1, 1);
        private SessionIterator sessionIterator;
        private TimeZoneInfo chicago;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Reimplementacion independiente EdgeReplica (modelo empirico, 60 reglas)";
                Name = "EdgeReplica";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 60;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 0;
                IsInstantiatedOnEachOptimizationIteration = true;
                Contracts = 1;
                SessionMargin = 0;
            }
            else if (State == State.Configure)
            {
                schedule.Clear();
                foreach (RuleDef r in Rules)
                {
                    List<RuleDef> l;
                    if (!schedule.TryGetValue(r.Hhmm, out l)) { l = new List<RuleDef>(); schedule[r.Hhmm] = l; }
                    l.Add(r);
                }
                try { chicago = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time"); }
                catch { chicago = TimeZoneInfo.FindSystemTimeZoneById("America/Chicago"); }
            }
            else if (State == State.DataLoaded)
            {
                sessionIterator = new SessionIterator(Bars);
                positions.Clear(); pendingEntries.Clear(); submitted.Clear(); lastFired.Clear();
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 1)
                return;

            DateTime now = Time[0];

            // 1) "Fills": las ordenes enviadas en la barra previa se ejecutaron al open de esta barra.
            //    Se espeja el simulador: salida antes que entrada; una entrada contraria cierra las opuestas
            //    (NinjaTrader invierte la posicion por si mismo; aqui solo se actualiza el estado logico).
            foreach (Order_ o in submitted)
            {
                if (o.IsExit)
                {
                    positions.Remove(o.Rule.Id);
                }
                else
                {
                    List<int> toClose = new List<int>();
                    foreach (KeyValuePair<int, Pos> kv in positions)
                        if (kv.Value.Rule.Dir != o.Rule.Dir) toClose.Add(kv.Key);
                    foreach (int id in toClose) positions.Remove(id);
                    // la hora de envio (inicio de HOLD) se guardo en Signal -> ver paso 3
                    positions[o.Rule.Id] = new Pos { Rule = o.Rule, Submission = o.Signal };
                }
            }
            submitted.Clear();

            // 2) Salidas por HOLD: primera barra con timestamp >= envio + HOLD -> orden para el open siguiente.
            List<RuleDef> exitsNow = new List<RuleDef>();
            foreach (KeyValuePair<int, Pos> kv in positions)
                if (now >= kv.Value.Submission.AddMinutes(kv.Value.Rule.Hold))
                    exitsNow.Add(kv.Value.Rule);
            foreach (RuleDef r in exitsNow)
            {
                string entryName = "EXPERIMENT-" + r.Id;
                string exitName = "EXPERIMENT-" + r.Id + "x";
                if (r.Dir > 0) ExitLong(Contracts, exitName, entryName);
                else ExitShort(Contracts, exitName, entryName);
                submitted.Add(new Order_ { IsExit = true, Rule = r });
            }

            // 3) Entradas pendientes (senal en la barra previa): se envian ahora, fill al open siguiente.
            foreach (RuleDef r in pendingEntries)
            {
                string entryName = "EXPERIMENT-" + r.Id;
                if (r.Dir > 0) EnterLong(Contracts, entryName);
                else EnterShort(Contracts, entryName);
                submitted.Add(new Order_ { IsExit = false, Rule = r, Signal = now });
            }
            pendingEntries.Clear();

            // 4) Senales nuevas. La barra con timestamp = HHMM + 1 minuto (hora Chicago) es b1.
            if (CurrentBar < BarsRequiredToTrade)
                return;
            DateTime local = TimeZoneInfo.ConvertTime(now.AddMinutes(-1), NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo, chicago);
            if (local.Date < DataFloor.Date || local.DayOfWeek == DayOfWeek.Saturday || local.DayOfWeek == DayOfWeek.Sunday)
                return;
            int hm = local.Hour * 100 + local.Minute;
            List<RuleDef> due;
            if (!schedule.TryGetValue(hm, out due))
                return;

            int isoDow = local.DayOfWeek == DayOfWeek.Sunday ? 7 : (int)local.DayOfWeek;
            foreach (RuleDef r in due)
            {
                if (r.Dow != 0 && r.Dow != isoDow) continue;
                string key = r.Id + "|" + local.ToString("yyyy-MM-dd");
                if (lastFired.Contains(key)) continue;

                // Cambio de close contra la ultima barra con timestamp <= ahora - 15 min (minutos de reloj).
                int sign = 0; bool hasRef = false;
                DateTime limit = now.AddMinutes(-15);
                for (int i = 1; i <= CurrentBar && i < 5000; i++)
                {
                    if (Time[i] <= limit)
                    {
                        double delta = Close[0] - Close[i];
                        sign = delta > 0 ? 1 : (delta < 0 ? -1 : 0);
                        hasRef = true;
                        break;
                    }
                }

                // Tiempo restante de sesion (plantilla ETH, incluye feriados / cierres anticipados).
                sessionIterator.GetNextSession(now, true);
                double remaining = (sessionIterator.ActualSessionEnd - now).TotalMinutes;
                bool permitted = sessionIterator.ActualSessionEnd >= now && remaining >= r.Hold + SessionMargin;
                bool passes = r.Cond == 0 || (hasRef && sign == r.Cond);

                if (permitted && passes)
                {
                    pendingEntries.Add(r);
                    lastFired.Add(key);
                }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts per trade", Order = 1, GroupName = "Parameters")]
        public int Contracts { get; set; }

        [NinjaScriptProperty]
        [Range(0, 120)]
        [Display(Name = "Session margin (min, extra a HOLD)", Order = 2, GroupName = "Parameters")]
        public int SessionMargin { get; set; }
        #endregion
    }
}
