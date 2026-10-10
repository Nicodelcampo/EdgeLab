# PUENTE — del CerebroSSRN al ecosistema VectorBT (ES)

Este es el archivo que cierra el circuito: no un grafo que se admira a sí
mismo, sino el cruce entre lo que el corpus sabe y lo que el ecosistema real
del usuario (`C:\$AVectorBTecosistema`) ya tiene y ya midió. Se regenera
corriendo `pipeline/prepare_anchor_context.py` + editando este archivo cuando
entra un análisis nuevo o más papers.

## Estado del ecosistema al 2026-07-13 (contra qué se cruza)

- **Datos disponibles**: velas ES M1 (`es_m1_candles.parquet`), ticks L1
  (`es_full_ticks.parquet`, ~480MB), zonas HFT del indicador
  HFTZonesESPureV22 (`ES_zones.csv` → logger `hft_zones`). **NO hay L2/L3**
  (profundidad por nivel, cola de órdenes) — brecha central a declarar en
  cada recomendación.
- **Logger `hft_zones`**: zonas de 1 tick de grosor, `direction` ±1
  (soporte/resistencia), `bucket` (Absorb/Predator/Ultra), `vol_rate`,
  `pasos`, `total_vol`, `touch_ms_list`. Regla de mitigación canónica:
  `strict_touch` (penetración estricta de 1 tick).
- **Último estudio** (`runs/excursion_study/20260712_201602`): fuerza bruta
  de la familia "rebote" sobre 7.351 zonas. Resultado: el rebote genérico en
  zonas Absorb **colapsó OOS**; lo único robusto IS+OOS (243/35.280 combos)
  fue **`vol_rate` en el decil superior (≥20.870) + bucket Predator + TP/SL
  grandes (48/48)**. Advertencia viva: el split IS/OOS cae casi exacto sobre
  el roll 06-26→09-26, así que la degradación mezcla overfit con cambio de
  régimen.

## Uso 1 — Auditor anti-overfitting (prioridad máxima)

**Constelación del grafo**: comunidad [75] — backtest overfitting (22 docs),
walk-forward validation (12), look-ahead bias (9), data snooping (6),
out-of-sample testing, survivorship bias, false discovery rate, multiple
testing, deflated/probabilistic Sharpe ratio, model uncertainty.

**Qué dice el corpus que aplica YA a tu estudio de zonas**:
- El split IS/OOS 70/30 temporal simple es exactamente lo que la literatura
  de `backtest overfitting` marca como insuficiente cuando hay un cambio de
  régimen en el medio (tu roll). El corpus ofrece los reemplazos:
  **purged/combinatorial cross-validation** y **deflated Sharpe ratio**
  (penaliza el mejor de N pruebas — y vos probaste 67.500 combos, así que el
  mejor IS "a secas" es ruido casi garantizado, cosa que el propio docstring
  de `brute_excursions` ya intuía).
- `false discovery rate` / `multiple testing` (doc67 *The Statistical Limit
  of Arbitrage*, robustez alta): con miles de combos, controlar FDR
  (Benjamini-Hochberg) es la diferencia entre un edge y un falso positivo.

**Próximo experimento concreto**: agregar a `brute_excursions.py` un paso
final que, sobre los N combos que pasan el filtro IS, compute el **deflated
Sharpe ratio** (o al menos el haircut de Bonferroni/BH sobre el t-stat de la
expectancy) usando N = número de combos probados. Un combo cuyo edge no
sobrevive el ajuste por multiplicidad se descarta aunque su OOS se vea lindo.
Esto ataca la duda central del reporte del 12-jul sin datos nuevos.

**➤ EJECUTADO (EXP-001, 2026-07-13 — ver LEDGER_EXPERIMENTOS.md).**
`scripts/deflated_audit.py` corrió esto. Resultado: **el cluster robusto era
ruido**. Mejor Sharpe por-trade de los 35.280 combos = 0.656, por DEBAJO del
haircut de multiplicidad SR0 = 0.796; 0 combos superan DSR>0.95; el cluster
Predator/vol_rate-decil-superior tiene DSR máximo 0.000. **No construir sobre
el rebote genérico en zonas Absorb/Predator — está refutado.** El auditor pasa
a ser paso obligatorio de toda corrida de grilla/Optuna.

## Uso 2 — Fábrica de features de order flow

**Constelación**: comunidad [78] — order flow imbalance (7 docs), market
impact (16), Kyle lambda (3), mid-price, microprice (2), trade sign, VPIN,
tick data. Más [17] — Hawkes process, branching ratio, time-of-day
conditioning.

**Construibles sobre tus ticks L1 (sin necesitar L2)**:
- **Order flow imbalance / trade-sign imbalance**: con Lee-Ready o tick-rule
  sobre los ticks, sin libro. Predictor de retorno de corto plazo replicado
  en múltiples papers (doc17, doc78 y otros).
- **Kyle's lambda**: impacto de precio por unidad de flujo firmado —
  regresión rodante de Δprecio contra flujo neto. Una medida de cuán "frágil"
  está la liquidez alrededor de una zona.
- **Intensidad de Hawkes / branching ratio** (comunidad [17], doc208
  robustez alta: relación ley-de-potencia entre intensidad de llegada
  in-spread y ancho del spread): un feature de "cuán auto-excitado/clusterizado
  está el flujo ahora mismo" — candidato natural para condicionar la calidad
  de una zona en el momento del toque.

**Brecha honesta**: microprice y queue position "puros" necesitan L2/L3 que
no tenés. Sus versiones L1-aproximadas son más ruidosas — testear, no asumir.

**Próximo experimento**: agregar al logger o a un pre-proceso Python una
columna de **OFI acumulado en la ventana previa al toque de zona** y meterla
como eje nuevo en la grilla de `brute_excursions` (junto a `vol_rate`, que ya
demostró importar). Hipótesis falsable: los toques con OFI alineado al rebote
tienen expectancy OOS mayor que los del decil superior de vol_rate solo.

## Uso 3 — Meta-labeling de las zonas HFT (mayor relación esfuerzo/retorno)

**Constelación**: comunidad [16] — random forest, XGBoost, feature
importance, Shapley values, AutoML; cruce con triple-barrier/meta-labeling
(López de Prado, en la cola larga del grafo).

**La idea**: en vez de buscar una señal nueva, usás **el toque de zona como
evento primario** (lo que ya tenés) y entrenás un **modelo secundario** que
decide cuáles tomar. Las features: `bucket`, `vol_rate`, `pasos`, excursión
previa, OFI del Uso 2, hora del día (Uso 4). El label: triple-barrier
(TP/SL/tiempo) — que es *exactamente* la mecánica que `brute_excursions` ya
simula.

**Por qué encaja**: tu estudio ya mostró que el edge es condicional
(`vol_rate` decil superior). Un meta-modelo generaliza esa condicionalidad a
un espacio de features en vez de una grilla de cortes duros, y `feature
importance`/Shapley te dice *qué* de la zona predice el rebote.

**Próximo experimento**: exportar de `brute_excursions` la tabla
evento×outcome (ya la computa internamente: `build_touch_events` +
`simulate_outcomes`) con las features de zona, y entrenar un XGBoost
meta-labeler con purged CV (Uso 1). Comparar su expectancy OOS contra el
mejor combo de grilla fija. Es la síntesis de los usos 1+2+3.

## Uso 4 — Variables de condicionamiento

**Constelación**: [17] time-of-day conditioning, intraday seasonality (8
docs, comunidad [74]); regime switching (8) y hidden Markov model (6) en [75].

El corpus repite que el edge intradía es condicional a **hora del día**
(aperturas/cierres vs. sesión ilíquida) y **régimen de volatilidad**. Tu
grilla ya condiciona por `vol_rate` de la zona; falta condicionar por
**estado del mercado en el momento del toque** (hora, vol realizada rodante,
régimen HMM).

**Próximo experimento**: agregar `hora_del_toque` y `vol_realizada_rodante`
como ejes/filtros. Barato y con soporte empírico fuerte y replicado.

## Uso 5 — Realismo de costos e impacto

**Constelación**: comunidad [78]/[49] — market impact, square-root law,
Almgren-Chriss, transaction costs (29 docs), slippage, effective spread.
Hallazgo transversal fuerte (doc61 robustez alta): *el pairs trading clásico
deja de ser rentable una vez incluidos todos los costos*.

`brute_excursions` hoy asume entrada limit en el precio de penetración y
supuestos conservadores de fill, pero **no modela impacto/slippage variable**.
Para un rebote de 1 tick de penetración en el ES, el spread y el slippage se
comen una fracción no trivial de un TP de 8-16 ticks.

**Próximo experimento**: parametrizar un costo por trade (spread efectivo +
slippage) en la simulación de outcomes y re-rankear. Los combos de TP chico
(8-12) probablemente se caen; los de TP 48 (que sobrevivieron OOS) aguantan
mejor — confirmando por otra vía que el edge robusto está en targets grandes.

---

## Cómo el cerebro usa este puente

Cuando la consulta toca el ecosistema, el orden es: (1) leer este puente,
(2) recuperar hallazgos y pasajes con `consultar.py`, (3) cruzar contra el
último `runs/excursion_study`, (4) proponer el **próximo experimento** como
un cambio concreto a un script de `quantlab`/`scripts`, nunca como idea
genérica. La regla de oro: no proponer como novedad algo que el estudio del
12-jul ya refutó, y siempre declarar la brecha de datos (L1 vs L2/L3).
