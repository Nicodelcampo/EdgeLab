#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeGold0415 - celda congelada de la etapa B/C (docs/research/barrido_horario_20261004/PREREGISTRO_ETAPA_C_GC_SPOT.md):
// franja 04:15 hora de Chicago, dias habiles. Condicion: close(barra que cierra 04:16) - close(barra que cierra 04:01) > 0.
// Accion: CORTO a mercado a las 04:17 (franja + 2 min), salida por tiempo 15 min despues (04:32). Sin stop ni objetivo.
// Requisitos: MGC o GC, grafico de 1 minuto, Calculate = On bar close, zona horaria de NT8 = Central (o ajustar Hhmm).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeGold0415 : Strategy
    {
        private bool armed;          // la condicion se cumplio en la barra de las 04:16
        private DateTime exitAt;     // hora de cierre de barra en la que se manda la salida

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeGold0415";
                Description = "Corto 04:17 CT tras subida de los 15 min previos, salida 15 min. Exploratorio.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 20;
                Contracts = 1;
                SlotHhmm = 415;
                HoldMinutes = 15;
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 16) return;
            DateTime t = Time[0];                         // NT8: hora de CIERRE de la barra
            DateTime slot = t.Date.AddHours(SlotHhmm / 100).AddMinutes(SlotHhmm % 100);
            // Una orden a mercado enviada al cierre de la barra de las hh:mm se llena en la apertura de la siguiente (~hh:mm:00).
            if (Position.MarketPosition == MarketPosition.Short && t >= exitAt)
            {
                ExitShort(Contracts, "G0415x", "G0415");   // al cierre de 04:32 -> fill ~04:32
                return;
            }
            if (t.DayOfWeek == DayOfWeek.Saturday || t.DayOfWeek == DayOfWeek.Sunday) return;

            if (t == slot.AddMinutes(1))                  // barra que cierra 04:16
                armed = Close[0] - Close[15] > 0;         // contra la barra que cierra 04:01 (subida estricta)
            else if (t == slot.AddMinutes(2))             // barra que cierra 04:17 -> fill ~04:17 = franja + 2 min
            {
                if (armed && Position.MarketPosition == MarketPosition.Flat)
                {
                    EnterShort(Contracts, "G0415");
                    exitAt = t.AddMinutes(HoldMinutes);   // 04:32
                }
                armed = false;
            }
        }

        [NinjaScriptProperty, Range(1, int.MaxValue)]
        [Display(Name = "Contracts", Order = 1, GroupName = "Parameters")]
        public int Contracts { get; set; }

        [NinjaScriptProperty, Range(0, 2359)]
        [Display(Name = "Slot (hhmm, hora del chart)", Order = 2, GroupName = "Parameters")]
        public int SlotHhmm { get; set; }

        [NinjaScriptProperty, Range(1, 240)]
        [Display(Name = "Hold (min)", Order = 3, GroupName = "Parameters")]
        public int HoldMinutes { get; set; }
    }
}
