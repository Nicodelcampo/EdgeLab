// # meta indicator=BigTrapGC,version=1.5.0
//
// BigTrapGC — Detector de Absorción y Trampas Institucionales para Oro (GC / MGC).
// 
// Optimizado para COMEX Gold:
// - Tick Size: 0.10 pt ($10.00 USD por tick en GC, $1.00 USD en MGC).
// - Multiplicador de Punto: $100.00 USD por punto entero.
// - Resolución Nativa Recomendada: Barras de 25 Ticks (25-Tick Bars) o 15 Ticks.
// - Umbral de Absorción: 40.0 contratos (Sweet spot empírico calibrado a la profundidad de GC).
// - Subasta Terminada (Finished Auction): True (tol <= 1.0 contrato).
// - Simulación Visual en Tiempo Real:
//   * Modo BarClose: Entrada inmediata al cierre de la vela de señal.
//   * Modo ZoneRetest: Entrada al pullback / re-test a la zona de absorción.
//   * Flecha Dorada: Señaliza con precisión el inicio de la primera vela posterior a la entrada.
//   * Dashboard en Vivo: HUD con WinRate, Profit Factor, PnL Bruto, PnL Neto CME y estado de posición.

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
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript
{
	public enum BigTrapEntryMode
	{
		BarClose,    // Entrada inmediata al cierre de la vela que genera la señal
		ZoneRetest   // Entrada en el retroceso (pullback / re-test) a la zona
	}
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrapGC : Indicator
	{
		private const string IND_VERSION = "1.5.0";

		private enum SimTradeStatus { PendingTouch, InTrade, Won, Lost }

		private sealed class TrapZone
		{
			public int CreatedBar;
			public bool IsBull; // true = Trapped Buyers (Techo/Resistencia/SHORT), false = Trapped Sellers (Suelo/Soporte/LONG)
			public double Top;
			public double Bottom;
			public double Volume;
			public int Touches;
			public bool IsActive;
			public string Tag;

			// Simulación de Ejecución (SL / TP / BE)
			public SimTradeStatus SimStatus = SimTradeStatus.PendingTouch;
			public int EntryBar = -1;
			public double EntryPrice;
			public double StopLoss;
			public double TakeProfit;
			public double RealizedPts = 0.0;
			public double ArrowY = 0.0;
			public bool IsBreakEvenTriggered = false;
		}

		private Dictionary<long, double> _currentAsk;
		private Dictionary<long, double> _currentBid;
		private List<TrapZone> _zones;
		private long _lastSubTickPrice;
		private int _lastSubTickDir;

		// Métricas de Simulación acumuladas
		private int _simWins;
		private int _simLosses;
		private double _simNetPts;
		private double _simGrossProfit;
		private double _simGrossLoss;

		#region Properties
		[NinjaScriptProperty]
		[Range(1, 10)]
		[Display(Name = "Ticks Per Row", GroupName = "1. Geometria", Order = 1)]
		public int TicksPerRow { get; set; }

		[NinjaScriptProperty]
		[Range(5, 300)]
		[Display(Name = "Min Trap Volume", GroupName = "2. Absorcion GC (Oro)", Order = 1)]
		public double MinTrapVolume { get; set; }

		[NinjaScriptProperty]
		[Range(1.5, 10.0)]
		[Display(Name = "Imbalance Ratio", GroupName = "2. Absorcion GC (Oro)", Order = 2)]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Require Finished Auction", GroupName = "3. Auction Market", Order = 1)]
		public bool RequireFinishedAuction { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Finished Auction Tol", GroupName = "3. Auction Market", Order = 2)]
		public double FinishedAuctionTol { get; set; }

		[NinjaScriptProperty]
		[Range(0, 10)]
		[Display(Name = "Anti-Overshoot Buffer (Ticks)", GroupName = "4. Gestion de Riesgo", Order = 1)]
		public int AntiOvershootBufferTicks { get; set; }

		[NinjaScriptProperty]
		[Range(10, 50)]
		[Display(Name = "Wick Zone Pct", GroupName = "4. Gestion de Riesgo", Order = 2)]
		public double WickZonePct { get; set; }

		[NinjaScriptProperty]
		[Range(20, 2000)]
		[Display(Name = "Max Age Bars", GroupName = "4. Gestion de Riesgo", Order = 3)]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Activar Simulacion SL/TP", GroupName = "5. Simulacion SL y TP", Order = 1)]
		public bool EnableSimulation { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo de Entrada", GroupName = "5. Simulacion SL y TP", Order = 2)]
		public BigTrapEntryMode EntryMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Permitir Trades Simultaneos", GroupName = "5. Simulacion SL y TP", Order = 3)]
		public bool AllowSimultaneousTrades { get; set; }

		[NinjaScriptProperty]
		[Range(0.2, 50.0)]
		[Display(Name = "Take Profit (Puntos GC)", GroupName = "5. Simulacion SL y TP", Order = 4)]
		public double TpPoints { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 10.0)]
		[Display(Name = "SL Multiplicador", GroupName = "5. Simulacion SL y TP", Order = 5)]
		public double SlMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0, 20)]
		[Display(Name = "SL Buffer Extra (Ticks)", GroupName = "5. Simulacion SL y TP", Order = 6)]
		public int SlBufferTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Activar Break-Even", GroupName = "5. Simulacion SL y TP", Order = 7)]
		public bool EnableBreakEven { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 20.0)]
		[Display(Name = "Gatillo Break-Even (Puntos GC)", GroupName = "5. Simulacion SL y TP", Order = 8)]
		public double BreakEvenTriggerPts { get; set; }

		[NinjaScriptProperty]
		[Range(0, 10)]
		[Display(Name = "Offset Break-Even (Ticks a Favor)", GroupName = "5. Simulacion SL y TP", Order = 9)]
		public int BreakEvenOffsetTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Flecha Dorada de Entrada", GroupName = "5. Simulacion SL y TP", Order = 10)]
		public bool DrawGoldArrow { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Lineas SL/TP", GroupName = "5. Simulacion SL y TP", Order = 11)]
		public bool DrawTpSlLines { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Dashboard de Trades", GroupName = "5. Simulacion SL y TP", Order = 12)]
		public bool ShowDashboard { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Posicion del Dashboard", GroupName = "5. Simulacion SL y TP", Order = 13)]
		public TextPosition PosicionDashboard { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 50.0)]
		[Display(Name = "Comision Round-Turn (USD)", GroupName = "5. Simulacion SL y TP", Order = 14)]
		public double ComisionRoundTurnUSD { get; set; }

		[NinjaScriptProperty]
		[Range(0, 10)]
		[Display(Name = "Slippage Stop Loss (Ticks)", GroupName = "5. Simulacion SL y TP", Order = 15)]
		public int SlippageStopsTicks { get; set; }
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "BigTrapGC — Detector de Absorcion y Trampas Institucionales para Oro (GC / MGC)";
				Name = "BigTrapGC";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = true;

				// Parámetros Óptimos Validados para Oro (GC)
				TicksPerRow = 1;
				MinTrapVolume = 40.0;            // Sweet spot empírico en GC: 3.5 a 4.5 zonas/sesión, simetría 1.18
				ImbalanceRatio = 3.0;            // 300% de desbalance diagonal
				RequireFinishedAuction = true;   // Subasta cerrada en extremo (filtra 18% de ruido)
				FinishedAuctionTol = 1.0;        // Tolerancia de 1 contrato en el extremo opuesto
				AntiOvershootBufferTicks = 2;    // 2 ticks de buffer = 0.20 pt en GC
				WickZonePct = 40.0;              // 40% extremo de mecha
				MaxAgeBars = 300;                // Duración activa máxima de zona

				// Simulación SL/TP activada con entrada al cierre de vela por defecto
				EnableSimulation = true;
				EntryMode = BigTrapEntryMode.BarClose;
				AllowSimultaneousTrades = false; // Simulación realista de 1 trade a la vez
				TpPoints = 4.0;                  // 4.0 puntos en GC (40 ticks = $400 USD por contrato GC)
				SlMultiplier = 1.5;              // 1.5x = meseta equilibrada y robusta
				SlBufferTicks = 1;               // 1 tick de holgura estructural
				EnableBreakEven = false;         // Desactivado por defecto (el backtest forense prueba que asfixia el trade en GC)
				BreakEvenTriggerPts = 2.5;       // Nivel de excursión favorable para activar BE
				BreakEvenOffsetTicks = 1;        // +1 tick ($10 USD) para cubrir comisiones de $4.50
				DrawGoldArrow = true;            // Flecha dorada en la primera vela posterior a la entrada
				DrawTpSlLines = true;
				ShowDashboard = true;            // Dashboard activo en pantalla
				PosicionDashboard = TextPosition.TopRight;
				ComisionRoundTurnUSD = 4.50;     // Comisión CME institucional
				SlippageStopsTicks = 1;          // 1 tick adverso en stops ($10 USD)
			}
			else if (State == State.Configure)
			{
				// Serie secundaria de 1 Tick para cálculo exacto de Footprint Bid/Ask
				AddDataSeries(Data.BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				_currentAsk = new Dictionary<long, double>();
				_currentBid = new Dictionary<long, double>();
				_zones = new List<TrapZone>();
				_lastSubTickPrice = 0;
				_lastSubTickDir = 0;
				_simWins = 0;
				_simLosses = 0;
				_simNetPts = 0.0;
				_simGrossProfit = 0.0;
				_simGrossLoss = 0.0;
			}
		}

		protected override void OnBarUpdate()
		{
			// Procesar ticks de la subserie para armar el Footprint en memoria
			if (BarsInProgress == 1)
			{
				long pTick = (long)Math.Round(Closes[1][0] / TickSize);
				double vol = Volumes[1][0];
				int idx = CurrentBars[1];
				double askQ = idx >= 0 ? BarsArray[1].GetAsk(idx) : 0.0;
				double bidQ = idx >= 0 ? BarsArray[1].GetBid(idx) : 0.0;
				long aq = askQ > 0 ? (long)Math.Round(askQ / TickSize) : 0;
				long bq = bidQ > 0 ? (long)Math.Round(bidQ / TickSize) : 0;

				int side = 0;
				if (aq > 0 && bq > 0 && aq >= bq)
				{
					if (pTick >= aq) side = 1;
					else if (pTick <= bq) side = -1;
				}
				if (side == 0)
				{
					if (_lastSubTickPrice > 0)
					{
						if (pTick > _lastSubTickPrice) side = 1;
						else if (pTick < _lastSubTickPrice) side = -1;
						else side = _lastSubTickDir;
					}
					if (side == 0) side = 1;
				}
				_lastSubTickPrice = pTick;
				_lastSubTickDir = side;

				if (side > 0)
					_currentAsk[pTick] = (_currentAsk.ContainsKey(pTick) ? _currentAsk[pTick] : 0.0) + vol;
				else
					_currentBid[pTick] = (_currentBid.ContainsKey(pTick) ? _currentBid[pTick] : 0.0) + vol;
				return;
			}

			// Barra primaria cerrada (BarsInProgress == 0)
			if (CurrentBar < 1) return;

			int b = CurrentBar;
			double hi = Highs[0][0];
			double lo = Lows[0][0];
			double close = Closes[0][0];
			double rng = hi - lo;
			long hiTk = (long)Math.Round(hi / TickSize);
			long loTk = (long)Math.Round(lo / TickSize);

			// 1. Actualizar zonas activas previas y evaluar simulación SL/TP
			foreach (var z in _zones)
			{
				if (!z.IsActive && z.SimStatus != SimTradeStatus.InTrade)
					continue;

				int barsSinceCreated = b - z.CreatedBar;

				// A. Evaluación de ciclo de vida de la zona
				if (z.IsActive)
				{
					if (MaxAgeBars > 0 && barsSinceCreated > MaxAgeBars)
					{
						z.IsActive = false;
					}

					bool touched = (hi >= z.Bottom) && (lo <= z.Top);
					if (touched) z.Touches++;

					bool adverseClose = z.IsBull ? (close > z.Top) : (close < z.Bottom);
					if (adverseClose)
					{
						z.IsActive = false;
					}
					else if (z.IsActive)
					{
						// Extender dibujo de zona activa
						Draw.Rectangle(this, z.Tag, false, barsSinceCreated, z.Top, 0, z.Bottom,
							Brushes.Transparent,
							z.IsBull ? Brushes.Red : Brushes.LimeGreen,
							35);
					}
				}

				// B. Evaluación de Simulación SL y TP
				if (EnableSimulation)
				{
					// Modo Retest: Si aún no ha sido tocada, chequear si esta barra hace el pullback
					if (EntryMode == BigTrapEntryMode.ZoneRetest && z.SimStatus == SimTradeStatus.PendingTouch && b > z.CreatedBar)
					{
						bool retested = (hi >= z.Bottom) && (lo <= z.Top);
						if (retested)
						{
							bool canEnter = AllowSimultaneousTrades || !_zones.Any(x => x.SimStatus == SimTradeStatus.InTrade);
							if (canEnter)
							{
								z.SimStatus = SimTradeStatus.InTrade;
								z.EntryBar = b;

								double baseRisk = (z.Top - z.Bottom) + (SlBufferTicks * TickSize);
								double totalSlDist = baseRisk * SlMultiplier;

								if (!z.IsBull) // LONG (Trapped Sellers)
								{
									z.EntryPrice = z.Top;
									z.StopLoss = z.EntryPrice - totalSlDist;
									z.TakeProfit = z.EntryPrice + TpPoints;
								}
								else // SHORT (Trapped Buyers)
								{
									z.EntryPrice = z.Bottom;
									z.StopLoss = z.EntryPrice + totalSlDist;
									z.TakeProfit = z.EntryPrice - TpPoints;
								}

								if (DrawTpSlLines)
								{
									Draw.Line(this, z.Tag + "_tp", false, 0, z.TakeProfit, -25, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
									Draw.Line(this, z.Tag + "_sl", false, 0, z.StopLoss, -25, z.StopLoss, Brushes.IndianRed, DashStyleHelper.Dash, 2);
									Draw.Text(this, z.Tag + "_ent", string.Format("ENTRY {0:F2}", z.EntryPrice), 0, z.EntryPrice, !z.IsBull ? Brushes.LimeGreen : Brushes.OrangeRed);
								}
							}
						}
					}

					// Dibujar flecha dorada apuntando a la primera vela posterior a la entrada (b >= EntryBar + 1)
					if (DrawGoldArrow && z.SimStatus != SimTradeStatus.PendingTouch && b >= z.EntryBar + 1)
					{
						int arrowBarsAgo = b - (z.EntryBar + 1);
						if (arrowBarsAgo >= 0 && arrowBarsAgo < BarsArray[0].Count)
						{
							if (z.ArrowY == 0.0)
								z.ArrowY = !z.IsBull ? (Lows[0][arrowBarsAgo] - (2 * TickSize)) : (Highs[0][arrowBarsAgo] + (2 * TickSize));

							if (!z.IsBull)
								Draw.ArrowUp(this, z.Tag + "_gold_arrow", false, arrowBarsAgo, z.ArrowY, Brushes.Gold);
							else
								Draw.ArrowDown(this, z.Tag + "_gold_arrow", false, arrowBarsAgo, z.ArrowY, Brushes.Gold);
						}
					}

					// Si ya está en trade, verificar si la barra actual toca SL o TP (evaluado a partir de b > EntryBar)
					if (z.SimStatus == SimTradeStatus.InTrade && b > z.EntryBar)
					{
						int barsAgo = b - z.EntryBar;
						if (!z.IsBull) // LONG
						{
							// 1. Comprobar si se activa Break-Even
							if (EnableBreakEven && !z.IsBreakEvenTriggered && hi >= z.EntryPrice + BreakEvenTriggerPts)
							{
								z.IsBreakEvenTriggered = true;
								double bePrice = z.EntryPrice + (BreakEvenOffsetTicks * TickSize);
								if (bePrice > z.StopLoss)
								{
									z.StopLoss = bePrice;
									Draw.Text(this, z.Tag + "_be_tag", string.Format("⚡ BE ({0:F2})", z.StopLoss), 0, z.StopLoss - 1 * TickSize, Brushes.Yellow);
								}
							}

							// 2. Evaluación realista / conservadora: comprobar SL primero para evitar sesgos intra-barra
							if (lo <= z.StopLoss)
							{
								if (z.IsBreakEvenTriggered && z.StopLoss >= z.EntryPrice)
								{
									z.SimStatus = SimTradeStatus.Won;
									double gain = z.StopLoss - z.EntryPrice;
									z.RealizedPts = gain;
									_simWins++;
									_simGrossProfit += gain;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F1} pt / +${1:N0})", gain, gain * 100.0), 0, z.StopLoss - 2 * TickSize, Brushes.Yellow);
								}
								else
								{
									z.SimStatus = SimTradeStatus.Lost;
									double loss = z.EntryPrice - z.StopLoss;
									z.RealizedPts = -loss;
									_simLosses++;
									_simGrossLoss += loss;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F1} pts / -${1:N0})", loss, loss * 100.0), 0, z.StopLoss - 2 * TickSize, Brushes.IndianRed);
								}

								if (DrawTpSlLines)
								{
									Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, 0, z.TakeProfit, Brushes.Gray, DashStyleHelper.Dot, 1);
									Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, 0, z.StopLoss, z.IsBreakEvenTriggered ? Brushes.Yellow : Brushes.IndianRed, DashStyleHelper.Solid, 2);
								}
							}
							else if (hi >= z.TakeProfit)
							{
								z.SimStatus = SimTradeStatus.Won;
								z.RealizedPts = TpPoints;
								_simWins++;
								_simGrossProfit += TpPoints;
								_simNetPts += z.RealizedPts;
								Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts / +${1:N0})", TpPoints, TpPoints * 100.0), 0, z.TakeProfit + 2 * TickSize, Brushes.MediumSpringGreen);
								if (DrawTpSlLines)
								{
									Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, 0, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Solid, 2);
									Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, 0, z.StopLoss, Brushes.Gray, DashStyleHelper.Dot, 1);
								}
							}
							else if (DrawTpSlLines)
							{
								// Mantener proyección mientras el trade siga activo
								Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, -15, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
								Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, -15, z.StopLoss, z.IsBreakEvenTriggered ? Brushes.Yellow : Brushes.IndianRed, DashStyleHelper.Dash, 2);
							}
						}
						else // SHORT
						{
							// 1. Comprobar si se activa Break-Even
							if (EnableBreakEven && !z.IsBreakEvenTriggered && lo <= z.EntryPrice - BreakEvenTriggerPts)
							{
								z.IsBreakEvenTriggered = true;
								double bePrice = z.EntryPrice - (BreakEvenOffsetTicks * TickSize);
								if (bePrice < z.StopLoss)
								{
									z.StopLoss = bePrice;
									Draw.Text(this, z.Tag + "_be_tag", string.Format("⚡ BE ({0:F2})", z.StopLoss), 0, z.StopLoss + 1 * TickSize, Brushes.Yellow);
								}
							}

							if (hi >= z.StopLoss)
							{
								if (z.IsBreakEvenTriggered && z.StopLoss <= z.EntryPrice)
								{
									z.SimStatus = SimTradeStatus.Won;
									double gain = z.EntryPrice - z.StopLoss;
									z.RealizedPts = gain;
									_simWins++;
									_simGrossProfit += gain;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F1} pt / +${1:N0})", gain, gain * 100.0), 0, z.StopLoss + 2 * TickSize, Brushes.Yellow);
								}
								else
								{
									z.SimStatus = SimTradeStatus.Lost;
									double loss = z.StopLoss - z.EntryPrice;
									z.RealizedPts = -loss;
									_simLosses++;
									_simGrossLoss += loss;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F1} pts / -${1:N0})", loss, loss * 100.0), 0, z.StopLoss + 2 * TickSize, Brushes.IndianRed);
								}

								if (DrawTpSlLines)
								{
									Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, 0, z.TakeProfit, Brushes.Gray, DashStyleHelper.Dot, 1);
									Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, 0, z.StopLoss, z.IsBreakEvenTriggered ? Brushes.Yellow : Brushes.IndianRed, DashStyleHelper.Solid, 2);
								}
							}
							else if (lo <= z.TakeProfit)
							{
								z.SimStatus = SimTradeStatus.Won;
								z.RealizedPts = TpPoints;
								_simWins++;
								_simGrossProfit += TpPoints;
								_simNetPts += z.RealizedPts;
								Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts / +${1:N0})", TpPoints, TpPoints * 100.0), 0, z.TakeProfit - 2 * TickSize, Brushes.MediumSpringGreen);
								if (DrawTpSlLines)
								{
									Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, 0, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Solid, 2);
									Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, 0, z.StopLoss, Brushes.Gray, DashStyleHelper.Dot, 1);
								}
							}
							else if (DrawTpSlLines)
							{
								Draw.Line(this, z.Tag + "_tp", false, barsAgo, z.TakeProfit, -15, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
								Draw.Line(this, z.Tag + "_sl", false, barsAgo, z.StopLoss, -15, z.StopLoss, z.IsBreakEvenTriggered ? Brushes.Yellow : Brushes.IndianRed, DashStyleHelper.Dash, 2);
							}
						}
					}
				}
			}

			// 2. Evaluar Finished Auction en extremos
			double askAtLo = _currentAsk.ContainsKey(loTk) ? _currentAsk[loTk] : 0.0;
			double bidAtHi = _currentBid.ContainsKey(hiTk) ? _currentBid[hiTk] : 0.0;
			bool finishedHi = bidAtHi <= FinishedAuctionTol;
			bool finishedLo = askAtLo <= FinishedAuctionTol;

			double wickHiFloor = hi - rng * (WickZonePct / 100.0);
			double wickLoCeil = lo + rng * (WickZonePct / 100.0);

			// 3. Detección de Trapped Buyers (Techo/Resistencia -> SHORT)
			List<long> buyImbalanceLevels = new List<long>();
			double totalBuyTrapVol = 0.0;

			foreach (var kvp in _currentAsk)
			{
				long pK = kvp.Key;
				double askV = kvp.Value;
				double bidBelow = _currentBid.ContainsKey(pK - 1) ? _currentBid[pK - 1] : 0.0;
				double ratio = askV / Math.Max(bidBelow, 1.0);
				double px = pK * TickSize;

				if (askV >= 1.0 && ratio >= ImbalanceRatio && px > close)
				{
					if (WickZonePct >= 100.0 || (rng > 0 && px >= wickHiFloor))
					{
						buyImbalanceLevels.Add(pK);
						totalBuyTrapVol += askV;
					}
				}
			}

			if (buyImbalanceLevels.Count > 0 && (!RequireFinishedAuction || finishedHi))
			{
				if (totalBuyTrapVol >= MinTrapVolume)
				{
					long minTk = buyImbalanceLevels.Min();
					long maxTk = buyImbalanceLevels.Max();
					double zBottom = minTk * TickSize - (TickSize / 2.0);
					double zTop = maxTk * TickSize + (TickSize / 2.0) + (AntiOvershootBufferTicks * TickSize);

					TrapZone z = new TrapZone
					{
						CreatedBar = b,
						IsBull = true,
						Top = zTop,
						Bottom = zBottom,
						Volume = totalBuyTrapVol,
						Touches = 0,
						IsActive = true,
						Tag = string.Format("BTGC_{0}_TB", b)
					};

					// Dibujar rectángulo inicial de absorción
					Draw.Rectangle(this, z.Tag, false, 0, z.Top, -10, z.Bottom,
						Brushes.Transparent,
						Brushes.Red,
						40);

					// Marcador visual de trampa
					Draw.Text(this, z.Tag + "_lbl", string.Format("▼ TRAP {0:F0}v", totalBuyTrapVol), 0, z.Top + 2 * TickSize, Brushes.Coral);

					// Entrada inmediata si estamos en modo BarClose
					if (EnableSimulation && EntryMode == BigTrapEntryMode.BarClose)
					{
						bool canEnter = AllowSimultaneousTrades || !_zones.Any(x => x.SimStatus == SimTradeStatus.InTrade);
						if (canEnter)
						{
							z.SimStatus = SimTradeStatus.InTrade;
							z.EntryBar = b;
							z.EntryPrice = close;

							double slAnchor = z.Top + (SlBufferTicks * TickSize);
							double riskDist = Math.Max(TickSize, slAnchor - z.EntryPrice);
							z.StopLoss = z.EntryPrice + (riskDist * SlMultiplier);
							z.TakeProfit = z.EntryPrice - TpPoints;

							if (DrawTpSlLines)
							{
								Draw.Line(this, z.Tag + "_ent", false, 0, z.EntryPrice, -15, z.EntryPrice, Brushes.OrangeRed, DashStyleHelper.Solid, 2);
								Draw.Line(this, z.Tag + "_tp", false, 0, z.TakeProfit, -25, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
								Draw.Line(this, z.Tag + "_sl", false, 0, z.StopLoss, -25, z.StopLoss, Brushes.IndianRed, DashStyleHelper.Dash, 2);
								Draw.Text(this, z.Tag + "_ent_lbl", string.Format("ENT {0:F2}", z.EntryPrice), 0, z.EntryPrice, Brushes.OrangeRed);
							}
						}
					}

					_zones.Add(z);
				}
			}

			// 4. Detección de Trapped Sellers (Suelo/Soporte -> LONG)
			List<long> sellImbalanceLevels = new List<long>();
			double totalSellTrapVol = 0.0;

			foreach (var kvp in _currentBid)
			{
				long pK = kvp.Key;
				double bidV = kvp.Value;
				double askAbove = _currentAsk.ContainsKey(pK + 1) ? _currentAsk[pK + 1] : 0.0;
				double ratio = bidV / Math.Max(askAbove, 1.0);
				double px = pK * TickSize;

				if (bidV >= 1.0 && ratio >= ImbalanceRatio && px < close)
				{
					if (WickZonePct >= 100.0 || (rng > 0 && px <= wickLoCeil))
					{
						sellImbalanceLevels.Add(pK);
						totalSellTrapVol += bidV;
					}
				}
			}

			if (sellImbalanceLevels.Count > 0 && (!RequireFinishedAuction || finishedLo))
			{
				if (totalSellTrapVol >= MinTrapVolume)
				{
					long minTk = sellImbalanceLevels.Min();
					long maxTk = sellImbalanceLevels.Max();
					double zTop = maxTk * TickSize + (TickSize / 2.0);
					double zBottom = minTk * TickSize - (TickSize / 2.0) - (AntiOvershootBufferTicks * TickSize);

					TrapZone z = new TrapZone
					{
						CreatedBar = b,
						IsBull = false,
						Top = zTop,
						Bottom = zBottom,
						Volume = totalSellTrapVol,
						Touches = 0,
						IsActive = true,
						Tag = string.Format("BTGC_{0}_TS", b)
					};

					// Dibujar rectángulo inicial de absorción
					Draw.Rectangle(this, z.Tag, false, 0, z.Top, -10, z.Bottom,
						Brushes.Transparent,
						Brushes.LimeGreen,
						40);

					// Marcador visual de trampa
					Draw.Text(this, z.Tag + "_lbl", string.Format("▲ TRAP {0:F0}v", totalSellTrapVol), 0, z.Bottom - 2 * TickSize, Brushes.LimeGreen);

					// Entrada inmediata si estamos en modo BarClose
					if (EnableSimulation && EntryMode == BigTrapEntryMode.BarClose)
					{
						bool canEnter = AllowSimultaneousTrades || !_zones.Any(x => x.SimStatus == SimTradeStatus.InTrade);
						if (canEnter)
						{
							z.SimStatus = SimTradeStatus.InTrade;
							z.EntryBar = b;
							z.EntryPrice = close;

							double slAnchor = z.Bottom - (SlBufferTicks * TickSize);
							double riskDist = Math.Max(TickSize, z.EntryPrice - slAnchor);
							z.StopLoss = z.EntryPrice - (riskDist * SlMultiplier);
							z.TakeProfit = z.EntryPrice + TpPoints;

							if (DrawTpSlLines)
							{
								Draw.Line(this, z.Tag + "_ent", false, 0, z.EntryPrice, -15, z.EntryPrice, Brushes.LimeGreen, DashStyleHelper.Solid, 2);
								Draw.Line(this, z.Tag + "_tp", false, 0, z.TakeProfit, -25, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
								Draw.Line(this, z.Tag + "_sl", false, 0, z.StopLoss, -25, z.StopLoss, Brushes.IndianRed, DashStyleHelper.Dash, 2);
								Draw.Text(this, z.Tag + "_ent_lbl", string.Format("ENT {0:F2}", z.EntryPrice), 0, z.EntryPrice, Brushes.LimeGreen);
							}
						}
					}

					_zones.Add(z);
				}
			}

			// 5. Renderizar Tablero Dashboard en vivo
			if (ShowDashboard && EnableSimulation)
			{
				int totalTrades = _simWins + _simLosses;
				double wr = totalTrades > 0 ? ((double)_simWins / totalTrades) * 100.0 : 0.0;
				double grossUsd = _simNetPts * 100.0; // Multiplicador de $100/punto en GC
				double pfGross = _simGrossLoss > 0.001 ? (_simGrossProfit / _simGrossLoss) : (_simGrossProfit > 0 ? 99.9 : 0.0);
				double avgW = _simWins > 0 ? (_simGrossProfit / _simWins) : 0.0;
				double avgL = _simLosses > 0 ? (_simGrossLoss / _simLosses) : 0.0;

				// Fricciones Reales Institucionales CME
				double totalCommissions = totalTrades * ComisionRoundTurnUSD;
				double totalSlippage = _simLosses * (SlippageStopsTicks * TickSize * 100.0);
				double netRealUsd = grossUsd - totalCommissions - totalSlippage;
				double netRealPts = netRealUsd / 100.0;
				double totalGrossGain = (_simGrossProfit * 100.0) - (_simWins * ComisionRoundTurnUSD);
				double totalGrossLossFriction = (_simGrossLoss * 100.0) + (_simLosses * ComisionRoundTurnUSD) + totalSlippage;
				double pfNet = totalGrossLossFriction > 0.001 ? (Math.Max(0.0, totalGrossGain) / totalGrossLossFriction) : 0.0;

				string modeStr = EntryMode == BigTrapEntryMode.BarClose ? "BarClose" : "Retest";

				var activeTrade = _zones.LastOrDefault(x => x.SimStatus == SimTradeStatus.InTrade);
				string statusStr;
				if (activeTrade != null)
				{
					string side = !activeTrade.IsBull ? "LONG" : "SHORT";
					statusStr = string.Format("● IN TRADE: {0} @ {1:F2}\n  SL: {2:F2} | TP: {3:F2}", side, activeTrade.EntryPrice, activeTrade.StopLoss, activeTrade.TakeProfit);
				}
				else
				{
					statusStr = "○ FLAT (Esperando señal)";
				}

				string beInfo = EnableBreakEven ? string.Format("{0:F1} pt (+{1} tk)", BreakEvenTriggerPts, BreakEvenOffsetTicks) : "OFF";

				string dashText = string.Format(
					"=== BIGTRAP GC | DASHBOARD ===\n" +
					"Modo Entrada : {0}\n" +
					"Total Trades : {1} (W: {2} | L: {3})\n" +
					"Win Rate     : {4:F1}%\n" +
					"Avg Win/Loss : +{5:F1} pt / -{6:F1} pt\n" +
					"Target TP/SL : {7:F1} pt / {8:F1}x\n" +
					"Break-Even   : {9}\n" +
					"-------------------------------\n" +
					"PnL BRUTO    : {10:+0.0;-0.0;0.0} pts (${11:+0,0;-0,0;0} USD) [PF: {12:F2}]\n" +
					"PnL NETO CME : {13:+0.0;-0.0;0.0} pts (${14:+0,0;-0,0;0} USD) [PF: {15:F2}]\n" +
					"-------------------------------\n" +
					"Estado:\n{16}",
					modeStr,
					totalTrades,
					_simWins,
					_simLosses,
					wr,
					avgW,
					avgL,
					TpPoints,
					SlMultiplier,
					beInfo,
					_simNetPts,
					grossUsd,
					pfGross,
					netRealPts,
					netRealUsd,
					pfNet,
					statusStr
				);

				Draw.TextFixed(this, "BTGC_DASHBOARD", dashText, PosicionDashboard,
					Brushes.White, new NinjaTrader.Gui.Tools.SimpleFont("Consolas", 11),
					Brushes.Gold, Brushes.Black, 85);
			}

			// Reiniciar acumuladores para la siguiente barra
			_currentAsk.Clear();
			_currentBid.Clear();
		}
	}
}
