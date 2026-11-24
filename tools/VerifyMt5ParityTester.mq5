//+------------------------------------------------------------------+
//|                                       VerifyMt5ParityTester.mq5  |
//| Headless MQL5 Numerical Parity Harness vs C# / Python Reference  |
//+------------------------------------------------------------------+
#property copyright "EdgeLab"
#property version   "1.01"
#property strict

#include <EdgeLabFundedSync/FS_CoordinatorAndAdapter.mqh>

struct FsBinM1Row
{
   long   closeUtcSec;
   double o;
   double h;
   double l;
   double c;
   double v;
};

bool g_parityDone = false;

string FormatIsoSpace(datetime dtSec)
{
   MqlDateTime dt;
   TimeToStruct(dtSec, dt);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d",
                       dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
}

void WritePortfolioRecords(int outHandle, string portTag, const CFundedSyncCoordinator *coord, int evalStartYmd)
{
   int n = coord.CompletedTradesCount();
   FsCompletedTrade r;
   for(int i = 0; i < n; i++)
   {
      if(!coord.GetCompletedTrade(i, r)) continue;
      if(r.sessionDate < evalStartYmd) continue;
      string row = StringFormat("%s,%d,%s,%.6f,%d,%s,%s,%.2f,%.4f,%.4f,%.4f,%.2f,%.6f,%.6f,%s\r\n",
         portTag,
         r.sessionDate,
         r.moduleId,
         r.weightW5,
         r.side,
         FormatIsoSpace(r.entryNy),
         FormatIsoSpace(r.exitNy),
         r.entryPrice,
         r.initialStopPrice,
         r.exitPrice,
         r.riskPts,
         r.pnlPts,
         r.rBruto,
         r.rNetoMini,
         r.exitName);
      FileWriteString(outHandle, row);
   }
}

void ConfigureCoordinatorLikeCs(
   CFundedSyncCoordinator *c,
   double maxSleeveUnits,
   double maxTotUnits,
   double risk1R,
   double maxOpR,
   ENUM_FS_COLLISION_POLICY pol,
   int flattenHhmm)
{
   c.signalTickSize     = 0.25;
   c.usdPerPointPerLot  = 2.0;
   c.lotStep            = 1.0;
   c.minLots            = 1.0;
   c.maxLotsPerSleeve   = maxSleeveUnits;
   c.maxTotalNetLots    = maxTotUnits;
   c.frictionPts        = 1.545;
   c.accountMode        = FS_MODE_EVALUATION;
   c.sizingMode         = FS_SIZE_FIXED_USD;
   c.evalRisk1R_USD     = risk1R;
   c.fundedRisk1R_USD   = risk1R;
   c.maxOpenR           = maxOpR;
   c.collisionPolicy    = pol;
   c.hardFlattenHHMM_ET = flattenHhmm;
   c.enforceEvalDailyCap= false;
   c.evalDailyCapUsd    = 0.0;
   c.dailyLossLimitUsd  = 0.0;
   c.warmupOnly         = false;
}

void RunFullParityPass()
{
   if(g_parityDone) return;
   g_parityDone = true;

   int fh = FileOpen("edgelab_parity\\nq_m1_2008_2026.bin", FILE_READ | FILE_BIN | FILE_COMMON);
   if(fh == INVALID_HANDLE)
   {
      PrintFormat("ERR_OPEN_BIN code=%d", GetLastError());
      return;
   }

   double wP7[7], wC5[7];
   FsGetPresetWeights(FS_PRESET_P_OPT_SF_V2, wP7);
   FsGetPresetWeights(FS_PRESET_CORE5_ALTACONV, wC5);
   bool flagsAll[7] = { true, true, true, true, true, true, true };

   CFundedSyncCoordinator *coordIndep = new CFundedSyncCoordinator(wP7, flagsAll, false);
   CFundedSyncCoordinator *coordCore5 = new CFundedSyncCoordinator(wC5, flagsAll, false);
   CFundedSyncCoordinator *coordP7    = new CFundedSyncCoordinator(wP7, flagsAll, false);

   ConfigureCoordinatorLikeCs(coordIndep, 10000.0, 100000.0, 100000.0, 999.0, FS_COL_INDEPENDENT, 2400);
   ConfigureCoordinatorLikeCs(coordCore5, 100.0,   100.0,    450.0,    3.0,   FS_COL_NETTING,     1640);
   ConfigureCoordinatorLikeCs(coordP7,    100.0,   100.0,    450.0,    3.0,   FS_COL_NETTING,     1640);

   FsBinM1Row buf[];
   ArrayResize(buf, 65536);
   FsBarContext ctx;
   long barCount = 0;

   while(!FileIsEnding(fh))
   {
      uint got = FileReadArray(fh, buf, 0, 65536);
      if(got == 0) break;
      for(uint i = 0; i < got; i++)
      {
         FsBuildBarContext((datetime)buf[i].closeUtcSec, buf[i].o, buf[i].h, buf[i].l, buf[i].c, buf[i].v, ctx);
         coordIndep.FeedHistoricalBar(ctx);
         coordCore5.FeedHistoricalBar(ctx);
         coordP7.FeedHistoricalBar(ctx);
         barCount++;
      }
   }
   FileClose(fh);

   int outH = FileOpen("edgelab_parity\\mt5_parity_trades_2025_2026.csv", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(outH != INVALID_HANDLE)
   {
      FileWriteString(outH, "portfolio,fecha_int,modulo,w_w5,side,en_ny,ex_ny,entry_price,stop_price,exit_price,riesgo_pts,pnl_pts,R_bruto,R_neto_mini,exit_name\r\n");
      WritePortfolioRecords(outH, "INDEP", coordIndep, 20250101);
      WritePortfolioRecords(outH, "CORE5", coordCore5, 20250101);
      WritePortfolioRecords(outH, "P7",    coordP7,    20250101);
      FileClose(outH);
   }

   PrintFormat("MT5_PARITY_DONE bars=%I64d indep=%d core5=%d p7=%d",
               barCount, coordIndep.CompletedTradesCount(), coordCore5.CompletedTradesCount(), coordP7.CompletedTradesCount());

   delete coordIndep;
   delete coordCore5;
   delete coordP7;
}

int OnInit()
{
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(!g_parityDone)
      RunFullParityPass();
   ExpertRemove();
}

double OnTester()
{
   if(!g_parityDone)
      RunFullParityPass();
   return 1.0;
}
