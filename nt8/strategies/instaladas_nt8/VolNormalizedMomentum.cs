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
    public class VolNormalizedMomentum : Strategy
    {
        private List<double> volumeList = new List<double>();
        private MAX maxInd;
        private MIN minInd;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Momentum Breakout with Volume-Normalized filter (EXP-019)";
                Name                                        = "VolNormalizedMomentum";
                Calculate                                   = Calculate.OnBarClose;
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
                BarsRequiredToTrade                         = 60;
                
                DonchianPeriod = 40;
                VolumePeriod = 60;
                TargetTicks = 32;
                StopTicks = 4;
                StartTimeInt = 93000;
                EndTimeInt = 155500;
                EnterAtMarket = false;
            }
            else if (State == State.Configure)
            {
                SetProfitTarget("LongBreakout", CalculationMode.Ticks, TargetTicks);
                SetStopLoss("LongBreakout", CalculationMode.Ticks, StopTicks, false);
                
                SetProfitTarget("ShortBreakout", CalculationMode.Ticks, TargetTicks);
                SetStopLoss("ShortBreakout", CalculationMode.Ticks, StopTicks, false);
            }
            else if (State == State.DataLoaded)
            {
                maxInd = MAX(High, DonchianPeriod);
                minInd = MIN(Low, DonchianPeriod);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // Maintain rolling volume list
            volumeList.Add(Volume[0]);
            if (volumeList.Count > VolumePeriod)
            {
                volumeList.RemoveAt(0);
            }

            // Calculate Volume P75
            if (volumeList.Count == VolumePeriod)
            {
                List<double> sortedVolumes = new List<double>(volumeList);
                sortedVolumes.Sort();
                
                // Index for 75th percentile (0-indexed)
                int indexP75 = (int)Math.Round((VolumePeriod - 1) * 0.75);
                double volumeP75 = sortedVolumes[indexP75];

                // Breakout logic
                double currentMax = maxInd[1];
                double currentMin = minInd[1];

                bool isLongBreakout = Close[0] > currentMax;
                bool isShortBreakout = Close[0] < currentMin;
                bool isVolumeAbnormal = Volume[0] > volumeP75;

                // Time filter
                int currentTime = ToTime(Time[0]);
                bool isRTH = currentTime >= StartTimeInt && currentTime <= EndTimeInt;

                if (Position.MarketPosition == MarketPosition.Flat && isRTH)
                {
                    if (isLongBreakout && isVolumeAbnormal)
                    {
                        if (EnterAtMarket)
                            EnterLong("LongBreakout");
                        else
                            EnterLongLimit(currentMax, "LongBreakout");
                            
                        Draw.ArrowUp(this, "L"+CurrentBar, false, 0, Low[0] - TickSize * 5, Brushes.Green);
                    }
                    else if (isShortBreakout && isVolumeAbnormal)
                    {
                        if (EnterAtMarket)
                            EnterShort("ShortBreakout");
                        else
                            EnterShortLimit(currentMin, "ShortBreakout");
                            
                        Draw.ArrowDown(this, "S"+CurrentBar, false, 0, High[0] + TickSize * 5, Brushes.Red);
                    }
                }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Donchian Period", Description="Bars for breakout channel", Order=1, GroupName="Parameters")]
        public int DonchianPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Volume Period", Description="Bars for volume normalization", Order=2, GroupName="Parameters")]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Target Ticks", Description="Profit Target in Ticks", Order=3, GroupName="Parameters")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Stop Ticks", Description="Stop Loss in Ticks", Order=4, GroupName="Parameters")]
        public int StopTicks { get; set; }
        
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Start Time (HHMMSS)", Description="Start time filter", Order=5, GroupName="Parameters")]
        public int StartTimeInt { get; set; }
        
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="End Time (HHMMSS)", Description="End time filter", Order=6, GroupName="Parameters")]
        public int EndTimeInt { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Enter at Market?", Description="If true, enters Market at close. If false, uses Limit order at breakout level.", Order=7, GroupName="Parameters")]
        public bool EnterAtMarket { get; set; }
        #endregion
    }
}
