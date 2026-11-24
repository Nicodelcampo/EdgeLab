//+------------------------------------------------------------------+
//|                                              FS_TypesAndTime.mqh |
//|     EdgeLab FUNDEDSYNC MQL5 Shared Enums, DST, Calendar, Configs |
//+------------------------------------------------------------------+
#ifndef FS_TYPES_AND_TIME_MQH
#define FS_TYPES_AND_TIME_MQH

#property strict

enum ENUM_FS_ACCOUNT_MODE
{
   FS_MODE_EVALUATION = 0, // Evaluation
   FS_MODE_FUNDED     = 1  // Funded
};

enum ENUM_FS_COLLISION_POLICY
{
   FS_COL_NETTING       = 0, // Netting (combine net exposure)
   FS_COL_VETO_OPPOSITE = 1, // Veto opposite new signal
   FS_COL_INDEPENDENT   = 2  // Independent virtual sleeves
};

enum ENUM_FS_PORTFOLIO_PRESET
{
   FS_PRESET_P_OPT_SF_V2      = 0, // P_OPT_SF_v2 (7 modules, W5)
   FS_PRESET_P_OPT_CORE6      = 1, // P_OPT_Core6 (6 modules, no SOMEOD)
   FS_PRESET_P_OPT_SF_SINW    = 2, // P_OPT_SF_SinW (6 modules, no W)
   FS_PRESET_CORE5_ALTACONV   = 3, // Core5_AltaConv (R+Z+T+N+SOMEOD)
   FS_PRESET_TIER1_SNIPERS_RZ = 4, // Tier1_Snipers_RZ (R+Z)
   FS_PRESET_TIER23_FLOW_TVNS = 5, // Tier23_Flow_TVNS (T+V+N+SOMEOD)
   FS_PRESET_CUSTOM_WEIGHTS   = 6  // CustomWeights
};

enum ENUM_FS_PROP_PROFILE
{
   FS_PROP_FTMO_SWING_100K    = 0, // FTMO Swing 100K (0.75% 1R, News OK)
   FS_PROP_FTMO_STD_100K      = 1, // FTMO Standard 100K (0.75% 1R, News +-2m)
   FS_PROP_THE5ERS_HS_100K    = 2, // The5ers High Stakes 100K (0.65% 1R, News +-2m)
   FS_PROP_THE5ERS_SUM_200K   = 3, // The5ers Summer 200K (0.50% 1R)
   FS_PROP_FUNDINGPIPS_STD    = 4, // FundingPips Std 100K (0.75% 1R, News +-5m)
   FS_PROP_E8_PRO_100K        = 5, // E8 Pro 1-Step 100K (0.45% 1R)
   FS_PROP_PERSONAL_CUSTOM    = 6  // Personal / Custom inputs
};

enum ENUM_FS_RISK_SIZING_MODE
{
   FS_SIZE_PCT_INITIAL = 0, // % of Initial Balance
   FS_SIZE_PCT_CURRENT = 1, // % of Current Balance
   FS_SIZE_FIXED_USD   = 2  // Fixed USD per 1R
};

enum ENUM_FS_TZ_MODE
{
   FS_TZ_NY_PLUS_7_ALL_YEAR = 0, // Broker = NY+7h all year (FTMO/The5ers/ICMarkets US DST)
   FS_TZ_EU_DST_EET         = 1, // Broker = EET/EEST (EU DST +2/+3)
   FS_TZ_FIXED_UTC_OFFSET   = 2  // Broker = Fixed UTC offset
};

enum ENUM_FS_MODULE_ID
{
   FS_MOD_R      = 0, // R_osc30_end660_ATR50
   FS_MOD_Z      = 1, // Z_b15_e20_eff40_ATR50
   FS_MOD_T      = 2, // T_stop100_BE15R_calFalse
   FS_MOD_V      = 3, // V_nm25_noCap_mae30
   FS_MOD_W      = 4, // W_slope_allowReFalse_ATR25
   FS_MOD_N      = 5, // N_d5_fbTrue_ATR25
   FS_MOD_SOMEOD = 6  // SOMEOD_ext_NQ
};

struct FsPropDefaults
{
   ENUM_FS_RISK_SIZING_MODE sizingMode;
   double evalRiskPct;
   double fundedRiskPct;
   double evalRiskUsd;
   double fundedRiskUsd;
   double maxOpenR;
   double dailyLossLimitPct;
   double evalDailyCapPct;
   bool   enforceEvalDailyCap;
   int    hardFlattenHHMM_ET;
   bool   enableNewsGuard;
   int    newsBlackoutMin;
   bool   enableFundedDdBrake;
   double fundedDdBrakeThreshPct;
   double fundedDdBrakeScale;
   ENUM_FS_COLLISION_POLICY collisionPolicy;
};

struct FsBarContext
{
   datetime closeUtc;
   datetime openUtc;
   datetime closeNy;
   datetime openNy;
   datetime closeCt;
   datetime openCt;
   int      openDateUtc;
   int      openHhmmUtc;
   int      openDateEt;
   int      closeDateEt;
   int      openMinEt;
   int      closeMinEt;
   int      closeHhmmEt;
   int      openDateCt;
   int      closeDateCt;
   int      openMinCt;
   int      closeHhmmssCt;
   int      nextMinHhmmssCt;
   int      dowCtMon0;
   int      ethTradeDate;
   bool     exactMinute;
   double   open;
   double   high;
   double   low;
   double   close;
   double   volume;
};

struct FsVirtualSleeve
{
   int      idx;
   string   moduleId;
   double   weightW5;
   bool     enabled;
   bool     isOpen;
   int      side;
   double   lots;
   double   appliedW;
   double   entryPrice;
   double   initialStopPrice;
   double   stopPrice;
   double   targetPrice;
   double   riskPts;
   double   maxFavPts;
   bool     overlayBeActivated;
   datetime entryNy;
   int      entrySessionDate;

   bool     hasPendingEntry;
   int      pendingEntrySide;
   double   pendingStopPts;
   double   pendingFixedStopMarker;
   double   pendingTargetPrice;
   bool     pendingEntryIsStopOrder;
   double   pendingEntryStopPrice;

   string   pendingExitReason;
};

struct FsCompletedTrade
{
   int      sessionDate;
   string   moduleId;
   double   weightW5;
   int      side;
   double   lots;
   datetime entryNy;
   datetime exitNy;
   double   entryPrice;
   double   initialStopPrice;
   double   exitPrice;
   double   riskPts;
   double   pnlPts;
   double   rBruto;
   double   rNetoMini;
   string   exitName;
};

string FsModuleName(int i)
{
   switch(i)
   {
      case 0: return "R_osc30_end660_ATR50";
      case 1: return "Z_b15_e20_eff40_ATR50";
      case 2: return "T_stop100_BE15R_calFalse";
      case 3: return "V_nm25_noCap_mae30";
      case 4: return "W_slope_allowReFalse_ATR25";
      case 5: return "N_d5_fbTrue_ATR25";
      case 6: return "SOMEOD_ext_NQ";
   }
   return "";
}

void FsGetPresetWeights(ENUM_FS_PORTFOLIO_PRESET preset, double &w[])
{
   ArrayResize(w, 7);
   ArrayInitialize(w, 0.0);
   switch(preset)
   {
      case FS_PRESET_P_OPT_CORE6:
         w[0] = 1.733376; w[1] = 2.060732; w[2] = 0.747167;
         w[3] = 1.002927; w[4] = 0.899909; w[5] = 1.215438;
         break;
      case FS_PRESET_P_OPT_SF_SINW:
         w[0] = 1.747109; w[1] = 2.077058; w[2] = 0.719343;
         w[3] = 1.003434; w[5] = 1.256155; w[6] = 0.875168;
         break;
      case FS_PRESET_CORE5_ALTACONV:
         w[0] = 1.802134; w[1] = 2.277168; w[2] = 0.709531;
         w[5] = 1.261968; w[6] = 0.848629;
         break;
      case FS_PRESET_TIER1_SNIPERS_RZ:
         w[0] = 0.732985; w[1] = 1.613336;
         break;
      case FS_PRESET_TIER23_FLOW_TVNS:
         w[2] = 0.774228; w[3] = 1.078114; w[5] = 1.326865; w[6] = 0.984898;
         break;
      case FS_PRESET_P_OPT_SF_V2:
      default:
         w[0] = 1.653354; w[1] = 1.965598; w[2] = 0.768284;
         w[3] = 1.019769; w[4] = 0.915674; w[5] = 1.252428; w[6] = 0.911410;
         break;
   }
}

void FsGetPropProfileDefaults(ENUM_FS_PROP_PROFILE prof, FsPropDefaults &out)
{
   out.sizingMode             = FS_SIZE_PCT_INITIAL;
   out.evalRiskPct            = 0.75;
   out.fundedRiskPct          = 0.75;
   out.evalRiskUsd            = 750.0;
   out.fundedRiskUsd          = 750.0;
   out.maxOpenR               = 3.0;
   out.dailyLossLimitPct      = 3.80;
   out.evalDailyCapPct        = 0.0;
   out.enforceEvalDailyCap    = false;
   out.hardFlattenHHMM_ET     = 1640;
   out.enableNewsGuard        = false;
   out.newsBlackoutMin        = 2;
   out.enableFundedDdBrake    = false;
   out.fundedDdBrakeThreshPct = 5.0;
   out.fundedDdBrakeScale     = 0.50;
   out.collisionPolicy        = FS_COL_NETTING;

   switch(prof)
   {
      case FS_PROP_FTMO_STD_100K:
         out.enableNewsGuard = true;
         break;
      case FS_PROP_THE5ERS_HS_100K:
         out.evalRiskPct       = 0.65;
         out.fundedRiskPct     = 0.65;
         out.evalRiskUsd       = 650.0;
         out.fundedRiskUsd     = 650.0;
         out.dailyLossLimitPct = 3.00;
         out.enableNewsGuard   = true;
         out.fundedDdBrakeThreshPct = 4.0;
         break;
      case FS_PROP_THE5ERS_SUM_200K:
         out.evalRiskPct       = 0.50;
         out.fundedRiskPct     = 0.50;
         out.evalRiskUsd       = 1000.0;
         out.fundedRiskUsd     = 1000.0;
         out.dailyLossLimitPct = 2.20;
         break;
      case FS_PROP_FUNDINGPIPS_STD:
         out.enableNewsGuard = true;
         out.newsBlackoutMin = 5;
         break;
      case FS_PROP_E8_PRO_100K:
         out.evalRiskPct       = 0.45;
         out.fundedRiskPct     = 0.45;
         out.evalRiskUsd       = 450.0;
         out.fundedRiskUsd     = 450.0;
         out.dailyLossLimitPct = 1.80;
         out.fundedDdBrakeThreshPct = 3.0;
         break;
      case FS_PROP_PERSONAL_CUSTOM:
         out.sizingMode        = FS_SIZE_FIXED_USD;
         out.evalRiskUsd       = 450.0;
         out.fundedRiskUsd     = 450.0;
         out.dailyLossLimitPct = 0.0;
         break;
      case FS_PROP_FTMO_SWING_100K:
      default:
         break;
   }
}

double FsRoundTick(double price, double tickSize)
{
   if(!MathIsValidNumber(price) || price == EMPTY_VALUE || tickSize <= 0.0) return price;
   double units = price / tickSize;
   double rounded = (units >= 0.0) ? MathFloor(units + 0.5) : MathCeil(units - 0.5);
   return rounded * tickSize;
}

bool FsIsValidPos(double v)
{
   return (v != EMPTY_VALUE && MathIsValidNumber(v) && v > 0.0 && v < 1e100);
}

bool FsIsValidFinite(double v)
{
   return (v != EMPTY_VALUE && MathIsValidNumber(v) && MathAbs(v) < 1e100);
}

double FsRoundZetaTarget(int side, double price, double tickSize)
{
   if(!MathIsValidNumber(price) || tickSize <= 0.0) return price;
   return (side <= 0) ? (MathFloor(price / tickSize) * tickSize)
                      : (MathCeil(price / tickSize) * tickSize);
}

int FsDateKey(const MqlDateTime &dt) { return dt.year * 10000 + dt.mon * 100 + dt.day; }
int FsHhmmss(const MqlDateTime &dt)  { return dt.hour * 10000 + dt.min * 100 + dt.sec; }
int FsHhmm(const MqlDateTime &dt)    { return dt.hour * 100 + dt.min; }
int FsMinOfDay(const MqlDateTime &dt){ return dt.hour * 60 + dt.min; }
int FsWeekdayMon0(const MqlDateTime &dt) { return (dt.day_of_week + 6) % 7; }

int FsDowFromYmd(int year, int mon, int day)
{
   MqlDateTime mdt;
   ZeroMemory(mdt);
   mdt.year = year;
   mdt.mon  = mon;
   mdt.day  = day;
   datetime t = StructToTime(mdt);
   TimeToStruct(t, mdt);
   return mdt.day_of_week; // 0 = Sun
}

datetime FsMakeTime(int year, int mon, int day, int hour, int minute, int sec)
{
   MqlDateTime mdt;
   ZeroMemory(mdt);
   mdt.year = year;
   mdt.mon  = mon;
   mdt.day  = day;
   mdt.hour = hour;
   mdt.min  = minute;
   mdt.sec  = sec;
   return StructToTime(mdt);
}

int FsNthSundayDom(int year, int mon, int nth)
{
   int dow1 = FsDowFromYmd(year, mon, 1);
   int firstSun = 1 + ((7 - dow1) % 7);
   return firstSun + (nth - 1) * 7;
}

int FsLastSundayDom(int year, int mon)
{
   int dowEnd = FsDowFromYmd(year, mon, 31); // Used for March and October (both 31 days)
   return 31 - dowEnd;
}

bool FsIsUsDstUtc(datetime utcSec)
{
   MqlDateTime dt;
   TimeToStruct(utcSec, dt);
   int marSun = FsNthSundayDom(dt.year, 3, 2);
   int novSun = FsNthSundayDom(dt.year, 11, 1);
   datetime startUtc = FsMakeTime(dt.year, 3, marSun, 7, 0, 0); // 02:00 EST = 07:00 UTC
   datetime endUtc   = FsMakeTime(dt.year, 11, novSun, 6, 0, 0); // 02:00 EDT = 06:00 UTC
   return (utcSec >= startUtc && utcSec < endUtc);
}

bool FsIsUsDstWallNy(datetime nyWallSec)
{
   MqlDateTime dt;
   TimeToStruct(nyWallSec, dt);
   int marSun = FsNthSundayDom(dt.year, 3, 2);
   int novSun = FsNthSundayDom(dt.year, 11, 1);
   datetime startNy = FsMakeTime(dt.year, 3, marSun, 2, 0, 0);
   datetime endNy   = FsMakeTime(dt.year, 11, novSun, 2, 0, 0);
   return (nyWallSec >= startNy && nyWallSec < endNy);
}

bool FsIsEuDstUtc(datetime utcSec)
{
   MqlDateTime dt;
   TimeToStruct(utcSec, dt);
   int marSun = FsLastSundayDom(dt.year, 3);
   int octSun = FsLastSundayDom(dt.year, 10);
   datetime startUtc = FsMakeTime(dt.year, 3, marSun, 1, 0, 0);
   datetime endUtc   = FsMakeTime(dt.year, 10, octSun, 1, 0, 0);
   return (utcSec >= startUtc && utcSec < endUtc);
}

datetime FsServerTimeToUtc(datetime serverTime, ENUM_FS_TZ_MODE tzMode, double fixedUtcOffsetHours)
{
   if(tzMode == FS_TZ_NY_PLUS_7_ALL_YEAR)
   {
      datetime nyWall = serverTime - 7 * 3600;
      int etOff = FsIsUsDstWallNy(nyWall) ? (-4 * 3600) : (-5 * 3600);
      return nyWall - etOff;
   }
   if(tzMode == FS_TZ_EU_DST_EET)
   {
      datetime candUtc = serverTime - 2 * 3600;
      if(FsIsEuDstUtc(candUtc))
         return serverTime - 3 * 3600;
      return candUtc;
   }
   return serverTime - (datetime)MathRound(fixedUtcOffsetHours * 3600.0);
}

void FsBuildBarContext(
   datetime closeUtc,
   double openPx,
   double highPx,
   double lowPx,
   double closePx,
   double vol,
   FsBarContext &ctx)
{
   datetime oUtc = closeUtc - 60;
   bool cDst = FsIsUsDstUtc(closeUtc);
   bool oDst = FsIsUsDstUtc(oUtc);
   int cEtOff = cDst ? (-4 * 3600) : (-5 * 3600);
   int oEtOff = oDst ? (-4 * 3600) : (-5 * 3600);
   int cCtOff = cDst ? (-5 * 3600) : (-6 * 3600);
   int oCtOff = oDst ? (-5 * 3600) : (-6 * 3600);

   datetime cNy = closeUtc + cEtOff;
   datetime oNy = oUtc + oEtOff;
   datetime cCt = closeUtc + cCtOff;
   datetime oCt = oUtc + oCtOff;
   datetime ethDt = oNy + 6 * 3600;

   MqlDateTime mCU, mOU, mCNy, mONy, mCCt, mOCt, mNextCt, mEth;
   TimeToStruct(closeUtc, mCU);
   TimeToStruct(oUtc, mOU);
   TimeToStruct(cNy, mCNy);
   TimeToStruct(oNy, mONy);
   TimeToStruct(cCt, mCCt);
   TimeToStruct(oCt, mOCt);
   TimeToStruct(cCt + 60, mNextCt);
   TimeToStruct(ethDt, mEth);

   ctx.closeUtc       = closeUtc;
   ctx.openUtc        = oUtc;
   ctx.closeNy        = cNy;
   ctx.openNy         = oNy;
   ctx.closeCt        = cCt;
   ctx.openCt         = oCt;
   ctx.openDateUtc    = FsDateKey(mOU);
   ctx.openHhmmUtc    = FsHhmm(mOU);
   ctx.openDateEt     = FsDateKey(mONy);
   ctx.closeDateEt    = FsDateKey(mCNy);
   ctx.openMinEt      = FsMinOfDay(mONy);
   ctx.closeMinEt     = FsMinOfDay(mCNy);
   ctx.closeHhmmEt    = FsHhmm(mCNy);
   ctx.openDateCt     = FsDateKey(mOCt);
   ctx.closeDateCt    = FsDateKey(mCCt);
   ctx.openMinCt      = FsMinOfDay(mOCt);
   ctx.closeHhmmssCt  = FsHhmmss(mCCt);
   ctx.nextMinHhmmssCt= FsHhmmss(mNextCt);
   ctx.dowCtMon0      = FsWeekdayMon0(mCCt);
   ctx.ethTradeDate   = FsDateKey(mEth);
   ctx.exactMinute    = (mCU.sec == 0);
   ctx.open           = openPx;
   ctx.high           = highPx;
   ctx.low            = lowPx;
   ctx.close          = closePx;
   ctx.volume         = (vol > 0.0) ? vol : 1.0;
}

datetime FsEasterSunday(int year)
{
   int a = year % 19;
   int b = year / 100;
   int c = year % 100;
   int d = b / 4;
   int e = b % 4;
   int f = (b + 8) / 25;
   int g = (b - f + 1) / 3;
   int h = (19 * a + b - d - g + 15) % 30;
   int i = c / 4;
   int k = c % 4;
   int l = (32 + 2 * e + 2 * i - h - k) % 7;
   int m = (a + 11 * h + 22 * l) / 451;
   int mon = (h + l - 7 * m + 114) / 31;
   int day = ((h + l - 7 * m + 114) % 31) + 1;
   return FsMakeTime(year, mon, day, 0, 0, 0);
}

bool FsIsFullNyseTradingDay(int ymd)
{
   int y = ymd / 10000;
   int m = (ymd / 100) % 100;
   int d = ymd % 100;
   if(y < 1970 || m < 1 || m > 12 || d < 1 || d > 31) return false;
   int dow = FsDowFromYmd(y, m, d);
   if(dow == 0 || dow == 6) return false;

   if(ymd == 20121029 || ymd == 20121030 || ymd == 20181205 || ymd == 20250109) return false;
   if(m == 1 && (d == 1 || (d == 2 && dow == 1))) return false;
   if(m == 1 && y >= 1998 && dow == 1 && d >= 15 && d <= 21) return false;
   if(m == 2 && dow == 1 && d >= 15 && d <= 21) return false;
   datetime goodFriday = FsEasterSunday(y) - 2 * 86400;
   MqlDateTime gfDt;
   TimeToStruct(goodFriday, gfDt);
   if(FsDateKey(gfDt) == ymd) return false;
   if(m == 5 && dow == 1 && d >= 25) return false;
   if(m == 6 && y >= 2022 && (d == 19 || (d == 18 && dow == 5) || (d == 20 && dow == 1))) return false;
   if(m == 7 && (d == 4 || (d == 5 && dow == 1) || (d == 3 && dow >= 1 && dow <= 4))) return false;
   if(m == 9 && dow == 1 && d <= 7) return false;
   if(m == 11 && ((dow == 4 && d >= 22 && d <= 28) || (dow == 5 && d >= 23 && d <= 29))) return false;
   if(m == 12 && (d == 25 || (d == 26 && dow == 1) || (d == 24 && dow >= 1 && dow <= 4))) return false;
   return true;
}

bool FsIsZetaFullNyseSession(int ymd)
{
   static const int nonFull[] = {
      20100101, 20100118, 20100215, 20100402, 20100531, 20100705, 20100906, 20101125, 20101126, 20101224,
      20110117, 20110221, 20110422, 20110530, 20110704, 20110905, 20111124, 20111125, 20111226,
      20120102, 20120116, 20120220, 20120406, 20120528, 20120703, 20120704, 20120903, 20121029, 20121030, 20121122, 20121123, 20121224, 20121225,
      20130101, 20130121, 20130218, 20130329, 20130527, 20130703, 20130704, 20130902, 20131128, 20131129, 20131224, 20131225,
      20140101, 20140120, 20140217, 20140418, 20140526, 20140703, 20140704, 20140901, 20141127, 20141128, 20141224, 20141225,
      20150101, 20150119, 20150216, 20150403, 20150525, 20150703, 20150907, 20151126, 20151127, 20151224, 20151225,
      20160101, 20160118, 20160215, 20160325, 20160530, 20160704, 20160905, 20161124, 20161125, 20161226,
      20170102, 20170116, 20170220, 20170414, 20170529, 20170703, 20170704, 20170904, 20171123, 20171124, 20171225,
      20180101, 20180115, 20180219, 20180330, 20180528, 20180703, 20180704, 20180903, 20181122, 20181123, 20181205, 20181224, 20181225,
      20190101, 20190121, 20190218, 20190419, 20190527, 20190703, 20190704, 20190902, 20191128, 20191129, 20191224, 20191225,
      20200101, 20200120, 20200217, 20200410, 20200525, 20200703, 20200907, 20201126, 20201127, 20201224, 20201225,
      20210101, 20210118, 20210215, 20210402, 20210531, 20210705, 20210906, 20211125, 20211126, 20211224,
      20220117, 20220221, 20220415, 20220530, 20220620, 20220704, 20220905, 20221124, 20221125, 20221226,
      20230102, 20230116, 20230220, 20230407, 20230529, 20230619, 20230703, 20230704, 20230904, 20231123, 20231124, 20231225,
      20240101, 20240115, 20240219, 20240329, 20240527, 20240619, 20240703, 20240704, 20240902, 20241128, 20241129, 20241224, 20241225,
      20250101, 20250109, 20250120, 20250217, 20250418, 20250526, 20250619, 20250703, 20250704, 20250901, 20251127, 20251128, 20251224, 20251225,
      20260101, 20260119, 20260216, 20260403, 20260525, 20260619, 20260703, 20260907, 20261126, 20261127, 20261224, 20261225,
      20270101, 20270118, 20270215, 20270326, 20270531, 20270618, 20270705
   };
   int y = ymd / 10000;
   int m = (ymd / 100) % 100;
   int d = ymd % 100;
   if(y < 1970 || m < 1 || m > 12 || d < 1 || d > 31) return false;
   int dow = FsDowFromYmd(y, m, d);
   if(dow == 0 || dow == 6) return false;
   if(ymd >= 20100101 && ymd <= 20270902)
   {
      int lo = 0, hi = ArraySize(nonFull) - 1;
      while(lo <= hi)
      {
         int mid = (lo + hi) / 2;
         if(nonFull[mid] == ymd) return false;
         if(nonFull[mid] < ymd) lo = mid + 1;
         else hi = mid - 1;
      }
      return true;
   }
   return FsIsFullNyseTradingDay(ymd);
}

int FsAddDaysYmd(int ymd, int deltaDays)
{
   datetime t = FsMakeTime(ymd / 10000, (ymd / 100) % 100, ymd % 100, 12, 0, 0) + deltaDays * 86400;
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return FsDateKey(dt);
}

void FsParseBlackoutMinutesCsv(string csv, int &mins[])
{
   ArrayResize(mins, 0);
   if(StringLen(csv) == 0) return;
   string norm = csv;
   StringReplace(norm, ";", ",");
   StringReplace(norm, " ", ",");
   string parts[];
   int n = StringSplit(norm, ',', parts);
   for(int i = 0; i < n; i++)
   {
      string p = parts[i];
      StringTrimLeft(p);
      StringTrimRight(p);
      if(StringLen(p) == 0) continue;
      int hhmm = (int)StringToInteger(p);
      int hh = hhmm / 100;
      int mm = hhmm % 100;
      if(hh >= 0 && hh < 24 && mm >= 0 && mm < 60)
      {
         int sz = ArraySize(mins);
         ArrayResize(mins, sz + 1);
         mins[sz] = hh * 60 + mm;
      }
   }
}

#endif
//+------------------------------------------------------------------+
