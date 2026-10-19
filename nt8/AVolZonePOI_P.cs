#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// AVolZonePOI_P v1.0 -- zonas de concentracion de volumen, disenado para PARIDAD.
//
// Reemplaza a aVolClusterPOI, que resulto imposible de paritar: su umbral es
// "mediana de las ~66 celdas del bloque x 2", y un ruido de +-1 en el volumen
// por celda cambia el 66% de sus zonas (docs/research/avolcluster_sensitivity_20260902/).
//
// Cumple docs/research/PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md:
//   1. Aritmetica ENTERA en toda decision (volumen long, share en basis points).
//   2. Sin reloj entre ticks.
//   3. Sin mediana ni cuantil: seleccion por RANKING top-K y por CONTEO.
//   4. Empates rotos por precio ascendente, siempre.
//   5. Sin estado entre sesiones: el bloque se decide solo con sus propias celdas.
//   6. Un solo origen de footprint, sin filtros que descarten ticks en silencio.
//   7. Log completo por bloque (CREATE y ABSTAIN) con las celdas crudas.
//
// Por que es robusto a +-1 de ruido: "las K celdas de mayor volumen" solo cambia
// si el ruido cruza el orden entre la celda K y la K+1, y ese empate se rompe por
// precio de forma determinista. No hay un umbral continuo que un +-1 pueda cruzar.

namespace NinjaTrader.NinjaScript.Indicators
{
	public class AVolZonePOI_P : Indicator
	{
		// ---- estado del bloque en curso (sin estado entre sesiones) ----
		private Dictionary<long, long> _blockCells;   // tick de precio -> volumen entero
		private Dictionary<long, long> _barCells;     // acumulador de la barra en formacion
		private int _barsInBlock;
		private int _blockIndex;
		private int _sessionIndex = -1;
		private DateTime _sessionBegin = DateTime.MinValue;
		private SessionIterator _sessIter;
		private StreamWriter _log;
		private int _zoneSeq;
		private readonly List<Zone> _zones = new List<Zone>();

		private class Zone
		{
			public int Id;
			public long LowerTick, UpperTick, Volume;
			public int Direction;        // +1 soporte (debajo del cierre), -1 resistencia
			public DateTime Created;
			public bool Active = true;
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "AVolZonePOI_P";
				Description = "Zonas de concentracion de volumen con seleccion entera (paridad primero)";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				BarsPerBlock = 10;      // barras primarias por bloque
				TopKCells = 8;          // celdas de mayor volumen consideradas
				MaxGapTicks = 1;        // huecos permitidos al agrupar celdas contiguas
				MinClusterCells = 2;    // celdas minimas del cluster
				MinShareBps = 1200;     // volumen del cluster >= 12,00 % del bloque
				MinBlockCells = 3;      // celdas minimas para evaluar el bloque
				ZoneColor = Brushes.SteelBlue;
				ZoneOpacity = 30;
				EventLogPath = "";
			}
			else if (State == State.Configure)
			{
				// UNICO origen de footprint: subserie de 1 tick, sin filtros de descarte
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				_blockCells = new Dictionary<long, long>();
				_barCells = new Dictionary<long, long>();
				_sessIter = new SessionIterator(BarsArray[0]);
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { _log.Flush(); _log.Dispose(); _log = null; }
			}
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				_log = new StreamWriter(EventLogPath, false, Encoding.UTF8);
				_log.WriteLine("# meta,indicator=AVolZonePOI_P,version=1.0,contract=parity_first_v1"
					+ ",bars_per_block=" + BarsPerBlock + ",top_k=" + TopKCells
					+ ",max_gap_ticks=" + MaxGapTicks + ",min_cluster_cells=" + MinClusterCells
					+ ",min_share_bps=" + MinShareBps + ",min_block_cells=" + MinBlockCells
					+ ",cells_format=tick:vol pipe-separated sorted by tick asc");
				_log.WriteLine("block_index,bar_close_time_utc,session_index,n_cells,block_volume,"
					+ "decision,sel_lower_tick,sel_upper_tick,sel_volume,sel_cells,share_bps,close_tick,cells");
			}
			catch { _log = null; }
		}

		private long PriceToTick(double price)
		{
			// entero, redondeo half-away-from-zero explicito: no depende del modo de FPU
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		protected override void OnBarUpdate()
		{
			// ---- subserie de 1 tick: acumula el footprint de la barra en formacion ----
			if (BarsInProgress == 1)
			{
				if (CurrentBars[1] < 0) return;
				long vol = (long)Volumes[1][0];
				if (vol <= 0) return;
				long tick = PriceToTick(Closes[1][0]);
				long cur;
				// REGLA 6: se acumula TODO tick. Ningun filtro de rango lo descarta.
				if (_barCells.TryGetValue(tick, out cur)) _barCells[tick] = cur + vol;
				else _barCells[tick] = vol;
				return;
			}

			if (BarsInProgress != 0) return;
			if (CurrentBar < 0) return;

			// ---- REGLA 5: reset explicito y declarado en el limite de sesion ----
			if (Bars.IsFirstBarOfSession)
			{
				_sessionIndex++;
				try { _sessIter.GetNextSession(Time[0], true); _sessionBegin = _sessIter.ActualSessionBegin; }
				catch { _sessionBegin = DateTime.MinValue; }
				_blockCells.Clear();
				_barsInBlock = 0;
				_blockIndex = 0;
				foreach (Zone z in _zones) z.Active = false;
				if (_log != null)
					_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
						"-1,{0},{1},0,0,SESSION_RESET,,,,,,,",
						Time[0].ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture),
						_sessionIndex));
			}

			// volcar la barra cerrada al bloque
			foreach (KeyValuePair<long, long> kv in _barCells)
			{
				long cur;
				if (_blockCells.TryGetValue(kv.Key, out cur)) _blockCells[kv.Key] = cur + kv.Value;
				else _blockCells[kv.Key] = kv.Value;
			}
			_barCells.Clear();
			_barsInBlock++;

			if (_barsInBlock < BarsPerBlock) return;

			EvaluateBlock();
			_blockCells.Clear();
			_barsInBlock = 0;
			_blockIndex++;
		}

		private void EvaluateBlock()
		{
			long closeTick = PriceToTick(Close[0]);
			long blockVolume = 0;
			foreach (long v in _blockCells.Values) blockVolume += v;

			string decision = "CREATE";
			long selLower = 0, selUpper = 0, selVol = 0, shareBps = 0;
			int selCells = 0;

			if (_blockCells.Count < MinBlockCells) decision = "ABSTAIN_FEW_CELLS";
			else
			{
				// ---- REGLA 3: ranking top-K, no umbral sobre estadistico ----
				// ---- REGLA 4: orden (volumen DESC, precio ASC) -> empate determinista
				List<long> ticks = new List<long>(_blockCells.Keys);
				ticks.Sort(delegate (long a, long b)
				{
					long va = _blockCells[a], vb = _blockCells[b];
					if (va != vb) return vb.CompareTo(va);   // mayor volumen primero
					return a.CompareTo(b);                   // empate: precio ascendente
				});
				int k = Math.Min(TopKCells, ticks.Count);
				List<long> hot = ticks.GetRange(0, k);
				hot.Sort();   // ahora por precio, para agrupar contiguos

				// agrupar celdas contiguas permitiendo huecos <= MaxGapTicks
				long bestLo = 0, bestUp = 0, bestVol = -1;
				int bestCells = 0;
				int i = 0;
				while (i < hot.Count)
				{
					int j = i;
					while (j + 1 < hot.Count && hot[j + 1] - hot[j] <= MaxGapTicks + 1) j++;
					int cells = j - i + 1;
					if (cells >= MinClusterCells)
					{
						long sum = 0;
						for (int q = i; q <= j; q++) sum += _blockCells[hot[q]];
						// mejor cluster: mayor volumen; empate -> precio inferior mas bajo
						if (sum > bestVol || (sum == bestVol && hot[i] < bestLo))
						{
							bestVol = sum; bestLo = hot[i]; bestUp = hot[j]; bestCells = cells;
						}
					}
					i = j + 1;
				}

				if (bestVol < 0) decision = "ABSTAIN_NO_CLUSTER";
				else
				{
					// ---- REGLA 1: proporcion en basis points ENTEROS, sin floats ----
					shareBps = blockVolume > 0 ? (bestVol * 10000L) / blockVolume : 0;
					if (shareBps < MinShareBps) decision = "ABSTAIN_BELOW_SHARE";
					else
					{
						selLower = bestLo; selUpper = bestUp; selVol = bestVol; selCells = bestCells;
					}
				}
			}

			if (decision == "CREATE")
			{
				_zoneSeq++;
				Zone z = new Zone
				{
					Id = _zoneSeq, LowerTick = selLower, UpperTick = selUpper, Volume = selVol,
					Direction = closeTick > selUpper ? 1 : (closeTick < selLower ? -1 : 0),
					Created = Time[0]
				};
				_zones.Add(z);
				Draw.Rectangle(this, "azp" + z.Id, false, Time[0], (selLower - 0.5) * TickSize,
					Time[0].AddMinutes(1), (selUpper + 0.5) * TickSize,
					Brushes.Transparent, ZoneColor, ZoneOpacity);
			}

			WriteBlockRow(decision, blockVolume, selLower, selUpper, selVol, selCells, shareBps, closeTick);
		}

		private void WriteBlockRow(string decision, long blockVolume, long lo, long up,
			long vol, int cells, long shareBps, long closeTick)
		{
			if (_log == null) return;
			// ---- REGLA 7: celdas crudas ordenadas por tick asc, para cruce celda a celda ----
			List<long> keys = new List<long>(_blockCells.Keys);
			keys.Sort();
			StringBuilder sb = new StringBuilder();
			for (int i = 0; i < keys.Count; i++)
			{
				if (i > 0) sb.Append('|');
				sb.Append(keys[i]).Append(':').Append(_blockCells[keys[i]]);
			}
			_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
				"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12}",
				_blockIndex,
				Time[0].ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss.fff", CultureInfo.InvariantCulture),
				_sessionIndex, _blockCells.Count, blockVolume, decision,
				decision == "CREATE" ? lo.ToString(CultureInfo.InvariantCulture) : "",
				decision == "CREATE" ? up.ToString(CultureInfo.InvariantCulture) : "",
				decision == "CREATE" ? vol.ToString(CultureInfo.InvariantCulture) : "",
				decision == "CREATE" ? cells.ToString(CultureInfo.InvariantCulture) : "",
				shareBps, closeTick, sb.ToString()));
			_log.Flush();
		}

		#region Properties
		[NinjaScriptProperty] [Range(2, 500)]
		[Display(Name = "BarsPerBlock", Order = 1, GroupName = "Bloque")]
		public int BarsPerBlock { get; set; }

		[NinjaScriptProperty] [Range(2, 200)]
		[Display(Name = "TopKCells", Order = 2, GroupName = "Deteccion")]
		public int TopKCells { get; set; }

		[NinjaScriptProperty] [Range(0, 20)]
		[Display(Name = "MaxGapTicks", Order = 3, GroupName = "Deteccion")]
		public int MaxGapTicks { get; set; }

		[NinjaScriptProperty] [Range(1, 100)]
		[Display(Name = "MinClusterCells", Order = 4, GroupName = "Deteccion")]
		public int MinClusterCells { get; set; }

		[NinjaScriptProperty] [Range(0, 10000)]
		[Display(Name = "MinShareBps", Description = "Volumen del cluster sobre el bloque, en basis points enteros",
			Order = 5, GroupName = "Deteccion")]
		public int MinShareBps { get; set; }

		[NinjaScriptProperty] [Range(1, 500)]
		[Display(Name = "MinBlockCells", Order = 6, GroupName = "Deteccion")]
		public int MinBlockCells { get; set; }

		[XmlIgnore] [Display(Name = "ZoneColor", Order = 7, GroupName = "Visual")]
		public Brush ZoneColor { get; set; }

		[Browsable(false)]
		public string ZoneColorSerialize
		{
			get { return Serialize.BrushToString(ZoneColor); }
			set { ZoneColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "ZoneOpacity", Order = 8, GroupName = "Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EventLogPath", Description = "CSV de bloques para el cruce de paridad",
			Order = 9, GroupName = "Auditoria")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
