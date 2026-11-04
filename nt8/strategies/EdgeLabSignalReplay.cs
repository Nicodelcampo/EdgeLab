#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabSignalReplay (version=1.0, 2026-11-04)
// Repite en NT8 (Market Replay o Sim) las operaciones que EdgeLab simuló para una regla congelada, a partir de un CSV de señales
// exportado por `tools/senales_nt8.py`, y registra cada llenado real para medir:
//   - paridad de ejecución: misma entrada, stop, objetivo y salida que la simulación de Python;
//   - fricción real: precio de llenado de NT8 contra la entrada teórica de Python (spread + llenado), y salida contra el nivel.
// La señal NO se recalcula acá (eso es la paridad del indicador, otra etapa): se toma del CSV, que puede venir de un CFD.
//
// CSV de entrada (cabecera obligatoria): id,t,lado,limite,entrada,stop,objetivo
//   t        = cierre de la vela M1 de decisión, epoch UTC en segundos
//   lado     = 1 compra, -1 venta
//   limite   = 2 mercado en el primer tick siguiente; 0 cierre de la vela (en vivo: igual que 2); 1 orden límite en `entrada`
//   entrada, stop, objetivo = precios absolutos del futuro de ejecución
// CSV de salida: id,evento,t_utc,precio,cantidad,motivo  (evento = SEÑAL | ENTRADA | SALIDA | OMITIDA | CANCELADA)
//
// Uso: gráfico M1 del futuro (p. ej. NQ 12-25), Market Replay en las fechas del CSV, Calculate = OnBarClose. Una operación a la vez
// por cuenta: si llega una señal con posición abierta se registra OMITIDA (Python las simula independientes).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabSignalReplay : Strategy
    {
        private class Senal { public string Id; public long T; public int Lado; public int Limite; public double Entrada, Stop, Objetivo; }

        private readonly Dictionary<long, List<Senal>> porMinuto = new Dictionary<long, List<Senal>>();
        private StreamWriter salida;
        private string activa = null;          // id de la señal en curso
        private int barraEntrada = -1;
        private int barraOrdenLimite = -1;
        private Order ordenLimite = null;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabSignalReplay";
                Description = "Repite señales congeladas de EdgeLab y registra los llenados reales (paridad y fricción).";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 60;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 1;
                SignalFile = string.Empty;
                OutFile = string.Empty;
                MaxBars = 240;
                LimitBars = 120;
                Quantity = 1;
            }
            else if (State == State.DataLoaded)
            {
                Cargar();
                string ruta = string.IsNullOrWhiteSpace(OutFile)
                    ? Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "edgelab_replay_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + ".csv")
                    : OutFile;
                salida = new StreamWriter(ruta, false);
                salida.WriteLine("id,evento,t_utc,precio,cantidad,motivo");
                Print("EdgeLabSignalReplay: " + porMinuto.Count + " minutos con señal; salida en " + ruta);
            }
            else if (State == State.Terminated)
            {
                if (salida != null) { salida.Flush(); salida.Dispose(); salida = null; }
            }
        }

        private void Cargar()
        {
            porMinuto.Clear();
            if (string.IsNullOrWhiteSpace(SignalFile) || !File.Exists(SignalFile)) { Print("EdgeLabSignalReplay: falta el CSV de señales"); return; }
            string[] lineas = File.ReadAllLines(SignalFile);
            for (int i = 1; i < lineas.Length; i++)
            {
                string[] p = lineas[i].Split(',');
                if (p.Length < 7) continue;
                var s = new Senal
                {
                    Id = p[0],
                    T = long.Parse(p[1], CultureInfo.InvariantCulture),
                    Lado = int.Parse(p[2], CultureInfo.InvariantCulture),
                    Limite = int.Parse(p[3], CultureInfo.InvariantCulture),
                    Entrada = double.Parse(p[4], CultureInfo.InvariantCulture),
                    Stop = double.Parse(p[5], CultureInfo.InvariantCulture),
                    Objetivo = double.Parse(p[6], CultureInfo.InvariantCulture)
                };
                List<Senal> l;
                if (!porMinuto.TryGetValue(s.T, out l)) { l = new List<Senal>(); porMinuto[s.T] = l; }
                l.Add(s);
            }
        }

        private long EpochUtc(DateTime t)
        {
            DateTime utc = TimeZoneInfo.ConvertTimeToUtc(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo);
            return (long)(utc - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
        }

        private void Log(string id, string evento, DateTime t, double precio, int cant, string motivo)
        {
            if (salida == null) return;
            salida.WriteLine(string.Join(",", id, evento, EpochUtc(t).ToString(CultureInfo.InvariantCulture),
                precio.ToString("R", CultureInfo.InvariantCulture), cant.ToString(CultureInfo.InvariantCulture), motivo));
            salida.Flush();
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < BarsRequiredToTrade) return;

            // tope de tenencia (240 velas, como el simulador de Python) y vencimiento de la orden límite (120 velas)
            if (activa != null && Position.MarketPosition != MarketPosition.Flat && barraEntrada >= 0 && CurrentBar - barraEntrada >= MaxBars)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("TIEMPO", activa); else ExitShort("TIEMPO", activa);
            }
            if (ordenLimite != null && barraOrdenLimite >= 0 && CurrentBar - barraOrdenLimite >= LimitBars
                && (ordenLimite.OrderState == OrderState.Working || ordenLimite.OrderState == OrderState.Accepted))
            {
                CancelOrder(ordenLimite);
            }

            List<Senal> l;
            if (!porMinuto.TryGetValue(EpochUtc(Time[0]), out l)) return;
            foreach (Senal s in l)
            {
                Log(s.Id, "SEÑAL", Time[0], s.Entrada, 0, "lim" + s.Limite);
                if (activa != null || Position.MarketPosition != MarketPosition.Flat) { Log(s.Id, "OMITIDA", Time[0], 0, 0, "posicion_abierta"); continue; }
                activa = s.Id; barraEntrada = -1;
                SetStopLoss(s.Id, CalculationMode.Price, s.Stop, false);
                SetProfitTarget(s.Id, CalculationMode.Price, s.Objetivo);
                if (s.Limite == 1)
                {
                    ordenLimite = s.Lado == 1 ? EnterLongLimit(0, true, Quantity, s.Entrada, s.Id) : EnterShortLimit(0, true, Quantity, s.Entrada, s.Id);
                    barraOrdenLimite = CurrentBar;
                }
                else
                {
                    if (s.Lado == 1) EnterLong(Quantity, s.Id); else EnterShort(Quantity, s.Id);
                }
            }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled, double averageFillPrice,
                                              OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (order == ordenLimite && (orderState == OrderState.Cancelled || orderState == OrderState.Rejected))
            {
                Log(activa ?? order.Name, "CANCELADA", time, limitPrice, 0, orderState.ToString());
                ordenLimite = null; activa = null; barraOrdenLimite = -1;
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition,
                                                  string orderId, DateTime time)
        {
            if (execution.Order == null) return;
            string nombre = execution.Order.Name;
            if (execution.IsEntry)
            {
                Log(execution.Order.FromEntrySignal ?? nombre, "ENTRADA", time, price, quantity, nombre);
                barraEntrada = CurrentBar; ordenLimite = null;
            }
            else if (execution.IsExit)
            {
                string motivo = nombre == "Stop loss" ? "STOP" : nombre == "Profit target" ? "OBJETIVO"
                              : nombre == "TIEMPO" ? "TIEMPO" : nombre == "Exit on session close" ? "SESION" : nombre;
                Log(execution.Order.FromEntrySignal, "SALIDA", time, price, quantity, motivo);
                if (Position.MarketPosition == MarketPosition.Flat) { activa = null; barraEntrada = -1; }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "CSV de señales", Order = 1, GroupName = "EdgeLab")]
        public string SignalFile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "CSV de salida (vacío = carpeta de NT8)", Order = 2, GroupName = "EdgeLab")]
        public string OutFile { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Tope de tenencia (velas M1)", Order = 3, GroupName = "EdgeLab")]
        public int MaxBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Vencimiento de la límite (velas M1)", Order = 4, GroupName = "EdgeLab")]
        public int LimitBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Contratos", Order = 5, GroupName = "EdgeLab")]
        public int Quantity { get; set; }
        #endregion
    }
}
