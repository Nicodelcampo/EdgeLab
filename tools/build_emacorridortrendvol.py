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
// ANCLAS (puntos de referencia dentro del sector, 3 en total; se calculan con el perfil de volumen por precio del sector):
//   1. POC del sector: el precio con mas volumen operado (nivel de mayor aceptacion).
//   2. Borde del Area de Valor (70 %) del lado del INTERIOR de la zona: VAL en una suba, VAH en una baja (el borde mas cercano al
//      camino por el que volveria el precio a lo largo del corredor).
//   3. Barra de maximo volumen del sector (vela tipo VolTicksDef): punto medio de su rango (parametro HvBarUseClose para usar el cierre).
//   Se dibujan como lineas horizontales desde el inicio del sector hasta AnchorLifeBars barras despues de evaluar, y se exponen en los
//   plots AnchorPOC, AnchorVAEdge y AnchorHVBar (precio en la barra de evaluacion; 0 en el resto).
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
		private class ActiveAnchor
		{
			public int    StartBar;
			public int    ExpiryBar;
			public string Tag;
			public double Poc;
			public double VaEdge;
			public double HvBar;
			public int    Dir;
			public bool   Flagged;
		}
		private List<ActiveAnchor> anchors;
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
				AnchorsOnlyFlagged = true;
				AnchorLifeBars     = 150;
				HvBarUseClose      = false;
				PocBrush           = Brushes.Magenta;
				VaBrush            = Brushes.DarkOrange;
				HvBrush            = Brushes.DeepSkyBlue;
				FlagBrush          = Brushes.Gold;
				NoFlagBrush        = Brushes.Gray;
''')
rep('''				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "StabilityScore");
			}
			else if (State == State.DataLoaded)
			{''','''				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "StabilityScore");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "VolFlag");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorPOC");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorVAEdge");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorHVBar");
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
				anchors = new List<ActiveAnchor>();
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

			for (int i = 0; i < 9; i++)
				Values[i][0] = 0.0;

			ProcessPendingZones();
			DrawActiveAnchors();
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

		// Perfil de volumen por precio del sector y las 3 anclas: POC, borde del Area de Valor (70 %) del lado del interior, barra de maximo volumen
		private void ComputeAnchors(PendingZone z, out double total, out double poc, out double vaEdge, out double hvBar)
		{
			total = 0.0; poc = 0.0; vaEdge = 0.0; hvBar = 0.0;

			DateTime t0  = z.SecStartBar > 0 ? Time[CurrentBar - (z.SecStartBar - 1)] : DateTime.MinValue;
			DateTime t1  = Time[CurrentBar - z.SecEndBar];
			double   eps = TickSize * 0.01;

			int minIdx = int.MaxValue, maxIdx = int.MinValue;
			List<int>    ids  = new List<int>();
			List<double> vols = new List<double>();
			for (int i = UpperBound(t0); i < tkTime.Count; i++)
			{
				if (tkTime[i] > t1)
					break;
				double p = tkPx[i];
				if (p < z.Lo - eps || p > z.Hi + eps)
					continue;
				int id = (int)Math.Round(p / TickSize);
				ids.Add(id);
				vols.Add(tkVol[i]);
				total += tkVol[i];
				if (id < minIdx) minIdx = id;
				if (id > maxIdx) maxIdx = id;
			}
			if (total <= 0.0)
				return;

			int n = maxIdx - minIdx + 1;
			double[] v = new double[n];
			for (int k = 0; k < ids.Count; k++)
				v[ids[k] - minIdx] += vols[k];

			// POC: nivel con mas volumen; en empate, el mas cercano al centro de la banda
			double mid = 0.5 * (z.Lo + z.Hi);
			int    pocI = 0;
			for (int k = 1; k < n; k++)
			{
				if (v[k] > v[pocI])
					pocI = k;
				else if (v[k] == v[pocI] && Math.Abs((minIdx + k) * TickSize - mid) < Math.Abs((minIdx + pocI) * TickSize - mid))
					pocI = k;
			}
			poc = (minIdx + pocI) * TickSize;

			// Area de Valor 70 %: desde el POC se suma el par de niveles contiguos (arriba o abajo) con mas volumen
			double target = 0.70 * total;
			double acc    = v[pocI];
			int    lo = pocI, hi = pocI;
			while (acc < target && (lo > 0 || hi < n - 1))
			{
				double up = (hi + 1 < n ? v[hi + 1] : 0.0) + (hi + 2 < n ? v[hi + 2] : 0.0);
				double dn = (lo - 1 >= 0 ? v[lo - 1] : 0.0) + (lo - 2 >= 0 ? v[lo - 2] : 0.0);
				if (hi < n - 1 && (up >= dn || lo == 0))
				{
					acc += v[hi + 1] + (hi + 2 < n ? v[hi + 2] : 0.0);
					hi = Math.Min(n - 1, hi + 2);
				}
				else
				{
					acc += v[lo - 1] + (lo - 2 >= 0 ? v[lo - 2] : 0.0);
					lo = Math.Max(0, lo - 2);
				}
			}
			double val = (minIdx + lo) * TickSize;
			double vah = (minIdx + hi) * TickSize;
			vaEdge = z.Dir > 0 ? val : vah;          // lado del interior de la zona: por debajo en una suba, por encima en una baja

			// Barra de maximo volumen entre las barras del sector
			int    bestBar = -1;
			double bestVol = -1.0;
			for (int b = z.SecStartBar; b <= z.SecEndBar; b++)
			{
				int ago = CurrentBar - b;
				if (ago < 0) continue;
				if (Volume[ago] > bestVol)
				{
					bestVol = Volume[ago];
					bestBar = b;
				}
			}
			if (bestBar >= 0)
			{
				int ago = CurrentBar - bestBar;
				hvBar = HvBarUseClose ? Close[ago] : 0.5 * (High[ago] + Low[ago]);
			}
		}

		// Redibuja cada ancla activa como linea horizontal desde el inicio del sector hasta la barra actual (o hasta que vence)
		private void DrawActiveAnchors()
		{
			for (int ai = anchors.Count - 1; ai >= 0; ai--)
			{
				ActiveAnchor a = anchors[ai];
				int endBar   = Math.Min(CurrentBar, a.ExpiryBar);
				int startAgo = CurrentBar - a.StartBar;
				int endAgo   = CurrentBar - endBar;
				if (startAgo > endAgo)
				{
					Draw.Line(this, a.Tag + "POC", false, startAgo, a.Poc,    endAgo, a.Poc,    PocBrush, DashStyleHelper.Solid, 2);
					Draw.Line(this, a.Tag + "VAE", false, startAgo, a.VaEdge, endAgo, a.VaEdge, VaBrush,  DashStyleHelper.Dash,  2);
					Draw.Line(this, a.Tag + "HVB", false, startAgo, a.HvBar,  endAgo, a.HvBar,  HvBrush,  DashStyleHelper.Dot,   2);
					if (CurrentBar == a.ExpiryBar || a.StartBar == CurrentBar)
					{
						Draw.Text(this, a.Tag + "TPOC", "POC", startAgo, a.Poc,    PocBrush);
						Draw.Text(this, a.Tag + "TVAE", a.Dir > 0 ? "VAL" : "VAH", startAgo, a.VaEdge, VaBrush);
						Draw.Text(this, a.Tag + "THVB", "HVB", startAgo, a.HvBar,  HvBrush);
					}
				}
				if (CurrentBar >= a.ExpiryBar)
					anchors.RemoveAt(ai);
			}
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

				double vol, poc, vaEdge, hvBar;
				ComputeAnchors(z, out vol, out poc, out vaEdge, out hvBar);

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

				if (vol > 0.0 && (flagged || !AnchorsOnlyFlagged))
				{
					Values[6][0] = poc;
					Values[7][0] = vaEdge;
					Values[8][0] = hvBar;
					ActiveAnchor an = new ActiveAnchor();
					an.StartBar  = z.SecStartBar;
					an.ExpiryBar = CurrentBar + AnchorLifeBars;
					an.Tag       = z.Tag;
					an.Poc       = poc;
					an.VaEdge    = vaEdge;
					an.HvBar     = hvBar;
					an.Dir       = z.Dir;
					an.Flagged   = flagged;
					anchors.Add(an);
				}

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
		public Series<double> VolFlag { get { return Values[5]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorPOC { get { return Values[6]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorVAEdge { get { return Values[7]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorHVBar { get { return Values[8]; } }''')
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
		[NinjaScriptProperty]
		[Display(Name = "Anclas solo en zonas marcadas", Order = 10, GroupName = "5. Volumen de sector",
			Description = "true: dibuja POC, borde del area de valor y barra de maximo volumen solo si la zona supera el percentil; false: en todas.")]
		public bool AnchorsOnlyFlagged { get; set; }

		[NinjaScriptProperty] [Range(10, 5000)]
		[Display(Name = "Vida de las anclas (barras)", Order = 11, GroupName = "5. Volumen de sector")]
		public int AnchorLifeBars { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Barra de maximo volumen: usar cierre", Order = 12, GroupName = "5. Volumen de sector",
			Description = "false = punto medio del rango de la barra; true = su cierre.")]
		public bool HvBarUseClose { get; set; }

		[XmlIgnore]
		[Display(Name = "Color POC", Order = 13, GroupName = "5. Volumen de sector")]
		public Brush PocBrush { get; set; }
		[Browsable(false)]
		public string PocBrushSerialize
		{
			get { return Serialize.BrushToString(PocBrush); }
			set { PocBrush = Serialize.StringToBrush(value); }
		}

		[XmlIgnore]
		[Display(Name = "Color borde del area de valor", Order = 14, GroupName = "5. Volumen de sector")]
		public Brush VaBrush { get; set; }
		[Browsable(false)]
		public string VaBrushSerialize
		{
			get { return Serialize.BrushToString(VaBrush); }
			set { VaBrush = Serialize.StringToBrush(value); }
		}

		[XmlIgnore]
		[Display(Name = "Color barra de maximo volumen", Order = 15, GroupName = "5. Volumen de sector")]
		public Brush HvBrush { get; set; }
		[Browsable(false)]
		public string HvBrushSerialize
		{
			get { return Serialize.BrushToString(HvBrush); }
			set { HvBrush = Serialize.StringToBrush(value); }
		}
'''
i=s.rindex('\t\t#endregion')
s=s[:i]+props+'\t\t#endregion'+s[i+len('\t\t#endregion'):]
open(DST,'w',encoding='utf-8-sig',newline='').write(s)
print('ok',len(s))
