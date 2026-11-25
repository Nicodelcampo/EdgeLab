# Estado de producción

Estado: VIGENTE (GENERADO con `python tools/estado_produccion.py --write` desde `config/cuentas_activas.json`; no editar a mano)  
Actualizado: 2026-11-25  

Operar con dinero real es decisión humana: el agente prepara, verifica y documenta; Nico activa.

## Cuentas

| cuenta | tipo | estado | dinero real | balance | observado | colchón al piso |
|---|---|---|---|---|---|---|
| LucidFlex 25K (`LFE02575951920002`) | eval | RESCATE | sí | $24.270,10 | 2026-11-25 | $270,10 (piso sin verificar) |
| Demo de servidor NT8 (`DEMO2xy4tfNV`) | demo | AUDITORIA_EJECUCION | no | — | — | — |

## Bot por cuenta

- **LucidFlex 25K**: NT8 `EdgeLabFundedSyncPortfolio` en MES 1-Minute ETH (>= 500 días cargados); preset `ES_Core_US500`, perfil `LucidFlex_25K_Rescate`, max_micros `1`, daily_loss_bot_usd `120`, hard_flatten_hhmm_et `1635`; NO ACTIVO (configurado en el handoff; Nico confirma si está corriendo).
  - Colchón al piso <= $270,10 si nunca cerró EOD por encima de $25.000: verificar en el dashboard.
  - Con DailyLoss $120, dos días malos seguidos consumen casi todo el colchón.
  - Evitar 08:30 ET (CPI/NFP) y 14:00 ET (FOMC) por slippage con este colchón.
- **Demo de servidor NT8**: NT8 `EdgeLabExecutionProbe` en MES 1m y MNQ 1m; NO ACTIVO (pendiente de correr).
  Parámetros: Mode=MarketOnBarClose (luego PassiveLimitThenCross), Quantity=1, IntervalBars=3, HoldBars=1, MaxRoundTrips=15.
  - No usar Sim101 ni Playback101 para medir ejecución real.

## Planificadas

- FTMO Swing 100K: C2_VZ + C2_EVRP + Turtles_GC_CFD + Core + RQ5_ES_CFD (swing) (sin abrir).
- The5ers HS 100K: SOM_ES_CFD + ES5N_ES_CFD (intradía CFD) (sin abrir).

## Auditorías de ejecución real

- ninguna todavía.

Avisos al generar: ver `python tools/estado_produccion.py --check`.
