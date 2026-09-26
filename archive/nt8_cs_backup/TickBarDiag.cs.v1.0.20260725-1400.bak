// ============================================================================
// TickBarDiag.cs — v1.0 — Instrumental de diagnóstico TICKBAR-001
// NO es un indicador de trading: no dibuja, no detecta, no crea zonas.
// Vuelca DOS ledgers para distinguir H1/H2/H3/H4 de
// docs/campaigns/TICKBAR-001_paridad_en_barras_de_tick.md
//
// NO TOCA BigTrap2.cs. Reproduce EXACTAMENTE su patrón de acumulación
// (AddDataSeries(Tick,1) + take/reset en OnBarUpdate con BarsInProgress==0)
// para que lo que se mida sea el comportamiento real de ese patrón.
//
// LEDGER "E" (un evento de la subserie de 1 tick):
//   E,seq,ts_ticks,ts_iso,price_tick,vol,session_idx,digest_stream
// LEDGER "B" (cierre de una barra primaria):
//   B,bar,seq_first,seq_last,n_events,ts_ticks,ts_iso,o,h,l,c,vol_bar,
//     vol_fp,digest_fp,session_idx,is_first_of_session
//
// DIGESTS (reproducibles bit a bit en Python, ver tools/tickbar_diag.py):
//   h = 1469598103934665603
//   mezclar(x): h = (h * 1000003 + (ulong)x)   // aritmética ulong, wrap natural
//   stream: por cada evento, mezclar(price_tick) y luego mezclar(vol_int)
//   footprint: sobre las claves ORDENADAS del mapa, mezclar(tick),
//              mezclar(ask_int), mezclar(bid_int)
//   vol_int = (long)Math.Round(vol * 100)   // el volumen puede no ser entero
//
// PRECIOS: siempre índices ENTEROS de tick vía
//   Math.Round(price / TickSize, MidpointRounding.AwayFromZero)
//   (lección permanente: nunca comparar ni hashear doubles de precio).
//
// VENTANA: se registran las barras primarias [SkipBars, SkipBars+MaxBars).
//   SkipBars descarta el warm-up (la primera barra primaria puede tener el
//   footprint parcial, igual que en BigTrap2).
// ============================================================================
#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class TickBarDiag : Indicator
	{
		private const ulong FNV_BASIS = 1469598103934665603UL;
		private const ulong MIX       = 1000003UL;

		private StreamWriter log;
		private ulong  digestStream = FNV_BASIS;
		private int    sessionIdx   = -1;
		private int    loggedBars   = 0;
		private long   seqFirst     = -1;
		private long   seqLast      = -1;
		private int    nEvents      = 0;
		private double pendingVol   = 0;
		private Dictionary<long, double> pendingAsk = new Dictionary<long, double>(64);
		private Dictionary<long, double> pendingBid = new Dictionary<long, double>(64);
		private double lastTickPrice = double.NaN;
		private int    lastTickDir   = 0;
		private CultureInfo inv = CultureInfo.InvariantCulture;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name        = "TickBarDiag";
				Description = "Diagnostico TICKBAR-001: vuelca stream de 1 tick y limites de barra. No opera.";
				Calculate   = Calculate.OnBarClose;
				IsOverlay   = true;
				DrawOnPricePanel = false;
				SkipBars    = 20;
				MaxBars     = 150;
				EventLogPath = @"E:\EdgeLab\oracles\tickbar_diag.csv";
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				try
				{
					string dir = Path.GetDirectoryName(EventLogPath);
					if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
						Directory.CreateDirectory(dir);
					// false = SOBREESCRIBE. Este archivo es de diagnostico y debe
					// contener UNA sola corrida (el modo append fue el que mezclo
					// tres corridas en el oraculo de BigTrap2 el 2026-07-24).
					log = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
					log.AutoFlush = true;
					log.WriteLine("# meta indicator=TickBarDiag,version=1.0,purpose=TICKBAR-001,"
						+ "digest=fnv_basis_mix1000003_ulong,price=integer_ticks_awayfromzero,"
						+ "vol_int=round(vol*100)");
					log.WriteLine(string.Format(inv,
						"# params instrument={0},tick_size={1},bars_period={2},bars_value={3},"
						+ "skip_bars={4},max_bars={5}",
						Instrument.MasterInstrument.Name, TickSize,
						BarsPeriod.BarsPeriodType, BarsPeriod.Value, SkipBars, MaxBars));
					log.WriteLine("kind,seq,ts_ticks,ts_iso,a,b,c,d,e,f,g,h,i,j,k");
				}
				catch (Exception ex)
				{
					Print("TickBarDiag: no se pudo abrir el log: " + ex.Message);
				}
			}
			else if (State == State.Terminated)
			{
				if (log != null) { log.Flush(); log.Close(); log = null; }
			}
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		private static ulong Mix(ulong h, long x)
		{
			unchecked { return h * MIX + (ulong)x; }
		}

		private bool InWindow()
		{
			return CurrentBar >= SkipBars && loggedBars < MaxBars;
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress == 1)
			{
				AccumulateTick();
				return;
			}
			if (BarsInProgress != 0)
				return;

			// take + reset SIEMPRE, igual que BigTrap2 (sin fuga entre barras)
			Dictionary<long, double> askMap = pendingAsk;
			Dictionary<long, double> bidMap = pendingBid;
			double fpVol = pendingVol;
			long   sF = seqFirst, sL = seqLast;
			int    nE = nEvents;
			pendingAsk = new Dictionary<long, double>(64);
			pendingBid = new Dictionary<long, double>(64);
			pendingVol = 0; seqFirst = -1; seqLast = -1; nEvents = 0;

			if (Bars.IsFirstBarOfSession) sessionIdx++;
			if (log == null || !InWindow()) return;

			// digest del footprint sobre claves ORDENADAS (determinista)
			List<long> keys = new List<long>();
			foreach (long k in askMap.Keys) if (!keys.Contains(k)) keys.Add(k);
			foreach (long k in bidMap.Keys) if (!keys.Contains(k)) keys.Add(k);
			keys.Sort();
			ulong dfp = FNV_BASIS;
			for (int i = 0; i < keys.Count; i++)
			{
				long k = keys[i];
				double av, bv;
				askMap.TryGetValue(k, out av);
				bidMap.TryGetValue(k, out bv);
				dfp = Mix(dfp, k);
				dfp = Mix(dfp, (long)Math.Round(av * 100.0));
				dfp = Mix(dfp, (long)Math.Round(bv * 100.0));
			}

			log.WriteLine(string.Format(inv,
				"B,{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13}",
				CurrentBar, sF, sL, nE, Time[0].Ticks,
				Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fffffff", inv),
				PriceToTick(Open[0]), PriceToTick(High[0]),
				PriceToTick(Low[0]), PriceToTick(Close[0]),
				(long)Math.Round(Volume[0] * 100.0),
				(long)Math.Round(fpVol * 100.0),
				dfp, sessionIdx));
			loggedBars++;
		}

		private void AccumulateTick()
		{
			double price = Closes[1][0];
			double vol   = Volumes[1][0];
			int    idx   = CurrentBars[1];

			double askQ = BarsArray[1].GetAsk(idx);
			double bidQ = BarsArray[1].GetBid(idx);

			int  side = 0;
			if (askQ > 0 && bidQ > 0 && askQ >= bidQ)
			{
				if      (price >= askQ) side =  1;
				else if (price <= bidQ) side = -1;
			}
			if (side == 0)
			{
				if (!double.IsNaN(lastTickPrice))
				{
					if      (price > lastTickPrice) side =  1;
					else if (price < lastTickPrice) side = -1;
					else                            side = lastTickDir;
				}
				if (side == 0) side = 1;
			}
			lastTickPrice = price;
			lastTickDir   = side;

			long tick = PriceToTick(price);
			long volInt = (long)Math.Round(vol * 100.0);
			Dictionary<long, double> map = side > 0 ? pendingAsk : pendingBid;
			double cur;
			map[tick] = map.TryGetValue(tick, out cur) ? cur + vol : vol;
			pendingVol += vol;
			if (seqFirst < 0) seqFirst = idx;
			seqLast = idx;
			nEvents++;

			digestStream = Mix(digestStream, tick);
			digestStream = Mix(digestStream, volInt);

			if (log != null && InWindow())
			{
				log.WriteLine(string.Format(inv,
					"E,{0},{1},{2},{3},{4},{5},{6},,,,,,,",
					idx, Times[1][0].Ticks,
					Times[1][0].ToString("yyyy-MM-ddTHH:mm:ss.fffffff", inv),
					tick, volInt, sessionIdx, digestStream));
			}
		}

		#region Properties
		[NinjaScriptProperty]
		[System.ComponentModel.DisplayName("Barras de warm-up a descartar")]
		public int SkipBars { get; set; }

		[NinjaScriptProperty]
		[System.ComponentModel.DisplayName("Barras a registrar")]
		public int MaxBars { get; set; }

		[NinjaScriptProperty]
		[System.ComponentModel.DisplayName("Ruta del CSV (SE SOBREESCRIBE)")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
