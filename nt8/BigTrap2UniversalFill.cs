// # meta indicator=BigTrap2UniversalFill,version=1.0
//
// BigTrap2UniversalFill — bolita = fill de un bot a mercado.
//
// CONTRATO
// 1. Un solo motor: AddDataSeries(Tick, 1). El chart es SOLO pantalla.
//    TapeWindowTicks es constante interna (25). Misma zona en cualquier
//    tickframe o timeframe.
// 2. Senal al close de la cubeta. FILL = primer tick POSTERIOR
//    (tiempo y precio de ese print). Eso es lo mas cerca de un bot
//    a mercado sin look-ahead. No corona edge.
// 3. Kernel = BigTrap2. MinTrapVolume solo corta burbuja+zona.
// 4. TopPercentFilter visual, default 100.
// 5. Sin region generated. CRLF. Convive con BigTrap2 / Universal / Edge.
// 6. Tick data historico. No Tick Replay.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
#endregion

public enum BT2UFImbalanceMode { Diagonal, SameLevel }
public enum BT2UFTrapVolumeSrc { AggressiveSide, TotalLevel }
public enum BT2UFInvalidation  { None, FirstTouch, CloseThrough }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrap2UniversalFill : Indicator
	{
		private const string IND_VERSION = "1.0";
		private const int TapeWindowTicks = 25;

		private struct FpTick
		{
			public long Tick; public double Vol; public int Side;
			public bool ByQuote; public DateTime Time;
		}

		private struct BarSnap
		{
			public int Bar;
			public double Open, High, Low, Close, Volume;
			public DateTime Time;
		}

		private struct UBubble
		{
			public DateTime AvailableAt;
			public double Price, ZoneLo, ZoneHi, Volume;
			public bool IsBull;
		}

		private struct PendingFill
		{
			public bool IsBull;
			public double ZoneLo, ZoneHi, Volume;
			public DateTime SignalAt;
		}

		private sealed class UZone
		{
			public int CreatedBar; public DateTime CreatedAt; public bool IsBull;
			public long LoTick, HiTick; public double Volume; public int Touches;
		}

		private readonly List<FpTick> curBlock = new List<FpTick>(64);
		private readonly List<UBubble> bubbles = new List<UBubble>(512);
		private readonly List<UZone> activeZones = new List<UZone>(64);
		private readonly List<PendingFill> pending = new List<PendingFill>(8);
		private readonly object bubbleLock = new object();
		private SessionIterator _sessIter;
		private DateTime _sessEnd = DateTime.MinValue;
		private double lastTickPrice = double.NaN;
		private int lastTickDir;
		private int analyzeBarSeq;
		private bool skippedFirst;
		private int eventSeq;
		private StreamWriter eventWriter;
		private SharpDX.Direct2D1.Brush dxBull, dxBear, dxZone;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "BigTrap2UniversalFill";
				Description = "Bolita en el fill: primer tick despues del aviso. Lo mas cerca de un bot a mercado.";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = false;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				TicksPerRow = 1;
				ImbalanceMode = BT2UFImbalanceMode.Diagonal;
				TrapVolumeSource = BT2UFTrapVolumeSrc.AggressiveSide;
				UseWickFilter = true;
				WickZonePct = 30.0;
				ImbalanceRatio = 3.0;
				MinDeltaFilter = 0;
				MinTrapVolume = 30;
				MinExportVolume = 1;
				InvalidationMode = BT2UFInvalidation.CloseThrough;
				MaxTouches = 0;
				MaxAgeBars = 2000;
				EventLogPath = "";
				DrawZoneBand = true;
				TopPercentFilter = 100.0;
				MaxBubblesStored = 4000;
				BullColor = Brushes.Teal;
				BearColor = Brushes.Red;
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				_sessIter = new SessionIterator(BarsArray[1]);
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (eventWriter != null)
				{
					try { eventWriter.Flush(); eventWriter.Dispose(); } catch { }
					eventWriter = null;
				}
				if (dxBull != null) { dxBull.Dispose(); dxBull = null; }
				if (dxBear != null) { dxBear.Dispose(); dxBear = null; }
				if (dxZone != null) { dxZone.Dispose(); dxZone = null; }
			}
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress != 1) return;
			if (CurrentBars == null || CurrentBars.Length < 2 || CurrentBars[1] < 0) return;
			AccumulateTick();
		}

		private void AccumulateTick()
		{
			double price = Closes[1][0];
			double vol = Volumes[1][0];
			int idx = CurrentBars[1];
			DateTime tEv = Times[1][0];

			double askQ = BarsArray[1].GetAsk(idx);
			double bidQ = BarsArray[1].GetBid(idx);
			int side = 0; bool byQuote = false;
			if (askQ > 0 && bidQ > 0 && askQ >= bidQ)
			{
				if (price >= askQ) { side = 1; byQuote = true; }
				else if (price <= bidQ) { side = -1; byQuote = true; }
			}
			if (side == 0)
			{
				if (!double.IsNaN(lastTickPrice))
				{
					if (price > lastTickPrice) side = 1;
					else if (price < lastTickPrice) side = -1;
					else side = lastTickDir;
				}
				if (side == 0) side = 1;
			}
			lastTickPrice = price;
			lastTickDir = side;

			long tick = (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
			FpTick ev = new FpTick { Tick = tick, Vol = vol, Side = side, ByQuote = byQuote, Time = tEv };

			if (_sessEnd == DateTime.MinValue || tEv >= _sessEnd)
			{
				if (curBlock.Count > 0) FlushBlock(true);
				_sessIter.GetNextSession(tEv, true);
				_sessEnd = _sessIter.ActualSessionEnd;
			}

			FillPendings(ev);
			curBlock.Add(ev);
			if (curBlock.Count >= TapeWindowTicks)
				FlushBlock(false);
		}

		private void FillPendings(FpTick ev)
		{
			if (pending.Count == 0) return;
			double px = ev.Tick * TickSize;
			lock (bubbleLock)
			{
				for (int i = 0; i < pending.Count; i++)
				{
					PendingFill p = pending[i];
					bubbles.Add(new UBubble {
						AvailableAt = ev.Time, Price = px,
						ZoneLo = p.ZoneLo, ZoneHi = p.ZoneHi,
						Volume = p.Volume, IsBull = p.IsBull });
					LogEvent(ev.Time, "FILL", string.Format(CultureInfo.InvariantCulture,
						"side={0};fill_px={1};fill_at={2:o};signal_at={3:o}",
						p.IsBull ? "trapped_buyers" : "trapped_sellers",
						px, ev.Time, p.SignalAt));
				}
				int excess = bubbles.Count - Math.Max(100, MaxBubblesStored);
				if (excess > 0) bubbles.RemoveRange(0, excess);
			}
			pending.Clear();
		}

		private void FlushBlock(bool residual)
		{
			if (curBlock.Count == 0) return;
			if (!skippedFirst)
			{
				curBlock.Clear();
				skippedFirst = true;
				return;
			}

			BarSnap s = SnapFromBlock(curBlock, residual);
			UpdateZones(s);

			var askMap = new Dictionary<long, double>(64);
			var bidMap = new Dictionary<long, double>(64);
			double fpVol = 0; int nQuote = 0, nRule = 0;
			for (int i = 0; i < curBlock.Count; i++)
			{
				FpTick e = curBlock[i];
				Dictionary<long, double> m = e.Side > 0 ? askMap : bidMap;
				double cur;
				m[e.Tick] = m.TryGetValue(e.Tick, out cur) ? cur + e.Vol : e.Vol;
				fpVol += e.Vol;
				if (e.ByQuote) nQuote++; else nRule++;
			}
			if (askMap.Count > 0 || bidMap.Count > 0)
				ProcessBar(s, askMap, bidMap, fpVol, nQuote, nRule);
			curBlock.Clear();
		}

		private BarSnap SnapFromBlock(List<FpTick> blk, bool residual)
		{
			long o = blk[0].Tick, c = blk[blk.Count - 1].Tick;
			long mn = o, mx = o;
			double vol = 0;
			for (int i = 0; i < blk.Count; i++)
			{
				if (blk[i].Tick < mn) mn = blk[i].Tick;
				if (blk[i].Tick > mx) mx = blk[i].Tick;
				vol += blk[i].Vol;
			}
			analyzeBarSeq++;
			BarSnap s = new BarSnap {
				Bar = analyzeBarSeq,
				Open = o * TickSize, High = mx * TickSize,
				Low = mn * TickSize, Close = c * TickSize,
				Volume = vol, Time = blk[blk.Count - 1].Time
			};
			LogEvent(s.Time, "BARRA_PROCESADA", string.Format(CultureInfo.InvariantCulture,
				"bar={0};largo={1};residual={2};tape_window={3}",
				s.Bar, blk.Count, residual, TapeWindowTicks));
			return s;
		}

		private void ProcessBar(BarSnap s, Dictionary<long, double> askMap, Dictionary<long, double> bidMap,
		                        double fpVol, int nQuote, int nRule)
		{
			int rowTicks = Math.Max(1, TicksPerRow);
			var rowAsk = new Dictionary<long, double>();
			var rowBid = new Dictionary<long, double>();
			foreach (var kv in askMap)
			{
				long r = FloorDiv(kv.Key, rowTicks);
				double cur;
				rowAsk[r] = rowAsk.TryGetValue(r, out cur) ? cur + kv.Value : kv.Value;
			}
			foreach (var kv in bidMap)
			{
				long r = FloorDiv(kv.Key, rowTicks);
				double cur;
				rowBid[r] = rowBid.TryGetValue(r, out cur) ? cur + kv.Value : kv.Value;
			}
			var rowKeys = new SortedSet<long>(rowAsk.Keys);
			foreach (long k in rowBid.Keys) rowKeys.Add(k);
			if (rowKeys.Count == 0) return;

			double close = s.Close;
			long closeHalfTick = 2 * (long)Math.Round(close / TickSize, MidpointRounding.AwayFromZero);
			double lo = s.Low, hi = s.High, range = hi - lo;
			double wickHiFloor = hi - range * (WickZonePct / 100.0);
			double wickLoCeil = lo + range * (WickZonePct / 100.0);

			double buyVol = 0, buyWSum = 0, buyMaxRatio = 0;
			long buyLo = long.MaxValue, buyHi = long.MinValue; int buyRows = 0;
			double sellVol = 0, sellWSum = 0, sellMaxRatio = 0;
			long sellLo = long.MaxValue, sellHi = long.MinValue; int sellRows = 0;

			foreach (long r in rowKeys)
			{
				double a, b;
				rowAsk.TryGetValue(r, out a);
				rowBid.TryGetValue(r, out b);
				double total = a + b;
				if (Math.Abs(a - b) < MinDeltaFilter) continue;

				double buyRatio, sellRatio;
				if (ImbalanceMode == BT2UFImbalanceMode.Diagonal)
				{
					double bDn, aUp;
					rowBid.TryGetValue(r - 1, out bDn);
					rowAsk.TryGetValue(r + 1, out aUp);
					buyRatio = a / Math.Max(bDn, 1.0);
					sellRatio = b / Math.Max(aUp, 1.0);
				}
				else
				{
					buyRatio = a / Math.Max(b, 1.0);
					sellRatio = b / Math.Max(a, 1.0);
				}

				double rowPrice = (r * rowTicks + (rowTicks - 1) / 2.0) * TickSize;
				long rowHalfTick = 2 * r * rowTicks + (rowTicks - 1);
				double contribBuy = TrapVolumeSource == BT2UFTrapVolumeSrc.AggressiveSide ? a : total;
				double contribSell = TrapVolumeSource == BT2UFTrapVolumeSrc.AggressiveSide ? b : total;

				if (a >= 1 && buyRatio >= ImbalanceRatio && rowHalfTick > closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice >= wickHiFloor)))
				{
					buyVol += contribBuy; buyWSum += rowPrice * contribBuy; buyRows++;
					if (r < buyLo) buyLo = r; if (r > buyHi) buyHi = r;
					if (buyRatio > buyMaxRatio) buyMaxRatio = buyRatio;
				}
				if (b >= 1 && sellRatio >= ImbalanceRatio && rowHalfTick < closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice <= wickLoCeil)))
				{
					sellVol += contribSell; sellWSum += rowPrice * contribSell; sellRows++;
					if (r < sellLo) sellLo = r; if (r > sellHi) sellHi = r;
					if (sellRatio > sellMaxRatio) sellMaxRatio = sellRatio;
				}
			}

			EmitSide(s, true, buyVol, buyWSum, buyLo, buyHi, buyRows, buyMaxRatio, fpVol, nQuote, nRule, rowTicks);
			EmitSide(s, false, sellVol, sellWSum, sellLo, sellHi, sellRows, sellMaxRatio, fpVol, nQuote, nRule, rowTicks);
		}

		private void EmitSide(BarSnap s, bool isBull, double vol, double wSum, long loRow, long hiRow, int nRows,
		                      double maxRatio, double fpVol, int nQuote, int nRule, int rowTicks)
		{
			if (nRows == 0 || vol <= 0 || vol < MinExportVolume) return;
			double centroid = wSum / vol;
			long loTick = loRow * rowTicks;
			long hiTick = (hiRow + 1) * rowTicks - 1;
			double zoneLo = loTick * TickSize - TickSize / 2.0;
			double zoneHi = hiTick * TickSize + TickSize / 2.0;

			LogEvent(s.Time, "TRAP", string.Format(CultureInfo.InvariantCulture,
				"bar={0};side={1};vol={2};centroid={3};zone_lo={4};zone_hi={5};n_rows={6};max_ratio={7};close={8};bar_vol={9};fp_vol={10};n_quote={11};n_rule={12};available_at={13:o}",
				s.Bar, isBull ? "trapped_buyers" : "trapped_sellers",
				vol, centroid, zoneLo, zoneHi, nRows, maxRatio, s.Close, s.Volume, fpVol, nQuote, nRule, s.Time));

			if (vol < MinTrapVolume) return;

			pending.Add(new PendingFill {
				IsBull = isBull, ZoneLo = zoneLo, ZoneHi = zoneHi,
				Volume = vol, SignalAt = s.Time });
			activeZones.Add(new UZone {
				CreatedBar = s.Bar, CreatedAt = s.Time, IsBull = isBull,
				LoTick = loTick, HiTick = hiTick, Volume = vol });
			LogEvent(s.Time, "ZONE_CREATED", string.Format(CultureInfo.InvariantCulture,
				"zone_id={0}_{1};created_bar={0};side={2};lo={3};hi={4};vol={5};available_at={6:o}",
				s.Bar, isBull ? "B" : "S",
				isBull ? "trapped_buyers" : "trapped_sellers",
				zoneLo, zoneHi, vol, s.Time));
		}

		private void UpdateZones(BarSnap s)
		{
			if (activeZones.Count == 0) return;
			double hi = s.High, lo = s.Low, close = s.Close;
			for (int i = activeZones.Count - 1; i >= 0; i--)
			{
				UZone z = activeZones[i];
				if (MaxAgeBars > 0 && s.Bar - z.CreatedBar > MaxAgeBars)
				{
					LogEvent(s.Time, "ZONE_EXPIRED", "bar=" + s.Bar);
					activeZones.RemoveAt(i);
					continue;
				}
				double zLo = z.LoTick * TickSize - TickSize / 2.0;
				double zHi = z.HiTick * TickSize + TickSize / 2.0;
				bool touched = hi >= zLo && lo <= zHi;
				bool adverse = z.IsBull ? close > zHi : close < zLo;
				if (touched) z.Touches++;
				string reason = null;
				if (InvalidationMode == BT2UFInvalidation.FirstTouch && touched) reason = "first_touch";
				else if (InvalidationMode == BT2UFInvalidation.CloseThrough && adverse) reason = "close_through";
				else if (MaxTouches > 0 && z.Touches >= MaxTouches) reason = "max_touches";
				if (reason != null)
				{
					LogEvent(s.Time, "ZONE_INVALIDATED", "reason=" + reason + ";bar=" + s.Bar);
					activeZones.RemoveAt(i);
				}
			}
		}

		protected override void OnRender(ChartControl chartControl, ChartScale chartScale)
		{
			base.OnRender(chartControl, chartScale);
			if (chartControl == null || ChartBars == null || RenderTarget == null) return;
			UBubble[] snap;
			lock (bubbleLock) { snap = bubbles.ToArray(); }
			if (snap.Length == 0) return;
			if (dxBull == null) dxBull = ToDx(BullColor);
			if (dxBear == null) dxBear = ToDx(BearColor);
			if (dxZone == null) dxZone = ToDx(Brushes.DimGray);

			double thresh = 0;
			if (TopPercentFilter < 100.0 && snap.Length > 1)
			{
				double[] vols = new double[snap.Length];
				for (int i = 0; i < snap.Length; i++) vols[i] = snap[i].Volume;
				Array.Sort(vols);
				int keep = Math.Max(1, (int)Math.Ceiling(vols.Length * TopPercentFilter / 100.0));
				thresh = vols[vols.Length - keep];
			}

			var oldAA = RenderTarget.AntialiasMode;
			RenderTarget.AntialiasMode = SharpDX.Direct2D1.AntialiasMode.PerPrimitive;
			try
			{
				foreach (UBubble b in snap)
				{
					if (b.Volume < thresh) continue;
					float x = chartControl.GetXByTime(b.AvailableAt);
					if (float.IsNaN(x) || x < 0) continue;
					float y = chartScale.GetYByValue(b.Price);
					var brush = b.IsBull ? dxBull : dxBear;
					if (brush == null) continue;
					if (DrawZoneBand)
					{
						float yLo = chartScale.GetYByValue(b.ZoneHi);
						float yHi = chartScale.GetYByValue(b.ZoneLo);
						if (yHi < yLo) { float tmp = yHi; yHi = yLo; yLo = tmp; }
						RenderTarget.DrawLine(new SharpDX.Vector2(x - 6, yLo), new SharpDX.Vector2(x - 6, yHi), brush, 1.5f);
					}
					RenderTarget.FillEllipse(new SharpDX.Direct2D1.Ellipse(new SharpDX.Vector2(x, y), 6f, 6f), brush);
				}
			}
			finally { RenderTarget.AntialiasMode = oldAA; }
		}

		private static long FloorDiv(long a, long b)
		{
			long q = a / b;
			if ((a % b != 0) && ((a < 0) != (b < 0))) q--;
			return q;
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				eventWriter = new StreamWriter(EventLogPath, false);
				eventWriter.WriteLine("# meta indicator=BigTrap2UniversalFill,version=" + IND_VERSION
					+ ",attribution=self_cut_1tick,tape_window=" + TapeWindowTicks
					+ ",imbalance_mode=" + ImbalanceMode + ",ticks_per_row=" + TicksPerRow
					+ ",imbalance_ratio=" + ImbalanceRatio.ToString(CultureInfo.InvariantCulture)
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture));
			}
			catch { eventWriter = null; }
		}

		private void LogEvent(DateTime t, string type, string payload)
		{
			if (eventWriter == null) return;
			try
			{
				eventWriter.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0}|{1:o}|{2}|{3}", eventSeq++, t, type, payload));
			}
			catch { }
		}

		private SharpDX.Direct2D1.Brush ToDx(Brush b)
		{
			var sb = b as SolidColorBrush;
			if (sb == null) sb = Brushes.Gray;
			var c = sb.Color;
			return new SharpDX.Direct2D1.SolidColorBrush(RenderTarget,
				new SharpDX.Color4(c.R / 255f, c.G / 255f, c.B / 255f, c.A / 255f));
		}

		[NinjaScriptProperty, Range(1, 100), Display(Name = "TicksPerRow", GroupName = "1. Semantica", Order = 0)]
		public int TicksPerRow { get; set; }

		[NinjaScriptProperty, Display(Name = "ImbalanceMode", GroupName = "1. Semantica", Order = 1)]
		public BT2UFImbalanceMode ImbalanceMode { get; set; }

		[NinjaScriptProperty, Display(Name = "TrapVolumeSource", GroupName = "1. Semantica", Order = 2)]
		public BT2UFTrapVolumeSrc TrapVolumeSource { get; set; }

		[NinjaScriptProperty, Display(Name = "UseWickFilter", GroupName = "1. Semantica", Order = 3)]
		public bool UseWickFilter { get; set; }

		[NinjaScriptProperty, Range(0, 100), Display(Name = "WickZonePct", GroupName = "1. Semantica", Order = 4)]
		public double WickZonePct { get; set; }

		[NinjaScriptProperty, Range(1, 100), Display(Name = "ImbalanceRatio", GroupName = "2. Seleccion", Order = 0)]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinDeltaFilter", GroupName = "2. Seleccion", Order = 1)]
		public double MinDeltaFilter { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinTrapVolume", GroupName = "2. Seleccion", Order = 2)]
		public double MinTrapVolume { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinExportVolume", GroupName = "2. Seleccion", Order = 3)]
		public double MinExportVolume { get; set; }

		[NinjaScriptProperty, Display(Name = "InvalidationMode", GroupName = "3. Ciclo", Order = 0)]
		public BT2UFInvalidation InvalidationMode { get; set; }

		[NinjaScriptProperty, Range(0, int.MaxValue), Display(Name = "MaxTouches", GroupName = "3. Ciclo", Order = 1)]
		public int MaxTouches { get; set; }

		[NinjaScriptProperty, Range(0, int.MaxValue), Display(Name = "MaxAgeBars", GroupName = "3. Ciclo", Order = 2)]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty, Display(Name = "EventLogPath", GroupName = "4. Export", Order = 0)]
		public string EventLogPath { get; set; }

		[NinjaScriptProperty, Display(Name = "DrawZoneBand", GroupName = "5. Visual", Order = 0)]
		public bool DrawZoneBand { get; set; }

		[Range(1, 100), Display(Name = "TopPercentFilter (LOOKAHEAD)", GroupName = "5. Visual", Order = 1)]
		public double TopPercentFilter { get; set; }

		[Range(100, 20000), Display(Name = "MaxBubblesStored", GroupName = "5. Visual", Order = 2)]
		public int MaxBubblesStored { get; set; }

		[XmlIgnore, Display(Name = "BullColor", GroupName = "5. Visual", Order = 3)]
		public Brush BullColor { get; set; }
		[Browsable(false)]
		public string BullColorSerializable { get { return Serialize.BrushToString(BullColor); } set { BullColor = Serialize.StringToBrush(value); } }

		[XmlIgnore, Display(Name = "BearColor", GroupName = "5. Visual", Order = 4)]
		public Brush BearColor { get; set; }
		[Browsable(false)]
		public string BearColorSerializable { get { return Serialize.BrushToString(BearColor); } set { BearColor = Serialize.StringToBrush(value); } }
	}
}
