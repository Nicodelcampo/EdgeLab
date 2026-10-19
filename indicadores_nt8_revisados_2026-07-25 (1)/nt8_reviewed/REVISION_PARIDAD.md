# Revisión de los 5 indicadores NT8 — 2026-07-25

## Resultado ejecutivo

| Indicador | SHA-256 recibido | Veredicto | Cambio aplicado |
|---|---|---|---|
| Gaps2.cs | `04a578cdac758764e8e3f3dbef4eca68d009cb19a880e33f76ca40390b3eced6` | Ya tiene paridad exacta para la configuración validada. No apareció un defecto nuevo que justifique romper esa referencia. | Ninguno |
| BigTrap2.cs | `0f918e063a6bd3b063ff7d25044feb95203a7d456d72268b2c3508cd114c31e6` | El archivo recibido ya es v2.1 y contiene el fix correcto: comparación en medios ticks enteros, `AwayFromZero`, empate excluido. | Ninguno adicional |
| VolTicksPOC2.cs | `77acadc4cd7c62159be9d866020c2cd27f0c4e64c5a8c7bd75593ab5d931a951` | Conversión de precios a ticks robusta. Sin defecto ULP de alta confianza con defaults. | Ninguno |
| HFTZones2.cs | `b0238867004fa05909c256e0e3cffa9fef602aaaeee8383d705e2577edc27b7d` | Hallazgo alto: `retro > allowed` y altura se calculaban dividiendo doubles por TickSize; podía decidir distinto en el borde por 1 ULP. | **Corregido a v2.1** |
| aVolCellPOI2.cs | `6539bfb6a80f7991e06f9c85a91927f60ed54601214bc69c39d7fddf882ed585` | Usa ticks enteros y zonas definidas en medias celdas; sin defecto ULP de alta confianza. | Ninguno |

## Cambio en HFTZones2 v2.1

- Se agregó `PriceToTick(price)` con `Math.Round(price / TickSize, MidpointRounding.AwayFromZero)`.
- La altura y el retroceso se calculan como diferencias entre índices enteros de tick.
- La comparación conserva la semántica estricta: `retroTicks > allowed`; el empate no corta la racha.
- `FinalizeStreak` usa la misma altura entera, evitando que detección y clasificación discrepen.
- Se actualizó la meta del CSV a `version=2.1` y `engine=...integer_grid`.
- No se cambió ningún parámetro, umbral, lifecycle, geometría ni clasificación.

## Limitación transversal confirmada

BigTrap2, VolTicksPOC2 y aVolCellPOI2 reconstruyen footprint con `AddDataSeries(Tick, 1)` y take/reset al cierre de la barra primaria. El diagnóstico de BigTrap2 mostró que este patrón es confiable en `time:1` para la ventana comparada, pero no en `tick:25` (89,12 % de `FOOTPRINT_MISMATCH`). Por ahora, generar sus oráculos en charts de **1 Minute**, no de ticks.

Gaps2 y HFTZones2 también consumen la subserie de un tick, pero no usan ese take/reset de footprint para crear el mismo tipo de perfil por barra. Aun así, cada oráculo debe conservar su `bar_spec` y metadatos exactos.

## Riesgo condicionado en VolTicksPOC2

Con el default `PriceMarkTicks=1`, los bordes quedan a medio tick y un precio negociable no puede empatar con ellos: riesgo ULP bajo. Si en el futuro se barren valores **pares** de `PriceMarkTicks`, los bordes quedan sobre ticks enteros y las comparaciones `Close[0] > UpperPrice` / `< LowerPrice` deberían migrarse a medios ticks enteros antes de considerar esas configs cubiertas.

## Próximos oráculos

1. BigTrap2 v2.1: `time:1`, 6E 09-26, defaults, archivo nuevo `BigTrap2_time1_6E_0926_v2.csv`.
2. HFTZones2 v2.1: compilar primero este archivo corregido; después exportar su primer oráculo `time:1` con nombre nuevo y meta v2.1.
3. VolTicksPOC2 y aVolCellPOI2: `time:1`, defaults, archivos nuevos.
4. Gaps2: conservar el binario/código actual para no invalidar la referencia que ya dio PASS; cualquier modificación futura exige nuevo digest y nuevo oráculo.

## QA realizado

- Auditoría estática de divisiones por `TickSize`, redondeos, comparaciones feed-vs-reconstruido, subserie de un tick y metadatos.
- Balance de llaves de HFTZones2 v2.1: 177/177.
- No se pudo compilar NinjaScript en el sandbox porque no contiene los assemblies de NinjaTrader. La compilación final debe hacerse en el editor de NT8.
