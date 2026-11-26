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
  - Configuración congelada hasta probar todas las estrategias en NT8 y que Nico vea sus curvas (2026-11-25). ES_Core_US500 está BAJO_REVISION (sin evidencia de los módulos en ES).
  - 2026-11-25: propuesta de rescate = EdgeLabCartera preset Rescate25K (T en 1 MNQ, registro de ejecución): pasa ≈ 14 % (docs/research/cartera_nt8_20261125/RESULTADO.md). Cambiar el bot lo decide Nico.
- **Demo de servidor NT8**: NT8 `EdgeLabExecutionProbe` en MES 1m y MNQ 1m; NO ACTIVO (pendiente de correr).
  Parámetros: Mode=MarketOnBarClose (luego PassiveLimitThenCross), Quantity=1, IntervalBars=3, HoldBars=1, MaxRoundTrips=15.
  - No usar Sim101 ni Playback101 para medir ejecución real.

## Planificadas

- FTMO Swing 100K: C2_VZ + C2_EVRP + Turtles_GC_CFD + Core + RQ5_ES_CFD (swing) (sin abrir; estrategias BAJO_REVISION (enmienda 2026-11-25), carteras sin efecto hasta las pruebas individuales).
- The5ers HS 100K: SOM_ES_CFD + ES5N_ES_CFD (intradía CFD) (sin abrir; estrategias BAJO_REVISION (enmienda 2026-11-25), carteras sin efecto hasta las pruebas individuales).
- LucidFlex 150K (40 % + DLL): EdgeLabCartera preset Intradía (MNQ: T, R, Z, V, RQ5, Franklin; MES: RQ5, ES5N), 1 micro c/u, sin freno diario (propuesta 2026-11-25 (docs/research/cartera_nt8_20261125/RESULTADO.md: P cobro 0,25 contraída / 0,50 desarrollo); abrir y operar lo decide Nico).
- Cuenta que permita tenencia nocturna (a definir): EdgeLabCartera preset Interdía (SOM sin_finde, C2_VZ NQ/ES) o intradía + C2_VZ (propuesta 2026-11-25; C2_VZ es el único estabilizador medido (F-C2VZ-ESTABILIZA-CARTERA-INTRADIA)).

## Auditorías de ejecución real

- ninguna todavía.

Avisos al generar: ver `python tools/estado_produccion.py --check`.
