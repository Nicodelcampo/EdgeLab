# Estrategias instaladas en el NT8 de Nico que no estaban en el repo

Estado: VIGENTE (copia del 2026-11-26 de `Documents\NinjaTrader 8\bin\Custom\Strategies`, pedido de Nico: «subí todas las estrategias»)

Copias tal cual, para que cualquier agente tenga el código. **No se instalan** con `tools/sync_ctrader_mt5_bots.py` (no están en
`NT8_FILES`) y **no tienen evaluación EdgeLab propia** salvo que su familia figure en `docs/research/FACTORES.jsonl`; varias son de
terceros o de pruebas anteriores. Antes de operarlas: paridad con Python, costos canónicos y el embudo.

| Archivo | Qué parece ser (por el nombre) |
|---|---|
| EdgeLabTRZ.cs | combinación T + R + Z de FundedSync (antecesora de EdgeLabCartera) |
| EdgeLabFtmOrb.cs | módulo T (ORB, FtmOrb) suelto |
| EdgeLabZetaBand.cs | Z-banda |
| EdgeLabAbsorb20m.cs | absorción en 20 min |
| BigTrap2OptimizerStrategy.cs | BigTrap2 (familia cerrada como imán: `BIGTRAP2_MAGNET_LINE_CLOSED`) |
| Escalonadas150tGanadora.cs, Escalonadas150tStrategy.cs | escalonadas 150 ticks (F-ESCALONADAS-M1-SIN-SENAL) |
| HFTAutoApex.cs, HFTImpulseZones_Strategy.cs, HFT_IcebergStrategy6E.cs, BrokenIcebergRetest.cs | familias HFT / iceberg |
| HolyGrailTrendStrategy.cs, SchermanQuantReversion.cs, VolNormalizedMomentum.cs, VolZoneAssistStrategy.cs | externas / pruebas |

Las estrategias vigentes de EdgeLab están en `nt8/strategies/` (inventario: `docs/research/inventario_estrategias_20261125/`).
