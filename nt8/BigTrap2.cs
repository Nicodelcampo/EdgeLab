// BigTrap2.cs — v2 de "BigTrap" (port del "BIG TRAP" de TradingView) para NinjaTrader 8.
//
// ─── NOTA DE DISEÑO (contrato — leer antes de tocar o traducir) ───────────────
// 1. non_repainting: Calculate = OnBarClose. available_at = cierre de la barra
//    creadora. La barra creadora nunca toca ni invalida sus propias zonas.
// 2. UN SOLO MOTOR: el footprint se reconstruye SIEMPRE desde la subserie de
//    1 tick (AddDataSeries Tick/1), aunque el chart use barras Volumetric.
//    El dual-path de la v1 (API nativa o tick rule según el chart) eran dos
//    indicadores distintos bajo el mismo nombre → paridad indefinible.
// 3. Clasificación buy/sell jerárquica declarada:
//      trade >= ask → buy ; trade <= bid → sell   (quote-based, criterio Volumetric)
//      dentro del spread o sin quotes → tick rule  (fallback contado)
//    n_quote / n_rule se exportan por barra. Si n_rule domina, el feed no tiene
//    bid/ask por tick y el delta/imbalance NO es confiable para research.
//    Primer tick sin información: se asigna a buy (declarado; cae en n_rule).
// 4. Precios como índices enteros de tick (long). Nunca claves double crudas ni
//    loops += TickSize. Filas de TicksPerRow ancladas a la grilla ABSOLUTA de
//    precios (fila = floor(tick / TicksPerRow)), no al low de cada barra.
// 5. Imbalance declarado: Diagonal (estándar footprint: ask[fila] vs bid[fila−1];
//    bid[fila] vs ask[fila+1]) o SameLevel (fiel al original, para A/B).
//    Denominador cero: ratio = agresor / max(opuesto, 1). Volumen del trap:
//    AggressiveSide (default) o TotalLevel (comportamiento v1).
// 6. Trap = filas con imbalance agresor del lado perdedor del close (buy
//    imbalance por ENCIMA del close = compradores atrapados; espejo para
//    vendedores), opcional restringido a la zona de mecha (WickZonePct).
// 7. Export continuo: evento TRAP por barra/lado desde MinExportVolume (piso
//    bajo). MinTrapVolume es SOLO el corte de burbuja+zona on-chart; los
//    umbrales reales se barren offline en vectorbt sobre los eventos TRAP.
// 8. Zonas con ciclo de vida: [borde inferior, borde superior] de las filas
//    calificadas. CloseThrough: trapped_buyers se invalida con close > techo
//    (los compradores dejaron de estar atrapados); espejo para sellers.
//    Identidad analítica: (created_bar, side, geometría en ticks).
// 9. Auditoría: FOOTPRINT_MISMATCH si |suma(footprint) − Volume[0]| > 0.5
//    (omitida en la barra 0, que puede arrancar parcial). Caveat declarado:
//    ticks con timestamp == cierre de la barra primaria pueden fugarse a la
//    barra siguiente; el footprint definitivo lo arbitra EdgeLab con [inicio,fin).
// 10. TopPercentFilter / AutoScale / OutlierPercentile son 100% VISUALES y
//     tienen look-ahead por definición (percentiles sobre lo acumulado en el
//     renderer). JAMÁS usarlos como selección analítica. Burbujas con lock +
//     snapshot (OnBarUpdate y OnRender corren en hilos distintos).
// Requiere tick data histórico descargado (no Tick Replay). Congelar la v1
// como BigTrap_legacy_v1 con hash antes de reemplazarla.

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
#endregion

public enum BT2ImbalanceMode    { Diagonal, SameLevel }
public enum BT2TrapVolumeSource { AggressiveSide, TotalLevel }
public enum BT2InvalidationMode { None, FirstTouch, CloseThrough }
public enum BT2VisualMode       { SizeScaling, TransparencyScaling }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrap2 : Indicator
	{
		// ── tipos internos ────────────────────────────────────────────────
		private struct BT2Bubble
		{
			public int    BarIndex;
			public double Price;
			public double Volume;
			public bool   IsBull;
		}

		private sealed class BT2Zone
		{
			public int    CreatedBar;
			public bool   IsBull;      // true = trapped buyers (zona arriba del close creador)
			public long   LoTick;
			public long   HiTick;
			public double Volume;
			public int    Touches;
		}

		// ── footprint pendiente (subserie de 1 tick) ──────────────────────
		private Dictionary<long, double> pendingAsk = new Dictionary<long, double>(64);
		private Dictionary<long, double> pendingBid = new Dictionary<long, double>(64);
		private double pendingVolume;
		private int    pendingQuoteTicks;
		private int    pendingRuleTicks;
		private double lastTickPrice = double.NaN;
		private int    lastTickDir;   // +1 buy, -1 sell, 0 sin información aún

		// ── estado analítico ──────────────────────────────────────────────
		private readonly object          bubbleLock  = new object();
		private readonly List<BT2Bubble> bubbles     = new List<BT2Bubble>(512);
		private readonly List<BT2Zone>   activeZones = new List<BT2Zone>();

		// ── export ────────────────────────────────────────────────────────
		private StreamWriter eventWriter;
		private bool         eventWriterFailed;
		private long         eventSeq;

		// ── visual (cachés del renderer, sin valor analítico) ─────────────
		private SharpDX.Color dxBull, dxBear;
		private int    lastBubbleCount = -1;
		private double cachedThreshold;
		private double cachedMaxVol = 1000;

		// ──────────────────────────────────────────────────────────────────
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name        = "BigTrap2";
				Description = "Trapped traders v2: footprint reconstruido desde subserie de 1 tick, export de eventos continuos y zonas con ciclo de vida.";
				Calculate   = Calculate.OnBarClose;
				IsOverlay   = true;
				DisplayInDataBox         = false;
				PaintPriceMarkers        = false;
				IsSuspendedWhileInactive = false;   // el estado no puede depender de si el chart estuvo visible

				// ── 1. Semántica (entran en run_id) ──
				TicksPerRow      = 1;
				ImbalanceMode    = BT2ImbalanceMode.Diagonal;
				TrapVolumeSource = BT2TrapVolumeSource.AggressiveSide;
				UseWickFilter    = true;
				WickZonePct      = 30.0;

				// ── 2. Selección (barrible offline sobre los eventos TRAP) ──
				ImbalanceRatio  = 3.0;
				MinDeltaFilter  = 0;
				MinTrapVolume   = 30;
				MinExportVolume = 1;

				// ── 3. Ciclo de vida ──
				InvalidationMode = BT2InvalidationMode.CloseThrough;
				MaxTouches       = 0;      // 0 = sin límite
				MaxAgeBars       = 2000;   // 0 = sin expiración

				// ── 4. Export ──
				EventLogPath = "";

				// ── 5. Visual (JAMÁS en run_id ni en optimización) ──
				ShowPOC           = false;
				VisualMode        = BT2VisualMode.SizeScaling;
				AutoScale         = true;
				OutlierPercentile = 90.0;
				TopPercentFilter  = 100.0;  // v1 default 15 ocultaba el 85% de las detecciones
				ManualMaxVol      = 1000;
				FixedTransparency = 40;
				FixedBubbleRadius = 8;
				TranspStart       = 80;
				TranspEnd         = 10;
				MaxBubblesStored  = 2000;
				BullColor         = System.Windows.Media.Brushes.Teal;
				BearColor         = System.Windows.Media.Brushes.Red;

				AddPlot(new Stroke(System.Windows.Media.Brushes.Gold, 2), PlotStyle.Dot, "POC");
			}
			else if (State == State.Configure)
			{
				// Motor único: SIEMPRE la subserie de 1 tick, sea cual sea la serie primaria.
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				dxBull = ToDx(BullColor);
				dxBear = ToDx(BearColor);
			}
			else if (State == State.Terminated)
			{
				if (eventWriter != null)
				{
					try { eventWriter.Flush(); eventWriter.Dispose(); } catch { }
					eventWriter = null;
				}
			}
		}

		// ──────────────────────────────────────────────────────────────────
		protected override void OnBarUpdate()
		{
			if (BarsInProgress == 1)
			{
				AccumulateTick();
				return;
			}
			if (BarsInProgress != 0)
				return;

			// Take + reset SIEMPRE (también en warm-up): sin fuga entre barras.
			Dictionary<long, double> askMap = pendingAsk;
			Dictionary<long, double> bidMap = pendingBid;
			double fpVol  = pendingVolume;
			int    nQuote = pendingQuoteTicks;
			int    nRule  = pendingRuleTicks;
			pendingAsk        = new Dictionary<long, double>(64);
			pendingBid        = new Dictionary<long, double>(64);
			pendingVolume     = 0;
			pendingQuoteTicks = 0;
			pendingRuleTicks  = 0;

			Values[0][0] = double.NaN;

			if (CurrentBars.Length < 2 || CurrentBars[1] < 0)
			{
				LogEvent("ERROR", "subserie de 1 tick sin datos; descargar tick data historico. Cero detecciones, nunca fallback.");
				return;
			}
			if (CurrentBar == 0)
				return; // primera barra primaria: footprint potencialmente parcial, se descarta

			if (Math.Abs(fpVol - Volume[0]) > 0.5)
				LogEvent("FOOTPRINT_MISMATCH", string.Format(CultureInfo.InvariantCulture,
					"bar={0};fp_vol={1};bar_vol={2};n_quote={3};n_rule={4}",
					CurrentBar, fpVol, Volume[0], nQuote, nRule));

			// Lifecycle primero: la barra recién cerrada evalúa zonas de barras ANTERIORES,
			// así la barra creadora nunca toca su propia zona.
			UpdateZones();

			if (askMap.Count == 0 && bidMap.Count == 0)
				return;

			ProcessBar(askMap, bidMap, fpVol, nQuote, nRule);
		}

		// ── acumulación por tick ──────────────────────────────────────────
		private void AccumulateTick()
		{
			double price = Closes[1][0];
			double vol   = Volumes[1][0];
			int    idx   = CurrentBars[1];

			double askQ = BarsArray[1].GetAsk(idx);
			double bidQ = BarsArray[1].GetBid(idx);

			int  side    = 0;
			bool byQuote = false;
			if (askQ > 0 && bidQ > 0 && askQ >= bidQ)
			{
				if      (price >= askQ) { side =  1; byQuote = true; }
				else if (price <= bidQ) { side = -1; byQuote = true; }
			}
			if (side == 0) // dentro del spread o sin quotes → tick rule (fallback declarado)
			{
				if (!double.IsNaN(lastTickPrice))
				{
					if      (price > lastTickPrice) side =  1;
					else if (price < lastTickPrice) side = -1;
					else                            side = lastTickDir;
				}
				if (side == 0) side = 1; // primer tick sin información (declarado en contrato)
			}
			lastTickPrice = price;
			lastTickDir   = side;
			if (byQuote) pendingQuoteTicks++; else pendingRuleTicks++;

			long tick = (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
			Dictionary<long, double> map = side > 0 ? pendingAsk : pendingBid;
			double cur;
			map[tick] = map.TryGetValue(tick, out cur) ? cur + vol : vol;
			pendingVolume += vol;
		}

		// ── kernel de detección ───────────────────────────────────────────
		private void ProcessBar(Dictionary<long, double> askMap, Dictionary<long, double> bidMap,
		                        double fpVol, int nQuote, int nRule)
		{
			int rowTicks = Math.Max(1, TicksPerRow);

			// Filas ancladas a la grilla absoluta de precios (declarado en contrato).
			var rowAsk = new Dictionary<long, double>();
			var rowBid = new Dictionary<long, double>();
			foreach (var kv in askMap)
			{
				long r; double c;
				r = FloorDiv(kv.Key, rowTicks);
				rowAsk[r] = rowAsk.TryGetValue(r, out c) ? c + kv.Value : kv.Value;
			}
			foreach (var kv in bidMap)
			{
				long r; double c;
				r = FloorDiv(kv.Key, rowTicks);
				rowBid[r] = rowBid.TryGetValue(r, out c) ? c + kv.Value : kv.Value;
			}

			var rowKeys = new SortedSet<long>(rowAsk.Keys);
			foreach (long k in rowBid.Keys) rowKeys.Add(k);
			if (rowKeys.Count == 0) return;

			double close = Close[0];
			// Indice entero del close en MEDIOS ticks, calculado UNA vez por barra.
			// Toda comparacion fila-vs-close se hace sobre ENTEROS: comparar el precio
			// RECONSTRUIDO (row*TickSize) contra el precio del FEED (Close[0]) en double
			// difiere en 1 ULP, y eso hacia que el empate (fila == close) entrara como
			// trapped_buyers -> 101 falsos positivos en la ventana de paridad del
			// 2026-07-24 (12,5% de las zonas). Ver docs/parity_coverage/BigTrap2.md.
			// Se usa MEDIO tick porque con rowTicks PAR el centro de fila cae en x.5
			// ticks; en medios ticks el centro de fila siempre es un entero exacto.
			// MidpointRounding.AwayFromZero, NUNCA floor/truncate/cast directo:
			// close/TickSize puede dar 22816.999999... y un floor crearia un off-by-one
			// nuevo. Misma familia de bug que el banker's rounding que ya aparecio en la
			// geometria del matcher: las comparaciones de precio van en enteros de tick,
			// los double solo para I/O.
			long closeHalfTick = 2 * (long)Math.Round(close / TickSize, MidpointRounding.AwayFromZero);
			double lo    = Low[0];
			double hi    = High[0];
			double range = hi - lo;
			double wickHiFloor = hi - range * (WickZonePct / 100.0);
			double wickLoCeil  = lo + range * (WickZonePct / 100.0);

			long   pocRow = long.MinValue;
			double pocVol = -1;

			double buyVol = 0, buyWSum = 0, buyMaxRatio = 0;
			long   buyLo  = long.MaxValue, buyHi = long.MinValue;
			int    buyRows = 0;

			double sellVol = 0, sellWSum = 0, sellMaxRatio = 0;
			long   sellLo  = long.MaxValue, sellHi = long.MinValue;
			int    sellRows = 0;

			foreach (long r in rowKeys)
			{
				double a, b;
				rowAsk.TryGetValue(r, out a);
				rowBid.TryGetValue(r, out b);
				double total = a + b;

				// POC: en empate gana la fila más baja (SortedSet asc + estrictamente mayor).
				if (total > pocVol) { pocVol = total; pocRow = r; }

				if (Math.Abs(a - b) < MinDeltaFilter)
					continue;

				double buyRatio, sellRatio;
				if (ImbalanceMode == BT2ImbalanceMode.Diagonal)
				{
					double bDn, aUp;
					rowBid.TryGetValue(r - 1, out bDn);
					rowAsk.TryGetValue(r + 1, out aUp);
					buyRatio  = a / Math.Max(bDn, 1.0);
					sellRatio = b / Math.Max(aUp, 1.0);
				}
				else
				{
					buyRatio  = a / Math.Max(b, 1.0);
					sellRatio = b / Math.Max(a, 1.0);
				}

				double rowPrice = RowCenterPrice(r, rowTicks);
				long   rowHalfTick = RowCenterHalfTick(r, rowTicks);

				double contribBuy  = TrapVolumeSource == BT2TrapVolumeSource.AggressiveSide ? a : total;
				double contribSell = TrapVolumeSource == BT2TrapVolumeSource.AggressiveSide ? b : total;

				// Trapped buyers: agresión compradora que quedó por ENCIMA del close.
				if (a >= 1 && buyRatio >= ImbalanceRatio && rowHalfTick > closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice >= wickHiFloor)))
				{
					buyVol  += contribBuy;
					buyWSum += rowPrice * contribBuy;
					buyRows++;
					if (r < buyLo) buyLo = r;
					if (r > buyHi) buyHi = r;
					if (buyRatio > buyMaxRatio) buyMaxRatio = buyRatio;
				}

				// Trapped sellers: agresión vendedora que quedó por DEBAJO del close.
				if (b >= 1 && sellRatio >= ImbalanceRatio && rowHalfTick < closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice <= wickLoCeil)))
				{
					sellVol  += contribSell;
					sellWSum += rowPrice * contribSell;
					sellRows++;
					if (r < sellLo) sellLo = r;
					if (r > sellHi) sellHi = r;
					if (sellRatio > sellMaxRatio) sellMaxRatio = sellRatio;
				}
			}

			if (ShowPOC && pocVol > 0)
				Values[0][0] = RowCenterPrice(pocRow, rowTicks); // precio real, sin offset

			EmitSide(true,  buyVol,  buyWSum,  buyLo,  buyHi,  buyRows,  buyMaxRatio,  fpVol, nQuote, nRule, rowTicks);
			EmitSide(false, sellVol, sellWSum, sellLo, sellHi, sellRows, sellMaxRatio, fpVol, nQuote, nRule, rowTicks);
		}

		private void EmitSide(bool isBull, double vol, double wSum, long loRow, long hiRow, int nRows,
		                      double maxRatio, double fpVol, int nQuote, int nRule, int rowTicks)
		{
			if (nRows == 0 || vol <= 0 || vol < MinExportVolume)
				return;

			double centroid = wSum / vol;
			long   loTick   = loRow * rowTicks;
			long   hiTick   = (hiRow + 1) * rowTicks - 1;
			double zoneLo   = loTick * TickSize - TickSize / 2.0;
			double zoneHi   = hiTick * TickSize + TickSize / 2.0;

			// Export continuo: los umbrales de selección se barren offline sobre estos eventos.
			LogEvent("TRAP", string.Format(CultureInfo.InvariantCulture,
				"bar={0};side={1};vol={2};centroid={3};zone_lo={4};zone_hi={5};n_rows={6};max_ratio={7};close={8};bar_vol={9};fp_vol={10};n_quote={11};n_rule={12}",
				CurrentBar, isBull ? "trapped_buyers" : "trapped_sellers",
				vol, centroid, zoneLo, zoneHi, nRows, maxRatio, Close[0], Volume[0], fpVol, nQuote, nRule));

			if (vol < MinTrapVolume)
				return; // el evento TRAP ya quedó exportado; esto solo corta burbuja + zona

			lock (bubbleLock)
			{
				bubbles.Add(new BT2Bubble { BarIndex = CurrentBar, Price = centroid, Volume = vol, IsBull = isBull });
				int excess = bubbles.Count - Math.Max(100, MaxBubblesStored);
				if (excess > 0) bubbles.RemoveRange(0, excess);
			}

			var z = new BT2Zone { CreatedBar = CurrentBar, IsBull = isBull, LoTick = loTick, HiTick = hiTick, Volume = vol };
			activeZones.Add(z);
			LogEvent("ZONE_CREATED", ZoneDesc(z));
		}

		// ── ciclo de vida de zonas ────────────────────────────────────────
		private void UpdateZones()
		{
			if (activeZones.Count == 0) return;

			double hi = High[0], lo = Low[0], close = Close[0];

			for (int i = activeZones.Count - 1; i >= 0; i--)
			{
				BT2Zone z = activeZones[i];

				if (MaxAgeBars > 0 && CurrentBar - z.CreatedBar > MaxAgeBars)
				{
					LogEvent("ZONE_EXPIRED", ZoneDesc(z) + ";bar=" + CurrentBar);
					activeZones.RemoveAt(i);
					continue;
				}

				double zLo = ZoneLoPrice(z), zHi = ZoneHiPrice(z);
				bool touched      = hi >= zLo && lo <= zHi;
				bool adverseClose = z.IsBull ? close > zHi : close < zLo; // los atrapados dejaron de estarlo

				if (touched)
				{
					z.Touches++;
					LogEvent("ZONE_TOUCHED", ZoneDesc(z) + string.Format(CultureInfo.InvariantCulture,
						";bar={0};touches={1}", CurrentBar, z.Touches));
				}

				string reason = null;
				if      (InvalidationMode == BT2InvalidationMode.FirstTouch && touched)      reason = "first_touch";
				else if (InvalidationMode == BT2InvalidationMode.CloseThrough && adverseClose) reason = touched ? "close_through" : "close_through_gap";
				else if (MaxTouches > 0 && z.Touches >= MaxTouches)                          reason = "max_touches";

				if (reason != null)
				{
					LogEvent("ZONE_INVALIDATED", ZoneDesc(z) + ";reason=" + reason + ";bar=" + CurrentBar);
					activeZones.RemoveAt(i);
				}
			}
		}

		// ── helpers ───────────────────────────────────────────────────────
		private static long FloorDiv(long a, long b)
		{
			long q = a / b;
			if ((a % b != 0) && ((a < 0) != (b < 0))) q--;
			return q;
		}

		// Centro de fila en MEDIOS ticks: entero EXACTO para todo rowTicks.
		// 2*(row*rowTicks + (rowTicks-1)/2) = 2*row*rowTicks + (rowTicks-1).
		private long RowCenterHalfTick(long row, int rowTicks)
		{
			return 2 * row * rowTicks + (rowTicks - 1);
		}
		
		private double RowCenterPrice(long row, int rowTicks)
		{
			return (row * rowTicks + (rowTicks - 1) / 2.0) * TickSize;
		}

		private double ZoneLoPrice(BT2Zone z) { return z.LoTick * TickSize - TickSize / 2.0; }
		private double ZoneHiPrice(BT2Zone z) { return z.HiTick * TickSize + TickSize / 2.0; }

		private string ZoneDesc(BT2Zone z)
		{
			return string.Format(CultureInfo.InvariantCulture,
				"zone_id={0}_{1};created_bar={0};side={2};lo={3};hi={4};vol={5}",
				z.CreatedBar, z.IsBull ? "B" : "S",
				z.IsBull ? "trapped_buyers" : "trapped_sellers",
				ZoneLoPrice(z), ZoneHiPrice(z), z.Volume);
		}

		private void LogEvent(string type, string payload)
		{
			if (string.IsNullOrEmpty(EventLogPath) || eventWriterFailed)
				return;
			try
			{
				if (eventWriter == null)
				{
					bool exists = File.Exists(EventLogPath);
					eventWriter = new StreamWriter(EventLogPath, true) { AutoFlush = true };
					if (!exists)
						eventWriter.WriteLine("# meta indicator=BigTrap2,version=2.1"
							+ ",footprint=reconstructed_1tick_subseries,classifier=bidask_then_tickrule"
							+ ",row_anchor=absolute_grid,ratio_floor=max(opposite,1),poc_tiebreak=lowest_row"
							+ ",close_cmp=integer_half_ticks,tie_excluded_both_sides"
							+ ",imbalance_mode=" + ImbalanceMode
							+ ",trap_volume=" + TrapVolumeSource
							+ ",ticks_per_row=" + TicksPerRow
							+ ",imbalance_ratio=" + ImbalanceRatio.ToString(CultureInfo.InvariantCulture)
							+ ",wick_filter=" + UseWickFilter
							+ ",wick_zone_pct=" + WickZonePct.ToString(CultureInfo.InvariantCulture)
							+ ",min_delta=" + MinDeltaFilter
							+ ",invalidation=" + InvalidationMode
							+ ",max_age_bars=" + MaxAgeBars
							+ ",max_touches=" + MaxTouches
							+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
							+ ",instrument=" + Instrument.FullName);
				}
				eventWriter.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0}|{1:o}|{2}|{3}", eventSeq++, Time[0], type, payload));
			}
			catch (Exception ex)
			{
				eventWriterFailed = true;
				Print("BigTrap2: fallo escribiendo eventos: " + ex.Message);
			}
		}

		private static SharpDX.Color ToDx(System.Windows.Media.Brush wpfBrush)
		{
			var scb = wpfBrush as System.Windows.Media.SolidColorBrush;
			if (scb != null)
				return new SharpDX.Color(scb.Color.R, scb.Color.G, scb.Color.B, scb.Color.A);
			return SharpDX.Color.White;
		}

		// ── salida analítica de solo lectura ──────────────────────────────
		[Browsable(false)] [XmlIgnore]
		public int ActiveZoneCount { get { return activeZones.Count; } }

		// ── renderer (100% visual; sus filtros tienen look-ahead declarado) ─
		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (chartControl == null || ChartBars == null || RenderTarget == null)
				return;

			BT2Bubble[] snap;
			lock (bubbleLock) { snap = bubbles.ToArray(); }
			if (snap.Length == 0) return;

			if (snap.Length != lastBubbleCount)
			{
				lastBubbleCount = snap.Length;
				double[] vols = snap.Select(b => b.Volume).OrderBy(v => v).ToArray();

				if (TopPercentFilter < 100.0 && vols.Length > 1)
				{
					int keep = Math.Max(1, (int)Math.Ceiling(vols.Length * TopPercentFilter / 100.0));
					cachedThreshold = vols[vols.Length - keep];
				}
				else cachedThreshold = 0;

				if (AutoScale)
				{
					int idx = Math.Min(vols.Length - 1, (int)Math.Floor(vols.Length * OutlierPercentile / 100.0));
					cachedMaxVol = Math.Max(vols[idx], MinTrapVolume + 1);
				}
				else cachedMaxVol = ManualMaxVol;
			}

			int   firstBar = ChartBars.FromIndex, lastBar = ChartBars.ToIndex;
			float minR = 3f, maxR = 22f;

			var oldAA = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.PerPrimitive;
			try
			{
				foreach (BT2Bubble b in snap)
				{
					if (b.BarIndex < firstBar || b.BarIndex > lastBar) continue;
					if (b.Volume < cachedThreshold) continue;

					float  x = chartControl.GetXByBarIndex(ChartBars, b.BarIndex);
					float  y = chartScale.GetYByValue(b.Price);
					double strength = Math.Max(0.0, Math.Min(1.0,
						(b.Volume - MinTrapVolume) / Math.Max(1.0, cachedMaxVol - MinTrapVolume)));

					float radius; byte alpha;
					if (VisualMode == BT2VisualMode.SizeScaling)
					{
						radius = minR + (float)(strength * (maxR - minR));
						alpha  = (byte)(255 * (1.0 - Math.Max(0, Math.Min(100, FixedTransparency)) / 100.0));
					}
					else
					{
						radius = FixedBubbleRadius;
						double tr = TranspStart - strength * (TranspStart - TranspEnd);
						alpha = (byte)(255 * (1.0 - Math.Max(0.0, Math.Min(100.0, tr)) / 100.0));
					}

					SharpDX.Color baseC = b.IsBull ? dxBull : dxBear;
					var color = new SharpDX.Color(baseC.R, baseC.G, baseC.B, alpha);
					using (var brush = new SharpDX.Direct2D1.SolidColorBrush(RenderTarget, color))
						RenderTarget.FillEllipse(
							new SharpDX.Direct2D1.Ellipse(new SharpDX.Vector2(x, y), radius, radius), brush);
				}
			}
			finally
			{
				RenderTarget.AntialiasMode = oldAA;
			}
		}

		#region Properties

		// ── 1. Semántica ──
		[NinjaScriptProperty] [Range(1, 50)]
		[Display(Name = "Ticks per Row", Order = 1, GroupName = "1. Semántica",
			Description = "Agrupa N ticks por fila, anclado a la grilla absoluta de precios.")]
		public int TicksPerRow { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Imbalance Mode", Order = 2, GroupName = "1. Semántica",
			Description = "Diagonal = estándar footprint (ask vs bid de la fila inferior). SameLevel = fiel al original.")]
		public BT2ImbalanceMode ImbalanceMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Trap Volume Source", Order = 3, GroupName = "1. Semántica",
			Description = "AggressiveSide = solo volumen agresor. TotalLevel = ask+bid (comportamiento v1).")]
		public BT2TrapVolumeSource TrapVolumeSource { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Use Wick Filter", Order = 4, GroupName = "1. Semántica",
			Description = "Restringir traps a la zona de mecha (antes StrictMode con 30% hardcodeado).")]
		public bool UseWickFilter { get; set; }

		[NinjaScriptProperty] [Range(5.0, 100.0)]
		[Display(Name = "Wick Zone %", Order = 5, GroupName = "1. Semántica",
			Description = "Porcentaje superior/inferior del rango de la vela considerado zona de mecha.")]
		public double WickZonePct { get; set; }

		// ── 2. Selección ──
		[NinjaScriptProperty] [Range(1.0, 100.0)]
		[Display(Name = "Imbalance Ratio", Order = 1, GroupName = "2. Selección")]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty] [Range(0, 10000)]
		[Display(Name = "Min Delta Filter (Per Row)", Order = 2, GroupName = "2. Selección")]
		public int MinDeltaFilter { get; set; }

		[NinjaScriptProperty] [Range(1, 100000)]
		[Display(Name = "Min Trap Volume (burbuja+zona)", Order = 3, GroupName = "2. Selección",
			Description = "Corte on-chart. Los eventos TRAP se exportan desde MinExportVolume igual.")]
		public int MinTrapVolume { get; set; }

		[NinjaScriptProperty] [Range(0, 100000)]
		[Display(Name = "Min Export Volume", Order = 4, GroupName = "2. Selección",
			Description = "Piso bajo del export continuo; los umbrales reales se barren offline.")]
		public int MinExportVolume { get; set; }

		// ── 3. Ciclo de vida ──
		[NinjaScriptProperty]
		[Display(Name = "Invalidation Mode", Order = 1, GroupName = "3. Ciclo de vida")]
		public BT2InvalidationMode InvalidationMode { get; set; }

		[NinjaScriptProperty] [Range(0, 1000)]
		[Display(Name = "Max Touches (0 = sin límite)", Order = 2, GroupName = "3. Ciclo de vida")]
		public int MaxTouches { get; set; }

		[NinjaScriptProperty] [Range(0, 50000)]
		[Display(Name = "Max Age Bars (0 = sin expiración)", Order = 3, GroupName = "3. Ciclo de vida")]
		public int MaxAgeBars { get; set; }

		// ── 4. Export ──
		[NinjaScriptProperty]
		[Display(Name = "Event Log Path (vacío = off)", Order = 1, GroupName = "4. Export")]
		public string EventLogPath { get; set; }

		// ── 5. Visual ──
		[NinjaScriptProperty]
		[Display(Name = "Show POC Dots", Order = 1, GroupName = "5. Visual")]
		public bool ShowPOC { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Visual Mode", Order = 2, GroupName = "5. Visual")]
		public BT2VisualMode VisualMode { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Auto-Scale", Order = 3, GroupName = "5. Visual")]
		public bool AutoScale { get; set; }

		[NinjaScriptProperty] [Range(50.0, 100.0)]
		[Display(Name = "Outlier Percentile Cap", Order = 4, GroupName = "5. Visual")]
		public double OutlierPercentile { get; set; }

		[NinjaScriptProperty] [Range(1.0, 100.0)]
		[Display(Name = "Show Top % (SOLO visual, con look-ahead)", Order = 5, GroupName = "5. Visual",
			Description = "Percentil sobre todo lo acumulado: cambia retroactivamente. Jamás usar como selección analítica.")]
		public double TopPercentFilter { get; set; }

		[NinjaScriptProperty] [Range(1, 1000000)]
		[Display(Name = "Manual Max Volume", Order = 6, GroupName = "5. Visual")]
		public int ManualMaxVol { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "Fixed Transparency (%)", Order = 7, GroupName = "5. Visual")]
		public int FixedTransparency { get; set; }

		[NinjaScriptProperty] [Range(2, 50)]
		[Display(Name = "Fixed Bubble Radius (px)", Order = 8, GroupName = "5. Visual")]
		public int FixedBubbleRadius { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "Start Transparency (Low Vol)", Order = 9, GroupName = "5. Visual")]
		public int TranspStart { get; set; }

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "End Transparency (High Vol)", Order = 10, GroupName = "5. Visual")]
		public int TranspEnd { get; set; }

		[NinjaScriptProperty] [Range(100, 100000)]
		[Display(Name = "Max Bubbles Stored", Order = 11, GroupName = "5. Visual",
			Description = "Límite de memoria de burbujas dibujables. No afecta zonas ni export.")]
		public int MaxBubblesStored { get; set; }

		[XmlIgnore]
		[Display(Name = "Trapped Buyers Color", Order = 12, GroupName = "5. Visual")]
		public System.Windows.Media.Brush BullColor { get; set; }
		[Browsable(false)]
		public string BullColorSerialize
		{
			get { return Serialize.BrushToString(BullColor); }
			set { BullColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore]
		[Display(Name = "Trapped Sellers Color", Order = 13, GroupName = "5. Visual")]
		public System.Windows.Media.Brush BearColor { get; set; }
		[Browsable(false)]
		public string BearColorSerialize
		{
			get { return Serialize.BrushToString(BearColor); }
			set { BearColor = Serialize.StringToBrush(value); }
		}

		#endregion
	}
}
