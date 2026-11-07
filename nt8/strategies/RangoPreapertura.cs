#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// RangoPreapertura — traducción de las celdas PREAPERTURA-ES y PREAPERTURA-NQ.
// No es un edge promovido. No abre el holdout. Sirve para simulación y paper.
//
// Regla, igual que edgelab/research/rango_ruptura.py y rango_preapertura.py:
//   rango = máximo y mínimo de las velas de 1 minuto que cierran en (09:15, 09:30] ET
//   (hace falta al menos 12 de esas 15 velas);
//   primer quiebre = primer cierre fuera de ese rango hasta las 11:30 ET;
//   reentrada = si después de ese quiebre el precio toca la mitad del rango, el
//   siguiente cierre fuera, en cualquier dirección, también hasta las 11:30;
//   stop = un tick más allá del borde opuesto del rango;
//   salida forzada al cierre de la vela de las 15:55 ET.
//
// Intento 0 = primer quiebre (PREAPERTURA-ES). Intento 1 = sólo la reentrada (PREAPERTURA-NQ).
// El tercil de ancho/ATR de la celda publicada no se aplica: los cortes del E0 no están archivados.
// Cuerpo, volumen y eficiencia quedan en «cualquiera», que es lo que dice la coordenada.
//
// Gráfico de 1 minuto de ES o NQ. Calculate = On bar close.
// La entrada a mercado al cierre de la vela de señal se llena en la vela siguiente.
// Eso aproxima «el tick siguiente» del simulador; no es el fill de tick.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class RangoPreapertura : Strategy
    {
        private TimeZoneInfo et;
        private DateTime dia = DateTime.MinValue;
        private int fase;                 // 0 busca el primero, 1 espera el medio, 2 busca la reentrada, 3 día cerrado
        private int lado1;
        private int velasRango;
        private double rHi, rLo, rMid;
        private bool enRango;
        private string entrada;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "RangoPreapertura";
                Description = "Rango 09:16-09:30 ET, stop en el borde opuesto, salida 15:55 ET. Paper. No es un edge promovido.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 20;
                Contratos = 1;
                Intento = 0;
            }
            else if (State == State.DataLoaded)
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
        }

        private DateTime AEt(DateTime t)
        {
            return TimeZoneInfo.ConvertTime(t, Core.Globals.GeneralOptions.TimeZoneInfo, et);
        }

        private void ResetDia(DateTime fecha)
        {
            dia = fecha.Date;
            fase = 0;
            lado1 = 0;
            velasRango = 0;
            rHi = 0;
            rLo = 0;
            rMid = 0;
            enRango = false;
            entrada = null;
        }

        private void Entrar(int lado)
        {
            if (Position.MarketPosition != MarketPosition.Flat || lado != 1 && lado != -1) return;
            if (fase == 0 && Intento != 0) return;
            if (fase == 2 && Intento != 1) return;
            double tick = TickSize;
            if (lado == 1)
            {
                double stop = Math.Floor(rLo / tick) * tick - tick;
                if (Close[0] - stop < tick) return;
                entrada = "RPl";
                EnterLong(Contratos, entrada);
                ExitLongStopMarket(0, true, Contratos, stop, "RPsl", entrada);
            }
            else
            {
                double stop = Math.Ceiling(rHi / tick) * tick + tick;
                if (stop - Close[0] < tick) return;
                entrada = "RPs";
                EnterShort(Contratos, entrada);
                ExitShortStopMarket(0, true, Contratos, stop, "RPsl", entrada);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 1) return;
            DateTime e = AEt(Time[0]);
            if (e.DayOfWeek == DayOfWeek.Saturday || e.DayOfWeek == DayOfWeek.Sunday) return;
            if (e.Date != dia) ResetDia(e);
            int hm = e.Hour * 100 + e.Minute;

            if (hm >= 1555)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong(Contratos, "RPx", entrada);
                else if (Position.MarketPosition == MarketPosition.Short) ExitShort(Contratos, "RPx", entrada);
                fase = 3;
                return;
            }

            if (fase == 3 || hm <= 915) return;

            if (hm <= 930)
            {
                if (!enRango) { rHi = High[0]; rLo = Low[0]; enRango = true; }
                else { rHi = Math.Max(rHi, High[0]); rLo = Math.Min(rLo, Low[0]); }
                velasRango++;
                if (hm == 930)
                {
                    rMid = (rHi + rLo) / 2.0;
                    if (velasRango < 12 || !(rHi > rLo)) fase = 3;
                }
                return;
            }

            if (!enRango || fase == 3 || hm > 1130) return;

            if (fase == 1)
            {
                if ((lado1 == 1 && Low[0] <= rMid) || (lado1 == -1 && High[0] >= rMid)) fase = 2;
                return;
            }
            if (fase != 0 && fase != 2) return;

            int lado = Close[0] > rHi ? 1 : (Close[0] < rLo ? -1 : 0);
            if (lado == 0) return;
            Entrar(lado);
            if (fase == 0) { fase = 1; lado1 = lado; }
            else fase = 3;
        }

        [NinjaScriptProperty, Range(1, 50)]
        [Display(Name = "Contratos", Order = 1, GroupName = "Parameters")]
        public int Contratos { get; set; }

        [NinjaScriptProperty, Range(0, 1)]
        [Display(Name = "Intento (0 primer quiebre ES, 1 reentrada NQ)", Order = 2, GroupName = "Parameters")]
        public int Intento { get; set; }
    }
}
