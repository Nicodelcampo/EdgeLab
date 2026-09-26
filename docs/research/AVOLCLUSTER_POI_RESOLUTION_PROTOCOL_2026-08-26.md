# Protocolo target-free — selección de resolución de barra para `aVolClusterPOI` (GC)

Estado: `DISEÑO_PROTOCOLO_NO_EJECUTADO`. Ningún dato tocado, ningún barrido corrido, kernel sin modificar. Hash del cuerpo de `docs/NORTH_STAR.md` citado por `CLAUDE.md`: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`. Holdout (2026-07-01→) no interviene en nada de lo que sigue — todo el universo propuesto es pre-holdout.

Este documento responde el pedido de Nico: criticar las 5 métricas estructurales que propuso Antigravity/Gemini para elegir resolución de barra de `aVolClusterPOI` sobre GC, y diseñar un protocolo target-free mejorado, sin correr nada todavía.

---

## 0. Resumen ejecutivo

Las 5 métricas de Antigravity apuntan en la dirección correcta pero **no son un protocolo**: no dicen contra qué se comparan (no hay nulo), no controlan la multiplicidad de elegir "la más linda" entre varias resoluciones, tratan tiempo y ticks como si fueran el mismo eje, y — la más peligrosa — pueden caer en la misma trampa que ya se documentó dos veces en este proyecto: mirar conteo/geometría agregada en vez del fingerprint completo del objeto (`docs/research/BT2_ABSORPTION_SWEEP_OVERNIGHT_2026-08-24.md`, línea 18, y el hallazgo de seis ejes "no-op por conteo" citado en `CLAUDE.md`).

Verificado en el código del kernel (no supuesto): `aVolClusterPOI` **ya es agnóstico a la unidad de barra** — `edgelab/bridge/indicators/avolclusterpoi.py` consume `cells` (volumen por tick dentro de un bloque) ya armadas por el caller; el kernel en sí mismo no sabe si el bloque vino de un minuto o de 250 ticks. Lo que hoy fija `minutes=1` es el *harness* (`diag/tasa_senales/avolcluster_tick_formal.py:348,460` y `diag/tasa_senales/avolcluster_p2_replay_v01.py:173`), no el kernel. Y el constructor de barras de N-ticks **ya existe y ya está resuelto el defecto de reinicio por sesión** (`edgelab/bridge/bars.py::build_tick_bars`, `TICKBAR-001`). Esto cambia la respuesta a "qué hay que escribir": no hace falta tocar el kernel ni escribir un bar-builder nuevo — hace falta un harness de orquestación nuevo más una pieza que hoy no existe en absoluto: el **placebo target-free**.

---

## 1. Crítica puntual de las 5 métricas de Antigravity

### 1.1 Densidad y espesor de zona (2-6 ticks)

**Lo que está bien**: es la idea correcta de cohesión intra-cluster, versión 1-D honesta de lo que Dunn/Silhouette intentan capturar en clustering multidimensional — y con más legitimidad que importar esos índices tal cual, porque la literatura los cuestiona incluso en su hábitat nativo (`https://www.sciencedirect.com/science/article/abs/pii/S0020025521010082`, "Are cluster validity measures (in)valid?"; y `https://en.wikipedia.org/wiki/Silhouette_(clustering)`: Silhouette está "especializado para clusters convexos" y no aplica bien a un evento disperso sobre fondo mayoritariamente normal, que es la topología real de este detector).

**Lo que le falta**: un umbral fijo en ticks (2-6) es una restricción de negocio válida (stops ajustados), pero tal como está planteada es una estadística agregada de UNA corrida — no dice si esa distribución de anchos es estable entre configuraciones vecinas o si es ruido de muestreo de esas sesiones particulares. Sin nulo (ver §2.1) "2-6 ticks" no distingue "esta resolución produce zonas compactas por estructura" de "esta resolución produce zonas compactas porque con pocos ticks activos por bloque cualquier cluster que sobreviva el filtro de mediana×2 es corto casi por construcción".

**Trampa conocida en la que cae si se usa cruda**: es exactamente la trampa de "mirar conteo/geometría agregada, no el fingerprint completo del objeto" que ya pasó con los seis ejes de BigTrap2 que parecían no-op por conteo pero cambiaban el ciclo de vida (`jaccard=1.0`, fingerprint distinto). Dos resoluciones vecinas pueden dar la MISMA distribución de anchos (mismo resumen agregado) mientras detectan zonas en bloques completamente distintos (fingerprint distinto). Espesor solo se puede usar acompañado del fingerprint por sesión (`target_free_fingerprint` tal como lo implementa `tools/bt2_absorption_param_sweep.py:374`, digest de `{sessions, events}`, no un conteo), nunca solo.

### 1.2 Frecuencia operativa (2-6 zonas/sesión)

**Lo que está bien**: acotar frecuencia operativa es un requisito de negocio legítimo (ni 40/hora ni 1/semana).

**Lo que le falta, y es el problema más grave de las 5**: "zonas por sesión" mezcla dos cosas que cambian juntas al cambiar de resolución — la propiedad estructural del detector Y la cantidad de bloques que esa resolución genera por sesión. Esto tiene cita directa y es el hallazgo más aplicable de toda la investigación: `https://www.mql5.com/en/articles/23310` — "cambiar el tipo de barra modifica simultáneamente dos cosas: número de muestras y estructura de correlación serial, así que cualquier diferencia en performance downstream es una maraña de efectos de tamaño de muestra y efectos de representación que no se puede separar después de ocurrida". Una sesión asiática lenta genera muchos menos bloques de N-ticks que la apertura de NY genera del mismo N; comparar "zonas/sesión" cruda entre resoluciones sin normalizar por bloques evaluados mide en parte "cuántos bloques generó hoy esta resolución", no "qué tan buena es la zona".

**Fix obligatorio**: reportar SIEMPRE tasa normalizada (zonas / 100 bloques evaluados), no solo zonas/sesión cruda.

### 1.3 Independencia y aislamiento

**Lo que está bien**: apunta a la idea correcta (separación inter-cluster, "que no se pisen"), y es más apropiada que trasplantar Dunn/CH formal — la literatura de índices de validez está diseñada para particiones completas tipo k-means, no para eventos anómalos dispersos sobre fondo normal (mismo punto que en §1.1).

**Lo que le falta**: tal como está descripta mide separación en el momento de **creación**. `CLAUDE.md` ya exige separar evento de estado y enumerar por separado creación / aproximación / primer toque / invalidación / expiración / confluencia / estado continuo antes de congelar cuál familia se mide (regla de población, sección "Ninguna población se congela sin enumerar..."). Una zona puede nacer aislada y luego solaparse en su vida activa con otra zona nueva — "independencia" medida solo en creación no ve eso. Hay que medir gap mínimo sobre el LIFECYCLE completo (creación→expiración vía `max_age_bars`), no un snapshot puntual — otra vez la lección de fingerprint vs. conteo puntual.

### 1.4 Estabilidad entre sesiones

**Lo que está bien**: esta es, sin que Antigravity lo haya nombrado así, la versión informal de un marco formal real y bien fundamentado: validación por estabilidad bajo perturbación (Ben-Hur, Elisseeff & Guyon 2002, `https://psb.stanford.edu/psb-online/proceedings/psb02/benhur.pdf`) — perturbar el dataset y exigir que la estructura detectada no se desarme. Es la métrica mejor orientada de las 5.

**Lo que le falta**: "funciona parejo en días lentos y de alta volatilidad" no es una estadística, es una intención. Hay que convertirla en algo computable: coeficiente de variación de (densidad, tasa normalizada, aislamiento) entre los terciles de volatilidad que el proyecto ya usa para HFTZones-ES (la misma partición de terciles del handoff vigente), MÁS estabilidad bajo resampleo de sesiones (bootstrap, la receta formal de Ben-Hur et al.). Sin esto, "estable" es una impresión visual, exactamente lo que el propio Market Profile advierte que NO alcanza como evidencia: la fuente que originó POC/Value Area dice literalmente que sobre una distribución fuera de equilibrio "a simple visual examination will often be enough to certify that the distribution is abnormal" pero eso no es un test (`https://en.wikipedia.org/wiki/Market_profile`) — mismo tipo de atajo a evitar acá.

### 1.5 Test de meseta

**Lo que está bien**: esta es, con nombre propio en la literatura, la métrica mejor fundamentada de las 5. "Parameter plateau" es un concepto establecido (Pardo; formalizado en 2024 con PSO) y comparte la lógica de fondo que ya usan PBO/DSR en este repo: bajo un nulo de puro ruido, una meseta ancha y simultánea en muchas configuraciones correlacionadas es mucho menos probable que un pico aislado — la meseta es evidencia estructural de señal, no de ruido.

**Lo que le falta, y es una trampa ya vivida en este proyecto en otra familia**: si se prueba 40t/50t/60t re-derivando `WindowBars` proporcionalmente para "mantener el tiempo de reloj constante" al cambiar `tick_size`, eso NO es una meseta — es una **cresta colineal** disfrazada de meseta (la literatura de "collinearity in parameter sweeps" lo nombra así). Es exactamente la misma familia de error que ya obligó a separar `TicksPerRow` de `bar_spec` en la campaña de BigTrap2 (`CLAUDE.md`: "`ticks_per_row` y `bar_spec` son ejes distintos — no confundir un parámetro del indicador con la resolución de barra"). El test de meseta tiene que variar tamaño de bloque y tick_size **de forma independiente en una grilla 2-D**, no sobre la diagonal `WindowBars ∝ 1/tick_size`.

---

## 2. Qué falta estructuralmente (no metrica por métrica, sino al framework completo)

### 2.1 No hay nulo/placebo — "2-6 zonas por sesión es bueno" ¿bueno respecto a qué?

Ninguna de las 5 métricas tiene un punto de comparación. El precedente correcto en este mismo proyecto es F2.7-F2.10 sobre BigTrap2: el patrón que dejaron sentado es que un placebo/control replica la MISMA geometría del objeto real pero **elimina exactamente el ingrediente que se prueba** (`docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md`: "un control sin zona, misma geometría, da casi lo mismo: el contraste cruza cero"). Ese nulo específico no se puede transportar tal cual — `CLAUDE.md` lo prohíbe explícitamente entre familias de indicador ("No se transportan resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad entre familias") — y de hecho no existe HOY ningún nulo target-free reusable para `aVolClusterPOI`: el único nulo ya escrito en el repo, `edgelab/research/nulls.py::PlaceboResampleWithinSession`, opera sobre outcomes netos de trade (P&L), es decir, es un nulo de campaña bajo el STOP, no uno target-free — no sirve para esta tarea de diseño.

Hay que diseñar uno nuevo, propio de esta familia (protocolo completo en §3.3).

### 2.2 Multiplicidad/sobreajuste de la SELECCIÓN en sí — aunque no mire P&L

Elegir "la resolución más linda" entre varias candidatas por un score estructural sigue siendo un camino bifurcado (garden of forking paths, Gelman & Loken). Cita literal: el sesgo "puede aparecer aunque el investigador haga un solo análisis... esto puede pasar implícitamente en investigadores que conocen las buenas prácticas y sólo hacen una comparación y evalúan sus datos una sola vez" — el mecanismo depende del número de caminos analíticos posibles, **no de si al final del camino se mira P&L o una métrica estructural** (`https://sites.stat.columbia.edu/gelman/research/unpublished/p_hacking.pdf`).

Dos consecuencias concretas y verificables sin ejecutar nada:

- **Double dipping / circular analysis**: si las 5 métricas se calculan sobre las mismas sesiones que después "confirman" que la resolución ganadora es buena, esa confirmación está contaminada — es el mismo patrón que Kriegeskorte et al. 2009 documentaron en el 42% de una muestra de papers de fMRI (`https://www.nature.com/articles/nn.2303`). Fix: split de sesiones (§2.4).
- **PBO/winner's curse sobre el score estructural**: el resultado de Bailey/Borwein/López de Prado/Zhu (PBO crece con el número de configuraciones comparadas, "regardless of whether any individual configuration has genuine predictive power", `https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf`) es agnóstico al estadístico optimizado — aplica igual de literal a "elegir la config con mejor score estructural compuesto entre N candidatas" que a Sharpe. Fix: pre-registrar el tamaño de la grilla ANTES de correr (igual que el STOP exige para campañas de P&L) y publicar el landscape completo de todas las configs, no solo la ganadora — mismo espíritu que "target-free publica el landscape completo... nunca selecciona por P&L máximo aislado" pero aplicado al score estructural.

Adicionalmente, el estudio de selección de hiperparámetros sin labels sobre 297 modelos candidatos encontró que ninguna estrategia de evaluación interna resultó "prácticamente útil" — apenas comparable a elegir al azar (`https://arxiv.org/abs/2104.01422`, KDD 2023). Esto no es razón para no usar las 5 métricas, pero sí para tratarlas como **filtro de descarte grosero** (eliminar lo absurdo) y no como criterio fino de optimización — ver el criterio de selección en cascada de §3.4, diseñado explícitamente para no depender de un ranking fino.

### 2.3 ¿Tiempo (1m/3m/5m) y ticks (25t/50t/100t) son el mismo eje? — NO, y con argumento

Decisión: **NO son comparables en una sola grilla.** Son dos preguntas de investigación separadas, tratadas como eje categórico (bar-type) que se decide primero, y eje continuo (tamaño de bloque) que se explora después, dentro de la elección de bar-type. Tres argumentos, no uno:

1. **Efecto de tamaño de muestra inseparable del efecto de representación** (`https://www.mql5.com/en/articles/23310`, ya citado en §1.2) — comparar 1m contra 250t en la misma tabla de métricas confunde "cuántos bloques genera esta resolución hoy" con "qué tan buena es la zona".
2. **Propiedades estadísticas distintas por diseño**: la literatura de barras alternativas (López de Prado, resumida en `https://hudsonthames.org/machine-learning-trading-essentials-part-1-financial-data-structures/`) argumenta que las barras dirigidas por evento (tick/volumen/dólar) tienen menor autocorrelación serial y retornos más cercanos a gaussianos que las barras de tiempo fijo, precisamente PORQUE capturan contenido informativo comparable en vez de duración de reloj comparable — son ejes con propiedades estadísticas de fondo distintas (heterocedasticidad vs. homocedasticidad, `https://www.quantbeckman.com/p/what-are-your-bars-hiding-from-you`), no dos puntos en la misma escala.
3. **Hecho nuevo, verificado en el código del kernel, que nadie había señalado todavía**: el bucket horario contra el que se compara el percentil histórico (`time_bucket_minutes`, default 30) está anclado SIEMPRE a tiempo de reloj — `session_relative_bucket()` en `edgelab/bridge/indicators/avolclusterpoi.py:52-60` calcula el bucket a partir de `block_end_ns` (timestamp real) y `session_begin_ns`, independientemente de si el bloque vino de velas de tiempo o de ticks. Es decir: cambiar `WindowBars` de minutos a N-ticks cambia CUÁNTOS eventos se agrupan antes de calcular el score de un bloque, pero NO cambia que la comparación "¿es esto anómalo para este horario?" siga siendo de reloj. Eso es una decisión de diseño razonable (encaja con la estacionalidad intradiaria en U del volumen documentada en `https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0165057`), pero tiene una consecuencia que ninguna de las 5 métricas de Antigravity contempla: en barras de N-ticks, la NY open produce muchos bloques por bucket de 30 minutos y la sesión asiática produce pocos — la **profundidad de historial por bucket** (`min_samples_per_bucket=20` en el kernel) se llena a velocidades distintas según hora del día Y según resolución, de forma sistemática. Esto es un segundo efecto de tamaño de muestra dependiente de resolución, más sutil que el de §1.2 (ahí era "bloques por sesión"; acá es "bloques por bucket horario"), y específico de esta arquitectura de kernel — hay que reportarlo aparte, no mezclado con frecuencia operativa.

Consecuencia práctica: primero se decide bar-type con un criterio estadístico target-free e independiente de las 5 métricas de Antigravity (estacionariedad/homocedasticidad de la serie de volumen-por-bloque — exactamente el criterio que la literatura de López de Prado usa para elegir tipo de barra, y que no requiere P&L). Recién después, DENTRO del bar-type elegido, se corre el test de meseta 2-D para el tamaño de bloque. Nunca se arma una sola tabla donde "1 minuto" compite fila contra fila con "250 ticks" en las 5 métricas crudas.

### 2.4 Split de sesiones — sin esto, elegir y confirmar son el mismo dato

Precedente directo y ya congelado en este repo para una campaña hermana: `docs/research/ESTADO_BT2_ABSORPTION_2026-08-24.md` — universo de 152 sesiones, split **133/19 congelado antes de abrir outcomes** (`specs/bt2_absorption_gate1_split_v1.json`, intersección 0). El mismo mecanismo aplica acá aunque no haya outcomes de por medio: si las 5 métricas (o las corregidas) se calculan y el "ganador" se elige sobre las mismas sesiones, es double-dipping (§2.2) sin necesidad de mirar P&L.

Fix: **SELECCIÓN (S)** y **CONFIRMACIÓN (C)**, disjuntas, congeladas por escrito en un spec ANTES de calcular ninguna métrica — mismo patrón que `bt2_absorption_gate1_split_v1.json`, estratificado por tercil de volatilidad y por mes/contrato para que ningún régimen quede enteramente de un solo lado. El score estructural y el criterio de selección en cascada (§3.4) se calculan y se declaran ganadores en S; en C sólo se **re-chequea** que sigan pasando los mismos gates (pass/fail, no re-optimizar) — si fallan en C, la resolución queda `SIN EFECTO ESTRUCTURAL CONFIRMADO`, no se rescata con una métrica nueva inventada post-hoc.

---

## 3. Protocolo mejorado — target-free, cero P&L

### 3.0 Objeto y población (regla de `CLAUDE.md`: enumerar el event-space antes de congelar)

Objeto medido: **creación de zona** (`event_type in {AT_PRICE_CREATED, ZONE_CREATED}` del kernel), sobre GC, target-free, sin cruce con ningún otro indicador. Familias enumeradas y explícitamente NO medidas en esta campaña: aproximación, primer toque, toque n-ésimo, invalidación, expiración, confluencia, estado continuo. Justificación de por qué creación y no estado continuo: la pregunta de Nico es "qué resolución produce OBJETOS de mejor calidad estructural", que es una pregunta sobre el evento de nacimiento del objeto, no sobre cuánto tiempo pasa activo un objeto ya nacido (eso sería la pregunta de un protocolo distinto, de estado, con más potencia estadística pero que responde otra cosa). Cómo se refutaría esta elección: si al correr el protocolo la métrica de aislamiento/lifecycle (§1.3 corregida) muestra que la calidad de una zona depende fuerte de su historia de vida y no de su creación, hay que reabrir esta decisión y medir estado en vez de/además de creación.

### 3.1 Eje A — bar-type (decidir primero, target-free, sin las 5 métricas)

Candidatos: `time:{1m, 3m, 5m}` vs. `tick:{lista derivada, no arbitraria}`.

Los candidatos de ticks NO se eligen a mano (25t, 50t, 100t "porque suenan bien" sería exactamente el tipo de elección sin justificación escrita que `CLAUDE.md` prohíbe para poblaciones). Se derivan de una medición previa, 100% target-free y sin outcomes: distribución empírica de ticks/minuto por sesión en el universo S (paso 0 del harness) — de ahí se toman 3-4 tamaños que abarquen el mismo orden de magnitud de "duración típica de bloque" que los candidatos de tiempo, PERO variados independientemente después (no en diagonal — ver §1.5/§3.2).

Criterio de decisión del eje A (estadístico, sin P&L, tomado de la justificación de barras alternativas de López de Prado): para cada bar-type candidato, sobre la serie de "volumen total del bloque" a lo largo de una sesión:

- Autocorrelación serial (lag-1) del volumen por bloque — más baja es mejor (indica que cada bloque aporta contenido menos redundante).
- Homocedasticidad: razón de varianza entre el primer y el último tercio de la sesión (más cerca de 1 es mejor — controla el efecto ya documentado en §2.3.3 de bloques que se acumulan a velocidades muy distintas según hora).
- CV de "bloques por sesión" entre sesiones (más bajo es mejor — bloques de tiempo fijo dan CV≈0 por construcción; se reporta igual, como referencia, no como criterio que favorezca a barras de tiempo por default).

No hay ranking ponderado acá tampoco: se reporta el landscape completo de los tres estadísticos para cada bar-type candidato, y bar-type se decide por el mismo criterio de cascada de §3.4 adaptado (plateau + gates), no por un promedio ponderado inventado.

### 3.2 Eje B — tamaño de bloque dentro del bar-type elegido (grilla 2-D, plateau)

Dentro del bar-type ganador de §3.1, variar **de forma independiente**:

- tamaño de bloque (minutos si ganó tiempo; ticks si ganó tick-bars) — grilla de al menos 5 valores.
- `detection_percentile` y `median_multiplier` del kernel — al menos 3 valores cada uno, cruzados con tamaño de bloque (grilla 2-D real, nunca la diagonal "reescalar `WindowBars` para mantener minutos de reloj constantes" — esa diagonal es precisamente la cresta colineal de §1.5).

### 3.3 El nulo target-free (nuevo, no existe hoy en el repo)

**Placebo de permutación de volumen intra-bloque.** Para cada bloque real ya construido (mismo bloque que ve el detector real), se permuta la asignación `tick → volumen` entre los ticks activos del bloque, preservando exactamente: conjunto de ticks activos, multiset de volúmenes por tick, volumen total del bloque. Se destruye exactamente lo que se prueba — la contigüidad espacial del volumen — sin tocar nada de precio, dirección ni P&L. El historial usado para el umbral de percentil (`history_scores`, construido por `SessionProfile` a partir de sesiones completas reales) **no se toca** — solo se permuta el bloque evaluado, para evitar que el placebo termine comparándose contra un umbral también placebo (lo que ocultaría el efecto). K repeticiones por bloque por sesión (K=200, tomando la práctica del permutation test citado en `https://www.mql5.com/en/articles/23310`).

Salida del placebo, por config: tasa de bloques placebo que igual pasan el umbral de percentil real, y distribución placebo de densidad/aislamiento. El contraste real-vs-placebo (pareado por sesión, nunca `sqrt(se1²+se2²)` — misma regla que F2.7-F2.10) da el "excedente estructural" de cada métrica, **con su propio MDE publicado** (regla permanente de `CLAUDE.md`: "todo nulo publica su MDE, y todo efecto se mide en dos canales" — acá el canal direccional es "más denso/más aislado que placebo" y el no-direccional es "distinto de placebo en cualquier sentido").

### 3.4 Métricas exactas por config (las 5 corregidas + el excedente sobre placebo)

Para cada config `(bar-type, tamaño de bloque, percentile, multiplier)`, calculadas sobre S:

1. **Espesor**: mediana + IQR del ancho de zona en ticks, PAREADO con `target_free_fingerprint` (digest de sesiones+eventos, patrón de `tools/bt2_absorption_param_sweep.py:374`) contra la config vecina más cercana en la grilla — un espesor "estable" con fingerprint distinto no cuenta como estable.
2. **Frecuencia normalizada**: zonas por 100 bloques evaluados (no por sesión cruda) + zonas/sesión cruda solo como referencia descriptiva.
3. **Aislamiento sobre lifecycle completo**: gap mínimo en ticks y en tiempo entre zonas, medido sobre la ventana `creación→expiración` (`max_age_bars`), no solo en el instante de creación.
4. **Estabilidad**: CV de (1)-(3) entre terciles de volatilidad (misma partición que usa la campaña HFTZones-ES vigente) + estabilidad bajo bootstrap de sesiones (Ben-Hur/Elisseeff/Guyon).
5. **Meseta**: sobre la grilla 2-D de §3.2 — plateau pasa si (1)-(3) varían menos de un umbral relativo pre-declarado (ej. ±15%) simultáneamente en AMBOS ejes de la grilla en el vecindario de la config candidata, nunca en uno solo.
6. **Excedente sobre placebo** (nuevo, §3.3): diferencia pareada por sesión real-vs-placebo en (1)-(3), con IC y MDE.

### 3.5 Split y orden de ejecución

`specs/avolclusterpoi_resolution_split_v1.json` (a crear en el commit A, antes de calcular nada): universo pre-holdout disponible para GC, split S/C estratificado por tercil de volatilidad y por contrato/mes, intersección 0, mismo espíritu que `specs/bt2_absorption_gate1_split_v1.json`. Todo lo de §3.1-§3.4 se corre y se decide sobre S. Sobre C solo se re-chequea pass/fail de los gates de §3.6 para el/los ganador(es) de S — nunca se re-optimiza ahí.

### 3.6 Criterio de selección — declarado ahora, mecánico después

Cascada de eliminación, no score ponderado (un promedio ponderado sería otro camino bifurcado más — §2.2):

1. Eliminar configs que no pasan el test de meseta (§3.4.5) — no robustas.
2. Eliminar configs cuyo excedente sobre placebo en densidad Y aislamiento no despeja su propio MDE (§3.4.6) — no hay señal estructural detectable por encima de ruido de asignación.
3. Entre las sobrevivientes, eliminar las que caen fuera de las bandas de negocio declaradas de antemano (2-6 ticks de espesor, 2-6 zonas/sesión normalizada) — restricciones operativas, no métricas a optimizar.
4. Entre lo que quede (idealmente ≤3 candidatas), rankear por menor CV de estabilidad (§3.4.4, entre terciles Y bootstrap). Si hay empate, **se reportan todas las empatadas como viables** — no se inventa un desempate post-hoc.
5. Confirmar en C: recalcular (1)-(3) para el/los ganador(es) de S y verificar que sigan pasando los gates 1-3 en C. Si no pasan, la resolución queda `SIN EFECTO ESTRUCTURAL CONFIRMADO, split C`, no se rescata.

### 3.7 Qué hace falta escribir/generalizar (verificado en código, no supuesto)

- **Kernel (`edgelab/bridge/indicators/avolclusterpoi.py`): nada.** Ya es agnóstico a unidad de barra — consume `cells` armadas por el caller. `session_relative_bucket()` funciona igual con timestamps de barras de tiempo o de ticks (§2.3.3).
- **Bar builder (`edgelab/bridge/bars.py`): nada nuevo.** `build_tick_bars` ya existe, con el reinicio por sesión ya corregido (`TICKBAR-001`).
- **Falta, genuinamente nuevo**:
  - Un harness de orquestación análogo a `diag/tasa_senales/avolcluster_tick_formal.py` pero parametrizado por bar-type y tamaño de bloque en vez de hardcodear `build_time_bars(..., minutes=1)`.
  - El generador de placebo de permutación intra-bloque de §3.3 (no existe ninguna versión reusable — `edgelab/research/nulls.py` es de outcomes, prohibido transportar entre familias por `CLAUDE.md`).
  - El logger de métricas/lineage con los campos ATJ-15 (`n_universe/n_available/.../population_id/eligibility_rule/seed/schema_version/run_id`) y etiqueta epistémica ATJ-16 por afirmación — mismo estándar que `docs/research_funnel_playbook.md` exige para cualquier barrido nuevo.
  - El spec de split `avolclusterpoi_resolution_split_v1.json` (§3.5).
  - Medición previa (paso 0, §3.1) de ticks/minuto por sesión para derivar los candidatos de tick-size sin elegirlos a mano.

---

## 4. Recomendación concreta — qué correr primero

**El experimento mínimo que responde la pregunta de Nico sin gastar de más**:

1. Medir la distribución de ticks/minuto por sesión sobre ~15-20 sesiones pre-holdout de GC ya disponibles (paso 0 de §3.1) — un script chico, sin tocar el kernel, target-free puro.
2. Con eso, decidir el **eje A (bar-type)** con el criterio estadístico de §3.1 (autocorrelación/homocedasticidad/CV de bloques-por-sesión) sobre esas mismas 15-20 sesiones — esto solo ya responde la pregunta más cara de Nico ("¿tiempo o ticks?") sin haber tocado todavía ninguna de las 5 métricas de Antigravity ni el placebo.
3. Recién con el bar-type resuelto, correr el plateau test 2-D (§3.2) sobre 3-5 tamaños de bloque × 3 combinaciones de `detection_percentile`/`median_multiplier`, más el placebo de permutación (§3.3), sobre el split S completo.
4. Dejar la confirmación en C, y el barrido fino de espesor/aislamiento con fingerprint completo, para una segunda pasada — no hace falta correrlo junto con el paso 3 para tener una respuesta accionable.

**Qué dejar para después, explícitamente**: el barrido cruzado de más de 2 parámetros del kernel (`max_gap_ticks`, `min_cluster_ticks`, `lookback_sessions`) — eso es optimización fina de un detector ya elegido, no la pregunta de resolución que Nico hizo, y correrlo ahora sería exactamente el tipo de barrido sin manifiesto que el STOP de `CLAUDE.md` reserva para campañas de retorno (acá no hay P&L, pero el mismo principio de "no ampliar el espacio de búsqueda sin necesidad" aplica, y F9 está pausada por la misma razón para indicadores nuevos).

---

## 5. Justificación económica

Este protocolo no mide edge ni promete rentabilidad — es diseño de instrumento. Su valor económico es indirecto: si `aVolClusterPOI` corre hoy sobre una unidad de barra (M1) cuya relación con `WindowBars` cambia de significado según hora del día (10 minutos de reloj en NY open vs. 10 minutos de reloj en sesión asiática, que son regímenes de liquidez completamente distintos), cualquier campaña formal posterior que use ese detector hereda esa ambigüedad sin saberlo — un resultado positivo o negativo de esa campaña quedaría contaminado por una elección de resolución no examinada, y no se podría distinguir si "no hay edge" significa "no hay edge" o "se midió con la unidad de barra equivocada para ese horario". Resolver esto ahora, target-free y barato (sin tocar el kernel, reusando `build_tick_bars` ya existente), evita gastar presupuesto de multiplicidad de una futura campaña con P&L en descartar una resolución mal elegida.

## 6. Cómo podría refutarse este protocolo

- Si el criterio de bar-type de §3.1 (autocorrelación/homocedasticidad) da resultados inestables entre sub-muestras de sesiones (falla su propio test de estabilidad, §3.4.4 aplicado al eje A), el protocolo no tiene una forma target-free de decidir el eje A y hay que reconocer eso explícitamente en vez de forzar una elección.
- Si el placebo de permutación intra-bloque (§3.3) resulta indistinguible del real en TODAS las configs de la grilla, la conclusión correcta no es "el placebo está mal diseñado" — es que, con las herramientas target-free disponibles, no hay forma de distinguir estructura real de ruido de asignación en este objeto, y hay que decirlo así, no inventar una sexta métrica hasta que algo separe del placebo (la misma disciplina que `docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md` aplicó cuando el control sin zona dio casi lo mismo que el objeto real: se cerró la hipótesis, no se buscó una séptima métrica).
- Si al medir aislamiento sobre lifecycle completo (§3.4.3) aparece que la calidad de una zona depende mucho más de su historia de vida que de su creación, la elección de objeto de §3.0 (creación, no estado) queda refutada y hay que reabrir esa decisión antes de seguir.
- Si el split S/C (§3.5) no alcanza sesiones suficientes por tercil de volatilidad para tener MDE razonable en el placebo, el protocolo entero queda bloqueado por potencia — igual que la familia HFTZones-ES hoy, "el límite es N" — y hay que declararlo `SIN POTENCIA, NO CERRADA`, no forzar una conclusión con lo que hay.

---

**Aporte al referente**: no reduce todavía la distancia a un edge neto — es protocolo de diseño de instrumento, cero P&L, cero holdout tocado. El aporte es evitar que la próxima medición formal sobre `aVolClusterPOI` (la única segunda familia viva después del cierre de BigTrap2-imán) herede una elección de resolución de barra sin examinar, con las dos trampas que ya costaron tiempo en este proyecto — mirar conteo/geometría agregada en vez de fingerprint completo, y confundir una cresta colineal con una meseta — ya nombradas y con su fix escrito antes de que se corra un solo bloque.

---

