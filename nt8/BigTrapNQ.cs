// # meta indicator=BigTrapNQ,version=1.2.0
//
// BigTrapNQ — Detector de Absorción y Trampas Institucionales para Nasdaq (NQ / MNQ).
// 
// Optimizado para CME Nasdaq Futures:
// - Tick Size: 0.25 pt ($5.00 USD por tick en NQ, $0.50 USD en MNQ).
// - Multiplicador de Punto: $20.00 USD por punto entero ($2.00 USD en MNQ).
// - Simulación Visual en Tiempo Real:
//   * Modo BarClose: Entrada inmediata al cierre de la vela de señal.
//   * Modo ZoneRetest: Entrada al pullback / re-test a la zona de absorción.
//   * Flecha Dorada: Señaliza con precisión el inicio de la primera vela posterior a la entrada.
//   * Break-Even Dinámico: Gatillo en puntos y offset para absorber comisiones.
//   * Dashboard en Vivo: HUD interactivo con PnL Bruto, PnL Neto CME ($4.50 com + 1 tk slippage), WinRate, PF y estado de posición.
// 
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
	public enum BigTrapNQEntryMode
	{
		BarClose,    // Entrada inmediata al cierre de la vela que genera la señal
		ZoneRetest   // Entrada en el retroceso (pullback / re-test) a la zona
	}
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrapNQ : Indicator
	{
		private const string IND_VERSION = "1.2.0";

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
		[Range(10, 500)]
		[Display(Name = "Min Trap Volume", GroupName = "2. Absorcion NQ", Order = 1)]
		public double MinTrapVolume { get; set; }

		[NinjaScriptProperty]
		[Range(1.5, 10.0)]
		[Display(Name = "Imbalance Ratio", GroupName = "2. Absorcion NQ", Order = 2)]
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
		[Range(50, 2000)]
		[Display(Name = "Max Age Bars", GroupName = "4. Gestion de Riesgo", Order = 3)]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Activar Simulacion SL/TP", GroupName = "5. Simulacion SL y TP", Order = 1)]
		public bool EnableSimulation { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo de Entrada", GroupName = "5. Simulacion SL y TP", Order = 2)]
		public BigTrapNQEntryMode EntryMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Permitir Trades Simultaneos", GroupName = "5. Simulacion SL y TP", Order = 3)]
		public bool AllowSimultaneousTrades { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 150.0)]
		[Display(Name = "Take Profit (Puntos NQ)", GroupName = "5. Simulacion SL y TP", Order = 4)]
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
		[Range(1.0, 100.0)]
		[Display(Name = "Gatillo Break-Even (Puntos NQ)", GroupName = "5. Simulacion SL y TP", Order = 8)]
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
				Description = "BigTrapNQ — Detector de Absorcion y Trampas Institucionales para NQ";
				Name = "BigTrapNQ";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = true;

				// Parámetros Óptimos Validados para NQ
				TicksPerRow = 1;
				MinTrapVolume = 60.0;            // Umbral calibrado a la profundidad de NQ
				ImbalanceRatio = 3.0;            // 300% de desbalance diagonal
				RequireFinishedAuction = true;   // Subasta cerrada en el extremo
				FinishedAuctionTol = 1.0;
				AntiOvershootBufferTicks = 2;    // 2 ticks = 0.50 pt en NQ
				WickZonePct = 40.0;              // 40% extremo de la mecha
				MaxAgeBars = 500;

				// Simulación SL/TP activada con BarClose por defecto
				EnableSimulation = true;
				EntryMode = BigTrapNQEntryMode.BarClose;
				AllowSimultaneousTrades = false; // 1 trade activo a la vez
				TpPoints = 24.0;                 // 24 puntos en NQ (96 ticks = $480 USD por contrato NQ)
				SlMultiplier = 1.5;              // 1.5x de riesgo estructural
				SlBufferTicks = 2;               // 2 ticks de holgura (0.50 pt)
				EnableBreakEven = false;         // Desactivado por defecto
				BreakEvenTriggerPts = 12.0;      // Gatillo a +12 puntos
				BreakEvenOffsetTicks = 2;        // +2 ticks (+0.50 pt = +$10 USD para cubrir comisiones)
				DrawGoldArrow = true;            // Flecha dorada en primera vela posterior a la entrada
				DrawTpSlLines = true;
				ShowDashboard = true;
				PosicionDashboard = TextPosition.TopRight;
				ComisionRoundTurnUSD = 4.50;     // Comisión institucional CME por contrato NQ
				SlippageStopsTicks = 1;          // 1 tick de deslizamiento adverso ($5 USD)
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);
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
			// Procesar ticks de la subserie para armar el Footprint exacto
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
						side = pTick > _lastSubTickPrice ? 1 : (pTick < _lastSubTickPrice ? -1 : _lastSubTickDir);
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
					if (EntryMode == BigTrapNQEntryMode.ZoneRetest && z.SimStatus == SimTradeStatus.PendingTouch && b > z.CreatedBar)
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

					// Si ya está en trade, verificar si la barra actual toca SL o TP
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

							// 2. Evaluación pesimista / conservadora: comprobar SL primero para evitar sesgos intra-barra
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
									Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F1} pt / +${1:N0})", gain, gain * 20.0), 0, z.StopLoss - 2 * TickSize, Brushes.Yellow);
								}
								else
								{
									z.SimStatus = SimTradeStatus.Lost;
									double loss = z.EntryPrice - z.StopLoss;
									z.RealizedPts = -loss;
									_simLosses++;
									_simGrossLoss += loss;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F1} pts / -${1:N0})", loss, loss * 20.0), 0, z.StopLoss - 2 * TickSize, Brushes.IndianRed);
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
								Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts / +${1:N0})", TpPoints, TpPoints * 20.0), 0, z.TakeProfit + 2 * TickSize, Brushes.MediumSpringGreen);
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
									Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F1} pt / +${1:N0})", gain, gain * 20.0), 0, z.StopLoss + 2 * TickSize, Brushes.Yellow);
								}
								else
								{
									z.SimStatus = SimTradeStatus.Lost;
									double loss = z.StopLoss - z.EntryPrice;
									z.RealizedPts = -loss;
									_simLosses++;
									_simGrossLoss += loss;
									_simNetPts += z.RealizedPts;
									Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F1} pts / -${1:N0})", loss, loss * 20.0), 0, z.StopLoss + 2 * TickSize, Brushes.IndianRed);
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
								Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts / +${1:N0})", TpPoints, TpPoints * 20.0), 0, z.TakeProfit - 2 * TickSize, Brushes.MediumSpringGreen);
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

			// 3. Detección de Trapped Buyers (Techo / Resistencia -> SHORT)
			List<long> buyImbTicks = new List<long>();
			double buyVol = 0;
			foreach (var kvp in _currentAsk)
			{
				long tk = kvp.Key;
				double a = kvp.Value;
				double bv = _currentBid.ContainsKey(tk - 1) ? _currentBid[tk - 1] : 0.0;
				double ratio = a / Math.Max(bv, 1.0);
				double px = tk * TickSize;

				if (a >= 1.0 && ratio >= ImbalanceRatio && px > close && px >= wickHiFloor)
				{
					buyImbTicks.Add(tk);
					buyVol += a;
				}
			}

			if (buyImbTicks.Count > 0 && buyVol >= MinTrapVolume && (!RequireFinishedAuction || finishedHi))
			{
				double zBottom = buyImbTicks.Min() * TickSize - (TickSize / 2.0);
				double zTop = buyImbTicks.Max() * TickSize + (TickSize / 2.0) + (AntiOvershootBufferTicks * TickSize);
				string tag = "BT_NQ_" + b + "_TB";

				TrapZone z = new TrapZone
				{
					CreatedBar = b,
					IsBull = true,
					Top = zTop,
					Bottom = zBottom,
					Volume = buyVol,
					Touches = 0,
					IsActive = true,
					Tag = tag
				};

				// Dibujar zona y etiqueta de trampa
				Draw.Rectangle(this, tag, false, 0, zTop, -10, zBottom, Brushes.Transparent, Brushes.Red, 40);
				Draw.Text(this, tag + "_lbl", string.Format("▼ TRAP {0:0}c", buyVol), 0, zTop + 2 * TickSize, Brushes.Coral);

				// Entrada inmediata si estamos en modo BarClose
				if (EnableSimulation && EntryMode == BigTrapNQEntryMode.BarClose)
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

			// 4. Detección de Trapped Sellers (Suelo / Soporte -> LONG)
			List<long> sellImbTicks = new List<long>();
			double sellVol = 0;
			foreach (var kvp in _currentBid)
			{
				long tk = kvp.Key;
				double bv = kvp.Value;
				double a = _currentAsk.ContainsKey(tk + 1) ? _currentAsk[tk + 1] : 0.0;
				double ratio = bv / Math.Max(a, 1.0);
				double px = tk * TickSize;

				if (bv >= 1.0 && ratio >= ImbalanceRatio && px < close && px <= wickLoCeil)
				{
					sellImbTicks.Add(tk);
					sellVol += bv;
				}
			}

			if (sellImbTicks.Count > 0 && sellVol >= MinTrapVolume && (!RequireFinishedAuction || finishedLo))
			{
				double zTop = sellImbTicks.Max() * TickSize + (TickSize / 2.0);
				double zBottom = sellImbTicks.Min() * TickSize - (TickSize / 2.0) - (AntiOvershootBufferTicks * TickSize);
				string tag = "BT_NQ_" + b + "_TS";

				TrapZone z = new TrapZone
				{
					CreatedBar = b,
					IsBull = false,
					Top = zTop,
					Bottom = zBottom,
					Volume = sellVol,
					Touches = 0,
					IsActive = true,
					Tag = tag
				};

				Draw.Rectangle(this, tag, false, 0, zTop, -10, zBottom, Brushes.Transparent, Brushes.LimeGreen, 40);
				Draw.Text(this, tag + "_lbl", string.Format("▲ TRAP {0:0}c", sellVol), 0, zBottom - 2 * TickSize, Brushes.LimeGreen);

				// Entrada inmediata si estamos en modo BarClose
				if (EnableSimulation && EntryMode == BigTrapNQEntryMode.BarClose)
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

			// 5. Renderizar Tablero Dashboard en vivo
			if (ShowDashboard && EnableSimulation)
			{
				int totalTrades = _simWins + _simLosses;
				double wr = totalTrades > 0 ? ((double)_simWins / totalTrades) * 100.0 : 0.0;
				double grossUsd = _simNetPts * 20.0; // Multiplicador de $20.00/punto en NQ ($2.00 en MNQ)
				double pfGross = _simGrossLoss > 0.001 ? (_simGrossProfit / _simGrossLoss) : (_simGrossProfit > 0 ? 99.9 : 0.0);
				double avgW = _simWins > 0 ? (_simGrossProfit / _simWins) : 0.0;
				double avgL = _simLosses > 0 ? (_simGrossLoss / _simLosses) : 0.0;

				// Fricciones Reales Institucionales CME
				double totalCommissions = totalTrades * ComisionRoundTurnUSD;
				double totalSlippage = _simLosses * (SlippageStopsTicks * TickSize * 20.0);
				double netRealUsd = grossUsd - totalCommissions - totalSlippage;
				double netRealPts = netRealUsd / 20.0;
				double totalGrossGain = (_simGrossProfit * 20.0) - (_simWins * ComisionRoundTurnUSD);
				double totalGrossLossFriction = (_simGrossLoss * 20.0) + (_simLosses * ComisionRoundTurnUSD) + totalSlippage;
				double pfNet = totalGrossLossFriction > 0.001 ? (Math.Max(0.0, totalGrossGain) / totalGrossLossFriction) : 0.0;

				string modeStr = EntryMode == BigTrapNQEntryMode.BarClose ? "BarClose" : "Retest";

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
					"=== BIGTRAP NQ | DASHBOARD ===\n" +
					"Modo Entrada : {0}\n" +
					"Total Trades : {1} (W: {2} | L: {3})\n" +
					"Win Rate     : {4:F1}%\n" +
					"Avg Win/Loss : +{5:F1} pt / -{6:F1} pt\n" +
					"Target TP/SL : {7:F1} pt / {8:F1}x\n" +
					"Break-Even   : {9}\n" +
					"-------------------------------\n" +
					"PnL BRUTO    : {10:+0.00;-0.00;0.00} pts (${11:+0,0;-0,0;0} USD) [PF: {12:F2}]\n" +
					"PnL NETO CME : {13:+0.00;-0.00;0.00} pts (${14:+0,0;-0,0;0} USD) [PF: {15:F2}]\n" +
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

				Draw.TextFixed(this, "BT_NQ_DASHBOARD", dashText, PosicionDashboard,
					Brushes.White, new NinjaTrader.Gui.Tools.SimpleFont("Consolas", 11),
					Brushes.Gold, Brushes.Black, 85);
			}

			// Reiniciar acumuladores para la siguiente barra
			_currentAsk.Clear();
			_currentBid.Clear();
		}
	}
}
