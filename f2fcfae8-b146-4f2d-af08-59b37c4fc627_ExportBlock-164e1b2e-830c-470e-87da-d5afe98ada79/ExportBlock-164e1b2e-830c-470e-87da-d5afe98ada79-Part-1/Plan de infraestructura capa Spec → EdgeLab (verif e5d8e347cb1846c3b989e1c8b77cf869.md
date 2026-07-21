# Plan de infraestructura: capa Spec → EdgeLab (verificación de la interpretación del LLM)

> **Problema a resolver:** hoy, cuando le pedís a un LLM (Claude Code u otro) que pruebe algo en EdgeLab ("probá ARB con SMA200 y salida a las 16:00"), el LLM traduce tu pedido directamente a código Python ad-hoc. No tenés forma sistemática de confirmar que lo que entró al motor es lo que vos quisiste decir. El caso ARB lo demuestra: `eurusd_session_breakout.py` implementa una estrategia distinta a la documentada en EDGES_[DISCOVERED.md](http://DISCOVERED.md), y nadie lo detectó.
> 

<aside>
🔎

**Revisión de arquitectura v2 — 21 jul 2026:** mantengo la idea Spec → validación → aprobación → compilación, pero corrijo cinco puntos: condiciones estructuradas en vez de strings Python; hash semántico en vez de hash del YAML crudo; aprobaciones append-only; registro de intención antes de ejecutar para medir multiplicidad; y versionado completo de calendario, política de barras, costes y compilador.

</aside>

## Implementaciones nuevas de alto valor

- **Candidate Registry:** estados obligatorios `DRAFT → APPROVED → DRY_RUN_VERIFIED → FROZEN → EVALUATED → PROMOTED/REJECTED`. No se puede saltar un estado.
- **Research budget:** antes de probar, declarar familia, rango de parámetros, máximo de trials y métrica primaria. Cada trial consume presupuesto aunque falle o se aborte.
- **Holdout vault:** fechas OOS quedan selladas; solo el comando de evaluación final puede abrirlas una vez por versión de candidato. Toda reapertura crea una nueva familia y penaliza multiplicidad.
- **Decision trace:** por cada timestamp evaluado, guardar features observables, valores, resultado de cada condición, decisión, orden y fill. Permite auditar tanto trades como no-trades.
- **Differential runner:** ejecutar la misma spec en referencia Python lenta y engine Numba; exigir paridad de señales y fills en fixtures antes de habilitar producción.
- **Data contracts:** schema, zona horaria, monotonía, duplicados, crossed quotes, gaps, calendario y fingerprint del dataset se validan antes de calcular features.

# Principio de diseño

<aside>
🧭

**Para una prueba normal, el LLM produce una spec declarativa y no modifica el motor.** Si hace falta un indicador nuevo, puede proponer un plugin Python en un cambio separado, con contrato tipado, implementación de referencia, fixtures y tests de paridad. El compilador es determinista y cualquier extensión cambia su `compiler_contract_hash`.

</aside>

Beneficios directos:

- **Verificabilidad:** la spec es legible por humanos y comparable 1:1 con tu intención.
- **Reproducibilidad:** la spec se hashea y va al ledger; cualquier resultado es re-derivable.
- **Multiplicidad honesta:** toda intención y trial queda registrada. El registro cuantifica la búsqueda; PBO/SPA se calculan aparte sobre matrices sincronizadas de retornos, no mediante un simple denominador.
- **Menos superficie de bug:** el compilador se valida una vez; las estrategias ya no introducen código nuevo en el hot path.

# Arquitectura (6 componentes)

```
Tu pedido en lenguaje natural
        │  (LLM traduce)
        ▼
① StrategySpec (YAML) ──► ② Validador (schema + semántica + unidades)
        │                          │ errores legibles
        ▼                          ▼
③ Echo-back en español ◄── vos APROBÁS o corregís (gate humano)
        │ aprobado (hash firmado)
        ▼
④ Compilador spec → engine (determinista, sin LLM)
        │
        ▼
⑤ Dry-run + golden trades explicados ──► segunda confirmación
        │
        ▼
⑥ Ejecución real + ledger (spec hash + resultados + gauntlet gate)
```

---

# Fase A — Schema `StrategySpec` (1–2 días)

**Archivos nuevos:** `edgelab/spec/schema.py` (pydantic v2), `specs/` (carpeta de specs versionadas en git), `edgelab/spec/__init__.py`.

**Diseño del schema (campos mínimos):**

```yaml
# specs/arb_eurusd_v1.yaml
meta:
  name: arb_eurusd
  version: 1
  author_intent: >
    Breakout del rango asiático con filtro de tendencia SMA200,
    solo en 4 ventanas horarias, cierre forzado 16:00 UTC.
  hypothesis: "El quiebre del rango asiático con tendencia a favor persiste hasta la tarde europea"
instrument: EURUSD
data:
  source: jforex_ticks
  bar_frame: 15min          # solo para indicadores; fills siempre con ticks
  bar_label: left
  bar_interval: left_closed_right_open
  decision_lag: next_tick
  calendar: fx_ny_v1
  session_utc: ["00:00", "16:00"]
indicators:
  - id: sma200
    type: sma
    input: close
    period: 200
    frame: 15min
  - id: asian_range
    type: session_range
    window_utc: ["00:00:00", "08:00:00"]
    interval: left_closed_right_open
    available_at: "08:00:00"
entry:
  windows_utc: ["08:45", "09:00", "11:00", "12:00"]
  long_when:
    all:
      - {left: close, op: gt, right: asian_range.high}
      - {left: close, op: gt, right: sma200}
  short_when:
    all:
      - {left: close, op: lt, right: asian_range.low}
      - {left: close, op: lt, right: sma200}
  max_entries_per_day: 1
exit:
  take_profit: {value: 20, unit: pips}
  stop_loss:   {value: 50, unit: pips}
  time_exit_utc: "16:00"
costs:
  commission_round_trip: {value: 0.0, unit: pips}
  slippage_each_side: {value: 0.0, unit: pips}
  fill_model: tick_bid_ask   # el spread observado ya queda incorporado
validation:
  gauntlet: required          # no se puede omitir; ver Fase F
```

**Pasos:**

1. Implementar el schema con pydantic: tipos estrictos, `extra="forbid"` (un typo en un campo = error, no silencio), enums para `unit` (pips / pipettes / ticks — la confusión pips↔pipettes ya apareció en `HEADLINE=(150.0, 50.0)`).
2. Las condiciones usan un **árbol estructurado cerrado** (`all`, `any`, `not`, `left`, `op`, `right`) validado por discriminated unions de Pydantic. Evitar strings con sintaxis Python y `ast.parse`: agregan una segunda gramática, ambigüedad y superficie de seguridad sin aportar valor.
3. Catálogo cerrado de tipos de indicador (`sma`, `ema`, `session_range`, `atr`, `vwap`, ...): agregar un indicador nuevo requiere tocar el compilador con tests, no lo puede inventar el LLM en la spec.
4. Documentar el schema en `edgelab/spec/SPEC_REFERENCE.md` — este archivo es el que le pegás al LLM cuando le pedís que redacte una spec.

**Criterios de aceptación:** una spec con typo de campo, unidad inexistente o indicador no declarado en una condición **falla en carga** con mensaje claro.

---

# Fase B — Validación semántica y de unidades (1 día)

**Archivo nuevo:** `edgelab/spec/validate.py`.

Reglas de dominio (más allá del schema), cada una con test:

1. **Unidades:** TP/SL en pips para FX, ticks para futuros; conversión explícita a pipettes internos con factor documentado. Rechazar valores sospechosos con warning bloqueante (ej. TP 200 pips en EURUSD intradía → "¿seguro que no son pipettes?").
2. **Tiempo:** todo en UTC obligatorio; ventanas de entrada deben caer dentro de la sesión; `time_exit_utc` posterior a la última ventana de entrada; ventanas alineadas al `bar_frame`.
3. **Coherencia:** indicadores referenciados en condiciones deben estar declarados; `session_range.window` no puede solaparse con ventanas de entrada; `fill_model: mid` prohibido salvo flag explícito `allow_mid: true` con justificación.
4. **Anti-overfitting estructural:** si la spec tiene >N parámetros libres (configurable, ej. 6), warning que exige declarar el tamaño de la búsqueda prevista (alimenta el conteo de multiplicidad de Fase F).
5. **Holdout/poison windows:** administrarlas en una política de evaluación separada y sellada. El motor genérico no debe censurar fechas silenciosamente; el manifest debe mostrar qué períodos estaban ocultos, excluidos o habilitados y por qué.

**Criterio de aceptación:** suite de ≥15 specs inválidas en `tests/specs_invalid/`, cada una rechazada con el mensaje esperado.

---

# Fase C — Echo-back: el gate humano (1 día) ⭐

**Archivo nuevo:** `edgelab/spec/render.py` + comando CLI `edgelab spec explain specs/arb_eurusd_v1.yaml`.

Este es el componente que resuelve tu problema central. Genera una **re-narración determinista en español** de la spec (NO generada por LLM — generada por plantillas de código, para que no pueda "alucinar" la explicación):

```jsx
═══ arb_eurusd v1 · EURUSD · ticks JForex ═══
SESIÓN      00:00 → 16:00 UTC (13:00 hora Buenos Aires en invierno)
RANGO       Máx/mín en [00:00:00, 08:00:00) UTC; queda disponible a las 08:00
INDICADOR   SMA 200 sobre closes M15 (50 horas de barras válidas; warm-up según calendario y gaps)
ENTRADAS    La spec debe indicar si 08:45/09:00/11:00/12:00 nombran inicio de barra o instante de decisión
  LONG  si  close > máximo del rango asiático  Y  close > SMA200
  SHORT si  close < mínimo del rango asiático  Y  close < SMA200
  Máximo 1 trade por día. Fills con bid/ask real del tick siguiente.
SALIDAS     TP +20.0 pips · SL −50.0 pips · cierre forzado 16:00:00 UTC
            En ticks bid/ask se respeta el primer evento observable; una barra OHLC con TP y SL es ambigua
COSTOS      Spread observado + comisión + slippage separados. Sin doble conteo.
VALIDACIÓN  Gauntlet OBLIGATORIO (MCPT≤0.05, PBO≤0.50, SPA)
TIMELINE    00:00 ─────rango───── 07:45 │ 08:45↑ 09:00↑ ... 11:00↑ 12:00↑ ──── 16:00 ✕
Hash spec   a3f8c2…  →  aprobar con: edgelab spec approve a3f8c2
```

**Pasos:**

1. Renderer de plantillas con **derivaciones explícitas** (breakeven en pips, horas locales, cuántos días de warm-up necesita la SMA): estas derivaciones son las que delatan malentendidos ("¿200 barras M15 son solo 2 días? yo quería 200 días").
2. Timeline ASCII de la sesión con rango, ventanas y salida.
3. Comando `edgelab spec approve <semantic_hash>`: agrega un evento inmutable a `ledger/approvals.jsonl` con usuario, timestamp UTC, `semantic_hash`, `raw_source_hash`, `schema_version`, `compiler_contract_hash` y `data_contract_version`. El hash semántico surge de la spec parseada y canonicalizada; comentarios, espacios u orden irrelevante del YAML no invalidan aprobación, pero cualquier cambio de significado sí. El runner rechaza specs sin aprobación vigente.
4. Sección "⚠️ Interpretaciones que asumí" al final del render: lista automática de defaults aplicados (ej. "asumí evaluación al close de barra, no intra-barra") — los defaults silenciosos son la fuente nº1 de malentendidos con LLMs.

**Criterio de aceptación:** el flujo completo pedido→spec→explain→corrección→approve funciona de punta a punta con el ARB real como caso de prueba.

---

# Fase D — Compilador spec → engine (2–3 días)

**Archivo nuevo:** `edgelab/spec/compile.py`.

**Pasos:**

1. El compilador toma una spec aprobada y produce: (a) series de indicadores precalculadas desde barras corregidas (reusa Fase 1 del plan de remediación), (b) arrays de señales/ventanas listos para el hot loop numba, (c) parámetros del engine (TP/SL en unidades internas, `exit_at_utc` de la Fase 3 del otro plan, fees).
2. **Un solo camino de ejecución:** las estrategias existentes (noise_area, orb, tickfade) se migran gradualmente a specs; mientras tanto conviven, pero toda estrategia *nueva* entra solo por spec.
3. Property-based testing con `hypothesis`: generar specs válidas e inválidas y verificar invariantes. Mantener dos ejecutores: `ReferenceEngine` Python simple como oráculo y `NumbaEngine` optimizado; correr differential tests sobre señales, órdenes, fills, razones de salida y PnL en unidades enteras. `poison windows` pertenecen a la política de evaluación/holdout, no al motor de ejecución genérico.
4. El compilador emite `compiled_manifest.json` con spec semántica, schema/compilador, calendario, política de barras, catálogo de instrumentos, modelo de costos, rango de datos, fingerprint de archivos/particiones y hashes de código. Nunca reutilizar artefactos si cambia alguno.

**Criterio de aceptación:** el ARB compilado desde spec reproduce trade por trade el port manual de la Fase 4 del plan de remediación (test de paridad automática).

---

# Fase E — Golden trades: la segunda confirmación (1–2 días) ⭐

**Archivos nuevos:** `edgelab/spec/replay.py`, comando `edgelab run spec.yaml --dry-run --sample-trades 5`.

El echo-back (Fase C) confirma la *intención*; los golden trades confirman el *comportamiento*:

1. **Dry-run con selección determinista y estratificada:** muestra casos por outcome y casos borde, sin permitir que el LLM elija ejemplos favorables. Incluir TP, SL, salida horaria, no-señal, señal filtrada, barra faltante, spread extremo e intrabar ambiguo cuando existan. Cada caso imprime su **cadena causal completa**, diferenciando `signal_time`, `decision_time`, `order_time` y `fill_time`:
    
    ```
    Trade #3 · 2025-04-11 · SHORT
    07:44:59 rango asiático cerrado: high 1.09432 / low 1.09218
    09:00:00 close barra = 1.09201 < low(1.09218) ✓  y  < SMA200(1.09480) ✓ → SHORT
    09:00:00.412 fill al bid 1.09199 (spread 0.6 pips en ese tick)
    11:23:07.891 TP tocado: ask 1.08999 ≤ 1.09199−0.0020 → cierre +20.0 pips
    PnL neto: +19.0 pips (fees 1.0)
    ```
    
2. **Golden tests sintéticos:** por cada tipo de regla del DSL, un dataset de ticks sintético diminuto con resultado calculable a mano, guardado en `tests/golden/`. Cuando el compilador cambia, los goldens detectan regresiones de interpretación.
3. **Contra-ejemplos automáticos:** el dry-run reporta también "días donde NO se operó y por qué" (rango no quebrado / filtro SMA / poison window) — la ausencia de trades esperados es tan diagnóstica como los trades.

**Criterio de aceptación:** para el ARB, los 5 trades de muestra coinciden con inspección manual tuya en JForex/chart.

---

# Fase F — Integración con ledger, preflight y multiplicidad (1 día)

1. **Spec hash en el ledger:** cada corrida registra `spec_hash`, `data_hash`, `engine_version`, seed. Resultado no reproducible = resultado inválido.
2. **Gate estructural de gauntlet:** `EDGES_DISCOVERED.md` deja de editarse a mano; un edge solo puede marcarse como DESCUBIERTO vía `edgelab promote <spec_hash>`, que exige en el ledger un gauntlet verde (MCPT/PBO/SPA) para ese hash exacto. Esto hace **estructuralmente imposible** repetir el caso ARB (edge documentado sin gauntlet).
3. **Registro previo de intención y multiplicidad:** `edgelab candidate register` crea `family_id`, `candidate_id`, espacio de búsqueda, presupuesto, métrica primaria y holdout antes de ejecutar. Trials fallidos o abortados también quedan como eventos append-only. PBO y SPA consumen matrices sincronizadas de retornos; el contador de trials documenta multiplicidad, pero no sustituye esos tests.
4. Preflight agrega gates para aprobación semántica, contrato de datos, contrato del compilador, ausencia de look-ahead, presupuesto de investigación y disponibilidad autorizada del holdout.

---

# Fase G — CLI y ergonomía (1 día)

Comando único `edgelab` (typer o argparse):

```
edgelab spec new <nombre>          # plantilla comentada
edgelab spec explain <spec>        # echo-back (Fase C)
edgelab spec approve <hash>
edgelab run <spec> --dry-run --sample-trades 5
edgelab run <spec>                 # exige approve + registra en ledger
edgelab gauntlet <spec>
edgelab promote <spec_hash>
edgelab ledger show [--edge <nombre>]
```

Detalles de eficiencia y practicidad:

- Cache de barras/indicadores con key content-addressed que incluya fingerprint de datos/particiones, schema, calendario, timezone, convención de barras, código del indicador, parámetros, versión de librerías y política de NaN. `(data_hash, frame, indicador)` solo es insuficiente.
- Salidas atómicas en `runs/<candidate_id>/<run_id>/`: primero directorio temporal, luego rename al completar. Incluir `manifest.json`, `decision_trace.parquet`, `orders.parquet`, `fills.parquet`, `trades.parquet`, `metrics.json`, logs y estado final. Una corrida interrumpida queda explícitamente `ABORTED`.
- `--profile` opcional que reporta tiempos por etapa (build barras / compile / hot loop / métricas) para tu Ryzen 5.

---

# Fase H — Actualizar CONTRATO_[LLM.md](http://LLM.md) y flujo de trabajo (½ día)

Nuevo contrato con el LLM (agregar estas cláusulas):

1. *"Para una prueba soportada, tu output funcional es una spec en `specs/`; no modifiques engine ni compilador. Si falta una capacidad, detenete y proponé un plugin/ADR separado con implementación de referencia, tests y migración. Nunca hagas bypass ad-hoc."*
2. *"Después de escribir la spec, corré `edgelab spec explain` y pegá el output completo. No ejecutes nada hasta que Nico apruebe con el hash."*
3. *"Si la spec necesita un indicador o regla que el DSL no soporta, tu tarea es proponer la extensión del compilador (con tests y golden cases) como PR separado, nunca un bypass."*
4. *"Cambios al compilador/engine requieren: golden tests, differential tests Reference↔Numba, ledger de trades canario estable, PnL dentro de tolerancia declarada y evento de auditoría."*

**Flujo final de una idea nueva (tu día a día):**

1. Le describís la idea al LLM en lenguaje natural.
2. El LLM redacta `specs/idea_v1.yaml` (30 líneas legibles).
3. `edgelab spec explain` → leés la re-narración en español + defaults asumidos (2 min).
4. Corregís en el YAML lo que se malinterpretó → nuevo explain → `approve`.
5. `edgelab run --dry-run --sample-trades 5` → verificás 5 trades con su cadena causal (5 min).
6. `edgelab run` + `edgelab gauntlet` → resultados al ledger con multiplicidad automática.
7. Solo `edgelab promote` puede declarar un edge — y exige gauntlet verde.

---

# Resumen de esfuerzo

| Fase | Esfuerzo | Valor |
| --- | --- | --- |
| A Schema | 1–2 d | Base de todo |
| B Validación semántica | 1 d | Mata typos y confusión de unidades |
| C Echo-back + approve | 1 d | ⭐ Tu gate de interpretación |
| D Compilador | 2–3 d | Un solo camino al motor |
| E Golden trades | 1–2 d | ⭐ Confirmación por comportamiento |
| F Ledger + gate gauntlet | 1 d | Imposibilita el caso ARB |
| G CLI + cache | 1 d | Eficiencia diaria |
| H Contrato LLM | ½ d | Cierra el loop |

**Estimación revisada: 12–16 días efectivos** si se implementan también ReferenceEngine, Candidate Registry, holdout sellado, contratos de datos y differential testing. MVP recomendado: A → B → C → Candidate Registry básico (4–5 días). Después D → E → F → G → H.

<aside>
🔗

**Relación con el plan de remediación:** hacé primero las Fases 0–3 del plan de remediación (higiene, weekend bars, validator, exit-at-time) porque este plan las reusa. La Fase 4 (port del ARB) es el caso de prueba perfecto para el compilador (Fase D): el test de paridad entre el port manual y el ARB compilado desde spec valida ambos planes a la vez.

</aside>