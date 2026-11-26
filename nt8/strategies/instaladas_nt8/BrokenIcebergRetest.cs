#region Using declarations
using System;
using System.IO;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class BrokenIcebergRetest : Strategy
    {
        // Settings
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Min HFT Volume (Sweep)", Order=1, GroupName="1. Parámetros")]
        public int MinHFTVolume { get; set; }
        
        [NinjaScriptProperty]
        [Range(0.01, 1.0)]
        [Display(Name="Min OBI Threshold (0.3 = 30%)", Order=2, GroupName="1. Parámetros")]
        public double MinOBIThreshold { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Target Ticks (TP)", Order=3, GroupName="2. Gestión de Riesgo")]
        public int TargetTicks { get; set; }
        
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Stop Ticks (SL)", Order=4, GroupName="2. Gestión de Riesgo")]
        public int StopTicks { get; set; }
        
        [NinjaScriptProperty]
        [Range(1, 300)]
        [Display(Name="Max Retest Time (Secs)", Order=5, GroupName="2. Gestión de Riesgo")]
        public int MaxRetestSeconds { get; set; }

        // L2 Reconstruction Books
        private SortedDictionary<double, long> askBook = new SortedDictionary<double, long>();
        private SortedDictionary<double, long> bidBook = new SortedDictionary<double, long>(Comparer<double>.Create((x, y) => y.CompareTo(x))); // descending

        // State variables
        private double activeBrokenPrice = 0;
        private DateTime brokenTime;
        private int currentSweepVolume = 0;
        private DateTime sweepStartTime;
        private int lastSide = 0;

        private Order pendingEntryOrder = null;

        private void LogToFile(string msg)
        {
            try
            {
                string path = @"C:\LoggerHFT\data\NT8_BrokenIceberg_Log.txt";
                using (StreamWriter sw = File.AppendText(path))
                {
                    sw.WriteLine(msg);
                }
                Print(msg);
            }
            catch { }
        }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Automatización V2: Order Book Imbalance (Top 3 Levels) cruzado con HFT.";
                Name                                        = "BrokenIcebergRetest";
                Calculate                                   = Calculate.OnEachTick; 
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 0;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;

                // Valores por defecto OBI
                MinHFTVolume = 50;  // Relajado porque el alfa ahora está en el OBI
                MinOBIThreshold = 0.30; // 30% Imbalance
                TargetTicks = 8;
                StopTicks = 4;
                MaxRetestSeconds = 30;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                SetProfitTarget("", CalculationMode.Ticks, TargetTicks);
                SetStopLoss("", CalculationMode.Ticks, StopTicks, false);
            }
            else if (State == State.Realtime)
            {
                LogToFile(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " -> [SISTEMA] Bot V2 OBI Iniciado. Reconstruyendo L2 Top-3...");
            }
        }

        protected override void OnMarketDepth(MarketDepthEventArgs marketDepthUpdate)
        {
            if (marketDepthUpdate.MarketDataType == MarketDataType.Ask)
            {
                if (marketDepthUpdate.Operation == Operation.Add || marketDepthUpdate.Operation == Operation.Update)
                    askBook[marketDepthUpdate.Price] = marketDepthUpdate.Volume;
                else if (marketDepthUpdate.Operation == Operation.Remove)
                    askBook.Remove(marketDepthUpdate.Price);
            }
            else if (marketDepthUpdate.MarketDataType == MarketDataType.Bid)
            {
                if (marketDepthUpdate.Operation == Operation.Add || marketDepthUpdate.Operation == Operation.Update)
                    bidBook[marketDepthUpdate.Price] = marketDepthUpdate.Volume;
                else if (marketDepthUpdate.Operation == Operation.Remove)
                    bidBook.Remove(marketDepthUpdate.Price);
            }
        }

        protected override void OnMarketData(MarketDataEventArgs marketDataUpdate)
        {
            if (marketDataUpdate.MarketDataType == MarketDataType.Last)
            {
                double price = marketDataUpdate.Price;
                int volume = (int)marketDataUpdate.Volume;
                DateTime time = marketDataUpdate.Time;

                double topAskPrice = askBook.Count > 0 ? askBook.Keys.First() : double.MaxValue;
                double topBidPrice = bidBook.Count > 0 ? bidBook.Keys.First() : double.MinValue;

                int side = 0;
                if (price >= topAskPrice) side = 1; 
                else if (price <= topBidPrice) side = -1;

                if (side != 0)
                {
                    if (side == lastSide && (time - sweepStartTime).TotalMilliseconds <= 1000)
                    {
                        currentSweepVolume += volume;
                    }
                    else
                    {
                        currentSweepVolume = volume;
                        sweepStartTime = time;
                        lastSide = side;
                    }

                    if (Position.MarketPosition == MarketPosition.Flat && pendingEntryOrder == null)
                    {
                        if (currentSweepVolume >= MinHFTVolume)
                        {
                            // Calcular OBI de los Top 3 niveles
                            double askVolTop3 = 0;
                            int count = 0;
                            foreach(var kv in askBook) {
                                askVolTop3 += kv.Value;
                                count++;
                                if(count >= 3) break;
                            }

                            double bidVolTop3 = 0;
                            count = 0;
                            foreach(var kv in bidBook) {
                                bidVolTop3 += kv.Value;
                                count++;
                                if(count >= 3) break;
                            }

                            double obi = 0;
                            if ((bidVolTop3 + askVolTop3) > 0)
                                obi = (bidVolTop3 - askVolTop3) / (bidVolTop3 + askVolTop3);

                            if (side == 1 && obi <= -MinOBIThreshold)
                            {
                                // Absorción fallida Alcista (Muro Ask roto a pesar del gran OBI negativo)
                                activeBrokenPrice = topAskPrice;
                                brokenTime = time;
                                LogToFile(time.ToString("yyyy-MM-dd HH:mm:ss.fff") + " -> [V2 ALERTA] Muro Ask Roto en " + activeBrokenPrice + " (OBI: " + obi.ToString("0.00") + "). Esperando Retest...");
                                EnterLongLimit(0, true, 1, activeBrokenPrice, "RetestLong");
                                currentSweepVolume = 0; 
                            }
                            else if (side == -1 && obi >= MinOBIThreshold)
                            {
                                // Absorción fallida Bajista
                                activeBrokenPrice = topBidPrice;
                                brokenTime = time;
                                LogToFile(time.ToString("yyyy-MM-dd HH:mm:ss.fff") + " -> [V2 ALERTA] Muro Bid Roto en " + activeBrokenPrice + " (OBI: " + obi.ToString("0.00") + "). Esperando Retest...");
                                EnterShortLimit(0, true, 1, activeBrokenPrice, "RetestShort");
                                currentSweepVolume = 0;
                            }
                        }
                    }
                }
            }
        }
        
        protected override void OnBarUpdate()
        {
            if (pendingEntryOrder != null && Position.MarketPosition == MarketPosition.Flat)
            {
                if ((Time[0] - brokenTime).TotalSeconds > MaxRetestSeconds)
                {
                    LogToFile(Time[0].ToString("yyyy-MM-dd HH:mm:ss.fff") + " -> [ABORTAR] Expiró ventana TTR de " + MaxRetestSeconds + "s.");
                    CancelOrder(pendingEntryOrder);
                    pendingEntryOrder = null;
                }
            }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled, double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string nativeError)
        {
            if (order.Name == "RetestLong" || order.Name == "RetestShort" || order.Name == "Profit target" || order.Name == "Stop loss")
            {
                if (orderState == OrderState.Filled)
                {
                    LogToFile(time.ToString("yyyy-MM-dd HH:mm:ss.fff") + " -> [EJECUCION] " + order.Name + " | Precio: " + averageFillPrice + " | Estado: FILLED");
                }
            }

            if (pendingEntryOrder == null && (order.Name == "RetestLong" || order.Name == "RetestShort") && orderState == OrderState.Working)
            {
                pendingEntryOrder = order;
            }

            if (pendingEntryOrder != null && pendingEntryOrder == order)
            {
                if (orderState == OrderState.Cancelled || orderState == OrderState.Rejected || orderState == OrderState.Filled)
                {
                    pendingEntryOrder = null; 
                }
            }
        }
    }
}
