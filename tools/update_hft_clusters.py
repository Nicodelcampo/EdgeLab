import sys

path = r'C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTZonesNQPureV4.cs'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# 1. Update ClusterZone class
old_cz = """        public sealed class ClusterZone
        {
            public double Lower;
            public double Upper;
            public int    StartBar;
            public int    EndBar;
            public int    ZoneCount;
            public string Tag;
        }"""

new_cz = """        public sealed class ClusterZone
        {
            public double Lower;
            public double Upper;
            public int    StartBar;
            public int    EndBar;
            public int    ZoneCount;
            public string Tag;
            public double PocPrice;
        }"""

assert old_cz in text, 'old_cz not found'
text = text.replace(old_cz, new_cz, 1)

# 2. Update SetDefaults
old_sd = """                MostrarClusters                = true;
                MinOverlapRectangulos          = 3;
                ColorCluster                   = Brushes.Gold;
                ColorBordeCluster              = Brushes.DarkOrange;
                OpacidadCluster                = 60;
                ExtenderClusterHastaZonaActual = false;
                MostrarTextoCluster            = false;"""

new_sd = """                MostrarClusters                = true;
                MinOverlapRectangulos          = 4;
                ColorCluster                   = Brushes.Gold;
                ColorBordeCluster              = Brushes.DarkOrange;
                OpacidadCluster                = 55;
                ExtenderClusterHastaZonaActual = false;
                MostrarTextoCluster            = true;
                DibujarPocCluster              = true;"""

assert old_sd in text, 'old_sd not found'
text = text.replace(old_sd, new_sd, 1)

# 3. Update DetectarSolapamientoCluster and ConsolidarClusters
old_detect = """        // ===================== CLUSTERS (SOLAPAMIENTO VISUAL EXACTO) =====================
        private void DetectarSolapamientoCluster(int newIdx)
        {
            if (newIdx < 0 || newIdx >= zones.Count) return;
            Zone newZ = zones[newIdx];
            double newLo = Math.Min(newZ.Lower, newZ.Upper);
            double newHi = Math.Max(newZ.Lower, newZ.Upper);
            int newStart = newZ.StartBar;
            int newEnd   = newZ.VisualEndBar;

            // 1. Filtrar zonas anteriores activas que se solapen visualmente con newZ
            List<Zone> candidatos = new List<Zone>();
            int searchStart = Math.Max(0, newIdx - 60);
            for (int i = searchStart; i < newIdx; i++)
            {
                Zone prevZ = zones[i];
                if (prevZ.VisualEndBar <= newStart) continue; // expiro antes de que comience newZ
                double pLo = Math.Min(prevZ.Lower, prevZ.Upper);
                double pHi = Math.Max(prevZ.Lower, prevZ.Upper);
                if (pHi <= newLo || pLo >= newHi) continue; // no hay solapamiento de precio con newZ
                candidatos.Add(prevZ);
            }

            int reqPrev = Math.Max(1, MinOverlapRectangulos - 1);
            if (candidatos.Count < reqPrev) return;

            // 2. Evaluar combinaciones que formen el solapamiento requerido
            List<ClusterZone> clustersGenerados = new List<ClusterZone>();

            if (MinOverlapRectangulos <= 2)
            {
                for (int a = 0; a < candidatos.Count; a++)
                {
                    Zone za = candidatos[a];
                    double zaLo = Math.Min(za.Lower, za.Upper);
                    double zaHi = Math.Max(za.Lower, za.Upper);

                    double interLo = Math.Max(newLo, zaLo);
                    double interHi = Math.Min(newHi, zaHi);
                    if (interHi - interLo < TickSize * 0.5) continue;

                    int interStart = Math.Max(newStart, za.StartBar);
                    int interEnd   = ExtenderClusterHastaZonaActual ? newEnd : Math.Min(newEnd, za.VisualEndBar);
                    if (interEnd <= interStart) continue;

                    clustersGenerados.Add(new ClusterZone
                    {
                        Lower = interLo,
                        Upper = interHi,
                        StartBar = interStart,
                        EndBar = interEnd,
                        ZoneCount = 2
                    });
                }
            }
            else
            {
                for (int a = 0; a < candidatos.Count; a++)
                {
                    Zone za = candidatos[a];
                    double zaLo = Math.Min(za.Lower, za.Upper);
                    double zaHi = Math.Max(za.Lower, za.Upper);

                    for (int b = a + 1; b < candidatos.Count; b++)
                    {
                        Zone zb = candidatos[b];
                        double zbLo = Math.Min(zb.Lower, zb.Upper);
                        double zbHi = Math.Max(zb.Lower, zb.Upper);

                        // Interseccion exacta de precio entre las 3 zonas
                        double interLo = Math.Max(newLo, Math.Max(zaLo, zbLo));
                        double interHi = Math.Min(newHi, Math.Min(zaHi, zbHi));
                        if (interHi - interLo < TickSize * 0.5) continue;

                        // Interseccion temporal exacta donde coexisten las 3 zonas visuales
                        int interStart = Math.Max(newStart, Math.Max(za.StartBar, zb.StartBar));
                        int interEnd   = ExtenderClusterHastaZonaActual ? newEnd : Math.Min(newEnd, Math.Min(za.VisualEndBar, zb.VisualEndBar));
                        if (interEnd <= interStart) continue;

                        clustersGenerados.Add(new ClusterZone
                        {
                            Lower = interLo,
                            Upper = interHi,
                            StartBar = interStart,
                            EndBar = interEnd,
                            ZoneCount = 3
                        });
                    }
                }
            }

            if (clustersGenerados.Count == 0) return;

            // 3. Consolidar sub-rectangulos redundantes
            List<ClusterZone> consolidados = ConsolidarClusters(clustersGenerados);

            // 4. Dibujar o extender rectangulos de cluster en el grafico
            for (int c = 0; c < consolidados.Count; c++)
            {
                ClusterZone cz = consolidados[c];
                ClusterZone matchingExisting = null;
                bool completamenteCubierto = false;

                for (int ex = activeClusters.Count - 1; ex >= 0; ex--)
                {
                    ClusterZone prevC = activeClusters[ex];
                    bool mismoPrecio = Math.Abs(cz.Lower - prevC.Lower) < TickSize * 0.5
                                    && Math.Abs(cz.Upper - prevC.Upper) < TickSize * 0.5;

                    if (mismoPrecio)
                    {
                        if (cz.StartBar >= prevC.StartBar && cz.EndBar <= prevC.EndBar)
                        {
                            completamenteCubierto = true;
                            break;
                        }

                        if (cz.StartBar <= prevC.EndBar && cz.EndBar > prevC.EndBar)
                        {
                            matchingExisting = prevC;
                            break;
                        }
                    }
                }

                if (completamenteCubierto) continue;

                if (matchingExisting != null)
                {
                    matchingExisting.EndBar = Math.Max(matchingExisting.EndBar, cz.EndBar);
                    matchingExisting.ZoneCount = Math.Max(matchingExisting.ZoneCount, cz.ZoneCount);

                    int startAgo = CurrentBars[0] - matchingExisting.StartBar;
                    int endAgo   = CurrentBars[0] - matchingExisting.EndBar;

                    Draw.Rectangle(this, matchingExisting.Tag, false,
                        startAgo, matchingExisting.Upper, endAgo, matchingExisting.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("{0}x", matchingExisting.ZoneCount);
                        int textBar = Math.Max(0, startAgo);
                        Draw.Text(this, matchingExisting.Tag + "_T", txt, textBar, matchingExisting.Upper + (TickSize * 2), ColorBordeCluster);
                    }
                }
                else
                {
                    clusterCounter++;
                    string tag = "HFTCLUST_" + clusterCounter;
                    cz.Tag = tag;
                    clusterTags.Add(tag);

                    int startAgo = CurrentBars[0] - cz.StartBar;
                    int endAgo   = CurrentBars[0] - cz.EndBar;

                    Draw.Rectangle(this, tag, false,
                        startAgo, cz.Upper, endAgo, cz.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("{0}x", cz.ZoneCount);
                        string textTag = tag + "_T";
                        clusterTags.Add(textTag);
                        int textBar = Math.Max(0, startAgo);
                        Draw.Text(this, textTag, txt, textBar, cz.Upper + (TickSize * 2), ColorBordeCluster);
                    }

                    activeClusters.Add(cz);
                    if (activeClusters.Count > 500) activeClusters.RemoveAt(0);
                }
            }
        }

        private List<ClusterZone> ConsolidarClusters(List<ClusterZone> lista)
        {
            if (lista.Count <= 1) return lista;
            List<ClusterZone> res = new List<ClusterZone>();

            lista.Sort((x, y) => ((y.Upper - y.Lower) * (y.EndBar - y.StartBar))
                .CompareTo((x.Upper - x.Lower) * (x.EndBar - x.StartBar)));

            for (int i = 0; i < lista.Count; i++)
            {
                ClusterZone c = lista[i];
                bool contained = false;
                for (int j = 0; j < res.Count; j++)
                {
                    ClusterZone r = res[j];
                    if (c.Lower >= r.Lower - TickSize * 0.25 && c.Upper <= r.Upper + TickSize * 0.25 &&
                        c.StartBar >= r.StartBar && c.EndBar <= r.EndBar)
                    {
                        contained = true;
                        r.ZoneCount = Math.Max(r.ZoneCount, c.ZoneCount);
                        break;
                    }
                }
                if (!contained)
                {
                    res.Add(c);
                }
            }
            return res;
        }"""

new_detect = """        // ===================== CLUSTERS (HISTOGRAMA DE DENSIDAD DE CONFLUENCIA 4+) =====================
        private void DetectarSolapamientoCluster(int newIdx)
        {
            if (newIdx < 0 || newIdx >= zones.Count) return;
            Zone newZ = zones[newIdx];
            int currentBar = CurrentBars[0];

            // 1. Filtrar zonas activas que coexisten temporalmente o recientemente
            List<Zone> candidatos = new List<Zone>();
            int searchStart = Math.Max(0, newIdx - 150);
            for (int i = searchStart; i <= newIdx; i++)
            {
                Zone z = zones[i];
                if (z.VisualEndBar <= newZ.StartBar) continue; // expiro antes del inicio de la nueva zona
                candidatos.Add(z);
            }

            if (candidatos.Count < MinOverlapRectangulos) return;

            // 2. Construir Histograma de Densidad por Ticks
            Dictionary<long, int> tickDensity = new Dictionary<long, int>();
            Dictionary<long, double> tickVolume = new Dictionary<long, double>();

            for (int i = 0; i < candidatos.Count; i++)
            {
                Zone z = candidatos[i];
                double zLo = Math.Min(z.Lower, z.Upper);
                double zHi = Math.Max(z.Lower, z.Upper);
                long loTk = (long)Math.Round(zLo / TickSize);
                long hiTk = (long)Math.Round(zHi / TickSize);

                for (long tk = loTk; tk <= hiTk; tk++)
                {
                    tickDensity[tk] = tickDensity.ContainsKey(tk) ? tickDensity[tk] + 1 : 1;
                    tickVolume[tk]  = tickVolume.ContainsKey(tk) ? tickVolume[tk] + z.TotalVol : z.TotalVol;
                }
            }

            // 3. Extraer ticks que alcanzan el umbral de 4+ zonas (MinOverlapRectangulos)
            List<long> qualifyingTicks = new List<long>();
            foreach (KeyValuePair<long, int> kv in tickDensity)
            {
                if (kv.Value >= MinOverlapRectangulos)
                    qualifyingTicks.Add(kv.Key);
            }

            if (qualifyingTicks.Count == 0) return;
            qualifyingTicks.Sort();

            // 4. Agrupar en segmentos contiguos (tolerancia de 1 tick de gap)
            List<List<long>> clusters = new List<List<long>>();
            List<long> currentCluster = new List<long>();

            for (int i = 0; i < qualifyingTicks.Count; i++)
            {
                if (currentCluster.Count == 0)
                {
                    currentCluster.Add(qualifyingTicks[i]);
                    continue;
                }

                if (qualifyingTicks[i] - currentCluster[currentCluster.Count - 1] <= 1)
                {
                    currentCluster.Add(qualifyingTicks[i]);
                }
                else
                {
                    clusters.Add(currentCluster);
                    currentCluster = new List<long> { qualifyingTicks[i] };
                }
            }
            if (currentCluster.Count > 0)
                clusters.Add(currentCluster);

            // 5. Duracion del cluster: el doble que el resto de rectangulos (2 * ExtensionDibujo)
            int clusterEndBar = currentBar + (ExtensionDibujo * 2);
            int endAgo = -(ExtensionDibujo * 2);

            // 6. Procesar y dibujar cada cluster detectado
            for (int c = 0; c < clusters.Count; c++)
            {
                List<long> cTicks = clusters[c];
                double cLower = cTicks.Min() * TickSize - (TickSize * 0.5);
                double cUpper = cTicks.Max() * TickSize + (TickSize * 0.5);

                // Encontrar el tick POC (maxima confluencia de zonas y volumen)
                long pocTk = cTicks[0];
                int maxCount = 0;
                double maxVol = 0;
                for (int t = 0; t < cTicks.Count; t++)
                {
                    long tk = cTicks[t];
                    int cnt = tickDensity[tk];
                    double vol = tickVolume.ContainsKey(tk) ? tickVolume[tk] : 0;
                    if (cnt > maxCount || (cnt == maxCount && vol > maxVol))
                    {
                        maxCount = cnt;
                        maxVol = vol;
                        pocTk = tk;
                    }
                }
                double pocPrice = pocTk * TickSize;

                // Identificar zonas contribuyentes para determinar la barra de inicio
                int clusterStartBar = newZ.StartBar;
                for (int i = 0; i < candidatos.Count; i++)
                {
                    Zone z = candidatos[i];
                    double zLo = Math.Min(z.Lower, z.Upper);
                    double zHi = Math.Max(z.Lower, z.Upper);
                    if (zHi >= cLower && zLo <= cUpper)
                    {
                        clusterStartBar = Math.Min(clusterStartBar, z.StartBar);
                    }
                }

                int startAgo = currentBar - clusterStartBar;

                // Buscar si ya existe un cluster activo en este nivel para actualizarlo sin duplicar
                ClusterZone matchingExisting = null;
                for (int ex = activeClusters.Count - 1; ex >= 0; ex--)
                {
                    ClusterZone prevC = activeClusters[ex];
                    double ovLo = Math.Max(cLower, prevC.Lower);
                    double ovHi = Math.Min(cUpper, prevC.Upper);
                    if (ovHi > ovLo) // Se intersectan en precio
                    {
                        matchingExisting = prevC;
                        break;
                    }
                }

                if (matchingExisting != null)
                {
                    matchingExisting.Lower = Math.Min(matchingExisting.Lower, cLower);
                    matchingExisting.Upper = Math.Max(matchingExisting.Upper, cUpper);
                    matchingExisting.ZoneCount = Math.Max(matchingExisting.ZoneCount, maxCount);
                    matchingExisting.StartBar = Math.Min(matchingExisting.StartBar, clusterStartBar);
                    matchingExisting.EndBar = clusterEndBar;
                    matchingExisting.PocPrice = pocPrice;

                    int exStartAgo = currentBar - matchingExisting.StartBar;

                    Draw.Rectangle(this, matchingExisting.Tag, false,
                        exStartAgo, matchingExisting.Upper, endAgo, matchingExisting.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (DibujarPocCluster)
                    {
                        Draw.Line(this, matchingExisting.Tag + "_POC", false,
                            exStartAgo, matchingExisting.PocPrice, endAgo, matchingExisting.PocPrice,
                            ColorBordeCluster, DashStyleHelper.Dash, 2);
                    }

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("★ CLUSTER {0}x (POC: {1:F2})", matchingExisting.ZoneCount, matchingExisting.PocPrice);
                        int textBar = Math.Max(0, exStartAgo);
                        Draw.Text(this, matchingExisting.Tag + "_T", txt, textBar, matchingExisting.Upper + (TickSize * 3), ColorBordeCluster);
                    }
                }
                else
                {
                    clusterCounter++;
                    string tag = "HFTCLUST_" + clusterCounter;
                    ClusterZone cz = new ClusterZone
                    {
                        Lower = cLower,
                        Upper = cUpper,
                        StartBar = clusterStartBar,
                        EndBar = clusterEndBar,
                        ZoneCount = maxCount,
                        Tag = tag,
                        PocPrice = pocPrice
                    };
                    clusterTags.Add(tag);
                    clusterTags.Add(tag + "_POC");

                    Draw.Rectangle(this, tag, false,
                        startAgo, cz.Upper, endAgo, cz.Lower,
                        ColorBordeCluster, ColorCluster, OpacidadCluster);

                    if (DibujarPocCluster)
                    {
                        Draw.Line(this, tag + "_POC", false,
                            startAgo, cz.PocPrice, endAgo, cz.PocPrice,
                            ColorBordeCluster, DashStyleHelper.Dash, 2);
                    }

                    if (MostrarTextoCluster)
                    {
                        string txt = string.Format("★ CLUSTER {0}x (POC: {1:F2})", cz.ZoneCount, cz.PocPrice);
                        string textTag = tag + "_T";
                        clusterTags.Add(textTag);
                        int textBar = Math.Max(0, startAgo);
                        Draw.Text(this, textTag, txt, textBar, cz.Upper + (TickSize * 3), ColorBordeCluster);
                    }

                    activeClusters.Add(cz);
                    if (activeClusters.Count > 500) activeClusters.RemoveAt(0);
                }
            }
        }"""

assert old_detect in text, 'old_detect not found'
text = text.replace(old_detect, new_detect, 1)

# 4. Update Region H Properties
old_reg_h = """        #region H. Clusters (solapamiento exacto)
        [Display(Name="Mostrar clusters (3+ zonas)", Order=1, GroupName="H. Clusters", Description="Destaca con otro color el rectangulo exacto donde se solapan 3 o mas zonas visuales.")]
        public bool MostrarClusters { get; set; }

        [Range(2, 20)]
        [Display(Name="Minimo rectangulos solapados", Order=2, GroupName="H. Clusters", Description="Cantidad minima de rectangulos solapados simultaneamente (por defecto 3).")]
        public int MinOverlapRectangulos { get; set; }

        [XmlIgnore]
        [Display(Name="Color relleno cluster", Order=3, GroupName="H. Clusters", Description="Color de relleno para el area exacta de solapamiento.")]
        public Brush ColorCluster { get; set; }
        [Browsable(false)] public string ColorClusterSerializable
        { get { return Serialize.BrushToString(ColorCluster); } set { ColorCluster = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color borde cluster", Order=4, GroupName="H. Clusters", Description="Color del contorno del area de solapamiento.")]
        public Brush ColorBordeCluster { get; set; }
        [Browsable(false)] public string ColorBordeClusterSerializable
        { get { return Serialize.BrushToString(ColorBordeCluster); } set { ColorBordeCluster = Serialize.StringToBrush(value); } }

        [Range(1, 100)]
        [Display(Name="Opacidad cluster", Order=5, GroupName="H. Clusters", Description="Opacidad del relleno del cluster (1 a 100).")]
        public int OpacidadCluster { get; set; }

        [Display(Name="Extender hasta fin de zona actual", Order=6, GroupName="H. Clusters", Description="Si esta activo, extiende el cluster hasta el fin de la zona actual. Si esta inactivo (default), cubre solo el solapamiento visual literal.")]
        public bool ExtenderClusterHastaZonaActual { get; set; }

        [Display(Name="Mostrar etiqueta cluster", Order=7, GroupName="H. Clusters", Description="Muestra una etiqueta indicando la cantidad de zonas solapadas.")]
        public bool MostrarTextoCluster { get; set; }
        #endregion"""

new_reg_h = """        #region H. Clusters (densidad de confluencia 4+)
        [Display(Name="Mostrar clusters (4+ zonas)", Order=1, GroupName="H. Clusters", Description="Destaca con otro color el rectangulo donde confluyen 4 o mas zonas visuales.")]
        public bool MostrarClusters { get; set; }

        [Range(2, 20)]
        [Display(Name="Minimo rectangulos solapados", Order=2, GroupName="H. Clusters", Description="Cantidad minima de rectangulos solapados simultaneamente (por defecto 4).")]
        public int MinOverlapRectangulos { get; set; }

        [XmlIgnore]
        [Display(Name="Color relleno cluster", Order=3, GroupName="H. Clusters", Description="Color de relleno para el area exacta de solapamiento.")]
        public Brush ColorCluster { get; set; }
        [Browsable(false)] public string ColorClusterSerializable
        { get { return Serialize.BrushToString(ColorCluster); } set { ColorCluster = Serialize.StringToBrush(value); } }

        [XmlIgnore]
        [Display(Name="Color borde cluster", Order=4, GroupName="H. Clusters", Description="Color del contorno del area de solapamiento.")]
        public Brush ColorBordeCluster { get; set; }
        [Browsable(false)] public string ColorBordeClusterSerializable
        { get { return Serialize.BrushToString(ColorBordeCluster); } set { ColorBordeCluster = Serialize.StringToBrush(value); } }

        [Range(1, 100)]
        [Display(Name="Opacidad cluster", Order=5, GroupName="H. Clusters", Description="Opacidad del relleno del cluster (1 a 100).")]
        public int OpacidadCluster { get; set; }

        [Display(Name="Extender hasta fin de zona actual", Order=6, GroupName="H. Clusters", Description="Si esta activo, extiende el cluster hasta el fin de la zona actual. Si esta inactivo (default), cubre solo el solapamiento visual literal.")]
        public bool ExtenderClusterHastaZonaActual { get; set; }

        [Display(Name="Mostrar etiqueta cluster", Order=7, GroupName="H. Clusters", Description="Muestra una etiqueta indicando la cantidad de zonas solapadas.")]
        public bool MostrarTextoCluster { get; set; }

        [Display(Name="Dibujar linea central POC", Order=8, GroupName="H. Clusters", Description="Dibuja la linea discontinua del punto de maxima confluencia gravitacional dentro del cluster.")]
        public bool DibujarPocCluster { get; set; }
        #endregion"""

assert old_reg_h in text, 'old_reg_h not found'
text = text.replace(old_reg_h, new_reg_h, 1)

# Write back with CRLF
crlf_text = text.replace('\r\n', '\n').replace('\n', '\r\n')
with open(path, 'wb') as f:
    f.write(crlf_text.encode('utf-8'))

with open(r'D:\EdgeLab\nt8\HFTZonesNQPureV4.cs', 'wb') as f:
    f.write(crlf_text.encode('utf-8'))

print('SUCCESSFULLY UPDATED HFTZonesNQPureV4.cs in both directories')
