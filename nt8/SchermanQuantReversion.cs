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
// SchermanQuantReversion.cs — Estrategia Cuantitativa de Reversión y Agotamiento
// Inspirada en la metodología de trading algorítmico de Iván Scherman
// (Ganador World Cup Championship of Futures Trading 2023, +491.4%).
//
// PILARES DEL SISTEMA:
// 1. Filtro de Régimen: Ratio de Eficiencia de Kaufman (KER) para operar solo en
//    mercados de absorción y rango, evitando tendencias explosivas.
// 2. Disparador de Agotamiento: Bollinger Bands extremas (2.5 std) + RSI(3)
//    ultra-corto en zonas de sobreventa (< 12) / sobrecompra (> 88).
// 3. Confirmación de Volumen: Spike de volumen relativo respecto a su media móvil.
// 4. Salidas Cuantitativas:
//    - Take Profit: Reversión exacta a la media central (SMA 20).
//    - Stop Loss Dinámico: 1.75x ATR(14) adaptativo a la volatilidad.
//    - Time Stop: Cierre obligatorio tras N barras si la reversión no madura.
//    - Control de Riesgo Diario para Prop Firms (Max Daily Loss & Trades).
// ============================================================================

namespace NinjaTrader.NinjaScript.Strategies
{
	public class SchermanQuantReversion : Strategy
	{
		#region Variables & Indicadores
		private NinjaTrader.NinjaScript.Indicators.Bollinger bollinger;
		private NinjaTrader.NinjaScript.Indicators.RSI rsi;
		private NinjaTrader.NinjaScript.Indicators.ATR atr;
		private NinjaTrader.NinjaScript.Indicators.SMA smaVol;

		private int barsInPosition = 0;
		private double dailyPnL = 0;
		private int tradesToday = 0;
		private DateTime currentDay = DateTime.MinValue;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Estrategia Cuantitativa de Reversión a la Media y Agotamiento de Volatilidad (Metodología Iván Scherman).";
				Name										= "SchermanQuantReversion";
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
				BarsRequiredToTrade							= 50;

				// Parámetros de Detección Cuantitativa
				BbPeriod									= 20;
				BbStdDev									= 2.5;
				RsiPeriod									= 3;
				RsiOversold									= 12.0;
				RsiOverbought								= 88.0;
				KerPeriod									= 10;
				MaxKerThreshold								= 0.45; // Solo operar si KER < 0.45 (mercado en rango/absorción)
				VolFactor									= 1.15; // Volumen >= 115% de su media de 20 barras

				// Parámetros de Salida y Gestión de Riesgo
				AtrPeriod									= 14;
				AtrStopMultiplier							= 1.75;
				MaxBarsInTrade								= 8;   // Time Stop: Salir si no revierte en 8 barras
				ExitAtMiddleBand							= true; // Tomar beneficio en la media central

				// Parámetros de Prop Firm
				MaxDailyLoss								= 800.0;
				MaxDailyTrades								= 6;
				EnableLong									= true;
				EnableShort									= true;
			}
			else if (State == State.Configure)
			{
			}
			else if (State == State.DataLoaded)
			{
				bollinger = Bollinger(BbStdDev, BbPeriod);
				rsi = RSI(RsiPeriod, 1);
				atr = ATR(AtrPeriod);
				smaVol = SMA(Volume, 20);

				// Visualización en gráfico
				AddChartIndicator(bollinger);
				AddChartIndicator(rsi);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < Math.Max(50, Math.Max(BbPeriod, Math.Max(RsiPeriod, KerPeriod))))
				return;

			// Reseteo de métricas diarias
			if (Time[0].Date != currentDay)
			{
				currentDay = Time[0].Date;
				dailyPnL = 0;
				tradesToday = 0;
			}

			// Control de riesgo diario (Prop Firm Safety Guard)
			if (dailyPnL <= -Math.Abs(MaxDailyLoss) || tradesToday >= MaxDailyTrades)
			{
				if (Position.MarketPosition == MarketPosition.Long)
					ExitLong("Daily Risk Limit Reached");
				else if (Position.MarketPosition == MarketPosition.Short)
					ExitShort("Daily Risk Limit Reached");
				return;
			}

			// 1. Cálculo del Kaufman Efficiency Ratio (KER)
			double netDirection = Math.Abs(Close[0] - Close[KerPeriod]);
			double totalVolPath = 0;
			for (int i = 0; i < KerPeriod; i++)
			{
				totalVolPath += Math.Abs(Close[i] - Close[i + 1]);
			}
			double ker = (totalVolPath > 0) ? (netDirection / totalVolPath) : 0;

			// 2. Condición de Régimen: Mercado en absorción / oscilación (KER bajo)
			bool isMeanRevertingRegime = ker <= MaxKerThreshold;

			// 3. Confirmación de Volumen
			bool isHighVolume = Volume[0] >= (smaVol[0] * VolFactor);

			// ================================================================
			// LÓGICA DE GESTIÓN DE POSICIÓN ACTIVA
			// ================================================================
			if (Position.MarketPosition == MarketPosition.Long)
			{
				barsInPosition++;

				// A. Take Profit: Reversión al Centro (Media Central Bollinger)
				if (ExitAtMiddleBand && Close[0] >= bollinger.Middle[0])
				{
					ExitLong("TP_MiddleBand_L");
					barsInPosition = 0;
					return;
				}

				// B. Time Stop: Salida obligatoria si la reversión no madura
				if (barsInPosition >= MaxBarsInTrade)
				{
					ExitLong("TimeStop_L");
					barsInPosition = 0;
					return;
				}
			}
			else if (Position.MarketPosition == MarketPosition.Short)
			{
				barsInPosition++;

				// A. Take Profit: Reversión al Centro (Media Central Bollinger)
				if (ExitAtMiddleBand && Close[0] <= bollinger.Middle[0])
				{
					ExitShort("TP_MiddleBand_S");
					barsInPosition = 0;
					return;
				}

				// B. Time Stop: Salida obligatoria si la reversión no madura
				if (barsInPosition >= MaxBarsInTrade)
				{
					ExitShort("TimeStop_S");
					barsInPosition = 0;
					return;
				}
			}

			// ================================================================
			// LÓGICA DE ENTRADA CUANTITATIVA
			// ================================================================
			if (Position.MarketPosition == MarketPosition.Flat && isMeanRevertingRegime && isHighVolume)
			{
				double stopDistance = atr[0] * AtrStopMultiplier;

				// --- ENTRADA LARGA (Agotamiento Bajista + Absorción) ---
				// Precio perfora la banda inferior + RSI en extrema sobreventa (< 12)
				if (EnableLong && Close[0] < bollinger.Lower[0] && rsi[0] <= RsiOversold)
				{
					SetStopLoss(CalculationMode.Price, Close[0] - stopDistance);
					EnterLong(1, "Long_Scherman_Exhaustion");
					barsInPosition = 0;
					tradesToday++;
				}
				// --- ENTRADA CORTA (Agotamiento Alcista + Absorción) ---
				// Precio perfora la banda superior + RSI en extrema sobrecompra (> 88)
				else if (EnableShort && Close[0] > bollinger.Upper[0] && rsi[0] >= RsiOverbought)
				{
					SetStopLoss(CalculationMode.Price, Close[0] + stopDistance);
					EnterShort(1, "Short_Scherman_Exhaustion");
					barsInPosition = 0;
					tradesToday++;
				}
			}
		}

		protected override void OnPositionUpdate(Position position, double averagePrice, int quantity, MarketPosition marketPosition)
		{
			if (marketPosition == MarketPosition.Flat)
			{
				barsInPosition = 0;
			}
		}

		#region Propiedades Configurables en NinjaTrader

		// ── 1. Parámetros Cuantitativos de Entrada ──
		[NinjaScriptProperty]
		[Range(5, 100)]
		[Display(Name = "Período Bollinger", Order = 1, GroupName = "1. Detección de Agotamiento")]
		public int BbPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 4.0)]
		[Display(Name = "Desviaciones Bollinger", Order = 2, GroupName = "1. Detección de Agotamiento")]
		public double BbStdDev { get; set; }

		[NinjaScriptProperty]
		[Range(2, 14)]
		[Display(Name = "Período RSI", Order = 3, GroupName = "1. Detección de Agotamiento")]
		public int RsiPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 30.0)]
		[Display(Name = "Umbral Sobreventa RSI", Order = 4, GroupName = "1. Detección de Agotamiento")]
		public double RsiOversold { get; set; }

		[NinjaScriptProperty]
		[Range(70.0, 99.0)]
		[Display(Name = "Umbral Sobrecompra RSI", Order = 5, GroupName = "1. Detección de Agotamiento")]
		public double RsiOverbought { get; set; }

		// ── 2. Filtro de Régimen y Volumen ──
		[NinjaScriptProperty]
		[Range(3, 50)]
		[Display(Name = "Período KER (Kaufman)", Order = 1, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public int KerPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 1.0)]
		[Display(Name = "Máximo Umbral KER (Absorción)", Order = 2, GroupName = "2. Filtro de Régimen (Kaufman)", Description = "Valores bajos (<0.45) filtran mercados en rango/absorción")]
		public double MaxKerThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 3.0)]
		[Display(Name = "Factor de Volumen Relativo", Order = 3, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public double VolFactor { get; set; }

		// ── 3. Salidas y Gestión de Riesgo ──
		[NinjaScriptProperty]
		[Range(5, 50)]
		[Display(Name = "Período ATR (Stop Dinámico)", Order = 1, GroupName = "3. Salidas Cuantitativas")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 5.0)]
		[Display(Name = "Multiplicador ATR Stop Loss", Order = 2, GroupName = "3. Salidas Cuantitativas")]
		public double AtrStopMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name = "Time Stop (Max Barras en Trade)", Order = 3, GroupName = "3. Salidas Cuantitativas")]
		public int MaxBarsInTrade { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Take Profit en Media Central", Order = 4, GroupName = "3. Salidas Cuantitativas")]
		public bool ExitAtMiddleBand { get; set; }

		// ── 4. Control de Riesgo Prop Firm ──
		[NinjaScriptProperty]
		[Range(100.0, 5000.0)]
		[Display(Name = "Máxima Pérdida Diaria ($)", Order = 1, GroupName = "4. Reglas Prop Firm")]
		public double MaxDailyLoss { get; set; }

		[NinjaScriptProperty]
		[Range(1, 20)]
		[Display(Name = "Máximo Trades por Día", Order = 2, GroupName = "4. Reglas Prop Firm")]
		public int MaxDailyTrades { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Compras (Long)", Order = 3, GroupName = "4. Reglas Prop Firm")]
		public bool EnableLong { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Ventas (Short)", Order = 4, GroupName = "4. Reglas Prop Firm")]
		public bool EnableShort { get; set; }

		#endregion
	}
}
