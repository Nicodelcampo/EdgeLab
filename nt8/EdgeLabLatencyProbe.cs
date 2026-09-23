// EdgeLabLatencyProbe — mide latencia de ordenes y del feed SIN operar (Fase 1 del plan L2,
// docs/research/PLAN_L2_POST_DEEP_RESEARCH_20260923.md).
//
// Que hace:
//   * Cada ProbeIntervalSeconds envia UNA orden LIMITE de 1 contrato a OffsetTicks del mejor precio (lejos, no deberia
//     ejecutarse), y apenas queda Working la cancela. Registra con Stopwatch (monotonic, alta resolucion):
//       submit -> Submitted -> Accepted -> Working -> CancelSubmitted -> Cancelled.
//   * En cada tick de mercado registra (muestreado) la diferencia entre la hora local UTC y la hora que trae el dato
//     (e.Time). Es un estimado de atraso del feed; depende de que el reloj de la PC este sincronizado (NTP).
//   * Escribe todo a Documents\NinjaTrader 8\edgelab_latency\<instrumento>_<fecha>.csv.
//
// Seguridad: unmanaged, una orden por vez, 1 contrato, MaxProbes por corrida, cancela todo al deshabilitar, y si una
// sonda se llegara a ejecutar se detiene la estrategia y queda registrado (FILL_UNEXPECTED). Mide RTT de ack/cancel;
// la latencia hasta el FILL requiere ordenes que se ejecuten y NO se mide aca a proposito.
// Sim101 simula localmente: sus tiempos NO son latencia real. Usar la conexion del broker (demo del servidor o real).
#region Using declarations
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabLatencyProbe : Strategy
    {
        private Order probe;
        private long tSubmit;
        private int probes, lastSampleSec = -1;
        private DateTime nextProbeUtc = DateTime.MinValue;
        private StreamWriter log;
        private static readonly double TickUs = 1e6 / Stopwatch.Frequency;

        [NinjaScriptProperty] public int ProbeIntervalSeconds { get; set; }
        [NinjaScriptProperty] public int OffsetTicks { get; set; }
        [NinjaScriptProperty] public int MaxProbes { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabLatencyProbe";
                Description = "Mide RTT de ack/cancel de ordenes limite lejanas y atraso del feed. No opera.";
                Calculate = Calculate.OnEachTick;
                IsUnmanaged = true;
                IsExitOnSessionCloseStrategy = false;
                ProbeIntervalSeconds = 20;
                OffsetTicks = 50;
                MaxProbes = 200;
            }
            else if (State == State.DataLoaded)
            {
                string dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "edgelab_latency");
                Directory.CreateDirectory(dir);
                string f = Path.Combine(dir, Instrument.FullName.Replace(' ', '_') + "_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss", CultureInfo.InvariantCulture) + ".csv");
                log = new StreamWriter(f, false) { AutoFlush = true };
                log.WriteLine("utc_iso,kind,probe,state,us_since_submit,detail");
                Write("START", 0, "", -1, "account=" + Account.Name + " offset=" + OffsetTicks + " interval=" + ProbeIntervalSeconds);
            }
            else if (State == State.Terminated)
            {
                if (probe != null && (probe.OrderState == OrderState.Working || probe.OrderState == OrderState.Accepted))
                    CancelOrder(probe);
                if (log != null) { Write("STOP", probes, "", -1, ""); log.Dispose(); log = null; }
            }
        }

        private void Write(string kind, int n, string state, double us, string detail)
        {
            if (log == null) return;
            log.WriteLine(string.Join(",", DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture), kind,
                n.ToString(CultureInfo.InvariantCulture), state,
                us < 0 ? "" : us.ToString("F0", CultureInfo.InvariantCulture), detail.Replace(',', ';')));
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            if (State != State.Realtime || e.MarketDataType != MarketDataType.Last) return;
            int sec = DateTime.UtcNow.Second;
            if (sec != lastSampleSec)
            {
                lastSampleSec = sec;
                double lagMs = (DateTime.UtcNow - e.Time.ToUniversalTime()).TotalMilliseconds;
                Write("FEED", probes, "Last", -1, "feed_lag_ms=" + lagMs.ToString("F1", CultureInfo.InvariantCulture));
            }
            if (probe != null || probes >= MaxProbes || DateTime.UtcNow < nextProbeUtc) return;
            double bid = GetCurrentBid();
            if (bid <= 0) return;
            double px = Instrument.MasterInstrument.RoundToTickSize(bid - OffsetTicks * TickSize);
            probes++;
            tSubmit = Stopwatch.GetTimestamp();
            probe = SubmitOrderUnmanaged(0, OrderAction.Buy, OrderType.Limit, 1, px, 0, "", "EL_PROBE_" + probes);
            Write("ORDER", probes, "SubmitCalled", 0, "limit=" + px.ToString(CultureInfo.InvariantCulture) + " bid=" + bid.ToString(CultureInfo.InvariantCulture));
            nextProbeUtc = DateTime.UtcNow.AddSeconds(ProbeIntervalSeconds);
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
            double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (probe == null || order.Name != probe.Name) return;
            double us = (Stopwatch.GetTimestamp() - tSubmit) * TickUs;
            Write("ORDER", probes, orderState.ToString(), us, "error=" + error + " comment=" + comment);
            if (orderState == OrderState.Working)
                CancelOrder(order);
            else if (orderState == OrderState.Filled || orderState == OrderState.PartFilled)
            {
                Write("FILL_UNEXPECTED", probes, orderState.ToString(), us, "sonda ejecutada: estrategia detenida");
                SetState(State.Terminated);
            }
            else if (orderState == OrderState.Cancelled || orderState == OrderState.Rejected)
                probe = null;
        }
    }
}
