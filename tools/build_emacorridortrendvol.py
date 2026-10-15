import io,re
SRC=r'C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\EmaCorridorTrend.cs'
DST=r'C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\EmaCorridorTrendVol.cs'
s=open(SRC,encoding='utf-8-sig').read()
T='\t'
# 0. quitar la region generada (NT8 la regenera al compilar) y renombrar
i=s.index('#region NinjaScript generated code')
s=s[:i].rstrip()+'\n'
def rep(old,new):
    global s
    assert old in s, old[:60]
    s=s.replace(old,new,1)
rep('using NinjaTrader.Gui;','using NinjaTrader.Data;\nusing NinjaTrader.Gui;')
rep('public class EmaCorridorTrend : Indicator','public class EmaCorridorTrendVol : Indicator')
rep('Name              = "EmaCorridorTrend";','Name              = "EmaCorridorTrendVol";')
rep('Description       = "v4.0 — Detecta y enmarca','Description       = "v4.0-VOL — Variante con prueba de volumen de sector. Detecta y enmarca')
hdr='''// EmaCorridorTrendVol.cs — VARIANTE de EmaCorridorTrend v4.0 con PRUEBA DE VOLUMEN DE SECTOR (2026-10-15).
//
// QUE AGREGA (el detector de zonas es identico al original):
//   Para cada zona terminada se define un SECTOR de evaluacion en el eje de PRECIO y de TIEMPO:
//     - precio: el ULTIMO TailPct % del ALTO del rectangulo de la zona (por defecto 25 %) + los BeyondPct % SIGUIENTES de ese alto, MAS ALLA
//       del extremo en la direccion de la tendencia (por defecto 25 %). En una suba: [max - 25 % del alto, max + 25 % del alto];
//       en una baja: [min - 25 % del alto, min + 25 % del alto];
//     - tiempo: desde el FINAL del rectangulo hasta una distancia igual a su ancho (ForwardWidthPct = 100 %).
//   Se mide el VOLUMEN OPERADO dentro de ese sector (ticks con tiempo y precio dentro del rectangulo), con una serie extra de 1 tick.
//   La zona se MARCA si su volumen de sector es MAYOR al percentil VolPercentile (por defecto 90) de los volumenes de ese mismo sector
//   en las LookbackZones zonas anteriores (por defecto 50), exigiendo al menos MinPriorZones zonas previas (por defecto 20).
//
// CAUSALIDAD: una zona se sabe terminada recien cuando la tendencia se rompe, y el sector se extiende un ancho de zona hacia adelante;
//   la evaluacion se hace cuando cerro la barra SIGUIENTE al final del sector, usando solo ticks con tiempo <= esa barra. La marca llega
//   TARDE respecto del fin de la zona: sirve para clasificar y para medir lo que viene despues, no como senal de entrada en el fin.
// SALIDAS: plot VolFlag = +1/-1 (direccion de la zona) en la barra en que se evalua una zona marcada; 0 en el resto.
'''
s=hdr+s
rep(T+T+'private SMA rangeAvg;\n', T+T+'private SMA rangeAvg;\n'+'''
		// --- Volumen de sector (variante) ---
		private class PendingZone
		{
			public int    Dir;
			public int    OriginBar;
			public int    EndBar;
			public int    SecStartBar;
			public int    SecEndBar;
			public double Lo;
			public double Hi;
			public string Tag;
		}
		private List<DateTime>    tkTime;
		private List<double>      tkPx;
		private List<double>      tkVol;
		private List<PendingZone> pending;
		private List<double>      volHist;
		private int               ticksSincePurge;
''')
rep('''				UpTrendBrush       = Brushes.DodgerBlue;
				DownTrendBrush     = Brushes.Crimson;
''','''				UpTrendBrush       = Brushes.DodgerBlue;
				DownTrendBrush     = Brushes.Crimson;

				// 5. Volumen de sector
				TailPct            = 25;
				BeyondPct          = 25;
				ForwardWidthPct    = 100;
				LookbackZones      = 50;
				MinPriorZones      = 20;
				VolPercentile      = 90;
				KeepTickBars       = 1500;
				DrawSector         = true;
				FlagBrush          = Brushes.Gold;
				NoFlagBrush        = Brushes.Gray;
''')
rep('''				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "StabilityScore");
			}
			else if (State == State.DataLoaded)
			{''','''				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "StabilityScore");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "VolFlag");
			}
			else if (State == State.Configure)
			{
				AddDataSeries(BarsPeriodType.Tick, 1);      // subserie de 1 tick para el volumen por precio
			}
			else if (State == State.DataLoaded)
			{
				tkTime = new List<DateTime>(1 << 20);
				tkPx   = new List<double>(1 << 20);
				tkVol  = new List<double>(1 << 20);
				pending = new List<PendingZone>();
				volHist = new List<double>();
				ticksSincePurge = 0;
''')
rep('''		protected override void OnBarUpdate()
		{
			for (int i = 0; i < 5; i++)
				Values[i][0] = 0.0;
''','''		protected override void OnBarUpdate()
		{
			if (BarsInProgress == 1)
			{
				StoreTick();
				return;
			}
			if (BarsInProgress != 0)
				return;

			for (int i = 0; i < 6; i++)
				Values[i][0] = 0.0;

			ProcessPendingZones();
''')
rep('''					DrawZoneCorridor(activeDir);
					lastZoneEndBar = Math.Max(lastZoneEndBar, bestExtremeBar);
				}''','''					DrawZoneCorridor(activeDir);
					lastZoneEndBar = Math.Max(lastZoneEndBar, bestExtremeBar);
					RegisterZone(activeDir, originBar, bestExtremeBar, curTagPrefix);
				}''')
methods=r'''		// ===================== VOLUMEN DE SECTOR (variante) =====================

		private void StoreTick()
		{
			tkTime.Add(Times[1][0]);
			tkPx.Add(Closes[1][0]);
			tkVol.Add(Volumes[1][0]);
			ticksSincePurge++;
			if (ticksSincePurge >= 20000 && CurrentBars[0] > KeepTickBars)
			{
				ticksSincePurge = 0;
				DateTime keepFrom = Times[0][KeepTickBars];
				int cut = UpperBound(keepFrom.AddTicks(-1));
				if (cut > 0)
				{
					tkTime.RemoveRange(0, cut);
					tkPx.RemoveRange(0, cut);
					tkVol.RemoveRange(0, cut);
				}
			}
		}

		// Primer indice cuyo tiempo es estrictamente mayor que t (busqueda binaria; tkTime esta ordenado)
		private int UpperBound(DateTime t)
		{
			int lo = 0, hi = tkTime.Count;
			while (lo < hi)
			{
				int mid = (lo + hi) >> 1;
				if (tkTime[mid] <= t) lo = mid + 1; else hi = mid;
			}
			return lo;
		}

		// Rectangulo de la zona (mismos limites que DrawZoneCorridor): fin de barra, maximo y minimo de precio entre origen y fin
		private bool ComputeBoxAtEnd(int origin, int endBarRaw, out int endBar, out double minLo, out double maxHi)
		{
			minLo = 1e18; maxHi = -1e18;
			endBar = Math.Max(origin + 15, endBarRaw);
			if (endBar > CurrentBar)
				endBar = CurrentBar;
			int nSpan = endBar - origin + 1;
			if (nSpan < 10)
				return false;
			for (int k = 0; k < nSpan; k++)
			{
				int ago = CurrentBar - (origin + k);
				if (High[ago] > maxHi) maxHi = High[ago];
				if (Low[ago]  < minLo) minLo = Low[ago];
			}
			return maxHi > minLo;
		}

		private void RegisterZone(int dir, int origin, int endBarRaw, string tag)
		{
			int endBar;
			double boxLo, boxHi;
			if (!ComputeBoxAtEnd(origin, endBarRaw, out endBar, out boxLo, out boxHi))
				return;

			double height  = boxHi - boxLo;
			int    width   = endBar - origin + 1;
			double tailH   = TailPct   / 100.0 * height;      // ultimo TailPct % del alto, del lado del extremo de la tendencia
			double beyondH = BeyondPct / 100.0 * height;      // BeyondPct % mas alla del extremo
			double lo, hi;
			if (dir > 0)
			{
				lo = boxHi - tailH;
				hi = boxHi + beyondH;
			}
			else
			{
				lo = boxLo - beyondH;
				hi = boxLo + tailH;
			}
			int fwd = Math.Max(1, (int)Math.Round(ForwardWidthPct / 100.0 * width));

			PendingZone z = new PendingZone();
			z.Dir         = dir;
			z.OriginBar   = origin;
			z.EndBar      = endBar;
			z.SecStartBar = endBar + 1;                      // desde el borde derecho del rectangulo
			z.SecEndBar   = endBar + fwd;                    // hasta una distancia igual a su ancho
			z.Lo          = lo;
			z.Hi          = hi;
			z.Tag         = tag;
			pending.Add(z);
		}

		// Suma el volumen de los ticks con tiempo dentro de las barras [startBar, endBar] y precio dentro de [lo, hi]
		private double SectorVolume(int startBar, int endBar, double lo, double hi)
		{
			DateTime t0  = startBar > 0 ? Time[CurrentBar - (startBar - 1)] : DateTime.MinValue;
			DateTime t1  = Time[CurrentBar - endBar];
			double   eps = TickSize * 0.01;
			double   vol = 0.0;
			for (int i = UpperBound(t0); i < tkTime.Count; i++)
			{
				if (tkTime[i] > t1)
					break;
				double p = tkPx[i];
				if (p >= lo - eps && p <= hi + eps)
					vol += tkVol[i];
			}
			return vol;
		}

		// Evalua cada zona pendiente cuando ya cerro la barra SIGUIENTE al final de su sector (asi estan todos sus ticks)
		private void ProcessPendingZones()
		{
			for (int pi = pending.Count - 1; pi >= 0; pi--)
			{
				PendingZone z = pending[pi];
				if (CurrentBar < z.SecEndBar + 1)
					continue;

				pending.RemoveAt(pi);

				double vol = SectorVolume(z.SecStartBar, z.SecEndBar, z.Lo, z.Hi);

				// Percentil (rango por vecino mas cercano) sobre las LookbackZones zonas anteriores
				int    n       = Math.Min(LookbackZones, volHist.Count);
				bool   flagged = false;
				double thr     = 0.0;
				if (n >= MinPriorZones && n > 0)
				{
					List<double> prev = volHist.GetRange(volHist.Count - n, n);
					prev.Sort();
					int rank = (int)Math.Ceiling(VolPercentile / 100.0 * n) - 1;
					rank     = Math.Min(n - 1, Math.Max(0, rank));
					thr      = prev[rank];
					flagged  = vol > thr;
				}
				volHist.Add(vol);

				if (flagged)
					Values[5][0] = z.Dir;

				if (DrawSector)
				{
					int startAgo = CurrentBar - z.SecStartBar;
					int endAgo   = CurrentBar - z.SecEndBar;
					if (startAgo > endAgo && endAgo >= 0)
					{
						Brush br = flagged ? FlagBrush : NoFlagBrush;
						Draw.Rectangle(this, z.Tag + "SECTOR", false, startAgo, z.Hi, endAgo, z.Lo, br, Brushes.Transparent, 0);
						if (flagged)
							Draw.Text(this, z.Tag + "VOLTXT", "Vol>P" + VolPercentile.ToString(CultureInfo.InvariantCulture) + "  " + vol.ToString("N0", CultureInfo.InvariantCulture)
								+ " (umbral " + thr.ToString("N0", CultureInfo.InvariantCulture) + ")", endAgo, z.Hi + 2 * TickSize, br);
					}
				}
			}
		}

'''
anchor='\t\t#region Plot Series Accessors'
rep(anchor,methods+anchor)
rep('''		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Peaks { get { return Values[4]; } }''','''		[Browsable(false)]
		[XmlIgnore]
		public Series<double> Peaks { get { return Values[4]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> VolFlag { get { return Values[5]; } }''')
props='''		[NinjaScriptProperty] [Range(1, 100)]
		[Display(Name = "Tail % del ALTO de la zona (lado del extremo)", Order = 1, GroupName = "5. Volumen de sector",
			Description = "Ultimo porcentaje del alto del rectangulo de la zona, del lado del extremo de la tendencia, que entra al sector (25 = ultimo cuarto).")]
		public int TailPct { get; set; }

		[NinjaScriptProperty] [Range(0, 200)]
		[Display(Name = "Beyond % del ALTO mas alla del extremo", Order = 2, GroupName = "5. Volumen de sector",
			Description = "Porcentaje del alto del rectangulo que se agrega MAS ALLA del extremo, en la direccion de la tendencia (0 = solo el tramo final).")]
		public int BeyondPct { get; set; }

		[NinjaScriptProperty] [Range(10, 400)]
		[Display(Name = "Ancho hacia adelante % del ancho de la zona", Order = 2, GroupName = "5. Volumen de sector",
			Description = "Desde el final del rectangulo hasta esta distancia, en % del ancho del rectangulo (100 = igual al rectangulo).")]
		public int ForwardWidthPct { get; set; }

		[NinjaScriptProperty] [Range(5, 500)]
		[Display(Name = "Zonas anteriores a comparar", Order = 3, GroupName = "5. Volumen de sector")]
		public int LookbackZones { get; set; }

		[NinjaScriptProperty] [Range(1, 500)]
		[Display(Name = "Minimo de zonas previas para marcar", Order = 4, GroupName = "5. Volumen de sector")]
		public int MinPriorZones { get; set; }

		[NinjaScriptProperty] [Range(1, 99)]
		[Display(Name = "Percentil de volumen", Order = 5, GroupName = "5. Volumen de sector",
			Description = "La zona se marca si su volumen de sector es MAYOR a este percentil de las zonas anteriores.")]
		public int VolPercentile { get; set; }

		[NinjaScriptProperty] [Range(200, 100000)]
		[Display(Name = "Barras de ticks que se conservan", Order = 6, GroupName = "5. Volumen de sector",
			Description = "Memoria: los ticks mas viejos que estas barras primarias se descartan.")]
		public int KeepTickBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dibujar sector", Order = 7, GroupName = "5. Volumen de sector")]
		public bool DrawSector { get; set; }

		[XmlIgnore]
		[Display(Name = "Color zona marcada", Order = 8, GroupName = "5. Volumen de sector")]
		public Brush FlagBrush { get; set; }
		[Browsable(false)]
		public string FlagBrushSerialize
		{
			get { return Serialize.BrushToString(FlagBrush); }
			set { FlagBrush = Serialize.StringToBrush(value); }
		}

		[XmlIgnore]
		[Display(Name = "Color zona no marcada", Order = 9, GroupName = "5. Volumen de sector")]
		public Brush NoFlagBrush { get; set; }
		[Browsable(false)]
		public string NoFlagBrushSerialize
		{
			get { return Serialize.BrushToString(NoFlagBrush); }
			set { NoFlagBrush = Serialize.StringToBrush(value); }
		}
'''
i=s.rindex('\t\t#endregion')
s=s[:i]+props+'\t\t#endregion'+s[i+len('\t\t#endregion'):]
open(DST,'w',encoding='utf-8-sig',newline='').write(s)
print('ok',len(s))
