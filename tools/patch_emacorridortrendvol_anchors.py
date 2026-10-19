p = 'build_variant.py'
t = open(p, encoding='utf-8').read()


def rep(old, new):
    global t
    assert old in t, old[:70]
    t = t.replace(old, new, 1)


# --- cabecera
rep("// SALIDAS: plot VolFlag", '''// ANCLAS (puntos de referencia dentro del sector, 3 en total; se calculan con el perfil de volumen por precio del sector):
//   1. POC del sector: el precio con mas volumen operado (nivel de mayor aceptacion).
//   2. Borde del Area de Valor (70 %) del lado del INTERIOR de la zona: VAL en una suba, VAH en una baja (el borde mas cercano al
//      camino por el que volveria el precio a lo largo del corredor).
//   3. Barra de maximo volumen del sector (vela tipo VolTicksDef): punto medio de su rango (parametro HvBarUseClose para usar el cierre).
//   Se dibujan como lineas horizontales desde el inicio del sector hasta AnchorLifeBars barras despues de evaluar, y se exponen en los
//   plots AnchorPOC, AnchorVAEdge y AnchorHVBar (precio en la barra de evaluacion; 0 en el resto).
// SALIDAS: plot VolFlag''')

# --- campos
rep("		private List<double>      volHist;\n", '''		private List<double>      volHist;
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
''')

# --- defaults, plots, init
rep("				DrawSector         = true;\n", '''				DrawSector         = true;
				AnchorsOnlyFlagged = true;
				AnchorLifeBars     = 150;
				HvBarUseClose      = false;
				PocBrush           = Brushes.Magenta;
				VaBrush            = Brushes.DarkOrange;
				HvBrush            = Brushes.DeepSkyBlue;
''')
rep('				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "VolFlag");\n', '''				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "VolFlag");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorPOC");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorVAEdge");
				AddPlot(new Stroke(Brushes.Transparent, 1), PlotStyle.Line, "AnchorHVBar");
''')
rep("				volHist = new List<double>();\n", "				volHist = new List<double>();\n				anchors = new List<ActiveAnchor>();\n")
rep("			for (int i = 0; i < 6; i++)", "			for (int i = 0; i < 9; i++)")
rep("			ProcessPendingZones();\n", "			ProcessPendingZones();\n			DrawActiveAnchors();\n")

# --- evaluacion con perfil
rep("				double vol = SectorVolume(z.SecStartBar, z.SecEndBar, z.Lo, z.Hi);\n", '''				double vol, poc, vaEdge, hvBar;
				ComputeAnchors(z, out vol, out poc, out vaEdge, out hvBar);
''')
rep("				if (flagged)\n					Values[5][0] = z.Dir;\n", '''				if (flagged)
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
''')

# --- metodos nuevos antes de SectorVolume
rep("		// Suma el volumen de los ticks con tiempo dentro", '''		// Perfil de volumen por precio del sector y las 3 anclas: POC, borde del Area de Valor (70 %) del lado del interior, barra de maximo volumen
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

		// Suma el volumen de los ticks con tiempo dentro''')

# --- accesores y propiedades
rep("		public Series<double> VolFlag { get { return Values[5]; } }", '''		public Series<double> VolFlag { get { return Values[5]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorPOC { get { return Values[6]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorVAEdge { get { return Values[7]; } }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> AnchorHVBar { get { return Values[8]; } }''')

props = '''		[NinjaScriptProperty]
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
marker = "'''\ni=s.rindex("
j = t.index(marker)
t = t[:j] + props + t[j:]
open(p, 'w', encoding='utf-8').write(t)
print('anchors patched')
