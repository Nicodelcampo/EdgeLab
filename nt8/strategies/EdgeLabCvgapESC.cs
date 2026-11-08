#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

// EdgeLabCvgapESC (version=1.1, 2026-11-04)
// Port nativo de la regla congelada CVGAP-ES-C (edgelab/research/corredor_vol_gaps.py, escala M1) para ES, señal y ejecución en el
// mismo gráfico. Traducción línea a línea de:
//   _atr_y_vwap_m1_nb, _gaps_barras_nb (M1), _eval_stability_window_nb, _find_zone_origin_nb, _acumular_perfil_sector_nb,
//   _evaluar_percentil_causal_nb, _calcular_poc_y_va_nb, _extraer_cajas_amarillas_nb (W1 = 100 %), _contar_toques_epoca_nb,
//   _escanear_ruptura_excursion_regreso_nb y niveles(("SIG", "ORIG100", "S_CAJA")).
// Celda congelada [1,0,1,0,1,2,3,1,1,4,11]: M1 · W1 · volumen de la caja >= P90 · excursión >= 1 · regreso EN_CAJA_AMARILLA ·
//   g_tom >= 1,15 · g_cam cualquiera · tamaño del impulso >= 2,8201 ATR (tercil alto) · VWAP a favor · cualquier hora ·
//   entrada SIG (mercado en la apertura de la vela k+2), objetivo ORIG100, stop S_CAJA. Sin tope.
// Uso: gráfico ES 1 Minute con plantilla de sesión "CME US Index Futures ETH" (la sesión de Python), Calculate = OnBarClose.
// Necesita datos de ticks (la serie de 1 tick se agrega sola) para el perfil de volumen del sector, como Python.
// Warm-up: las EMAs y el percentil de volumen (últimas 50 cajas) dependen de la historia: dejar al menos 1 mes de datos antes de medir.
// Logger opcional: DisparosFile (todos los disparos con sus variables y si pasan la celda) y OperacionesFile (entradas y salidas).
namespace NinjaTrader.NinjaScript.Strategies
{
    public class EdgeLabCvgapESC : Strategy
    {
        // --- Parámetros exactos de corredor_vol_gaps.py ---
        private const int FAST = 20, SLOW = 60, STAB_W = 15, SLOPE_LB = 5, MAX_INSIDE = 3, CONFIRM_BREAK = 2;
        private const double MAX_NARROW = 15.0, TAIL_PCT = 25.0, BEYOND_PCT = 25.0, VA_PCT = 70.0, FWD_PCT = 100.0;
        private const int LOOKBACK_ZONES = 50, MIN_ZONES_PCT = 8, MIN_GAP_TICKS = 3, AWAY_TICKS = 10, VIDA_MAX = 1440, N_BINS = 20;
        private const double X_ANTES = 0.60;
        // --- Celda congelada ---
        private const double G_TOM_MIN = 1.15, TAM_IMP_MIN = 2.820143884892086;

        private class Pend { public int Dir, EndBar, IcBar, FwdEnd; public bool Emitted; public double BoxLo, BoxHi, SecLo, SecHi; }
        private class Trk
        {
            public int K0, Dir, Pvol, MExt, KBrk; public double BoxLo, BoxHi, SecLo, SecHi, Poc, Vae, Ext; public bool Broke, F0, F1, F2, Dead;
        }
        private class Gap { public int K, Conf; public double Lo, Hi; }
        private class Orden { public string Id; public int Lado; public double Stop, Obj; public int BarraDecision; }

        // series propias (índice = barra M1 desde el inicio)
        private readonly List<double> O = new List<double>(), H = new List<double>(), L = new List<double>(), C = new List<double>(), V = new List<double>();
        private readonly List<double> EF = new List<double>(), ES = new List<double>(), ATR = new List<double>(), VWAP = new List<double>();
        private readonly List<int> SES = new List<int>();
        private readonly List<Dictionary<long, int>> TICKS = new List<Dictionary<long, int>>();
        private readonly List<int> NTICKS = new List<int>();
        private Dictionary<long, int> tickBuf = new Dictionary<long, int>();
        private int tickCnt = 0;

        private readonly double[] trBuf = new double[14];
        private double trSum = 0, pvAcc = 0, vAcc = 0;
        private int sesId = -1;

        private readonly List<double> histVols = new List<double>();
        private readonly List<Pend> pend = new List<Pend>();
        private readonly List<Trk> trks = new List<Trk>();
        private readonly List<Gap> gaps = new List<Gap>();
        private bool inZone = false; private int zDir = 0, originBar = 0, outsideCnt = 0, lastCloseBar = -1000;

        private Orden pendiente = null;          // decidida en k, se envía al cierre de k+1
        private string activa = null; private int barraEntrada = -1, nOrd = 0;
        private StreamWriter logDisp, logOps;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabCvgapESC";
                Description = "CVGAP-ES-C de EdgeLab, calculada nativamente (paridad con corredor_vol_gaps.py, escala M1).";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1; EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true; ExitOnSessionCloseSeconds = 60;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 0;
                Quantity = 1; MaxBars = 240; DisparosFile = string.Empty; OperacionesFile = string.Empty;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Tick, 1);
            }
            else if (State == State.DataLoaded)
            {
                if (!string.IsNullOrWhiteSpace(DisparosFile))
                {
                    logDisp = new StreamWriter(DisparosFile, false);
                    logDisp.WriteLine("t_utc,k,dir,pt_reg,pvol,exc_am,g_tom,g_cam,tam_imp,vwap_al,h_imp,h_am,ext,ancla,mid50,mid25,orig100,sec_lo,sec_hi,poc,celda");
                }
                if (!string.IsNullOrWhiteSpace(OperacionesFile))
                {
                    logOps = new StreamWriter(OperacionesFile, false);
                    logOps.WriteLine("id,evento,t_utc,precio,cantidad,motivo,lado,entrada_teorica,stop,objetivo");
                }
            }
            else if (State == State.Terminated)
            {
                if (logOps != null && SystemPerformance != null)
                {   // 1.1: operaciones reales desde SystemPerformance (entrada y salida con precio, hora y motivo)
                    foreach (Trade tr in SystemPerformance.AllTrades)
                    {
                        string id = tr.Entry.Name, mot = tr.Exit.Name == "Stop loss" ? "STOP" : tr.Exit.Name == "Profit target" ? "OBJETIVO"
                                  : tr.Exit.Name == "TIEMPO" ? "TIEMPO" : tr.Exit.Name == "Exit on session close" ? "SESION" : tr.Exit.Name;
                        int lado = tr.Entry.MarketPosition == MarketPosition.Long ? 1 : -1;
                        logOps.WriteLine(string.Join(",", id, "ENTRADA", Epoch(tr.Entry.Time), F(tr.Entry.Price), tr.Quantity, id, lado, "", "", ""));
                        logOps.WriteLine(string.Join(",", id, "SALIDA", Epoch(tr.Exit.Time), F(tr.Exit.Price), tr.Quantity, mot, lado, "", "", ""));
                    }
                }
                if (logDisp != null) { logDisp.Dispose(); logDisp = null; }
                if (logOps != null) { logOps.Dispose(); logOps = null; }
            }
        }

        private static string F(double x) { return x.ToString("R", CultureInfo.InvariantCulture); }
        private long Epoch(DateTime t)
        {
            DateTime u = TimeZoneInfo.ConvertTimeToUtc(DateTime.SpecifyKind(t, DateTimeKind.Unspecified), NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo);
            return (long)(u - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
        }
        private double R(double x) { return Math.Round(x / TickSize, MidpointRounding.ToEven) * TickSize; }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress == 1)
            {   // ticks del minuto en curso: conteo por precio (Python pondera cada tick con v_minuto / n_ticks)
                long p = (long)Math.Round(Close[0] / TickSize);
                int n; tickBuf.TryGetValue(p, out n); tickBuf[p] = n + 1; tickCnt++;
                return;
            }
            if (BarsInProgress != 0) return;

            // ---------- 1. barra M1 cerrada: series causales ----------
            bool nuevaSes = SES.Count == 0 || Bars.IsFirstBarOfSession;
            if (nuevaSes) { sesId++; pvAcc = 0; vAcc = 0; }
            int i = C.Count;
            double o = Open[0], h = High[0], l = Low[0], c = Close[0], v = Volume[0];
            O.Add(o); H.Add(h); L.Add(l); C.Add(c); V.Add(v); SES.Add(sesId);
            TICKS.Add(tickBuf); NTICKS.Add(tickCnt); tickBuf = new Dictionary<long, int>(); tickCnt = 0;
            if (i > 6000) TICKS[i - 6000] = null;                       // memoria: ningún sector mira tan atrás

            double tr = nuevaSes ? h - l : Math.Max(h - l, Math.Max(Math.Abs(h - C[i - 1]), Math.Abs(l - C[i - 1])));
            double atr;
            if (i < 14) { trBuf[i] = tr; trSum += tr; atr = Math.Max(trSum / (i + 1), 1e-6); }
            else { int ix = i % 14; trSum += tr - trBuf[ix]; trBuf[ix] = tr; atr = Math.Max(trSum / 14.0, 1e-6); }
            ATR.Add(atr);
            double vi = Math.Max(v, 1.0); pvAcc += (h + l + c) / 3.0 * vi; vAcc += vi; VWAP.Add(pvAcc / vAcc);
            double af = 2.0 / (FAST + 1.0), aS = 2.0 / (SLOW + 1.0);
            EF.Add(i == 0 ? c : af * c + (1 - af) * EF[i - 1]); ES.Add(i == 0 ? c : aS * c + (1 - aS) * ES[i - 1]);

            // ---------- 2. orden decidida en la vela anterior: se envía ahora (llena en la apertura de k+2) ----------
            ManejarOrdenes(i);

            // ---------- 3. gaps de la barra i ----------
            if (i >= 1) DetectarGap(i);

            // ---------- 4. cajas amarillas (extraer) ----------
            if (i >= SLOW) PasoCajas(i);

            // ---------- 5. seguimiento de cajas: ruptura, excursión y regreso ----------
            for (int j = trks.Count - 1; j >= 0; j--)
            {
                Trk z = trks[j];
                if (z.Dead || i <= z.K0) continue;
                if (i >= z.K0 + VIDA_MAX || (z.F0 && z.F1 && z.F2)) { z.Dead = true; continue; }
                PasoSeguimiento(z, i);
            }
            trks.RemoveAll(z => z.Dead);
        }

        // ===================== gaps (M1, is_50t = 0) =====================
        private void DetectarGap(int i)
        {
            double umbral = Math.Max(MIN_GAP_TICKS * TickSize - 1e-9, 0.12 * ATR[i] - 1e-9);
            double diff = O[i] - C[i - 1];
            if (Math.Abs(diff) >= umbral)
            {
                double lo, hi; int conf;
                if (diff > 0) { lo = C[i - 1]; hi = O[i]; double remHi = Math.Min(hi, L[i]); conf = (remHi - lo) >= umbral ? 1 : 0; if (conf == 1) hi = remHi; }
                else { lo = O[i]; hi = C[i - 1]; double remLo = Math.Max(lo, H[i]); conf = (hi - remLo) >= umbral ? 1 : 0; if (conf == 1) lo = remLo; }
                gaps.Add(new Gap { K = i, Lo = lo, Hi = hi, Conf = conf });
                return;
            }
            if (i >= 2)
            {
                if (L[i] - H[i - 2] >= umbral) gaps.Add(new Gap { K = i, Lo = H[i - 2], Hi = L[i], Conf = 1 });
                else if (L[i - 2] - H[i] >= umbral) gaps.Add(new Gap { K = i, Lo = H[i], Hi = L[i - 2], Conf = 1 });
            }
        }

        // ===================== corredor EMA y cajas amarillas =====================
        private int EvalStability(int idx)
        {
            int start = idx - STAB_W + 1;
            if (start < SLOPE_LB) return 0;
            double f0 = EF[start], s0 = ES[start]; int d;
            if (f0 > s0) d = 1; else if (f0 < s0) d = -1; else return 0;
            int inside = 0; double prevW = Math.Abs(f0 - s0); if (prevW <= 1e-9) return 0;
            double nf = 1.0 - MAX_NARROW / 100.0;
            for (int b = start; b <= idx; b++)
            {
                double ef = EF[b], es = ES[b];
                if (d == 1 && ef <= es) return 0;
                if (d == -1 && ef >= es) return 0;
                double cw = Math.Abs(ef - es);
                if (b > start && cw < prevW * nf) return 0;
                prevW = cw;
                if (b >= SLOPE_LB)
                {
                    double fs = ef - EF[b - SLOPE_LB], ss = es - ES[b - SLOPE_LB];
                    if (d == 1 && (fs <= 0 || ss <= 0)) return 0;
                    if (d == -1 && (fs >= 0 || ss >= 0)) return 0;
                }
                double cl = C[b], hiC = Math.Max(ef, es), loC = Math.Min(ef, es);
                if (d == 1 && cl < loC) return 0;
                if (d == -1 && cl > hiC) return 0;
                if (cl >= loC && cl <= hiC) { inside++; if (inside > MAX_INSIDE) return 0; }
            }
            return d;
        }

        private int FindOrigin(int winStart, int d)
        {
            int cross = 0;
            for (int b = winStart; b > 0; b--)
            {
                if (d == 1 && EF[b] <= ES[b]) { cross = b; break; }
                if (d == -1 && EF[b] >= ES[b]) { cross = b; break; }
            }
            int best = cross;
            if (d == 1) { double bv = L[cross]; for (int b = cross; b <= winStart; b++) if (L[b] <= bv) { bv = L[b]; best = b; } }
            else { double bv = H[cross]; for (int b = cross; b <= winStart; b++) if (H[b] >= bv) { bv = H[b]; best = b; } }
            return best;
        }

        private bool Perfil(int eb, int barEnd, double slo, double shi, out double secVol, out double[] bins, out double step)
        {
            bins = new double[N_BINS]; step = Math.Max((shi - slo) / N_BINS, TickSize); secVol = 0; bool touched = false;
            for (int b = eb + 1; b <= barEnd; b++)
            {
                if (H[b] < slo || L[b] > shi) continue;
                touched = true;
                Dictionary<long, int> tk = TICKS[b]; int n = NTICKS[b];
                if (tk != null && n > 0)
                {
                    double w = V[b] / n;
                    foreach (KeyValuePair<long, int> kv in tk)
                    {
                        double px = kv.Key * TickSize;
                        if (px < slo || px > shi) continue;
                        secVol += w * kv.Value;
                        int bi = (int)((px - slo) / step); if (bi < 0) bi = 0; else if (bi >= N_BINS) bi = N_BINS - 1;
                        bins[bi] += w * kv.Value;
                    }
                }
                else
                {
                    double ovLo = Math.Max(L[b], slo), ovHi = Math.Min(H[b], shi);
                    if (ovHi >= ovLo)
                    {
                        double rng = H[b] - L[b], frac = rng > 1e-9 ? (ovHi - ovLo) / rng : 1.0, add = V[b] * frac;
                        secVol += add;
                        int bi = (int)((0.5 * (ovLo + ovHi) - slo) / step); if (bi < 0) bi = 0; else if (bi >= N_BINS) bi = N_BINS - 1;
                        bins[bi] += add;
                    }
                }
            }
            return touched;
        }

        private void Percentil(double secVol, out bool p80, out bool p90)
        {
            p80 = false; p90 = false; int nh = histVols.Count;
            if (nh < MIN_ZONES_PCT || secVol <= 0) return;
            int h0 = Math.Max(0, nh - LOOKBACK_ZONES), nw = nh - h0, less = 0;
            for (int k = h0; k < nh; k++) if (histVols[k] < secVol) less++;
            double rank = 100.0 * less / nw;
            p80 = rank >= (nw >= 20 ? 80.0 : 75.0); p90 = rank >= (nw >= 20 ? 90.0 : 85.0);
        }

        private void PocVa(double slo, double shi, double secVol, double[] bins, double step, int d, out double poc, out double vae)
        {
            double mid = 0.5 * (slo + shi); int pb = 0; double bestV = -1, bestD = 1e18;
            for (int bi = 0; bi < N_BINS; bi++)
            {
                double bv = bins[bi], dist = Math.Abs(slo + (bi + 0.5) * step - mid);
                if (bv > bestV + 1e-12 || (Math.Abs(bv - bestV) <= 1e-12 && dist < bestD)) { bestV = bv; bestD = dist; pb = bi; }
            }
            poc = slo + (pb + 0.5) * step;
            int lo = pb, hi = pb; double acc = bins[pb], target = secVol * (VA_PCT / 100.0);
            while (acc < target && (lo > 0 || hi < N_BINS - 1))
            {
                double up = hi + 1 < N_BINS ? bins[hi + 1] : -1, dn = lo - 1 >= 0 ? bins[lo - 1] : -1;
                if (up >= dn && hi + 1 < N_BINS) { hi++; acc += bins[hi]; }
                else if (lo - 1 >= 0) { lo--; acc += bins[lo]; }
                else break;
            }
            vae = d == 1 ? slo + lo * step : slo + (hi + 1) * step;
        }

        private void NuevaCaja(Pend p, int kConf, double poc, double vae, bool p90)
        {
            var z = new Trk { K0 = kConf, Dir = p.Dir, Pvol = p90 ? 1 : 0, BoxLo = p.BoxLo, BoxHi = p.BoxHi, SecLo = p.SecLo, SecHi = p.SecHi, Poc = poc, Vae = vae };
            // ruptura en la dirección del impulso ya ocurrida entre k_ic y k0 (incluye k0)
            z.Ext = z.Dir == 1 ? z.SecHi : z.SecLo; z.MExt = kConf; z.KBrk = kConf;
            int kic = Math.Min(p.IcBar, kConf);
            for (int m = Math.Max(0, kic); m <= kConf; m++)
            {
                if (!z.Broke)
                {
                    if ((z.Dir == 1 && L[m] <= z.BoxLo) || (z.Dir == -1 && H[m] >= z.BoxHi)) { z.Dead = true; break; }
                    if (z.Dir == 1 && H[m] > z.SecHi + TickSize) { z.Broke = true; z.Ext = H[m]; z.MExt = m; z.KBrk = m; }
                    else if (z.Dir == -1 && L[m] < z.SecLo - TickSize) { z.Broke = true; z.Ext = L[m]; z.MExt = m; z.KBrk = m; }
                }
                else
                {
                    if (z.Dir == 1 && H[m] > z.Ext) { z.Ext = H[m]; z.MExt = m; }
                    else if (z.Dir == -1 && L[m] < z.Ext) { z.Ext = L[m]; z.MExt = m; }
                }
            }
            if (!z.Dead) trks.Add(z);
        }

        private void PasoCajas(int i)
        {
            // 1. sectores adelantados activos
            foreach (Pend p in pend.ToArray())
            {
                if (!p.Emitted && i > p.IcBar && i < p.FwdEnd)
                {
                    bool broke = (p.Dir == 1 && H[i] > p.SecHi + TickSize) || (p.Dir == -1 && L[i] < p.SecLo - TickSize);
                    if (broke && p.SecHi > p.SecLo + 1e-9)
                    {
                        double sv, st; double[] bins;
                        if (Perfil(p.EndBar, i, p.SecLo, p.SecHi, out sv, out bins, out st) && sv > 0)
                        {
                            bool p80, p90; Percentil(sv, out p80, out p90);
                            if (p80) { double poc, vae; PocVa(p.SecLo, p.SecHi, sv, bins, st, p.Dir, out poc, out vae); NuevaCaja(p, i, poc, vae, p90); p.Emitted = true; }
                        }
                    }
                }
                if (i == p.FwdEnd)
                {
                    pend.Remove(p);
                    if (p.SecHi <= p.SecLo + 1e-9 || p.FwdEnd <= p.EndBar) continue;
                    double sv, st; double[] bins;
                    if (!Perfil(p.EndBar, p.FwdEnd, p.SecLo, p.SecHi, out sv, out bins, out st) || sv <= 0) continue;
                    bool p80, p90; Percentil(sv, out p80, out p90);
                    histVols.Add(sv);
                    if (!p.Emitted && p80) { double poc, vae; PocVa(p.SecLo, p.SecHi, sv, bins, st, p.Dir, out poc, out vae); NuevaCaja(p, i, poc, vae, p90); }
                }
            }
            // 2. corredor
            if (!inZone)
            {
                if (i - lastCloseBar < STAB_W) return;
                int d = EvalStability(i);
                if (d != 0)
                {
                    int ws = i - STAB_W + 1;
                    originBar = Math.Max(lastCloseBar + 1, FindOrigin(ws, d));
                    inZone = true; zDir = d; outsideCnt = 0;
                }
            }
            else
            {
                double ef = EF[i], es = ES[i];
                bool flipped = (zDir == 1 && ef <= es) || (zDir == -1 && ef >= es);
                bool wrong = (zDir == 1 && C[i] < es) || (zDir == -1 && C[i] > es);
                outsideCnt = wrong ? outsideCnt + 1 : 0;
                if (flipped || outsideCnt >= CONFIRM_BREAK)
                {
                    int endBar = Math.Max(originBar + 1, i - outsideCnt);
                    double bhi = -1e18, blo = 1e18;
                    for (int b = originBar; b <= endBar; b++) { if (H[b] > bhi) bhi = H[b]; if (L[b] < blo) blo = L[b]; }
                    double hImp = bhi - blo; int impW = Math.Max(1, endBar - originBar);
                    int fwdBars = Math.Max(1, (int)Math.Round(impW * (FWD_PCT / 100.0), MidpointRounding.ToEven));
                    if (hImp > 2.0 * TickSize && pend.Count < 32)
                    {
                        double tail = hImp * TAIL_PCT / 100.0, bey = hImp * BEYOND_PCT / 100.0;
                        var p = new Pend { Dir = zDir, EndBar = endBar, IcBar = i, FwdEnd = endBar + fwdBars, BoxLo = blo, BoxHi = bhi };
                        if (zDir == 1) { p.SecLo = bhi - tail; p.SecHi = bhi + bey; } else { p.SecLo = blo - bey; p.SecHi = blo + tail; }
                        pend.Add(p);
                    }
                    inZone = false; zDir = 0; outsideCnt = 0; lastCloseBar = i;
                }
            }
        }

        // ===================== ruptura, excursión, regreso y gaps =====================
        private int Toques(int gk, int mLim, double glo, double ghi, double away)
        {
            int touches = 0; bool inTouch = false, wasAway = true;
            for (int tb = gk + 1; tb < mLim; tb++)
            {
                bool ov = H[tb] >= glo && L[tb] <= ghi;
                if (ov) { if (wasAway) { touches++; wasAway = false; inTouch = true; if (touches >= 3) return touches; } }
                else if (inTouch) { if (L[tb] > ghi + away || H[tb] < glo - away) { wasAway = true; inTouch = false; } }
                else if (L[tb] > ghi + away || H[tb] < glo - away) wasAway = true;
            }
            return touches;
        }

        private void PasoSeguimiento(Trk z, int m)
        {
            double hm = H[m], lm = L[m], cm = C[m], tick = TickSize; int d = z.Dir;
            if (!z.Broke)
            {
                if ((d == 1 && lm <= z.BoxLo) || (d == -1 && hm >= z.BoxHi)) { z.Dead = true; return; }
                if (d == 1 && hm > z.SecHi + tick) { z.Broke = true; z.Ext = hm; z.MExt = m; z.KBrk = m; }
                else if (d == -1 && lm < z.SecLo - tick) { z.Broke = true; z.Ext = lm; z.MExt = m; z.KBrk = m; }
                return;
            }
            if (d == 1 && hm > z.Ext) { z.Ext = hm; z.MExt = m; } else if (d == -1 && lm < z.Ext) { z.Ext = lm; z.MExt = m; }
            double slo = z.SecLo, shi = z.SecHi, hAm = Math.Max(shi - slo, tick), hImp = Math.Max(z.BoxHi - z.BoxLo, 2 * tick);
            double ext = z.Ext, extBey = d == 1 ? ext - shi : slo - ext;
            if (extBey < Math.Max(0.25 * hAm, 2 * tick)) return;
            double semi = Math.Max(0.5 * hAm, tick), amp = d == 1 ? ext - 0.5 * (slo + shi) : 0.5 * (slo + shi) - ext, exc = amp / semi;
            if (exc < 1.0) return;
            double mid50 = 0.5 * (z.BoxLo + z.BoxHi), mid25 = d == 1 ? z.BoxLo + 0.25 * hImp : z.BoxHi - 0.25 * hImp, orig = d == 1 ? z.BoxLo : z.BoxHi;
            for (int pt = 0; pt < 3; pt++)
            {
                if ((pt == 0 && z.F0) || (pt == 1 && z.F1) || (pt == 2 && z.F2)) continue;
                bool ok = false; double ancla = z.Poc;
                if (d == 1)
                {
                    double rem = cm - shi;
                    if (pt == 0) { if (rem > 0 && rem <= X_ANTES * extBey && cm < ext - 2 * tick) { ok = true; ancla = cm + 0.25 * (ext - cm); } }
                    else if (pt == 1) { if (lm <= shi && cm >= slo && cm <= shi + 0.15 * hAm) { ok = true; ancla = Math.Max(z.Poc, shi); } }
                    else { double thr = Math.Min(z.Vae, z.Poc - 0.15 * hAm); if (lm <= thr && cm > orig + 2 * tick) { ok = true; ancla = z.Poc; } }
                }
                else
                {
                    double rem = slo - cm;
                    if (pt == 0) { if (rem > 0 && rem <= X_ANTES * extBey && cm > ext + 2 * tick) { ok = true; ancla = cm - 0.25 * (cm - ext); } }
                    else if (pt == 1) { if (hm >= slo && cm <= shi && cm >= slo - 0.15 * hAm) { ok = true; ancla = Math.Min(z.Poc, slo); } }
                    else { double thr = Math.Max(z.Vae, z.Poc + 0.15 * hAm); if (hm >= thr && cm < orig - 2 * tick) { ok = true; ancla = z.Poc; } }
                }
                if (!ok) continue;
                if (pt == 0) z.F0 = true; else if (pt == 1) z.F1 = true; else z.F2 = true;

                double sTom = 0, sCam = 0, lastTom = -1e18, lastCam = -1e18, cd = 12 * tick, away = AWAY_TICKS * tick; int nTom = 0, nCam = 0;
                for (int gi = gaps.Count - 1; gi >= 0; gi--)
                {
                    Gap g = gaps[gi];
                    if (g.K > m) continue;
                    double age = m - g.K; if (age > VIDA_MAX) break;
                    double gmid = 0.5 * (g.Lo + g.Hi), wConf = g.Conf == 1 ? 1.0 : 0.5, wAge = Math.Exp(-age / 180.0);
                    bool inExc = (d == 1 && gmid >= slo && gmid <= ext) || (d == -1 && gmid <= shi && gmid >= ext);
                    if (inExc && g.K <= z.MExt)
                    {
                        int tp = Toques(g.K, Math.Min(z.KBrk, m), g.Lo, g.Hi, away);
                        if (tp <= 1) { sTom += wConf * wAge * (tp == 1 ? 1.35 : 1.0); if (lastTom < -1e17 || Math.Abs(gmid - lastTom) <= cd) nTom++; lastTom = gmid; }
                    }
                    bool inPath = (d == 1 && gmid < cm && gmid >= orig) || (d == -1 && gmid > cm && gmid <= orig);
                    if (inPath && g.Conf == 1)
                    {
                        int tq = Toques(g.K, m, g.Lo, g.Hi, away);
                        if (tq <= 1) { sCam += wAge * (tq == 1 ? 1.35 : 1.0); if (lastCam < -1e17 || Math.Abs(gmid - lastCam) <= cd) nCam++; lastCam = gmid; }
                    }
                }
                if (nTom >= 3) sTom *= 1.25;
                if (nCam >= 3) sCam *= 1.25;

                int s = -d; double tamImp = hImp / Math.Max(ATR[m], tick);
                int vwapAl = ((s == 1 && VWAP[m] >= cm) || (s == -1 && VWAP[m] <= cm)) ? 1 : 0;
                bool celda = pt == 1 && z.Pvol == 1 && exc >= 1.0 && sTom >= G_TOM_MIN && tamImp >= TAM_IMP_MIN && vwapAl == 1;
                if (logDisp != null)
                    logDisp.WriteLine(string.Join(",", Epoch(Time[0]).ToString(CultureInfo.InvariantCulture), m.ToString(CultureInfo.InvariantCulture), d, pt, z.Pvol,
                        F(exc), F(sTom), F(sCam), F(tamImp), vwapAl, F(hImp), F(hAm), F(ext), F(ancla), F(mid50), F(mid25), F(orig), F(slo), F(shi), F(z.Poc), celda ? 1 : 0));
                if (celda) Decidir(m, s, ext, hAm, mid50, mid25, orig);
                break;                                    // a lo sumo un disparo por barra y caja
            }
            if (logDisp != null) logDisp.Flush();
        }

        // ===================== niveles(("SIG", "ORIG100", "S_CAJA")) y órdenes =====================
        private void Decidir(int k, int s, double ext, double hAm, double mid50, double mid25, double orig)
        {
            if (Bars.IsLastBarOfSession) return;                          // k+1 tiene que ser de la misma sesión
            double tick = TickSize, e = R(C[k] + s * tick);
            double rec = Math.Max(Math.Abs(e - orig), 3 * tick);
            double d50 = (mid50 - e) * s < 2 * tick ? Math.Max(0.35 * rec, 2 * tick) : (mid50 - e) * s;
            double d25r = (mid25 - e) * s >= 3 * tick ? (mid25 - e) * s : Math.Max(0.65 * rec, 3 * tick);
            double d25 = Math.Max(d25r, d50 + tick);
            double d100r = (orig - e) * s >= 4 * tick ? (orig - e) * s : Math.Max(1.0 * rec, 4 * tick);
            double d100 = Math.Max(d100r, d25 + tick);
            double tp = R(e + s * d100);
            double col = Math.Max(4 * tick, 0.55 * hAm), sl;
            if (s == -1) sl = Math.Ceiling((Math.Max(ext, e + tick) + col) / tick) * tick;
            else sl = Math.Floor((Math.Min(ext, e - tick) - col) / tick) * tick;
            if ((tp - e) * s < tick || (e - sl) * s < tick) return;
            if (pendiente != null) return;                                 // ya hay una decidida esperando la vela k+1
            pendiente = new Orden { Id = "CVGAP-ES-C-" + (++nOrd).ToString("D4", CultureInfo.InvariantCulture), Lado = s, Stop = sl, Obj = tp, BarraDecision = k };
            if (logOps != null) { logOps.WriteLine(string.Join(",", pendiente.Id, "DECISION", Epoch(Time[0]), F(e), 0, "k=" + k, s, F(e), F(sl), F(tp))); logOps.Flush(); }
        }

        private void ManejarOrdenes(int i)
        {
            // 1.1: el estado sale de la posición (en el backtest OnExecutionUpdate puede no llegar con la orden): entrada vista -> barra de entrada;
            // posición plana después de haber entrado -> operación terminada; orden que nunca llenó en 3 velas -> se libera.
            if (activa != null)
            {
                if (Position.MarketPosition != MarketPosition.Flat) { if (barraEntrada < 0) barraEntrada = CurrentBars[0] - 1; }
                else if (barraEntrada >= 0 || CurrentBars[0] - envioBarra > 3) { activa = null; barraEntrada = -1; }
            }
            if (activa != null && Position.MarketPosition != MarketPosition.Flat && barraEntrada >= 0 && CurrentBars[0] - barraEntrada >= MaxBars)
            {
                if (Position.MarketPosition == MarketPosition.Long) ExitLong("TIEMPO", activa); else ExitShort("TIEMPO", activa);
            }
            if (pendiente == null || i != pendiente.BarraDecision + 1) { if (pendiente != null && i > pendiente.BarraDecision + 1) pendiente = null; return; }
            Orden p = pendiente; pendiente = null;
            if (Bars.IsLastBarOfSession || SES[i] != SES[p.BarraDecision]) { Log(p.Id, "OMITIDA", Time[0], 0, 0, "fin_de_sesion", p); return; }
            if (activa != null || Position.MarketPosition != MarketPosition.Flat) { Log(p.Id, "OMITIDA", Time[0], 0, 0, "posicion_abierta", p); return; }
            activa = p.Id; barraEntrada = -1; envioBarra = CurrentBars[0];
            SetStopLoss(p.Id, CalculationMode.Price, p.Stop, false);
            SetProfitTarget(p.Id, CalculationMode.Price, p.Obj);
            if (p.Lado == 1) EnterLong(Quantity, p.Id); else EnterShort(Quantity, p.Id);
            ultima = p;
        }
        private Orden ultima = null; private int envioBarra = -1;

        private void Log(string id, string ev, DateTime t, double precio, int cant, string motivo, Orden p)
        {
            if (logOps == null) return;
            logOps.WriteLine(string.Join(",", id, ev, Epoch(t).ToString(CultureInfo.InvariantCulture), F(precio), cant.ToString(CultureInfo.InvariantCulture), motivo,
                p != null ? p.Lado.ToString(CultureInfo.InvariantCulture) : "", "", p != null ? F(p.Stop) : "", p != null ? F(p.Obj) : ""));
            logOps.Flush();
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, MarketPosition marketPosition,
                                                  string orderId, DateTime time)
        {
            if (execution.Order == null) return;
            string nombre = execution.Order.Name;
            if (execution.IsEntry && barraEntrada < 0) barraEntrada = CurrentBars[0];
        }

        #region Properties
        [NinjaScriptProperty][Range(1, int.MaxValue)]
        [Display(Name = "Contratos", Order = 1, GroupName = "EdgeLab")]
        public int Quantity { get; set; }

        [NinjaScriptProperty][Range(1, int.MaxValue)]
        [Display(Name = "Tope de tenencia (velas M1)", Order = 2, GroupName = "EdgeLab")]
        public int MaxBars { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "CSV de disparos (vacío = no)", Order = 3, GroupName = "EdgeLab")]
        public string DisparosFile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "CSV de operaciones (vacío = no)", Order = 4, GroupName = "EdgeLab")]
        public string OperacionesFile { get; set; }
        #endregion
    }
}
