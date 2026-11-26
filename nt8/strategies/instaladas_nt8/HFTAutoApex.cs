#region Using declarations
using System;
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
    public class HFTAutoApex : Strategy
    {
        // Use fully qualified name to avoid conflict with the auto-generated method
        private NinjaTrader.NinjaScript.Indicators.HFTZonesNQPureV3 hftIndicator;
        private EMA trendEma;
        private int lastZoneCount = 0;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Estrategia Automatizada basada en Machine Learning para operar zonas HFT institucionales.";
                Name                                        = "HFTAutoApex";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 2;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                
                // User Editable Parameters
                Quantity                                    = 1;
                TargetTicks                                 = 20;
                StopBufferTicks                             = 4;
                EmaPeriod                                   = 50;
                StartTimeHour                               = 9;
                StartTimeMin                                = 30;
                EndTimeHour                                 = 16;
                EndTimeMin                                  = 0;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                // Instantiate the indicator explicitly using the class constructor
                hftIndicator = new NinjaTrader.NinjaScript.Indicators.HFTZonesNQPureV3();
                AddChartIndicator(hftIndicator);
                
                trendEma = EMA(Close, EmaPeriod);
                AddChartIndicator(trendEma);
                
                ClearOutputWindow();
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // 1. Session Filter (US Time 09:30 - 16:00 ET)
            int currentHour = Time[0].Hour;
            int currentMin = Time[0].Minute;
            int timeInMinutes = currentHour * 60 + currentMin;
            int startMinutes = StartTimeHour * 60 + StartTimeMin;
            int endMinutes = EndTimeHour * 60 + EndTimeMin;
            
            bool isUsSession = timeInMinutes >= startMinutes && timeInMinutes <= endMinutes;

            // Trend Filter
            bool isUptrend = Close[0] > trendEma[0];
            bool isDowntrend = Close[0] < trendEma[0];

            // 2. Check for new HFT Zones
            if (hftIndicator != null && hftIndicator.PublicZones != null)
            {
                int currentZoneCount = hftIndicator.PublicZones.Count;
                
                if (currentZoneCount > lastZoneCount)
                {
                    var newZone = hftIndicator.PublicZones[currentZoneCount - 1];
                    lastZoneCount = currentZoneCount;

                    // Fully qualified enum access
                    if (newZone.Bucket == NinjaTrader.NinjaScript.Indicators.HFTZonesNQPureV3.HFTBucket.Predator || 
                        newZone.Bucket == NinjaTrader.NinjaScript.Indicators.HFTZonesNQPureV3.HFTBucket.Ultra)
                    {
                        if (!isUsSession)
                        {
                            Print($"{Time[0]} - [REJECTED] HFT {newZone.Bucket} ignorado por estar fuera del Horario US.");
                            return;
                        }

                        if (Position.MarketPosition != MarketPosition.Flat)
                        {
                            return;
                        }

                        if (newZone.Direction == 1 && isUptrend)
                        {
                            Print($"{Time[0]} - [EXECUTE] LONG HFT {newZone.Bucket} detectado.");
                            
                            double slPrice = newZone.Lower - (StopBufferTicks * TickSize);
                            int slTicks = (int)Math.Round((Close[0] - slPrice) / TickSize);
                            
                            SetStopLoss(CalculationMode.Ticks, slTicks);
                            SetProfitTarget(CalculationMode.Ticks, TargetTicks);
                            
                            EnterLong(Quantity, "HFT_Long");
                        }
                        else if (newZone.Direction == -1 && isDowntrend)
                        {
                            Print($"{Time[0]} - [EXECUTE] SHORT HFT {newZone.Bucket} detectado.");
                            
                            double slPrice = newZone.Upper + (StopBufferTicks * TickSize);
                            int slTicks = (int)Math.Round((slPrice - Close[0]) / TickSize);
                            
                            SetStopLoss(CalculationMode.Ticks, slTicks);
                            SetProfitTarget(CalculationMode.Ticks, TargetTicks);
                            
                            EnterShort(Quantity, "HFT_Short");
                        }
                        else
                        {
                            Print($"{Time[0]} - [REJECTED] HFT ignorado por filtro de tendencia EMA({EmaPeriod}).");
                        }
                    }
                }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Quantity", Description="Numero de contratos", Order=1, GroupName="1. Order")]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Target (Ticks)", Description="Take profit estático", Order=2, GroupName="1. Order")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name="Stop Buffer (Ticks)", Description="Ticks por debajo/encima de la caja HFT", Order=3, GroupName="1. Order")]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 200)]
        [Display(Name="EMA Period", Description="Periodo de la media móvil para filtro de tendencia", Order=1, GroupName="2. Filters")]
        public int EmaPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="Start Hour (US)", Order=2, GroupName="2. Filters")]
        public int StartTimeHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="Start Min (US)", Order=3, GroupName="2. Filters")]
        public int StartTimeMin { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="End Hour (US)", Order=4, GroupName="2. Filters")]
        public int EndTimeHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="End Min (US)", Order=5, GroupName="2. Filters")]
        public int EndTimeMin { get; set; }
        #endregion
    }
}
