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

// EdgeLabAtrPhaseStop — módulo R (AtrPhase) de FundedSync con el stop de catástrofe que validó EdgeLab.
// No es un edge promovido. No abre el holdout. Sirve para paper/forward y, si Nico lo decide, para operar R con stop
// (el DLL del vendedor NO tiene stop para R: docs/research/regimen_forward_20261119/ADENDA_POTENCIA.md).
//
// Especificación: edgelab/research/fundedsyncstack/modulos_r_z_e_q.py (run_r, _AtrPhaseEngine), traducción exacta del IL.
//   Serie de decisión: velas de 10 minutos ETH (plantilla CME US Index Futures ETH).
//   EMA(21) del cierre (semilla = primer cierre); ATR(14) de Wilder sobre el True Range de 10 min (semilla = media de los 14 primeros TR).
//   Oscilador crudo = 100 · (cierre − EMA21) / (3 · ATR14); suavizado = 0,5 · crudo + 0,5 · anterior.
//   Cruce alcista: anterior <= +100 y actual > +100; bajista: anterior >= −100 y actual < −100.
//   Ventana de entrada: velas de 10 min que CIERRAN en [09:30, 11:00) ET. VWAP de la sesión ET con las velas que ABREN en [09:30, 16:00):
//   entra sólo si |cierre − VWAP| < 2,5 · ATR14. Reversa dentro de la ventana; fuera de la ventana un cruce opuesto cierra.
//   Cierre de contado: la vela de 10 min que cierra a las 16:00 ET cierra todo.
//   Reinicio por vencimiento: vela que abre 00:00 UTC con |apertura − cierre previo| > 400 ticks reinicia el estado.
//   Entradas y salidas a mercado: se llenan en la apertura de la vela de 1 minuto siguiente (igual que el simulador).
// Agregado de EdgeLab (NETO-PISTAS, REGIMEN_ROBUSTO 81/81, PBO 0,23): stop de catástrofe a 0,25 × ATR20 desde el precio de entrada, donde
// ATR20 = media de los rangos (máximo − mínimo) de las 20 sesiones CME previas (sesión desde las 18:00 ET), igual que tools/m1_largo.py::atr20.
// La lista de fechas bloqueadas del vendedor está desactivada por defecto (versión operable; auditoría AUDITORIA-EXCLUSIONES: inocua).
//
// Gráfico de 1 minuto de NQ o MNQ, plantilla ETH. Calculate = On bar close. Paridad: comparar con
// docs/research/regimen_forward_20261119/R_REFERENCIA_PARIDAD.csv (operaciones del simulador en Python) antes de usarla.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabAtrPhaseStop : Strategy
    {
        private TimeZoneInfo et;
        // estado del indicador (serie de 10 min)
        private bool prevCloseReady, oscReady, atrReady, emaReady;
        private double trSeedSum, prevDecisionClose, osc, atr14, ema21;
        private int trSeedCount, shadowSide, pendingReversal;
        private DateTime vwapDate = DateTime.MinValue;
        private double vwapVol, vwapPv;
        // ATR20 de sesión CME (serie de 1 min)
        private DateTime sesionActual = DateTime.MinValue;
        private double sesHi = double.MinValue, sesLo = double.MaxValue;
        private readonly Queue<double> rangos = new Queue<double>();
        private double atr20 = double.NaN;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabAtrPhaseStop";
                Description = "R (AtrPhase) de FundedSync con stop de catástrofe 0,25 × ATR20 de sesión. Paper. No es un edge promovido.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 20;
                Contratos = 1;
                MultiploStop = 0.25;
                UsarFechasVendedor = false;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Minute, 10);
            }
            else if (State == State.DataLoaded)
            {
                et = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
            }
        }

        private static readonly HashSet<int> FechasVendedor = new HashSet<int> { 20220803, 20220830, 20230405, 20240704, 20241224, 20250120, 20250703, 20250829 };

        private DateTime AEt(DateTime t) { return TimeZoneInfo.ConvertTime(t, TimeZoneInfo.Local, et); }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 0) { BarraUnMinuto(); return; }
            if (BarsInProgress == 1 && CurrentBars[1] >= 1) BarraDiezMinutos();
        }

        // ---- 1 minuto: ATR20 de sesión CME y envío de órdenes pedidas ----
        private void BarraUnMinuto()
        {
            DateTime tEt = AEt(Times[0][0]);
            DateTime abreEt = tEt.AddMinutes(-1);
            DateTime ses = abreEt.AddHours(6).Date;               // sesión CME: desde las 18:00 ET es el día siguiente
            if (ses != sesionActual)
            {
                if (sesionActual != DateTime.MinValue && sesHi > sesLo)
                {
                    rangos.Enqueue(sesHi - sesLo);
                    while (rangos.Count > 20) rangos.Dequeue();
                }
                atr20 = rangos.Count == 20 ? rangos.Average() : double.NaN;   // 20 sesiones PREVIAS (causal)
                sesionActual = ses; sesHi = double.MinValue; sesLo = double.MaxValue;
            }
            sesHi = Math.Max(sesHi, Highs[0][0]); sesLo = Math.Min(sesLo, Lows[0][0]);

            if (CurrentBars[0] < BarsRequiredToTrade) return;
            // reversa pendiente: igual que TrySubmitAtrPhaseReversal (corre en la vela de 1 min, con la posición ya cerrada)
            if (pendingReversal != 0 && Position.MarketPosition == MarketPosition.Flat)
            {
                int lado = pendingReversal; pendingReversal = 0; Entrar(lado);
            }
        }

        private void Entrar(int lado)
        {
            if (double.IsNaN(atr20) || atr20 <= 0) return;          // sin ATR20 no hay stop: no se opera
            int ticks = Math.Max(1, (int)Math.Round(MultiploStop * atr20 / TickSize));
            string sig = lado > 0 ? "R_L" : "R_S";
            SetStopLoss(sig, CalculationMode.Ticks, ticks, false);   // relativo al precio de llenado
            if (lado > 0) EnterLong(0, Contratos, sig); else EnterShort(0, Contratos, sig);
        }

        private void Salir(string motivo)
        {
            if (Position.MarketPosition == MarketPosition.Long) ExitLong(0, Position.Quantity, motivo, "R_L");
            else if (Position.MarketPosition == MarketPosition.Short) ExitShort(0, Position.Quantity, motivo, "R_S");
        }

        private void ReiniciarEstado()
        {
            prevCloseReady = oscReady = atrReady = emaReady = false;
            trSeedSum = prevDecisionClose = osc = atr14 = ema21 = 0; trSeedCount = 0;
            shadowSide = 0; pendingReversal = 0; vwapDate = DateTime.MinValue; vwapVol = vwapPv = 0;
        }

        private bool ActualizarIndicador(double hi, double lo, double cl)
        {
            double alpha = 2.0 / (21 + 1.0);
            if (!emaReady) { ema21 = cl; emaReady = true; } else ema21 = alpha * cl + (1 - alpha) * ema21;
            double tr = !prevCloseReady ? hi - lo : Math.Max(hi - lo, Math.Max(Math.Abs(hi - prevDecisionClose), Math.Abs(lo - prevDecisionClose)));
            prevDecisionClose = cl; prevCloseReady = true;
            if (!atrReady)
            {
                trSeedCount++; trSeedSum += tr;
                if (trSeedCount == 14) { atr14 = trSeedSum / 14.0; atrReady = true; }
            }
            else atr14 = (13.0 * atr14 + tr) / 14.0;
            if (!atrReady || atr14 <= 0 || double.IsNaN(atr14)) return false;
            double raw = 100.0 * (cl - ema21) / (3.0 * atr14);
            if (!oscReady) { osc = raw; oscReady = true; } else osc = 0.5 * raw + 0.5 * osc;
            return true;
        }

        // ---- 10 minutos: traducción de _on_bip9_bar ----
        private void BarraDiezMinutos()
        {
            DateTime cierreEt = AEt(Times[1][0]);
            DateTime abreEt = cierreEt.AddMinutes(-10);
            DateTime abreUtc = TimeZoneInfo.ConvertTimeToUtc(Times[1][0], TimeZoneInfo.Local).AddMinutes(-10);
            int fechaSes = abreEt.Year * 10000 + abreEt.Month * 100 + abreEt.Day;
            if (UsarFechasVendedor && FechasVendedor.Contains(fechaSes))
            {
                shadowSide = 0; pendingReversal = 0; Salir("INCOMPLETE_SESSION"); return;
            }
            double op = Opens[1][0], hi = Highs[1][0], lo = Lows[1][0], cl = Closes[1][0], vol = Volumes[1][0];

            if (abreUtc.Hour == 0 && abreUtc.Minute == 0 && prevCloseReady && Math.Abs(op - prevDecisionClose) > 400 * TickSize)
            {
                bool habia = shadowSide != 0;
                ReiniciarEstado();
                if (habia) Salir("ROLL_RESET");
            }

            double prevOsc = osc; bool prevReady = oscReady;
            bool ready = ActualizarIndicador(hi, lo, cl);

            bool vwapOk = false;
            int abreMin = abreEt.Hour * 60 + abreEt.Minute;
            if (abreMin >= 570 && abreMin < 960)
            {
                if (vwapDate != abreEt.Date) { vwapDate = abreEt.Date; vwapVol = 0; vwapPv = 0; }
                vwapPv += (hi + lo + cl) / 3.0 * vol; vwapVol += vol;
                if (vwapVol > 0 && atrReady) vwapOk = Math.Abs(cl - vwapPv / vwapVol) < 2.5 * atr14;
            }

            int cierreMin = cierreEt.Hour * 60 + cierreEt.Minute;
            if (cierreMin == 960) { shadowSide = 0; pendingReversal = 0; Salir("CASH_CLOSE"); return; }
            if (!prevReady || !ready) return;

            bool alcista = !double.IsNaN(prevOsc) && prevOsc <= 100.0 && osc > 100.0;
            bool bajista = !double.IsNaN(prevOsc) && prevOsc >= -100.0 && osc < -100.0;
            if (!alcista && !bajista) return;
            int nuevo = alcista ? 1 : -1;
            if (shadowSide == nuevo) return;
            bool enVentana = cierreMin >= 570 && cierreMin < 660;
            bool plano = Position.MarketPosition == MarketPosition.Flat;

            if (shadowSide == 0)
            {
                if (!enVentana) return;
                shadowSide = nuevo;
                if (vwapOk && plano && CurrentBars[0] >= BarsRequiredToTrade) Entrar(nuevo);
                return;
            }
            if (!enVentana) { shadowSide = 0; pendingReversal = 0; Salir("OPPOSITE"); return; }
            shadowSide = nuevo;
            if (!plano) { pendingReversal = vwapOk ? nuevo : 0; Salir("REVERSAL"); return; }
            if (vwapOk && CurrentBars[0] >= BarsRequiredToTrade) Entrar(nuevo);
        }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Contratos", Order = 1, GroupName = "Parámetros")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 5.0)]
        [Display(Name = "Stop (× ATR20 de sesión)", Order = 2, GroupName = "Parámetros")]
        public double MultiploStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar fechas bloqueadas del vendedor", Order = 3, GroupName = "Parámetros")]
        public bool UsarFechasVendedor { get; set; }
    }
}
