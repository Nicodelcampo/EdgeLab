#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
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

// ============================================================================
// BigTrap2OptimizerStrategy.cs — Estrategia de Absorción Institucional BigTrap2
//
// LÓGICA DE ENTRADA:
// - Bull Trap (Compradores atrapados en techo con imbalance agresor) -> VENTA (Short).
// - Bear Trap (Vendedores atrapados en piso con imbalance agresor)   -> COMPRA (Long).
//
// OPTIMIZACIÓN PURA DE STOP LOSS Y TAKE PROFIT:
// Expone StopLossTicks y TakeProfitTicks diseñados para correr en el Optimizer
// de NinjaTrader 8 en 30 segundos.
// ============================================================================

namespace NinjaTrader.NinjaScript.Strategies
{
	public class BigTrap2OptimizerStrategy : Strategy
	{
		#region Variables
		private double dailyPnL = 0;
		private int tradesToday = 0;
		private DateTime currentDay = DateTime.MinValue;

		// Footprint subserie de 1 tick
		private double lastTickPrice = double.NaN;
		private int lastTickDir = 0;
		private readonly Dictionary<long, double> askFootprint = new Dictionary<long, double>();
		private readonly Dictionary<long, double> bidFootprint = new Dictionary<long, double>();
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Estrategia de Absorción BigTrap2 para optimización pura de SL y TP en NinjaTrader 8.";
				Name										= "BigTrap2OptimizerStrategy";
				Calculate									= Calculate.OnBarClose;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= true;
				ExitOnSessionCloseSeconds					= 300;
				IsFillLimitOnTouch							= false;
				MaximumBarsLookBack							= MaximumBarsLookBack.TwoHundredFiftySix;
				OrderFillResolution							= OrderFillResolution.Standard;
				Slippage									= 1;
				StartBehavior								= StartBehavior.WaitUntilFlat;
				TimeInForce									= TimeInForce.Gtc;
				TraceOrders									= false;
				RealtimeErrorHandling						= RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling							= StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade							= 20;

				// ── 1. Parámetros Principales de Optimización (SL & TP) ──
				StopLossTicks								= 20;   // Optimizable en Strategy Analyzer (ej. 10 a 40)
				TakeProfitTicks								= 40;   // Optimizable en Strategy Analyzer (ej. 20 a 100)
				EnableTrailingStop							= false;
				TrailingStopTicks							= 15;

				// ── 2. Parámetros de Detección BigTrap2 ──
				ImbalanceRatio								= 3.0;  // Ratio de imbalance diagonal (3:1)
				MinTrapVolume								= 30;   // Volumen mínimo en la zona de trampa
				UseWickFilter								= true; // Exigir que la trampa ocurra en la mecha
				WickZonePct									= 30.0;

				// ── 3. Gestión y Prop Firm ──
				MaxDailyLoss								= 1000.0;
				MaxDailyTrades								= 15;
				EnableLong									= true;
				EnableShort									= true;
			}
			else if (State == State.Configure)
			{
				// Motor de ticks: subserie de 1 tick para footprint exacto
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
		}

		protected override void OnBarUpdate()
		{
			// Procesamiento del stream de 1 tick para reconstruir el footprint
			if (BarsInProgress == 1)
			{
				double tickPrice = Closes[1][0];
				double tickVol = Volumes[1][0];
				double bid = Bids[1][0];
				double ask = Asks[1][0];

				if (!double.IsNaN(lastTickPrice))
				{
					if (tickPrice > lastTickPrice) lastTickDir = 1;
					else if (tickPrice < lastTickPrice) lastTickDir = -1;
				}
				lastTickPrice = tickPrice;

				// Clasificación Buy / Sell
				bool isBuy = false;
				if (!double.IsNaN(ask) && !double.IsNaN(bid) && ask > bid)
				{
					if (tickPrice >= ask) isBuy = true;
					else if (tickPrice <= bid) isBuy = false;
					else isBuy = (lastTickDir >= 0);
				}
				else
				{
					isBuy = (lastTickDir >= 0);
				}

				long priceTick = (long)Math.Round(tickPrice / TickSize);
				if (isBuy)
				{
					if (!askFootprint.ContainsKey(priceTick)) askFootprint[priceTick] = 0;
					askFootprint[priceTick] += tickVol;
				}
				else
				{
					if (!bidFootprint.ContainsKey(priceTick)) bidFootprint[priceTick] = 0;
					bidFootprint[priceTick] += tickVol;
				}
				return;
			}

			// ── Serie Primaria (Cierre de barra) ──
			if (CurrentBar < BarsRequiredToTrade)
			{
				askFootprint.Clear();
				bidFootprint.Clear();
				return;
			}

			// Reseteo diario
			if (Time[0].Date != currentDay)
			{
				currentDay = Time[0].Date;
				dailyPnL = 0;
				tradesToday = 0;
			}

			// Control diario
			if (dailyPnL <= -Math.Abs(MaxDailyLoss) || tradesToday >= MaxDailyTrades)
			{
				if (Position.MarketPosition == MarketPosition.Long)
					ExitLong("Daily Risk Limit Reached");
				else if (Position.MarketPosition == MarketPosition.Short)
					ExitShort("Daily Risk Limit Reached");
				askFootprint.Clear();
				bidFootprint.Clear();
				return;
			}

			// Geometría de la barra en ticks enteros
			long barCloseTick = (long)Math.Round(Close[0] / TickSize);
			long barHighTick  = (long)Math.Round(High[0] / TickSize);
			long barLowTick   = (long)Math.Round(Low[0] / TickSize);
			long barRange     = Math.Max(1, barHighTick - barLowTick);

			double bullTrapVol = 0;
			double bearTrapVol = 0;

			// Detección de Imbalances diagonales en el footprint
			foreach (var kvp in askFootprint)
			{
				long tickLevel = kvp.Key;
				double askVol = kvp.Value;
				double oppositeBid = bidFootprint.ContainsKey(tickLevel - 1) ? bidFootprint[tickLevel - 1] : 0;

				// Imbalance de Compras agresivas
				if (askVol >= oppositeBid * ImbalanceRatio && askVol >= 5)
				{
					// Bull Trap: Compradores agresivos atrapados por ENCIMA del Close
					if (tickLevel > barCloseTick)
					{
						bool inUpperWick = !UseWickFilter || (tickLevel >= barHighTick - (long)Math.Round(barRange * (WickZonePct / 100.0)));
						if (inUpperWick)
							bullTrapVol += askVol;
					}
				}
			}

			foreach (var kvp in bidFootprint)
			{
				long tickLevel = kvp.Key;
				double bidVol = kvp.Value;
				double oppositeAsk = askFootprint.ContainsKey(tickLevel + 1) ? askFootprint[tickLevel + 1] : 0;

				// Imbalance de Ventas agresivas
				if (bidVol >= oppositeAsk * ImbalanceRatio && bidVol >= 5)
				{
					// Bear Trap: Vendedores agresivos atrapados por DEBAJO del Close
					if (tickLevel < barCloseTick)
					{
						bool inLowerWick = !UseWickFilter || (tickLevel <= barLowTick + (long)Math.Round(barRange * (WickZonePct / 100.0)));
						if (inLowerWick)
							bearTrapVol += bidVol;
					}
				}
			}

			// Limpieza de buffers para la siguiente barra
			askFootprint.Clear();
			bidFootprint.Clear();

			// ================================================================
			// EJECUCIÓN CON SL Y TP EN TICKS
			// ================================================================
			if (Position.MarketPosition == MarketPosition.Flat)
			{
				// 1. Bullish Absorption (Compradores atrapados en techo) -> VENDER (Short)
				if (EnableShort && bullTrapVol >= MinTrapVolume)
				{
					SetStopLoss(CalculationMode.Ticks, StopLossTicks);
					SetProfitTarget(CalculationMode.Ticks, TakeProfitTicks);
					if (EnableTrailingStop)
						SetTrailStop(CalculationMode.Ticks, TrailingStopTicks);

					EnterShort(1, "Short_BullTrap_Absorption");
					tradesToday++;
				}
				// 2. Bearish Absorption (Vendedores atrapados en piso) -> COMPRAR (Long)
				else if (EnableLong && bearTrapVol >= MinTrapVolume)
				{
					SetStopLoss(CalculationMode.Ticks, StopLossTicks);
					SetProfitTarget(CalculationMode.Ticks, TakeProfitTicks);
					if (EnableTrailingStop)
						SetTrailStop(CalculationMode.Ticks, TrailingStopTicks);

					EnterLong(1, "Long_BearTrap_Absorption");
					tradesToday++;
				}
			}
		}

		#region Propiedades de Optimización

		// ── 1. Optimización Pura de SL y TP ──
		[NinjaScriptProperty]
		[Range(5, 200)]
		[Display(Name = "Stop Loss (Ticks)", Order = 1, GroupName = "1. Optimización SL & TP", Description = "Rango para optimizar en Strategy Analyzer (ej: Min 10, Max 40, Step 5)")]
		public int StopLossTicks { get; set; }

		[NinjaScriptProperty]
		[Range(5, 500)]
		[Display(Name = "Take Profit (Ticks)", Order = 2, GroupName = "1. Optimización SL & TP", Description = "Rango para optimizar en Strategy Analyzer (ej: Min 15, Max 100, Step 5)")]
		public int TakeProfitTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Trailing Stop", Order = 3, GroupName = "1. Optimización SL & TP")]
		public bool EnableTrailingStop { get; set; }

		[NinjaScriptProperty]
		[Range(5, 100)]
		[Display(Name = "Trailing Stop (Ticks)", Order = 4, GroupName = "1. Optimización SL & TP")]
		public int TrailingStopTicks { get; set; }

		// ── 2. Parámetros BigTrap2 ──
		[NinjaScriptProperty]
		[Range(1.5, 10.0)]
		[Display(Name = "Ratio de Imbalance", Order = 1, GroupName = "2. Detección BigTrap2")]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty]
		[Range(5, 500)]
		[Display(Name = "Volumen Mínimo Trap", Order = 2, GroupName = "2. Detección BigTrap2")]
		public int MinTrapVolume { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Filtrar por Zona de Mecha", Order = 3, GroupName = "2. Detección BigTrap2")]
		public bool UseWickFilter { get; set; }

		[NinjaScriptProperty]
		[Range(10.0, 50.0)]
		[Display(Name = "% Zona de Mecha", Order = 4, GroupName = "2. Detección BigTrap2")]
		public double WickZonePct { get; set; }

		// ── 3. Reglas Prop Firm ──
		[NinjaScriptProperty]
		[Range(100.0, 10000.0)]
		[Display(Name = "Máxima Pérdida Diaria ($)", Order = 1, GroupName = "3. Reglas Prop Firm")]
		public double MaxDailyLoss { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Máximo Trades por Día", Order = 2, GroupName = "3. Reglas Prop Firm")]
		public int MaxDailyTrades { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Compras (Long)", Order = 3, GroupName = "3. Reglas Prop Firm")]
		public bool EnableLong { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Ventas (Short)", Order = 4, GroupName = "3. Reglas Prop Firm")]
		public bool EnableShort { get; set; }

		#endregion
	}
}
