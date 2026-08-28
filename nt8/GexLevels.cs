// GexLevels.cs — Niveles GEX diarios (Call Wall / Put Wall / Gamma Flip) en el chart.
//
// Lee el CSV que genera tools/gex/gex_levels.py:
//   date,symbol,spot_index,call_wall,put_wall,gamma_flip,net_gex_bn,regime,source
//
// Por cada dia con niveles dibuja 3 lineas horizontales que cubren ese dia:
//   Call Wall  (resistencia)  — naranja
//   Put Wall   (soporte)      — verde
//   Gamma Flip (corte regimen)— amarillo punteado
//
// Los niveles vienen en PUNTOS DE INDICE (SPY x 10 ~ SPX). Si el chart es ES,
// usar el parametro PriceOffset para el basis (ES ~ SPX + 20-60, varia por dia).
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Windows.Media;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class GexLevels : Indicator
    {
        private sealed class Levels
        {
            public double CallWall, PutWall, Flip, NetGex;
            public string Regime;
            public bool Ok;
        }

        private readonly Dictionary<string, Levels> byDate =
            new Dictionary<string, Levels>();
        private readonly HashSet<string> drawn = new HashSet<string>();
        private DateTime lastFileWrite = DateTime.MinValue;
        private string curDate = "";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Niveles GEX diarios: Call Wall, Put Wall, Gamma Flip.";
                Name = "GexLevels";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = true;

                LevelsFile = @"E:\EdgeLab\data\gex\gex_levels.csv";
                SymbolFilter = "SPY";
                PriceOffset = 0.0;
                MaxDaysBack = 120;
                ShowLabels = true;
            }
        }

        private void ReloadIfChanged()
        {
            try
            {
                if (!File.Exists(LevelsFile)) return;
                DateTime w = File.GetLastWriteTime(LevelsFile);
                if (w == lastFileWrite) return;
                lastFileWrite = w;
                byDate.Clear();
                drawn.Clear();

                string[] lines = File.ReadAllLines(LevelsFile);
                if (lines.Length < 2) return;

                // Columnas por NOMBRE, no por posicion. Las posiciones fijas estaban
                // corridas una: leia c[3] como CallWall cuando c[3] es spot_index, asi
                // que dibujaba el PRECIO como Call Wall -- un nivel que el mercado
                // "respeta" siempre porque es el precio. Con lookup por header, agregar
                // o mover una columna del CSV no vuelve a romper esto en silencio.
                string[] head = lines[0].Split(',');
                int iDate = -1, iSym = -1, iCW = -1, iPW = -1, iFL = -1, iNG = -1, iRG = -1;
                for (int k = 0; k < head.Length; k++)
                {
                    string h = head[k].Trim().ToLowerInvariant();
                    if (h == "date") iDate = k;
                    else if (h == "symbol") iSym = k;
                    else if (h == "call_wall") iCW = k;
                    else if (h == "put_wall") iPW = k;
                    else if (h == "gamma_flip") iFL = k;
                    else if (h == "net_gex_bn") iNG = k;
                    else if (h == "regime") iRG = k;
                }
                if (iDate < 0 || iSym < 0 || iCW < 0 || iPW < 0 || iFL < 0)
                {
                    Print("GexLevels: al CSV le faltan columnas obligatorias — no dibujo");
                    return;
                }

                int minCols = Math.Max(iDate, Math.Max(iSym,
                                  Math.Max(iCW, Math.Max(iPW, iFL)))) + 1;
                for (int i = 1; i < lines.Length; i++)
                {
                    string[] c = lines[i].Split(',');
                    if (c.Length < minCols) continue;
                    if (!string.Equals(c[iSym], SymbolFilter,
                            StringComparison.OrdinalIgnoreCase)) continue;
                    var lv = new Levels();
                    var inv = CultureInfo.InvariantCulture;
                    if (!double.TryParse(c[iCW], NumberStyles.Any, inv, out lv.CallWall)) continue;
                    if (!double.TryParse(c[iPW], NumberStyles.Any, inv, out lv.PutWall)) continue;
                    if (!double.TryParse(c[iFL], NumberStyles.Any, inv, out lv.Flip)) continue;
                    if (iNG >= 0 && iNG < c.Length)
                        double.TryParse(c[iNG], NumberStyles.Any, inv, out lv.NetGex);
                    lv.Regime = (iRG >= 0 && iRG < c.Length) ? c[iRG] : "";
                    lv.Ok = true;
                    byDate[c[iDate]] = lv;   // date = yyyy-MM-dd
                }
            }
            catch { /* archivo a medio escribir: se reintenta en la proxima barra */ }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;
            ReloadIfChanged();

            string d = Time[0].ToString("yyyy-MM-dd");
            if (d == curDate) return;
            curDate = d;

            Levels lv;
            if (!byDate.TryGetValue(d, out lv) || !lv.Ok) return;
            if (drawn.Contains(d)) return;

            DateTime day;
            if (!DateTime.TryParse(d, out day)) return;
            if ((Time[0].Date - day.Date).TotalDays > MaxDaysBack && day.Date != Time[0].Date)
            {
                // solo se dibuja cuando el chart llega a ese dia; el control real
                // de historia es el propio scroll del chart
            }

            DateTime t0 = day.Date;
            DateTime t1 = day.Date.AddDays(1).AddMinutes(-1);
            double off = PriceOffset;

            var orange = Brushes.Orange;
            var green = Brushes.LimeGreen;
            var yellow = Brushes.Gold;

            Draw.Line(this, "GEX_CW_" + d, false, t0, lv.CallWall + off, t1,
                lv.CallWall + off, orange, DashStyleHelper.Solid, 2);
            Draw.Line(this, "GEX_PW_" + d, false, t0, lv.PutWall + off, t1,
                lv.PutWall + off, green, DashStyleHelper.Solid, 2);
            Draw.Line(this, "GEX_FL_" + d, false, t0, lv.Flip + off, t1,
                lv.Flip + off, yellow, DashStyleHelper.Dash, 1);

            if (ShowLabels)
            {
                var fuente = new NinjaTrader.Gui.Tools.SimpleFont("Arial", 11);
                Draw.Text(this, "GEX_CWT_" + d, false,
                    "CallWall " + (lv.CallWall + off).ToString("F0"),
                    t0, lv.CallWall + off, 8, orange, fuente,
                    System.Windows.TextAlignment.Left,
                    Brushes.Transparent, Brushes.Transparent, 0);
                Draw.Text(this, "GEX_PWT_" + d, false,
                    "PutWall " + (lv.PutWall + off).ToString("F0"),
                    t0, lv.PutWall + off, 8, green, fuente,
                    System.Windows.TextAlignment.Left,
                    Brushes.Transparent, Brushes.Transparent, 0);
                Draw.Text(this, "GEX_FLT_" + d, false,
                    "Flip " + (lv.Flip + off).ToString("F0") + "  [" + lv.Regime + " "
                    + lv.NetGex.ToString("F1") + "bn]",
                    t0, lv.Flip + off, 8, yellow, fuente,
                    System.Windows.TextAlignment.Left,
                    Brushes.Transparent, Brushes.Transparent, 0);
            }
            drawn.Add(d);
        }

        #region Properties
        [NinjaScriptProperty]
        [Display(Name = "Levels File", Order = 1, GroupName = "1. GEX",
            Description = "CSV generado por gex_levels.py")]
        public string LevelsFile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Symbol", Order = 2, GroupName = "1. GEX")]
        public string SymbolFilter { get; set; }

        [NinjaScriptProperty]
        [Range(-500, 500)]
        [Display(Name = "Price Offset (basis)", Order = 3, GroupName = "1. GEX",
            Description = "Puntos a sumar: si el chart es ES y los niveles son SPX, el basis ES-SPX del dia")]
        public double PriceOffset { get; set; }

        [NinjaScriptProperty]
        [Range(1, 2000)]
        [Display(Name = "Max Days Back", Order = 4, GroupName = "1. GEX")]
        public int MaxDaysBack { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show Labels", Order = 5, GroupName = "1. GEX")]
        public bool ShowLabels { get; set; }
        #endregion
    }
}
