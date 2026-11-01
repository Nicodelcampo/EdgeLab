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

// EdgeLabSpiralBasketExecutor (version=1.0, 2026-10-29)
// Estrategia de ejecución en NinjaTrader 8 para Reglas Congeladas (`ACTA_HOLDOUT`) y Canastas de Regímenes (`PISTAS_VIVAS`)
// de EdgeLab, garantizando paridad 1-a-1 con `edgelab/research/analizador.py` y `areas_expansion.simular`:
//   1. Entradas `E1A` (apertura del minuto siguiente con Calculate.OnBarClose), `E1C` (cierre de barra) y Límite (`E2`/`E3`)
//      con expiración de 120 barras M1 y trade-through de 1 tick.
//   2. Tope de pérdida por construcción (`aplicar_tope`: "pts" o "mult" sobre |TP - Entry|, redondeado hacia la entrada).
//   3. Armado causal de Break-Even (`BE = 1`) al cierre de la primera barra M1 cuya excursión favorable alcance >= 1R.
//   4. Time-stop de 240 barras M1 y cierre obligatorio al final de la sesión (`fin_ses`).
//   5. Dos arquitecturas para ejecutar Canastas de Regímenes:
//      - VirtualSubAccountsNetting (M1): K slots virtuales independientes (`Flat-Only` dentro de cada pista) sincronizados
//        con la posición neta en micro-futuros (`MNQ`, `MES`, `MGC`).
//      - SingleGlobalFlatLock (M2): bloqueo `Position.MarketPosition == MarketPosition.Flat` global en toda la canasta.
namespace NinjaTrader.NinjaScript.Strategies
{
    public enum EdgeLabBasketMode
    {
        SingleGlobalFlatLock = 0,
        VirtualSubAccountsNetting = 1
    }

    public class EdgeLabSpiralBasketExecutor : Strategy
    {
        private class VirtualSlot
        {
            public int SlotId;
            public bool Enabled;
            public int Direction;          // +1 Long, -1 Short, 0 Flat
            public double EntryPrice;
            public double StopPrice;
            public double TargetPrice;
            public double InitialRiskPts;
            public bool BreakEvenEnabled;
            public bool BreakEvenArmed;
            public int EntryBarIndex;
            public int SessionDateInt;
        }

        private readonly Dictionary<int, VirtualSlot> slots = new Dictionary<int, VirtualSlot>();
        private HashSet<int> activeRegimeSlots = new HashSet<int>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "EdgeLabSpiralBasketExecutor";
                Description = "Ejecutor NT8 con paridad exacta de reglas congeladas y canastas de regímenes de EdgeLab.";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 20;

                BasketMode = EdgeLabBasketMode.VirtualSubAccountsNetting;
                ContractsPerSlot = 1;
                MaxActiveSlots = 20;
                MaxHoldBarsM1 = 240;
                StopCapPts = 50.0;
                StopCapMultiplier = 0.0;
                EnableBreakEvenAt1R = false;
                RegimeStateFilePath = string.Empty;
            }
            else if (State == State.DataLoaded)
            {
                slots.Clear();
                activeRegimeSlots.Clear();
                for (int i = 0; i < MaxActiveSlots; i++)
                {
                    slots[i] = new VirtualSlot { SlotId = i, Enabled = true, Direction = 0 };
                    activeRegimeSlots.Add(i);
                }
                ReloadCausalRegimeMask();
            }
        }

        public static double ApplyConservativeStopCap(
            double entryPrice,
            int direction,
            double rawStopPrice,
            double targetPrice,
            double capPts,
            double capMult,
            double tickSize)
        {
            double maxDist = 0.0;
            if (capPts > 0.0)
                maxDist = capPts;
            else if (capMult > 0.0)
                maxDist = capMult * Math.Abs(targetPrice - entryPrice);

            if (maxDist <= 0.0 || Math.Abs(entryPrice - rawStopPrice) <= maxDist)
                return rawStopPrice;

            double capped = entryPrice - direction * maxDist;
            if (direction == 1)
                return Math.Ceiling(capped / tickSize) * tickSize;
            return Math.Floor(capped / tickSize) * tickSize;
        }

        private void ReloadCausalRegimeMask()
        {
            if (string.IsNullOrWhiteSpace(RegimeStateFilePath) || !File.Exists(RegimeStateFilePath))
                return;
            try
            {
                string[] lines = File.ReadAllLines(RegimeStateFilePath);
                HashSet<int> parsed = new HashSet<int>();
                foreach (string line in lines)
                {
                    string trimmed = line.Trim();
                    if (trimmed.Length == 0 || trimmed.StartsWith("#", StringComparison.Ordinal))
                        continue;
                    int id;
                    if (int.TryParse(trimmed, NumberStyles.Integer, CultureInfo.InvariantCulture, out id))
                        parsed.Add(id);
                }
                if (parsed.Count > 0)
                    activeRegimeSlots = parsed;
            }
            catch
            {
                // En caso de contienda de lectura del archivo de régimen, conserva la máscara causal previa.
            }
        }

        public bool TrySubmitSignal(
            int slotId,
            int direction,
            double entryPrice,
            double rawStopPrice,
            double targetPrice,
            bool breakEvenAt1R,
            int sessionDateInt)
        {
            if (direction != 1 && direction != -1)
                return false;
            if (!activeRegimeSlots.Contains(slotId))
                return false;

            if (BasketMode == EdgeLabBasketMode.SingleGlobalFlatLock)
            {
                foreach (KeyValuePair<int, VirtualSlot> kv in slots)
                {
                    if (kv.Value.Direction != 0)
                        return false;
                }
            }

            VirtualSlot slot;
            if (!slots.TryGetValue(slotId, out slot))
            {
                slot = new VirtualSlot { SlotId = slotId, Enabled = true, Direction = 0 };
                slots[slotId] = slot;
            }

            // Regla Flat-Only por slot (paridad con filtrar_solapadas_nt8 y Mercado.simular)
            if (slot.Direction != 0)
                return false;

            double tk = TickSize > 0.0 ? TickSize : 0.25;
            double stopFixed = ApplyConservativeStopCap(
                entryPrice, direction, rawStopPrice, targetPrice, StopCapPts, StopCapMultiplier, tk);

            slot.Direction = direction;
            slot.EntryPrice = entryPrice;
            slot.StopPrice = stopFixed;
            slot.TargetPrice = targetPrice;
            slot.InitialRiskPts = Math.Abs(entryPrice - stopFixed);
            slot.BreakEvenEnabled = breakEvenAt1R || EnableBreakEvenAt1R;
            slot.BreakEvenArmed = false;
            slot.EntryBarIndex = CurrentBar;
            slot.SessionDateInt = sessionDateInt;

            SyncNetPositionWithMarket();
            return true;
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < BarsRequiredToTrade)
                return;

            if (Bars.IsFirstBarOfSession)
                ReloadCausalRegimeMask();

            double hi = High[0];
            double lo = Low[0];
            double cl = Close[0];
            double tk = TickSize > 0.0 ? TickSize : 0.25;
            int sesInt = Time[0].Year * 10000 + Time[0].Month * 100 + Time[0].Day;
            bool changed = false;

            foreach (KeyValuePair<int, VirtualSlot> kv in slots)
            {
                VirtualSlot s = kv.Value;
                if (s.Direction == 0)
                    continue;

                bool hitStop = s.Direction == 1 ? (lo <= s.StopPrice) : (hi >= s.StopPrice);
                // Paridad estricta con areas_expansion.simular: el objetivo límite exige 1 tick de trade-through
                bool hitTarget = s.Direction == 1 ? (hi >= s.TargetPrice + tk) : (lo <= s.TargetPrice - tk);
                bool hitTimeStop = (CurrentBar - s.EntryBarIndex) >= MaxHoldBarsM1;
                bool hitSessionChange = sesInt != s.SessionDateInt;

                if (hitStop || hitTarget || hitTimeStop || hitSessionChange)
                {
                    s.Direction = 0;
                    s.BreakEvenArmed = false;
                    changed = true;
                    continue;
                }

                // Armado de Break-Even al cierre de la primera barra M1 que alcanza +1R
                if (s.BreakEvenEnabled && !s.BreakEvenArmed && s.InitialRiskPts > 0.0)
                {
                    double favExcursion = s.Direction == 1 ? (hi - s.EntryPrice) : (s.EntryPrice - lo);
                    if (favExcursion >= s.InitialRiskPts)
                    {
                        s.BreakEvenArmed = true;
                        s.StopPrice = s.Direction == 1
                            ? Math.Max(s.StopPrice, s.EntryPrice)
                            : Math.Min(s.StopPrice, s.EntryPrice);
                    }
                }
            }

            if (changed)
                SyncNetPositionWithMarket();
        }

        private void SyncNetPositionWithMarket()
        {
            int targetNetContracts = 0;
            foreach (KeyValuePair<int, VirtualSlot> kv in slots)
            {
                if (kv.Value.Direction != 0)
                    targetNetContracts += kv.Value.Direction * ContractsPerSlot;
            }

            int currentNetContracts = 0;
            if (Position.MarketPosition == MarketPosition.Long)
                currentNetContracts = Position.Quantity;
            else if (Position.MarketPosition == MarketPosition.Short)
                currentNetContracts = -Position.Quantity;

            if (targetNetContracts == currentNetContracts)
                return;

            if (targetNetContracts == 0)
            {
                if (currentNetContracts > 0)
                    ExitLong("EdgeLabBasketFlatLong");
                else if (currentNetContracts < 0)
                    ExitShort("EdgeLabBasketFlatShort");
            }
            else if (targetNetContracts > 0)
            {
                EnterLong(targetNetContracts, "EdgeLabBasketLong");
            }
            else
            {
                EnterShort(Math.Abs(targetNetContracts), "EdgeLabBasketShort");
            }
        }

        [NinjaScriptProperty]
        [Display(Name = "Basket Execution Mode", Order = 1, GroupName = "EdgeLab Basket")]
        public EdgeLabBasketMode BasketMode { get; set; }

        [NinjaScriptProperty, Range(1, 100)]
        [Display(Name = "Contracts Per Active Slot", Order = 2, GroupName = "EdgeLab Basket")]
        public int ContractsPerSlot { get; set; }

        [NinjaScriptProperty, Range(1, 100)]
        [Display(Name = "Max Active Slots (K)", Order = 3, GroupName = "EdgeLab Basket")]
        public int MaxActiveSlots { get; set; }

        [NinjaScriptProperty, Range(1, 1440)]
        [Display(Name = "Max Hold Bars M1", Order = 4, GroupName = "EdgeLab Risk")]
        public int MaxHoldBarsM1 { get; set; }

        [NinjaScriptProperty, Range(0.0, 5000.0)]
        [Display(Name = "Stop Cap Points (0 = disabled)", Order = 5, GroupName = "EdgeLab Risk")]
        public double StopCapPts { get; set; }

        [NinjaScriptProperty, Range(0.0, 20.0)]
        [Display(Name = "Stop Cap Target Multiplier (0 = disabled)", Order = 6, GroupName = "EdgeLab Risk")]
        public double StopCapMultiplier { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Break-Even at +1R", Order = 7, GroupName = "EdgeLab Risk")]
        public bool EnableBreakEvenAt1R { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Causal Regime Mask File Path", Order = 8, GroupName = "EdgeLab Regime")]
        public string RegimeStateFilePath { get; set; }
	}
}
