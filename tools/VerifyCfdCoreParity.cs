using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using EdgeLabFundedSyncCfd;

internal static class VerifyCfdCoreParity
{
    public static int Main(string[] args)
    {
        if (args.Length < 4)
        {
            Console.Error.WriteLine("Usage: VerifyCfdCoreParity.exe <m1_csv> <eval_start_ymd> <out_trades_csv> <out_daily_csv>");
            return 2;
        }
        string barsCsv = args[0];
        int evalStartYmd = int.Parse(args[1], CultureInfo.InvariantCulture);
        string outTradesCsv = args[2];
        string outDailyCsv = args[3];

        TimeZoneInfo nyTz = FundedSyncMath.ResolveTz("Eastern Standard Time");
        TimeZoneInfo ctTz = FundedSyncMath.ResolveTz("Central Standard Time");

        var flagsAll = new bool[] { true, true, true, true, true, true, true };
        var coordIndep = new PortfolioCoordinator(
            FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.P_OPT_SF_v2),
            flagsAll, enableWTrail: false)
        {
            SignalTickSize = 0.25,
            UsdPerPointPerUnit = 2.0,
            VolumeStep = 1.0,
            MinVolumeUnits = 1.0,
            MaxVolumeUnitsPerSleeve = 10000.0,
            MaxTotalNetVolumeUnits = 100000.0,
            FrictionPts = 1.545,
            AccountMode = FundedSyncAccountMode.Evaluation,
            SizingMode = FundedSyncRiskSizingMode.FixedUsd,
            EvalRisk1R_USD = 100000.0,
            FundedRisk1R_USD = 100000.0,
            MaxOpenR = 999.0,
            CollisionPolicy = FundedSyncCollisionPolicy.Independent,
            HardFlattenHHMM_ET = 2400,
            EnforceEvalDailyCap = false,
            EvalDailyCapUSD = 0.0,
            DailyLossLimitUSD = 0.0
        };

        var coordCore5 = new PortfolioCoordinator(
            FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.Core5_AltaConv),
            flagsAll, enableWTrail: false)
        {
            SignalTickSize = 0.25,
            UsdPerPointPerUnit = 2.0,
            VolumeStep = 1.0,
            MinVolumeUnits = 1.0,
            MaxVolumeUnitsPerSleeve = 100.0,
            MaxTotalNetVolumeUnits = 100.0,
            FrictionPts = 1.545,
            AccountMode = FundedSyncAccountMode.Evaluation,
            SizingMode = FundedSyncRiskSizingMode.FixedUsd,
            EvalRisk1R_USD = 450.0,
            FundedRisk1R_USD = 450.0,
            MaxOpenR = 3.0,
            CollisionPolicy = FundedSyncCollisionPolicy.Netting,
            HardFlattenHHMM_ET = 1640,
            EnforceEvalDailyCap = false,
            EvalDailyCapUSD = 0.0,
            DailyLossLimitUSD = 0.0
        };

        var coordP7 = new PortfolioCoordinator(
            FundedSyncMath.GetPresetWeights(FundedSyncPortfolioPreset.P_OPT_SF_v2),
            flagsAll, enableWTrail: false)
        {
            SignalTickSize = 0.25,
            UsdPerPointPerUnit = 2.0,
            VolumeStep = 1.0,
            MinVolumeUnits = 1.0,
            MaxVolumeUnitsPerSleeve = 100.0,
            MaxTotalNetVolumeUnits = 100.0,
            FrictionPts = 1.545,
            AccountMode = FundedSyncAccountMode.Evaluation,
            SizingMode = FundedSyncRiskSizingMode.FixedUsd,
            EvalRisk1R_USD = 450.0,
            FundedRisk1R_USD = 450.0,
            MaxOpenR = 3.0,
            CollisionPolicy = FundedSyncCollisionPolicy.Netting,
            HardFlattenHHMM_ET = 1640,
            EnforceEvalDailyCap = false,
            EvalDailyCapUSD = 0.0,
            DailyLossLimitUSD = 0.0
        };

        var sep = new[] { ',' };
        using (var sr = new StreamReader(barsCsv, Encoding.UTF8))
        {
            string header = sr.ReadLine();
            if (header == null) throw new InvalidDataException("Empty CSV");
            string line;
            while ((line = sr.ReadLine()) != null)
            {
                if (line.Length == 0) continue;
                string[] parts = line.Split(sep);
                DateTime cUtc = DateTime.ParseExact(parts[0], "yyyy-MM-ddTHH:mm:ss", CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
                double o = double.Parse(parts[1], CultureInfo.InvariantCulture);
                double h = double.Parse(parts[2], CultureInfo.InvariantCulture);
                double l = double.Parse(parts[3], CultureInfo.InvariantCulture);
                double c = double.Parse(parts[4], CultureInfo.InvariantCulture);
                double v = double.Parse(parts[5], CultureInfo.InvariantCulture);

                BarTimeContext ctx = FundedSyncMath.BuildBarTimeContext(cUtc, o, h, l, c, v, nyTz, ctTz);
                coordIndep.FeedHistoricalBar(ctx);
                coordCore5.FeedHistoricalBar(ctx);
                coordP7.FeedHistoricalBar(ctx);
            }
        }

        using (var sw = new StreamWriter(outTradesCsv, false, Encoding.UTF8))
        {
            sw.WriteLine("portfolio,fecha_int,modulo,w_w5,side,en_ny,ex_ny,entry_price,stop_price,exit_price,riesgo_pts,pnl_pts,R_bruto,R_neto_mini,exit_name");
            WriteRecords(sw, "INDEP", coordIndep.CompletedTrades, evalStartYmd);
            WriteRecords(sw, "CORE5", coordCore5.CompletedTrades, evalStartYmd);
            WriteRecords(sw, "P7", coordP7.CompletedTrades, evalStartYmd);
        }

        // Daily portfolio R series summary for Core5 & P7
        var dailyCore5 = AggregateDailyR(coordCore5.CompletedTrades, evalStartYmd);
        var dailyP7 = AggregateDailyR(coordP7.CompletedTrades, evalStartYmd);
        var allDates = new SortedSet<int>();
        foreach (int k in dailyCore5.Keys) allDates.Add(k);
        foreach (int k in dailyP7.Keys) allDates.Add(k);

        using (var sw = new StreamWriter(outDailyCsv, false, Encoding.UTF8))
        {
            sw.WriteLine("fecha_int,R_core5,R_p7");
            foreach (int d in allDates)
            {
                double v5 = dailyCore5.ContainsKey(d) ? dailyCore5[d] : 0.0;
                double v7 = dailyP7.ContainsKey(d) ? dailyP7[d] : 0.0;
                sw.WriteLine(string.Format(CultureInfo.InvariantCulture, "{0},{1:F6},{2:F6}", d, v5, v7));
            }
        }

        return 0;
    }

    private static void WriteRecords(StreamWriter sw, string portTag, List<CompletedTradeRecord> list, int evalStartYmd)
    {
        for (int i = 0; i < list.Count; i++)
        {
            var r = list[i];
            if (r.SessionDate < evalStartYmd) continue;
            sw.WriteLine(string.Format(CultureInfo.InvariantCulture,
                "{0},{1},{2},{3:F6},{4},{5},{6},{7:F2},{8:F4},{9:F4},{10:F4},{11:F2},{12:F6},{13:F6},{14}",
                portTag, r.SessionDate, r.ModuleId, r.WeightW5, r.Side,
                r.EntryNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                r.ExitNy.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                r.EntryPrice, r.InitialStopPrice, r.ExitPrice, r.RiskPts, r.PnlPts, r.RBruto, r.RNetoMini, r.ExitName));
        }
    }

    private static Dictionary<int, double> AggregateDailyR(List<CompletedTradeRecord> list, int evalStartYmd)
    {
        var map = new Dictionary<int, double>();
        for (int i = 0; i < list.Count; i++)
        {
            var r = list[i];
            if (r.SessionDate < evalStartYmd) continue;
            double cur = map.ContainsKey(r.SessionDate) ? map[r.SessionDate] : 0.0;
            map[r.SessionDate] = cur + r.WeightW5 * r.RNetoMini;
        }
        return map;
    }
}
