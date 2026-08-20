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

                LevelsFile = @"D:\EdgeLab\data\gex\gex_levels.csv";
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
                for (int i = 1; i < lines.Length; i++)  // salta header
                {
                    string[] c = lines[i].Split(',');
                    if (c.Length < 9) continue;
                    if (!string.Equals(c[1], SymbolFilter,
                            StringComparison.OrdinalIgnoreCase)) continue;
                    var lv = new Levels();
                    var inv = CultureInfo.InvariantCulture;
                    if (!double.TryParse(c[3], NumberStyles.Any, inv, out lv.CallWall)) continue;
                    if (!double.TryParse(c[4], NumberStyles.Any, inv, out lv.PutWall)) continue;
                    if (!double.TryParse(c[5], NumberStyles.Any, inv, out lv.Flip)) continue;
                    double.TryParse(c[6], NumberStyles.Any, inv, out lv.NetGex);
                    lv.Regime = c[7];
                    lv.Ok = true;
                    byDate[c[0]] = lv;   // date = yyyy-MM-dd
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
                Draw.Text(this, "GEX_CWT_" + d, "CallWall " + (lv.CallWall + off).ToString("F0"),
                    t0, lv.CallWall + off, orange);
                Draw.Text(this, "GEX_PWT_" + d, "PutWall " + (lv.PutWall + off).ToString("F0"),
                    t0, lv.PutWall + off, green);
                Draw.Text(this, "GEX_FLT_" + d,
                    "Flip " + (lv.Flip + off).ToString("F0") + "  [" + lv.Regime + " "
                    + lv.NetGex.ToString("F1") + "bn]",
                    t0, lv.Flip + off, yellow);
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
