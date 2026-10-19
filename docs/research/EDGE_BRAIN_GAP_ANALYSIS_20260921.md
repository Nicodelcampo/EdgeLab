# Edge Brain — qué tiene, qué le falta y si se puede orquestar

> 2026-09-21. Pedido de Nico: revisar el Brain implementado en EdgeLab, compararlo con `CerebroSSRN`
> (los datos que le interesan) y `CerebroJLP` (la mejor estructura), determinar qué le falta, y verificar que
> se pueda orquestar el Brain y lanzar análisis en Kaggle.
> Todo lo de abajo se **ejecutó o midió** salvo lo marcado *no verificado*. Holdout intacto; nada abre outcomes.

## 0. En una mirada

| | |
| :-- | :-- |
| **Lo que hay** | Un **ledger de conocimiento** riguroso: registro tipado hash-encadenado, 35 esquemas, cascada de invalidación, máscara de cobertura, compuertas de elegibilidad y triangulación, política de modelos, hipocampo experimental, atlas de mediciones, y un cortex bibliográfico que verifica el corpus SSRN real (`VERIFIED_COMPLETE`: 401 papers, 24.340 pasajes) |
| **Lo que es** | Un **validador pasivo**. No busca semánticamente, no razona, no ejecuta nada: cero referencias a Kaggle, modelos o subprocesos en `edgelab/edge_brain/` |
| **Orquestación** | **Sí se puede, hoy, por mí** (verificado de punta a punta en Kaggle), pero **no está en el Brain**: no hay código que abra un episodio, lance el análisis, verifique la salida y asiente lo aprendido |
| **Brechas mayores** | 1) búsqueda semántica, 2) capa de razonamiento con el grafo en contexto, 3) el bucle proponer→ejecutar→verificar→aprender, 4) el corpus no está en Kaggle, 5) el Brain vive repartido en 3 ramas sin integrar |

## 1. Qué se ejecutó

| Prueba | Resultado |
| :-- | :-- |
| Tests del Brain (rama del PR #52), 52 | 49 pasan; **3 fallaban por un defecto real** (abajo) → 52 con el arreglo |
| `ssrn_brain_cli audit` sobre `C:\$ACerebroSSRN` | `VERIFIED_COMPLETE`: 401 papers, 401 extracciones, 3.254 chunks, 24.340 pasajes, 771 hallazgos, grafo 2.488 nodos / 3.476 aristas, 1.331 relaciones sin destino (el resolutor las materializa: 3.819 nodos / 5.082 aristas) |
| `ssrn_brain_cli search`, 6 consultas | 6 pasajes por consulta; **relevantes en inglés, ruido en español** (§3.1) |
| **Kernel de orquestación en Kaggle** (`notebooks/kaggle/orchestration_smoke/`) | Creado, ejecutado (4 CPU, Python 3.12.13, pyarrow 24), montó 2 datasets privados, **0 filas leídas**, salida recuperada. Evidencia: `artifacts/audit/orchestration_smoke_20260921.json` |
| Auditoría de holdout del lado del servidor | 5/5 parquets de `edgelab-ticks-6b-preholdout` con `ts_max < 1782856800000000000` (solo pies de parquet). El de `09-26` llega a **3,6 s antes** de la frontera |

**Defecto encontrado y arreglado.** `with sqlite3.connect(...) as con:` **no cierra la conexión**, solo confirma la transacción.
El cortex dejaba abiertas las conexiones de `audit` y `search_passages`; en Linux se libera al recolectar, en
Windows el archivo queda bloqueado (`WinError 32`) y fallaban 3 tests. Corregido con `contextlib.closing` en la rama
local `fix/brain-close-sqlite-connections-20260921` (sobre la del PR #52; **no se empujó**: es de otra línea), con un
test de regresión portable que espía `sqlite3.connect` y **falla sin el arreglo**.

**Un dato del camino de Kaggle:** los datasets se montan en `/kaggle/input/datasets/<owner>/<slug>/`, no en
`/kaggle/input/<slug>/`. Cualquier kernel que asuma la ruta vieja falla.

## 2. Qué aporta cada cerebro

| | `CerebroSSRN` | `CerebroJLP` | Brain de EdgeLab |
| :-- | :-- | :-- | :-- |
| **Es** | los **datos**: 401 papers, 24.340 pasajes con embeddings e5, grafo, 771 hallazgos, ledger histórico | la **estructura**: pipeline por fases con checkpoint, adjudicación, entregas verificables, runtime empaquetado | un **ledger con gobierno**: autoridad, procedencia, invalidación, cobertura |
| Extracción | LLM lee el corpus una vez | ídem, con gold set y auditoría | importa lo ya extraído como `LLM_EXTRACTED_CONCEPT` sin verificar |
| Recuperación | **RAG cruzado idioma** (`consultar.py`, e5-small) | ídem + embeddings de nodos | **léxica** (`LIKE`) |
| Grafo | idempotente, 254 comunidades, núcleo de 317 nodos que **entra entero en el contexto** | ídem + `grafo_v4` con adjudicación | proyección determinista; sin comunidades ni núcleo |
| Razonamiento | `CEREBRO_SSRN.md`: crítico cuantitativo escéptico | reglas de razonamiento por fase | política de modelos (independencia, no evidencia) |
| Aprendizaje | `LEDGER_EXPERIMENTOS.md`: propuesta→test→resultado→lección | — | hipocampo (clases) **sin bucle que lo alimente** |

## 3. Qué le falta al Brain de EdgeLab (con evidencia)

### 3.1 Búsqueda semántica — ALTA
`search_passages` arma un `WHERE lower(texto) LIKE %término%` por cada palabra y suma coincidencias. Sin IDF, sin
palabras vacías, sin diversificar por documento. Medido: «order flow imbalance» devuelve pasajes de *order book
dynamics* (bien); «desequilibrio del flujo de ordenes» devuelve *A Journey into the Dark Arts…* y *A Practical Guide
to Quantitative Portfolio Trading* (coincide con «de», «el»); y para «deflated sharpe ratio» **5 de 7 pasajes son del
mismo paper**. Los embeddings (`Normalizado/embeddings.npy`, 24.340 pasajes) **ya existen** y no se usan. `CerebroSSRN`
los usaba para consultar en español sobre un corpus en inglés.

### 3.2 Capa de razonamiento con el grafo en contexto — ALTA
El principio 5 de JLP («el grafo final ES el contexto») no está adoptado. `context_memory` empaqueta pasajes con
presupuesto de tokens, pero no hay: núcleo del grafo, resúmenes de comunidades, «barro empírico» (los 771 hallazgos
consultables por mercado) ni las reglas de razonamiento escéptico. El Brain **guarda** conocimiento pero no lo pone a
razonar.

### 3.3 El bucle proponer → ejecutar → verificar → aprender — ALTA
Hoy nada ejecuta análisis desde el Brain. Lo que sí está: las clases del hipocampo (`AnalysisEpisode`, `Expectation`,
`FailureEvent`, `RepairAction`, `LessonCandidate`) y el formato del `LEDGER_EXPERIMENTOS.md`. Falta el **corredor de
episodios**:
1. abrir episodio + expectativa desde un `measurement_contract` pre-registrado;
2. materializar el kernel (metadatos + entrypoint versionado) y fijar **la versión de cada dataset de Kaggle**;
3. lanzar, monitorear, recuperar;
4. verificar la salida (hash, esquema, **auditoría de holdout**, sin filas de outcomes);
5. asentar paso/fallo/éxito/lección en el ledger y disparar la cascada de invalidación si corresponde.
Yo puedo hacer los pasos 2-3 a mano (probado); no queda asentado ni verificado por el Brain.

### 3.4 El corpus no está en Kaggle — ALTA (si los análisis viven ahí)
Depende de `EDGELAB_SSRN_CORPUS_ROOT=C:\$ACerebroSSRN`. Un kernel no lo ve. Falta un dataset privado del corpus
(con hashes) y un modo del cortex que lea de `/kaggle/input/datasets/...`. **Ojo con los términos de SSRN** para
redistribuir PDFs, aunque sea privado: subir solo lo derivado (texto normalizado, chunks, embeddings) reduce el
riesgo, pero conviene que lo decida Nico. *No verificado.*

### 3.5 Pipeline de crecimiento — MEDIA
El corpus es un artefacto congelado por hash (`$ACerebroSSRN.rar`). Los scripts que lo construyen (`extract_pdfs`,
`chunk_docs`, `embed_chunks`, `consolidate_concepts`, `build_graph` idempotente, `detect_communities`) viven solo en
`CerebroSSRN\pipeline`. Sin ellos no se pueden agregar papers ni regenerar el grafo desde EdgeLab. Además
`$ASSRNdownloader` (1,1 GB de PDFs) no está enlazado.

### 3.6 Adjudicación de calidad — MEDIA
Todo lo importado es `LLM_EXTRACTED_CONCEPT` / `AUTHOR_REPORTED_RESULT`. No hay medida de **precisión de la
extracción** (gold set) ni flujo de adjudicación humano/Opus por muestra. El resolutor de deuda semántica rechaza
fusionar por similitud (correcto: «market efficiency» vs «inefficiency»), pero deja 1.331 nodos `TARGET_ONLY_UNCLASSIFIED`
sin camino para clasificarlos. `CerebroJLP` tiene `REPORTE_ADJUDICACION.md` y kits de «soldaduras» con verificador de entrega.

### 3.7 Verificación de entregas de trabajadores externos — MEDIA
`model_policy` valida independencia del revisor, pero nada valida que la **salida** de un trabajador (Kaggle, otro
modelo) sea íntegra. JLP lo resolvía con `verificar_entrega_v2.py`.

### 3.8 Hipocampo sin memoria real — MEDIA
Las lecciones de **este** proyecto no están en el ledger: ATJ-01…18 del playbook, los incidentes (`docs/incidents/`),
y lo de hoy —cinco implementaciones de «corredor», la función declarada dos veces que pisaba a la primera, el `vol: null`
que rompía Python y habría contaminado JS con `NaN`, `with sqlite3.connect` sin cerrar, el triaje ULP por lectura—.
Son exactamente `methodological_learning` (intención / medición real / brecha / regla / test). *Cantidad de episodios
actualmente almacenados: no verificada.*

### 3.9 Integración — ALTA
El Brain vive en **tres ramas encadenadas** (#43 base, #46 reconstrucción, #52 cortex SSRN) más el adaptador de la
fábrica (#49), con CI rojo y sin mergear; hay un worktree aparte (`D:\EdgeLab-brain-reconstruct`). «Una única verdad»
también vale acá. Además el lock de `jsonschema` (`requirements/jsonschema-ci.lock`) trae hashes **solo de Linux**
(`rpds-py`): en Windows no se puede instalar con `--require-hashes`.

## 4. Orquestación: qué puedo y qué no

| Capacidad | Estado |
| :-- | :-- |
| Correr las CLIs y tests del Brain | **Sí** (con `jsonschema` instalado a mano en Windows) |
| Crear/ejecutar/leer logs/borrar kernels en Kaggle | **Sí**, verificado |
| Montar datasets privados de EdgeLab y recuperar salida | **Sí**, verificado; ruta `/kaggle/input/datasets/<owner>/<slug>/` |
| Auditar holdout en el servidor sin leer filas | **Sí**, verificado |
| Crear/borrar datasets | **Sí**, verificado |
| Cuota | GPU 30 h, TPU 20 h semanales (no se usan; los análisis son CPU) |
| Que el Brain asiente lo ocurrido y verifique la salida | **No**: falta §3.3 |
| Consultar el Brain desde un kernel | **No**: falta §3.4 |
| Límites que **no probé** | tiempo máximo por sesión, memoria (16 GB típicos), datasets grandes (NQ = 1,1 GB), kernels largos |

## 5. Orden propuesto

1. **Integrar** las tres ramas del Brain en una (§3.9) y aplicar el arreglo de conexiones.
2. **Corredor de episodios** (§3.3): es lo que convierte al Brain en orquestador y lo que hace útil la verificación de hoy.
3. **Búsqueda semántica** con los embeddings existentes (§3.1) y **capa de razonamiento** con el núcleo del grafo (§3.2).
4. **Corpus en Kaggle** (§3.4), tras decidir el tema de los términos de SSRN.
5. **Backfill del hipocampo** con las lecciones del proyecto (§3.8).
6. Adjudicación y pipeline de crecimiento (§3.5-3.7).

**Aporte al referente:** deja medido que el Brain hoy protege el conocimiento pero no lo usa ni lo produce, y que el
eslabón que falta para orquestar análisis en Kaggle con garantías —el corredor de episodios con auditoría de
holdout— es exactamente el que ya se probó a mano con éxito.
