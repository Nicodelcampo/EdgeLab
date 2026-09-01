// ============================================================================
// aVolClusterPOI.cs - Anomaly Volume Cluster POI (v0.5, research freeze)
// ============================================================================
//
// ORIGEN
//   Reescritura desde cero de aVolZonePOI.cs rescatando sus dos ideas utiles:
//   1) Deteccion por MASA DE CLUSTER: niveles "hot" (vol >= mediana x mult)
//      contiguos se agrupan, y la SUMA del cluster se compara contra el
//      perfil historico del mismo bucket horario. Anomalia a escala de
//      zona, no de celda individual (complementa a aVolCellPOI2).
//   2) Alerta de RAFAGA: N zonas creadas en pocas barras dentro de un rango
//      de ticks acotado (senal de segundo orden: tasa de formacion).
//
// QUE SE ELIMINO DEL ORIGINAL (y por que)
//   - SQLite y "mitigacion" por proceso externo: estado fuera del indicador
//     = repintado irreproducible. El ciclo de vida ahora es interno.
//   - Precios double como clave de diccionario y epsilons ad-hoc (+0.01):
//     TODO el estado usa TICKS ENTEROS (familia de bugs ULP, AUDIT-002).
//   - Fallback a cola global mezclando horas: reintroducia el sesgo de
//     estacionalidad intradiaria. Sin historial del bucket => no detecta.
//   - Bloques anclados al punto de carga del chart: ahora se anclan al
//     inicio de sesion => deterministas.
//   - Percentil con interpolacion lineal: cuantil empirico SIN interpolar.
//
// CONTRATO (declarado para una futura traduccion a EdgeLab)
//   1. Calculate = OnBarClose, fijo. Clase de repintado: non_repainting.
//      Una zona creada al cierre de la barra B esta disponible desde B+1;
//      la barra creadora nunca toca ni invalida su propia zona.
//   2. Ticks enteros: tick = round(snap_NT8(precio) / TickSize,
//      MidpointRounding.AwayFromZero). Limites fisicos de la celda P:
//      [P - ts/2, P + ts/2] (solo para dibujo). Todas las comparaciones
//      del ciclo de vida son aritmetica entera: exposicion ULP = 0 por
//      construccion (verificar con tools/ulp_exposure.py si se traduce).
//   3. Perfil por barra reconstruido SIEMPRE de la subserie 1-tick
//      (footprint=reconstructed_1tick_subseries), en cualquier chart.
//      Ticks fuera de [lowTick, highTick] de la barra primaria se ignoran.
//   4. Bloques: WindowBars barras primarias, contador reiniciado al inicio
//      de cada sesion. El bloque parcial al final de la sesion se descarta.
//   5. Perfil historico por bucket: SOLO sesiones completas anteriores.
//      La sesion actual acumula aparte y se commitea al iniciar la
//      siguiente. Los datos previos al primer inicio de sesion visto se
//      descartan. FIFO por sesion: LookbackSessions. Muestra por bloque =
//      score del mejor cluster (0 si no hubo clusters).
//   6. Bucket horario: ancla en (cierre - 1 segundo). SessionRelative
//      (default): minutos desde ActualSessionBegin / TimeBucketMinutes.
//      WallClock si UseSessionBuckets = false.
//   7. Mediana = sorted[n/2] (mediana superior para n par). Cuantil
//      empirico: menor v tal que count(<= v) >= ceil(p*n). Sin interpolar.
//   8. Ciclo de vida: TOUCH = [lowTick, highTick] de una barra posterior
//      interseca [LowerTick, UpperTick]. FirstTouch: primer touch invalida.
//      CloseThrough: lado de referencia = lado del close al crear (si
//      cierra dentro, lo fija el primer close externo posterior); invalida
//      el primer close en el lado opuesto. MaxTouches / MaxAgeBars.
//   9. Export CSV opcional (EventLogPath): SOBREESCRIBE siempre (nunca
//      append) para no mezclar corridas. Meta en linea 1.
//
// CAPACIDAD PREDICTIVA (hipotesis, no promesa)
//   - Cada zona recibe direccion causal: LONG si el cierre creador queda arriba
//     (soporte esperado), SHORT si queda abajo (resistencia esperada).
//   - QualityScore 0..100 combina SOLO informacion disponible al crear:
//     anomalia 35%, concentracion 25%, densidad 15%, rechazo 15%, rafaga 10%.
//     Es un ranking heuristico transparente, NO una probabilidad calibrada.
//   - Tras el primer touch, un evaluador forward registra TARGET/STOP/TIMEOUT/
//     AMBIGUOUS, MFE y MAE. Si target y stop ocurren en la misma barra, no
//     inventa el orden: AMBIGUOUS. Esto permite validar capacidad predictiva.
//   - Dashboard en una esquina del chart (Draw.TextFixed): estado del perfil,
//     conteos de zonas y reacciones, ultima zona y leyenda de lectura.
//     SOLO visual: no afecta deteccion, ciclo de vida ni export.
//   - Las zonas invalidadas NO se borran (default): quedan en GRIS acotadas
//     a su vida real (creacion -> invalidacion), para auditar visualmente
//     todo lo que el indicador marco. RemoveInvalidatedZones=true las borra.
//
// DEFAULTS v0.5 = MODO RESEARCH (censo 2026-08-13):
//   percentil 98, min 20 muestras, filtro predictivo OFF, MaxAge=0,
//   1 cluster de maxima masa por bloque, at-price separado de off-price.
//   Export: ZONE_CREATED | FIRST_TOUCH | ZONE_INVALIDATED | AT_PRICE_CREATED.
//   Sin ZONE_TOUCHED, ZONE_OUTCOME ni BURST en el CSV.
//
// ESTADO: DETECTOR CONGELADO para paridad P2 con el kernel Python.
// No usar sus zonas para operar hasta pasar el pipeline estandar
// (contrato de paridad, oraculo, ulp_exposure, tests).
// ============================================================================

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using System.Windows.Media;
using NinjaTrader.Data;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// Enums en ambito GLOBAL (fuera del namespace): el codigo autogenerado de
// NT8 (MarketAnalyzerColumns, Strategies) los referencia sin calificar desde
// otros namespaces; declararlos dentro de Indicators produce CS0246.
public enum AVCLPInvalidationMode { None = 0, FirstTouch = 1, CloseThrough = 2 }
public enum AVCLPDashboardCorner { TopRight = 0, TopLeft = 1, BottomRight = 2, BottomLeft = 3 }

namespace NinjaTrader.NinjaScript.Indicators
{
	public class aVolClusterPOI : Indicator
	{
		// ---- sesion y buckets ----
		private SessionIterator sessionIterator;
		private DateTime sessionBegin = DateTime.MinValue;
		private int sessionIndex = -1;

		private class Sample { public int Session; public double Score; }
		private Dictionary<int, List<Sample>> bucketHistory;   // sesiones completas anteriores
		private Dictionary<int, List<double>> pendingSession;  // sesion actual, aun no commiteada

		// ---- acumuladores ----
		private Dictionary<long, double> tickProfile;  // barra primaria en formacion (tick -> vol)
		private Dictionary<long, double> blockCells;   // bloque actual (tick -> vol)
		private int blockBarCount;

		// ---- zonas ----
		private class Zone
		{
			public long Id;
			public int CreatedBar;
			public long LowerTick;
			public long UpperTick;
			public double Score;
			public int Bucket;
			public int TouchCount;
			public int RefSide;      // +1 close arriba al crear, -1 abajo, 0 indefinido
			public bool Active;
			public string RectTag;
			public string LabelTag;
			public int Direction;       // +1 LONG/support, -1 SHORT/resistance
			public double AnomalyRatio;
			public double ClusterShare;
			public double Density;
			public double QualityScore; // heuristic rank, not probability
			public int DistanceTicks;
			public int BurstCount;
			public bool OutcomeStarted;
			public bool OutcomeDone;
			public int TouchBar;
			public int MfeTicks;
			public int MaeTicks;
			public string Outcome;
			public string Kind;          // OFF_PRICE | AT_PRICE
			public bool FirstTouchEmitted;
		}
		private List<Zone> zones;
		private long nextZoneId;

		private class Creation { public int Bar; public long Center2; } // Center2 = LowerTick + UpperTick (entero siempre)
		private List<Creation> creations;

		private Queue<string> renderedTags;

		// ---- export ----
		private StreamWriter writer;
		private bool writerFailed;
		private long eventSeq;

		// ---- export diagnostico por bloque (opcional, off por defecto) ----
		private StreamWriter diagWriter;
		private bool diagWriterFailed;
		private long diagSeq;

		// ---- dashboard (solo visual) ----
		private int totalZonesCreated;
		private int sessionZonesCreated;
		private int outcomeTarget;
		private int outcomeStop;
		private int outcomeTimeout;
		private int outcomeAmbiguous;
		private string lastZoneInfo;
		private SimpleFont dashFont;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Cluster-mass POI v0.5: 1 cluster/bloque, at-price separado, FIRST_TOUCH, MaxAge=0.";
				Name = "aVolClusterPOI";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = false;
				DrawOnPricePanel = true;
				PaintPriceMarkers = false;
				IsSuspendedWhileInactive = true;

				WindowBars = 10;
				MedianMultiplier = 2.0;
				MaxGapTicks = 1;
				MinClusterTicks = 2;

				UseSessionBuckets = true;
				TimeBucketMinutes = 30;
				LookbackSessions = 20;
				DetectionPercentile = 98.0;
				MinSamplesPerBucket = 20;

				EnablePredictiveFilter = false;
				MinQualityScore = 0.0;
				MaxDistanceFromZoneTicks = 80;
				RejectionFullScoreTicks = 12;
				ReactionHorizonBars = 50;
				ReactionTargetTicks = 12;
				ReactionStopTicks = 8;

				InvalidationMode = AVCLPInvalidationMode.CloseThrough;
				MaxAgeBars = 0;
				MaxTouches = 0;

				BurstMinZones = 3;
				BurstWindowBars = 200;
				BurstRangeTicks = 40;

				EventLogPath = "";
				DiagBlockExportEnabled = false;
				DiagBlockExportPath = "";
				Opacity = 40;
				VisualExtendBars = 500;
				MaxRenderedZones = 500;
				RemoveInvalidatedZones = false;
				ShowScoreLabel = true;
				ShowOutcomeLabels = false;
				ShowDashboard = true;
				DashboardCorner = AVCLPDashboardCorner.TopRight;
			}
			else if (State == State.Configure)
			{
				// Subserie de 1 tick para reconstruir el perfil por precio en cualquier chart.
				AddDataSeries(BarsPeriodType.Tick, 1);
			}
			else if (State == State.DataLoaded)
			{
				sessionIterator = new SessionIterator(Bars);
				sessionBegin = DateTime.MinValue;
				sessionIndex = -1;
				bucketHistory = new Dictionary<int, List<Sample>>();
				pendingSession = new Dictionary<int, List<double>>();
				tickProfile = new Dictionary<long, double>();
				blockCells = new Dictionary<long, double>();
				blockBarCount = 0;
				zones = new List<Zone>();
				nextZoneId = 1;
				creations = new List<Creation>();
				renderedTags = new Queue<string>();
				writer = null;
				writerFailed = false;
				eventSeq = 0;
				diagWriter = null;
				diagWriterFailed = false;
				diagSeq = 0;
				totalZonesCreated = 0;
				sessionZonesCreated = 0;
				outcomeTarget = 0;
				outcomeStop = 0;
				outcomeTimeout = 0;
				outcomeAmbiguous = 0;
				lastZoneInfo = "";
				dashFont = new SimpleFont("Consolas", 12);
			}
			else if (State == State.Terminated)
			{
				if (writer != null)
				{
					try { writer.Flush(); writer.Close(); } catch { }
					writer = null;
				}
				if (diagWriter != null)
				{
					try { diagWriter.Flush(); diagWriter.Close(); } catch { }
					diagWriter = null;
				}
			}
		}

		protected override void OnBarUpdate()
		{
			// === Subserie 1-tick: acumular volumen por precio (tick entero) ===
			if (BarsInProgress == 1)
			{
				if (tickProfile == null) return;
				if (BarsArray[1] == null || BarsArray[1].Count == 0) return;
				double tvol = Volumes[1][0];
				if (tvol <= 0) return;
				long tick = PriceToTick(Closes[1][0]);
				double cur;
				if (tickProfile.TryGetValue(tick, out cur)) tickProfile[tick] = cur + tvol;
				else tickProfile[tick] = tvol;
				return;
			}

			if (BarsInProgress != 0) return;
			if (CurrentBar < 0) return;

			// === Inicio de sesion: commit del perfil pendiente, reset de bloque ===
			if (Bars.IsFirstBarOfSession)
			{
				CommitSession();
				sessionIndex++;
				try
				{
					sessionIterator.GetNextSession(Time[0], true);
					sessionBegin = sessionIterator.ActualSessionBegin;
				}
				catch { sessionBegin = DateTime.MinValue; }
				blockCells.Clear();
				blockBarCount = 0;
				sessionZonesCreated = 0;
			}

			// === Snapshot del perfil de la barra primaria recien cerrada ===
			long lowTick = PriceToTick(Low[0]);
			long highTick = PriceToTick(High[0]);
			if (tickProfile.Count > 0)
			{
				foreach (KeyValuePair<long, double> kv in tickProfile)
				{
					if (kv.Key < lowTick || kv.Key > highTick) continue; // defensa de borde
					double cur;
					if (blockCells.TryGetValue(kv.Key, out cur)) blockCells[kv.Key] = cur + kv.Value;
					else blockCells[kv.Key] = kv.Value;
				}
				tickProfile.Clear();
			}
			blockBarCount++;

			// === Ciclo de vida: solo zonas creadas en barras ANTERIORES ===
			ProcessLifecycle(lowTick, highTick, PriceToTick(Close[0]));

			// === Cierre de bloque ===
			if (blockBarCount >= WindowBars)
			{
				ProcessBlock();
				blockCells.Clear();
				blockBarCount = 0;
				zones.RemoveAll(delegate(Zone z) { return !z.Active && (!z.OutcomeStarted || z.OutcomeDone); });
			}

			if (ShowDashboard) UpdateDashboard();
		}

		// ------------------------------------------------------------------
		// Deteccion
		// ------------------------------------------------------------------
		private void ProcessBlock()
		{
			int bucket = GetTimeBucket(Time[0]);
			double bestScore = 0;

			// ---- variables de diagnostico (solo lectura, no alteran la deteccion) ----
			// Declaradas en el scope de ProcessBlock para que EmitBlockDiag() las vea
			// sin importar que rama se tomo. DiagBlockExportPath="" => todo esto es
			// costo cero salvo la asignacion de estos defaults.
			double diagMedian = double.NaN;
			double diagHotThreshold = double.NaN;
			double diagThresh = double.NaN;
			int diagHistCount = 0;
			List<List<long>> diagClusters = null;
			List<long> diagBestCluster = null;
			double diagBestPassScore = 0;
			string diagDecision = "ABSTAIN_FEW_CELLS";

			if (blockCells.Count >= 3)
			{
				// Mediana (superior para n par) de los volumenes por celda del bloque
				List<double> vols = new List<double>(blockCells.Values);
				vols.Sort();
				double median = vols[vols.Count / 2];
				double hotThreshold = median * MedianMultiplier;
				diagMedian = median;
				diagHotThreshold = hotThreshold;

				// Niveles hot ordenados por tick (entero)
				List<long> hotTicks = new List<long>();
				foreach (KeyValuePair<long, double> kv in blockCells)
					if (kv.Value >= hotThreshold) hotTicks.Add(kv.Key);
				hotTicks.Sort();

				// Clusters por gap entero (sin epsilons)
				List<List<long>> clusters = new List<List<long>>();
				List<long> current = new List<long>();
				for (int i = 0; i < hotTicks.Count; i++)
				{
					if (current.Count == 0) { current.Add(hotTicks[i]); continue; }
					long gap = hotTicks[i] - current[current.Count - 1] - 1;
					if (gap <= MaxGapTicks) current.Add(hotTicks[i]);
					else
					{
						if (current.Count >= MinClusterTicks) clusters.Add(current);
						current = new List<long>();
						current.Add(hotTicks[i]);
					}
				}
				if (current.Count >= MinClusterTicks) clusters.Add(current);
				diagClusters = clusters;
				diagDecision = clusters.Count == 0 ? "ABSTAIN_NO_CLUSTER" : diagDecision;

				// Umbral historico del bucket. SIN fallback global: sin historia => sin deteccion.
				double thresh = double.NaN;
				int histCount = 0;
				List<double> hist = HistoryScores(bucket);
				if (hist != null && hist.Count >= MinSamplesPerBucket)
				{
					hist.Sort();
					histCount = hist.Count;
					thresh = EmpiricalQuantile(hist, DetectionPercentile / 100.0);
				}
				diagThresh = thresh;
				diagHistCount = histCount;
				if (double.IsNaN(thresh)) diagDecision = "ABSTAIN_NO_HISTORY";

				double blockTotal = 0;
				foreach (double v in blockCells.Values) blockTotal += v;

				List<long> bestCluster = null;
				double bestPassScore = 0;
				foreach (List<long> cluster in clusters)
				{
					double score = 0;
					for (int i = 0; i < cluster.Count; i++) score += blockCells[cluster[i]];
					if (score > bestScore) bestScore = score;
					if (double.IsNaN(thresh) || thresh <= 0 || score < thresh) continue;
					if (bestCluster == null || score > bestPassScore)
					{
						bestCluster = cluster;
						bestPassScore = score;
					}
				}
				diagBestCluster = bestCluster;
				diagBestPassScore = bestPassScore;
				if (bestCluster == null && !double.IsNaN(thresh) && clusters.Count > 0)
					diagDecision = "ABSTAIN_BELOW_THRESHOLD";

				if (bestCluster != null)
				{
					long lower = bestCluster[0];
					long upper = bestCluster[bestCluster.Count - 1];
					long closeTick = PriceToTick(Close[0]);
					int direction = closeTick > upper ? 1 : (closeTick < lower ? -1 : 0);
					int distance = direction == 1 ? (int)(closeTick - upper)
						: (direction == -1 ? (int)(lower - closeTick) : 0);
					int width = (int)(upper - lower + 1);
					double ratio = bestPassScore / thresh;
					double share = blockTotal > 0 ? bestPassScore / blockTotal : 0;
					double density = width > 0 ? (double)bestCluster.Count / width : 0;
					int burstCount = CountNearbyCreations(lower + upper) + 1;
					double quality = ComputeQuality(ratio, share, density, distance, burstCount);
					bool offPrice = direction != 0;
					bool passes = offPrice && quality >= MinQualityScore;
					if (MaxDistanceFromZoneTicks > 0 && distance > MaxDistanceFromZoneTicks) passes = false;
					if (EnablePredictiveFilter && !passes)
					{
						/* filtro ON: no crea ni at-price ni off-price que no pase */
						diagDecision = offPrice ? "ABSTAIN_DISTANCE_OR_QUALITY_FILTER" : "ABSTAIN_AT_PRICE_FILTERED";
					}
					else
					{
						CreateZone(lower, upper, bestPassScore, bucket, thresh, histCount, direction,
							ratio, share, density, quality, distance, burstCount,
							offPrice ? "OFF_PRICE" : "AT_PRICE");
						diagDecision = "CREATE";
					}
				}
			}

			if (DiagBlockExportEnabled) EmitBlockDiag(bucket, diagMedian, diagHotThreshold,
				diagThresh, diagHistCount, diagClusters, diagBestCluster, diagBestPassScore, diagDecision);

			// La muestra del bloque entra SIEMPRE al pendiente de la sesion actual
			// (una muestra por bloque = score del mejor cluster; 0 si no hubo).
			List<double> pend;
			if (!pendingSession.TryGetValue(bucket, out pend))
			{
				pend = new List<double>();
				pendingSession[bucket] = pend;
			}
			pend.Add(bestScore);
		}

		private void CreateZone(long lowerTick, long upperTick, double score, int bucket,
		double threshold, int samples, int direction, double anomalyRatio,
		double clusterShare, double density, double quality, int distanceTicks, int burstCount,
		string kind)
		{
			Zone z = new Zone();
			z.Id = nextZoneId++;
			z.CreatedBar = CurrentBar;
			z.LowerTick = lowerTick;
			z.UpperTick = upperTick;
			z.Score = score;
			z.Bucket = bucket;
			z.TouchCount = 0;
			z.Active = true;
			z.Direction = direction;
			z.RefSide = direction;
			z.AnomalyRatio = anomalyRatio;
			z.ClusterShare = clusterShare;
			z.Density = density;
			z.QualityScore = quality;
			z.DistanceTicks = distanceTicks;
			z.BurstCount = burstCount;
			z.Outcome = "";
			z.Kind = kind;
			z.FirstTouchEmitted = false;

			totalZonesCreated++;
			sessionZonesCreated++;
			string dirName = kind == "AT_PRICE" ? "AT-PRICE" : (direction > 0 ? "SOPORTE" : "RESIST");
			double midPrice = ((lowerTick + upperTick) * 0.5) * TickSize;
			lastZoneInfo = dirName + "  Q" + quality.ToString("0", CultureInfo.InvariantCulture)
				+ "  R" + anomalyRatio.ToString("0.00", CultureInfo.InvariantCulture)
				+ "  @ " + Instrument.MasterInstrument.FormatPrice(midPrice);

			zones.Add(z);
			EmitEvent(kind == "AT_PRICE" ? "AT_PRICE_CREATED" : "ZONE_CREATED",
				z.Id, lowerTick, upperTick, score, threshold, samples, bucket, 0, kind);

			double lowerPrice = lowerTick * TickSize - TickSize * 0.5;
			double upperPrice = upperTick * TickSize + TickSize * 0.5;
			Brush zoneBrush = kind == "AT_PRICE" ? Brushes.SteelBlue
				: (direction > 0 ? Brushes.SeaGreen : Brushes.IndianRed);
			z.RectTag = "AVCLP_R" + z.Id.ToString(CultureInfo.InvariantCulture);
			Draw.Rectangle(this, z.RectTag, false, 0, lowerPrice, -VisualExtendBars, upperPrice,
				zoneBrush, zoneBrush, Opacity);
			TrackTag(z.RectTag);

			if (ShowScoreLabel)
			{
				z.LabelTag = "AVCLP_L" + z.Id.ToString(CultureInfo.InvariantCulture);
				string side = kind == "AT_PRICE" ? "OCC" : (direction > 0 ? "SOP" : "RES");
				string label = side + " Q" + quality.ToString("0", CultureInfo.InvariantCulture)
					+ " R" + anomalyRatio.ToString("0.00", CultureInfo.InvariantCulture);
				Draw.Text(this, z.LabelTag, label, 0, upperPrice + TickSize, zoneBrush);
				TrackTag(z.LabelTag);
			}

			Creation c = new Creation();
			c.Bar = CurrentBar;
			c.Center2 = lowerTick + upperTick;
			creations.Add(c);

			if (BurstMinZones > 0 && burstCount >= BurstMinZones)
			{
				string btag = "AVCLP_B" + z.Id.ToString(CultureInfo.InvariantCulture);
				Draw.Text(this, btag, "RAFAGA x" + burstCount.ToString(CultureInfo.InvariantCulture),
					0, upperPrice + 3 * TickSize, Brushes.Orange);
				TrackTag(btag);
			}
		}

		private int CountNearbyCreations(long center2)
		{
			while (creations.Count > 0 && CurrentBar - creations[0].Bar > BurstWindowBars)
				creations.RemoveAt(0);
			int near = 0;
			for (int i = 0; i < creations.Count; i++)
				if (Math.Abs(creations[i].Center2 - center2) <= 2L * BurstRangeTicks) near++;
			return near;
		}

		private double ComputeQuality(double ratio, double share, double density, int distance, int burstCount)
		{
			double anomaly = Clamp01((ratio - 1.0) / 0.50);
			double concentration = Clamp01(share / 0.20);
			double compactness = Clamp01(density);
			double rejection = Clamp01((double)distance / Math.Max(1, RejectionFullScoreTicks));
			double burst = BurstMinZones > 0 ? Clamp01((double)burstCount / BurstMinZones) : 0;
			return 100.0 * (0.35 * anomaly + 0.25 * concentration + 0.15 * compactness
				+ 0.15 * rejection + 0.10 * burst);
		}

		private static double Clamp01(double x)
		{
			if (x < 0) return 0;
			if (x > 1) return 1;
			return x;
		}

		// ------------------------------------------------------------------
		// Ciclo de vida (aritmetica entera, cero ULP por construccion)
		// ------------------------------------------------------------------
		private void ProcessLifecycle(long lowTick, long highTick, long closeTick)
		{
			for (int i = 0; i < zones.Count; i++)
			{
				Zone z = zones[i];
				if (z.CreatedBar >= CurrentBar) continue;
				if (z.Kind == "AT_PRICE") continue;

				if (z.OutcomeStarted && !z.OutcomeDone) UpdateOutcome(z, lowTick, highTick);
				if (!z.Active) continue;

				if (MaxAgeBars > 0 && CurrentBar - z.CreatedBar >= MaxAgeBars)
				{
					KillZone(z, "ZONE_EXPIRED", "max_age");
					continue;
				}

				bool touched = lowTick <= z.UpperTick && highTick >= z.LowerTick;
				if (touched)
				{
					z.TouchCount++;
					if (!z.FirstTouchEmitted)
					{
						z.FirstTouchEmitted = true;
						EmitEvent("FIRST_TOUCH", z.Id, z.LowerTick, z.UpperTick, z.Score, double.NaN, 0, z.Bucket, 1, "first_touch");
						if (!z.OutcomeStarted && z.Direction != 0)
						{
							z.OutcomeStarted = true;
							z.TouchBar = CurrentBar;
							UpdateOutcome(z, lowTick, highTick);
						}
					}
					if (InvalidationMode == AVCLPInvalidationMode.FirstTouch)
					{
						KillZone(z, "ZONE_INVALIDATED", "first_touch");
						continue;
					}
					if (MaxTouches > 0 && z.TouchCount >= MaxTouches)
					{
						KillZone(z, "ZONE_INVALIDATED", "max_touches");
						continue;
					}
				}

				if (InvalidationMode == AVCLPInvalidationMode.CloseThrough)
				{
					if (z.RefSide == 1 && closeTick < z.LowerTick)
					{
						KillZone(z, "ZONE_INVALIDATED", "close_through_down");
						continue;
					}
					if (z.RefSide == -1 && closeTick > z.UpperTick)
					{
						KillZone(z, "ZONE_INVALIDATED", "close_through_up");
						continue;
					}
				}
			}
		}

		private void UpdateOutcome(Zone z, long lowTick, long highTick)
		{
			int favorable;
			int adverse;
			if (z.Direction > 0)
			{
				favorable = (int)Math.Max(0, highTick - z.UpperTick);
				adverse = (int)Math.Max(0, z.UpperTick - lowTick);
			}
			else
			{
				favorable = (int)Math.Max(0, z.LowerTick - lowTick);
				adverse = (int)Math.Max(0, highTick - z.LowerTick);
			}
			if (favorable > z.MfeTicks) z.MfeTicks = favorable;
			if (adverse > z.MaeTicks) z.MaeTicks = adverse;

			bool hitTarget = favorable >= ReactionTargetTicks;
			bool hitStop = adverse >= ReactionStopTicks;
			if (hitTarget && hitStop) FinishOutcome(z, "AMBIGUOUS");
			else if (hitTarget) FinishOutcome(z, "TARGET");
			else if (hitStop) FinishOutcome(z, "STOP");
			else if (CurrentBar - z.TouchBar + 1 >= ReactionHorizonBars) FinishOutcome(z, "TIMEOUT");
		}

		private void FinishOutcome(Zone z, string outcome)
		{
			if (z.OutcomeDone) return;
			z.OutcomeDone = true;
			z.Outcome = outcome;
			if (outcome == "TARGET") outcomeTarget++;
			else if (outcome == "STOP") outcomeStop++;
			else if (outcome == "TIMEOUT") outcomeTimeout++;
			else outcomeAmbiguous++;
			if (ShowOutcomeLabels)
			{
				string tag = "AVCLP_O" + z.Id.ToString(CultureInfo.InvariantCulture);
				Brush b = outcome == "TARGET" ? Brushes.LimeGreen : (outcome == "STOP" ? Brushes.Red : Brushes.Gold);
				Draw.Text(this, tag, outcome, 0, z.UpperTick * TickSize + 2 * TickSize, b);
				TrackTag(tag);
			}
		}

		private void KillZone(Zone z, string type, string reason)
		{
			z.Active = false;
			EmitEvent(type, z.Id, z.LowerTick, z.UpperTick, z.Score, double.NaN, 0, z.Bucket, z.TouchCount, reason);
			if (RemoveInvalidatedZones)
			{
				if (z.RectTag != null) RemoveDrawObject(z.RectTag);
				if (z.LabelTag != null) RemoveDrawObject(z.LabelTag);
			}
			else if (z.RectTag != null)
			{
				// Redibuja la zona muerta acotada a su vida real, en gris apagado.
				// Asi el historial de zonas queda auditable en el grafico.
				double lowerPrice = z.LowerTick * TickSize - TickSize * 0.5;
				double upperPrice = z.UpperTick * TickSize + TickSize * 0.5;
				int startAgo = CurrentBar - z.CreatedBar;
				if (startAgo < 0) startAgo = 0;
				Draw.Rectangle(this, z.RectTag, false, startAgo, lowerPrice, 0, upperPrice,
					Brushes.Gray, Brushes.Gray, Math.Max(10, Opacity / 2));
			}
		}

		// ------------------------------------------------------------------
		// Perfil historico por sesiones completas
		// ------------------------------------------------------------------
		private void CommitSession()
		{
			if (sessionIndex >= 0 && pendingSession.Count > 0)
			{
				foreach (KeyValuePair<int, List<double>> kv in pendingSession)
				{
					List<Sample> hist;
					if (!bucketHistory.TryGetValue(kv.Key, out hist))
					{
						hist = new List<Sample>();
						bucketHistory[kv.Key] = hist;
					}
					for (int i = 0; i < kv.Value.Count; i++)
					{
						Sample s = new Sample();
						s.Session = sessionIndex;
						s.Score = kv.Value[i];
						hist.Add(s);
					}
				}
				// Poda FIFO por sesion
				int minSession = sessionIndex - LookbackSessions + 1;
				foreach (KeyValuePair<int, List<Sample>> kv in bucketHistory)
					kv.Value.RemoveAll(delegate(Sample s) { return s.Session < minSession; });
			}
			pendingSession.Clear();
		}

		private List<double> HistoryScores(int bucket)
		{
			List<Sample> hist;
			if (!bucketHistory.TryGetValue(bucket, out hist) || hist.Count == 0) return null;
			List<double> outList = new List<double>(hist.Count);
			for (int i = 0; i < hist.Count; i++) outList.Add(hist[i].Score);
			return outList;
		}

		// ------------------------------------------------------------------
		// Utilidades declaradas en el contrato
		// ------------------------------------------------------------------
		private long PriceToTick(double price)
		{
			double snapped = Instrument.MasterInstrument.RoundToTickSize(price);
			return (long)Math.Round(snapped / TickSize, MidpointRounding.AwayFromZero);
		}

		private int GetTimeBucket(DateTime barCloseTime)
		{
			DateTime anchor = barCloseTime.AddSeconds(-1);
			if (UseSessionBuckets && sessionBegin != DateTime.MinValue && anchor >= sessionBegin)
			{
				double mins = (anchor - sessionBegin).TotalMinutes;
				return (int)(mins / TimeBucketMinutes);
			}
			return (anchor.Hour * 60 + anchor.Minute) / TimeBucketMinutes;
		}

		// Cuantil empirico sin interpolacion: menor v tal que count(<=v) >= ceil(p*n)
		private static double EmpiricalQuantile(List<double> sortedAsc, double p)
		{
			int n = sortedAsc.Count;
			int k = (int)Math.Ceiling(p * n);
			if (k < 1) k = 1;
			if (k > n) k = n;
			return sortedAsc[k - 1];
		}

		// ------------------------------------------------------------------
		// Dashboard explicativo (SOLO visual; no afecta deteccion ni export)
		// ------------------------------------------------------------------
		private void UpdateDashboard()
		{
			int bucketsReady = 0;
			int totalSamples = 0;
			foreach (KeyValuePair<int, List<Sample>> kv in bucketHistory)
			{
				totalSamples += kv.Value.Count;
				if (kv.Value.Count >= MinSamplesPerBucket) bucketsReady++;
			}

			int activeZones = 0;
			int activeLong = 0;
			int activeShort = 0;
			for (int i = 0; i < zones.Count; i++)
			{
				if (!zones[i].Active) continue;
				activeZones++;
				if (zones[i].Direction > 0) activeLong++;
				else if (zones[i].Direction < 0) activeShort++;
			}

			StringBuilder sb = new StringBuilder(640);
			sb.Append("aVolClusterPOI v0.5 - off-price vs at-price\n");
			sb.Append("---------------------------------------------\n");

			if (sessionIndex < 0)
				sb.Append("ESTADO: ESPERANDO 1ra SESION COMPLETA (aun sin perfil)\n");
			else if (bucketsReady == 0)
				sb.Append("ESTADO: CALENTANDO - juntando historial, todavia no detecta\n");
			else
				sb.Append("ESTADO: ACTIVO - " + bucketsReady + " franjas horarias listas\n");

			sb.Append("Sesiones completas: " + (sessionIndex < 0 ? 0 : sessionIndex)
				+ " / " + LookbackSessions + " | Muestras: " + totalSamples + "\n");
			sb.Append("Zonas activas: " + activeZones + " (" + activeLong + " soporte / "
				+ activeShort + " resistencia)\n");
			sb.Append("Creadas: " + sessionZonesCreated + " en la sesion | "
				+ totalZonesCreated + " en total\n");

			int evaluated = outcomeTarget + outcomeStop;
			sb.Append("Reacciones: " + outcomeTarget + " target / " + outcomeStop + " stop / "
				+ outcomeTimeout + " timeout / " + outcomeAmbiguous + " ambiguas\n");
			if (evaluated > 0)
				sb.Append("Aciertos (target vs stop): "
					+ (100.0 * outcomeTarget / evaluated).ToString("0", CultureInfo.InvariantCulture)
					+ "% sobre " + evaluated + " evaluadas\n");
			if (!string.IsNullOrEmpty(lastZoneInfo))
				sb.Append("Ultima zona: " + lastZoneInfo + "\n");

			sb.Append("---------------------------------------------\n");
			sb.Append("COMO LEERLO:\n");
			sb.Append("VERDE = soporte esperado (precio cerro ARRIBA de la zona)\n");
			sb.Append("ROJO  = resistencia esperada (precio cerro DEBAJO)\n");
			sb.Append("GRIS  = zona ya invalidada (historial auditable)\n");
			sb.Append("Q = calidad 0-100 (ranking heuristico, NO probabilidad)\n");
			sb.Append("R = volumen del cluster / umbral historico del horario\n");
			sb.Append(EnablePredictiveFilter
				? "Filtro: solo zonas con Q >= " + MinQualityScore.ToString("0", CultureInfo.InvariantCulture) + "\n"
				: "Filtro predictivo: OFF (muestra todo)\n");
			sb.Append("Test tras 1er toque: target " + ReactionTargetTicks + "t / stop "
				+ ReactionStopTicks + "t / " + ReactionHorizonBars + " barras");

			Draw.TextFixed(this, "AVCLP_DASH", sb.ToString(), ToTextPosition(DashboardCorner),
				Brushes.White, dashFont, Brushes.DimGray, Brushes.Black, 60);
		}

		private TextPosition ToTextPosition(AVCLPDashboardCorner corner)
		{
			switch (corner)
			{
				case AVCLPDashboardCorner.TopLeft: return TextPosition.TopLeft;
				case AVCLPDashboardCorner.BottomRight: return TextPosition.BottomRight;
				case AVCLPDashboardCorner.BottomLeft: return TextPosition.BottomLeft;
				default: return TextPosition.TopRight;
			}
		}

		private void TrackTag(string tag)
		{
			renderedTags.Enqueue(tag);
			while (renderedTags.Count > MaxRenderedZones)
				RemoveDrawObject(renderedTags.Dequeue());
		}

		// ------------------------------------------------------------------
		// Export CSV (sobreescribe siempre; nunca append)
		// ------------------------------------------------------------------
		private void EmitEvent(string type, long zoneId, long lowerTick, long upperTick,
			double score, double threshold, int samples, int bucket, int touchCount, string reason)
		{
			if (string.IsNullOrEmpty(EventLogPath) || writerFailed) return;
			try
			{
				if (writer == null)
				{
					string dir = Path.GetDirectoryName(EventLogPath);
					if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
					writer = new StreamWriter(EventLogPath, false, new UTF8Encoding(false));
					writer.AutoFlush = true;
					writer.WriteLine("# meta,indicator=aVolClusterPOI,version=0.5,instrument=" + Instrument.FullName
						+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
						+ ",window_bars=" + WindowBars.ToString(CultureInfo.InvariantCulture)
						+ ",median_mult=" + MedianMultiplier.ToString(CultureInfo.InvariantCulture)
						+ ",max_gap_ticks=" + MaxGapTicks.ToString(CultureInfo.InvariantCulture)
						+ ",min_cluster_ticks=" + MinClusterTicks.ToString(CultureInfo.InvariantCulture)
						+ ",bucket_minutes=" + TimeBucketMinutes.ToString(CultureInfo.InvariantCulture)
						+ ",percentile=" + DetectionPercentile.ToString(CultureInfo.InvariantCulture)
						+ ",lookback_sessions=" + LookbackSessions.ToString(CultureInfo.InvariantCulture)
						+ ",min_samples=" + MinSamplesPerBucket.ToString(CultureInfo.InvariantCulture)
						+ ",predictive_filter=" + (EnablePredictiveFilter ? "1" : "0")
						+ ",min_quality=" + MinQualityScore.ToString(CultureInfo.InvariantCulture)
						+ ",reaction_horizon=" + ReactionHorizonBars.ToString(CultureInfo.InvariantCulture)
						+ ",reaction_target_ticks=" + ReactionTargetTicks.ToString(CultureInfo.InvariantCulture)
						+ ",reaction_stop_ticks=" + ReactionStopTicks.ToString(CultureInfo.InvariantCulture)
						+ ",quality_formula=heuristic_v1_not_probability"
						+ ",session_buckets=" + (UseSessionBuckets ? "1" : "0")
						+ ",invalidation=" + InvalidationMode.ToString()
						+ ",max_age_bars=" + MaxAgeBars.ToString(CultureInfo.InvariantCulture)
						+ ",max_touches=" + MaxTouches.ToString(CultureInfo.InvariantCulture)
						+ ",one_cluster_per_block=1,kinds=OFF_PRICE|AT_PRICE,export=ZONE_CREATED|AT_PRICE_CREATED|FIRST_TOUCH|ZONE_INVALIDATED,footprint=reconstructed_1tick_subseries,quantile=empirical_no_interp,write_mode=overwrite");
					writer.WriteLine("event_seq,event_type,bar_index,bar_close_time,session_index,bucket,"
						+ "zone_id,lower_tick,upper_tick,score,threshold,samples,touch_count,reason,"
						+ "direction,anomaly_ratio,cluster_share,density,quality_score,distance_ticks,burst_count,"
						+ "touch_bar,mfe_ticks,mae_ticks,outcome");
					Print(Name + " log de eventos: " + EventLogPath);
				}
				eventSeq++;
				Zone ez = null;
				for (int zi = 0; zi < zones.Count; zi++)
					if (zones[zi].Id == zoneId) { ez = zones[zi]; break; }
				string direction = ez == null ? "" : (ez.Direction > 0 ? "LONG" : (ez.Direction < 0 ? "SHORT" : "NEUTRAL"));
				writer.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24}",
					eventSeq, type, CurrentBar,
					Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					sessionIndex, bucket, zoneId, lowerTick, upperTick,
					score.ToString("0.######", CultureInfo.InvariantCulture),
					double.IsNaN(threshold) ? "" : threshold.ToString("0.######", CultureInfo.InvariantCulture),
					samples, touchCount, reason, direction,
					ez == null ? "" : ez.AnomalyRatio.ToString("0.######", CultureInfo.InvariantCulture),
					ez == null ? "" : ez.ClusterShare.ToString("0.######", CultureInfo.InvariantCulture),
					ez == null ? "" : ez.Density.ToString("0.######", CultureInfo.InvariantCulture),
					ez == null ? "" : ez.QualityScore.ToString("0.##", CultureInfo.InvariantCulture),
					ez == null ? "" : ez.DistanceTicks.ToString(CultureInfo.InvariantCulture),
					ez == null ? "" : ez.BurstCount.ToString(CultureInfo.InvariantCulture),
					ez == null || !ez.OutcomeStarted ? "" : ez.TouchBar.ToString(CultureInfo.InvariantCulture),
					ez == null ? "" : ez.MfeTicks.ToString(CultureInfo.InvariantCulture),
					ez == null ? "" : ez.MaeTicks.ToString(CultureInfo.InvariantCulture),
					ez == null ? "" : ez.Outcome));
			}
			catch (Exception ex)
			{
				writerFailed = true;
				Print(Name + " ERROR [event_log]: " + ex.Message);
			}
		}

		// ------------------------------------------------------------------
		// Export CSV diagnostico por bloque (opcional, off por defecto).
		// Un renglon por bloque procesado, CREATE o ABSTAIN, con las celdas
		// crudas, la mediana/umbral, todos los clusters candidatos y el
		// elegido. No participa de la deteccion -- solo lectura de variables
		// ya calculadas en ProcessBlock(). Pensado para research target-free
		// (paridad Python<->NT8), no para produccion; dejar DiagBlockExportEnabled
		// en false salvo corrida de auditoria explicita.
		// ------------------------------------------------------------------
		private void EmitBlockDiag(int bucket, double median, double hotThreshold,
			double thresh, int histCount, List<List<long>> clusters, List<long> bestCluster,
			double bestPassScore, string decision)
		{
			if (string.IsNullOrEmpty(DiagBlockExportPath) || diagWriterFailed) return;
			try
			{
				if (diagWriter == null)
				{
					string dir = Path.GetDirectoryName(DiagBlockExportPath);
					if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
					diagWriter = new StreamWriter(DiagBlockExportPath, false, new UTF8Encoding(false));
					diagWriter.AutoFlush = true;
					diagWriter.WriteLine("# meta,indicator=aVolClusterPOI,version=0.5,mode=block_diagnostic,"
						+ "instrument=" + Instrument.FullName
						+ ",tick_size=" + TickSize.ToString(CultureInfo.InvariantCulture)
						+ ",window_bars=" + WindowBars.ToString(CultureInfo.InvariantCulture)
						+ ",median_mult=" + MedianMultiplier.ToString(CultureInfo.InvariantCulture)
						+ ",max_gap_ticks=" + MaxGapTicks.ToString(CultureInfo.InvariantCulture)
						+ ",min_cluster_ticks=" + MinClusterTicks.ToString(CultureInfo.InvariantCulture)
						+ ",bucket_minutes=" + TimeBucketMinutes.ToString(CultureInfo.InvariantCulture)
						+ ",percentile=" + DetectionPercentile.ToString(CultureInfo.InvariantCulture)
						+ ",lookback_sessions=" + LookbackSessions.ToString(CultureInfo.InvariantCulture)
						+ ",min_samples=" + MinSamplesPerBucket.ToString(CultureInfo.InvariantCulture)
						+ ",cells_format=tick:vol pipe-separated, sorted by tick asc"
						+ ",clusters_format=lower:upper:score:count pipe-separated, in discovery order"
						+ ",write_mode=overwrite,scope=every_block_CREATE_and_ABSTAIN");
					diagWriter.WriteLine("diag_seq,bar_index,bar_close_time,session_index,bucket,"
						+ "n_cells,median,hot_threshold,best_score,threshold,hist_samples,decision,"
						+ "selected_lower_tick,selected_upper_tick,selected_score,selected_count,"
						+ "n_clusters,clusters,cells");
					Print(Name + " log diagnostico por bloque: " + DiagBlockExportPath);
				}
				diagSeq++;

				List<long> cellTicks = new List<long>(blockCells.Keys);
				cellTicks.Sort();
				StringBuilder cellsSb = new StringBuilder();
				for (int i = 0; i < cellTicks.Count; i++)
				{
					if (i > 0) cellsSb.Append('|');
					cellsSb.Append(cellTicks[i].ToString(CultureInfo.InvariantCulture));
					cellsSb.Append(':');
					cellsSb.Append(blockCells[cellTicks[i]].ToString("0.######", CultureInfo.InvariantCulture));
				}

				StringBuilder clustersSb = new StringBuilder();
				int nClusters = clusters == null ? 0 : clusters.Count;
				if (clusters != null)
				{
					for (int ci = 0; ci < clusters.Count; ci++)
					{
						List<long> c = clusters[ci];
						double cScore = 0;
						for (int i = 0; i < c.Count; i++) cScore += blockCells[c[i]];
						if (ci > 0) clustersSb.Append('|');
						clustersSb.Append(c[0]).Append(':').Append(c[c.Count - 1]).Append(':')
							.Append(cScore.ToString("0.######", CultureInfo.InvariantCulture)).Append(':')
							.Append(c.Count);
					}
				}

				diagWriter.WriteLine(string.Format(CultureInfo.InvariantCulture,
					"{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18}",
					diagSeq, CurrentBar,
					Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
					sessionIndex, bucket,
					blockCells.Count,
					double.IsNaN(median) ? "" : median.ToString("0.######", CultureInfo.InvariantCulture),
					double.IsNaN(hotThreshold) ? "" : hotThreshold.ToString("0.######", CultureInfo.InvariantCulture),
					bestPassScore.ToString("0.######", CultureInfo.InvariantCulture),
					double.IsNaN(thresh) ? "" : thresh.ToString("0.######", CultureInfo.InvariantCulture),
					histCount, decision,
					bestCluster == null ? "" : bestCluster[0].ToString(CultureInfo.InvariantCulture),
					bestCluster == null ? "" : bestCluster[bestCluster.Count - 1].ToString(CultureInfo.InvariantCulture),
					bestCluster == null ? "" : bestPassScore.ToString("0.######", CultureInfo.InvariantCulture),
					bestCluster == null ? "" : bestCluster.Count.ToString(CultureInfo.InvariantCulture),
					nClusters, clustersSb.ToString(), cellsSb.ToString()));
			}
			catch (Exception ex)
			{
				diagWriterFailed = true;
				Print(Name + " ERROR [block_diag]: " + ex.Message);
			}
		}

		#region Properties

		// -------- Grupo 1: Deteccion (bloque) --------
		[NinjaScriptProperty]
		[Range(2, 500)]
		[Display(Name = "Window Bars (bloque)", Order = 1, GroupName = "1. Deteccion",
			Description = "Barras primarias por bloque. El contador se reinicia al inicio de sesion.")]
		public int WindowBars { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 100.0)]
		[Display(Name = "Median Multiplier", Order = 2, GroupName = "1. Deteccion",
			Description = "Un nivel es hot si su volumen >= mediana del bloque x este valor.")]
		public double MedianMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0, 50)]
		[Display(Name = "Max Gap Ticks", Order = 3, GroupName = "1. Deteccion",
			Description = "Separacion maxima (en ticks enteros) entre niveles hot del mismo cluster.")]
		public int MaxGapTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Min Cluster Ticks", Order = 4, GroupName = "1. Deteccion")]
		public int MinClusterTicks { get; set; }

		// -------- Grupo 2: Perfil horario --------
		[NinjaScriptProperty]
		[Display(Name = "Session Relative Buckets", Order = 10, GroupName = "2. Perfil horario",
			Description = "true: buckets desde el inicio real de sesion. false: reloj de pared.")]
		public bool UseSessionBuckets { get; set; }

		[NinjaScriptProperty]
		[Range(1, 1440)]
		[Display(Name = "Time Bucket (minutos)", Order = 11, GroupName = "2. Perfil horario")]
		public int TimeBucketMinutes { get; set; }

		[NinjaScriptProperty]
		[Range(1, 200)]
		[Display(Name = "Lookback Sessions", Order = 12, GroupName = "2. Perfil horario",
			Description = "FIFO por sesion completa. La sesion actual nunca entra al perfil.")]
		public int LookbackSessions { get; set; }

		[NinjaScriptProperty]
		[Range(50.0, 100.0)]
		[Display(Name = "Detection Percentile", Order = 13, GroupName = "2. Perfil horario")]
		public double DetectionPercentile { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Min Samples Per Bucket", Order = 14, GroupName = "2. Perfil horario",
			Description = "Sin esta cantidad de muestras historicas en el bucket, no se detecta (sin fallback global).")]
		public int MinSamplesPerBucket { get; set; }

		// -------- Grupo 3: Ranking y evaluacion predictiva --------
		[NinjaScriptProperty]
		[Display(Name = "Enable Predictive Filter", Order = 20, GroupName = "3. Ranking predictivo",
			Description = "Solo dibuja zonas direccionales que superan Quality Score y distancia maxima.")]
		public bool EnablePredictiveFilter { get; set; }

		[NinjaScriptProperty]
		[Range(0.0, 100.0)]
		[Display(Name = "Min Quality Score", Order = 21, GroupName = "3. Ranking predictivo",
			Description = "Ranking heuristico causal, no probabilidad calibrada.")]
		public double MinQualityScore { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100000)]
		[Display(Name = "Max Distance From Zone (ticks, 0=off)", Order = 22, GroupName = "3. Ranking predictivo")]
		public int MaxDistanceFromZoneTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 10000)]
		[Display(Name = "Rejection Full Score (ticks)", Order = 23, GroupName = "3. Ranking predictivo")]
		public int RejectionFullScoreTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Reaction Horizon (bars)", Order = 24, GroupName = "3. Ranking predictivo")]
		public int ReactionHorizonBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Reaction Target (ticks)", Order = 25, GroupName = "3. Ranking predictivo")]
		public int ReactionTargetTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Reaction Stop (ticks)", Order = 26, GroupName = "3. Ranking predictivo")]
		public int ReactionStopTicks { get; set; }

		// -------- Grupo 4: Ciclo de vida --------
		[NinjaScriptProperty]
		[Display(Name = "Invalidation Mode", Order = 20, GroupName = "4. Ciclo de vida")]
		public AVCLPInvalidationMode InvalidationMode { get; set; }

		[NinjaScriptProperty]
		[Range(0, 100000)]
		[Display(Name = "Max Age (barras, 0 = sin expiracion)", Order = 21, GroupName = "4. Ciclo de vida")]
		public int MaxAgeBars { get; set; }

		[NinjaScriptProperty]
		[Range(0, 1000)]
		[Display(Name = "Max Touches (0 = ilimitado)", Order = 22, GroupName = "4. Ciclo de vida")]
		public int MaxTouches { get; set; }

		// -------- Grupo 5: Alerta de rafaga --------
		[NinjaScriptProperty]
		[Range(0, 100)]
		[Display(Name = "Burst Min Zones (0 = off)", Order = 30, GroupName = "5. Alerta de rafaga",
			Description = "Minimo de zonas creadas en la ventana y rango para marcar rafaga.")]
		public int BurstMinZones { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Burst Window (barras)", Order = 31, GroupName = "5. Alerta de rafaga")]
		public int BurstWindowBars { get; set; }

		[NinjaScriptProperty]
		[Range(1, 10000)]
		[Display(Name = "Burst Range (ticks)", Order = 32, GroupName = "5. Alerta de rafaga")]
		public int BurstRangeTicks { get; set; }

		// -------- Grupo 6: Export y visual --------
		[NinjaScriptProperty]
		[Display(Name = "Event Log Path (vacio = off)", Order = 40, GroupName = "6. Export y visual",
			Description = "Ruta completa del CSV. SOBREESCRIBE siempre; usar nombre nuevo por corrida.")]
		public string EventLogPath { get; set; }

		// -------- Grupo 9: Diagnostico por bloque (opcional, research/paridad) --------
		[NinjaScriptProperty]
		[Display(Name = "Diag Block Export Enabled", Order = 90, GroupName = "9. Diagnostico (opcional)",
			Description = "Exporta un CSV con 1 fila por bloque (CREATE y ABSTAIN), con blockCells crudo, "
				+ "mediana/umbral y todos los clusters candidatos. Off por defecto -- solo para research "
				+ "de paridad, no cambia la deteccion en produccion.")]
		public bool DiagBlockExportEnabled { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Diag Block Export Path (vacio = off)", Order = 91, GroupName = "9. Diagnostico (opcional)",
			Description = "Ruta completa del CSV diagnostico. SOBREESCRIBE siempre; usar nombre nuevo por corrida.")]
		public string DiagBlockExportPath { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name = "Opacity", Order = 41, GroupName = "6. Export y visual")]
		public int Opacity { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100000)]
		[Display(Name = "Visual Extend Bars", Order = 42, GroupName = "6. Export y visual")]
		public int VisualExtendBars { get; set; }

		[NinjaScriptProperty]
		[Range(10, 100000)]
		[Display(Name = "Max Rendered Zones", Order = 43, GroupName = "6. Export y visual",
			Description = "Limita SOLO el dibujo; nunca borra zonas del estado interno.")]
		public int MaxRenderedZones { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Remove Invalidated Zones", Order = 44, GroupName = "6. Export y visual",
			Description = "false (default): las zonas muertas quedan en gris acotadas a su vida real. true: se borran del grafico.")]
		public bool RemoveInvalidatedZones { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Score Label", Order = 45, GroupName = "6. Export y visual")]
		public bool ShowScoreLabel { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Outcome Labels", Order = 46, GroupName = "6. Export y visual",
			Description = "Muestra TARGET/STOP/TIMEOUT/AMBIGUOUS al completar la evaluacion forward.")]
		public bool ShowOutcomeLabels { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Show Dashboard", Order = 47, GroupName = "6. Export y visual",
			Description = "Panel fijo en una esquina con estado, conteos y leyenda de lectura.")]
		public bool ShowDashboard { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Dashboard Corner", Order = 48, GroupName = "6. Export y visual")]
		public AVCLPDashboardCorner DashboardCorner { get; set; }

		#endregion
	}
}
