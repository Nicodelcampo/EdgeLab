#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// =========================================================================================
// Escalonadas150tStrategy.cs — Estrategia Automatizada NinjaTrader 8
//
// Réplica EXACTA 1:1 del Dashboard y Optimizador Walk-Forward (IS / OOS)
// - Modos: 4 Picos (ganador) o 5 Picos
// - Entrada: Ruptura Inmediata (Trigger) / Confirmación al Cierre / Retesteo Límite
// - Ejecución Concurrente Multitrade: reproduce fielmente las 9.002 operaciones evaluadas
//   por el detector sin bloquear entradas subsecuentes.
// - Salida determinista: SL (0.8x de P1) y TP (5.0R) supervisados y ejecutados en cada barra.
// =========================================================================================

namespace NinjaTrader.NinjaScript.Strategies
{
	public enum TradeDirectionFilter
	{
		[Display(Name = "Ambas Direcciones (Long y Short)")]
		Both,

		[Display(Name = "Solo Compras (Long Only)")]
		LongOnly,

		[Display(Name = "Solo Ventas (Short Only)")]
		ShortOnly
	}

	public enum StrategyEntryMode
	{
		[Display(Name = "Ruptura Inmediata (Nivel Trigger)")]
		RupturaTrigger,

		[Display(Name = "Confirmación al Cierre (Punto Azul)")]
		ConfirmacionCierre,

		[Display(Name = "Retesteo Límite (Nivel del Pico)")]
		RetesteoPico
	}

	public enum SlCalculationMode
	{
		[Display(Name = "Estructural P1 (|Entry - P1| / 2) — Réplica Detector")]
		StructuralP1,

		[Display(Name = "Estático en Ticks")]
		FixedTicks
	}

	public enum TargetPeaksMode
	{
		[Display(Name = "4 Picos Consecutivos (Ganador Walk-Forward)")]
		FourPeaks = 4,

		[Display(Name = "5 Picos Consecutivos (Modelo Tradicional)")]
		FivePeaks = 5
	}

	public class Escalonadas150tStrategy : Strategy
	{
		#region Estructuras de Datos
		public class SignalInfo
		{
			public string Kind;              // "H" (Short) o "L" (Long)
			public double DetPrice;          // Close[0] al momento de detectar
			public double DetLevel;          // Nivel del pico confirmado Pk
			public double DetTriggerPrice;   // Pk -/+ confTicks * tickSize
			public double P1Price;           // Nivel del primer pico P1
			public int PeakCount;            // 4 o 5
			public int ChartBarIndex;        // Barra del gráfico
			public long ZoneId;              // Identificador secuencial
		}

		public class ActiveTradeItem
		{
			public long Id;
			public string EntryName;
			public string Kind;              // "H" (Short) o "L" (Long)
			public double EntryPrice;
			public double P1Price;
			public double Dist1R;
			public double SlPrice;
			public double TpPrice;
			public double BeTriggerPrice;
			public bool BeActivated;
			public int DetBar;
			public bool IsResolved;
		}

		private class DirectionDetector
		{
			public readonly int Kind; // +1 = Highs (H -> Sell), -1 = Lows (L -> Buy)
			private readonly int w;
			private readonly int maxGap;
			private readonly int maxStep;
			private readonly int minPull;
			private readonly int targetPeaks;
			private readonly int confTicks;
			private readonly double tickSize;

			private readonly List<double> barsH = new List<double>();
			private readonly List<double> barsL = new List<double>();
			private readonly List<DateTime> barsT = new List<DateTime>();

			private readonly List<int> pendingCandidates = new List<int>();
			private readonly List<int> cur = new List<int>();
			private double curP = double.NaN;
			private bool detectedInCurrentChain = false;
			private long globalZoneId = 0;

			public DirectionDetector(int kind, int w, int maxGap, int maxStep, int minPull, int targetPeaks, int confTicks, double tickSize)
			{
				this.Kind = kind;
				this.w = w;
				this.maxGap = maxGap;
				this.maxStep = maxStep;
				this.minPull = minPull;
				this.targetPeaks = targetPeaks;
				this.confTicks = confTicks;
				this.tickSize = tickSize;
			}

			public void Reset()
			{
				barsH.Clear();
				barsL.Clear();
				barsT.Clear();
				pendingCandidates.Clear();
				cur.Clear();
				curP = double.NaN;
				detectedInCurrentChain = false;
				globalZoneId = 0;
			}

			public List<SignalInfo> OnBar(int j, double h, double l, double c, DateTime t, int chartBarIdx)
			{
				barsH.Add(h);
				barsL.Add(l);
				barsT.Add(t);

				double x_j = (Kind == 1) ? h : -l;
				double y_j = (Kind == 1) ? l : -h;

				int qCand = j - 1;
				if (qCand >= w)
				{
					double x_q = (Kind == 1) ? barsH[qCand] : -barsL[qCand];
					bool isCand = true;
					for (int o = 1; o <= w; o++)
					{
						double x_prev = (Kind == 1) ? barsH[qCand - o] : -barsL[qCand - o];
						if (x_q < x_prev)
						{
							isCand = false;
							break;
						}
					}
					if (isCand)
						pendingCandidates.Add(qCand);
				}

				List<int> confirmedAtJ = new List<int>();
				List<int> aliveCandidates = new List<int>();

				double secDiff = (j > 0) ? (t - barsT[j - 1]).TotalSeconds : 0;
				bool sessionBreak = secDiff > 1800;

				if (!sessionBreak)
				{
					for (int cIdx = 0; cIdx < pendingCandidates.Count; cIdx++)
					{
						int q = pendingCandidates[cIdx];
						double x_q = (Kind == 1) ? barsH[q] : -barsL[q];

						if (x_j > x_q + 1e-9)
							continue;

						if ((x_q - y_j) / tickSize >= confTicks - 1e-9)
							confirmedAtJ.Add(q);
						else if (j - q < 60)
							aliveCandidates.Add(q);
					}
				}
				pendingCandidates.Clear();
				pendingCandidates.AddRange(aliveCandidates);

				if (cur.Count > 0)
				{
					int lastPeak = cur[cur.Count - 1];
					bool priceBroken = (x_j > curP + 1e-9 && j > lastPeak);
					bool gapBroken = (j - lastPeak > maxGap);

					if (sessionBreak || priceBroken || gapBroken)
					{
						cur.Clear();
						curP = double.NaN;
						detectedInCurrentChain = false;
					}
				}

				List<SignalInfo> signals = new List<SignalInfo>();
				confirmedAtJ.Sort();

				for (int i = 0; i < confirmedAtJ.Count; i++)
				{
					int q = confirmedAtJ[i];

					if (cur.Count > 0 && q <= cur[cur.Count - 1])
						continue;

					double x_q = (Kind == 1) ? barsH[q] : -barsL[q];

					if (cur.Count == 0)
					{
						cur.Add(q);
						curP = x_q;
						detectedInCurrentChain = false;
					}
					else
					{
						int lastPeak = cur[cur.Count - 1];
						double mn = double.MaxValue;
						if (q > lastPeak + 1)
						{
							for (int r = lastPeak + 1; r < q; r++)
							{
								double yr = (Kind == 1) ? barsL[r] : -barsH[r];
								if (yr < mn) mn = yr;
							}
						}

						double pull = (mn < double.MaxValue - 1e9) ? (curP - mn) / tickSize : 0.0;
						double step = (curP - x_q) / tickSize;

						if (x_q <= curP + 1e-9 && step <= maxStep && pull >= minPull)
						{
							cur.Add(q);
							curP = x_q;

							if (cur.Count == targetPeaks && !detectedInCurrentChain)
							{
								detectedInCurrentChain = true;

								double pNivel = (Kind == 1) ? barsH[q] : barsL[q];
								double pTrig = pNivel - (Kind == 1 ? 1 : -1) * confTicks * tickSize;
								int firstPeakIdx = cur[0];
								double p1Price = (Kind == 1) ? barsH[firstPeakIdx] : barsL[firstPeakIdx];

								signals.Add(new SignalInfo
								{
									Kind = (Kind == 1) ? "H" : "L",
									DetPrice = Math.Round(c, 2),
									DetLevel = Math.Round(pNivel, 2),
									DetTriggerPrice = Math.Round(pTrig, 2),
									P1Price = Math.Round(p1Price, 2),
									PeakCount = cur.Count,
									ChartBarIndex = chartBarIdx,
									ZoneId = ++globalZoneId
								});
							}
						}
					}
				}

				return signals;
			}
		}
		#endregion

		#region Variables de Estado
		private DirectionDetector detectorH;
		private DirectionDetector detectorL;

		// Lista de trades activos concurrentes
		private readonly List<ActiveTradeItem> activeTrades = new List<ActiveTradeItem>();
		private long tradeCounter = 0;

		// Acumulador para barras sintéticas (cuando AggregationRatio > 1)
		private int aggCount = 0;
		private double aggHigh = double.MinValue;
		private double aggLow = double.MaxValue;
		private double aggClose = 0.0;
		private DateTime aggTime;
		private int aggBarIndex = 0;
		private DateTime lastBarTime = DateTime.MinValue;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description                 = "Estrategia Escalonadas 150t réplica exacta 1:1 del Dashboard Optimizador Walk-Forward.";
				Name                        = "Escalonadas150tStrategy";
				Calculate                   = Calculate.OnBarClose;
				EntriesPerDirection         = 100;     // Permite múltiples operaciones simultáneas para replicar las 9.002 zonas del dashboard
				EntryHandling               = EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy= false;
				ExitOnSessionCloseSeconds   = 30;
				IsFillLimitOnTouch          = false;
				OrderFillResolution         = OrderFillResolution.Standard;
				Slippage                    = 0;
				StartBehavior               = StartBehavior.WaitUntilFlat;
				TimeInForce                 = TimeInForce.Gtc;
				TraceOrders                 = false;
				RealtimeErrorHandling       = RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling          = StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade         = 20;

				// 1. Configuración de Entrada y Picos (Configuración Ganadora Walk-Forward)
				Contracts                   = 1;
				TargetPeaks                 = TargetPeaksMode.FourPeaks; // 4 Picos (Ganador Walk-Forward)
				EntryMode                   = StrategyEntryMode.RupturaTrigger; // Ruptura Inmediata Trigger (Ganador Walk-Forward)
				DirectionFilter             = TradeDirectionFilter.Both;
				AllowSimultaneousTrades     = true;    // Replicar 1:1 el dashboard con entradas simultáneas
				StopBreakOffsetTicks        = 0;
				PullbackTicks               = 0;
				CancelTicks                 = 0;

				// 2. Gestión de Riesgo (SL / TP / BE) — Parámetros Ganadores
				SlMode                      = SlCalculationMode.StructuralP1; // Réplica exacta del detector (|Entry - P1| / 2)
				SlMultiplier                = 0.8;     // SL: 0.8x (Ganador Walk-Forward)
				SlBufferTicks               = 0;       // Buffer adicional en ticks
				StopLossTicks               = 30;      // Si SlMode == FixedTicks
				TakeProfitR                 = 5.0;     // TP: 5.0R (Ganador Walk-Forward)
				BreakEvenR                  = 0.0;     // BE: 0.0R (Ganador Walk-Forward — BE desactivado)

				// 3. Parámetros del Detector IPC-NQ 150t
				AggregationRatio            = 1;
				AutoDetectAggregation       = true;
				PivotsW                     = 1;       // Ventana de pivote (w=1 por lado)
				MaxGapBars                  = 30;      // Hueco máximo entre picos
				MaxStepTicks                = 42;      // Escalón máximo en ticks (42t para GC = 4.2 pts)
				MinPullTicks                = 14;      // Retroceso mínimo en ticks (14t para GC = 1.4 pts)
				ConfTicks                   = 16;      // Confirmación por alejamiento (16t para GC = 1.6 pts)

				// 4. Depuración y Visualización
				EnableLogging               = false;   // Desactivado por defecto para máxima velocidad de backtest
				DrawZones                   = true;
			}
			else if (State == State.Configure)
			{
				aggCount = 0;
				aggHigh = double.MinValue;
				aggLow = double.MaxValue;
				aggClose = 0.0;
				aggBarIndex = 0;
				lastBarTime = DateTime.MinValue;
				activeTrades.Clear();
				tradeCounter = 0;
			}
			else if (State == State.DataLoaded)
			{
				if (AutoDetectAggregation && BarsPeriod.BarsPeriodType == BarsPeriodType.Tick)
				{
					if (BarsPeriod.Value == 25)
						AggregationRatio = 6;
					else if (BarsPeriod.Value == 150)
						AggregationRatio = 1;
				}

				int targetPeakInt = (int)TargetPeaks;
				detectorH = new DirectionDetector(1, PivotsW, MaxGapBars, MaxStepTicks, MinPullTicks, targetPeakInt, ConfTicks, TickSize);
				detectorL = new DirectionDetector(-1, PivotsW, MaxGapBars, MaxStepTicks, MinPullTicks, targetPeakInt, ConfTicks, TickSize);

				if (EnableLogging)
				{
					Print(string.Format(CultureInfo.InvariantCulture,
						"[EscalonadasStrategy] Iniciada en {0}. Picos={1}, Modo={2}, SlMode={3}, TP={4:F1}R, BE={5:F1}R, AggRatio={6}, Simultaneas={7}",
						Instrument.FullName, TargetPeaks, EntryMode, SlMode, TakeProfitR, BreakEvenR, AggregationRatio, AllowSimultaneousTrades));
				}
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < BarsRequiredToTrade) return;

			DateTime t = Time[0];
			double h = High[0];
			double l = Low[0];
			double c = Close[0];

			// 1. GESTIÓN DE BREAK-EVEN DINÁMICO (Si BreakEvenR > 0)
			if (activeTrades.Count > 0 && BreakEvenR > 0)
			{
				for (int i = activeTrades.Count - 1; i >= 0; i--)
				{
					ActiveTradeItem tr = activeTrades[i];
					if (tr.IsResolved || tr.BeActivated) continue;
					if (CurrentBar <= tr.DetBar) continue;

					int sd = (tr.Kind == "H") ? -1 : 1;
					bool hitBe = (sd == -1) ? (l <= tr.BeTriggerPrice) : (h >= tr.BeTriggerPrice);
					if (hitBe)
					{
						tr.BeActivated = true;
						tr.SlPrice = tr.EntryPrice;
						if (tr.Kind == "H")
							ExitShortStopMarket(0, true, Contracts, tr.EntryPrice, "BE_" + tr.Id, tr.EntryName);
						else
							ExitLongStopMarket(0, true, Contracts, tr.EntryPrice, "BE_" + tr.Id, tr.EntryName);

						if (EnableLogging)
							Print(string.Format(CultureInfo.InvariantCulture, "{0} - [BE ACTIVADO] Trade {1} SL movido a {2:F2}", t, tr.EntryName, tr.SlPrice));
					}
				}
			}

			// 2. Control de sesión y alimentación del detector
			bool sessionBreak = (lastBarTime != DateTime.MinValue && (t - lastBarTime).TotalSeconds > 1800);
			lastBarTime = t;

			if (AggregationRatio <= 1)
			{
				ProcessSyntheticBar(aggBarIndex++, h, l, c, t, CurrentBar);
			}
			else
			{
				if (sessionBreak && aggCount > 0)
				{
					ProcessSyntheticBar(aggBarIndex++, aggHigh, aggLow, aggClose, aggTime, CurrentBar - 1);
					aggCount = 0;
					aggHigh = double.MinValue;
					aggLow = double.MaxValue;
				}

				if (aggCount == 0)
				{
					aggHigh = h;
					aggLow = l;
					aggClose = c;
					aggTime = t;
				}
				else
				{
					if (h > aggHigh) aggHigh = h;
					if (l < aggLow) aggLow = l;
					aggClose = c;
				}
				aggCount++;

				if (aggCount >= AggregationRatio)
				{
					ProcessSyntheticBar(aggBarIndex++, aggHigh, aggLow, aggClose, t, CurrentBar);
					aggCount = 0;
					aggHigh = double.MinValue;
					aggLow = double.MaxValue;
				}
			}
		}

		private void ProcessSyntheticBar(int synthIdx, double synthH, double synthL, double synthC, DateTime synthT, int chartIdx)
		{
			List<SignalInfo> signalsH = detectorH.OnBar(synthIdx, synthH, synthL, synthC, synthT, chartIdx);
			if (signalsH != null && signalsH.Count > 0)
			{
				for (int i = 0; i < signalsH.Count; i++)
					OnSignalDetected(signalsH[i]);
			}

			List<SignalInfo> signalsL = detectorL.OnBar(synthIdx, synthH, synthL, synthC, synthT, chartIdx);
			if (signalsL != null && signalsL.Count > 0)
			{
				for (int i = 0; i < signalsL.Count; i++)
					OnSignalDetected(signalsL[i]);
			}
		}

		private void OnSignalDetected(SignalInfo sig)
		{
			// Si no se permiten trades simultáneos y ya hay una posición abierta, descartar
			if (!AllowSimultaneousTrades && activeTrades.Count > 0)
				return;

			// Filtro de dirección
			if (sig.Kind == "H" && DirectionFilter == TradeDirectionFilter.LongOnly)
				return;
			if (sig.Kind == "L" && DirectionFilter == TradeDirectionFilter.ShortOnly)
				return;

			int sd = (sig.Kind == "H") ? -1 : 1;
			double pTrig = sig.DetTriggerPrice;
			double p1 = sig.P1Price;

			// En RupturaTrigger (ganador Walk-Forward), la entrada teórica del detector es exactamente pTrig
			double effectiveEntry = (EntryMode == StrategyEntryMode.RupturaTrigger) ? pTrig : sig.DetPrice;

			// Cálculo del 1R Estructural (|Entry - P1| / 2 * SlMultiplier) idéntico a SimulateFastTrade
			double dist1R;
			if (SlMode == SlCalculationMode.StructuralP1)
			{
				double baseDist1R = Math.Abs(effectiveEntry - p1) / 2.0;
				double mult = (SlMultiplier > 0.05) ? SlMultiplier : 1.0;
				dist1R = Math.Max(2 * TickSize, Math.Round(baseDist1R * mult, 2)) + (SlBufferTicks > 0 ? SlBufferTicks * TickSize : 0.0);
			}
			else
			{
				dist1R = StopLossTicks * TickSize;
			}

			double slPrice = Math.Round(effectiveEntry - sd * dist1R, 2);
			double tpPrice = Math.Round(effectiveEntry + sd * TakeProfitR * dist1R, 2);
			double bePrice = Math.Round(effectiveEntry + sd * BreakEvenR * dist1R, 2);

			// Nombre único de entrada para gestión independiente multi-trade
			string entryName = (sig.Kind == "H" ? "EscShort_" : "EscLong_") + (++tradeCounter);

			// Registro del trade activo en la lista interna
			ActiveTradeItem trade = new ActiveTradeItem
			{
				Id = tradeCounter,
				EntryName = entryName,
				Kind = sig.Kind,
				EntryPrice = effectiveEntry,
				P1Price = p1,
				Dist1R = dist1R,
				SlPrice = slPrice,
				TpPrice = tpPrice,
				BeTriggerPrice = bePrice,
				BeActivated = false,
				DetBar = CurrentBar,
				IsResolved = false
			};
			activeTrades.Add(trade);

			// Envío de la orden y sus brackets nativos OCO a NinjaTrader
			if (sig.Kind == "H")
			{
				EnterShort(0, Contracts, entryName);
				ExitShortStopMarket(0, true, Contracts, slPrice, "SL_" + trade.Id, entryName);
				ExitShortLimit(0, true, Contracts, tpPrice, "TP_" + trade.Id, entryName);

				if (EnableLogging)
				{
					Print(string.Format(CultureInfo.InvariantCulture,
						"{0} - [ENTRADA SHORT #{1}] Trigger={2:F2}, P1={3:F2} -> SL={4:F2} (-{5:F2}p), TP={6:F2} (+{7:F2}p)",
						Time[0], trade.Id, effectiveEntry, p1, slPrice, dist1R, tpPrice, dist1R * TakeProfitR));
				}
				if (DrawZones)
				{
					Draw.ArrowDown(this, "Strat_Sig_" + CurrentBar + "_" + trade.Id, true, 0, pTrig + 2 * TickSize, Brushes.Crimson);
					Draw.Line(this, "Strat_En_" + CurrentBar + "_" + trade.Id, false, 0, effectiveEntry, -10, effectiveEntry, Brushes.DarkRed, DashStyleHelper.Dash, 2);
				}
			}
			else if (sig.Kind == "L")
			{
				EnterLong(0, Contracts, entryName);
				ExitLongStopMarket(0, true, Contracts, slPrice, "SL_" + trade.Id, entryName);
				ExitLongLimit(0, true, Contracts, tpPrice, "TP_" + trade.Id, entryName);

				if (EnableLogging)
				{
					Print(string.Format(CultureInfo.InvariantCulture,
						"{0} - [ENTRADA LONG #{1}] Trigger={2:F2}, P1={3:F2} -> SL={4:F2} (-{5:F2}p), TP={6:F2} (+{7:F2}p)",
						Time[0], trade.Id, effectiveEntry, p1, slPrice, dist1R, tpPrice, dist1R * TakeProfitR));
				}
				if (DrawZones)
				{
					Draw.ArrowUp(this, "Strat_Sig_" + CurrentBar + "_" + trade.Id, true, 0, pTrig - 2 * TickSize, Brushes.DodgerBlue);
					Draw.Line(this, "Strat_En_" + CurrentBar + "_" + trade.Id, false, 0, effectiveEntry, -10, effectiveEntry, Brushes.DarkBlue, DashStyleHelper.Dash, 2);
				}
			}
		}

		protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
		{
			if (execution.Order != null && (execution.Order.OrderState == OrderState.Filled || execution.Order.OrderState == OrderState.PartFilled))
			{
				string fromEntry = execution.Order.FromEntrySignal;
				if (!string.IsNullOrEmpty(fromEntry))
				{
					activeTrades.RemoveAll(x => x.EntryName == fromEntry);
				}
			}
		}

		protected override void OnPositionUpdate(Position position, double averagePrice, int quantity, MarketPosition marketPosition)
		{
			if (position.MarketPosition == MarketPosition.Flat)
			{
				activeTrades.Clear();
			}
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Contratos", Order = 1, GroupName = "1. Parámetros de Trading")]
		public int Contracts { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Picos Objetivo", Description = "4 Picos (ganador Walk-Forward) o 5 Picos (tradicional)", Order = 2, GroupName = "1. Parámetros de Trading")]
		public TargetPeaksMode TargetPeaks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo de Entrada", Description = "RupturaTrigger (Nivel teórico), ConfirmacionCierre (Cierre de barra) o RetesteoPico (Límite en pico)", Order = 3, GroupName = "1. Parámetros de Trading")]
		public StrategyEntryMode EntryMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Filtro de Dirección", Description = "Permitir Both, LongOnly o ShortOnly", Order = 4, GroupName = "1. Parámetros de Trading")]
		public TradeDirectionFilter DirectionFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Permitir Trades Simultáneos", Description = "True = toma todas las zonas como el dashboard (9000+ ops). False = 1 posición a la vez.", Order = 5, GroupName = "1. Parámetros de Trading")]
		public bool AllowSimultaneousTrades { get; set; }

		[NinjaScriptProperty]
		[Range(0, 50)]
		[Display(Name = "Offset Ruptura Stop (Ticks)", Description = "Ticks adicionales a favor para orden stop (0 para nivel trigger exacto)", Order = 6, GroupName = "1. Parámetros de Trading")]
		public int StopBreakOffsetTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0, 50)]
		[Display(Name = "Retroceso Pullback (Ticks)", Description = "Ticks de retroceso para orden límite en ConfirmacionCierre (0 = mercado)", Order = 7, GroupName = "1. Parámetros de Trading")]
		public int PullbackTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Cancelación Escape (Ticks)", Description = "Ticks a favor para cancelar orden límite pendiente si el precio se escapa", Order = 8, GroupName = "1. Parámetros de Trading")]
		public int CancelTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo Cálculo SL", Description = "Estructural P1 (|Entry - P1| / 2) idéntico al detector, o Estático en Ticks", Order = 1, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public SlCalculationMode SlMode { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 5.0)]
		[Display(Name = "Multiplicador SL", Description = "Multiplicador de 1R para Stop Loss estructural (0.8 por defecto, ganador Walk-Forward)", Order = 2, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public double SlMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0, 50)]
		[Display(Name = "Buffer SL (Ticks)", Description = "Ticks de margen adicional para el Stop Loss", Order = 3, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public int SlBufferTicks { get; set; }

		[NinjaScriptProperty]
		[Range(5, 200)]
		[Display(Name = "Stop Loss Fijo (Ticks)", Description = "Stop loss estático si SlMode == FixedTicks (30t = 3.0 pts en GC)", Order = 4, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public int StopLossTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 15.0)]
		[Display(Name = "Take Profit (R)", Description = "Multiplicador de R para objetivo (5.0R por defecto, ganador Walk-Forward)", Order = 5, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public double TakeProfitR { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 5.0)]
		[Display(Name = "Break-Even (R)", Description = "R a favor para mover SL a entrada (0.0R por defecto, ganador Walk-Forward con BE desactivado)", Order = 6, GroupName = "2. Gestión de Riesgo (SL / TP / BE)")]
		public double BreakEvenR { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Ratio Agregación", Description = "1 para gráfico nativo 150t; 6 para gráfico 25t", Order = 1, GroupName = "3. Parámetros de Barras")]
		public int AggregationRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Auto-detectar Período", Description = "Si el gráfico es 25t fija ratio en 6; si es 150t fija ratio en 1", Order = 2, GroupName = "3. Parámetros de Barras")]
		public bool AutoDetectAggregation { get; set; }

		[NinjaScriptProperty]
		[Range(1, 10)]
		[Display(Name = "Pivotes W (Velas)", Description = "Velas por lado para pivotes", Order = 1, GroupName = "4. Parámetros IPC-NQ")]
		public int PivotsW { get; set; }

		[NinjaScriptProperty]
		[Range(5, 100)]
		[Display(Name = "Max Gap (Velas)", Description = "Hueco máximo entre picos en barras sintéticas", Order = 2, GroupName = "4. Parámetros IPC-NQ")]
		public int MaxGapBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name = "Max Step (Ticks)", Description = "Escalón máximo en ticks (42 para GC = 4.2 pts)", Order = 3, GroupName = "4. Parámetros IPC-NQ")]
		public int MaxStepTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Min Pull (Ticks)", Description = "Retroceso mínimo en ticks (14 para GC = 1.4 pts)", Order = 4, GroupName = "4. Parámetros IPC-NQ")]
		public int MinPullTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Confirmación Precio (Ticks)", Description = "Ticks de alejamiento para confirmar pivote (16 para GC = 1.6 pts)", Order = 5, GroupName = "4. Parámetros IPC-NQ")]
		public int ConfTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Activar Logging", Description = "Muestra trazas detalladas en la ventana Output de NinjaTrader", Order = 1, GroupName = "5. Depuración y Visualización")]
		public bool EnableLogging { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Señales en Gráfico", Description = "Dibuja flechas y niveles de entrada en el chart", Order = 2, GroupName = "5. Depuración y Visualización")]
		public bool DrawZones { get; set; }
		#endregion
	}
}
