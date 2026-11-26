// Arnes de paridad de EdgeLabCartera fuera de NT8 (2026-11-25). Compila los mismos .cs del motor (Core, Engines, Book)
// y corre barras M1 exportadas del parquet de NT8:
//   modo virtual : el coordinador simula los fills (como EdgeLabCandidataFS y las corridas NT8 individuales).
//   modo broker  : CarteraBook manda ordenes a un broker simulado con las reglas del backtest de NT8 (orden enviada en el
//                  cierre de la vela i, activa desde la vela i+1; mercado a la apertura; stop/limite si el rango lo toca).
// Uso: Harness.exe <modo> <salida> <noticias.csv|-> <cboe.csv|-> <interdia 0/1> <composicion> <ROOT=barras.csv> [...]
// Barras: close_utc_s,open,high,low,close,volume (vela de 1 min, sello = cierre, como NT8).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using NinjaTrader.NinjaScript.Strategies;
using NinjaTrader.NinjaScript.Strategies.EdgeLabFundedSync;

namespace EdgeLabHarness
{
    internal sealed class Bar { public long T; public double O, H, L, C, V; }

    internal sealed class SimOrder
    {
        public string Tag; public CarteraBook Book; public int Side, Qty; public CarteraOrderType Type; public double Price; public string Oco;
        public long ActiveFrom;
    }

    internal sealed class SimGateway : ICarteraGateway
    {
        public readonly List<SimOrder> Working = new List<SimOrder>();
        public long CurT;                 // sello de la vela que se esta procesando
        public int Fills, Rejects;
        public void Submit(CarteraBook book, string tag, CarteraRole role, string sleeveId, int side, int qty, CarteraOrderType type, double price, string oco)
        {
            Working.Add(new SimOrder { Tag = tag, Book = book, Side = side, Qty = qty, Type = type, Price = price, Oco = oco, ActiveFrom = CurT + 1 });
        }
        public void Change(CarteraBook book, string tag, int qty, double price)
        {
            var o = Working.FirstOrDefault(x => x.Tag == tag); if (o != null) { o.Qty = qty; o.Price = price; }
        }
        public void Cancel(CarteraBook book, string tag)
        {
            var o = Working.FirstOrDefault(x => x.Tag == tag);
            if (o == null) return;
            Working.Remove(o);
            o.Book.OnTerminal(tag, false);
        }
        public void Log(string msg) { Console.Error.WriteLine(msg); }

        /// <summary>Llena las ordenes activas del libro con la vela b (antes de que el libro procese la vela).</summary>
        public void ProcessBar(CarteraBook book, Bar b, TimeZoneInfo ny)
        {
            DateTime cNy = TimeZoneInfo.ConvertTimeFromUtc(DateTimeOffset.FromUnixTimeSeconds(b.T).UtcDateTime, ny);
            bool any = true;
            while (any)
            {
                any = false;
                // stops antes que objetivos (conservador, como la simulacion virtual)
                foreach (var o in Working.Where(x => x.Book == book && x.ActiveFrom <= b.T)
                                         .OrderBy(x => x.Type == CarteraOrderType.Market ? 0 : (x.Type == CarteraOrderType.Stop ? 1 : 2)).ToList())
                {
                    if (!Working.Contains(o)) continue;
                    double px; bool fill = false;
                    if (o.Type == CarteraOrderType.Market) { px = b.O; fill = true; }
                    else if (o.Type == CarteraOrderType.Stop)
                    {
                        if (o.Side > 0) { fill = b.H >= o.Price; px = Math.Max(b.O, o.Price); }
                        else { fill = b.L <= o.Price; px = Math.Min(b.O, o.Price); }
                    }
                    else
                    {
                        if (o.Side > 0) { fill = b.L <= o.Price; px = Math.Min(b.O, o.Price); }
                        else { fill = b.H >= o.Price; px = Math.Max(b.O, o.Price); }
                    }
                    if (!fill) continue;
                    Working.Remove(o); Fills++;
                    if (!string.IsNullOrEmpty(o.Oco))
                        foreach (var s in Working.Where(x => x.Oco == o.Oco).ToList()) { Working.Remove(s); s.Book.OnTerminal(s.Tag, false); }
                    o.Book.OnFilled(o.Tag, px, o.Qty, cNy);
                    any = true;
                    break;   // la lista cambio (nuevas ordenes o cancelaciones): se vuelve a recorrer
                }
            }
        }
    }

    internal static class Program
    {
        private static readonly Dictionary<string, string> FsIds = new Dictionary<string, string>
        {
            { "R", "R_osc30_end660_ATR50" }, { "Z", "Z_b15_e20_eff40_ATR50" }, { "T", "T_stop100_BE15R_calFalse" },
            { "V", "V_nm25_noCap_mae30" }, { "W", "W_slope_allowReFalse_ATR25" }, { "N", "N_d5_fbTrue_ATR25" },
            { "SOMEOD", "SOMEOD_ext_NQ" }, { "SOM", "SOM_sin_finde" }
        };
        private static readonly Dictionary<string, double[]> Specs = new Dictionary<string, double[]>
        {   // tick, valor del punto, friccion canonica en puntos (edgelab/costos.py, base)
            { "NQ", new[] { 0.25, 20.0, 1.5455 } }, { "ES", new[] { 0.25, 50.0, 0.8877 } },
            { "MNQ", new[] { 0.25, 2.0, 1.9775 } }, { "MES", new[] { 0.25, 5.0, 1.155 } },
            { "YM", new[] { 1.0, 5.0, 5.052 } }, { "MYM", new[] { 1.0, 0.5, 7.49 } },
            { "RTY", new[] { 0.1, 50.0, 0.4436 } }, { "GC", new[] { 0.1, 100.0, 0.605 } }
        };

        private static PortfolioCoordinator Build(string root, List<KeyValuePair<string, int>> items, string vol, bool interdia, NewsVetoCalendar cal)
        {
            var weights = new Dictionary<string, double>(); bool[] flags = new bool[FundedSyncMath.ModuleOrder.Length];
            foreach (var id in FundedSyncMath.ModuleOrder) weights[id] = 0.0;
            foreach (var kv in items) { string f; if (FsIds.TryGetValue(kv.Key, out f)) { weights[f] = 1.0; flags[Array.IndexOf(FundedSyncMath.ModuleOrder, f)] = true; } }
            bool es = root == "ES" || root == "MES";
            var c = es ? new PortfolioCoordinator(weights, flags, enableWTrail: false, rOscMult: 2.0, rEndEt: 660, rSlAtr: 0.50, zBucketMin: 15,
                            zEmaPeriod: 20, zMinEffPct: 35.0, zSlAtr: 0.50, tStopOrbMult: 1.0, tBeTrigR: 0.0, vNoiseMult: 0.30, vSlAtr: 0.35,
                            wSlAtr: 0.35, nDays: 5, nSlAtr: 0.25, tStopMinPts: 0.6, tStopMaxPts: 29.0, vTpPts: 15.7, wUseSlopeFilter: false, nAcceptBufPts: 0.9)
                       : new PortfolioCoordinator(weights, flags);
            double[] sp = Specs[root];
            bool nq = root == "NQ" || root == "MNQ";
            foreach (var kv in items)
            {
                string f; if (FsIds.TryGetValue(kv.Key, out f)) { c.SetSleeveFixedContracts(f, kv.Value); continue; }
                switch (kv.Key)
                {
                    case "RQ5": c.AddEngine(new RQ5Engine("RQ5", 60, 1.0, 1130, 0.45, 2.0, sp[2], 0.08), 1.0, kv.Value); break;
                    case "FR": c.AddEngine(new FranklinEngine("FRANKLIN", false), 1.0, kv.Value); break;
                    case "FRV": c.AddEngine(new FranklinEngine("FRANKLIN_VETOPREAP", true), 1.0, kv.Value); break;
                    case "ES5N": c.AddEngine(new ES5NEngine("ES5N"), 1.0, kv.Value); break;
                    case "C2VZ": c.AddEngine(new Carril2Engine("C2_VZ", true, nq, vol), 1.0, kv.Value); break;
                    case "C2EVRP": c.AddEngine(new Carril2Engine("C2_EVRP", false, nq, vol), 1.0, kv.Value); break;
                    default: throw new Exception("codigo desconocido " + kv.Key);
                }
            }
            c.TickSize = sp[0]; c.MicroPointValue = sp[1]; c.FrictionMiniPts = sp[2];
            c.EvalRisk1R_USD = 1.0; c.FundedRisk1R_USD = 1.0; c.MaxOpenR = 1000; c.MaxMicroContracts = 1000;
            c.CollisionPolicy = FundedSyncCollisionPolicy.Independent;
            c.HardFlattenHHMM_ET = interdia ? 0 : 1640;
            c.EnforceEvalDailyCap = false; c.DailyLossLimitUSD = 0; c.NewsVeto = cal;
            return c;
        }

        private static List<Bar> Load(string path)
        {
            var res = new List<Bar>();
            foreach (var line in File.ReadLines(path).Skip(1))
            {
                var p = line.Split(',');
                res.Add(new Bar { T = long.Parse(p[0], CultureInfo.InvariantCulture), O = double.Parse(p[1], CultureInfo.InvariantCulture),
                    H = double.Parse(p[2], CultureInfo.InvariantCulture), L = double.Parse(p[3], CultureInfo.InvariantCulture),
                    C = double.Parse(p[4], CultureInfo.InvariantCulture), V = double.Parse(p[5], CultureInfo.InvariantCulture) });
            }
            return res;
        }

        private static int Main(string[] a)
        {
            string modo = a[0], outDir = a[1], news = a[2], vol = a[3]; bool interdia = a[4] == "1"; string comp = a[5];
            Directory.CreateDirectory(outDir);
            var nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time"); var ctTz = FundedSyncMath.ResolveTz("Central Standard Time");
            NewsVetoCalendar cal = news == "-" ? null : new NewsVetoCalendar(news, 2.0, 2.0, 5.0, 5.0);
            var paths = a.Skip(6).Select(x => x.Split('=')).ToDictionary(x => x[0], x => x[1]);
            var gw = new SimGateway();
            var books = new List<CarteraBook>(); var bars = new List<List<Bar>>();
            int idx = 0;
            foreach (string blk in comp.Split(';'))
            {
                var p = blk.Split(':'); string root = p[0];
                var items = p[1].Split(',').Select(x => x.Split('=')).Select(x => new KeyValuePair<string, int>(x[0], x.Length > 1 ? int.Parse(x[1]) : 1)).ToList();
                var c = Build(root, items, vol, interdia, cal);
                c.EnableCsvLog = true; c.CsvLogPath = Path.Combine(outDir, modo + "_" + root + ".csv");
                if (File.Exists(c.CsvLogPath)) File.Delete(c.CsvLogPath);
                books.Add(new CarteraBook(idx++, root, c, Specs[root][0], gw, modo == "broker"));
                bars.Add(Load(paths[root]));
                Console.Error.WriteLine(root + ": " + bars.Last().Count + " velas");
            }
            // resultado diario por estrategia (dia de sesion CME): puntos realizados, minimo intradia (realizado + abierto en el
            // extremo adverso de cada vela) y operaciones cerradas; 1 contrato. Para simular el piso y la perdida diaria DENTRO del dia.
            var diario = new StreamWriter(Path.Combine(outDir, modo + "_diario.csv"));
            diario.WriteLine("dia,raiz,estrategia,real_pts,min_pts,n");
            var curDay = new int[books.Count]; var seen = new int[books.Count];
            var acc = new List<Dictionary<string, double[]>>();
            foreach (var bk in books) acc.Add(new Dictionary<string, double[]>());
            Action<int> flush = (int i) =>
            {
                foreach (var kv in acc[i])
                    if (kv.Value[2] > 0 || kv.Value[1] < 0)
                        diario.WriteLine(string.Format(CultureInfo.InvariantCulture, "{0},{1},{2},{3:F4},{4:F4},{5}", curDay[i], books[i].Root, kv.Key, kv.Value[0], kv.Value[1], kv.Value[2]));
                acc[i].Clear();
            };
            // recorrido en orden de tiempo (a igual sello, libro 0 primero, como NT8 con BarsInProgress)
            var pos = new int[books.Count];
            while (true)
            {
                int k = -1; long best = long.MaxValue;
                for (int i = 0; i < books.Count; i++) if (pos[i] < bars[i].Count && bars[i][pos[i]].T < best) { best = bars[i][pos[i]].T; k = i; }
                if (k < 0) break;
                var b = bars[k][pos[k]];
                bool last = pos[k] + 1 >= bars[k].Count || bars[k][pos[k] + 1].T - b.T > 30 * 60;
                gw.CurT = b.T;
                if (modo == "broker") gw.ProcessBar(books[k], b, nyTz);
                var ctx = FundedSyncMath.BuildBarTimeContext(DateTimeOffset.FromUnixTimeSeconds(b.T).UtcDateTime, b.O, b.H, b.L, b.C, b.V, nyTz, ctTz);
                ctx.IsLastBarOfSession = last;
                if (ctx.EthTradeDate != curDay[k]) { flush(k); curDay[k] = ctx.EthTradeDate; }
                books[k].OnBar(ctx);
                var co = books[k].Coord; var dk = acc[k];
                for (; seen[k] < co.CompletedTrades.Count; seen[k]++)
                {
                    var r = co.CompletedTrades[seen[k]];
                    double[] v; if (!dk.TryGetValue(r.ModuleId, out v)) { v = new double[3]; dk[r.ModuleId] = v; }
                    v[0] += r.PnlPts; v[2] += 1; if (v[0] < v[1]) v[1] = v[0];
                }
                foreach (var id in co.SleeveIds)
                {
                    var sl = co.Sleeves[id];
                    if (!sl.IsOpen) continue;
                    double adv = sl.Side > 0 ? b.L - sl.EntryPrice : sl.EntryPrice - b.H;
                    double[] v; if (!dk.TryGetValue(id, out v)) { v = new double[3]; dk[id] = v; }
                    if (v[0] + adv < v[1]) v[1] = v[0] + adv;
                }
                pos[k]++;
            }
            for (int i = 0; i < books.Count; i++) flush(i);
            diario.Close();
            foreach (var bk in books)
                Console.WriteLine(bk.Root + " operaciones " + bk.Coord.CompletedTrades.Count + " | neto esperado al final " + bk.ExpectedNet);
            Console.WriteLine("fills " + gw.Fills + " | ordenes vivas al final " + gw.Working.Count);
            return 0;
        }
    }
}
