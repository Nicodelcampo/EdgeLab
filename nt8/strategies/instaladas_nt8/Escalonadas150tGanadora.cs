#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
	public class Escalonadas150tGanadora : Strategy
	{
		private Escalonadas150tDetector detector;
		private int lastProcessedZoneId = -1;

		// Estado de orden pendiente (para modos con límite o retroceso)
		private bool hasPendingSetup = false;
		private int pendingDirection = 0; // +1 Long, -1 Short
		private double pendingLimitPrice = 0.0;
		private double pendingCancelPrice = 0.0;
		private int pendingSlTicks = 0;
		private int pendingTpTicks = 0;
		private int pendingBeTicks = 0;
		private int pendingQty = 1;
		private string pendingSignalName = string.Empty;
		private Order pendingEntryOrder = null;

		// Estado de la posición activa para Break-Even
		private double activeBeTriggerPrice = 0.0;
		private int activeBeTicks = 0;
		private bool activeBeMoved = false;
		private string activeEntryName = string.Empty;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Estrategia Escalonadas 150t con SL/TP atómicos en ticks y parámetros ganadores del Walk-Forward por defecto.";
				Name = "Escalonadas150tGanadora";
				Calculate = Calculate.OnBarClose;
				EntriesPerDirection = 1;
				EntryHandling = EntryHandling.AllEntries;

				// Igual que el simulador del indicador: no cerrar forzosamente al fin de sesión
				IsExitOnSessionCloseStrategy = false;
				ExitOnSessionCloseSeconds = 30;
				IsFillLimitOnTouch = false;
				TraceOrders = false;
				BarsRequiredToTrade = 20;
				IsInstantiatedOnEachOptimizationIteration = true;

				// 1. Parámetros del Detector (Ganadora Walk-Forward = 4 Picos)
				AggregationRatio = 1;
				AutoDetectAggregation = true;
				PivotsW = 1;
				MaxGapBars = 30;
				MaxStepTicks = 42;
				MinPullTicks = 14;
				NMinPeaks = 4;
				ConfTicks = 16;

				// 2. Parámetros Ganadores Walk-Forward por defecto
				ModoEntrada = TradeEntryMode.RupturaTrigger;
				TriggerComoOrdenLimite = false;
				Contratos = 1;
				DimensionarPorRiesgoUSD = false;
				RiesgoPorTradeUSD = 500.0;
				MaxContratos = 20;
				MultiplicadorSL = 0.8;
				BufferSlTicks = 0;
				BreakEvenR = 0.0;
				TakeProfitR = 5.0;
				PullbackTicks = 0;
				CancelTicks = 0;
				DibujarIndicador = false;
			}
			else if (State == State.DataLoaded)
			{
				lastProcessedZoneId = -1;
				ResetPendingState();
				ResetActiveTradeState();

				detector = Escalonadas150tDetector();
				detector.AggregationRatio = AggregationRatio;
				detector.AutoDetectAggregation = AutoDetectAggregation;
				detector.PivotsW = PivotsW;
				detector.MaxGapBars = MaxGapBars;
				detector.MaxStepTicks = MaxStepTicks;
				detector.MinPullTicks = MinPullTicks;
				detector.NMinPeaks = NMinPeaks;
				detector.ConfTicks = ConfTicks;
				detector.SimulateTrades = false;
				detector.TakeProfitR = TakeProfitR;
				detector.BreakEvenR = BreakEvenR;

				detector.EntryMode = ModoEntrada;
				detector.SlMultiplier = MultiplicadorSL;
				detector.SlBufferTicks = BufferSlTicks;
				detector.PullbackTicks = PullbackTicks;
				detector.CancelTicks = CancelTicks;
				detector.EnableIsOosOptimizer = false;
				detector.EnableCsvLogging = false;
				detector.ShowDashboard = false;
				detector.DrawZones = DibujarIndicador;

				if (DibujarIndicador)
					AddChartIndicator(detector);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < BarsRequiredToTrade || detector == null)
				return;

			detector.Update();

			// 1. Gestionar Break-Even si hay posición abierta y BreakEvenR > 0
			if (Position.MarketPosition != MarketPosition.Flat)
			{
				ManageOpenPositionBreakEven();
			}
			else
			{
				ResetActiveTradeState();
			}

			// 2. Gestionar órdenes límite pendientes
			if (hasPendingSetup && Position.MarketPosition == MarketPosition.Flat)
			{
				if (CancelTicks > 0)
				{
					bool hitCancel = (pendingDirection == 1)
						? (High[0] >= pendingCancelPrice)
						: (Low[0] <= pendingCancelPrice);

					if (hitCancel)
					{
						if (pendingEntryOrder != null &&
							(pendingEntryOrder.OrderState == OrderState.Working || pendingEntryOrder.OrderState == OrderState.Accepted))
						{
							CancelOrder(pendingEntryOrder);
						}
						ResetPendingState();
					}
				}

				if (hasPendingSetup)
				{
					SubmitPendingLimitOrder();
				}
			}

			// 3. Buscar en orden cronológico la primera zona válida de la barra actual
			if (Position.MarketPosition != MarketPosition.Flat)
				return;

			List<Escalonadas150tDetector.ZoneInfo> zones = detector.PublicZones;
			if (zones == null || zones.Count == 0)
				return;

			Escalonadas150tDetector.ZoneInfo chosenZone = null;
			for (int i = zones.Count - 1; i >= 0; i--)
			{
				Escalonadas150tDetector.ZoneInfo z = zones[i];
				if (z.ChartBarIndex < CurrentBar)
					break;

				if (z.ChartBarIndex == CurrentBar && z.ZoneId > lastProcessedZoneId && z.PeakIndices.Count == NMinPeaks)
				{
					chosenZone = z;
				}
			}

			if (chosenZone != null)
			{
				// Marcar como procesadas todas las zonas de esta barra para no enviar múltiples órdenes superpuestas
				lastProcessedZoneId = zones[zones.Count - 1].ZoneId;
				ProcessNewZone(chosenZone);
			}
		}

		private void ProcessNewZone(Escalonadas150tDetector.ZoneInfo z)
		{
			if (Position.MarketPosition != MarketPosition.Flat)
				return;

			if (hasPendingSetup && pendingEntryOrder != null)
			{
				CancelOrder(pendingEntryOrder);
				ResetPendingState();
			}

			int dir = (z.Kind == "L") ? 1 : -1;
			double p1 = (z.PeakPrices != null && z.PeakPrices.Count > 0)
				? z.PeakPrices[0]
				: (z.DetPrice - dir * 20 * TickSize);

			string sigName = (dir == 1 ? "EscLong_" : "EscShort_") + z.ZoneId;

			if (ModoEntrada == TradeEntryMode.RetesteoPico)
			{
				PreparePendingOrder(dir, z.DetLevel, z.DetPrice, p1, sigName);
			}
			else if (ModoEntrada == TradeEntryMode.RupturaTrigger)
			{
				if (TriggerComoOrdenLimite)
				{
					PreparePendingOrder(dir, z.DetTriggerPrice, z.DetPrice, p1, sigName);
				}
				else
				{
					// Calculamos 1R exactamente igual que el indicador (usando DetTriggerPrice como referencia)
					ExecuteImmediateEntry(dir, z.DetTriggerPrice, p1, sigName);
				}
			}
			else // ConfirmacionCierre (Punto Azul)
			{
				if (PullbackTicks > 0)
				{
					double pbPrice = z.DetPrice - dir * PullbackTicks * TickSize;
					PreparePendingOrder(dir, pbPrice, z.DetPrice, p1, sigName);
				}
				else
				{
					ExecuteImmediateEntry(dir, z.DetPrice, p1, sigName);
				}
			}
		}

		private void CalculateRiskTicksAndQty(double entryRef, double p1Price, out int slTicks, out int tpTicks, out int beTicks, out int qty)
		{
			double baseDist = Math.Abs(entryRef - p1Price) / 2.0;
			double mult = (MultiplicadorSL > 0.05) ? MultiplicadorSL : 1.0;
			double dist1R = Math.Round(baseDist * mult + (BufferSlTicks > 0 ? BufferSlTicks * TickSize : 0.0), 2);
			if (dist1R < 2 * TickSize)
				dist1R = 2 * TickSize;

			slTicks = Math.Max(2, (int)Math.Round(dist1R / TickSize));
			tpTicks = Math.Max(2, (int)Math.Round((dist1R * TakeProfitR) / TickSize));
			beTicks = (BreakEvenR > 0.0) ? Math.Max(1, (int)Math.Round((dist1R * BreakEvenR) / TickSize)) : 0;

			if (DimensionarPorRiesgoUSD && Instrument != null && Instrument.MasterInstrument.PointValue > 0)
			{
				double tickValue = Instrument.MasterInstrument.PointValue * TickSize;
				double riskPerContract = slTicks * tickValue;
				int calcQty = (riskPerContract > 0) ? (int)Math.Round(RiesgoPorTradeUSD / riskPerContract) : Contratos;
				qty = Math.Max(1, Math.Min(MaxContratos, calcQty));
			}
			else
			{
				qty = Contratos;
			}
		}

		private void ExecuteImmediateEntry(int dir, double refPriceFor1R, double p1Price, string sigName)
		{
			int slTicks, tpTicks, beTicks, qty;
			CalculateRiskTicksAndQty(refPriceFor1R, p1Price, out slTicks, out tpTicks, out beTicks, out qty);

			// Vincular SL y TP en ticks de forma atómica antes de enviar la orden de entrada
			SetStopLoss(sigName, CalculationMode.Ticks, slTicks, false);
			SetProfitTarget(sigName, CalculationMode.Ticks, tpTicks);

			activeEntryName = sigName;
			activeBeTicks = beTicks;
			activeBeMoved = false;
			activeBeTriggerPrice = 0.0;

			if (dir == 1)
				EnterLong(qty, sigName);
			else
				EnterShort(qty, sigName);
		}

		private void PreparePendingOrder(int dir, double rawLimitPrice, double detPrice, double p1Price, string sigName)
		{
			int slTicks, tpTicks, beTicks, qty;
			CalculateRiskTicksAndQty(rawLimitPrice, p1Price, out slTicks, out tpTicks, out beTicks, out qty);

			hasPendingSetup = true;
			pendingDirection = dir;
			pendingLimitPrice = Instrument.MasterInstrument.RoundToTickSize(rawLimitPrice);
			pendingCancelPrice = Instrument.MasterInstrument.RoundToTickSize(detPrice + dir * CancelTicks * TickSize);
			pendingSlTicks = slTicks;
			pendingTpTicks = tpTicks;
			pendingBeTicks = beTicks;
			pendingQty = qty;
			pendingSignalName = sigName;

			SubmitPendingLimitOrder();
		}

		private void SubmitPendingLimitOrder()
		{
			SetStopLoss(pendingSignalName, CalculationMode.Ticks, pendingSlTicks, false);
			SetProfitTarget(pendingSignalName, CalculationMode.Ticks, pendingTpTicks);

			activeEntryName = pendingSignalName;
			activeBeTicks = pendingBeTicks;
			activeBeMoved = false;

			if (pendingDirection == 1)
				pendingEntryOrder = EnterLongLimit(0, true, pendingQty, pendingLimitPrice, pendingSignalName);
			else
				pendingEntryOrder = EnterShortLimit(0, true, pendingQty, pendingLimitPrice, pendingSignalName);
		}

		private void ManageOpenPositionBreakEven()
		{
			if (activeBeMoved || BreakEvenR <= 0.0 || activeBeTicks <= 0 || string.IsNullOrEmpty(activeEntryName))
				return;

			int dir = (Position.MarketPosition == MarketPosition.Long) ? 1 : -1;
			double avgPrice = Position.AveragePrice;
			activeBeTriggerPrice = Instrument.MasterInstrument.RoundToTickSize(avgPrice + dir * activeBeTicks * TickSize);

			bool reachedBe = (dir == 1)
				? (High[0] >= activeBeTriggerPrice)
				: (Low[0] <= activeBeTriggerPrice);

			if (reachedBe)
			{
				activeBeMoved = true;
				SetStopLoss(activeEntryName, CalculationMode.Price, Instrument.MasterInstrument.RoundToTickSize(avgPrice), false);
			}
		}

		protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
		{
			if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
				return;

			if (execution.Order.Name == activeEntryName || execution.Order.Name == pendingSignalName)
			{
				hasPendingSetup = false;
				pendingEntryOrder = null;
			}
		}

		private void ResetPendingState()
		{
			hasPendingSetup = false;
			pendingDirection = 0;
			pendingLimitPrice = 0.0;
			pendingCancelPrice = 0.0;
			pendingSlTicks = 0;
			pendingTpTicks = 0;
			pendingBeTicks = 0;
			pendingQty = 1;
			pendingSignalName = string.Empty;
			pendingEntryOrder = null;
		}

		private void ResetActiveTradeState()
		{
			activeBeTriggerPrice = 0.0;
			activeBeTicks = 0;
			activeBeMoved = false;
			activeEntryName = string.Empty;
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Ratio Agregación", Order = 1, GroupName = "1. Detector Escalonadas")]
		public int AggregationRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Auto-detectar Período", Order = 2, GroupName = "1. Detector Escalonadas")]
		public bool AutoDetectAggregation { get; set; }

		[NinjaScriptProperty]
		[Range(1, 10)]
		[Display(Name = "Pivotes W", Order = 3, GroupName = "1. Detector Escalonadas")]
		public int PivotsW { get; set; }

		[NinjaScriptProperty]
		[Range(5, 100)]
		[Display(Name = "Max Gap (Velas)", Order = 4, GroupName = "1. Detector Escalonadas")]
		public int MaxGapBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name = "Max Step (Ticks)", Order = 5, GroupName = "1. Detector Escalonadas")]
		public int MaxStepTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Min Pull (Ticks)", Order = 6, GroupName = "1. Detector Escalonadas")]
		public int MinPullTicks { get; set; }

		[NinjaScriptProperty]
		[Range(2, 20)]
		[Display(Name = "Mínimo Picos (4 o 5)", Order = 7, GroupName = "1. Detector Escalonadas")]
		public int NMinPeaks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Confirmación (Ticks)", Order = 8, GroupName = "1. Detector Escalonadas")]
		public int ConfTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo de Entrada", Order = 1, GroupName = "2. Gestión de Orden y Riesgo")]
		public TradeEntryMode ModoEntrada { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Trigger como Orden Límite", Description = "En modo RupturaTrigger, envía orden límite en DetTriggerPrice en vez de orden a mercado al cierre", Order = 2, GroupName = "2. Gestión de Orden y Riesgo")]
		public bool TriggerComoOrdenLimite { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Contratos Fijos", Order = 3, GroupName = "2. Gestión de Orden y Riesgo")]
		public int Contratos { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dimensionar por Riesgo ($)", Description = "Ajusta contratos según el tamaño del SL para igualar el riesgo en dólares de cada trade (similar a medir en unidades R)", Order = 4, GroupName = "2. Gestión de Orden y Riesgo")]
		public bool DimensionarPorRiesgoUSD { get; set; }

		[NinjaScriptProperty]
		[Range(10.0, 100000.0)]
		[Display(Name = "Riesgo Base por Trade ($)", Order = 5, GroupName = "2. Gestión de Orden y Riesgo")]
		public double RiesgoPorTradeUSD { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name = "Máximo Contratos", Order = 6, GroupName = "2. Gestión de Orden y Riesgo")]
		public int MaxContratos { get; set; }

		[NinjaScriptProperty]
		[Range(0.2, 10.0)]
		[Display(Name = "Multiplicador SL (Factor 1R)", Order = 7, GroupName = "2. Gestión de Orden y Riesgo")]
		public double MultiplicadorSL { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Buffer Extra SL (Ticks)", Order = 8, GroupName = "2. Gestión de Orden y Riesgo")]
		public int BufferSlTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Break-Even (R)", Order = 9, GroupName = "2. Gestión de Orden y Riesgo")]
		public double BreakEvenR { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 20.0)]
		[Display(Name = "Take Profit (R)", Order = 10, GroupName = "2. Gestión de Orden y Riesgo")]
		public double TakeProfitR { get; set; }

		[NinjaScriptProperty]
		[Range(0, 200)]
		[Display(Name = "Pullback para Entrar (Ticks)", Order = 11, GroupName = "2. Gestión de Orden y Riesgo")]
		public int PullbackTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0, 500)]
		[Display(Name = "Cancelación si se Aleja (Ticks)", Order = 12, GroupName = "2. Gestión de Orden y Riesgo")]
		public int CancelTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Zonas del Indicador", Order = 1, GroupName = "3. Visualización")]
		public bool DibujarIndicador { get; set; }
		#endregion
	}
}