// # meta indicator=BigTrapVWAP_NQ,version=1.0.0
//
// BigTrapVWAP_NQ — Sistema Integral de Confluencia: Footprint Absorption + Anchored VWAP para CME Nasdaq (NQ / MNQ).
//
// Configuración Canónica por Defecto para Nasdaq:
// - Tick Size: 0.25 pt ($5.00 USD / tick en NQ, $0.50 USD en MNQ).
// - Multiplicador de Punto: $20.00 USD por punto entero ($2.00 USD en MNQ).
// - Resolución Recomendada: Barras de 10 Ticks o 25 Ticks (10-Tick / 25-Tick Bars).
// - Punto de Anclaje VWAP: 08:30 CT (09:30 ET / 10:30 Argentina) — Apertura Cash Wall Street (RTH).
// - Modo de Confluencia: Dual_Reversion_And_Trend (Continuación tendencial con pullback a VWAP + Reversión en extremos).
//   * COMPRA si Trapped Sellers ocurre en tendencia sobre VWAP (+0.5σ a +2.2σ) o en sobreventa extrema (<= -1.5σ).
//   * VENDE si Trapped Buyers ocurre en tendencia bajo VWAP (-0.5σ a -2.2σ) o en sobrecompra extrema (>= +1.5σ).
//   * Filtra el ruido aleatorio en la zona neutral central (entre -0.5σ y +0.5σ sin momentum).
// - Absorción Footprint: MinVol = 60.0 contratos, Imbalance = 3.0 (300%), Finished Auction = True (Tol = 0.0).
// - Gestión de Trade: Entrada BarClose, TP = 24.0 pt ($480 USD NQ / $48 MNQ), SL = 1.5x estructural (+2 tk buffer).
// - Costes CME Reales: $4.50 comisión round-turn + 1 tick slippage en paradas ($5.00 USD).
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
	public enum ConfluenceFilterNQ
	{
		Dual_Reversion_And_Trend,   // Ambos modos válidos (Recomendado NQ: tendencia y reversión en extremos)
		Trend_Continuation,         // Solo continuación de tendencia (Pullback a favor de VWAP)
		MeanReversion_Extremes,     // Solo reversión desde bandas extremas (>= +1.5σ o <= -1.5σ)
		None_Unfiltered             // Dispara todas las trampas sin filtrar por VWAP
	}

	public enum VWAPAnchorNQConfluence
	{
		RTH_WallStreet_0830_CT,     // 08:30 CT / 10:30 Argentina — Apertura Cash Wall Street (Recomendado NQ)
		Session_CME_1700_CT,        // 17:00 CT / 19:00 Argentina — Apertura Globex (Sesión diaria 23h)
		European_Open_0200_CT,      // 02:00 CT / 04:00 Argentina — Apertura europea / Londres
		Chart_Session,              // Según la plantilla de sesión configurada en el gráfico
		Custom_Time                 // Hora y minuto personalizados
	}

	public enum ConfluenceEntryNQ
	{
		BarClose,    // Entrada inmediata al cierre de la vela de señal (Recomendado)
		ZoneRetest   // Entrada al re-testeo / pullback a la zona de absorción
	}
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrapVWAP_NQ : Indicator
	{
		private const string IND_VERSION = "1.0.0";

		private enum SimTradeStatus { PendingTouch, InTrade, Won, Lost }

		private sealed class ConfluentZone
		{
			public int CreatedBar;
			public bool IsBull; // true = Trapped Buyers (Techo/SHORT), false = Trapped Sellers (Suelo/LONG)
			public double Top;
			public double Bottom;
			public double Volume;
			public int Touches;
			public bool IsActive;
			public string Tag;
			public bool PassedFilter;
			public string FilterNote;

			// Simulación de Ejecución
			public SimTradeStatus SimStatus = SimTradeStatus.PendingTouch;
			public int EntryBar = -1;
			public double EntryPrice;
			public double StopLoss;
			public double TakeProfit;
			public double RealizedPts = 0.0;
			public double ArrowY = 0.0;
			public bool IsBreakEvenTriggered = false;
		}

		// Footprint subserie de 1-tick
		private Dictionary<long, double> _currentAsk;
		private Dictionary<long, double> _currentBid;
		private List<ConfluentZone> _zones;
		private long _lastSubTickPrice;
		private int _lastSubTickDir;

		// Motor VWAP
		private double _cumVol;
		private double _cumPv;
		private double _cumP2v;
		private DateTime _lastAnchorDt;
		private TimeZoneInfo _cmeTz;

		// Métricas de Rendimiento
		private int _simWins;
		private int _simLosses;
		private double _simNetPts;
		private double _simGrossProfit;
		private double _simGrossLoss;
		private int _filteredTrapsCount;
		private int _confluentTrapsCount;

		#region Properties
		[NinjaScriptProperty]
		[Display(Name = "Modo de Confluencia VWAP", GroupName = "1. Filtro de Confluencia", Order = 1)]
		public ConfluenceFilterNQ FilterMode { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 4.0)]
		[Display(Name = "Umbral Extremo (σ)", GroupName = "1. Filtro de Confluencia", Order = 2)]
		public double MinSigmaExtreme { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Punto de Anclaje VWAP", GroupName = "2. Anclaje VWAP", Order = 1)]
		public VWAPAnchorNQConfluence AnchorMode { get; set; }

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name = "Hora Anclaje Personalizada (0-23 CT)", GroupName = "2. Anclaje VWAP", Order = 2)]
		public int CustomAnchorHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name = "Minuto Anclaje Personalizado (0-59 CT)", GroupName = "2. Anclaje VWAP", Order = 3)]
		public int CustomAnchorMinute { get; set; }

		[NinjaScriptProperty]
		[Range(5, 1000)]
		[Display(Name = "Min Trap Volume", GroupName = "3. Absorcion NQ (Nasdaq)", Order = 1)]
		public double MinTrapVolume { get; set; }

		[NinjaScriptProperty]
		[Range(1.5, 10.0)]
		[Display(Name = "Imbalance Ratio", GroupName = "3. Absorcion NQ (Nasdaq)", Order = 2)]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Require Finished Auction", GroupName = "3. Absorcion NQ (Nasdaq)", Order = 3)]
		public bool RequireFinishedAuction { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 10.0)]
		[Display(Name = "Finished Auction Tol", GroupName = "3. Absorcion NQ (Nasdaq)", Order = 4)]
		public double FinishedAuctionTol { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Modo de Entrada", GroupName = "4. Gestion de Trade", Order = 1)]
		public ConfluenceEntryNQ EntryMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Permitir Trades Simultaneos", GroupName = "4. Gestion de Trade", Order = 2)]
		public bool AllowSimultaneousTrades { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 150.0)]
		[Display(Name = "Take Profit (Puntos NQ)", GroupName = "4. Gestion de Trade", Order = 3)]
		public double TpPoints { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 10.0)]
		[Display(Name = "SL Multiplicador", GroupName = "4. Gestion de Trade", Order = 4)]
		public double SlMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0, 20)]
		[Display(Name = "SL Buffer Extra (Ticks)", GroupName = "4. Gestion de Trade", Order = 5)]
		public int SlBufferTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Activar Break-Even", GroupName = "4. Gestion de Trade", Order = 6)]
		public bool EnableBreakEven { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 100.0)]
		[Display(Name = "Gatillo Break-Even (Puntos NQ)", GroupName = "4. Gestion de Trade", Order = 7)]
		public double BreakEvenTriggerPts { get; set; }

		[NinjaScriptProperty]
		[Range(0, 20)]
		[Display(Name = "Offset Break-Even (Ticks a Favor)", GroupName = "4. Gestion de Trade", Order = 8)]
		public int BreakEvenOffsetTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Flecha en Entrada", GroupName = "5. Visualizacion y HUD", Order = 1)]
		public bool DrawEntryArrow { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar Lineas SL/TP", GroupName = "5. Visualizacion y HUD", Order = 2)]
		public bool DrawTpSlLines { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Trampas Filtradas (Gris)", GroupName = "5. Visualizacion y HUD", Order = 3)]
		public bool ShowFilteredTraps { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Mostrar Dashboard de Confluencia", GroupName = "5. Visualizacion y HUD", Order = 4)]
		public bool ShowDashboard { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Posicion del Dashboard", GroupName = "5. Visualizacion y HUD", Order = 5)]
		public TextPosition PosicionDashboard { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 50.0)]
		[Display(Name = "Comision Round-Turn (USD)", GroupName = "6. Fricciones Reales CME", Order = 1)]
		public double ComisionRoundTurnUSD { get; set; }

		[NinjaScriptProperty]
		[Range(0, 10)]
		[Display(Name = "Slippage Stop Loss (Ticks)", GroupName = "6. Fricciones Reales CME", Order = 2)]
		public int SlippageStopsTicks { get; set; }
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description					= "BigTrapVWAP_NQ — Sistema Integral de Confluencia: Footprint + Anchored VWAP para CME Nasdaq (NQ / MNQ)";
				Name						= "BigTrapVWAP_NQ";
				Calculate					= Calculate.OnBarClose;
				IsOverlay					= true;
				DisplayInDataBox			= true;
				DrawOnPricePanel			= true;
				PaintPriceMarkers			= true;
				ScaleJustification			= ScaleJustification.Right;
				IsSuspendedWhileInactive	= true;

				// Parámetros Óptimos Validados para NASDAQ (NQ)
				FilterMode					= ConfluenceFilterNQ.Dual_Reversion_And_Trend; // Doble confluencia (tendencia + reversión extrema)
				MinSigmaExtreme				= 1.5;                                         // Umbral estadístico ±1.5σ
				AnchorMode					= VWAPAnchorNQConfluence.RTH_WallStreet_0830_CT; // 08:30 CT (Apertura Cash Wall Street)
				CustomAnchorHour			= 8;
				CustomAnchorMinute			= 30;

				// Absorción Footprint calibrada a liquidez de NQ
				MinTrapVolume				= 60.0;                                        // 60 contratos acumulados en la zona
				ImbalanceRatio				= 3.0;                                         // 300% ratio de desequilibrio
				RequireFinishedAuction		= true;
				FinishedAuctionTol			= 0.0;                                         // Agotamiento estricto 0 contratos

				// Ejecución y Riesgo validados (Target 24.0 pt = $480 USD NQ)
				EntryMode					= ConfluenceEntryNQ.BarClose;
				AllowSimultaneousTrades		= false;
				TpPoints					= 24.0;                                        // 24.0 puntos NQ ($480 USD en NQ, $48 en MNQ)
				SlMultiplier				= 1.5;                                         // 1.5x estructural
				SlBufferTicks				= 2;                                           // 2 ticks de holgura (0.50 pt)
				EnableBreakEven				= false;                                       // Desactivado para no asfixiar el retest
				BreakEvenTriggerPts			= 12.0;
				BreakEvenOffsetTicks		= 2;

				// Visualización
				DrawEntryArrow				= true;
				DrawTpSlLines				= true;
				ShowFilteredTraps			= true;
				ShowDashboard				= true;
				PosicionDashboard			= TextPosition.TopRight;

				// Fricciones Reales CME
				ComisionRoundTurnUSD		= 4.50;                                        // $4.50 USD comisión round-turn
				SlippageStopsTicks			= 1;                                           // 1 tick slippage adverso ($5.00 USD)

				// Plots del VWAP y Bandas Gaussianas estilo Cyberpunk/Nasdaq
				AddPlot(new Stroke(Brushes.Cyan, 2), PlotStyle.Line, "VWAP");
				AddPlot(new Stroke(Brushes.SlateBlue, DashStyleHelper.Dash, 1), PlotStyle.Line, "Upper Band 1 (+1σ)");
				AddPlot(new Stroke(Brushes.SlateBlue, DashStyleHelper.Dash, 1), PlotStyle.Line, "Lower Band 1 (-1σ)");
				AddPlot(new Stroke(Brushes.Magenta, DashStyleHelper.Solid, 1), PlotStyle.Line, "Upper Band 2 (+2σ)");
				AddPlot(new Stroke(Brushes.Magenta, DashStyleHelper.Solid, 1), PlotStyle.Line, "Lower Band 2 (-2σ)");
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				try
				{
					_cmeTz = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
				}
				catch
				{
					_cmeTz = null;
				}

				_currentAsk = new Dictionary<long, double>();
				_currentBid = new Dictionary<long, double>();
				_zones = new List<ConfluentZone>();
				_lastSubTickPrice = 0;
				_lastSubTickDir = 0;

				_cumVol = 0.0;
				_cumPv = 0.0;
				_cumP2v = 0.0;
				_lastAnchorDt = DateTime.MinValue;

				_simWins = 0;
				_simLosses = 0;
				_simNetPts = 0.0;
				_simGrossProfit = 0.0;
				_simGrossLoss = 0.0;
				_filteredTrapsCount = 0;
				_confluentTrapsCount = 0;
			}
		}

		private double GetPointValue()
		{
			string inst = Instrument != null ? Instrument.MasterInstrument.Name.ToUpperInvariant() : "";
			if (inst.Contains("MNQ")) return 2.0; // MNQ Micro: $2.00/pt
			return 20.0; // NQ estándar: $20.00/pt
		}

		private DateTime GetAnchorDt(DateTime t, TimeSpan anchor)
		{
			if (t.TimeOfDay >= anchor)
				return t.Date.Add(anchor);
			else
				return t.Date.AddDays(-1).Add(anchor);
		}

		protected override void OnBarUpdate()
		{
			// 1. Procesar ticks de la subserie para armar el Footprint exacto
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

			// 2. Motor VWAP y Detección de Anclaje
			DateTime barDt = Time[0];
			DateTime cmeDt = barDt;
			if (_cmeTz != null)
			{
				if (barDt.Kind == DateTimeKind.Utc)
					cmeDt = TimeZoneInfo.ConvertTimeFromUtc(barDt, _cmeTz);
				else
				{
					DateTime localDt = DateTime.SpecifyKind(barDt, DateTimeKind.Local);
					cmeDt = TimeZoneInfo.ConvertTime(localDt, _cmeTz);
				}
			}

			bool shouldResetVwap = false;
			if (AnchorMode == VWAPAnchorNQConfluence.Chart_Session)
			{
				shouldResetVwap = Bars.IsFirstBarOfSession;
			}
			else
			{
				TimeSpan targetTime;
				switch (AnchorMode)
				{
					case VWAPAnchorNQConfluence.RTH_WallStreet_0830_CT:
						targetTime = new TimeSpan(8, 30, 0);
						break;
					case VWAPAnchorNQConfluence.Session_CME_1700_CT:
						targetTime = new TimeSpan(17, 0, 0);
						break;
					case VWAPAnchorNQConfluence.European_Open_0200_CT:
						targetTime = new TimeSpan(2, 0, 0);
						break;
					case VWAPAnchorNQConfluence.Custom_Time:
					default:
						targetTime = new TimeSpan(CustomAnchorHour, CustomAnchorMinute, 0);
						break;
				}

				DateTime anchorDt = GetAnchorDt(cmeDt, targetTime);
				if (anchorDt != _lastAnchorDt)
				{
					_lastAnchorDt = anchorDt;
					shouldResetVwap = true;
				}
			}

			if (CurrentBar == 0) shouldResetVwap = true;

			double typicalPx = (hi + lo + close) / 3.0;
			double barVol = Volumes[0][0];
			if (barVol <= 0.0) barVol = 1.0;

			if (shouldResetVwap)
			{
				_cumVol = barVol;
				_cumPv = typicalPx * barVol;
				_cumP2v = (typicalPx * typicalPx) * barVol;
			}
			else
			{
				_cumVol += barVol;
				_cumPv += typicalPx * barVol;
				_cumP2v += (typicalPx * typicalPx) * barVol;
			}

			double vwap = _cumPv / _cumVol;
			double variance = Math.Max(0.0, (_cumP2v / _cumVol) - (vwap * vwap));
			double stdDev = Math.Sqrt(variance);

			double upper1 = vwap + (1.0 * stdDev);
			double lower1 = vwap - (1.0 * stdDev);
			double upper2 = vwap + (2.0 * stdDev);
			double lower2 = vwap - (2.0 * stdDev);

			Values[0][0] = vwap;
			Values[1][0] = upper1;
			Values[2][0] = lower1;
			Values[3][0] = upper2;
			Values[4][0] = lower2;

			double numSigmas = stdDev > 0.0001 ? (close - vwap) / stdDev : 0.0;

			// 3. Evaluar Zonas Activas Previas y Simulación SL/TP
			foreach (var z in _zones)
			{
				if (!z.IsActive && z.SimStatus != SimTradeStatus.InTrade)
					continue;

				int barsAgo = b - z.EntryBar;

				// Dibujar flecha en EntryBar + 1
				if (DrawEntryArrow && z.PassedFilter && z.SimStatus != SimTradeStatus.PendingTouch && b >= z.EntryBar + 1)
				{
					int arrowBarsAgo = b - (z.EntryBar + 1);
					if (arrowBarsAgo >= 0 && arrowBarsAgo < BarsArray[0].Count)
					{
						if (z.ArrowY == 0.0)
							z.ArrowY = !z.IsBull ? (Lows[0][arrowBarsAgo] - (3 * TickSize)) : (Highs[0][arrowBarsAgo] + (3 * TickSize));

						if (!z.IsBull)
							Draw.ArrowUp(this, z.Tag + "_entry_arrow", false, arrowBarsAgo, z.ArrowY, Brushes.Cyan);
						else
							Draw.ArrowDown(this, z.Tag + "_entry_arrow", false, arrowBarsAgo, z.ArrowY, Brushes.Magenta);
					}
				}

				// Evaluación de SL / TP si el trade está en curso
				if (z.PassedFilter && z.SimStatus == SimTradeStatus.InTrade && b > z.EntryBar)
				{
					if (!z.IsBull) // LONG
					{
						if (EnableBreakEven && !z.IsBreakEvenTriggered && hi >= z.EntryPrice + BreakEvenTriggerPts)
						{
							z.IsBreakEvenTriggered = true;
							double bePrice = z.EntryPrice + (BreakEvenOffsetTicks * TickSize);
							if (bePrice > z.StopLoss)
							{
								z.StopLoss = bePrice;
								Draw.Text(this, z.Tag + "_be_tag", string.Format("⚡ BE ({0:F2})", z.StopLoss), 0, z.StopLoss - 2 * TickSize, Brushes.Yellow);
							}
						}

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
								Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F2} pt)", gain), 0, z.StopLoss - 3 * TickSize, Brushes.Yellow);
							}
							else
							{
								z.SimStatus = SimTradeStatus.Lost;
								double loss = z.EntryPrice - z.StopLoss;
								z.RealizedPts = -loss;
								_simLosses++;
								_simGrossLoss += loss;
								_simNetPts += z.RealizedPts;
								Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F2} pts)", loss), 0, z.StopLoss - 3 * TickSize, Brushes.IndianRed);
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
							Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts)", TpPoints), 0, z.TakeProfit + 3 * TickSize, Brushes.MediumSpringGreen);

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
						if (EnableBreakEven && !z.IsBreakEvenTriggered && lo <= z.EntryPrice - BreakEvenTriggerPts)
						{
							z.IsBreakEvenTriggered = true;
							double bePrice = z.EntryPrice - (BreakEvenOffsetTicks * TickSize);
							if (bePrice < z.StopLoss)
							{
								z.StopLoss = bePrice;
								Draw.Text(this, z.Tag + "_be_tag", string.Format("⚡ BE ({0:F2})", z.StopLoss), 0, z.StopLoss + 2 * TickSize, Brushes.Yellow);
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
								Draw.Text(this, z.Tag + "_res", string.Format("⚡ BE (+{0:F2} pt)", gain), 0, z.StopLoss + 3 * TickSize, Brushes.Yellow);
							}
							else
							{
								z.SimStatus = SimTradeStatus.Lost;
								double loss = z.StopLoss - z.EntryPrice;
								z.RealizedPts = -loss;
								_simLosses++;
								_simGrossLoss += loss;
								_simNetPts += z.RealizedPts;
								Draw.Text(this, z.Tag + "_res", string.Format("✖ SL (-{0:F2} pts)", loss), 0, z.StopLoss + 3 * TickSize, Brushes.IndianRed);
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
							Draw.Text(this, z.Tag + "_res", string.Format("✔ TP (+{0:F1} pts)", TpPoints), 0, z.TakeProfit - 3 * TickSize, Brushes.MediumSpringGreen);

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

			// 4. Evaluar Finished Auction en extremos
			double askAtLo = _currentAsk.ContainsKey(loTk) ? _currentAsk[loTk] : 0.0;
			double bidAtHi = _currentBid.ContainsKey(hiTk) ? _currentBid[hiTk] : 0.0;
			bool finishedHi = bidAtHi <= FinishedAuctionTol;
			bool finishedLo = askAtLo <= FinishedAuctionTol;

			double wickHiFloor = hi - rng * 0.40;
			double wickLoCeil = lo + rng * 0.40;

			// 5. Detección de Trapped Buyers (Techo -> SHORT)
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
				bool passesFilter = false;
				string filterReason = "";

				if (FilterMode == ConfluenceFilterNQ.None_Unfiltered)
				{
					passesFilter = true;
				}
				else if (FilterMode == ConfluenceFilterNQ.MeanReversion_Extremes)
				{
					passesFilter = (numSigmas >= MinSigmaExtreme);
					filterReason = passesFilter ? string.Format("✔ Sobrecompra ({0:+0.1}σ)", numSigmas) : string.Format("Filtro VWAP ({0:+0.1}σ < +{1:F1}σ)", numSigmas, MinSigmaExtreme);
				}
				else if (FilterMode == ConfluenceFilterNQ.Trend_Continuation)
				{
					passesFilter = (numSigmas <= 0.0 && numSigmas >= -2.2);
					filterReason = passesFilter ? "✔ Tendencia Bajista bajo VWAP" : "Filtro VWAP: Sobre VWAP alcista";
				}
				else if (FilterMode == ConfluenceFilterNQ.Dual_Reversion_And_Trend)
				{
					passesFilter = (numSigmas >= MinSigmaExtreme) || (numSigmas <= -0.5 && numSigmas >= -2.2);
					filterReason = passesFilter ? "✔ Confluencia Dual Aprobada" : "Filtro VWAP: Zona Neutra";
				}

				if (passesFilter) _confluentTrapsCount++;
				else _filteredTrapsCount++;

				double zBottom = buyImbTicks.Min() * TickSize - (TickSize / 2.0);
				double zTop = buyImbTicks.Max() * TickSize + (TickSize / 2.0) + (2 * TickSize);
				string tag = string.Format("BTW_NQ_{0}_TB", b);

				ConfluentZone z = new ConfluentZone
				{
					CreatedBar = b,
					IsBull = true,
					Top = zTop,
					Bottom = zBottom,
					Volume = buyVol,
					Touches = 0,
					IsActive = true,
					Tag = tag,
					PassedFilter = passesFilter,
					FilterNote = filterReason
				};

				if (passesFilter)
				{
					Draw.Rectangle(this, tag, false, 0, zTop, -10, zBottom, Brushes.Transparent, Brushes.Magenta, 45);
					Draw.Text(this, tag + "_lbl", string.Format("▼ SHORT {0:0}c [{1:+0.1}σ]", buyVol, numSigmas), 0, zTop + 3 * TickSize, Brushes.Magenta);

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
						}
					}
				}
				else if (ShowFilteredTraps)
				{
					Draw.Rectangle(this, tag, false, 0, zTop, -6, zBottom, Brushes.Transparent, Brushes.Gray, 15);
					Draw.Text(this, tag + "_lbl", string.Format("✖ FILTRADO ({0:+0.1}σ)", numSigmas), 0, zTop + 3 * TickSize, Brushes.Gray);
				}

				_zones.Add(z);
			}

			// 6. Detección de Trapped Sellers (Suelo -> LONG)
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
				bool passesFilter = false;
				string filterReason = "";

				if (FilterMode == ConfluenceFilterNQ.None_Unfiltered)
				{
					passesFilter = true;
				}
				else if (FilterMode == ConfluenceFilterNQ.MeanReversion_Extremes)
				{
					passesFilter = (numSigmas <= -MinSigmaExtreme);
					filterReason = passesFilter ? string.Format("✔ Sobreventa ({0:+0.1}σ)", numSigmas) : string.Format("Filtro VWAP ({0:+0.1}σ > -{1:F1}σ)", numSigmas, MinSigmaExtreme);
				}
				else if (FilterMode == ConfluenceFilterNQ.Trend_Continuation)
				{
					passesFilter = (numSigmas >= 0.0 && numSigmas <= 2.2);
					filterReason = passesFilter ? "✔ Tendencia Alcista sobre VWAP" : "Filtro VWAP: Bajo VWAP bajista";
				}
				else if (FilterMode == ConfluenceFilterNQ.Dual_Reversion_And_Trend)
				{
					passesFilter = (numSigmas <= -MinSigmaExtreme) || (numSigmas >= 0.5 && numSigmas <= 2.2);
					filterReason = passesFilter ? "✔ Confluencia Dual Aprobada" : "Filtro VWAP: Zona Neutra";
				}

				if (passesFilter) _confluentTrapsCount++;
				else _filteredTrapsCount++;

				double zTop = sellImbTicks.Max() * TickSize + (TickSize / 2.0);
				double zBottom = sellImbTicks.Min() * TickSize - (TickSize / 2.0) - (2 * TickSize);
				string tag = string.Format("BTW_NQ_{0}_TS", b);

				ConfluentZone z = new ConfluentZone
				{
					CreatedBar = b,
					IsBull = false,
					Top = zTop,
					Bottom = zBottom,
					Volume = sellVol,
					Touches = 0,
					IsActive = true,
					Tag = tag,
					PassedFilter = passesFilter,
					FilterNote = filterReason
				};

				if (passesFilter)
				{
					Draw.Rectangle(this, tag, false, 0, zTop, -10, zBottom, Brushes.Transparent, Brushes.Cyan, 45);
					Draw.Text(this, tag + "_lbl", string.Format("▲ LONG {0:0}c [{1:+0.1}σ]", sellVol, numSigmas), 0, zBottom - 3 * TickSize, Brushes.Cyan);

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
							Draw.Line(this, z.Tag + "_ent", false, 0, z.EntryPrice, -15, z.EntryPrice, Brushes.Cyan, DashStyleHelper.Solid, 2);
							Draw.Line(this, z.Tag + "_tp", false, 0, z.TakeProfit, -25, z.TakeProfit, Brushes.MediumSpringGreen, DashStyleHelper.Dash, 2);
							Draw.Line(this, z.Tag + "_sl", false, 0, z.StopLoss, -25, z.StopLoss, Brushes.IndianRed, DashStyleHelper.Dash, 2);
						}
					}
				}
				else if (ShowFilteredTraps)
				{
					Draw.Rectangle(this, tag, false, 0, zTop, -6, zBottom, Brushes.Transparent, Brushes.Gray, 15);
					Draw.Text(this, tag + "_lbl", string.Format("✖ FILTRADO ({0:+0.1}σ)", numSigmas), 0, zBottom - 3 * TickSize, Brushes.Gray);
				}

				_zones.Add(z);
			}

			// 7. Renderizar HUD Dashboard de Confluencia
			if (ShowDashboard)
			{
				double ptVal = GetPointValue();
				int totalTrades = _simWins + _simLosses;
				double wr = totalTrades > 0 ? ((double)_simWins / totalTrades) * 100.0 : 0.0;
				double grossUsd = _simNetPts * ptVal;
				double pfGross = _simGrossLoss > 0.001 ? (_simGrossProfit / _simGrossLoss) : (_simGrossProfit > 0 ? 99.9 : 0.0);

				double totalCommissions = totalTrades * ComisionRoundTurnUSD;
				double totalSlippage = _simLosses * (SlippageStopsTicks * TickSize * ptVal);
				double netRealUsd = grossUsd - totalCommissions - totalSlippage;
				double netRealPts = netRealUsd / ptVal;
				double totalGrossGain = (_simGrossProfit * ptVal) - (_simWins * ComisionRoundTurnUSD);
				double totalGrossLossFriction = (_simGrossLoss * ptVal) + (_simLosses * ComisionRoundTurnUSD) + totalSlippage;
				double pfNet = totalGrossLossFriction > 0.001 ? (Math.Max(0.0, totalGrossGain) / totalGrossLossFriction) : 0.0;

				int totalTrapsDetected = _confluentTrapsCount + _filteredTrapsCount;
				double filteredPct = totalTrapsDetected > 0 ? ((double)_filteredTrapsCount / totalTrapsDetected) * 100.0 : 0.0;

				var activeTrade = _zones.LastOrDefault(x => x.SimStatus == SimTradeStatus.InTrade);
				string statusStr = activeTrade != null ?
					string.Format("● IN TRADE: {0} @ {1:F2}\n  SL: {2:F2} | TP: {3:F2}", !activeTrade.IsBull ? "LONG" : "SHORT", activeTrade.EntryPrice, activeTrade.StopLoss, activeTrade.TakeProfit) :
					"○ FLAT (Esperando confluencia)";

				string filterModeStr = FilterMode == ConfluenceFilterNQ.Dual_Reversion_And_Trend ? "Dual (Extremos + Tend)" :
									   (FilterMode == ConfluenceFilterNQ.MeanReversion_Extremes ? string.Format("Extremos (±{0:F1}σ)", MinSigmaExtreme) :
									   (FilterMode == ConfluenceFilterNQ.Trend_Continuation ? "Continuación Tendencia" : "Sin Filtro"));

				string dashText = string.Format(
					"=== BIGTRAP + VWAP (NASDAQ NQ) ===\n" +
					"Filtro Activo : {0}\n" +
					"Confluentes   : {1} | Filtradas: {2} ({3:F0}% descartado)\n" +
					"Total Trades  : {4} (W: {5} | L: {6})\n" +
					"Win Rate      : {7:F1}%\n" +
					"----------------------------------\n" +
					"PnL BRUTO     : {8:+0.00;-0.00} pts (${9:+0,0;-0,0;0} USD) [PF: {10:F2}]\n" +
					"PnL NETO CME  : {11:+0.00;-0.00} pts (${12:+0,0;-0,0;0} USD) [PF: {13:F2}]\n" +
					"----------------------------------\n" +
					"VWAP (08:30CT): {14:F2} ({15:+0.0;-0.0}σ | {16:+0.00;-0.00} pts)\n" +
					"Estado:\n{17}",
					filterModeStr,
					_confluentTrapsCount,
					_filteredTrapsCount,
					filteredPct,
					totalTrades,
					_simWins,
					_simLosses,
					wr,
					_simNetPts,
					grossUsd,
					pfGross,
					netRealPts,
					netRealUsd,
					pfNet,
					vwap,
					numSigmas,
					close - vwap,
					statusStr
				);

				Draw.TextFixed(this, "BT_VWAP_NQ_DASH", dashText, PosicionDashboard,
					Brushes.White, new NinjaTrader.Gui.Tools.SimpleFont("Consolas", 10),
					Brushes.Cyan, Brushes.Black, 85);
			}

			_currentAsk.Clear();
			_currentBid.Clear();
		}
	}
}
