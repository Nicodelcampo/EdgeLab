# L2 público P0 — piloto de factibilidad BTC a un minuto

Estado: **MEDIDO, EXPLORATORIO, NO ESTRATEGIA**. Autorización: pedido de Nico del 29/09 para registrar e iniciar investigación en sandbox. Diseño registrado antes del cálculo en commit `632dedd316d246cb43545ea8b758b6a866c655ac`. No se modificó el kernel actual, ni se consultaron particiones selladas.

## Resultado

Añadir dos proxies agregados de flujo al baseline **no mejora la predicción en esta muestra**: RMSE 14.5122 → 14.5241 puntos básicos; empeora 0.0824 % en agregado. Mejora 1 día y empeora 3. Ambos R² frente a la media de evaluación son negativos (-0.003664 y -0.005319). Esto no demuestra que L2 sea inútil: delimita una especificación de laboratorio, un activo, una ventana y un horizonte.

## Datos y calidad

- Fuente: https://www.kaggle.com/datasets/martinsn/high-frequency-crypto-limit-order-book-data, versión 1, `BTC_1min.csv`, licencia publicada CC0.
- SHA-256 CSV: `1a4bf5d19f0f9b41f93a7fadacb44f015f8f7eb3212995b77bd70182d99afa93`. Raw y ZIP permanecen fuera del repo.
- 17,113 filas, 156 columnas. Ventana UTC: 2021-04-07T11:33:41.122161+00:00 → 2021-04-19T09:54:00.386544+00:00.
- Sin duplicados ni nulos; spread positivo y notionales no negativos. `system_time` parseado UTC. El índice `Unnamed: 0` es serial, no medida; se elimina, no se suma.
- 71 intervalos no son exactamente 60 s. Se exige transición exacta 60 s antes y después de cada fila.
- Se excluyen 1,337 filas de los días parciales extremos. En días interiores: 132 filas por gaps y 579 adicionales por proxy no finito. Reconciliación: 9,630 entrenamiento + 5,435 evaluación + 2,048 excluidas = 17,113.
- “Días completos” del diseño significa fechas interiores, no cobertura perfecta de 1440 filas: se conservaron gaps y se publicaron exclusiones, sin completar filas.

## Método fijo

Baseline: retorno log del minuto anterior, magnitud de ese retorno y spread relativo. Extensión: dos proxies de los 15 niveles:

1. Mercado: `(market_asks - market_bids) / (market_asks + market_bids)`.
2. Flujo límite neto: `((limit_bids - cancel_bids) - (limit_asks - cancel_asks)) / (limit_bids + cancel_bids + limit_asks + cancel_asks)`.

Los denominadores cero quedan missing, nunca cero imputado. **No son OFI exacto de eventos ni QI de colas**. Las convenciones de lado/ventana se toman de etiquetas del dataset, no se verificaron contra mensajes originales.

Target: cambio log del midprice de la siguiente fila, sólo si dista exactamente un minuto; en puntos básicos. Fechas interiores 08–18/04/2021: primeros 7 días entrenamiento, últimos 4 evaluación desde 2021-04-15. Frontera purgada: ningún target de entrenamiento entra en evaluación. Ajuste lineal, ridge fijo 1e-6, normalización sólo en entrenamiento. Sin grilla, sin elegir horizonte/corte ganador, sin P&L. Timestamps de sistema y disponibilidad exacta de las agregaciones no auditados: no se afirma ejecutabilidad causal en vivo.

| Día UTC de evaluación | Minutos | RMSE baseline (pb) | RMSE + L2 (pb) |
|---|---:|---:|---:|
| 2021-04-15 | 1,385 | 6.8238 | 6.8487 |
| 2021-04-16 | 1,351 | 8.8266 | 8.8024 |
| 2021-04-17 | 1,362 | 7.5753 | 7.5767 |
| 2021-04-18 | 1,337 | 25.8978 | 25.9262 |

Diagnóstico descriptivo (todas las fechas interiores elegibles; no confirmación):

| Proxy | Corr. retorno contemporáneo | Corr. siguiente minuto |
|---|---:|---:|
| market_proxy | -0.0276 | -0.0023 |
| net_limit_proxy | 0.1797 | 0.0600 |

Asociación contemporánea no implica predicción. No se usó la correlación para seleccionar variables después.

## Integridad y reproducción

`python tools/l2_public_pilot.py --raw /ruta/BTC_1min.csv --out /ruta/resultados`

- Código SHA-256: `1f50f5b11604a1b5001d93d3537174aaffbac88fa07b8d562a8dff08caad9a5b`; no es worktree de git: script aislado con hash, sin fingir árbol limpio.
- HEAD remoto antes/después del cálculo: `632dedd316d246cb43545ea8b758b6a866c655ac` / `632dedd316d246cb43545ea8b758b6a866c655ac`.
- Python 3.13.14; pandas 3.0.6; numpy 2.5.3.
- Controles: recuento independiente con `csv`; MSE por suma independiente; fixture de no dependencia de filas futuras; frontera train/test verificada; reconciliación de filas.
- Artefacto numérico único: `artifacts/l2_public_pilot_20260929/evidence.json`. Features y predicciones completos conservados en sandbox, no versionados.

## MEDIDO / NO MEDIDO y próximos pasos

**MEDIDO:** esquema/calidad, extracción de dos proxies, asociación descriptiva y comparación temporal de un minuto en BTC. El piloto no encontró mejora agregada.

**NO MEDIDO:** absorción real, agotamiento en A/B, rupturas de señales de espejo, camino hacia B, fills, prioridad de cola, costos/latencia y transferencia a NQ/ES. Fotos por nivel móvil no reconstruyen colas a precios fijos ni identifican cancelación frente a ejecución dentro del minuto.

Pendientes:
- bajar una muestra de 1 s (también agregada) para factibilidad temporal; no extrapolar este resultado;
- auditar código generador y convención de flujos antes de llamarlos delta/OFI;
- solicitar raw L2 y trades NQ del mismo stream, con timestamps/source_row, de sesiones de desarrollo expresamente autorizadas;
- aplicar R01/R05 como extensión de EXEC-QI a instantes de señal; R02/R03 requieren mensajes finos y controles emparejados;
- Optiver y libro de diez niveles quedan pendientes; no se probaron en este piloto.

## Investigación documental

- `MANIFIESTO_EJECUCION_QI_L2_20260924.md` §10 ya mide políticas sobre grilla uniforme; lo nuevo pendiente es en señales y validación de ejecución.
- https://arxiv.org/abs/1011.6402 — relación entre OFI, profundidad y cambios contemporáneos en acciones; no se replicó aquí su OFI.
- https://arxiv.org/abs/1512.03492 — QI y siguiente movimiento de midprice en acciones; no se replicó aquí su clasificación.
- Herramienta `research` no disponible en sesión; se usaron web_search/web_load_page, Kaggle MCP y GitHub MCP.

## Aporte al referente

Las cinco opciones quedan trazables y pendientes, y el primer ensayo registra también el resultado negativo sin convertir proxies de flujo en rentabilidad ni consumir confirmación.
