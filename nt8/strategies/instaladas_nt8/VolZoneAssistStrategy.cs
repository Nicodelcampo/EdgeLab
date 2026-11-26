// VolZoneAssistStrategy.cs — Fase 4 de la guía AlgoNQ (REDIRECCIÓN v4)
// Asistente de decisión activado manualmente por el usuario. 
// Evalúa zonas de volumen en tiempo real y ejecuta entradas usando un modelo ONNX.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using System.Data.SQLite;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using NinjaTrader.Gui;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public enum OrderSide { Long, Short }

    public class VolZoneAssistStrategy : Strategy
    {
        // Rutas y configuración de base de datos
        private string dbPath = @"C:\AlgoNQ\data\algo_features.sqlite";
        private string modelPath = @"C:\AlgoNQ\models\algo_multiclass.onnx";
        
        private SQLiteConnection dbConn;
        private InferenceSession onnxSession;

        private long lastProcessedSnapId = -1;
        private double currentAtr = 10.0; // valor inicial; se sobreescribe en cada tick con ATR(14)
        private ATR atrIndicator;          // indicador dinámico de ATR sobre el chart principal
        
        // Variables UI y Dibujo
        private StackPanel myPanel;
        private System.Windows.Controls.Button btnArmLong;
        private System.Windows.Controls.Button btnArmShort;
        private double lastEntryPrice = 0;
        private int lastEntryBar = -1;
        private bool forceRedrawLines = false;
        
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Estrategia Asistente: Evalúa entrar en una zona cuando el usuario la Arma en la dirección elegida.";
                Name = "VolZoneAssistStrategy";
                Calculate = Calculate.OnEachTick; // Monitoreo en tiempo real tick-by-tick
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                
                // Parámetros de Operación
                Armed = false;
                Side = OrderSide.Long;

                // Parámetros optimizables de la estrategia
                MinProbabilityThreshold = 0.70; // 70% de probabilidad requerida
                StopLossAtrMult = 1.0;          // Stop Loss = 1.0 * ATR
                ProfitTargetAtrMult = 2.0;      // Profit Target default = 2.0 * ATR
                Contratos = 1;
                TradeOnlyDuringAsianSession = false;
            }
            else if (State == State.Configure)
            {
                // Agrega serie de 1 tick para máxima sincronización temporal
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.Historical)
            {
                if (ChartControl != null)
                {
                    ChartControl.Dispatcher.InvokeAsync(() => { CreateWpfControls(); });
                }
            }
            else if (State == State.DataLoaded)
            {
                // 1. Abrir conexión SQLite persistente
                try
                {
                    dbConn = new SQLiteConnection("Data Source=" + dbPath + ";Version=3;Journal Mode=Wal;Synchronous=Off;");
                    dbConn.Open();
                    Print("[VolZoneAssist] Conexión SQLite abierta exitosamente.");
                }
                catch (Exception ex)
                {
                    Print("[VolZoneAssist] ERROR abriendo SQLite: " + ex.Message);
                }

                // 2. Cargar sesión de ONNX Runtime
                try
                {
                    var opts = new SessionOptions();
                    onnxSession = new InferenceSession(modelPath, opts);
                    Print("[VolZoneAssist] Modelo ONNX cargado exitosamente en memoria.");
                }
                catch (Exception ex)
                {
                    Print("[VolZoneAssist] ERROR cargando modelo ONNX: " + ex.Message);
                }

                // 3. Inicializar ATR(14) sobre el chart primario para SL/TP dinámicos
                try
                {
                    atrIndicator = ATR(BarsArray[0], 14);
                    Print("[VolZoneAssist] ATR(14) inicializado sobre serie primaria.");
                }
                catch (Exception ex)
                {
                    Print("[VolZoneAssist] ERROR inicializando ATR: " + ex.Message + " - se usará valor default 10.0");
                }
            }
            else if (State == State.Terminated)
            {
                // Cierre y disposición ordenada de recursos
                if (dbConn != null)
                {
                    try { dbConn.Close(); dbConn.Dispose(); } catch { }
                    dbConn = null;
                }
                
                if (ChartControl != null)
                {
                    ChartControl.Dispatcher.InvokeAsync(() => { DisposeWpfControls(); });
                }
                
                if (onnxSession != null)
                {
                    try { onnxSession.Dispose(); } catch { }
                    onnxSession = null;
                }
                Print("[VolZoneAssist] Recursos liberados de forma correcta.");
            }
        }

        protected override void OnBarUpdate()
        {
            // Fallback para inyectar botones si ChartControl no estaba listo en OnStateChange
            if (myPanel == null && ChartControl != null)
            {
                ChartControl.Dispatcher.InvokeAsync(() => { CreateWpfControls(); });
            }

            // Necesitamos al menos 1 barra
            if (CurrentBars[0] < 1 || CurrentBars[1] < 1) return;

            // Procesar lógica en la serie secundaria (1 tick) para máxima precisión
            if (BarsInProgress == 1)
            {
                if (!Armed)
                {
                    RemoveInteractiveLines();
                    return;
                }
                
                if (forceRedrawLines)
                {
                    RemoveInteractiveLines();
                    forceRedrawLines = false;
                }
                
                EnsureInteractiveLines();

                if (TradeOnlyDuringAsianSession)
                {
                    DateTime barTime = Times[1][0];
                    if (barTime.Hour >= 2 && barTime.Hour < 20)
                        return;
                }

                if (Position.MarketPosition == MarketPosition.Flat)
                {
                    EvaluateLgbmSignal();
                }
                else
                {
                    // Desarmar automáticamente una vez que entramos en posición para evitar múltiples trades
                    if (Armed)
                    {
                        Armed = false;
                        RemoveInteractiveLines();
                        UpdateButtonsState();
                        Print("[VolZoneAssist] Posición tomada, bot desarmado automáticamente.");
                    }
                }
            }
        }

        private double QueryNextZoneCluster(double entryPrice, OrderSide side)
        {
            if (dbConn == null || dbConn.State != System.Data.ConnectionState.Open) return -1;
            try
            {
                string condition = side == OrderSide.Long ? "cluster_low_px > @price" : "cluster_high_px < @price";
                string order = side == OrderSide.Long ? "ASC" : "DESC";
                string sql = $@"SELECT cluster_low_px, cluster_high_px 
                               FROM zone_events 
                               WHERE instrument = @inst AND is_mitigated = 0 
                                 AND {condition}
                               ORDER BY cluster_low_px {order} LIMIT 1";
                using (var cmd = new SQLiteCommand(sql, dbConn))
                {
                    cmd.Parameters.AddWithValue("@inst", Instrument.FullName);
                    cmd.Parameters.AddWithValue("@price", entryPrice);
                    using (var rd = cmd.ExecuteReader())
                    {
                        if (rd.Read())
                        {
                            double low = rd.GetDouble(0);
                            double high = rd.GetDouble(1);
                            // Tomar el borde más cercano de la zona como target
                            return side == OrderSide.Long ? low : high; 
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Print("[VolZoneAssist] Error buscando zona target: " + ex.Message);
            }
            return -1;
        }

        private void RemoveInteractiveLines()
        {
            RemoveDrawObject("PreTradeTP");
            RemoveDrawObject("PreTradeSL");
        }

        private void EnsureInteractiveLines()
        {
            if (DrawObjects["PreTradeTP"] == null && DrawObjects["PreTradeSL"] == null)
            {
                double closePrice = Closes[1][0];
                if (atrIndicator != null && CurrentBars[0] >= 15)
                {
                    double a = atrIndicator[0];
                    if (a > 0 && !double.IsNaN(a) && !double.IsInfinity(a))
                        currentAtr = a;
                }
                
                double slDistance = currentAtr * StopLossAtrMult;
                double tpDistance = currentAtr * ProfitTargetAtrMult;
                
                double nextZoneEdge = QueryNextZoneCluster(closePrice, Side);
                if (nextZoneEdge != -1)
                {
                    double distToZone = Math.Abs(nextZoneEdge - closePrice);
                    if (distToZone < tpDistance && distToZone > currentAtr * 0.5)
                    {
                        tpDistance = distToZone;
                    }
                }
                
                double stopPx = Side == OrderSide.Long ? closePrice - slDistance : closePrice + slDistance;
                double targetPx = Side == OrderSide.Long ? closePrice + tpDistance : closePrice - tpDistance;
                
                Draw.HorizontalLine(this, "PreTradeTP", targetPx, Brushes.LimeGreen, DashStyleHelper.Solid, 2);
                Draw.HorizontalLine(this, "PreTradeSL", stopPx, Brushes.Red, DashStyleHelper.Solid, 2);
            }
        }

        private void EvaluateLgbmSignal()
        {
            if (dbConn == null || dbConn.State != System.Data.ConnectionState.Open || onnxSession == null)
                return;

            try
            {
                // 1. Consultar el snapshot más reciente NO mitigado, de los últimos 60 seg, con el precio DENTRO de la zona
                long snapId = -1;
                float[] features = new float[14];
                double closePrice = Closes[1][0];
                long nowMs = new DateTimeOffset(DateTime.UtcNow).ToUnixTimeMilliseconds();
                long thresholdMs = nowMs - 60000; // últimos 60 segundos
                
                string sql = @"SELECT 
                                 s.snap_id, s.delta_cum, s.delta_slope, s.ofi_proxy, s.compression, s.entry_speed, 
                                 s.time_at_price, s.absorption_cnt, s.dist_gap_up_atr, s.dist_gap_dn_atr, 
                                 s.n_gaps_up, s.n_gaps_dn, s.hour_bucket, s.day_of_week
                               FROM feature_snapshots s
                               JOIN zone_events z ON s.zone_id = z.zone_id
                               WHERE z.instrument = @inst
                                 AND z.is_mitigated = 0
                                 AND s.snap_ts >= @timeThresh
                                 AND @price >= z.cluster_low_px AND @price <= z.cluster_high_px
                               ORDER BY s.snap_ts DESC LIMIT 1;";
                               
                using (var cmd = new SQLiteCommand(sql, dbConn))
                {
                    cmd.Parameters.AddWithValue("@inst", Instrument.FullName);
                    cmd.Parameters.AddWithValue("@timeThresh", thresholdMs);
                    cmd.Parameters.AddWithValue("@price", closePrice);
                    using (var rd = cmd.ExecuteReader())
                    {
                        if (rd.Read())
                        {
                            snapId = rd.GetInt64(0);
                            
                            if (snapId <= lastProcessedSnapId)
                                return;
                                
                            features[0] = (float)rd.GetDouble(1);  // delta_cum
                            features[1] = (float)rd.GetDouble(2);  // delta_slope
                            features[2] = (float)rd.GetDouble(3);  // ofi_proxy
                            features[3] = (float)rd.GetDouble(4);  // compression
                            features[4] = (float)rd.GetDouble(5);  // entry_speed
                            features[5] = (float)rd.GetInt32(6);   // time_at_price
                            features[6] = (float)rd.GetInt32(7);   // absorption_cnt
                            features[7] = (float)rd.GetDouble(8);  // dist_gap_up_atr (llenado con 0 por v4 ZFC)
                            features[8] = (float)rd.GetDouble(9);  // dist_gap_dn_atr (llenado con 0 por v4 ZFC)
                            features[9] = (float)rd.GetInt32(10);  // n_gaps_up (llenado con 0 por v4 ZFC)
                            features[10] = (float)rd.GetInt32(11); // n_gaps_dn (llenado con 0 por v4 ZFC)
                            features[11] = (float)rd.GetInt32(12); // hour_bucket
                            features[12] = (float)rd.GetInt32(13); // day_of_week
                            features[13] = Side == OrderSide.Long ? 1f : 0f; // is_long simulado
                        }
                    }
                }

                if (snapId == -1) return;
                lastProcessedSnapId = snapId;

                // 2. Ejecutar Inferencia con el modelo LightGBM cargado en ONNX
                var inputTensor = new DenseTensor<float>(features, new int[] { 1, 14 });
                var inputs = new List<NamedOnnxValue>
                {
                    NamedOnnxValue.CreateFromTensor("float_input", inputTensor)
                };

                using (var results = onnxSession.Run(inputs))
                {
                    // Extraer probabilidades del ZipMap de ONNX (LightGBM exporta como secuencia de diccionarios)
                    var probSequence = results.ElementAt(1).AsEnumerable<NamedOnnxValue>().First();
                    var probDict = probSequence.AsDictionary<Int64, float>();
                    
                    // La clase 0 es CONTINUE_FAV
                    double actionProbability = probDict[0];
                    
                    Print(string.Format("[VolZoneAssist] Analizando SnapID: {0} | Prob. CONTINUE: {1:F2}% (Umbral: {2:F2}%)", 
                                        snapId, actionProbability * 100.0, MinProbabilityThreshold * 100.0));

                    // 3. Evaluar gatillo de entrada
                    if (actionProbability >= MinProbabilityThreshold)
                    {
                        if (atrIndicator != null && CurrentBars[0] >= 15)
                        {
                            double a = atrIndicator[0];
                            if (a > 0 && !double.IsNaN(a) && !double.IsInfinity(a))
                                currentAtr = a;
                        }

                        double slDistance = currentAtr * StopLossAtrMult;
                        double tpDistance = currentAtr * ProfitTargetAtrMult;
                        
                        // Buscar la siguiente zona de liquidez para target dinámico
                        double nextZoneEdge = QueryNextZoneCluster(closePrice, Side);
                        if (nextZoneEdge != -1)
                        {
                            double distToZone = Math.Abs(nextZoneEdge - closePrice);
                            if (distToZone < tpDistance && distToZone > currentAtr * 0.5)
                            {
                                tpDistance = distToZone;
                                Print("[VolZoneAssist] Target adaptado a la siguiente zona de volumen: " + tpDistance + " puntos.");
                            }
                        }

                        double stopPx = Side == OrderSide.Long ? closePrice - slDistance : closePrice + slDistance;
                        double targetPx = Side == OrderSide.Long ? closePrice + tpDistance : closePrice - tpDistance;
                        
                        var preTradeTP = DrawObjects["PreTradeTP"] as NinjaTrader.NinjaScript.DrawingTools.HorizontalLine;
                        if (preTradeTP != null) targetPx = preTradeTP.StartAnchor.Price;
                        
                        var preTradeSL = DrawObjects["PreTradeSL"] as NinjaTrader.NinjaScript.DrawingTools.HorizontalLine;
                        if (preTradeSL != null) stopPx = preTradeSL.StartAnchor.Price;
                        
                        tpDistance = Math.Abs(targetPx - closePrice);
                        slDistance = Math.Abs(stopPx - closePrice);
                        
                        RemoveInteractiveLines();

                        string signalName = "VolZone" + Side.ToString();
                        
                        if (Side == OrderSide.Long)
                        {
                            SetStopLoss(signalName, CalculationMode.Price, stopPx, false);
                            SetProfitTarget(signalName, CalculationMode.Price, targetPx, false);
                            EnterLong(Contratos, signalName);
                        }
                        else
                        {
                            SetStopLoss(signalName, CalculationMode.Price, stopPx, false);
                            SetProfitTarget(signalName, CalculationMode.Price, targetPx, false);
                            EnterShort(Contratos, signalName);
                        }
                        
                        Print(string.Format("[VolZoneAssist] {0} EJECUTADO en {1} | TP dist: {2:F2} | SL dist: {3:F2}", 
                                            Side.ToString().ToUpper(), closePrice, tpDistance, slDistance));
                                            
                        PersistDecision(snapId, actionProbability, closePrice, stopPx, targetPx, Side.ToString().ToUpper());
                    }
                }
            }
            catch (Exception ex)
            {
                Print("[VolZoneAssist] ERROR en inferencia/ejecución: " + ex.Message);
            }
        }

        private void PersistDecision(long snapId, double probability, double entry, double stop, double target, string action)
        {
            if (dbConn == null || dbConn.State != System.Data.ConnectionState.Open) return;
            
            try
            {
                string sql = @"INSERT INTO decisions (snap_id, model_version, prob_calibrated, action, entry_px, stop_px, target_px)
                               VALUES (@sid, @ver, @prob, @action, @entry, @stop, @target)";
                using (var cmd = new SQLiteCommand(sql, dbConn))
                {
                    cmd.Parameters.AddWithValue("@sid", snapId);
                    cmd.Parameters.AddWithValue("@ver", "VolZone_Assist_v1");
                    cmd.Parameters.AddWithValue("@prob", probability);
                    cmd.Parameters.AddWithValue("@action", action);
                    cmd.Parameters.AddWithValue("@entry", entry);
                    cmd.Parameters.AddWithValue("@stop", stop);
                    cmd.Parameters.AddWithValue("@target", target);
                    cmd.ExecuteNonQuery();
                }
            }
            catch (Exception ex)
            {
                Print("[VolZoneAssist] Error guardando decisión: " + ex.Message);
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order.OrderState == OrderState.Filled || execution.Order.OrderState == OrderState.PartFilled)
            {
                if (execution.Order.Name.Contains("VolZone"))
                {
                    lastEntryPrice = execution.Price;
                    lastEntryBar = CurrentBars[0];
                    Draw.HorizontalLine(this, "TempEntryLine", lastEntryPrice, Brushes.Yellow, DashStyleHelper.Dash, 2);
                }
            }
        }

        protected override void OnPositionUpdate(Position position, double averagePrice, int quantity, MarketPosition marketPosition)
        {
            if (position.MarketPosition == MarketPosition.Flat && lastEntryBar != -1)
            {
                RemoveDrawObject("TempEntryLine");
                Draw.Line(this, "TradeLine_" + CurrentBars[0], false, lastEntryBar, lastEntryPrice, CurrentBars[0], lastEntryPrice, Brushes.Yellow, DashStyleHelper.Solid, 2);
                lastEntryBar = -1;
            }
        }

        #region WPF UI Methods
        private void CreateWpfControls()
        {
            if (myPanel != null) return;
            
            myPanel = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Top,
                Margin = new Thickness(0, 50, 50, 0)
            };
            
            btnArmLong = new System.Windows.Controls.Button
            {
                Content = "ARM LONG",
                Background = Brushes.LightGray,
                Foreground = Brushes.Black,
                Padding = new Thickness(5),
                Margin = new Thickness(2)
            };
            btnArmLong.Click += BtnArmLong_Click;
            
            btnArmShort = new System.Windows.Controls.Button
            {
                Content = "ARM SHORT",
                Background = Brushes.LightGray,
                Foreground = Brushes.Black,
                Padding = new Thickness(5),
                Margin = new Thickness(2)
            };
            btnArmShort.Click += BtnArmShort_Click;
            
            myPanel.Children.Add(btnArmLong);
            myPanel.Children.Add(btnArmShort);
            
            UserControlCollection.Add(myPanel);
            UpdateButtonsState();
            
            // Debug para verificar que se ejecuta
            if (ChartControl != null)
            {
                NinjaTrader.Code.Output.Process("[VolZoneAssist] Controles WPF inyectados en UserControlCollection.", PrintTo.OutputTab1);
            }
        }

        private void DisposeWpfControls()
        {
            if (btnArmLong != null) btnArmLong.Click -= BtnArmLong_Click;
            if (btnArmShort != null) btnArmShort.Click -= BtnArmShort_Click;
            if (myPanel != null) UserControlCollection.Remove(myPanel);
        }

        private void BtnArmLong_Click(object sender, RoutedEventArgs e)
        {
            if (Armed && Side == OrderSide.Long) 
                Armed = false; // Toggle off if already armed
            else
            {
                Side = OrderSide.Long;
                Armed = true;
                forceRedrawLines = true;
            }
            UpdateButtonsState();
        }

        private void BtnArmShort_Click(object sender, RoutedEventArgs e)
        {
            if (Armed && Side == OrderSide.Short) 
                Armed = false; // Toggle off if already armed
            else
            {
                Side = OrderSide.Short;
                Armed = true;
                forceRedrawLines = true;
            }
            UpdateButtonsState();
        }

        private void UpdateButtonsState()
        {
            if (ChartControl == null) return;
            ChartControl.Dispatcher.InvokeAsync(() =>
            {
                if (btnArmLong == null || btnArmShort == null) return;
                
                if (Armed && Side == OrderSide.Long)
                {
                    btnArmLong.Background = Brushes.LightGreen;
                    btnArmShort.Background = Brushes.LightGray;
                }
                else if (Armed && Side == OrderSide.Short)
                {
                    btnArmShort.Background = Brushes.LightPink;
                    btnArmLong.Background = Brushes.LightGray;
                }
                else
                {
                    btnArmLong.Background = Brushes.LightGray;
                    btnArmShort.Background = Brushes.LightGray;
                }
            });
        }
        #endregion

        #region Properties
        [NinjaScriptProperty]
        [Display(Name="Armar Asistente", Description="Si está activo, evalúa la siguiente zona tocada para ejecutar la orden en la dirección seleccionada.", Order=1, GroupName="01. Asistente Manual")]
        public bool Armed { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Dirección", Description="Dirección deseada de la próxima operación.", Order=2, GroupName="01. Asistente Manual")]
        public OrderSide Side { get; set; }

        [NinjaScriptProperty]
        [Range(0.50, 0.99)]
        [Display(Name="Umbral Probabilidad Mínima", Order=1, GroupName="02. Parámetros ML")]
        public double MinProbabilityThreshold { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
        [Display(Name="Multiplicador ATR Stop Loss", Order=1, GroupName="03. Riesgo")]
        public double StopLossAtrMult { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name="Multiplicador ATR Profit Target (Max)", Order=2, GroupName="03. Riesgo")]
        public double ProfitTargetAtrMult { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Cantidad Contratos", Order=3, GroupName="03. Riesgo")]
        public int Contratos { get; set; }

        [Display(Name="Solo Operar Sesión Asiática", Description="Si está activo, sólo ejecuta operaciones durante las horas de la sesión asiática (20:00 a 02:00 local).", Order=4, GroupName="03. Riesgo")]
        public bool TradeOnlyDuringAsianSession { get; set; }
        #endregion
    }
}
