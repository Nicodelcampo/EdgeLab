# Pre-registro — HFT-CLUSTERS-INFO: E0 sin retornos y una hipótesis de información

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-11-10.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `HFT_CLUSTERS_INFO`. Etapas: **E0 target-free** y **EF2/EF3 información** (no es P&L de una estrategia).
Origen: `DICTAMEN_ABOGADO_20261110.md`. Código: `edgelab/research/hft_clusters_info.py`, `tools/kaggle_grilla/hft_clusters_info_main.py`,
`tools/hft_clusters_info.py`, tests `tests/research/test_hft_clusters_info.py`.

## 1. Población (enumerada antes de congelarla)
Alrededor de un cluster de zonas HFT: (a) creación; (b) alejamiento; (c) **primer toque del borde cercano tras alejarse**; (d) toque
n-ésimo; (e) atravesada (ruptura); (f) expiración; (g) estado continuo «precio dentro/cerca de un cluster vivo». Se mide **(c)**: es
la entrada que proponía U1 y la única con hipótesis económica escrita (defensa del nivel). (e) y (g) quedan NO MEDIDOS; (g) tendría
más potencia y es la siguiente si (c) no tiene muestra. Un evento por cluster.

## 2. Paso E0 (sin retornos)
- Activos: NQ, ES, YM, GC (futuros del release, sólo horario regular). Ventana DESC 2025-07-01 → 2026-03-31.
- Zonas: `Z_CERT` (25 ms, volumen 50, con absorción: la certificada en NT8) y `Z_VOL10`. Clusters: familia P, K = 4, packing
  {0,85; 1,25}, vida de zona {300; 900} s. Vida del cluster 1.800 s. **8 definiciones por activo.**
- Reloj en segundos; sesión CME (`trade_date`); geometría congelada al detectar; escala de volatilidad de la barra anterior.
- Los umbrales del detector de zonas están en ticks y contratos calibrados para NQ: el E0 dice si en ES, YM y GC dan algo comparable.
- **Regla mecánica de elección (una definición por activo):** elegibles = al menos 0,5 clusters por sesión y CV ≤ 0,5 de la media
  mensual; entre ellas, la más cercana a 2 clusters por sesión. Sin elegibles, el activo no pasa al paso 3.
- Salida: clusters por sesión, ancho mediano, fracción de clusters más angostos que X, fricción en R si el stop fuera el ancho.

## 3. Paso INFO (una hipótesis)
- **Evento:** tras detectarse el cluster, el precio se aleja al menos X/2 de su rango y vuelve a tocar el borde cercano dentro de
  1.800 s. Sólo ticks posteriores a `t_ns`.
- **Desenlace:** carrera simétrica desde el borde: +1 si llega antes a +X en el sentido del rebote, −1 si llega antes a −X, 0 si
  ninguna en 3.600 s. X = fricción canónica / 0,08 redondeada al tick: NQ 19,5; ES 11,25; YM 64; GC 7,6 puntos.
- **Placebo:** mismo cluster (hora y ancho) con el nivel corrido ±1,5X y ±3X, mismo procedimiento.
- **Estadístico:** diferencia (real − placebo) del desenlace medio, bootstrap por sesión (20.000), p unilateral; por activo y
  combinado por Stouffer. Es **bruto** (sin costos): una carrera ganada vale +X y una perdida −X; con desenlace medio m, el neto
  sería (m·X − fricción)/X = m − 0,08 R, así que para ser operable hace falta m real > 0,08 además de superar al placebo.
- **Pruebas:** 1 hipótesis × 4 activos + 1 combinada = **5** (registro global `hft_clusters_info/info`). Linaje `HFT_CLUSTERS_INFO` ←
  `PRERANGE_HFT_NQ`, `PRERANGE_HFT_ES`, `ATLAS_BARRERAS_HFT_R` (zonas HFT ya medidas).
- **Decisión:** pasa a réplica (abr → sep 2026, una vez, mismo código, nivel LORD++) si Stouffer p < 0,05 **y** desenlace medio real
  > 0,08 en el conjunto. Si pasa la réplica, recién ahí se pre-registra un P&L con ejecución fija y stop = max(ancho + 2 ticks por
  lado, X). Si no pasa con MDE < 0,10: `NO_REPETIR`. Si no pasa por falta de eventos: se mide el estado continuo (g).
- Holdout (sesión CME 2026-10-01 en adelante): no se toca.

## 4. Justificación económica
Si varias ráfagas de ejecución rápida se apilan en el mismo rango en pocos minutos, alguien ejecutó tamaño ahí; la hipótesis es que
ese nivel se defiende en el primer regreso. El placebo separa «nivel con memoria» de «cualquier nivel a esa hora y con esa volatilidad».

## 5. Cómo podría refutarse
Diferencia real − placebo ≤ 0 con potencia; o diferencia positiva pero desenlace real ≤ 0,08 (no paga la fricción ni con stop
grande); o efecto en un solo activo que no replica.

## 6. Riesgos declarados
- Los parámetros visuales del indicador (frecuencia por sesión, percentiles, expansiones) se ajustaron mirando gráficos del 8-nov
  (período de holdout, sin P&L). Por eso acá NO se usan: sólo familia P con umbrales geométricos fijos.
- Sin paridad contra oráculo de NinjaTrader para los clusters (sí para el detector de zonas). Resultado provisional hasta tenerla.
- 9 meses de DESC: pocos eventos por activo; por eso se combinan 4 activos con la misma regla.

## 7. Enmienda (2026-11-10, antes de tener ningún resultado): segunda hipótesis, el cluster como IMÁN / objetivo
Pedido de Nico. El rebote (§3) mide qué pasa DESPUÉS del toque; no dice nada sobre si el precio LLEGA al cluster más que a otro nivel.
Un nivel puede atraer y dejar pasar (buen objetivo, mala entrada) o al revés. Se mide aparte, con el mismo almacén y la misma elección
mecánica del E0. Población: ítem (b) «alejamiento» de §1.
- **Evento:** el precio se aleja al menos X/2 del rango del cluster dentro de 1.800 s; en ese punto está a distancia d del borde cercano.
- **Desenlace:** +1 si vuelve a tocar el borde antes de alejarse otra d (nivel espejo); −1 si llega antes al espejo; 0 si ninguna en
  3.600 s. Bajo paseo al azar es 50/50.
- **Control (placebo temporal):** pseudo-clusters del mismo ancho, en la misma sesión, centrados en el precio que había 20 y 40 minutos
  antes y después, a más de 10 minutos de todo cluster real, con el MISMO procedimiento. Así el control tiene la misma condición que
  el real (parte del nivel y se aleja X/2); es la lección de BigTrap2, donde la carrera contra el espejo era positiva y un control sin
  zona con la misma geometría daba casi lo mismo.
- **Estadístico y decisión:** diferencia real − control del desenlace medio, bootstrap por sesión, Stouffer entre activos; pasa a
  réplica con p < 0,05. Es información sobre dónde poner un objetivo, **no un sistema**: sólo sirve para mejorar una regla que ya
  tenga entrada, y eso se pre-registra aparte.
- **Pruebas:** 4 activos + 1 combinada = **5** más (`hft_clusters_info/iman`). Total de la familia: 10.
- **Refutación:** diferencia ≤ 0 con MDE < 0,10 → el cluster no atrae más que cualquier nivel con la misma geometría.
