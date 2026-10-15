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
//   Para cada zona terminada se define un SECTOR de evaluacion:
//     - ancho: el ULTIMO TailPct % de la zona (por defecto 25 %) + BeyondPct % de su ancho MAS ALLA del fin (por defecto 25 %);
//     - alto: la BANDA del canal en el extremo final de la zona, entre la tangente estructural (TL) y la banda de picos lejanos (FAR),
//       extendida en horizontal (son las dos lineas azules horizontales del ejemplo).
//   Se mide el VOLUMEN OPERADO dentro de ese sector (ticks con tiempo y precio dentro del rectangulo), con una serie extra de 1 tick.
//   La zona se MARCA si su volumen de sector es MAYOR al percentil VolPercentile (por defecto 90) de los volumenes de ese mismo sector
//   en las LookbackZones zonas anteriores (por defecto 50), exigiendo al menos MinPriorZones zonas previas (por defecto 20).
//
// CAUSALIDAD: una zona se sabe terminada recien cuando la tendencia se rompe, y el sector llega hasta BeyondPct % mas alla de su fin;
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

		// Misma regresion que DrawZoneCorridor: devuelve la banda de precio del canal (TL..FAR) en el extremo final de la zona
		private bool ComputeBandAtEnd(int dir, int origin, int endBarRaw, out int endBar, out double lo, out double hi)
		{
			lo = 0.0; hi = 0.0;
			endBar = Math.Max(origin + 15, endBarRaw);
			if (endBar > CurrentBar)
				endBar = CurrentBar;
			int nSpan = endBar - origin + 1;
			if (nSpan < 10)
				return false;

			double xMean = 0.5 * (nSpan - 1);
			double ySum  = 0.0;
			for (int k = 0; k < nSpan; k++)
			{
				int ago = CurrentBar - (origin + k);
				ySum += 0.5 * (High[ago] + Low[ago]);
			}
			double yMean = ySum / nSpan;
			double sxx = 0.0, sxy = 0.0;
			for (int k = 0; k < nSpan; k++)
			{
				int    ago = CurrentBar - (origin + k);
				double dx  = k - xMean;
				double dy  = 0.5 * (High[ago] + Low[ago]) - yMean;
				sxx += dx * dx;
				sxy += dx * dy;
			}
			double slope     = sxx > 1e-12 ? sxy / sxx : 0.0;
			double intercept = yMean - slope * xMean;

			List<double> upRes = new List<double>(nSpan);
			List<double> dnRes = new List<double>(nSpan);
			for (int k = 0; k < nSpan; k++)
			{
				int    ago = CurrentBar - (origin + k);
				double reg = intercept + slope * k;
				upRes.Add(High[ago] - reg);
				dnRes.Add(reg - Low[ago]);
			}
			upRes.Sort();
			dnRes.Sort();
			int    idx90 = Math.Min(nSpan - 1, Math.Max(0, (int)Math.Round(0.90 * (nSpan - 1))));
			double upOff = Math.Max(TickSize, upRes[idx90]);
			double dnOff = Math.Max(TickSize, dnRes[idx90]);
			double yEnd  = intercept + slope * (nSpan - 1);

			// Banda entre la tangente (lado de los pullbacks) y la banda de picos lejanos, en el extremo final
			double a = yEnd + upOff;
			double b = yEnd - dnOff;
			lo = Math.Min(a, b);
			hi = Math.Max(a, b);
			return true;
		}

		private void RegisterZone(int dir, int origin, int endBarRaw, string tag)
		{
			int endBar;
			double lo, hi;
			if (!ComputeBandAtEnd(dir, origin, endBarRaw, out endBar, out lo, out hi))
				return;

			int width  = endBar - origin + 1;
			int tail   = Math.Max(1, (int)Math.Round(TailPct / 100.0 * width));
			int beyond = Math.Max(0, (int)Math.Round(BeyondPct / 100.0 * width));

			PendingZone z = new PendingZone();
			z.Dir         = dir;
			z.OriginBar   = origin;
			z.EndBar      = endBar;
			z.SecStartBar = Math.Max(origin, endBar - tail + 1);
			z.SecEndBar   = endBar + beyond;
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
		[Display(Name = "Tail % de la zona (final)", Order = 1, GroupName = "5. Volumen de sector",
			Description = "Porcentaje final del ancho de la zona que entra al sector de evaluacion (25 = ultimo cuarto).")]
		public int TailPct { get; set; }

		[NinjaScriptProperty] [Range(0, 200)]
		[Display(Name = "Beyond % mas alla del fin", Order = 2, GroupName = "5. Volumen de sector",
			Description = "Porcentaje del ancho de la zona que se agrega DESPUES del fin (0 = solo el tramo final de la zona).")]
		public int BeyondPct { get; set; }

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
