#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
	public class ZonasDeGaps : Indicator
	{
		private readonly List<GapZone> gapZones = new List<GapZone>();
		private readonly List<ClusterZone> clusterZones = new List<ClusterZone>();
		private readonly List<PendingGap> pendingGaps = new List<PendingGap>();
		private int lastProcessedBar = -1;
		private readonly Dictionary<int, int> tickToSeriesIndex = new Dictionary<int, int>();
		private readonly Dictionary<int, int> secondsToSeriesIndex = new Dictionary<int, int>();
		private readonly Dictionary<int, int> minutesToSeriesIndex = new Dictionary<int, int>();
		private readonly List<int> validationSeriesIndices = new List<int>();
		private int sourceSeriesIndex = 0;
		private int nextGapToDrawIndex = 0;
		private const int MaxNewRectanglesPerBar = 250;
		private const int MaxStoredGaps = 20000;
		private const int MaxGapFreeSpaceTicksInCluster = 2;
		private Brush clusterZoneFillBrush;
		private const int MaxPendingGaps = 20000;

		private sealed class GapZone
		{
			public int StartBarIndex { get; set; }
			public int EndBarIndex { get; set; } // Solo se usa para el largo visual del dibujo
			public double Low { get; set; }
			public double High { get; set; }
			public double Mid { get; set; }
			public string RectTag { get; set; }
			public bool IsDrawn { get; set; }
            
            public int CurrentOpacity { get; set; }
            public bool IsPriceAway { get; set; } 
		}

		private sealed class ClusterZone
		{
			public int StartBarIndex { get; set; }
			public int EndBarIndex { get; set; }
			public double Low { get; set; }
			public double High { get; set; }
			public string Tag { get; set; }
		}

		private sealed class PendingGap
		{
			public int CreatedSourceBarIndex { get; set; }
			public DateTime ReferenceTime { get; set; }
			public int MainBarIndex { get; set; }
			public int ExtendBarsRightAtCreation { get; set; }
			public double Low { get; set; }
			public double High { get; set; }
			public double Mid { get; set; }
			public string RectTag { get; set; }
		}

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "Marca zonas de gaps. La memoria del nivel de precio es infinita hasta que se rellena, independientemente del largo del dibujo.";
				Name = "ZonasDeGaps";
				
                Calculate = Calculate.OnEachTick; 
				
                IsOverlay = true;
				DisplayInDataBox = true;
				DrawOnPricePanel = true;
				PaintPriceMarkers = true;
				ScaleJustification = NinjaTrader.Gui.Chart.ScaleJustification.Right;
				IsSuspendedWhileInactive = true;

				MinGapPoints = 0;
				ExtendBarsRight = 10; // Reducido por defecto para gráficos más limpios
				MinGapsForCluster = 9;
				ClusterHeightTicks = 5;
				ClusterLineExtension = 500;
				ConfirmarNoRellenadoVelaSiguiente = false;
                
                InitialGapOpacity = 30;
                OpacityDropPerTouch = 30; 
                AwayDistanceTicks = 10;   

				Validate1Tick = false;
				Validate2Tick = false;
				Validate3Tick = false;
				Validate5Tick = false;
				Validate10Tick = false;
				Validate15Tick = false;
				Validate25Tick = false;
				Validate50Tick = false;
				Validate100Tick = false;
				Validate200Tick = false;
				Validate500Tick = false;

				ValidateS1 = false;
				ValidateS5 = false;
				ValidateS25 = false;
				Validate1Min = false;
				Validate5Min = false;
			}
			else if (State == State.DataLoaded)
			{
				SolidColorBrush fill = new SolidColorBrush(Color.FromArgb(40, 255, 0, 0));
				fill.Freeze();
				clusterZoneFillBrush = fill;
			}
			else if (State == State.Configure)
			{
				validationSeriesIndices.Clear();
				tickToSeriesIndex.Clear();
				secondsToSeriesIndex.Clear();
				minutesToSeriesIndex.Clear();

				int seriesIdx = 1;
				if (Validate1Tick) { AddDataSeries(BarsPeriodType.Tick, 1); tickToSeriesIndex[1] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate2Tick) { AddDataSeries(BarsPeriodType.Tick, 2); tickToSeriesIndex[2] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate3Tick) { AddDataSeries(BarsPeriodType.Tick, 3); tickToSeriesIndex[3] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate5Tick) { AddDataSeries(BarsPeriodType.Tick, 5); tickToSeriesIndex[5] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate10Tick) { AddDataSeries(BarsPeriodType.Tick, 10); tickToSeriesIndex[10] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate15Tick) { AddDataSeries(BarsPeriodType.Tick, 15); tickToSeriesIndex[15] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate25Tick) { AddDataSeries(BarsPeriodType.Tick, 25); tickToSeriesIndex[25] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate50Tick) { AddDataSeries(BarsPeriodType.Tick, 50); tickToSeriesIndex[50] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate100Tick) { AddDataSeries(BarsPeriodType.Tick, 100); tickToSeriesIndex[100] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate200Tick) { AddDataSeries(BarsPeriodType.Tick, 200); tickToSeriesIndex[200] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate500Tick) { AddDataSeries(BarsPeriodType.Tick, 500); tickToSeriesIndex[500] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }

				if (ValidateS1) { AddDataSeries(BarsPeriodType.Second, 1); secondsToSeriesIndex[1] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (ValidateS5) { AddDataSeries(BarsPeriodType.Second, 5); secondsToSeriesIndex[5] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (ValidateS25) { AddDataSeries(BarsPeriodType.Second, 25); secondsToSeriesIndex[25] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate1Min) { AddDataSeries(BarsPeriodType.Minute, 1); minutesToSeriesIndex[1] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }
				if (Validate5Min) { AddDataSeries(BarsPeriodType.Minute, 5); minutesToSeriesIndex[5] = seriesIdx; validationSeriesIndices.Add(seriesIdx); seriesIdx++; }

				sourceSeriesIndex = 0;
				if (tickToSeriesIndex.Count > 0)
				{
					int minTick = int.MaxValue;
					foreach (var kvp in tickToSeriesIndex)
						minTick = Math.Min(minTick, kvp.Key);
					sourceSeriesIndex = tickToSeriesIndex[minTick];
				}
				else if (secondsToSeriesIndex.Count > 0)
				{
					int minSec = int.MaxValue;
					foreach (var kvp in secondsToSeriesIndex)
						minSec = Math.Min(minSec, kvp.Key);
					sourceSeriesIndex = secondsToSeriesIndex[minSec];
				}
				else if (minutesToSeriesIndex.Count > 0)
				{
					int minMin = int.MaxValue;
					foreach (var kvp in minutesToSeriesIndex)
						minMin = Math.Min(minMin, kvp.Key);
					sourceSeriesIndex = minutesToSeriesIndex[minMin];
				}
			}
		}

		protected override void OnBarUpdate()
		{
			// 1) Detección de Gaps
			if (BarsInProgress == sourceSeriesIndex)
			{
				if (CurrentBars[sourceSeriesIndex] < 1)
					return;

                if (IsFirstTickOfBar)
                {
				    ProcessPendingGaps();

				    if (validationSeriesIndices.Count > 0)
				    {
					    for (int i = 0; i < validationSeriesIndices.Count; i++)
					    {
						    int seriesIdx = validationSeriesIndices[i];
						    if (CurrentBars[seriesIdx] < 1)
							    return;
					    }
				    }

				    double prevClose = Instrument.MasterInstrument.RoundToTickSize(Closes[sourceSeriesIndex][1]);
				    double currOpen = Instrument.MasterInstrument.RoundToTickSize(Opens[sourceSeriesIndex][0]);

				    if (prevClose != currOpen)
                    {
				        double gapSize = Math.Abs(currOpen - prevClose);
				        if (gapSize >= MinGapPoints * TickSize)
                        {
				            DateTime referenceTime = Times[sourceSeriesIndex][0];
				            if (validationSeriesIndices.Count <= 1 || GapExistsInAllTimeframes(referenceTime, prevClose, currOpen, sourceSeriesIndex))
                            {
				                int mainBarIndex = BarsArray[0].GetBar(referenceTime);
				                if (mainBarIndex >= 0)
                                {
				                    double gapLow = Math.Min(prevClose, currOpen);
				                    double gapHigh = Math.Max(prevClose, currOpen);
				                    double gapMid = (gapLow + gapHigh) / 2.0;

				                    string rectTag = "GapRect_" + sourceSeriesIndex + "_" + CurrentBar;
				                    int extendAtCreation = Math.Max(ExtendBarsRight, 0);

				                    if (ConfirmarNoRellenadoVelaSiguiente)
				                    {
					                    pendingGaps.Add(new PendingGap
					                    {
						                    CreatedSourceBarIndex = CurrentBar,
						                    ReferenceTime = referenceTime,
						                    MainBarIndex = mainBarIndex,
						                    ExtendBarsRightAtCreation = extendAtCreation,
						                    Low = gapLow,
						                    High = gapHigh,
						                    Mid = gapMid,
						                    RectTag = rectTag
					                    });
					                    if (pendingGaps.Count > MaxPendingGaps)
						                    pendingGaps.RemoveRange(0, pendingGaps.Count - MaxPendingGaps);
				                    }
				                    else
				                    {
					                    GapZone newGap = new GapZone
					                    {
						                    StartBarIndex = mainBarIndex,
						                    EndBarIndex = mainBarIndex + extendAtCreation,
						                    Low = gapLow,
						                    High = gapHigh,
						                    Mid = gapMid,
						                    RectTag = rectTag,
						                    IsDrawn = false,
                                            CurrentOpacity = InitialGapOpacity,
                                            IsPriceAway = false 
					                    };

					                    gapZones.Add(newGap);
					                    
                                        // Mantenemos a raya el consumo de memoria
                                        if (gapZones.Count > MaxStoredGaps)
					                    {
						                    int removeCount = gapZones.Count - MaxStoredGaps;
						                    gapZones.RemoveRange(0, removeCount);
						                    nextGapToDrawIndex = Math.Max(0, nextGapToDrawIndex - removeCount);
					                    }
				                    }
                                }
                            }
                        }
                    }
                }
				if (sourceSeriesIndex != 0)
					return;
			}

			// 2) Gráfico Principal y Lógica de Re-Testeos
			if (BarsInProgress != 0 || CurrentBar < 1)
				return;

            double currentHigh = High[0];
            double currentLow = Low[0];
            double currentClose = Close[0];

            for (int i = 0; i < gapZones.Count; i++)
            {
                GapZone g = gapZones[i];
                
                // NOTA IMPORTANTE: Ahora evalúa TODO gap que haya nacido antes o durante esta vela y que siga vivo (Opacity > 0).
                // Ya NO le importa si la vela actual es mayor al EndBarIndex del dibujo.
                // FIX BUG 3 (EdgeLab 2026-10-25): evaluar re-testeos y alejamiento estrictamente después de la barra creadora (< CurrentBar)
                if (g.StartBarIndex < CurrentBar && g.CurrentOpacity > 0)
                {
                    double upperAwayBoundary = g.High + (AwayDistanceTicks * TickSize);
                    double lowerAwayBoundary = g.Low - (AwayDistanceTicks * TickSize);

                    bool touchesGap = currentLow <= g.High && currentHigh >= g.Low;

                    // PASO A: Ejecutar el descuento
                    if (g.IsPriceAway && touchesGap)
                    {
                        g.CurrentOpacity = Math.Max(0, g.CurrentOpacity - OpacityDropPerTouch);
                        g.IsPriceAway = false; 

                        // Destrucción del gap si llega a 0
                        if (g.CurrentOpacity <= 0)
                        {
                            RemoveDrawObject(g.RectTag);
                            g.IsDrawn = false;
                        }
                        else if (g.IsDrawn)
                        {
                            // Actualizamos opacidad del dibujo
                            var rect = DrawObjects[g.RectTag] as NinjaTrader.NinjaScript.DrawingTools.Rectangle;
                            if (rect != null)
                            {
                                rect.AreaOpacity = g.CurrentOpacity;
                            }
                            else
                            {
                                int startBarsAgo = CurrentBar - g.StartBarIndex;
                                int endBarsAgo = CurrentBar - g.EndBarIndex;
                                Draw.Rectangle(this, g.RectTag, false, startBarsAgo, g.High, endBarsAgo, g.Low, Brushes.Transparent, Brushes.LightSkyBlue, g.CurrentOpacity);
                            }
                        }
                    }

                    // PASO B: Actualizar estado de "Alejamiento"
                    if (currentClose >= upperAwayBoundary || currentClose <= lowerAwayBoundary)
                    {
                        g.IsPriceAway = true;
                    }
                    else if (touchesGap)
                    {
                        g.IsPriceAway = false;
                    }
                }
            }

            // Dibujo de nuevos Gaps al cerrar la vela
            if (IsFirstTickOfBar)
            {
			    int drawnThisBar = 0;
			    while (nextGapToDrawIndex < gapZones.Count && drawnThisBar < MaxNewRectanglesPerBar)
			    {
				    GapZone g = gapZones[nextGapToDrawIndex];
				    if (g.StartBarIndex > CurrentBar)
					    break;

				    if (!g.IsDrawn && g.CurrentOpacity > 0)
				    {
					    int startBarsAgo = CurrentBar - g.StartBarIndex;
					    int endBarsAgo = CurrentBar - g.EndBarIndex;
                        
                        // Si el dibujo quedó en el pasado, endBarsAgo será negativo (hacia atrás). Lo dibujamos donde corresponde.
					    var rect = Draw.Rectangle(this, g.RectTag, false, startBarsAgo, g.High, endBarsAgo, g.Low, Brushes.Transparent, Brushes.LightSkyBlue, g.CurrentOpacity);
					    if (rect != null)
						    rect.IsLocked = true;
					    g.IsDrawn = true;
					    drawnThisBar++;
				    }

				    nextGapToDrawIndex++;
			    }

			    if (CurrentBar != lastProcessedBar)
			    {
				    TryDrawGapClusterLines();
				    lastProcessedBar = CurrentBar;
			    }
            }
		}

		private void ProcessPendingGaps()
		{
			if (!ConfirmarNoRellenadoVelaSiguiente)
			{
				pendingGaps.Clear();
				return;
			}

			if (pendingGaps.Count == 0)
				return;

			for (int i = pendingGaps.Count - 1; i >= 0; i--)
			{
				PendingGap pg = pendingGaps[i];
				int confirmSourceBarIndex = pg.CreatedSourceBarIndex + 1;
				if (CurrentBar < confirmSourceBarIndex)
					continue;

				int barsAgo = CurrentBar - confirmSourceBarIndex;
				if (barsAgo < 0)
					continue;
				if (barsAgo > CurrentBars[sourceSeriesIndex])
				{
					pendingGaps.RemoveAt(i);
					continue;
				}

				double nextHigh = Instrument.MasterInstrument.RoundToTickSize(Highs[sourceSeriesIndex][barsAgo]);
				double nextLow = Instrument.MasterInstrument.RoundToTickSize(Lows[sourceSeriesIndex][barsAgo]);
				// FIX BUG 2 (EdgeLab 2026-10-25): verificar también que la propia vela creadora no haya rellenado el gap tras abrir
				int creationBarsAgo = CurrentBar - pg.CreatedSourceBarIndex;
				double creationLow = creationBarsAgo >= 0 && creationBarsAgo <= CurrentBars[sourceSeriesIndex]
					? Instrument.MasterInstrument.RoundToTickSize(Lows[sourceSeriesIndex][creationBarsAgo]) : pg.High;
				double creationHigh = creationBarsAgo >= 0 && creationBarsAgo <= CurrentBars[sourceSeriesIndex]
					? Instrument.MasterInstrument.RoundToTickSize(Highs[sourceSeriesIndex][creationBarsAgo]) : pg.Low;
				bool filledOnCreation = (creationLow <= pg.Low && creationHigh >= pg.High);

				bool overlapsGap = filledOnCreation || (nextHigh >= pg.Low && nextLow <= pg.High);
				if (!overlapsGap)
				{
					GapZone confirmed = new GapZone
					{
						StartBarIndex = pg.MainBarIndex,
						EndBarIndex = pg.MainBarIndex + pg.ExtendBarsRightAtCreation,
						Low = pg.Low,
						High = pg.High,
						Mid = pg.Mid,
						RectTag = pg.RectTag,
						IsDrawn = false,
                        CurrentOpacity = InitialGapOpacity,
                        IsPriceAway = false 
					};
					gapZones.Add(confirmed);
					if (gapZones.Count > MaxStoredGaps)
					{
						int removeCount = gapZones.Count - MaxStoredGaps;
						gapZones.RemoveRange(0, removeCount);
						nextGapToDrawIndex = Math.Max(0, nextGapToDrawIndex - removeCount);
					}
				}

				pendingGaps.RemoveAt(i);
			}
		}

	    private void TryDrawGapClusterLines()
	    {
		    clusterZones.RemoveAll(z => z.EndBarIndex < CurrentBar);

		    double clusterHeightPrice = ClusterHeightTicks * TickSize;

            // Ahora los clusters también detectan zonas "vivas" sin importar el largo de su dibujo
		    List<GapZone> activeGaps = gapZones
			    .Where(g => g.StartBarIndex <= CurrentBar && g.CurrentOpacity > 0)
			    .ToList();

		    if (activeGaps.Count < MinGapsForCluster)
			    return;

		    activeGaps.Sort((a, b) => a.Mid.CompareTo(b.Mid));

		    // FIX BUG 1 (EdgeLab 2026-10-25): evaluar TODOS los clusters compactos disjuntos activos, no sólo un único bestStart..bestEnd global
		    activeGaps.Sort((a, b) => a.Low.CompareTo(b.Low));
		    double maxAllowedHole = MaxGapFreeSpaceTicksInCluster * TickSize;
		    double mergeTolerance = TickSize * 2;

		    int i = 0;
		    while (i < activeGaps.Count)
		    {
		        double clusterLow = activeGaps[i].Low;
		        double runningTop = activeGaps[i].High;
		        int count = 1;
		        int bestJ = -1;
		        double bestHigh = runningTop;

		        for (int j = i + 1; j < activeGaps.Count; j++)
		        {
		            if (activeGaps[j].Low - clusterLow > clusterHeightPrice)
		                break;
		            double hole = activeGaps[j].Low - runningTop;
		            if (hole > maxAllowedHole)
		                break;
		            if (activeGaps[j].High - clusterLow <= clusterHeightPrice)
		            {
		                count++;
		                if (activeGaps[j].High > runningTop)
		                    runningTop = activeGaps[j].High;
		                if (count >= MinGapsForCluster)
		                {
		                    bestJ = j;
		                    bestHigh = runningTop;
		                }
		            }
		        }

		        if (bestJ >= 0)
		        {
		            double clusterHigh = bestHigh;
		            bool alreadyExists = false;
		            for (int k = 0; k < clusterZones.Count; k++)
		            {
		                ClusterZone existing = clusterZones[k];
		                if (existing.StartBarIndex <= CurrentBar && CurrentBar <= existing.EndBarIndex)
		                {
		                    double overlapLow = Math.Max(existing.Low, clusterLow);
		                    double overlapHigh = Math.Min(existing.High, clusterHigh);
		                    if (overlapLow <= overlapHigh + mergeTolerance)
		                    {
		                        alreadyExists = true;
		                        break;
		                    }
		                }
		            }

		            if (!alreadyExists)
		            {
		                int startBar = CurrentBar;
		                int endBar = CurrentBar + ClusterLineExtension;
		                string tagZone = "ClusterZoneRect_" + startBar + "_" + clusterLow.ToString("F5") + "_" + clusterHigh.ToString("F5");
		                clusterZones.Add(new ClusterZone
		                {
		                    StartBarIndex = startBar,
		                    EndBarIndex = endBar,
		                    Low = clusterLow,
		                    High = clusterHigh,
		                    Tag = tagZone
		                });

		                var clusterRect = Draw.Rectangle(this, tagZone, false, 0, clusterHigh, -ClusterLineExtension, clusterLow, Brushes.Transparent, clusterZoneFillBrush ?? Brushes.Red, 20);
		                if (clusterRect != null)
		                    clusterRect.IsLocked = true;
		            }
		            i = bestJ + 1;
		        }
		        else
		        {
		            i++;
		        }
		    }
	    }

		private bool GapExistsInAllTimeframes(DateTime referenceTime, double prevClose, double currOpen, int referenceSeriesIdx)
		{
			if (validationSeriesIndices.Count == 0) return true;

			for (int k = 0; k < validationSeriesIndices.Count; k++)
			{
				int seriesIdx = validationSeriesIndices[k];
				if (seriesIdx == referenceSeriesIdx)
					continue;

				if (CurrentBars[seriesIdx] < 1) return false;

				int barIdx = 0;
				for (int i = 0; i <= CurrentBars[seriesIdx]; i++)
				{
					if (Times[seriesIdx][i] <= referenceTime)
					{
						barIdx = i;
						break;
					}
				}
				if (barIdx + 1 > CurrentBars[seriesIdx])
					return false;

				double otherPrevClose = Instrument.MasterInstrument.RoundToTickSize(Closes[seriesIdx][barIdx + 1]);
				double otherCurrOpen = Instrument.MasterInstrument.RoundToTickSize(Opens[seriesIdx][barIdx]);

				double tolerance = TickSize * 1;

				if (Math.Abs(otherCurrOpen - currOpen) > tolerance) return false;
				if (Math.Abs(otherPrevClose - prevClose) > tolerance) return false;
			}

			return true;
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(0, int.MaxValue)]
		[Display(Name = "Gap Mínimo (Ticks)", Order = 1, GroupName = "Parámetros")]
		public int MinGapPoints { get; set; }

		[NinjaScriptProperty]
		[Range(0, int.MaxValue)]
		[Display(Name = "Extensión Rectángulos (Barras)", Order = 2, GroupName = "Parámetros")]
		public int ExtendBarsRight { get; set; }

		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name = "Mínimo de Gaps para Confluencia", Order = 3, GroupName = "Parámetros")]
		public int MinGapsForCluster { get; set; }

		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name = "Altura de Clúster (Ticks)", Order = 4, GroupName = "Parámetros")]
		public int ClusterHeightTicks { get; set; }

		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name = "Extensión de Líneas de Clúster (Barras)", Order = 5, GroupName = "Parámetros")]
		public int ClusterLineExtension { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Confirmar gap no rellenado (1 vela)", Order = 6, GroupName = "Parámetros")]
		public bool ConfirmarNoRellenadoVelaSiguiente { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Opacidad Inicial del Gap (%)", Order = 7, GroupName = "Parámetros")]
        public int InitialGapOpacity { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Opacidad a restar por Toque", Order = 8, GroupName = "Parámetros", Description = "Si resta igual que la inicial, desaparecerá al primer re-testeo.")]
        public int OpacityDropPerTouch { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1000)]
        [Display(Name = "Distancia de Reseteo (Ticks)", Order = 9, GroupName = "Parámetros", Description = "Distancia que el precio debe alejarse del gap para armar un nuevo toque.")]
        public int AwayDistanceTicks { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 1 Tick", Order = 6, GroupName = "Validación Multi-Timeframe")]
		public bool Validate1Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 2 Tick", Order = 7, GroupName = "Validación Multi-Timeframe")]
		public bool Validate2Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 3 Tick", Order = 8, GroupName = "Validación Multi-Timeframe")]
		public bool Validate3Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 5 Tick", Order = 9, GroupName = "Validación Multi-Timeframe")]
		public bool Validate5Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 10 Tick", Order = 10, GroupName = "Validación Multi-Timeframe")]
		public bool Validate10Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 15 Tick", Order = 11, GroupName = "Validación Multi-Timeframe")]
		public bool Validate15Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 25 Tick", Order = 12, GroupName = "Validación Multi-Timeframe")]
		public bool Validate25Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 50 Tick", Order = 13, GroupName = "Validación Multi-Timeframe")]
		public bool Validate50Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 100 Tick", Order = 14, GroupName = "Validación Multi-Timeframe")]
		public bool Validate100Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 200 Tick", Order = 15, GroupName = "Validación Multi-Timeframe")]
		public bool Validate200Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 500 Tick", Order = 16, GroupName = "Validación Multi-Timeframe")]
		public bool Validate500Tick { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en S1", Order = 1, GroupName = "Validación Multi-Timeframe (Tiempo)")]
		public bool ValidateS1 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en S5", Order = 2, GroupName = "Validación Multi-Timeframe (Tiempo)")]
		public bool ValidateS5 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en S25", Order = 3, GroupName = "Validación Multi-Timeframe (Tiempo)")]
		public bool ValidateS25 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 1 Min", Order = 4, GroupName = "Validación Multi-Timeframe (Tiempo)")]
		public bool Validate1Min { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "Validar en 5 Min", Order = 5, GroupName = "Validación Multi-Timeframe (Tiempo)")]
		public bool Validate5Min { get; set; }
		#endregion
	}
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private ZonasDeGaps[] cacheZonasDeGaps;
		public ZonasDeGaps ZonasDeGaps(int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			return ZonasDeGaps(Input, minGapPoints, extendBarsRight, minGapsForCluster, clusterHeightTicks, clusterLineExtension, confirmarNoRellenadoVelaSiguiente, initialGapOpacity, opacityDropPerTouch, awayDistanceTicks, validate1Tick, validate2Tick, validate3Tick, validate5Tick, validate10Tick, validate15Tick, validate25Tick, validate50Tick, validate100Tick, validate200Tick, validate500Tick, validateS1, validateS5, validateS25, validate1Min, validate5Min);
		}

		public ZonasDeGaps ZonasDeGaps(ISeries<double> input, int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			if (cacheZonasDeGaps != null)
				for (int idx = 0; idx < cacheZonasDeGaps.Length; idx++)
					if (cacheZonasDeGaps[idx] != null && cacheZonasDeGaps[idx].MinGapPoints == minGapPoints && cacheZonasDeGaps[idx].ExtendBarsRight == extendBarsRight && cacheZonasDeGaps[idx].MinGapsForCluster == minGapsForCluster && cacheZonasDeGaps[idx].ClusterHeightTicks == clusterHeightTicks && cacheZonasDeGaps[idx].ClusterLineExtension == clusterLineExtension && cacheZonasDeGaps[idx].ConfirmarNoRellenadoVelaSiguiente == confirmarNoRellenadoVelaSiguiente && cacheZonasDeGaps[idx].InitialGapOpacity == initialGapOpacity && cacheZonasDeGaps[idx].OpacityDropPerTouch == opacityDropPerTouch && cacheZonasDeGaps[idx].AwayDistanceTicks == awayDistanceTicks && cacheZonasDeGaps[idx].Validate1Tick == validate1Tick && cacheZonasDeGaps[idx].Validate2Tick == validate2Tick && cacheZonasDeGaps[idx].Validate3Tick == validate3Tick && cacheZonasDeGaps[idx].Validate5Tick == validate5Tick && cacheZonasDeGaps[idx].Validate10Tick == validate10Tick && cacheZonasDeGaps[idx].Validate15Tick == validate15Tick && cacheZonasDeGaps[idx].Validate25Tick == validate25Tick && cacheZonasDeGaps[idx].Validate50Tick == validate50Tick && cacheZonasDeGaps[idx].Validate100Tick == validate100Tick && cacheZonasDeGaps[idx].Validate200Tick == validate200Tick && cacheZonasDeGaps[idx].Validate500Tick == validate500Tick && cacheZonasDeGaps[idx].ValidateS1 == validateS1 && cacheZonasDeGaps[idx].ValidateS5 == validateS5 && cacheZonasDeGaps[idx].ValidateS25 == validateS25 && cacheZonasDeGaps[idx].Validate1Min == validate1Min && cacheZonasDeGaps[idx].Validate5Min == validate5Min && cacheZonasDeGaps[idx].EqualsInput(input))
						return cacheZonasDeGaps[idx];
			return CacheIndicator<ZonasDeGaps>(new ZonasDeGaps(){ MinGapPoints = minGapPoints, ExtendBarsRight = extendBarsRight, MinGapsForCluster = minGapsForCluster, ClusterHeightTicks = clusterHeightTicks, ClusterLineExtension = clusterLineExtension, ConfirmarNoRellenadoVelaSiguiente = confirmarNoRellenadoVelaSiguiente, InitialGapOpacity = initialGapOpacity, OpacityDropPerTouch = opacityDropPerTouch, AwayDistanceTicks = awayDistanceTicks, Validate1Tick = validate1Tick, Validate2Tick = validate2Tick, Validate3Tick = validate3Tick, Validate5Tick = validate5Tick, Validate10Tick = validate10Tick, Validate15Tick = validate15Tick, Validate25Tick = validate25Tick, Validate50Tick = validate50Tick, Validate100Tick = validate100Tick, Validate200Tick = validate200Tick, Validate500Tick = validate500Tick, ValidateS1 = validateS1, ValidateS5 = validateS5, ValidateS25 = validateS25, Validate1Min = validate1Min, Validate5Min = validate5Min }, input, ref cacheZonasDeGaps);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.ZonasDeGaps ZonasDeGaps(int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			return indicator.ZonasDeGaps(Input, minGapPoints, extendBarsRight, minGapsForCluster, clusterHeightTicks, clusterLineExtension, confirmarNoRellenadoVelaSiguiente, initialGapOpacity, opacityDropPerTouch, awayDistanceTicks, validate1Tick, validate2Tick, validate3Tick, validate5Tick, validate10Tick, validate15Tick, validate25Tick, validate50Tick, validate100Tick, validate200Tick, validate500Tick, validateS1, validateS5, validateS25, validate1Min, validate5Min);
		}

		public Indicators.ZonasDeGaps ZonasDeGaps(ISeries<double> input , int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			return indicator.ZonasDeGaps(input, minGapPoints, extendBarsRight, minGapsForCluster, clusterHeightTicks, clusterLineExtension, confirmarNoRellenadoVelaSiguiente, initialGapOpacity, opacityDropPerTouch, awayDistanceTicks, validate1Tick, validate2Tick, validate3Tick, validate5Tick, validate10Tick, validate15Tick, validate25Tick, validate50Tick, validate100Tick, validate200Tick, validate500Tick, validateS1, validateS5, validateS25, validate1Min, validate5Min);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.ZonasDeGaps ZonasDeGaps(int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			return indicator.ZonasDeGaps(Input, minGapPoints, extendBarsRight, minGapsForCluster, clusterHeightTicks, clusterLineExtension, confirmarNoRellenadoVelaSiguiente, initialGapOpacity, opacityDropPerTouch, awayDistanceTicks, validate1Tick, validate2Tick, validate3Tick, validate5Tick, validate10Tick, validate15Tick, validate25Tick, validate50Tick, validate100Tick, validate200Tick, validate500Tick, validateS1, validateS5, validateS25, validate1Min, validate5Min);
		}

		public Indicators.ZonasDeGaps ZonasDeGaps(ISeries<double> input , int minGapPoints, int extendBarsRight, int minGapsForCluster, int clusterHeightTicks, int clusterLineExtension, bool confirmarNoRellenadoVelaSiguiente, int initialGapOpacity, int opacityDropPerTouch, int awayDistanceTicks, bool validate1Tick, bool validate2Tick, bool validate3Tick, bool validate5Tick, bool validate10Tick, bool validate15Tick, bool validate25Tick, bool validate50Tick, bool validate100Tick, bool validate200Tick, bool validate500Tick, bool validateS1, bool validateS5, bool validateS25, bool validate1Min, bool validate5Min)
		{
			return indicator.ZonasDeGaps(input, minGapPoints, extendBarsRight, minGapsForCluster, clusterHeightTicks, clusterLineExtension, confirmarNoRellenadoVelaSiguiente, initialGapOpacity, opacityDropPerTouch, awayDistanceTicks, validate1Tick, validate2Tick, validate3Tick, validate5Tick, validate10Tick, validate15Tick, validate25Tick, validate50Tick, validate100Tick, validate200Tick, validate500Tick, validateS1, validateS5, validateS25, validate1Min, validate5Min);
		}
	}
}

#endregion