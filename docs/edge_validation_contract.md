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

## G2 — Robustez estadística (G2-A1)

Aplicado a cada **ganador por familia**. La selección usa una única métrica
primaria declarada en el manifiesto; queda prohibido elegir la métrica después
de mirar resultados.

### 2.1 Estimando e inferencia primaria

El estimando canónico es la expectativa neta ponderada por trade:

```text
theta_trade = sum_d(pnl_net_d) / sum_d(n_trades_d)
```

La unidad de dependencia es la **sesión elegible**. El universo se toma de un
calendario pre-registrado y completo, incluyendo sesiones con cero trades como
`(pnl_net=0, n_trades=0)`. No se permite inferir el calendario desde los días en
los que la estrategia operó.

El requisito primario y duro es:

- IC bilateral 95% **bootstrap-t estacionario** sobre pares de sesión
  `(pnl_net_d, n_trades_d)`;
- cada réplica recalcula el ratio de totales, nunca la media de ratios diarios;
- longitud de bloque Politis–White sobre la influencia del ratio;
- studentización HAC sobre la misma serie ordenada;
- al menos **160 sesiones elegibles**;
- al menos 90% de réplicas studentizadas válidas;
- la cota inferior del IC debe ser **> 0**.

El IC es la inferencia de expectativa positiva. Los cinco componentes restantes
son vetos complementarios y no lo reemplazan.

### 2.2 Nulo específico de campaña — campo estructural `mcpt`

No existe un MCPT universal defendible para todas las familias. Cada campaña
debe persistir antes de correr:

- `null_id` y la hipótesis exacta que rompe;
- generador y digest de su implementación;
- nuisance variables preservadas y supuesto de intercambiabilidad;
- semilla y número de réplicas;
- estadístico observado y estadístico idéntico por réplica.

El núcleo únicamente aplica el p-valor unilateral finito:

```text
p = (1 + count(T_null >= T_observed)) / (1 + B), con B >= 1000
```

Gate duro: **p ≤ 0.05**. El nombre `mcpt` se conserva en el esquema persistido
por compatibilidad histórica; significa **nulo de campaña**, no la función
retirada `mcpt()` ni el diagnóstico de concentración temporal.

### 2.3 PBO

- **PBO ≤ 0.50** vía CSCV con `S=8` particiones.
- La matriz completa es configs × tiempo de la campaña.
- Ranking in-sample y evaluación out-of-sample usan exclusivamente
  `sum_pnl_net / n_trades`; los escalares de P&L total son inválidos.

### 2.4 DSR por sesión y multiplicidad

Gate duro: **DSR ≥ 0.95** con:

- retorno de sesión no anualizado y un denominador de riesgo fijo,
  pre-registrado e idéntico entre variantes;
- calendario completo de sesiones elegibles; una sesión sin trades se codifica
  como retorno exactamente cero;
- mínimo de 160 sesiones, las mismas usadas por el IC primario;
- `N_eff` de intentos tomado del manifiesto completo, incluidas variantes
  abandonadas;
- dependencia `session_hac_bartlett_v2`;
- lag por defecto `ceil(sqrt(n_sessions))`, acotado a `[1,n-1]`;
- `n_effective = max(2, n / max(1, hac_variance/sample_variance))`;
- la autocorrelación negativa nunca puede autorizar `n_effective > n`.

La evidencia persiste: Sharpe observado, probabilidad DSR, `n`, `n_effective`,
`N_eff` de intentos, skew, kurtosis, lag, varianza muestral, varianza HAC,
factor de dependencia, nº de sesiones sin trades, digest del calendario,
digest de la especificación y digest AST de la implementación ejecutada.

### 2.5 Walk-forward por contrato

Para cada fold `k` (test = contrato `k`) se re-selecciona el ganador usando
solo contratos anteriores. Selección y agregado OOS usan el ratio de totales.
Gate duro: **expectancy WF-OOS neta > 0**. El primer fold sin historia no se
presenta como evidencia OOS.

### 2.6 Sensibilidad paramétrica

Vecinos ±1 paso de la grilla del ganador, sin incluir al ganador en su propia
vecindad. Gate duro: **mediana de expectancies netas > 0**. Sin vecinos, el gate
queda no evaluado y falla cerrado.

### 2.7 Composición, multiplicidad y calibración

La autoridad persistida es `G2ValidationDecision`. Deben pasar simultáneamente
el IC primario y los cinco gates, con evidencia completa y reconstruible. Un
gate ausente nunca cuenta como aprobado. `GateResult.passed` se deriva y valida
contra valor y umbral; no se confía en un booleano recibido.

La multiplicidad de la grilla se cobra una sola vez mediante DSR con `N_eff`
del manifiesto. SPA/White puede usarse como diagnóstico o para una pregunta
pre-registrada distinta, pero no se suma automáticamente como segundo cobro de
la misma familia.

`session_hac_bartlett_v2` tiene una calibración sintética determinista previa a
activación sobre:

- nulo gaussiano IID;
- nulo AR(1) con `rho=0.50`;
- nulo Student-t con 5 grados de libertad;
- nulo con 40% de sesiones sin trades;
- multiplicidad `N_eff=48` sobre el mismo panel;
- efectos plantados IID y AR(1).

Los sobres se fijan en `tests/research/test_g2_dsr_calibration.py` antes de ver
el resultado de CI. Esta calibración busca fallos gruesos; no convierte DSR en
inferencia primaria ni prueba validez universal para cualquier proceso.

### 2.8 Gobernanza de activación

La promoción exige simultáneamente:

1. SHA-256 exacto de este contrato en `APPROVED_G2_CONTRACT_SHA256S`;
2. fingerprint exacto de la implementación DSR en
   `APPROVED_G2_IMPLEMENTATION_SHA256S`;
3. decisión G2 ligada a la misma campaña, run, config y calendario;
4. aprobación explícita de Nico para poblar ambas allowlists.

Mientras cualquiera de las allowlists esté vacía, G2 permanece congelado aunque
los tests pasen. Cambiar el cuerpo de la implementación altera su digest AST y
vuelve a congelar promociones aunque el texto de la especificación no cambie.

**Implementación G2-A1:** `edgelab/research/g2.py`,
`edgelab/research/g2_decision.py`, `edgelab/research/promotion.py`,
`edgelab/stats/cluster_estimand.py` y tests `test_g2*.py`/
`test_cluster_estimand.py`.

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
