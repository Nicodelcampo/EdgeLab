# KAGGLE — Política de ejecución scatter/gather multi-kernel (V1.1, 2026-08-31)

**Estado:** `POLICY_ADOPTED_NOT_YET_IMPLEMENTED`.
**Decisión de Nico (chat Notion AI, 2026-08-31 ~15:05 ART, verbatim):**
*"con todos los procesos que tengo pensado correr y encima serán de alta complejidad
creo que esto habrá que hacerlo si o si"* — ante la propuesta de partir la corrida de
Gate 1 en N kernels worker + 1 kernel de agregación, la respuesta es que el patrón
multi-kernel se adopta **como patrón del proyecto**, no como excepción de una corrida.

**V1.1 (mismo día, ~15:08 ART):** a pedido de Nico ("¿cuántas VM te presta Kaggle?
porque incluso podríamos dividir los contratos en partes") se agregan: §4.1 con los
límites documentados de la plataforma y su estado epistémico, y §7 con la factibilidad
de subdividir contratos en bloques de sesiones (shard sub-contrato).

**Relación con la política existente** (`docs/research/KAGGLE_LAUNCHER_PARALLELISM_POLICY_V1_2026-08-30.md`):
aquella regula el paralelismo DENTRO de una VM (thread pool de subprocesos en el
lanzador, fail-closed). Esta regula el paralelismo ENTRE VMs. Las dos componen: un
kernel worker puede seguir usando su pool de subprocesos adentro.

## 1. El patrón

**Scatter:** N kernels worker, uno por shard (para Gate 1 NQ: shard = contrato; para
la campaña SL/TP/BE: shard = contrato o slice de la grilla; para el censo P-44:
shard = activo/contrato). Cada worker, en su propia VM aislada:

1. clone parcial al commit pineado + verificación de HEAD (speed lever 3, inalterado);
2. **preflight físico propio** (el preflight es barato — hashing en streaming; correrlo
   en cada worker no cuesta nada y convierte "todo corrió verificado" en N afirmaciones
   independientes en vez de una);
3. cómputo del shard con las mismas puertas fail-closed de siempre;
4. escritura atómica de DOS artefactos: el artefacto de datos del shard
   (stats/parquet) y un **manifiesto parcial** (ver §3).

**Gather:** 1 kernel de agregación que:

1. descubre los N artefactos parciales (como datasets de Kaggle o outputs de kernel
   adjuntos — la mecánica exacta se fija en la primera implementación);
2. **re-verifica los N manifiestos parciales y se niega a agregar si falta alguno o
   alguno no calza** (fail-closed: agregar sobre un conjunto incompleto es el error
   más barato de cometer y el más caro de interpretar);
3. agrega y emite el artefacto final + el manifiesto final (§3).

## 2. Determinismo obligatorio por shard

- Las semillas se derivan de la **clave del shard**, nunca del reloj ni del id del
  worker ni del orden de ejecución. (Gate 1 ya cumple: `SEED + i*10000` por índice de
  contrato.)
- La agregación es sobre archivos, orden-independiente.
- Consecuencia medible y exigible: **una corrida scatter/gather y una corrida mono-kernel
  del mismo commit deben producir artefactos finales idénticos.** Esa igualdad es el
  test de aceptación del patrón en su primera implementación, no una aspiración.

## 3. Cadena de evidencia multi-kernel (la parte que no se improvisa)

Cada manifiesto parcial declara: `spec_sha256`, `frozen_commit` (o pin equivalente),
hashes de todos los inputs tocados, la clave del shard, el **kernel version id** de la
VM que corrió, timestamps, y el sha256 del artefacto de datos que acompaña.

El manifiesto final registra: los N hashes de manifiestos parciales (lista completa,
no resumen), los N kernel version ids, y las mismas ligaduras de spec/commit/inputs.
"Todo corrió con el código pineado" pasa de ser UNA afirmación a N+1 afirmaciones
verificables — y el agregador falla cerrado si cualquiera no reproduce.

**Semántica de tokens:** un token de ejecución (ej. `AUTHORIZE_RUN_BT2A_NQ_GATE1_V1`)
cubre el scatter+gather como **una sola corrida lógica** sobre el mismo spec congelado
y el mismo commit. Lanzar N workers no son N autorizaciones; pero cambiar de commit o
de spec entre workers sí invalida la corrida entera (el gather lo detecta por hash y
aborta).

## 4. Lo que se mide antes de la primera implementación (no se asume)

1. **Límite de sesiones concurrentes de la cuenta** de Kaggle (vía API; ver §4.1 —
   los números documentados existen pero el de TU cuenta lo manda el mensaje de error
   de la API; se mide antes de diseñar encima).
2. Tiempo por shard estimado desde la corrida mono-kernel de referencia (la primera
   corrida exitosa de Gate 1 fija la línea base: duración por contrato, pico de
   memoria por worker — marcadores `MemAvailable` ya instrumentados).
3. Mecánica de handoff (dataset por worker vs. kernel outputs adjuntos) — se elige en
   la primera implementación y queda escrita acá.

### 4.1. Límites documentados de la plataforma (V1.1) — con estado epistémico

Fuentes: documentación oficial de Notebooks (kaggle.com/docs/notebooks) y posts de
staff/comunidad. **Nada de esto está medido contra la cuenta de Nico todavía.**

- **Recursos por VM** (doc oficial): CPU = 4 cores / 30 GB RAM; T4x2 y P100 = 29 GB RAM;
  **TPU 1VM = 96 cores / 330 GB RAM** (una VM TPU usada como nodo CPU puro — opción
  real para un mono-kernel gordo, pero gasta cuota TPU: ~20 h/semana).
- **Runtime por sesión** (doc oficial): 12 h CPU/GPU (subió de 9 h en 2024), 9 h TPU.
- **Concurrencia**: doc/comunidad — GPU: 1 sesión interactiva + 2 en batch (post de
  staff). CPU: respuestas viejas dicen "hasta 10 kernels CPU en commit", pero un error
  de producto de 2024 reporta **"Maximum batch CPU session count of 5 reached"** —
  hipótesis de trabajo: **5 sesiones CPU batch concurrentes** hasta medir.
- **Cuotas semanales**: GPU ~30 h, TPU ~20 h (documentado en múltiples fuentes); CPU
  no tiene cuota semanal documentada, solo el límite de 12 h por sesión.
- **Disco**: 20 GB auto-guardados en /kaggle/working + scratchpad no persistente.

Traducción al diseño de Gate 1 (5 contratos): 5 workers + 1 gather **entran en la
hipótesis de 5 slots** (el gather encola hasta que termina el primer worker). No hace
falta subdividir para que Gate 1 quepa en concurrencia.

## 5. Aislamiento de fallos (la razón operativa principal)

Con mono-kernel, un contrato que muere tira la corrida entera. Con scatter/gather: se
re-corre solo ese shard; el gather no corre hasta que los N manifiestos parciales
existen y verifican. En campañas de alta complejidad (SL/TP/BE: 384 primarias con
bootstrap de 10.000 réplicas por celda) esto deja de ser conveniencia y pasa a ser la
diferencia entre iterar y no iterar.

## 6. Aplicación prevista, en orden

1. **Gate 1 NQ (ahora):** solo si la corrida mono-kernel actual (v7, con el fix de
   memoria `8830b74e` pineado) demuestra que hace falta. Si v7 pasa en tiempo razonable,
   Gate 1 no migra — el patrón no se estrena donde no hace falta.
2. **SL/TP/BE NQ** (`BT2A_NQ_SLTP_BREAKEVEN_DESIGN_V1_2026-08-31.md`, condicionada a
   Gate 1 SUPPORTED): primera candidata real al patrón — 384 primarias, el cómputo
   pesado de verdad.
3. **Censo P-44 multi-instrumento** (56 contratos): scatter natural por activo.
4. Cualquier entrenamiento de modelos (si alguna vez): mismo patrón, con la cuota de
   GPU/TPU contada aparte.

## 7. Subdividir contratos en partes (V1.1, pedido de Nico) — factible, con dos acoples

Idea: shard = (contrato, bloque de sesiones completas), p.ej. 5 contratos × 2-4
bloques = 10-20 workers.

**Por qué es estadísticamente transparente:** la unidad de inferencia es la sesión CME
y los `SessionCellArmStat` son filas aditivas por (contrato, sesión, celda, brazo) —
un bloque de sesiones produce exactamente las filas de sus sesiones; el gather
concatena. Ninguna estadística cambia por dónde se cortó el contrato.

**Los dos puntos de acoplamiento (resueltos, no gratis):**

1. **Quintile edges por contrato.** Se computan sobre TODOS los eventos K_ABS del
   contrato; un worker de un bloque no puede recomputarlos sin leer el contrato
   entero. Solución: pinearlos como artefacto chico (4 floats × 5 contratos = 20
   números) con hash verificado por cada worker — los edges son una función
   determinista del dato congelado, pinearlos es equivalente a computarlos y además
   remueve un grado de libertad de runtime.
2. **Carga por ventana de ticks.** Cada worker lee solo su bloque vía filtros pyarrow
   sobre `ts_ns` (el parquet canónico es contiguo por sesión dentro del contrato).
   Los pools N_RAND viven dentro de (sesión, fase), así que ningún estrato cruza el
   corte. La mediana móvil de volatilidad es intra-sesión — no necesita ticks de
   otras sesiones.

**Cuándo rinde:** con la hipótesis de 5 slots concurrentes, subdividir NO compra
velocidad (10-20 workers encolan en tandas de 5); compra **granularidad de fallos** y
**headroom de RAM** por worker. Si la medición de §4.1 da ≥10 slots, recién ahí
subdividir compra wall-clock. La decisión se toma con el límite medido en la mano.
