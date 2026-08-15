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
// SchermanQuantReversion.cs — Estrategia Cuantitativa Adaptativa (Multi-Timeframe)
// Optimizada para alta frecuencia: Gráficos de Segundos (15s, 30s), Minutos o Ticks.
// Inspirada en la metodología de trading algorítmico de Iván Scherman
// (Ganador World Cup Championship of Futures Trading 2023, +491.4%).
//
// CARACTERÍSTICAS DE ALTA FRECUENCIA:
// 1. Detección Ágil de Agotamiento: Bollinger Bands ajustables (2.0 std) + RSI(3).
// 2. Filtro de Régimen Dinámico: Kaufman Efficiency Ratio (KER).
// 3. Protección de Ganancias: Break-Even automático tras avance inicial.
// 4. Salidas Rápidas: Reversión al centro (SMA 20), Time Stop o Stop ATR dinámico.
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
		private double entryPrice = 0;
		private bool beTriggered = false;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Estrategia Cuantitativa Adaptativa de Reversión y Agotamiento (Alta Frecuencia / Segundos / Minutos).";
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
				BarsRequiredToTrade							= 30;

				// 1. Detección Ágil de Agotamiento (Optimizado para Segundos / 1 Minuto)
				BbPeriod									= 20;
				BbStdDev									= 2.0;   // 2.0 para mayor frecuencia de disparo
				RsiPeriod									= 3;
				RsiOversold									= 18.0;  // 18.0 para capturar más zonas de sobreventa
				RsiOverbought								= 82.0;  // 82.0 para capturar más zonas de sobrecompra

				// 2. Filtro de Régimen y Volumen
				KerPeriod									= 10;
				MaxKerThreshold								= 0.60;  // 0.60 permite operar en más regímenes
				UseVolumeFilter								= false; // Desactivable en gráficos de segundos
				VolFactor									= 1.0;

				// 3. Salidas Cuantitativas y Gestión de Riesgo
				AtrPeriod									= 14;
				AtrStopMultiplier							= 1.5;
				MaxBarsInTrade								= 15;    // Más barras para permitir maduración en segundos
				ExitAtMiddleBand							= true;  // Salida natural en la media central
				EnableBreakEven								= true;  // Mover Stop a Break-Even
				BreakEvenAtrMultiplier						= 0.8;   // Cuando avance 0.8x ATR, asegurar entrada

				// 4. Parámetros de Prop Firm
				MaxDailyLoss								= 1000.0;
				MaxDailyTrades								= 20;    // Apto para más operaciones por día
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

				AddChartIndicator(bollinger);
				AddChartIndicator(rsi);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < Math.Max(30, Math.Max(BbPeriod, Math.Max(RsiPeriod, KerPeriod))))
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

			// 2. Condición de Régimen
			bool isAllowedRegime = ker <= MaxKerThreshold;

			// 3. Confirmación de Volumen (opcional)
			bool isVolumeOk = !UseVolumeFilter || (Volume[0] >= (smaVol[0] * VolFactor));

			// ================================================================
			// GESTIÓN DE POSICIÓN ACTIVA
			// ================================================================
			if (Position.MarketPosition == MarketPosition.Long)
			{
				barsInPosition++;

				// A. Break-Even Dinámico
				if (EnableBreakEven && !beTriggered)
				{
					if (Close[0] >= entryPrice + (atr[0] * BreakEvenAtrMultiplier))
					{
						SetStopLoss(CalculationMode.Price, entryPrice + (TickSize * 1));
						beTriggered = true;
					}
				}

				// B. Take Profit: Reversión al Centro (Media Central)
				if (ExitAtMiddleBand && Close[0] >= bollinger.Middle[0])
				{
					ExitLong("TP_MiddleBand_L");
					barsInPosition = 0;
					return;
				}

				// C. Time Stop: Salida tras N barras
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

				// A. Break-Even Dinámico
				if (EnableBreakEven && !beTriggered)
				{
					if (Close[0] <= entryPrice - (atr[0] * BreakEvenAtrMultiplier))
					{
						SetStopLoss(CalculationMode.Price, entryPrice - (TickSize * 1));
						beTriggered = true;
					}
				}

				// B. Take Profit: Reversión al Centro (Media Central)
				if (ExitAtMiddleBand && Close[0] <= bollinger.Middle[0])
				{
					ExitShort("TP_MiddleBand_S");
					barsInPosition = 0;
					return;
				}

				// C. Time Stop: Salida tras N barras
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
			if (Position.MarketPosition == MarketPosition.Flat && isAllowedRegime && isVolumeOk)
			{
				double stopDistance = atr[0] * AtrStopMultiplier;

				// --- ENTRADA LARGA (Sobreventa Extrema) ---
				if (EnableLong && Close[0] < bollinger.Lower[0] && rsi[0] <= RsiOversold)
				{
					entryPrice = Close[0];
					beTriggered = false;
					SetStopLoss(CalculationMode.Price, Close[0] - stopDistance);
					EnterLong(1, "Long_Exhaustion");
					barsInPosition = 0;
					tradesToday++;
				}
				// --- ENTRADA CORTA (Sobrecompra Extrema) ---
				else if (EnableShort && Close[0] > bollinger.Upper[0] && rsi[0] >= RsiOverbought)
				{
					entryPrice = Close[0];
					beTriggered = false;
					SetStopLoss(CalculationMode.Price, Close[0] + stopDistance);
					EnterShort(1, "Short_Exhaustion");
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
				beTriggered = false;
			}
		}

		#region Propiedades Configurables en NinjaTrader

		// ── 1. Detección de Agotamiento ──
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
		[Range(1.0, 40.0)]
		[Display(Name = "Umbral Sobreventa RSI", Order = 4, GroupName = "1. Detección de Agotamiento")]
		public double RsiOversold { get; set; }

		[NinjaScriptProperty]
		[Range(60.0, 99.0)]
		[Display(Name = "Umbral Sobrecompra RSI", Order = 5, GroupName = "1. Detección de Agotamiento")]
		public double RsiOverbought { get; set; }

		// ── 2. Filtro de Régimen y Volumen ──
		[NinjaScriptProperty]
		[Range(3, 50)]
		[Display(Name = "Período KER (Kaufman)", Order = 1, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public int KerPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 1.0)]
		[Display(Name = "Máximo Umbral KER", Order = 2, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public double MaxKerThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Usar Filtro de Volumen", Order = 3, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public bool UseVolumeFilter { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 3.0)]
		[Display(Name = "Factor de Volumen Relativo", Order = 4, GroupName = "2. Filtro de Régimen (Kaufman)")]
		public double VolFactor { get; set; }

		// ── 3. Salidas Cuantitativas y Break-Even ──
		[NinjaScriptProperty]
		[Range(5, 50)]
		[Display(Name = "Período ATR (Stop Dinámico)", Order = 1, GroupName = "3. Salidas Cuantitativas")]
		public int AtrPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 5.0)]
		[Display(Name = "Multiplicador ATR Stop Loss", Order = 2, GroupName = "3. Salidas Cuantitativas")]
		public double AtrStopMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Time Stop (Max Barras en Trade)", Order = 3, GroupName = "3. Salidas Cuantitativas")]
		public int MaxBarsInTrade { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Take Profit en Media Central", Order = 4, GroupName = "3. Salidas Cuantitativas")]
		public bool ExitAtMiddleBand { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Habilitar Break-Even Dinámico", Order = 5, GroupName = "3. Salidas Cuantitativas")]
		public bool EnableBreakEven { get; set; }

		[NinjaScriptProperty]
		[Range(0.2, 3.0)]
		[Display(Name = "Avance ATR para Break-Even", Order = 6, GroupName = "3. Salidas Cuantitativas")]
		public double BreakEvenAtrMultiplier { get; set; }

		// ── 4. Reglas Prop Firm ──
		[NinjaScriptProperty]
		[Range(100.0, 10000.0)]
		[Display(Name = "Máxima Pérdida Diaria ($)", Order = 1, GroupName = "4. Reglas Prop Firm")]
		public double MaxDailyLoss { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
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
