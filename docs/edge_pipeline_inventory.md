# Inventario de piezas reutilizables para el pipeline de descubrimiento

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md).
> FASE 3a — **solo lectura**. Ningún módulo listado fue modificado. Ninguna
> decisión de "cuál usar" está tomada acá (eso es diseño, no inventario).
> Metodología: inspección directa de código + `grep` + intento de `import` en
> el `.venv` actual. Todo lo marcado "funcional" significa **importa sin error
> y su lógica interna se leyó completa**; NO significa "verificado numéricamente
> contra un caso conocido" (eso no se hizo en este turno, read-only).

## Resumen ejecutivo

EdgeLab (fuera del bridge) ya tiene un pipeline de auditoría de estrategias
**sofisticado y sustancialmente completo** en `validation/` + `edgelab/audit.py`
+ `edgelab/engine.py`, con **cero cobertura de tests en este repo** (`grep` no
encontró ninguna referencia a estos módulos desde `tests/`). Es reutilizable
para las piezas **estadísticas** (MCPT, PBO, DSR) casi sin cambios. La pieza de
**ejecución** (`edgelab/engine.py` + `harness.py`) está acoplada a un contrato
de señal a nivel de TICK crudo (`signal_fn(times_ms, last, bid, ask) -> idx,
dirs`) que **no coincide** con la política G0 del bridge (features as-of a
nivel de BARRA, ejecución en el open de la barra siguiente) — es un desajuste
arquitectónico real, no un detalle menor.

## Tabla por componente

| Componente | Ruta | Estado | Tests que lo cubren | Reutilizable |
|---|---|---|---|---|
| Simulador de ejecución | `edgelab/engine.py` (105 líneas) | Funcional (`import` OK, numba instalado) | **ninguno** | **Con adaptación** — ver nota 1 |
| Modelo de costos | disperso: `FEES_RT=0.5` en `engine.py`; `COST_RT` ad-hoc en `strategies/noise_area.py`, `orb_tickfill.py` | Funcional pero **no desglosado** (comisión/exchange/NFA/spread/slippage separados, con escenarios) | ninguno | **No reutilizable tal cual** — ver nota 2 |
| MCPT | `validation/mcpt.py` (`mcpt()`, 73 líneas) | Funcional (`import` OK) | ninguno | **Con adaptación** — ver nota 3 |
| PBO / CSCV | `validation/pbo.py` (`pbo_cscv(R, S=10)`, 45 líneas) | Funcional (`import` OK) | ninguno | **Casi tal cual** — ver nota 4 |
| DSR (Deflated Sharpe) | `edgelab/audit.py` (`deflated_sharpe`, `sr0_haircut`, `trade_stats`) | Funcional (`import` OK) | ninguno | **Tal cual** |
| Corrección múltiples pruebas | `edgelab/audit.py` (`benjamini_hochberg`) | Funcional (`import` OK) | ninguno | **Tal cual** |
| SPA (Hansen) | `validation/spa.py` (`spa_pvalue`) | **Degradado**: `import` OK pero requiere el paquete `arch` (NO instalado en este `.venv`; fallback silencioso a `NaN`) | ninguno | Con instalar `arch` (extra `research-vectorbt`) |
| Walk-forward | — | **No existe como función reutilizable.** Único hallazgo: un comentario `# GRID SEARCH (sobre datos completos + walk-forward)` en `validation/vectorbt_eurusd_deep.py`, sin implementación extraíble | — | No — hay que construirlo |
| Reporting reproducible | `validation/gauntlet.py::report()` | Imprime a stdout + devuelve un `dict` en memoria (incluye DataFrames). **No serializa** a archivo, no tiene `campaign_id`/`strategy_id`, no hashea nada | ninguno | No — hay que construirlo (usar el patrón manifest+digest de `edgelab/bridge/store.py` como modelo) |
| Ad-hoc CSV exports | `validation/vectorbt_eurusd_opt.py`, `validation/engine_validator.py` | Funcional pero rutas hardcodeadas, un-off | ninguno | No — no es un sistema, son scripts sueltos |
| Definición de estrategias (contrato) | `CONTRATO_LLM.md` + `validation/harness.py::full_audit` (120 líneas) | Funcional (`import` OK), **conceptualmente muy alineado con G0** (causalidad forzada por el motor, batería anti-bugs mecánica) pero con el contrato de señal a nivel de TICK crudo | ninguno | **Con adaptación** — ver nota 1 |

## Notas de integración (observaciones, no decisiones)

**Nota 1 — desajuste tick vs bar-as-of.** `edgelab/engine.py`/`harness.py`
esperan `signal_fn(times_ms, last, bid, ask) -> (idx, dirs)`: el motor entra
en el **tick siguiente** al índice de la señal. La política G0 sellada en
`edge_validation_contract.md` dice ejecución al **open de la BARRA siguiente**
tras `available_at` (cierre de barra). Son políticas de causalidad distintas
(tick-siguiente vs barra-siguiente) — no intercambiables sin decidir cuál rige
para el research de zonas. La batería anti-bugs de `harness.py` (synthetic /
mirror / prefix / ledger checks) es conceptualmente valiosa y candidata a
adaptarse al pipeline bar-as-of, pero tal como está opera sobre arrays de tick
crudo, no sobre `materialize_features`.

**Nota 2 — costos no desglosados.** `FEES_RT = 0.5` (ticks round-trip, motor
compartido) y los `COST_RT` de las estrategias legacy son **constantes únicas**
(spread ya pagado por el fill bid/ask del motor + una comisión fija). El
contrato `edge_validation_contract.md` §G3 pide componentes **separados**
(comisión broker, exchange/clearing, NFA, spread, slippage) con **4 escenarios**
(ideal/base/adverso/severo). Ningún módulo existente separa estos componentes
ni corre escenarios — habría que construirlo, aunque la mecánica de "una sola
fórmula de PnL en un solo lugar" de `engine.py` es un principio de diseño
directamente reutilizable.

**Nota 3 — MCPT acoplado a formato RTH ES/NQ.** `mcpt.mcpt(stat_fn, O, H, L, C,
V, ...)` recibe matrices **día × minuto** en el formato que produce
`edgelab/sessions.py::rth_matrices` (RTH 09:30-16:00 ET, ES/NQ). El **método**
de permutación (por sesión, preservando OHLC intrabar, un shuffle por día)
coincide exactamente con lo que `edge_validation_contract.md` §G2 exige para
MCPT — es el algoritmo correcto, pero la forma de entrada no calza con datos de
6E ni con el formato de barras del bridge (`edgelab/bridge/bars.py`,
`BarSeries`). Adaptación = cambiar la fuente de datos, no el algoritmo.

**Nota 4 — PBO casi directamente reutilizable.** `pbo_cscv(R, S=10)` recibe
una matriz genérica `(n_unidades_temporales × n_combos)` de PnL — sin
acoplamiento a ES/NQ ni a ningún formato de barra específico. `S=10` por
default; `edge_validation_contract.md` pide `S=8` — es un parámetro de llamada,
no un cambio de código.

## Qué NO se debe duplicar

Si se decide reutilizar (decisión pendiente, no tomada acá): **NO** reescribir
`deflated_sharpe`/`sr0_haircut`/`benjamini_hochberg` (ya son genéricos y
correctos), **NO** reescribir `pbo_cscv` (genérico, casi listo), **NO**
reescribir el algoritmo de permutación por sesión de MCPT (correcto, solo
cambia la fuente de datos). Si se decide NO reutilizar el motor de ejecución
tick-level (`engine.py`) por el desajuste de Nota 1, eso es una decisión de
diseño explícita a tomar con Nico — no una obviedad técnica.

## Extra opcional `research-vectorbt`

`requirements/full-research.lock` instalaría `vectorbt==1.1.0`, `arch==8.0.0`
(destraba `spa.py`), `statsmodels==0.14.6`, `scipy==1.18.0`, `numba==0.66.0`
(ya presente en el lock base). No instalado en este `.venv`. Los punteros de
`config.py` a rutas externas (`vectorbt_ecosystem_root` →
`C:/ProyectosQuant/VectorBTecosistema`, `cerebro_root` →
`C:/ProyectosQuant/CerebroSSRN`, ambos en `config/local.toml`) **no existen en
esta máquina** (confirmado: ambas rutas ausentes) — son remanentes de la
migración desde la máquina original; ningún módulo de `validation/`/
`strategies/` importa código directamente desde esas rutas (solo son variables
de config sin uso activo detectado en estos scripts).
