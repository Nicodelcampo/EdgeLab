# LITCHECK-SSRN-20261009 — el cerebro elige qué contrastar y Kaggle lo mide

**Estado:** `PRE_REGISTERED_EXPLORATORY` (hipótesis, métricas y reglas fijadas en
`notebooks/kaggle/litcheck_ssrn_20261009.py` antes de leer datos). **Tipo:** exploratorio/descriptivo: no promueve ni
descarta estrategias; un resultado `CONSISTENT_EXPLORATORY` solo motiva una campaña confirmatoria aprobada por Nico.

## 1. Qué consultó el cerebro

`EdgeBrainMemory.propose_tests(...)` (`edgelab/edge_brain/literature_planner.py`) con estas consultas:

- desbalance del flujo de órdenes predice retorno de corto plazo
- volumen y número de operaciones explican la volatilidad intradía
- estacionalidad intradía de volumen y volatilidad
- momentum intradía y reversión en futuros de índices
- agresor comprador vendedor continuidad del flujo de órdenes
- impacto de precio de las operaciones
- spread bid-ask efectivo y costos de ejecución en futuros
- agrupamiento de volumen en horas redondas

El planificador descarta hallazgos que piden datos que no tenemos (L2 de varios niveles, mensajes de órdenes,
tamaños L1, opciones, sección cruzada de acciones, eventos puntuales, identificación de participantes, otros mercados)
y ordena por relevancia × transferibilidad a futuros CME. Salida (top 12):

| # | Hallazgo | Paper | Prioridad | Transfer. | Necesita | Afirmación |
|---:|---|---|---:|---:|---|---|
| 1 | `CLAIM-SSRN-FINDING-0439` | `SRC-SSRN-0174` | 0.605 | 0.55 | TRADES, AGGRESSOR, INTRADAY_CLOCK | Existe una marcada monotonicidad en el aumento del volumen y cantidad de operaciones al acercarse a las marcas… |
| 2 | `CLAIM-SSRN-FINDING-0472` | `SRC-SSRN-0193` | 0.5616 | 0.85 | AGGRESSOR, INTRADAY_CLOCK | Los factorial moments de orden 2 (F_2) del contrato de futuro del Euro son iguales a 1 para resoluciones tempo… |
| 3 | `CLAIM-SSRN-FINDING-0440` | `SRC-SSRN-0174` | 0.5034 | 0.55 | TRADES, INTRADAY_CLOCK | La concentración de volumen en intervalos regulares no mejora la liquidez, sino que empeora el impacto en el p… |
| 4 | `CLAIM-SSRN-FINDING-0338` | `SRC-SSRN-0127` | 0.4299 | 0.5 | TRADES, INTRADAY_CLOCK | El Price Jerk Indicator (tercera derivada del precio) logra AUC-ROC de 0.534 frente a 0.512 del RSI-14 como ba… |
| 5 | `CLAIM-SSRN-FINDING-0340` | `SRC-SSRN-0127` | 0.4277 | 0.5 | INTRADAY_CLOCK | La degradación walk-forward de win rate es de 4.7 puntos porcentuales (26.9% in-sample vs 22.2% out-of-sample)… |
| 6 | `CLAIM-SSRN-FINDING-0210` | `SRC-SSRN-0066` | 0.4156 | 0.5 | AGGRESSOR, INTRADAY_CLOCK | La duración promedio del régimen de acumulación agresiva (s2) es de ~4.3 minutos, superior a los ~2.5 minutos … |
| 7 | `CLAIM-SSRN-FINDING-0200` | `SRC-SSRN-0063` | 0.3818 | 0.5 | TRADES, AGGRESSOR | El volume order imbalance es un predictor significativo de movimientos de precio de corto plazo. Las estimacio… |
| 8 | `CLAIM-SSRN-FINDING-0635` | `SRC-SSRN-0279` | 0.3641 | 0.7 | TRADES, INTRADAY_CLOCK | Estrategia intraday sobre GS y JPM (17 oct 2011) genera P&L de $1,348 con gamma=0.1 en un dia de trading compl… |
| 9 | `CLAIM-SSRN-FINDING-0717` | `SRC-SSRN-0338` | 0.3615 | 0.7 | TRADES, INTRADAY_CLOCK | La volatilidad de retornos de bonos es significativamente mayor en días en que la Fed implementa solo OMOs ove… |
| 10 | `CLAIM-SSRN-FINDING-0107` | `SRC-SSRN-0035` | 0.3422 | 0.7 | TRADES | Entre los 42 pares de FX estudiados con WFO de 36 meses, existe enorme heterogeneidad de desempeño y frecuenci… |
| 11 | `CLAIM-SSRN-FINDING-0075` | `SRC-SSRN-0026` | 0.3406 | 0.5 | TRADES, AGGRESSOR | El modelo estocástico calibrado reproduce con precisión la volatilidad realizada diaria observada en datos rea… |
| 12 | `CLAIM-SSRN-FINDING-0279` | `SRC-SSRN-0096` | 0.3293 | 0.5 | TRADES | A pesar de los picos de volumen y volatilidad, los costos de trading y la liquidez (bid-ask spread y lambda de… |

## 2. Qué se contrasta (5 hallazgos medibles con trades + agresor + reloj)

| H | Hallazgo | Por qué | Métrica primaria |
|---|---|---|---|
| H1 | `CLAIM-SSRN-FINDING-0439` (SRC-0174) | #1 del planificador; si existe, afecta ejecución y elección de horarios | exceso log de volumen/trades en ventanas de 30 s en :00/:30/:10/:05 vs vecinas |
| H2 | `CLAIM-SSRN-FINDING-0440` (SRC-0174) | mismo paper: ¿operar en marcas cuesta más? | λ de Kyle en marcas / λ en vecinas |
| H3 | `CLAIM-SSRN-FINDING-0168` (SRC-0051) | base de cualquier señal de order flow | P(compra\|compra), P(venta\|venta) por orden (barrido = una orden) |
| H4 | `CLAIM-SSRN-FINDING-0609` (SRC-0265) | qué explica la volatilidad intradía (n.º de trades vs tamaño) | OLS de \|Δp\| 5 min con efectos fijos de sesión y franja |
| H5 | `CLAIM-SSRN-FINDING-0200` (SRC-0063) | ¿el desbalance de volumen predice el minuto siguiente? | corr(OI_t, Δp_t+1) agrupada |

0609 menciona además la pendiente del libro (L2): solo se contrasta la parte de trades vs tamaño.
Reglas de veredicto exactas: docstring del script. 10 pruebas (5 × ES/NQ), IC bootstrap por sesión al 99,5 %
(Bonferroni 0,05/10), 2000 réplicas, semilla 20261009.

## 3. Datos (guía de Kaggle `nicolasbuttaro/edgelab-data-catalog`)

- Entrada única `edgelab_data.py` + `RESOLVER.json`: una fuente por sesión, serie líder, solo sesiones aprobadas.
- ES y NQ, sesiones aprobadas **2025-07-01 → 2026-06-30** (ES 188, NQ 220): pre-holdout también bajo la definición
  vieja (2026-07-01); HOLDOUT-A1 (desde 2026-10-01) no se toca. Partición `EXPLORATION`.
- Datasets: `edgelab-data-catalog`, `edgelab-nt8-historical-missing-20261001`, `edgelab-ticks-nt8-reexport-20261005`,
  `edgelab-ticks-nq-preholdout` (lista de `required_files`). Kernel privado, sin internet.

## 4. Evidencia y cierre del ciclo

La corrida emite `results.json`, `execution_attestation.json` (commit esperado, sha del script, sha de cada input,
sesiones máximas leídas, `holdout_touched`, `pnl_computed=false`), `artifact_manifest.json` y `output.zip` + sha256.
Después: observaciones `DESCRIPTIVE` en el hipocampo sobre la partición EXPLORATION → `record_claim_test`
(`PROPOSED`) por hallazgo → **adjudicación de Nico** (`adjudicate_claim_test`, `human:` ≠ quien registra).
