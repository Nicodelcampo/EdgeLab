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

//This namespace holds Strategies in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Strategies
{
	public class HolyGrailTrendStrategy : Strategy
	{
		private EMA emaFast;
		private EMA emaSlow;
		private EMA emaTrend;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Estrategia automática basada en alta autocorrelación para la ventana de 04:00 AM (European Open).";
				Name										= "HolyGrailTrendStrategy";
				Calculate									= Calculate.OnBarClose;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= true;
				ExitOnSessionCloseSeconds					= 30;
				IsFillLimitOnTouch							= false;
				MaximumBarsLookBack							= MaximumBarsLookBack.TwoHundredFiftySix;
				OrderFillResolution							= OrderFillResolution.Standard;
				Slippage									= 0;
				StartBehavior								= StartBehavior.WaitUntilFlat;
				TimeInForce									= TimeInForce.Gtc;
				TraceOrders									= false;
				RealtimeErrorHandling						= RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling							= StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade							= 50;
				// Disable this property for performance gains in Strategy Analyzer optimizations
				// See the Help Guide for additional information
				IsInstantiatedOnEachOptimizationIteration	= false;
				
				// Parameters
				StartTime									= 40000;
				EndTime										= 43000;
				FlatTime									= 53000;
				
				EmaFastPer									= 9;
				EmaSlowPer									= 21;
				EmaTrendPer									= 50;
				
				StopLossTicks								= 60;
				ProfitTargetTicks							= 120;
				Contratos									= 1;
			}
			else if (State == State.Configure)
			{
				SetStopLoss(CalculationMode.Ticks, StopLossTicks);
				SetProfitTarget(CalculationMode.Ticks, ProfitTargetTicks);
			}
			else if (State == State.DataLoaded)
			{				
				emaFast = EMA(EmaFastPer);
				emaSlow = EMA(EmaSlowPer);
				emaTrend = EMA(EmaTrendPer);
				
				// Optional: Color plots for debugging on chart
				emaFast.Plots[0].Brush = Brushes.Cyan;
				emaSlow.Plots[0].Brush = Brushes.Magenta;
				emaTrend.Plots[0].Brush = Brushes.Yellow;
				
				AddChartIndicator(emaFast);
				AddChartIndicator(emaSlow);
				AddChartIndicator(emaTrend);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < BarsRequiredToTrade) return;

			int timeNow = ToTime(Time[0]);

			// 1. Check for Forced Exit Time (FlatTime)
			if (Position.MarketPosition != MarketPosition.Flat && timeNow >= FlatTime)
			{
				if (Position.MarketPosition == MarketPosition.Long)
					ExitLong("TimeExit", "");
				else if (Position.MarketPosition == MarketPosition.Short)
					ExitShort("TimeExit", "");
				return; // Skip entry logic if we are flattening
			}

			// 2. Check Time Filter for Entries
			if (timeNow < StartTime || timeNow > EndTime)
				return;

			// 3. Entry Logic (EMA Crossover + EMA Trend Filter)
			if (Position.MarketPosition == MarketPosition.Flat)
			{
				// LONG Condition: Fast crosses above Slow, AND both are above Trend, AND Close is above Trend
				if (CrossAbove(emaFast, emaSlow, 1) && emaSlow[0] > emaTrend[0] && Close[0] > emaTrend[0])
				{
					EnterLong(Contratos, "LongEntry");
				}
				// SHORT Condition: Fast crosses below Slow, AND both are below Trend, AND Close is below Trend
				else if (CrossBelow(emaFast, emaSlow, 1) && emaSlow[0] < emaTrend[0] && Close[0] < emaTrend[0])
				{
					EnterShort(Contratos, "ShortEntry");
				}
			}
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(0, 235959)]
		[Display(Name="Start Time (HHMMSS)", Order=1, GroupName="1. Horarios")]
		public int StartTime { get; set; }

		[NinjaScriptProperty]
		[Range(0, 235959)]
		[Display(Name="End Time (HHMMSS)", Order=2, GroupName="1. Horarios")]
		public int EndTime { get; set; }

		[NinjaScriptProperty]
		[Range(0, 235959)]
		[Display(Name="Flat Time (HHMMSS)", Order=3, GroupName="1. Horarios")]
		public int FlatTime { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name="EMA Fast", Order=1, GroupName="2. Indicadores")]
		public int EmaFastPer { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name="EMA Slow", Order=2, GroupName="2. Indicadores")]
		public int EmaSlowPer { get; set; }

		[NinjaScriptProperty]
		[Range(1, 500)]
		[Display(Name="EMA Trend Filter", Order=3, GroupName="2. Indicadores")]
		public int EmaTrendPer { get; set; }

		[NinjaScriptProperty]
		[Range(1, 1000)]
		[Display(Name="Stop Loss (Ticks)", Order=1, GroupName="3. Riesgo")]
		public int StopLossTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 2000)]
		[Display(Name="Profit Target (Ticks)", Order=2, GroupName="3. Riesgo")]
		public int ProfitTargetTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name="Contratos", Order=3, GroupName="3. Riesgo")]
		public int Contratos { get; set; }
		#endregion
	}
}
