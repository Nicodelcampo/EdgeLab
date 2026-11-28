# AUDITORIA-CLAUDE-20261127: Corrección de CRIPTO-PIT v2, diagnóstico FutNoEq v2 y Marco Sin Forward (registro posterior, 2026-11-27)

Estado: REGISTRO POSTERIOR — auditoría y corrección post-hoc sobre las campañas de `2026-11-27` (`PR #203` y rama `audit/claude-20261127-sin-forward`). Se registra en `TRIAL_REGISTRY_GLOBAL.jsonl` para contabilidad honesta; es etapa **EF2** exploratoria/metodológica y no confirma ningún edge ni abre ningún `HOLDOUT A5` sellado (`CARRIL2_A5`, `CRIPTO_BINANCE`, `TENDENCIA_NO_EQUITY`) ni sesiones `>= 2026-10-01`.

- **Pedido de Nico (2026-11-27):** auditar los 33 commits de Claude (`80164f3d`), someter nuestro propio trabajo a 2 iteraciones de auditoría forense y definir los próximos frentes priorizados contra el referente.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa EF2.** Familias registradas: `CRIPTO_BINANCE` (12 pruebas), `TENDENCIA_NO_EQUITY` (4 pruebas), `CANASTA_AMPLIA` (8 pruebas).

Cambio respecto a falla previa: en `CRIPTO_BINANCE` se corrige el bug de neutralización de `cripto_pit.py` línea 177 (`w.sub(mean)` sobre monedas planas), se excluyen perpetuos TradFi/commodities/acciones de `UNIVERSO_PIT.csv`, se corrige `hysteresis_exit` de 35 a 25 (`rango` real `1..25`), se preservan saltos reales tras huecos internos de archivo (`2022-02-26..28`) sin inventar precios post-delisting y se eliminan el azar de fase y churn diario con 5 tranches escalonadas (`_stagger_weights`). En `TENDENCIA_NO_EQUITY` (`F-MULTIACTIVO-MECANISMOS-PERSISTENCIA-SIN-POTENCIA`) se auditan 22 futuros continuos de Yahoo `=F` verificando contaminación severa por empalmes sin back-adjustment (`NG=F` 208 días `>8%`, `CL=F` 78 días `>8%`), invalidando esa fuente de datos antes de extraer conclusiones definitivas. En `CANASTA_AMPLIA` (`F-ADAPTAR-TOPE-PUNTOS-T-F`, `F-LIT-MACRO-CFD`) se corrige la integración semanal/mensual para eliminar el spike de lunes (`1.77x`), se estandariza toda comparación de drawdown a volatilidad idéntica (`10%` anual) y se separa el `CSCV/Bayes` limpio (`Carril 2` y `Cripto v2`) de las series con sesgo previo del vendedor `CME/FundedSync`.

Antecedentes:
- `docs/research/HANDOFF_2026-11-27_CANASTA_EDGE_AUDITORIA.md`
- `docs/research/cripto_pit_20261127/RESULTADO.md` y `RESULTADO_TOP8.md`
- `docs/research/tendencia_no_equity_20261127/RESULTADO.md`
- `docs/research/canasta_amplia_20261127/RESULTADO.md` y `REGISTRO_POSTERIOR.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia antes de abrir holdout, K36 causalidad por prefijo, K51 contabilidad global, cero lectura de `>= 2026-10-01` ni `HOLDOUT A5` sellado).

Potencia previa: este bloque no realiza aperturas de `HOLDOUT A5`; computa en `MARCO_SIN_FORWARD.json` la potencia teórica de `Carril 2 Sellada 16` (`63m` sellados) y `Cripto PIT v2` (`18m` sellados) usando únicamente `DESC` y `REP`.

Diagnóstico de mecanismo: sin grilla de optimización de parámetros. Se reportan de forma íntegra las sensibilidades de fricción (`10, 20, 30, 40` bps RT en cripto), todas las fases de rebalanceo (`Phase 0..4`), la descomposición `Long-Only / Short-Only / L-S / LongAlts-ShortBTC`, los saltos de roll en futuros `=F` y los 3 escenarios de contracción OOS de `CME` (`1.0x` vs `0.5x`) a volatilidad anual idéntica (`10%`).

## Justificación económica
1. En perpetuos cripto USDT-M de Binance, la dispersión cross-sectional es elevada pero dominada por costos de transacción e inestabilidad cuando se rota intradía; reducir la frecuencia a ventanas escalonadas de `5` días sobre patas activas (`XSMOM` + `ResidMom`) mantiene captura de momentum relativo con rotación `2.7x–3.0x/mes` y exposición neta cercana a cero frente a `BTC` (`beta ~ 0.004`).
2. A nivel multi-frente, combinar mecanismos económicamente distintos (`CME Intradía` en índices, `Carril 2` swing en índices y `Cripto Cross-Sectional`) mantiene correlación entre frentes `<= 0.21`, reduciendo el drawdown a igual volatilidad cuando el borde dominante (`CME`) sufre contracción fuera de muestra (`0.5x`).

## Cómo podría refutarse
1. Si en `CRIPTO-PIT v2` el `Sharpe` neto a `20–40 bps` cae `<= 0` fuera de 2021, depende de menos de 5 días extremos (`top5_days_share > 0.50`) o se desarma tras estrés de delisting.
2. Si en `CSCV` limpio (`12,870` splits sin sobrevivientes `CME`), la canasta `1/N` cae por debajo de `0` OOS o presenta `PBO > 0.50` frente a selección aleatoria.
3. Si a volatilidad idéntica (`10%` anual) y bajo estrés realista de contracción `0.5x`, las combinaciones multi-frente no mejoran el `Calmar` ni reducen el `MDD` frente al frente `CME` aislado.
