# Contrato de "edge válido y aplicable" — gates G0–G5

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md)
> (sha256 `21bb3b01a33e2b37…`). Los gates de este contrato se declaran ANTES de
> ver resultados y NO se relajan después. Cambiarlos exige una enmienda
> versionada aprobada por Nico ANTES de correr la campaña afectada.

## 0. Definiciones

- **Gate duro**: si falla, la promoción se BLOQUEA. Sin excepciones ex-post.
- **Gate blando (WARN)**: no bloquea por sí solo, pero exige revisión explícita
  y registrada de Nico antes de promover. Nunca se resuelve en silencio.
- **Candidato**: (estrategia, config de zonas, bar_spec, grilla de params de
  estrategia) dentro de una campaña pre-registrada. Toda variante corrida se
  **cobra al presupuesto de hipótesis** de su campaña, se promueva o no.
- **Cadena de estados**: ver `NORTH_STAR.md`. Cada gate promueve al estado
  siguiente; un FAIL registra `failed` (no se borra, no se re-corre con gates
  relajados).

Mapa gates → estados:

| Gate | Estado que otorga |
|---|---|
| G0 | `technically_valid` |
| G1 | `exploratory_candidate` |
| G2 | `statistically_supported` |
| G3 | `economically_viable` |
| G4 | `holdout_confirmed` |
| G5 | `paper_validated` → `live_candidate` |

Reglas de promoción (duras):
- **`EDGES_DISCOVERED.md` exige ≥ `statistically_supported` (G2) y
  `parity_exact` PROPIO de la config ganadora** (si ganó con `parity_covered`,
  se exporta un oráculo NT8 ad-hoc de esa config exacta y se pasa P2 antes de
  promover).
- **`LIVE_CANDIDATES` exige ≥ `paper_validated` (G5)**.
- Un resultado negativo se registra en el índice de campañas con su evidencia.
  Prohibido: relajar gates, reabrir el holdout, o "reintentar" la misma
  hipótesis sin nueva campaña (que hereda el presupuesto acumulado).

## G0 — Integridad técnica (duro, condición necesaria jamás suficiente)

1. **Lineage completo**: cadena `dataset_id → config_id → run_id →
   campaign_id → strategy_id` registrada y reproducible; particiones del store
   inmutables con digests verificados (P3).
2. **Features as-of**: toda feature se materializa point-in-time
   (`materialize_features`); en la barra `t` solo se ve `created_ms <= t`.
   Cero look-ahead estructural (nada depende de `len(bars)` ni del futuro).
3. **Señales con `available_at`**: cada señal lleva `available_at` = cierre de
   la barra que la genera. **Política de ejecución pre-declarada**: la orden se
   ejecuta al **open de la barra siguiente** (o primer tick ejecutable
   posterior a `available_at`). Prohibido el fill en la misma barra de la señal.
4. **Política de fills** (descubrimiento): solo market / stop-market. Stops:
   fill = peor entre el nivel del stop y el open siguiente si hay hueco. Sin
   limit fills optimistas (un limit "tocado" NO es un fill).
5. **Identidad**: `config_id` + `bar_spec` externos e inmutables; `bar_spec`
   NUNCA es parámetro interno de un kernel (decisión sellada).
6. **Integridad del store**: consumo exploratorio exige `integrity_state =
   api_verified`; consumo formal (G2+) exige además `parity_covered` o
   `parity_exact` según la regla de promoción.
7. **Disponibilidad en tiempo real**: las features del candidato deben ser
   computables con el feed en vivo con su warmup declarado (p.ej. aVolCellPOI2
   exige ~35 sesiones de historia; se declara, no se descubre en live).
8. **Determinismo**: re-ejecutar la campaña con el mismo manifiesto produce
   los mismos digests (regla P3.3 extendida al pipeline de estrategias).

## G1 — Evidencia exploratoria (sin acceder JAMÁS al holdout)

Sobre el dataset de desarrollo pre-declarado en el manifiesto. Duros:

- **n_trades ≥ 100** en el agregado de desarrollo (menos = evidencia
  insuficiente, se registra `insufficient_n`, no FAIL estadístico).
- **Expectancy NETA base > 0** (modelo de costos §G3, escenario base) por trade.
- **Concentración**: P&L neto **sin los 5 mejores trades sigue > 0**.
- **Estabilidad**: ningún subperiodo (fold natural = contrato) aporta **> 80%**
  del P&L neto total.

Blandos (WARN): P&L neto sin top-10 ≤ 0; win-rate/payoff incoherentes con la
familia declarada; expectancy positiva en < 2/3 de los folds; distribución de
MAE/MFE sin margen frente al stop declarado. Se registran SIEMPRE: expectancy
bruta y neta (en ticks y USD/contrato), nº de trades, distribución de retornos
por trade (p5/p25/p50/p75/p95), top-1/5/10 concentración, MAE/MFE, y P&L por
subperiodo.

## G2 — Robustez estadística

> **Enmienda G2-A1 (2026-08-10), aprobada por Nico.** Auditoría adversarial
> encontró que el MCPT implementado no testeaba lo que este texto prometía —
> ver `docs/incidents/AMENDMENT_G2-A1_2026-08-10.md` para el detalle completo
> y la demostración. Los cambios están integrados en el texto que sigue, no
> en un addendum aparte, porque el texto anterior estaba objetivamente
> equivocado (ver §2 del incidente): mantenerlo habría sido preservar un
> error, no una decisión.

Aplicado a cada **ganador por familia** (la selección se hace con la métrica
primaria única del manifiesto; prohibido el metric-shopping). Duros:

- **Inferencia primaria de expectativa positiva**: bootstrap estacionario-t
  agrupado por sesión, `lower > 0` del intervalo de confianza (
  `g2_decision.PrimaryCI`, `method="stationary_bootstrap_t"`, `n_sessions ≥
  160`). Es la misma máquina de inferencia que usó H1
  (`edgelab.stats.cluster_estimand.studentized_stationary_interval`).
- **PBO ≤ 0.50** (`PBO_MAX`) vía CSCV (S = 8 particiones) sobre la matriz
  completa configs × tiempo de la campaña.
- **DSR ≥ 0.95** con nº de trials = **N_eff del manifiesto** (TODAS las
  variantes cobradas al presupuesto, incluidas las abandonadas), método de
  cómputo autorizado por hash (`g2.dsr_method_sha256()` en
  `AUTHORIZED_DSR_METHOD_SHA256S`).
- **Walk-forward por contrato**: para cada fold k (test = contrato k), se
  re-selecciona el ganador por familia usando SOLO contratos < k y se evalúa en
  k; el **agregado WF-OOS neto debe ser > 0**.
- **Sensibilidad paramétrica**: vecinos ±1 paso de grilla del ganador: la
  **mediana de sus expectancies netas > 0** (sin acantilados).

**Diagnóstico, no gate**: `temporal_concentration_test()` (`ex-mcpt`,
permutación por bloques de sesión) sigue disponible para preguntar DÓNDE se
concentró un resultado — información real, pero no una prueba de que la señal
informa, y un edge estable (el que G1 exige) da `p≈0,5` ahí por construcción.
Usarla como gate duro es exactamente el error que corrigió esta enmienda.

Blandos: signo consistente del WF en < 2/3 de folds; ganador aislado (menos de
la mitad de los vecinos positivos); SPA/White cuando el nº de familias lo
amerite. La corrección por múltiples hipótesis usa SIEMPRE el N_eff del
manifiesto; añadir variantes después de correr = nueva campaña.

### Implementación (2026-07-25, enmendada 2026-08-10)

`edgelab/research/g2.py` + `edgelab/research/g2_decision.py`, verificado en
`tests/research/test_g2.py` (28 tests) y `tests/research/test_g2_decision.py`
(6 tests).

Se construyó **antes** de tener ningún candidato positivo, a propósito: escribir
el test estadístico después de ver un resultado bueno invita a ajustarlo hasta
que lo apruebe. Los umbrales salen de esta sección, no del resultado. La
enmienda del 2026-08-10 se aprobó en la misma ventana, por el mismo motivo:
**ningún candidato había pasado G2 todavía** cuando se corrigió.

Cada prueba se verifica contra **datos sintéticos con verdad conocida**, en los
dos sentidos: sobre ruido puro debe rechazar, y sobre un efecto plantado debe
**aprobar**. Un gate que sólo sabe decir "no" no sirve para encontrar edges.

| función | verificación |
|---|---|
| `temporal_concentration_test` | ruido ⇒ p > 0.05 · efecto concentrado plantado ⇒ p ≤ 0.05 · **edge estable plantado ⇒ p > 0.30 (documenta por qué no es gate)** · determinista con la misma semilla · con una sola sesión devuelve p = 1 en vez de fingir significancia |
| `studentized_stationary_interval` (`PrimaryCI`) | sobre el mismo edge estable que `temporal_concentration_test` rechazaría, `lower > 0` — el fixture cruzado que fija la enmienda como regresión |
| `pbo_cscv` | ruido ⇒ mediana ≈ 0.5 sobre 30 matrices · ventaja real y estable ⇒ PBO ≤ 0.50 · genera las 70 particiones C(8,4) |
| `deflated_sharpe` | cae monótonamente al crecer N_eff · castiga cola izquierda gruesa |
| `walk_forward` | **no** evalúa el primer fold (sin historia previa) · re-selecciona sólo con folds anteriores, verificado con un config trampa que es el mejor únicamente en el último fold |
| `parameter_sensitivity` | detecta el pico aislado · acepta la meseta · sin vecinos devuelve `None`, no un valor inventado |

**Regla de composición:** `G2ValidationDecision.passed` exige `primary_ci.passed`
**y** los cuatro `gate_results` (`pbo`, `dsr`, `walk_forward`,
`parameter_sensitivity`) en verde. Es la **única** definición ejecutable de
"G2 aprobado" — la ruta paralela `g2.py::evaluar()` (vacua: sólo exigía
`DSR > 0`) se eliminó en la enmienda G2-A1.

**Trampa de escala, documentada porque casi me come:** el `sharpe` que consume
`deflated_sharpe` es **por observación**, no anualizado. Un SR/trade de 0.5 sobre
500 trades satura el DSR en ~1.0 — si alguien ve `DSR = 1.0` y lo celebra, el
problema está en la escala que le pasó, no en la estrategia. Valores realistas
por trade están en el orden de 0.02–0.1.

## G3 — Robustez económica

Modelo de costos **desglosado y pre-registrado** en el manifiesto (comisión
broker + exchange/clearing + NFA + spread + slippage, por lado y por contrato).
Cuatro escenarios:

| Escenario | Uso | Definición (por pata ejecutada) |
|---|---|---|
| ideal | SOLO diagnóstico | costos 0, slippage 0 — jamás para decidir |
| base | gate principal | costos plenos + slippage 1 tick en market/stop |
| adverso | resistencia | costos plenos + slippage 2 ticks (stops 2) |
| severo | estrés | costos plenos + slippage 3 ticks (stops 3) |

Duros: **neto base > 0**; **sin colapso en adverso**: expectancy neta en
adverso > **−0.5 × expectancy base** (colapso inmediato = FAIL). Se registran:
drawdown máximo neto (USD/contrato), turnover (trades/día), ganancia neta por
contrato-día, y una nota de capacidad (para 6E retail: informativa). Blandos:
adverso < 0; DD neto de desarrollo > USD 2.500 por contrato; expectancy neta
< 1 tick/trade (margen fino sobre el modelo de costos).

## G4 — Confirmación OOS (holdout sellado)

- Holdout: **2026-07-01 → 2026-12-31**. **Una sola apertura por candidato**,
  después de aprobar G3, con protocolo firmado antes de abrir.
  (Movido indebidamente a 2026-08-01 el 2026-08-01; revertido en INC-006. La
  frontera es un sello, no un cursor — regla 95.)
- Duros, pre-declarados: **PASS** = expectancy neta base > 0 en el holdout con
  n ≥ 30 trades y ≥ **50%** de la expectancy de desarrollo. **FAIL** = neta ≤ 0.
  **WARN** = neta > 0 pero < 50% de desarrollo o n < 30 (revisión de Nico).
- **Prohibido reoptimizar** sobre el holdout; el resultado (positivo o
  negativo) se registra y la apertura se anota en el log de accesos.

### Firewall del holdout (por código y por logs) — IMPLEMENTADO (FASE 3b)

- **Guard**: `edgelab/research/holdout_guard.py::check_holdout(start_utc,
  end_utc, *, purpose, caller, log_path=None)`. Toda función de carga de datos
  para research económico de estrategias debe llamarlo ANTES de tocar
  cualquier rango. `purpose` es obligatorio, sin default, uno de:
  - `"development"` — si el rango toca `HOLDOUT_START` (2026-07-01, única
    fuente de verdad en `holdout_guard.HOLDOUT_START_ISO`, citada de este
    documento y de `NORTH_STAR.md`) levanta `HoldoutViolation` (excepción
    dura) y registra el intento denegado en el log. Si el rango es enteramente
    anterior al holdout, permite sin loguear (no es un acceso al holdout).
  - `"target_free_validation"` — único uso permitido (paridad, determinismo,
    geometría, integridad, visor); SIEMPRE permitido, SIEMPRE logueado.
  - Fail-safe: `end_utc=None` (sin cota superior) se trata como "toca el
    holdout" — ante la duda, nunca se asume inocencia.
- **Log append-only**: `docs/holdout_access_log.md` (tabla markdown: timestamp
  UTC, purpose, outcome, ventana, caller). Se escribe siempre con `open(...,
  "a")`, nunca se reescribe ni se borra una fila — una corrección se agrega
  como fila nueva. Contiene la fila retroactiva del único acceso target-free
  real anterior a la existencia de este guard: la validación de paridad
  geométrica de Gaps2 (6E 09-26, ventana 2026-07-13→16, commit `0555e5d`).
- **Tests**: `tests/research/test_holdout_guard.py` (11 tests) — development
  pre-holdout OK sin log, development que pisa el holdout → excepción + log,
  target-free siempre permitido y logueado (incluso con ventana enteramente
  fuera del holdout), append-only verificado (múltiples llamadas solo agregan
  filas, ninguna se pierde), casos límite (borde exacto de `HOLDOUT_START`,
  rango sin cota superior).
- **Alcance declarado**: el guard hace cumplir el límite INFERIOR
  (`>= HOLDOUT_START`); no acota por el límite superior del rango cerrado
  (2026-12-31) — ver la nota de alcance en el docstring del módulo.
- Nota vigente: la partición de paridad de Gaps2 (6E 09-26, ventana
  2026-07-13→16) es un uso **target-free permitido** (paridad geométrica); sus
  datos NO pueden usarse para elegir dirección, thresholds ni candidatos.

## G5 — Aplicabilidad

- **Paper/shadow**: ≥ 20 sesiones o ≥ 30 señales (lo que ocurra después).
- **Paridad research↔live** (dura): ≥ 95% de las señales coinciden (mismo lado,
  timing dentro de 1 barra); slippage real observado ≤ escenario adverso.
- **Reglas completas pre-declaradas**: sizing (riesgo por trade ≤ 1% de la
  cuenta), límite diario (−3R → fin del día), **kill switch** (suspende si DD
  live > 1.5 × DD máx de desarrollo, o paridad research↔live < 90% durante 5
  sesiones); reactivación solo manual por Nico.
- **Despliegue con riesgo mínimo**: tamaño inicial 1 contrato / mínimo posible.

## Anti-gaming (transversal, duro)

1. Gates y métrica primaria definidos ANTES de ver resultados (este doc + el
   manifiesto, ambos hasheados).
2. Prohibido ampliar tolerancias, cambiar la métrica primaria o re-particionar
   folds después de ver resultados.
3. Todo lo corrido se cobra al presupuesto; los negativos se registran.
4. Cambios de semántica de validación → consulta previa con Nico, siempre.
