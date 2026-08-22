// # meta indicator=BigTrap2Absorption,version=1.0
//
// BigTrap2Absorption — absorcion = flujo alto con desplazamiento bajo.
//
// POR QUE EXISTE  (acta: docs/research/REVISION_MULTIMODELO_BT2_OPUS5.md)
// BigTrap2 define el evento con ratio = agresivo / max(opuesto, 1). Con la celda
// opuesta vacia el cociente degenera en el conteo absoluto, asi que con
// ImbalanceRatio = 3 el evento real es "tres contratos al ask y nada abajo".
// Medido en GC DEC26 17-21 ago: 11.964 / 24.093 cubetas = 49,7 % con TRAP,
// trap_vol mediano = 4 contratos en 1 sola fila. Eso no es un evento.
//
// QUE CAMBIA
// 1. El evento deja de ser un umbral absoluto y pasa a ser un RESIDUO: cuanto
//    flujo firmado se comio el mercado por cada tick que se movio.
//        dFav = sign(flujo) * (close - open)  en ticks
//        A    = |flujo| / (1 + max(0, dFav))        [AbsDirectional]
//        A    = |flujo| / (1 + |close - open|)      [AbsMagnitude]
//    Dispara si A supera el percentil AbsorptionPct de las ultimas
//    AbsorptionLookback cubetas. El percentil es CAUSAL: la cubeta actual no
//    entra en su propio umbral. Escala-libre: la tasa de disparo la fija el
//    percentil, no el tamano del contrato ni la hora del dia.
// 2. MinStackedRows: exige filas desbalanceadas CONTIGUAS. Una celda aislada es
//    ruido (trap_nrows p50 = 1 en el kernel viejo).
// 3. MinTrapFrac: el trap tiene que ser una FRACCION del volumen de la cubeta,
//    no un numero absoluto de contratos. MinTrapVolume queda en 0 (apagado).
// 4. TapeWindowTicks es PARAMETRO REAL. En BigTrap2UniversalFill era const 25.
//
// CONTRATO
// - Un solo motor: AddDataSeries(Tick, 1). El chart es SOLO pantalla. Misma zona
//   al mismo precio en cualquier tickframe o timeframe.
// - Senal al close de la cubeta. FILL = primer tick POSTERIOR (tiempo y precio de
//   ese print). Es lo mas cerca de un bot a mercado sin look-ahead.
// - El percentil es causal. TopPercentFilter sigue siendo look-ahead y sigue
//   siendo SOLO visual.
// - TRAP se exporta SIEMPRE que haya geometria (>= MinExportVolume), con el
//   agregado del kernel viejo (vol / centroid / zone_lo / zone_hi / n_rows /
//   max_ratio, campos identicos a BigTrap2) MAS los campos nuevos (a_score,
//   a_thr, a_pass, trap_frac, signed_flow, d_ticks, run_*). Una sola corrida
//   permite barrer q, MinStackedRows y MinTrapFrac OFFLINE y reproducir el
//   kernel viejo exactamente desde el mismo archivo.
// - ZONE_CREATED y FILL solo cuando pasan TODOS los cortes.
// - Las cubetas residuales (cierre de sesion, bloque parcial) NO entran al
//   historial del percentil y NO disparan: no son comparables con una completa.
// - NO corona edge. Se mide contra el control S1 de F2.9 (+0,038), no contra cero.
// - Sin region generated. CRLF. Convive con BigTrap2 / Universal / Fill / Edge.
// - Tick data historico. No Tick Replay.

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

public enum BT2AbsImbalanceMode { Diagonal, SameLevel }
public enum BT2AbsTrapVolumeSrc { AggressiveSide, TotalLevel }
public enum BT2AbsInvalidation  { None, FirstTouch, CloseThrough }
public enum BT2AbsScoreMode     { AbsDirectional, AbsMagnitude }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class BigTrap2Absorption : Indicator
	{
		private const string IND_VERSION = "1.0";

		private struct FpTick
		{
			public long Tick; public double Vol; public int Side;
			public bool ByQuote; public DateTime Time;
		}

		private struct BarSnap
		{
			public int Bar;
			public long OpenTick, CloseTick;
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
			public double ZoneLo, ZoneHi, Volume, Score;
			public DateTime SignalAt;
		}

		private struct Run
		{
			public long Lo, Hi; public double Vol, WSum, MaxRatio; public int NRows;
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
		private readonly List<Run> buyRuns = new List<Run>(16);
		private readonly List<Run> sellRuns = new List<Run>(16);
		private readonly object bubbleLock = new object();
		private SessionIterator _sessIter;
		private DateTime _sessEnd = DateTime.MinValue;
		private double lastTickPrice = double.NaN;
		private int lastTickDir;
		private int analyzeBarSeq;
		private bool skippedFirst;
		private int eventSeq;
		private StreamWriter eventWriter;
		private double[] absRing;
		private int absCount, absPos;
		private SharpDX.Direct2D1.Brush dxBull, dxBear;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "BigTrap2Absorption";
				Description = "Absorcion = flujo alto con desplazamiento bajo. Percentil causal, escala-libre. Bolita en el fill.";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = false;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				TapeWindowTicks = 25;

				ScoreMode = BT2AbsScoreMode.AbsDirectional;
				AbsorptionPct = 90.0;
				AbsorptionLookback = 500;
				MinHistoryBuckets = 200;
				RequireFlowSideMatch = true;

				TicksPerRow = 1;
				ImbalanceMode = BT2AbsImbalanceMode.Diagonal;
				TrapVolumeSource = BT2AbsTrapVolumeSrc.AggressiveSide;
				UseWickFilter = true;
				WickZonePct = 30.0;

				ImbalanceRatio = 3.0;
				MinStackedRows = 2;
				MinTrapFrac = 0.20;
				MinDeltaFilter = 0;
				MinTrapVolume = 0;
				MinExportVolume = 1;

				InvalidationMode = BT2AbsInvalidation.CloseThrough;
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
				absRing = new double[Math.Max(20, AbsorptionLookback)];
				absCount = 0;
				absPos = 0;
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
			if (curBlock.Count >= Math.Max(2, TapeWindowTicks))
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
						"side={0};dir={1};fill_px={2};fill_at={3:o};signal_at={4:o};a_score={5}",
						p.IsBull ? "trapped_buyers" : "trapped_sellers",
						p.IsBull ? "short" : "long",
						px, ev.Time, p.SignalAt, p.Score));
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
			double fpVol = 0, signedFlow = 0;
			int nQuote = 0, nRule = 0;
			for (int i = 0; i < curBlock.Count; i++)
			{
				FpTick e = curBlock[i];
				Dictionary<long, double> m = e.Side > 0 ? askMap : bidMap;
				double cur;
				m[e.Tick] = m.TryGetValue(e.Tick, out cur) ? cur + e.Vol : e.Vol;
				fpVol += e.Vol;
				signedFlow += e.Side > 0 ? e.Vol : -e.Vol;
				if (e.ByQuote) nQuote++; else nRule++;
			}

			double dPx = (double)(s.CloseTick - s.OpenTick);
			double denom;
			if (ScoreMode == BT2AbsScoreMode.AbsDirectional)
			{
				double sgn = signedFlow > 0 ? 1.0 : (signedFlow < 0 ? -1.0 : 0.0);
				denom = 1.0 + Math.Max(0.0, sgn * dPx);
			}
			else
			{
				denom = 1.0 + Math.Abs(dPx);
			}
			double aScore = Math.Abs(signedFlow) / denom;

			double aThr = double.NaN;
			bool aPass;
			if (AbsorptionPct <= 0.0)
			{
				aPass = true;
			}
			else if (absCount >= Math.Max(1, MinHistoryBuckets))
			{
				aThr = Percentile(AbsorptionPct);
				aPass = aScore >= aThr;
			}
			else
			{
				aPass = false;
			}
			if (residual) aPass = false;

			LogEvent(s.Time, "ABS_SCORE", string.Format(CultureInfo.InvariantCulture,
				"bar={0};residual={1};signed_flow={2};d_ticks={3};a_score={4};a_thr={5};a_pass={6};n_hist={7}",
				s.Bar, residual, signedFlow, dPx, aScore, aThr, aPass, absCount));

			if (askMap.Count > 0 || bidMap.Count > 0)
				ProcessBar(s, askMap, bidMap, fpVol, nQuote, nRule, signedFlow, dPx, aScore, aThr, aPass);

			if (!residual) PushAbs(aScore);
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
				OpenTick = o, CloseTick = c,
				Open = o * TickSize, High = mx * TickSize,
				Low = mn * TickSize, Close = c * TickSize,
				Volume = vol, Time = blk[blk.Count - 1].Time
			};
			LogEvent(s.Time, "BARRA_PROCESADA", string.Format(CultureInfo.InvariantCulture,
				"bar={0};largo={1};residual={2};tape_window={3}",
				s.Bar, blk.Count, residual, Math.Max(2, TapeWindowTicks)));
			return s;
		}

		private void ProcessBar(BarSnap s, Dictionary<long, double> askMap, Dictionary<long, double> bidMap,
		                        double fpVol, int nQuote, int nRule,
		                        double signedFlow, double dPx, double aScore, double aThr, bool aPass)
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

			buyRuns.Clear(); sellRuns.Clear();
			bool bAct = false; long bPrev = long.MinValue; Run bCur = default(Run);
			bool sAct = false; long sPrev = long.MinValue; Run sCur = default(Run);

			foreach (long r in rowKeys)
			{
				double a, b;
				rowAsk.TryGetValue(r, out a);
				rowBid.TryGetValue(r, out b);
				double total = a + b;
				bool skip = Math.Abs(a - b) < MinDeltaFilter;

				double buyRatio = 0, sellRatio = 0;
				if (!skip)
				{
					if (ImbalanceMode == BT2AbsImbalanceMode.Diagonal)
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
				}

				double rowPrice = (r * rowTicks + (rowTicks - 1) / 2.0) * TickSize;
				long rowHalfTick = 2 * r * rowTicks + (rowTicks - 1);
				double contribBuy = TrapVolumeSource == BT2AbsTrapVolumeSrc.AggressiveSide ? a : total;
				double contribSell = TrapVolumeSource == BT2AbsTrapVolumeSrc.AggressiveSide ? b : total;

				bool buyQ = !skip && a >= 1 && buyRatio >= ImbalanceRatio && rowHalfTick > closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice >= wickHiFloor));
				bool sellQ = !skip && b >= 1 && sellRatio >= ImbalanceRatio && rowHalfTick < closeHalfTick
					&& (!UseWickFilter || (range > 0 && rowPrice <= wickLoCeil));

				if (buyQ)
				{
					buyVol += contribBuy; buyWSum += rowPrice * contribBuy; buyRows++;
					if (r < buyLo) buyLo = r; if (r > buyHi) buyHi = r;
					if (buyRatio > buyMaxRatio) buyMaxRatio = buyRatio;

					if (bAct && r == bPrev + 1)
					{
						bCur.Hi = r; bCur.Vol += contribBuy; bCur.WSum += rowPrice * contribBuy; bCur.NRows++;
						if (buyRatio > bCur.MaxRatio) bCur.MaxRatio = buyRatio;
					}
					else
					{
						if (bAct) buyRuns.Add(bCur);
						bCur = new Run { Lo = r, Hi = r, Vol = contribBuy, WSum = rowPrice * contribBuy, MaxRatio = buyRatio, NRows = 1 };
						bAct = true;
					}
					bPrev = r;
				}
				else if (bAct) { buyRuns.Add(bCur); bAct = false; }

				if (sellQ)
				{
					sellVol += contribSell; sellWSum += rowPrice * contribSell; sellRows++;
					if (r < sellLo) sellLo = r; if (r > sellHi) sellHi = r;
					if (sellRatio > sellMaxRatio) sellMaxRatio = sellRatio;

					if (sAct && r == sPrev + 1)
					{
						sCur.Hi = r; sCur.Vol += contribSell; sCur.WSum += rowPrice * contribSell; sCur.NRows++;
						if (sellRatio > sCur.MaxRatio) sCur.MaxRatio = sellRatio;
					}
					else
					{
						if (sAct) sellRuns.Add(sCur);
						sCur = new Run { Lo = r, Hi = r, Vol = contribSell, WSum = rowPrice * contribSell, MaxRatio = sellRatio, NRows = 1 };
						sAct = true;
					}
					sPrev = r;
				}
				else if (sAct) { sellRuns.Add(sCur); sAct = false; }
			}
			if (bAct) buyRuns.Add(bCur);
			if (sAct) sellRuns.Add(sCur);

			int flowSide = signedFlow > 0 ? 1 : (signedFlow < 0 ? -1 : 0);

			EmitSide(s, true, buyVol, buyWSum, buyLo, buyHi, buyRows, buyMaxRatio, buyRuns,
				fpVol, nQuote, nRule, rowTicks, signedFlow, dPx, aScore, aThr, aPass, flowSide == 1);
			EmitSide(s, false, sellVol, sellWSum, sellLo, sellHi, sellRows, sellMaxRatio, sellRuns,
				fpVol, nQuote, nRule, rowTicks, signedFlow, dPx, aScore, aThr, aPass, flowSide == -1);
		}

		private void EmitSide(BarSnap s, bool isBull, double vol, double wSum, long loRow, long hiRow, int nRows,
		                      double maxRatio, List<Run> runs, double fpVol, int nQuote, int nRule, int rowTicks,
		                      double signedFlow, double dPx, double aScore, double aThr, bool aPass, bool sideMatch)
		{
			if (nRows == 0 || vol <= 0 || vol < MinExportVolume) return;

			double centroid = wSum / vol;
			long loTick = loRow * rowTicks;
			long hiTick = (hiRow + 1) * rowTicks - 1;
			double zoneLo = loTick * TickSize - TickSize / 2.0;
			double zoneHi = hiTick * TickSize + TickSize / 2.0;
			double barVol = s.Volume > 0 ? s.Volume : 1.0;
			double trapFrac = vol / barVol;

			int minRows = Math.Max(1, MinStackedRows);
			int iK = -1;
			for (int i = 0; i < runs.Count; i++)
			{
				if (runs[i].NRows >= minRows && (iK < 0 || runs[i].Vol > runs[iK].Vol)) iK = i;
			}
			bool hasRun = iK >= 0;
			double runVol = hasRun ? runs[iK].Vol : 0.0;
			int runRows = hasRun ? runs[iK].NRows : 0;
			double runFrac = runVol / barVol;
			long runLoTick = hasRun ? runs[iK].Lo * rowTicks : 0;
			long runHiTick = hasRun ? (runs[iK].Hi + 1) * rowTicks - 1 : 0;
			double runZoneLo = hasRun ? runLoTick * TickSize - TickSize / 2.0 : 0.0;
			double runZoneHi = hasRun ? runHiTick * TickSize + TickSize / 2.0 : 0.0;
			double runCentroid = hasRun && runVol > 0 ? runs[iK].WSum / runVol : 0.0;

			LogEvent(s.Time, "TRAP", string.Format(CultureInfo.InvariantCulture,
				"bar={0};side={1};vol={2};centroid={3};zone_lo={4};zone_hi={5};n_rows={6};max_ratio={7};close={8};bar_vol={9};fp_vol={10};n_quote={11};n_rule={12};trap_frac={13};signed_flow={14};d_ticks={15};a_score={16};a_thr={17};a_pass={18};side_match={19};n_runs={20};run_vol={21};run_rows={22};run_frac={23};run_lo={24};run_hi={25};run_centroid={26};available_at={27:o}",
				s.Bar, isBull ? "trapped_buyers" : "trapped_sellers",
				vol, centroid, zoneLo, zoneHi, nRows, maxRatio, s.Close, s.Volume, fpVol, nQuote, nRule,
				trapFrac, signedFlow, dPx, aScore, aThr, aPass, sideMatch,
				runs.Count, runVol, runRows, runFrac, runZoneLo, runZoneHi, runCentroid, s.Time));

			if (!aPass) return;
			if (RequireFlowSideMatch && !sideMatch) return;
			if (!hasRun) return;
			if (runVol < MinTrapVolume) return;
			if (runFrac < MinTrapFrac) return;

			pending.Add(new PendingFill {
				IsBull = isBull, ZoneLo = runZoneLo, ZoneHi = runZoneHi,
				Volume = runVol, Score = aScore, SignalAt = s.Time });
			activeZones.Add(new UZone {
				CreatedBar = s.Bar, CreatedAt = s.Time, IsBull = isBull,
				LoTick = runLoTick, HiTick = runHiTick, Volume = runVol });
			LogEvent(s.Time, "ZONE_CREATED", string.Format(CultureInfo.InvariantCulture,
				"zone_id={0}_{1};created_bar={0};side={2};dir={3};lo={4};hi={5};vol={6};rows={7};frac={8};a_score={9};a_thr={10};available_at={11:o}",
				s.Bar, isBull ? "B" : "S",
				isBull ? "trapped_buyers" : "trapped_sellers",
				isBull ? "short" : "long",
				runZoneLo, runZoneHi, runVol, runRows, runFrac, aScore, aThr, s.Time));
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
				if (InvalidationMode == BT2AbsInvalidation.FirstTouch && touched) reason = "first_touch";
				else if (InvalidationMode == BT2AbsInvalidation.CloseThrough && adverse) reason = "close_through";
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

		// Percentil CAUSAL sobre las ultimas AbsorptionLookback cubetas completas.
		// La cubeta en curso NO esta en el anillo cuando se evalua su propio umbral.
		private double Percentile(double q)
		{
			int n = absCount;
			if (absRing == null || n <= 0) return double.NaN;
			double[] tmp = new double[n];
			Array.Copy(absRing, tmp, n);
			Array.Sort(tmp);
			if (n == 1) return tmp[0];
			double qq = q < 0.0 ? 0.0 : (q > 100.0 ? 100.0 : q);
			double pos = (qq / 100.0) * (n - 1);
			int lo = (int)Math.Floor(pos);
			int hi = (int)Math.Ceiling(pos);
			if (lo < 0) lo = 0;
			if (hi >= n) hi = n - 1;
			if (lo == hi) return tmp[lo];
			return tmp[lo] + (tmp[hi] - tmp[lo]) * (pos - lo);
		}

		private void PushAbs(double v)
		{
			if (absRing == null || absRing.Length == 0) return;
			absRing[absPos] = v;
			absPos = (absPos + 1) % absRing.Length;
			if (absCount < absRing.Length) absCount++;
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				eventWriter = new StreamWriter(EventLogPath, false);
				eventWriter.WriteLine("# meta indicator=BigTrap2Absorption,version=" + IND_VERSION
					+ ",attribution=self_cut_1tick,classifier=bidask_then_tickrule"
					+ ",tape_window=" + Math.Max(2, TapeWindowTicks)
					+ ",score_mode=" + ScoreMode
					+ ",absorption_pct=" + AbsorptionPct.ToString(CultureInfo.InvariantCulture)
					+ ",absorption_lookback=" + AbsorptionLookback
					+ ",min_history=" + MinHistoryBuckets
					+ ",require_flow_side_match=" + RequireFlowSideMatch
					+ ",imbalance_mode=" + ImbalanceMode
					+ ",trap_volume=" + TrapVolumeSource
					+ ",ticks_per_row=" + TicksPerRow
					+ ",imbalance_ratio=" + ImbalanceRatio.ToString(CultureInfo.InvariantCulture)
					+ ",min_stacked_rows=" + MinStackedRows
					+ ",min_trap_frac=" + MinTrapFrac.ToString(CultureInfo.InvariantCulture)
					+ ",min_trap_volume=" + MinTrapVolume.ToString(CultureInfo.InvariantCulture)
					+ ",min_export_volume=" + MinExportVolume.ToString(CultureInfo.InvariantCulture)
					+ ",wick_filter=" + UseWickFilter
					+ ",wick_zone_pct=" + WickZonePct.ToString(CultureInfo.InvariantCulture)
					+ ",min_delta=" + MinDeltaFilter.ToString(CultureInfo.InvariantCulture)
					+ ",invalidation=" + InvalidationMode
					+ ",max_age_bars=" + MaxAgeBars
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

		[NinjaScriptProperty, Range(2, 100000), Display(Name = "TapeWindowTicks", GroupName = "0. Motor", Order = 0)]
		public int TapeWindowTicks { get; set; }

		[NinjaScriptProperty, Display(Name = "ScoreMode", GroupName = "1. Absorcion", Order = 0)]
		public BT2AbsScoreMode ScoreMode { get; set; }

		[NinjaScriptProperty, Range(0, 100), Display(Name = "AbsorptionPct (0 = sin corte)", GroupName = "1. Absorcion", Order = 1)]
		public double AbsorptionPct { get; set; }

		[NinjaScriptProperty, Range(20, 100000), Display(Name = "AbsorptionLookback", GroupName = "1. Absorcion", Order = 2)]
		public int AbsorptionLookback { get; set; }

		[NinjaScriptProperty, Range(1, 100000), Display(Name = "MinHistoryBuckets", GroupName = "1. Absorcion", Order = 3)]
		public int MinHistoryBuckets { get; set; }

		[NinjaScriptProperty, Display(Name = "RequireFlowSideMatch", GroupName = "1. Absorcion", Order = 4)]
		public bool RequireFlowSideMatch { get; set; }

		[NinjaScriptProperty, Range(1, 100), Display(Name = "TicksPerRow", GroupName = "2. Semantica", Order = 0)]
		public int TicksPerRow { get; set; }

		[NinjaScriptProperty, Display(Name = "ImbalanceMode", GroupName = "2. Semantica", Order = 1)]
		public BT2AbsImbalanceMode ImbalanceMode { get; set; }

		[NinjaScriptProperty, Display(Name = "TrapVolumeSource", GroupName = "2. Semantica", Order = 2)]
		public BT2AbsTrapVolumeSrc TrapVolumeSource { get; set; }

		[NinjaScriptProperty, Display(Name = "UseWickFilter", GroupName = "2. Semantica", Order = 3)]
		public bool UseWickFilter { get; set; }

		[NinjaScriptProperty, Range(0, 100), Display(Name = "WickZonePct", GroupName = "2. Semantica", Order = 4)]
		public double WickZonePct { get; set; }

		[NinjaScriptProperty, Range(1, 100), Display(Name = "ImbalanceRatio", GroupName = "3. Seleccion", Order = 0)]
		public double ImbalanceRatio { get; set; }

		[NinjaScriptProperty, Range(1, 50), Display(Name = "MinStackedRows", GroupName = "3. Seleccion", Order = 1)]
		public int MinStackedRows { get; set; }

		[NinjaScriptProperty, Range(0, 1), Display(Name = "MinTrapFrac", GroupName = "3. Seleccion", Order = 2)]
		public double MinTrapFrac { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinDeltaFilter", GroupName = "3. Seleccion", Order = 3)]
		public double MinDeltaFilter { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinTrapVolume (0 = apagado)", GroupName = "3. Seleccion", Order = 4)]
		public double MinTrapVolume { get; set; }

		[NinjaScriptProperty, Range(0, double.MaxValue), Display(Name = "MinExportVolume", GroupName = "3. Seleccion", Order = 5)]
		public double MinExportVolume { get; set; }

		[NinjaScriptProperty, Display(Name = "InvalidationMode", GroupName = "4. Ciclo", Order = 0)]
		public BT2AbsInvalidation InvalidationMode { get; set; }

		[NinjaScriptProperty, Range(0, int.MaxValue), Display(Name = "MaxTouches", GroupName = "4. Ciclo", Order = 1)]
		public int MaxTouches { get; set; }

		[NinjaScriptProperty, Range(0, int.MaxValue), Display(Name = "MaxAgeBars", GroupName = "4. Ciclo", Order = 2)]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty, Display(Name = "EventLogPath", GroupName = "5. Export", Order = 0)]
		public string EventLogPath { get; set; }

		[NinjaScriptProperty, Display(Name = "DrawZoneBand", GroupName = "6. Visual", Order = 0)]
		public bool DrawZoneBand { get; set; }

		[Range(1, 100), Display(Name = "TopPercentFilter (LOOKAHEAD)", GroupName = "6. Visual", Order = 1)]
		public double TopPercentFilter { get; set; }

		[Range(100, 20000), Display(Name = "MaxBubblesStored", GroupName = "6. Visual", Order = 2)]
		public int MaxBubblesStored { get; set; }

		[XmlIgnore, Display(Name = "BullColor", GroupName = "6. Visual", Order = 3)]
		public Brush BullColor { get; set; }
		[Browsable(false)]
		public string BullColorSerializable { get { return Serialize.BrushToString(BullColor); } set { BullColor = Serialize.StringToBrush(value); } }

		[XmlIgnore, Display(Name = "BearColor", GroupName = "6. Visual", Order = 4)]
		public Brush BearColor { get; set; }
		[Browsable(false)]
		public string BearColorSerializable { get { return Serialize.BrushToString(BearColor); } set { BearColor = Serialize.StringToBrush(value); } }
	}
}
