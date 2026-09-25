// EdgeLab EXEC-QI Probe: validacion de fills para docs/research/PROTOCOLO_VALIDACION_EXEC_QI_NT8_20260924.md
//
// Experimento aleatorizado. Cada DecisionIntervalSec (con jitter), si esta flat, sortea:
//   - direccion: compra o venta;
//   - politica: A (orden a mercado) o P (limite en el mejor precio propio, con TimeoutSec y despues cruza a mercado).
// Registra el libro L1 del instante (bid/ask y sus tamanos, y por lo tanto el QI), el precio de fill y el momento.
// Sale a mercado despues de HoldSec. Politica y direccion NO dependen del QI: el QI se usa despues para condicionar.
//
// Seguridad: 1 contrato; solo cuentas listadas en AllowedAccounts (por defecto Sim101 y Playback101); una cuenta de
// otra conexion (prop, live) exige AllowNonSimAccount = true y figurar en la lista; tope de decisiones; tope de perdida;
// sin decisiones cerca de la pausa diaria de CME; nada en historico (solo State.Realtime).
//
// Salida: <Documents>\NinjaTrader 8\EdgeLab\execqi\<cuenta>_<instrumento>_<yyyyMMdd>.csv, una fila por decision cerrada.
#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion
namespace NinjaTrader.NinjaScript.Strategies
{
 public class EdgeLabExecQIProbe : Strategy
 {
  enum Phase { Idle, Working, Canceling, WaitFill, Hold, Exiting, Stopped }
  Phase phase = Phase.Idle;
  Random rng;
  double bid = double.NaN, ask = double.NaN, bsz = double.NaN, asz = double.NaN;
  DateTime lastQuote = DateTime.MinValue, nextDecision = DateTime.MinValue, deadline, exitAt, tDecision, tSubmit, tFill;
  double dBid, dAsk, dBsz, dAsz, fillPrice, exitPrice, bidAtExit, askAtExit;
  int dir, decisions, crossed;
  string policy, signal;
  Order entryOrder;
  double realizedTicks;
  string outPath;

  protected override void OnStateChange()
  {
   if (State == State.SetDefaults)
   {
    Name = "EdgeLabExecQIProbe";
    Description = "EXEC-QI: experimento aleatorizado de fills pasivo vs agresivo (1 contrato, solo simulacion por defecto).";
    Calculate = Calculate.OnEachTick;
    EntriesPerDirection = 1;
    EntryHandling = EntryHandling.AllEntries;
    IsExitOnSessionCloseStrategy = true;
    ExitOnSessionCloseSeconds = 60;
    StartBehavior = StartBehavior.WaitUntilFlat;
    RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
    IsUnmanaged = false;
    DecisionIntervalSec = 90; JitterSec = 30; TimeoutSec = 30; HoldSec = 60;
    MaxDecisions = 400; MaxLossTicks = 400; MaxSpreadTicks = 12; Seed = 20260924;
    AllowedAccounts = "Sim101;Playback101"; AllowNonSimAccount = false;
    HaltStartART = "17:50"; HaltEndART = "19:10";
   }
   else if (State == State.DataLoaded)
   {
    rng = new Random(Seed);
    string dir_ = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "EdgeLab", "execqi");
    Directory.CreateDirectory(dir_);
    string inst = Instrument.FullName.Replace(" ", "_");
    outPath = Path.Combine(dir_, string.Format("{0}_{1}_{2:yyyyMMdd}.csv", Account.Name, inst, DateTime.Now));
    if (!File.Exists(outPath))
     File.AppendAllText(outPath, "account,connection,instrument,tick_size,decision_time,submit_time,bid,ask,bid_size,ask_size,qi,dir,policy,timeout_s,crossed_after_timeout,fill_time,fill_price,exit_time,exit_price,bid_at_exit,ask_at_exit,seed,decision_n\n");
   }
   else if (State == State.Realtime)
   {
    bool listed = Array.IndexOf(AllowedAccounts.Split(';'), Account.Name) >= 0;
    bool isSim = Account.Name == "Sim101" || Account.Name == "Playback101";
    if (!listed || (!isSim && !AllowNonSimAccount))
    {
     Print(string.Format("EdgeLabExecQIProbe: cuenta {0} no autorizada (lista: {1}, AllowNonSimAccount={2}). Detenido.", Account.Name, AllowedAccounts, AllowNonSimAccount));
     phase = Phase.Stopped;
    }
   }
  }

  protected override void OnBarUpdate() { }

  protected override void OnMarketData(MarketDataEventArgs e)
  {
   if (State != State.Realtime || phase == Phase.Stopped) return;
   if (e.MarketDataType == MarketDataType.Bid) { bid = e.Price; bsz = e.Volume; lastQuote = e.Time; }
   else if (e.MarketDataType == MarketDataType.Ask) { ask = e.Price; asz = e.Volume; lastQuote = e.Time; }
   DateTime now = e.Time;
   if (nextDecision == DateTime.MinValue) nextDecision = now.AddSeconds(DecisionIntervalSec + rng.Next(0, JitterSec + 1));

   if (phase == Phase.Idle && now >= nextDecision) Decide(now);
   else if (phase == Phase.Working && now >= deadline && entryOrder != null)
   {
    phase = Phase.Canceling;
    CancelOrder(entryOrder);
   }
   else if (phase == Phase.Hold && now >= exitAt)
   {
    phase = Phase.Exiting;
    bidAtExit = bid; askAtExit = ask;
    if (dir == 1) ExitLong("X" + signal, signal); else ExitShort("X" + signal, signal);
   }
  }

  void Decide(DateTime now)
  {
   nextDecision = now.AddSeconds(DecisionIntervalSec + rng.Next(0, JitterSec + 1));
   if (decisions >= MaxDecisions || realizedTicks <= -MaxLossTicks) { Print("EdgeLabExecQIProbe: tope alcanzado, detenido."); phase = Phase.Stopped; return; }
   if (double.IsNaN(bid) || double.IsNaN(ask) || ask <= bid || (now - lastQuote).TotalSeconds > 5) return;
   if ((ask - bid) / TickSize > MaxSpreadTicks || InHalt(now) || Position.MarketPosition != MarketPosition.Flat) return;
   decisions++;
   dir = rng.Next(2) == 0 ? 1 : -1;
   policy = rng.Next(2) == 0 ? "A" : "P";
   crossed = 0;
   tDecision = now; dBid = bid; dAsk = ask; dBsz = bsz; dAsz = asz;
   signal = "EQ" + decisions.ToString(CultureInfo.InvariantCulture);
   tSubmit = now;
   if (policy == "A")
   {
    phase = Phase.WaitFill;
    entryOrder = dir == 1 ? EnterLong(1, signal) : EnterShort(1, signal);
   }
   else
   {
    phase = Phase.Working;
    deadline = now.AddSeconds(TimeoutSec);
    entryOrder = dir == 1 ? EnterLongLimit(0, true, 1, dBid, signal) : EnterShortLimit(0, true, 1, dAsk, signal);
   }
  }

  bool InHalt(DateTime t)
  {
   TimeSpan a = TimeSpan.Parse(HaltStartART, CultureInfo.InvariantCulture), b = TimeSpan.Parse(HaltEndART, CultureInfo.InvariantCulture);
   return t.TimeOfDay >= a && t.TimeOfDay < b;
  }

  protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, int filled,
                                        double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
  {
   if (entryOrder == null || order != entryOrder) return;
   if (orderState == OrderState.Cancelled && phase == Phase.Canceling && filled == 0)
   {
    crossed = 1;                                   // vencio el plazo sin fill: cruza a mercado
    phase = Phase.WaitFill;
    entryOrder = dir == 1 ? EnterLong(1, signal) : EnterShort(1, signal);
   }
   else if (orderState == OrderState.Rejected) { Print("EdgeLabExecQIProbe: orden rechazada: " + comment); phase = Phase.Idle; entryOrder = null; }
  }

  protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
                                            MarketPosition marketPosition, string orderId, DateTime time)
  {
   if (execution.Order == null) return;
   bool isEntry = execution.Order.Name == signal;
   if (isEntry && (phase == Phase.Working || phase == Phase.Canceling || phase == Phase.WaitFill))
   {
    fillPrice = price; tFill = time;
    exitAt = time.AddSeconds(HoldSec);
    phase = Phase.Hold;
   }
   else if (!isEntry && phase == Phase.Exiting && Position.MarketPosition == MarketPosition.Flat)
   {
    exitPrice = price;
    realizedTicks += dir * (exitPrice - fillPrice) / TickSize;
    WriteRow(time);
    entryOrder = null;
    phase = Phase.Idle;
   }
  }

  void WriteRow(DateTime tExit)
  {
   var ci = CultureInfo.InvariantCulture;
   double qi = (dBsz - dAsz) / Math.Max(dBsz + dAsz, 1);
   string row = string.Join(",", new[] {
    Account.Name, Account.Connection != null ? Account.Connection.Options.Name : "", Instrument.FullName, TickSize.ToString(ci),
    tDecision.ToString("o", ci), tSubmit.ToString("o", ci), dBid.ToString(ci), dAsk.ToString(ci), dBsz.ToString(ci), dAsz.ToString(ci),
    qi.ToString("F4", ci), dir.ToString(ci), policy, TimeoutSec.ToString(ci), crossed.ToString(ci), tFill.ToString("o", ci),
    fillPrice.ToString(ci), tExit.ToString("o", ci), exitPrice.ToString(ci), bidAtExit.ToString(ci), askAtExit.ToString(ci),
    Seed.ToString(ci), decisions.ToString(ci) });
   File.AppendAllText(outPath, row + "\n");
  }

  #region Properties
  [NinjaScriptProperty, Range(10, 3600), Display(Name = "DecisionIntervalSec", Order = 1, GroupName = "EXEC-QI")] public int DecisionIntervalSec { get; set; }
  [NinjaScriptProperty, Range(0, 600), Display(Name = "JitterSec", Order = 2, GroupName = "EXEC-QI")] public int JitterSec { get; set; }
  [NinjaScriptProperty, Range(1, 600), Display(Name = "TimeoutSec (T)", Order = 3, GroupName = "EXEC-QI")] public int TimeoutSec { get; set; }
  [NinjaScriptProperty, Range(1, 3600), Display(Name = "HoldSec", Order = 4, GroupName = "EXEC-QI")] public int HoldSec { get; set; }
  [NinjaScriptProperty, Range(1, 5000), Display(Name = "MaxDecisions", Order = 5, GroupName = "Seguridad")] public int MaxDecisions { get; set; }
  [NinjaScriptProperty, Range(1, 100000), Display(Name = "MaxLossTicks", Order = 6, GroupName = "Seguridad")] public int MaxLossTicks { get; set; }
  [NinjaScriptProperty, Range(1, 1000), Display(Name = "MaxSpreadTicks", Order = 7, GroupName = "Seguridad")] public int MaxSpreadTicks { get; set; }
  [NinjaScriptProperty, Display(Name = "AllowedAccounts (;)", Order = 8, GroupName = "Seguridad")] public string AllowedAccounts { get; set; }
  [NinjaScriptProperty, Display(Name = "AllowNonSimAccount", Order = 9, GroupName = "Seguridad")] public bool AllowNonSimAccount { get; set; }
  [NinjaScriptProperty, Display(Name = "HaltStartART", Order = 10, GroupName = "Seguridad")] public string HaltStartART { get; set; }
  [NinjaScriptProperty, Display(Name = "HaltEndART", Order = 11, GroupName = "Seguridad")] public string HaltEndART { get; set; }
  [NinjaScriptProperty, Display(Name = "Seed", Order = 12, GroupName = "EXEC-QI")] public int Seed { get; set; }
  #endregion
 }
}
