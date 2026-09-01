# Embudo de medición — aVolClusterPOI (EF V1, diseño)

- **Fecha de registro:** 2026-09-01 (ART)
- **Autor:** Notion AI — Auditor Cuantitativo. **Pedido por:** Nicolás.
- **Estado:** `DESIGN_ONLY_NOT_EXECUTABLE` · `NOT_A_CAMPAIGN` · `DOES_NOT_AUTHORIZE_OUTCOMES`
- **Holdout:** no se abre, no se toca, no se menciona como fuente.
- **Namespace:** `EF0-A … EF5` de `docs/research_funnel_playbook.md`. No se crea otro conjunto de etapas.
- **Objeto:** `nt8/aVolClusterPOI.cs` v0.5 (research freeze), blob `d512d91a606d41609b21ef244c896ead1dc52a10`, leído completo para escribir este documento.
- **Estado epistémico del objeto:** `PROVISIONAL_UNPARITIED`. Ausencia verificada: no existe `docs/parity_coverage/aVolClusterPOI.md` (sí existe `aVolCellPOI2.md`). La cabecera del propio `.cs` dice: «No usar sus zonas para operar hasta pasar el pipeline estandar».

---

## 0. El principio que hace válido un embudo adaptativo

Lo pedido: ir de medidas generales a particulares, donde la particularización no es al azar sino guiada por lo que arrojen las mediciones iniciales. Eso es correcto y es la forma barata de trabajar — **pero sólo suma evidencia si se prerregistra el mapa, no las conclusiones.**

Regla constitutiva de este embudo:

> Antes de correr una etapa, se declara por escrito: (a) qué mide, (b) qué **variables de decisión** produce, (c) con qué **umbrales**, (d) **qué rama abre cada resultado posible**.

Si las ramas se eligen después de ver los números, el embudo deja de ser un embudo y pasa a ser *garden of forking paths*: cada decisión post hoc gasta evidencia sin registrarla, y ninguna medición posterior puede ser confirmatoria. El adaptativo legítimo es un árbol de decisión fijado de antemano, no una improvisación informada.

Dos parámetros se declaran **ahora, antes de medir nada**:

1. **Efecto mínimo económicamente relevante: ≥ 1 tick** (misma vara que Gate 1). Lección del 2026-08-31: con 234 sesiones, 9 de 16 celdas dieron `p_holm ≤ 0,05` y el efecto máximo fue **0,261 ticks** — estadísticamente significativo, económicamente nulo. La puerta económica se declara antes o no sirve.
2. **Unidad de inferencia: la sesión.** No la zona. Miles de zonas en pocas sesiones no son miles de apuestas independientes (ATJ-11).

Todo lo explorado entra al ledger (ATJ-12), incluso lo que se descarta.

---

## 1. Qué emite el objeto (leído del código, no supuesto)

| Pieza | Comportamiento declarado y verificado en el fuente |
|---|---|
| Unidad de detección | Bloque de `WindowBars = 10` barras primarias; contador reiniciado al inicio de sesión; bloque parcial final descartado |
| Perfil por precio | Reconstruido siempre desde la subserie de 1 tick; celdas en **ticks enteros** (ULP 0 por construcción); ticks fuera de `[low, high]` de la barra ignorados |
| Nivel «hot» | `vol_celda ≥ mediana(bloque) × MedianMultiplier` (2.0); mediana = superior para n par |
| Cluster | Niveles hot contiguos con `gap ≤ MaxGapTicks` (1) y `≥ MinClusterTicks` (2); score = **suma** de volumen |
| Umbral de anomalía | Cuantil **empírico sin interpolar** (p98) del historial del **mismo bucket horario** (30 min, relativo a sesión), con `≥ MinSamplesPerBucket` (20), FIFO `LookbackSessions` (20). **Sin fallback global**: sin historia del bucket, no detecta |
| Cardinalidad | **Una zona por bloque**: el cluster de máxima masa entre los que pasan |
| Muestra al historial | Una por bloque = score del mejor cluster (**0 si no hubo**), commiteada al iniciar la sesión siguiente ⇒ causal, sin look-ahead |
| Dirección | LONG si el cierre creador queda arriba (soporte), SHORT si abajo (resistencia), y si cierra **dentro** ⇒ `AT_PRICE` (población aparte) |
| QualityScore | Heurístico 0–100: anomalía 35 %, concentración 25 %, densidad 15 %, rechazo 15 %, ráfaga 10 %. Declarado explícitamente **no probabilidad calibrada** |
| Ciclo de vida | Touch = intersección de rangos; default `CloseThrough`; `MaxAgeBars = 0` (sin expiración); `MaxTouches = 0` (ilimitado) |
| Evaluador forward | Tras el primer toque: MFE/MAE en ticks, `TARGET` 12 t / `STOP` 8 t / `TIMEOUT` 50 barras; empate en la misma barra ⇒ **`AMBIGUOUS`** (no inventa el orden — bien) |
| Export | CSV con meta completa en línea 1; eventos `ZONE_CREATED`, `AT_PRICE_CREATED`, `FIRST_TOUCH`, `ZONE_INVALIDATED`; modo **overwrite** siempre |

El diseño interno es notablemente disciplinado: aritmética entera, sin fallback que mezcle horas, historial sólo de sesiones completas anteriores, cuantil sin interpolar, `AMBIGUOUS` en vez de inventar orden. Eso hace que el embudo pueda arrancar en factibilidad y no en limpieza.

---

## 2. Cinco hallazgos estructurales del código que condicionan el embudo

**H1 — El export mezcla features con outcomes.** Las columnas `touch_bar`, `mfe_ticks`, `mae_ticks`, `outcome` viajan en las filas `FIRST_TOUCH` y `ZONE_INVALIDATED`. Consecuencia dura: el atlas de `EF1` **debe proyectarlas fuera explícitamente** para ser target-free. Leerlas es `EF2` y requiere aprobación escrita. No es un detalle de estilo: es dónde está el cortafuegos.

**H2 — Riesgo de umbral degenerado.** La muestra por bloque incluye los ceros (bloques sin cluster). Si los clusters son raros en un bucket, el p98 puede ser **0**, y el código exige `thresh > 0` para que una zona pase ⇒ **el detector no enciende nunca en ese bucket**. Es el mismo patrón que los `quintile_edges` degenerados que aparecieron en Gate 1 sobre NQ. Se mide antes de cualquier hipótesis.

**H3 — Warm-up estructuralmente ajustado.** Con una muestra por bloque·bucket·sesión, `MinSamplesPerBucket = 20` y `LookbackSessions = 20`, la FIFO retiene apenas el mínimo exigido. Cuántas muestras por bucket entran por sesión depende del `bar_spec`, y de eso depende si el detector alguna vez alcanza el mínimo. Medible y barato.

**H4 — `AT_PRICE` fuera del ciclo de vida.** El lifecycle hace `continue` sobre esas zonas: nunca reciben `FIRST_TOUCH` ni invalidación, y quedan acumulándose en el estado interno. Población separada, sólo con evento de creación. No se comparan sus tasas con las de `OFF_PRICE` como si fueran lo mismo.

**H5 — La ráfaga cruza sesiones.** La lista `creations` sólo se poda por ventana de 200 barras, no al inicio de sesión ⇒ `burst_count` puede contar creaciones de sesiones distintas. Declarable; no fatal, pero no se interpreta «ráfaga» como fenómeno intrasesión sin corregirlo.

---

## 3. `EF0-A` — Factibilidad del dato (puede EXCLUIR; target-free; barato)

Cinco preguntas, cada una con su regla de decisión declarada de antemano:

| # | Qué se mide | Rama si NO | Rama si SÍ |
|---|---|---|---|
| A1 | ¿El tick store congelado tiene **volumen por tick**? El detector reconstruye el perfil desde la subserie de 1 tick: sin volumen por precio no existe el objeto | **EXCLUYE** la réplica en Python sobre ese store; la línea queda dependiendo de un export NT8 (y de la limitación de la prueba gratuita) | Sigue a A2 |
| A2 | Bloques por bucket por sesión, y sesiones completas por contrato (alimenta H3) | Si no se alcanzan 20 muestras/bucket: **reparametrizar bucket/lookback antes de medir nada** — y eso es un `config_id` nuevo, no un ajuste silencioso | Sigue a A3 |
| A3 | Distribución de mejores scores por bucket (alimenta H2) | Si el p98 es 0 en la mayoría de buckets: el detector no enciende con los defaults ⇒ decisión de reparametrización **declarada**, no post hoc | Sigue a A4 |
| A4 | Zona horaria de los timestamps y semántica de sesión | Queda `NOT_OBSERVABLE` hasta que Nico declare TZ (misma deuda que la línea L2 de ZB) | Sigue a A5 |
| A5 | Sesiones pre-holdout disponibles **menos** las quemadas por warm-up | Si el remanente no da potencia por celda, se cierra la ambición de grilla fina antes de diseñarla | Habilita `EF0-B` |

Salida: acta `EF0-A` con esos números y nada más. Cero outcomes.

---

## 4. `EF0-B` — Probe provisional (prioriza; **no** excluye)

- Réplica Python del contrato de la cabecera (ticks enteros ⇒ exposición ULP 0 por construcción; verificar con `tools/ulp_exposure.py`).
- Oráculo NT8 sobre una ventana chica y creación de `docs/parity_coverage/aVolClusterPOI.md` bajo las reglas fail-closed del contrato de paridad.
- **Regla del playbook (ATJ-01):** pocos eventos, dirección rara o lifecycle anómalo **no excluyen** ninguna configuración mientras el port no tenga paridad. Un bug de réplica no es un resultado científico.

---

## 5. `EF1` — Atlas estructural target-free (acá se decide qué se pregunta después)

Una fila por zona × `config_id`, con features PRE/AT_EVENT, quality flags, `population_id`, `session_id`. **Sin outcomes** — proyección explícita por H1. Inmutable y as-of (ATJ-08).

Poblaciones materializadas **antes** de mirar cualquier outcome (ATJ-07):

- zona real (`OFF_PRICE`), separada de `AT_PRICE` por H4;
- **near-miss**: el cluster que pasó el umbral pero fue descartado por la regla de uno-por-bloque, y el que quedó a un pelo del percentil;
- control genérico emparejado por sesión · bucket · volatilidad.

Variables de decisión de `EF1` — todas target-free — y qué rama abre cada una:

| Variable | Qué decide |
|---|---|
| Eventos por sesión y sesiones con eventos | Potencia disponible. Si no hay sesiones viables por celda, la celda **muere antes de existir** (ATJ-11). Este es el filtro que Gate 1 enseñó a poner primero |
| Balance LONG/SHORT y share `AT_PRICE` | Si hay una, dos o tres poblaciones que analizar |
| Ancho de zona, densidad, `anomaly_ratio`, `distance_ticks` | Si alcanza **una** representación por familia o hay que separar (ATJ-09) |
| Solapamiento con `aVolCellPOI2` y con los eventos BT2A del store congelado | Redundancia. Si es alto, la pregunta correcta pasa a ser **incremental** («¿agrega algo sobre lo ya medido?»), no nueva |
| Integridad de lifecycle: censura por derecha vs corrupción (ATJ-05) | Qué zonas son analizables y cuáles quedan en clase separada |

**Éste es el corazón del embudo:** las mediciones de `EF0-A` y `EF1` están elegidas justamente porque sus resultados determinan qué hipótesis tiene sentido escribir después — y las reglas de esa determinación están escritas arriba, antes de correrlas.

---

## 6. `EF2` — Screening exploratorio (requiere aprobación escrita; consume pre-holdout)

- Panel común predeclarado de outcomes (ATJ-10): desplazamiento firmado, MFE/MAE en horizontes comunes, una carrera de barreras común.
- **El evaluador interno del indicador (12 t / 8 t / 50 barras) no es el outcome primario:** son tres parámetros elegidos por el autor, no un panel neutral. Queda como comparador secundario, declarado.
- Unidad de remuestreo = sesión; bootstrap por sesión; Holm sobre la grilla; **efecto mínimo ≥ 1 tick** ya declarado en §0.
- Etiqueta obligatoria del resultado: `EXPLORATORY_OUTCOME_SCREEN_NOT_CONFIRMATORY`.
- El pre-holdout usado acá queda **gastado** para esta selección.

---

## 7. `EF3` → `EF4` → `EF5`

- `EF3`: reducción por familias, no recorrido del producto cartesiano (ATJ-09).
- `EF4`: freeze de **≤ 3 hipótesis** con `config_id`, poblaciones, outcome primario, umbral económico y potencia requerida. No produce evidencia nueva.
- `EF5`: confirmación, sólo con autorización de holdout bajo `docs/edge_validation_contract.md` (G4). No reajusta nada de lo congelado.

---

## 8. Lo que este documento NO hace

No autoriza `EF0`, `EF1` ni `EF2`. No accede a outcomes. No abre el holdout. No declara paridad ni la hereda. No promueve nada. No habilita usar las zonas para operar — lo prohíbe la propia cabecera del indicador.

## Aporte al referente

Un embudo adaptativo con **mapa prerregistrado** es lo que permite que «particularizar según lo que se midió» acumule evidencia en vez de gastarla. La diferencia entre este diseño y una exploración improvisada no está en los números que se van a medir, sino en que las ramas ya están escritas antes de verlos.
