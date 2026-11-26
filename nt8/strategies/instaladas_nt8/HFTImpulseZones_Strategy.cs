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

// =========================================================================================
// HFTImpulseZones_Strategy.cs — Estrategia Automatizada para NinjaTrader 8
//
// LÓGICA DE TRADING:
// 1. Detección continua de micro-impulsos de alta frecuencia (HFT) en ventana deslizante.
// 2. Mapeo de clusters de zonas con solapamiento espacial y proximidad temporal (ininterrumpido).
// 3. Disparo de orden en la barra exacta donde el cluster alcanza el Top 3% de solapamiento.
// 4. Gestión de salida 1 a 1:
//    - TP y SL fijados al tamaño total del cluster de zonas conectadas al movimiento.
//    - Break Even al 50% de ganancia: cuando el precio recorre la mitad hacia el TP,
//      el Stop Loss se ajusta automáticamente al precio de entrada para eliminar riesgo.
// =========================================================================================

namespace NinjaTrader.NinjaScript.Strategies
{
	public class HFTImpulseZones_Strategy : Strategy
	{
		private class ZoneRecord
		{
			public int Id;
			public int ClusterRootId;
			public int StartBar;
			public int EndBar;
			public long LowerTick;
			public long UpperTick;
			public int Direction;        // +1 alcista (soporte), -1 bajista (resistencia)
			public double OverlapScore;
			public int OverlapCount;
			public bool IsGold;
		}

		private class ClusterGroup
		{
			public int RootId;
			public int EarliestStartBar;
			public int LatestEndBar;
			public long MinLowerTick;
			public long MaxUpperTick;
			public bool IsGold;
			public bool SignalFired;
			public int TriggerBar;
			public int Direction;
			public readonly List<ZoneRecord> Members = new List<ZoneRecord>();
		}

		#region Variables Internas
		private List<long> _closeTicks;
		private List<long> _highTicks;
		private List<long> _lowTicks;
		private List<long> _volumes;

		private List<ZoneRecord> _allZones;
		private List<double> _scoreHistory;
		private Dictionary<int, ClusterGroup> _clusterMap;

		private int _sessionIndex = -1;
		private int _windowIndex;
		private int _zoneSeq;
		private double _cachedThreshold = double.MaxValue;

		// Gestión de posición activa
		private double _currentTargetDistance;
		private bool _isBreakEven;
		private int _tradesToday;
		private double _dailyPnL;
		private DateTime _currentDay = DateTime.MinValue;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Estrategia automatizada de clusters de zonas HFT con TP/SL 1:1 y Break Even al 50%.";
				Name										= "HFTImpulseZones_Strategy";
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
				BarsRequiredToTrade							= 20;
				IsInstantiatedOnEachOptimizationIteration	= true;

				// 1. Detección de Impulso
				WindowBars									= 12;
				MinDisplacementTicks						= 16;
				MinEfficiencyBps							= 6000;   // 60,00 %
				MinWindowVolume								= 0;
				ZoneHeightTicks								= 8;

				// 2. Filtro de Solapamiento Top %
				TopPercentile								= 3.0;    // Top 3,0 %
				MaxLookbackBars								= 100;
				MinOverlapZones								= 2;
				EnableLong									= true;
				EnableShort									= true;

				// 3. Ejecución y Gestión (SL es la mitad del TP)
				OrderQuantity								= 1;
				EnableBreakEven								= true;
				BreakEvenTriggerPct							= 50.0;   // 50% de ganancia hacia el TP
				RiskRewardRatio								= 1.0;
				StopLossRatio								= 0.5;    // SL = 50% del tamaño del TP (Ratio 2:1)

				// 4. Filtro Horario y Control Diario
				UseTimeFilter								= false;
				StartTime									= TimeSpan.Parse("08:30");
				EndTime										= TimeSpan.Parse("15:30");
				MaxDailyLoss								= 50000.0;
				MaxDailyTrades								= 500;
			}
			else if (State == State.DataLoaded)
			{
				_closeTicks = new List<long>();
				_highTicks = new List<long>();
				_lowTicks = new List<long>();
				_volumes = new List<long>();

				_allZones = new List<ZoneRecord>();
				_scoreHistory = new List<double>();
				_clusterMap = new Dictionary<int, ClusterGroup>();

				_cachedThreshold = double.MaxValue;
				_currentTargetDistance = 0;
				_isBreakEven = false;
				_tradesToday = 0;
				_dailyPnL = 0;
				_currentDay = DateTime.MinValue;
			}
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < BarsRequiredToTrade) return;

			// Control diario de pérdidas y trades
			if (Time[0].Date != _currentDay)
			{
				_currentDay = Time[0].Date;
				_tradesToday = 0;
				_dailyPnL = 0;
			}

			if (Bars.IsFirstBarOfSession)
			{
				_sessionIndex++;
				_closeTicks.Clear();
				_highTicks.Clear();
				_lowTicks.Clear();
				_volumes.Clear();
				_windowIndex = 0;
			}

			_closeTicks.Add(PriceToTick(Close[0]));
			_highTicks.Add(PriceToTick(High[0]));
			_lowTicks.Add(PriceToTick(Low[0]));
			_volumes.Add((long)Volume[0]);

			// ── 1. GESTIÓN DE BREAK EVEN EN POSICIÓN ABIERTA (SIN DETENER EL CÁLCULO DE ZONAS) ──
			if (Position.MarketPosition != MarketPosition.Flat)
			{
				ManageActiveBreakEven();
			}
			else
			{
				_isBreakEven = false;
			}

			// ── 2. DETECCIÓN CONTINUA DE IMPULSOS Y CLUSTERS EN CADA BARRA ──
			if (_closeTicks.Count >= WindowBars)
			{
				int n = _closeTicks.Count;
				int s = n - WindowBars;
				int e = n - 1;

				long startTick = _closeTicks[s];
				long endTick = _closeTicks[e];
				long displacement = Math.Abs(endTick - startTick);

				long path = 0;
				long windowVolume = 0;
				for (int i = s + 1; i <= e; i++) path += Math.Abs(_closeTicks[i] - _closeTicks[i - 1]);
				for (int i = s; i <= e; i++) windowVolume += _volumes[i];

				long effBps = path > 0 ? (displacement * 10000L) / path : 0L;

				if (windowVolume >= MinWindowVolume && displacement >= MinDisplacementTicks && effBps >= MinEfficiencyBps)
				{
					int direction = endTick > startTick ? 1 : -1;
					long zLower = 0, zUpper = 0;

					if (direction == 1)
					{
						long baseTick = _lowTicks[s];
						for (int i = s; i <= e; i++) if (_lowTicks[i] < baseTick) baseTick = _lowTicks[i];
						zLower = baseTick;
						zUpper = baseTick + ZoneHeightTicks;
					}
					else
					{
						long baseTick = _highTicks[s];
						for (int i = s; i <= e; i++) if (_highTicks[i] > baseTick) baseTick = _highTicks[i];
						zUpper = baseTick;
						zLower = baseTick - ZoneHeightTicks;
					}

					_zoneSeq++;
					int startBar = CurrentBar - (WindowBars - 1);
					int endBar = CurrentBar;

					ZoneRecord newZ = new ZoneRecord
					{
						Id = _zoneSeq,
						ClusterRootId = _zoneSeq,
						StartBar = startBar,
						EndBar = endBar,
						LowerTick = zLower,
						UpperTick = zUpper,
						Direction = direction,
						OverlapScore = 0,
						OverlapCount = 1,
						IsGold = false
					};

					List<ZoneRecord> clusterMembers = new List<ZoneRecord> { newZ };
					int rootId = newZ.Id;

					for (int i = _allZones.Count - 1; i >= 0; i--)
					{
						ZoneRecord prevZ = _allZones[i];
						if (endBar - prevZ.EndBar > MaxLookbackBars) break;
						if (prevZ.Direction != newZ.Direction) continue;

						long oLow = Math.Max(newZ.LowerTick, prevZ.LowerTick);
						long oHigh = Math.Min(newZ.UpperTick, prevZ.UpperTick);

						if (oHigh >= oLow)
						{
							int deltaBars = Math.Max(1, endBar - prevZ.EndBar);
							double weight = 100.0 / (deltaBars + 1.0);

							newZ.OverlapScore += weight;
							newZ.OverlapCount++;

							prevZ.OverlapScore += weight;
							prevZ.OverlapCount++;

							if (prevZ.ClusterRootId > 0 && prevZ.ClusterRootId < rootId)
								rootId = prevZ.ClusterRootId;

							clusterMembers.Add(prevZ);
						}
					}

					for (int i = 0; i < clusterMembers.Count; i++)
					{
						clusterMembers[i].ClusterRootId = rootId;
					}

					_allZones.Add(newZ);
					_scoreHistory.Add(newZ.OverlapScore);

					// Actualizar cluster en el mapa
					ClusterGroup cg;
					if (!_clusterMap.TryGetValue(rootId, out cg))
					{
						cg = new ClusterGroup
						{
							RootId = rootId,
							EarliestStartBar = newZ.StartBar,
							LatestEndBar = newZ.EndBar,
							MinLowerTick = newZ.LowerTick,
							MaxUpperTick = newZ.UpperTick,
							IsGold = false,
							SignalFired = false,
							TriggerBar = -1,
							Direction = direction
						};
						_clusterMap[rootId] = cg;
					}

					if (!cg.Members.Contains(newZ)) cg.Members.Add(newZ);
					if (newZ.StartBar < cg.EarliestStartBar) cg.EarliestStartBar = newZ.StartBar;
					if (newZ.EndBar > cg.LatestEndBar) cg.LatestEndBar = newZ.EndBar;
					if (newZ.LowerTick < cg.MinLowerTick) cg.MinLowerTick = newZ.LowerTick;
					if (newZ.UpperTick > cg.MaxUpperTick) cg.MaxUpperTick = newZ.UpperTick;

					// Actualizar umbral dinámico del Top 3%
					UpdateThreshold();

					// ── 3. EVALUAR CONDICIÓN DE DISPARO DE SEÑAL ──
					if (_cachedThreshold < double.MaxValue && !cg.SignalFired)
					{
						bool clusterQualifies = false;
						foreach (ZoneRecord m in clusterMembers)
						{
							if (m.OverlapScore >= _cachedThreshold && m.OverlapCount >= MinOverlapZones)
							{
								m.IsGold = true;
								cg.IsGold = true;
								clusterQualifies = true;
							}
						}

						if (clusterQualifies)
						{
							cg.SignalFired = true;
							cg.TriggerBar = CurrentBar;
							cg.Direction = direction;

							// Tamaño total del cluster conectado al movimiento
							double clusterHeight = (cg.MaxUpperTick - cg.MinLowerTick + 1) * TickSize;
							clusterHeight = Math.Max(clusterHeight, ZoneHeightTicks * TickSize);
							int distanceTicks = (int)Math.Round(clusterHeight / TickSize, MidpointRounding.AwayFromZero);

							int slTicks = distanceTicks;
							int tpTicks = (int)Math.Round(distanceTicks * RiskRewardRatio, MidpointRounding.AwayFromZero);

							// ── 4. EJECUTAR ENTRADA SOLO SI NO ESTAMOS EN POSICIÓN ACTIVA ──
							if (Position.MarketPosition == MarketPosition.Flat)
							{
								bool allowedByDaily = (_tradesToday < MaxDailyTrades && _dailyPnL > -MaxDailyLoss);
								bool allowedByTime = !UseTimeFilter || (Time[0].TimeOfDay >= StartTime && Time[0].TimeOfDay <= EndTime);

								if (allowedByDaily && allowedByTime)
								{
									_currentTargetDistance = clusterHeight;
									_isBreakEven = false;

									double entryEst = Close[0];
									double slDistance = clusterHeight * (StopLossRatio > 0 ? StopLossRatio : 0.5);
									double tpDistance = clusterHeight * RiskRewardRatio;

									double slPx = (direction == 1) ? (entryEst - slDistance) : (entryEst + slDistance);
									double tpPx = (direction == 1) ? (entryEst + tpDistance) : (entryEst - tpDistance);

									if (direction == 1 && EnableLong)
									{
										SetStopLoss("HFT_Long", CalculationMode.Price, slPx, false);
										SetProfitTarget("HFT_Long", CalculationMode.Price, tpPx);
										EnterLong(OrderQuantity, "HFT_Long");
										_tradesToday++;
									}
									else if (direction == -1 && EnableShort)
									{
										SetStopLoss("HFT_Short", CalculationMode.Price, slPx, false);
										SetProfitTarget("HFT_Short", CalculationMode.Price, tpPx);
										EnterShort(OrderQuantity, "HFT_Short");
										_tradesToday++;
									}
								}
							}
						}
					}
				}

				_windowIndex++;
			}
		}

		private void ManageActiveBreakEven()
		{
			if (!EnableBreakEven || _currentTargetDistance <= 0)
				return;

			double triggerGain = (BreakEvenTriggerPct / 100.0) * _currentTargetDistance;

			if (Position.MarketPosition == MarketPosition.Long)
			{
				double unrealizedHigh = High[0] - Position.AveragePrice;
				if (!_isBreakEven && unrealizedHigh >= triggerGain)
				{
					_isBreakEven = true;
					// Mueve el Stop Loss en el broker al precio exacto de entrada
					SetStopLoss("HFT_Long", CalculationMode.Price, Position.AveragePrice, false);
				}

				// Salida garantizada en Break Even si el precio retrocede a la entrada
				if (_isBreakEven && Low[0] <= Position.AveragePrice)
				{
					ExitLong("BE_Long", "HFT_Long");
				}
			}
			else if (Position.MarketPosition == MarketPosition.Short)
			{
				double unrealizedGain = Position.AveragePrice - Low[0];
				if (!_isBreakEven && unrealizedGain >= triggerGain)
				{
					_isBreakEven = true;
					// Mueve el Stop Loss en el broker al precio exacto de entrada
					SetStopLoss("HFT_Short", CalculationMode.Price, Position.AveragePrice, false);
				}

				// Salida garantizada en Break Even si el precio retrocede a la entrada
				if (_isBreakEven && High[0] >= Position.AveragePrice)
				{
					ExitShort("BE_Short", "HFT_Short");
				}
			}
		}

		private void UpdateThreshold()
		{
			if (_scoreHistory.Count < 10)
			{
				_cachedThreshold = 1.0;
				return;
			}

			List<double> nonZero = new List<double>();
			for (int i = 0; i < _scoreHistory.Count; i++)
			{
				if (_scoreHistory[i] > 0) nonZero.Add(_scoreHistory[i]);
			}
			if (nonZero.Count < 5)
			{
				_cachedThreshold = 1.0;
				return;
			}

			nonZero.Sort();
			double p = 1.0 - (TopPercentile / 100.0);
			int idx = (int)Math.Floor(p * (nonZero.Count - 1));
			idx = Math.Max(0, Math.Min(nonZero.Count - 1, idx));

			_cachedThreshold = Math.Max(1.0, nonZero[idx]);
		}

		protected override void OnPositionUpdate(Position position, double averagePrice, int quantity, MarketPosition marketPosition)
		{
			if (marketPosition == MarketPosition.Flat)
			{
				_isBreakEven = false;
				_currentTargetDistance = 0;
			}
		}

		protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
		{
			if (execution.Order != null && execution.Order.OrderState == OrderState.Filled)
			{
				// Acumular PnL diario
				if (Position.MarketPosition == MarketPosition.Flat)
				{
					_dailyPnL += SystemPerformance.AllTrades.Count > 0 ? SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1].ProfitCurrency : 0.0;
				}
			}
		}

		#region Propiedades de Configuración

		[NinjaScriptProperty]
		[Range(2, 200)]
		[Display(Name = "Window Bars", Order = 1, GroupName = "1. Impulso")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 1000)]
		[Display(Name = "Min Displacement (Ticks)", Order = 2, GroupName = "1. Impulso")]
		public int MinDisplacementTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1000, 10000)]
		[Display(Name = "Min Efficiency (bps)", Order = 3, GroupName = "1. Impulso")]
		public int MinEfficiencyBps { get; set; }

		[NinjaScriptProperty]
		[Range(0, long.MaxValue)]
		[Display(Name = "Min Window Volume", Order = 4, GroupName = "1. Impulso")]
		public long MinWindowVolume { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name = "Zone Height (Ticks)", Order = 5, GroupName = "1. Impulso")]
		public int ZoneHeightTicks { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 20.0)]
		[Display(Name = "Top Percentile (%)", Description = "Top % de mayor solapamiento para calificar la señal (3.0 = top 3%)", Order = 6, GroupName = "2. Solapamiento")]
		public double TopPercentile { get; set; }

		[NinjaScriptProperty]
		[Range(10, 500)]
		[Display(Name = "Max Lookback (Bars)", Description = "Lookback máximo en barras para evaluar solapamiento", Order = 7, GroupName = "2. Solapamiento")]
		public int MaxLookbackBars { get; set; }

		[NinjaScriptProperty]
		[Range(2, 10)]
		[Display(Name = "Min Overlap Zones", Description = "Mínimo de zonas en el cluster para disparar la orden", Order = 8, GroupName = "2. Solapamiento")]
		public int MinOverlapZones { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Enable Long", Order = 9, GroupName = "2. Solapamiento")]
		public bool EnableLong { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Enable Short", Order = 10, GroupName = "2. Solapamiento")]
		public bool EnableShort { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Order Quantity", Order = 11, GroupName = "3. Gestión y Salida 1:1")]
		public int OrderQuantity { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 5.0)]
		[Display(Name = "Risk Reward Ratio", Description = "Ratio TP respecto al SL (1.0 = 1 a 1)", Order = 12, GroupName = "3. Gestión y Salida 1:1")]
		public double RiskRewardRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Enable Break Even", Description = "Ajustar Stop Loss a precio de entrada al alcanzar el 50% de ganancia", Order = 13, GroupName = "3. Gestión y Salida 1:1")]
		public bool EnableBreakEven { get; set; }

		[NinjaScriptProperty]
		[Range(10.0, 90.0)]
		[Display(Name = "BE Trigger (% Profit)", Description = "Porcentaje de avance hacia el TP que activa el Break Even (50% por defecto)", Order = 14, GroupName = "3. Gestión y Salida")]
		public double BreakEvenTriggerPct { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 2.0)]
		[Display(Name = "Stop Loss Ratio", Description = "Proporción del SL respecto al TP (0.5 = SL es la mitad del tamaño del TP)", Order = 15, GroupName = "3. Gestión y Salida")]
		public double StopLossRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Use Time Filter", Order = 15, GroupName = "4. Filtro Horario y Riesgo")]
		public bool UseTimeFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Start Time", Order = 16, GroupName = "4. Filtro Horario y Riesgo")]
		public TimeSpan StartTime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "End Time", Order = 17, GroupName = "4. Filtro Horario y Riesgo")]
		public TimeSpan EndTime { get; set; }

		[NinjaScriptProperty]
		[Range(100.0, 100000.0)]
		[Display(Name = "Max Daily Loss ($)", Order = 18, GroupName = "4. Filtro Horario y Riesgo")]
		public double MaxDailyLoss { get; set; }

		[NinjaScriptProperty]
		[Range(1, 1000)]
		[Display(Name = "Max Daily Trades", Order = 19, GroupName = "4. Filtro Horario y Riesgo")]
		public int MaxDailyTrades { get; set; }

		#endregion
	}
}
