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

// AVolZoneSimple v1.0 -- zonas de volumen con UNA definicion, estable y barrible.
//
// Espejo exacto de edgelab/bridge/indicators/avolzonesimple.py.
//
// DEFINICION, toda la logica en una linea:
//   la zona es el rango de precios MAS ANGOSTO que concentra S% del volumen del
//   bloque, y se publica solo si su concentracion supera un umbral.
//
// QUE REEMPLAZA (aVolClusterPOI v0.5) Y POR QUE
//   Medido sobre los 22.507 bloques reales de NQ 06-26 120t:
//     - el 89,60% de los bloques tenia una celda a UN contrato del umbral
//       mediana*2, asi que un contrato de diferencia contra el parquet cambiaba
//       la zona;
//     - turnover de la geometria bajo ruido de +-1 contrato: 30,87%. Ninguna
//       variante de la regla de seleccion bajaba del 22%;
//     - esta definicion da 4,97% con los defaults, y conserva la altura mediana
//       de zona: 9 ticks contra 9 de la regla vieja.
//   La razon es estructural: un umbral sobre celdas individuales tiene un borde
//   que un contrato cruza; una SUMA sobre muchas celdas no lo tiene.
//
// QUE SE ELIMINO
//   - mediana y multiplicador: no hay umbral por celda;
//   - clustering por gap: la zona es un intervalo contiguo por construccion, no
//     puede fusionarse ni partirse por una celda marginal;
//   - percentil historico por franja horaria y sesion: era estado acumulado
//     entre bloques y sesiones, y es la causa de que el indicador marcara muchas
//     zonas en un momento y ninguna en otro sin que el mercado cambiara. Lo
//     reemplaza un umbral FIJO y declarado de concentracion.
//   Sin estado historico, cada bloque se decide solo: reproducible barra a barra
//   y barrible con cuatro parametros enteros y monotonos.
//
// ARITMETICA, entera y sin floats en la decision:
//   necesario     = techo(volumen_bloque * SharePct / 100)
//   concentracion = volumen_zona * ancho_bloque * 1000 / (volumen_bloque * ancho_zona)
//   concentracion == 1000 es "tan concentrada como el reparto uniforme"; 2000 el doble.
//
// EMPATES: menor ancho gana; si empatan, mayor volumen; si empatan, precio
// ascendente. Determinista, sin depender del orden de un diccionario.

namespace NinjaTrader.NinjaScript.Indicators
{
	public class AVolZoneSimple : Indicator
	{
		private Dictionary<long, long> _barProfile;    // perfil de la barra en curso
		private Dictionary<long, long> _blockCells;    // perfil acumulado del bloque
		private int _barsInBlock;
		private int _sessionIndex = -1;
		private long _blockSeq;
		private long _zoneSeq;
		private StreamWriter _log;
		private bool _logFailed;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "AVolZoneSimple";
				Description = "Zona de volumen: rango mas angosto que concentra S% del bloque";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = false;

				BarsPerBlock = 10;
				AreaSharePct = 30;
				MaxZoneTicks = 12;
				MinConcentration = 1500;
				ZoneOpacity = 30;
				SupportColor = Brushes.MediumSeaGreen;
				ResistanceColor = Brushes.IndianRed;
				AtPriceColor = Brushes.SteelBlue;
				EventLogPath = "";
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);   // perfil intrabarra
			}
			else if (State == State.DataLoaded)
			{
				_barProfile = new Dictionary<long, long>();
				_blockCells = new Dictionary<long, long>();
				OpenLog();
			}
			else if (State == State.Terminated)
			{
				if (_log != null) { try { _log.Flush(); _log.Close(); } catch { } _log = null; }
			}
		}

		private void OpenLog()
		{
			if (string.IsNullOrWhiteSpace(EventLogPath)) return;
			try
			{
				string dir = Path.GetDirectoryName(EventLogPath);
				if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
				_log = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
				_log.AutoFlush = true;
				_log.WriteLine("# meta,indicator=AVolZoneSimple,version=1.0"
					+ ",instrument=" + Instrument.FullName
					+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
					+ ",bars_per_block=" + BarsPerBlock
					+ ",area_share_pct=" + AreaSharePct
					+ ",max_zone_ticks=" + MaxZoneTicks
					+ ",min_concentration=" + MinConcentration
					+ ",stateless=true,history=none,write_mode=overwrite");
				_log.WriteLine("block_seq,bar_index,bar_close_time_utc,session_index,decision,"
					+ "lower_tick,upper_tick,zone_ticks,zone_volume,block_volume,block_ticks,"
					+ "concentration,side,distance_ticks,close_tick,cells");
			}
			catch { _log = null; _logFailed = true; }
		}

		private long PriceToTick(double price)
		{
			return (long)Math.Round(price / TickSize, MidpointRounding.AwayFromZero);
		}

		protected override void OnBarUpdate()
		{
			// --- subserie de 1 tick: acumula el perfil de la barra en curso ---
			if (BarsInProgress == 1)
			{
				long v = (long)Volumes[1][0];
				if (v <= 0) return;
				long t = PriceToTick(Closes[1][0]);
				long cur;
				if (_barProfile.TryGetValue(t, out cur)) _barProfile[t] = cur + v;
				else _barProfile[t] = v;
				return;
			}

			if (BarsInProgress != 0 || CurrentBar < 0) return;

			// --- frontera de sesion: el bloque no cruza sesiones ---
			if (Bars.IsFirstBarOfSession)
			{
				_sessionIndex++;
				_blockCells.Clear();
				_barsInBlock = 0;
			}

			// --- volcado del perfil de la barra al bloque ---
			// SIN filtro Low/High: descartar sin reasignar perdia volumen (0,41%
			// medido) y no aportaba nada. Si el perfil trae un tick fuera del
			// rango de la barra, entra igual: la suma del bloque es lo que decide.
			foreach (KeyValuePair<long, long> kv in _barProfile)
			{
				long cur;
				if (_blockCells.TryGetValue(kv.Key, out cur)) _blockCells[kv.Key] = cur + kv.Value;
				else _blockCells[kv.Key] = kv.Value;
			}
			_barProfile.Clear();
			_barsInBlock++;

			if (_barsInBlock < BarsPerBlock) return;

			ProcessBlock();
			_blockCells.Clear();
			_barsInBlock = 0;
		}

		private void ProcessBlock()
		{
			_blockSeq++;
			long closeTick = PriceToTick(Close[0]);

			string decision = "ABSTAIN_NO_CELLS";
			long lower = 0, upper = 0, zoneVol = 0, blockVol = 0, conc = 0;
			int zoneTicks = 0, blockTicks = 0, distance = 0;
			string side = "";

			if (_blockCells.Count >= 2)
			{
				List<long> ticks = new List<long>(_blockCells.Keys);
				ticks.Sort();
				int n = ticks.Count;

				long[] pre = new long[n + 1];
				for (int i = 0; i < n; i++) pre[i + 1] = pre[i] + _blockCells[ticks[i]];
				blockVol = pre[n];
				blockTicks = (int)(ticks[n - 1] - ticks[0] + 1);

				// techo entero de blockVol * SharePct / 100
				long need = (blockVol * AreaSharePct + 99L) / 100L;

				bool found = false;
				int bw = 0; long bvol = 0; long blo = 0, bhi = 0;
				int j = 0;
				for (int i = 0; i < n; i++)
				{
					if (j < i) j = i;
					while (j < n && pre[j + 1] - pre[i] < need) j++;
					if (j >= n) break;
					int w = (int)(ticks[j] - ticks[i] + 1);
					if (w > MaxZoneTicks) continue;
					long v = pre[j + 1] - pre[i];
					// empates: menor ancho, luego mayor volumen, luego precio ascendente
					if (!found || w < bw || (w == bw && v > bvol))
					{
						found = true; bw = w; bvol = v; blo = ticks[i]; bhi = ticks[j];
					}
				}

				if (!found) decision = "ABSTAIN_TOO_WIDE";
				else
				{
					lower = blo; upper = bhi; zoneVol = bvol; zoneTicks = bw;
					conc = (blockVol > 0 && zoneTicks > 0)
						? (zoneVol * blockTicks * 1000L) / (blockVol * zoneTicks) : 0L;
					if (conc < MinConcentration) decision = "ABSTAIN_LOW_CONCENTRATION";
					else
					{
						decision = "CREATE";
						if (closeTick > upper) { side = "SUPPORT"; distance = (int)(closeTick - upper); }
						else if (closeTick < lower) { side = "RESISTANCE"; distance = (int)(lower - closeTick); }
						else { side = "AT_PRICE"; distance = 0; }
						DrawZone(lower, upper, side);
					}
				}
			}

			WriteRow(decision, lower, upper, zoneTicks, zoneVol, blockVol, blockTicks,
				conc, side, distance, closeTick);
		}

		private void DrawZone(long lower, long upper, string side)
		{
			_zoneSeq++;
			Brush b = side == "SUPPORT" ? SupportColor
				: side == "RESISTANCE" ? ResistanceColor : AtPriceColor;
			Draw.Rectangle(this, "avzs" + _zoneSeq, false,
				BarsPerBlock - 1, (lower - 0.5) * TickSize, 0, (upper + 0.5) * TickSize,
				Brushes.Transparent, b, ZoneOpacity);
		}

		private void WriteRow(string decision, long lower, long upper, int zoneTicks,
			long zoneVol, long blockVol, int blockTicks, long conc, string side,
			int distance, long closeTick)
		{
			if (_log == null || _logFailed) return;
			try
			{
				// perfil crudo del bloque: hace la decision reproducible sin el tick data
				List<long> ks = new List<long>(_blockCells.Keys);
				ks.Sort();
				StringBuilder sb = new StringBuilder();
				for (int i = 0; i < ks.Count; i++)
				{
					if (i > 0) sb.Append('|');
					sb.Append(ks[i]).Append(':').Append(_blockCells[ks[i]]);
				}
				_log.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}",
					_blockSeq, CurrentBar,
					Time[0].ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					_sessionIndex, decision,
					decision == "CREATE" || decision == "ABSTAIN_LOW_CONCENTRATION" ? lower.ToString(CultureInfo.InvariantCulture) : "",
					decision == "CREATE" || decision == "ABSTAIN_LOW_CONCENTRATION" ? upper.ToString(CultureInfo.InvariantCulture) : "",
					zoneTicks, zoneVol, blockVol, blockTicks, conc, side, distance, closeTick,
					sb.ToString()));
			}
			catch (Exception ex)
			{
				_logFailed = true;
				Print(Name + " ERROR [event_log]: " + ex.Message);
			}
		}

		#region Properties
		[NinjaScriptProperty] [Range(2, 500)]
		[Display(Name = "Bars Per Block", Order = 1, GroupName = "1. Zona",
			Description = "Barras primarias que forman un bloque.")]
		public int BarsPerBlock { get; set; }

		[NinjaScriptProperty] [Range(1, 99)]
		[Display(Name = "Area Share %", Order = 2, GroupName = "1. Zona",
			Description = "Porcentaje del volumen del bloque que la zona debe concentrar. "
				+ "Mas alto = zona mas ancha y mas estable.")]
		public int AreaSharePct { get; set; }

		[NinjaScriptProperty] [Range(1, 1000)]
		[Display(Name = "Max Zone Ticks", Order = 3, GroupName = "1. Zona",
			Description = "Ancho maximo admitido. Si ningun rango de ese ancho alcanza el "
				+ "porcentaje, el bloque se abstiene (ABSTAIN_TOO_WIDE).")]
		public int MaxZoneTicks { get; set; }

		[NinjaScriptProperty] [Range(1000, 20000)]
		[Display(Name = "Min Concentration", Order = 4, GroupName = "1. Zona",
			Description = "1000 = tan concentrada como el reparto uniforme del bloque; "
				+ "1500 = 1,5x. Reemplaza al percentil historico: es fijo, declarado y "
				+ "sin estado entre bloques ni sesiones.")]
		public int MinConcentration { get; set; }

		[XmlIgnore] [Display(Name = "Support Color", Order = 10, GroupName = "2. Visual")]
		public Brush SupportColor { get; set; }
		[Browsable(false)]
		public string SupportColorSerialize
		{
			get { return Serialize.BrushToString(SupportColor); }
			set { SupportColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "Resistance Color", Order = 11, GroupName = "2. Visual")]
		public Brush ResistanceColor { get; set; }
		[Browsable(false)]
		public string ResistanceColorSerialize
		{
			get { return Serialize.BrushToString(ResistanceColor); }
			set { ResistanceColor = Serialize.StringToBrush(value); }
		}

		[XmlIgnore] [Display(Name = "At Price Color", Order = 12, GroupName = "2. Visual")]
		public Brush AtPriceColor { get; set; }
		[Browsable(false)]
		public string AtPriceColorSerialize
		{
			get { return Serialize.BrushToString(AtPriceColor); }
			set { AtPriceColor = Serialize.StringToBrush(value); }
		}

		[NinjaScriptProperty] [Range(0, 100)]
		[Display(Name = "Zone Opacity", Order = 13, GroupName = "2. Visual")]
		public int ZoneOpacity { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Event Log Path (vacio = off)", Order = 20, GroupName = "3. Auditoria",
			Description = "CSV con 1 fila por bloque, CREATE y ABSTAIN, incluyendo el perfil "
				+ "crudo. Con eso la decision se reproduce en Python sin el tick data.")]
		public string EventLogPath { get; set; }
		#endregion
	}
}
