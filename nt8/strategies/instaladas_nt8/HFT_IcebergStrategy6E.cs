#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class HFT_IcebergStrategy6E : Strategy
    {
        private Series<double> deltaSerie;
        private Series<double> sellVolSerie;
        private Series<double> buyVolSerie;
        
        private double curDelta;
        private double curSellVol;
        private double curBuyVol;
        private int lastSide = 0;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Estrategia Automatizada del patrón Iceberg Laddering HFT para 6E.";
                Name                                        = "HFT_IcebergStrategy6E";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 0;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                IsInstantiatedOnEachOptimizationIteration   = true;

                StartTime               = TimeSpan.Parse("08:00");
                EndTime                 = TimeSpan.Parse("12:00");
                ClusterBars             = 5;
                MinAbsorbVolume         = 200;
                MinIcebergDelta         = 100;
                MaxAbsorbRangeTicks     = 4;
                MaxExhaustionVolume     = 50;
                TargetTicks             = 10;
                StopLossTicks           = 2;
                EnableLongs             = true;
                EnableShorts            = true;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                deltaSerie   = new Series<double>(this);
                sellVolSerie = new Series<double>(this);
                buyVolSerie  = new Series<double>(this);
                curDelta     = 0;
                curSellVol   = 0;
                curBuyVol    = 0;
                lastSide     = 0;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBars[0] < 20 || CurrentBars[1] < 1)
                return;

            if (BarsInProgress == 1)
            {
                double cl  = Closes[1][0];
                double clP = Closes[1][1];
                double vol = Volumes[1][0];

                int side = cl > clP ? 1 : (cl < clP ? -1 : lastSide);
                if (side == 0) side = 1;
                lastSide = side;

                if (side == 1)
                {
                    curDelta += vol;
                    curBuyVol += vol;
                }
                else
                {
                    curDelta -= vol;
                    curSellVol += vol;
                }
            }
            else if (BarsInProgress == 0)
            {
                deltaSerie[0]   = curDelta;
                sellVolSerie[0] = curSellVol;
                buyVolSerie[0]  = curBuyVol;
                curDelta   = 0;
                curSellVol = 0;
                curBuyVol  = 0;

                EvaluatePattern();
            }
        }

        private void EvaluatePattern()
        {
            if (Position.MarketPosition != MarketPosition.Flat)
                return;

            TimeSpan timeOfDay = Times[0][0].TimeOfDay;
            if (timeOfDay < StartTime || timeOfDay > EndTime)
                return;

            for (int i = 1; i <= 4; i++)
            {
                double clusterVol = 0;
                double clusterDelta = 0;
                double clusterHigh = double.MinValue;
                double clusterLow = double.MaxValue;

                for (int c = 0; c < ClusterBars; c++)
                {
                    int idx = i + c;
                    clusterVol += Volumes[0][idx];
                    clusterDelta += deltaSerie[idx];
                    clusterHigh = Math.Max(clusterHigh, Highs[0][idx]);
                    clusterLow = Math.Min(clusterLow, Lows[0][idx]);
                }

                double rangeTicks = (clusterHigh - clusterLow) / TickSize;

                // ===== LOGICA LONG (DIRECTA) =====
                if (EnableLongs)
                {
                    bool isLongAbsorption = clusterVol >= MinAbsorbVolume 
                                         && clusterDelta <= -MinIcebergDelta 
                                         && rangeTicks <= MaxAbsorbRangeTicks;

                    if (isLongAbsorption)
                    {
                        int preClusterIdx = i + ClusterBars;
                        bool isLadderingDown = Highs[0][preClusterIdx] <= Highs[0][preClusterIdx + 1] &&
                                               Highs[0][preClusterIdx + 1] <= Highs[0][preClusterIdx + 2];

                        if (isLadderingDown)
                        {
                            bool exhaustionOk = true;
                            for (int j = 1; j < i; j++)
                            {
                                if (sellVolSerie[j] > MaxExhaustionVolume || Lows[0][j] < clusterLow - (2 * TickSize))
                                {
                                    exhaustionOk = false;
                                    break;
                                }
                            }

                            // Ahora armamos una orden PENDIENTE (Stop Market) para entrar exactamente al milisegundo de la ruptura
                            bool isPendingJumpFlowLong = exhaustionOk && Closes[0][0] <= clusterHigh;

                            if (isPendingJumpFlowLong)
                            {
                                SetStopLoss("IcebergLong", CalculationMode.Price, clusterLow - (StopLossTicks * TickSize), false);
                                SetProfitTarget("IcebergLong", CalculationMode.Price, clusterHigh + TickSize + (TargetTicks * TickSize));
                                EnterLongStopMarket(0, true, 1, clusterHigh + TickSize, "IcebergLong");
                                return; // Sale para no evaluar short en la misma vela si ya armó el long
                            }
                        }
                    }
                }

                // ===== LOGICA SHORT (INVERSA) =====
                if (EnableShorts)
                {
                    bool isShortAbsorption = clusterVol >= MinAbsorbVolume 
                                          && clusterDelta >= MinIcebergDelta 
                                          && rangeTicks <= MaxAbsorbRangeTicks;

                    if (isShortAbsorption)
                    {
                        int preClusterIdx = i + ClusterBars;
                        bool isLadderingUp = Lows[0][preClusterIdx] >= Lows[0][preClusterIdx + 1] &&
                                             Lows[0][preClusterIdx + 1] >= Lows[0][preClusterIdx + 2];

                        if (isLadderingUp)
                        {
                            bool exhaustionOk = true;
                            for (int j = 1; j < i; j++)
                            {
                                // Para shorts, verificamos que el volumen de compra se agote (nadie quiere seguir empujando arriba)
                                if (buyVolSerie[j] > MaxExhaustionVolume || Highs[0][j] > clusterHigh + (2 * TickSize))
                                {
                                    exhaustionOk = false;
                                    break;
                                }
                            }

                            bool isPendingJumpFlowShort = exhaustionOk && Closes[0][0] >= clusterLow;

                            if (isPendingJumpFlowShort)
                            {
                                SetStopLoss("IcebergShort", CalculationMode.Price, clusterHigh + (StopLossTicks * TickSize), false);
                                SetProfitTarget("IcebergShort", CalculationMode.Price, clusterLow - TickSize - (TargetTicks * TickSize));
                                EnterShortStopMarket(0, true, 1, clusterLow - TickSize, "IcebergShort");
                                return;
                            }
                        }
                    }
                }
            }
        }

        #region Properties
        [NinjaScriptProperty]
        [PropertyEditor("NinjaTrader.Gui.Tools.TimeEditorKey")]
        [Display(Name="Hora Inicio", Order=1, GroupName="1. Filtros")]
        public TimeSpan StartTime { get; set; }

        [NinjaScriptProperty]
        [PropertyEditor("NinjaTrader.Gui.Tools.TimeEditorKey")]
        [Display(Name="Hora Fin", Order=2, GroupName="1. Filtros")]
        public TimeSpan EndTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Activar Longs", Order=3, GroupName="1. Filtros")]
        public bool EnableLongs { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Activar Shorts", Order=4, GroupName="1. Filtros")]
        public bool EnableShorts { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Barras del Cluster", Order=1, GroupName="2. Parámetros Iceberg")]
        public int ClusterBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Volumen Mínimo Absorción", Order=2, GroupName="2. Parámetros Iceberg")]
        public int MinAbsorbVolume { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Delta Absoluto Mínimo", Order=3, GroupName="2. Parámetros Iceberg")]
        public int MinIcebergDelta { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Rango Máx Absorción (Ticks)", Order=4, GroupName="2. Parámetros Iceberg")]
        public int MaxAbsorbRangeTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name="Max Vol Contraparte (Agotamiento)", Order=1, GroupName="3. Parámetros Agotamiento")]
        public int MaxExhaustionVolume { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Target Ticks (TP1)", Order=1, GroupName="4. Gestión Asimétrica")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Stop Loss Ticks", Order=2, GroupName="4. Gestión Asimétrica")]
        public int StopLossTicks { get; set; }
        #endregion
    }
}
