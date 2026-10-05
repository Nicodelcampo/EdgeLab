# Un agente autónomo de descubrimiento de edges bajo un embudo falsacionista: arquitectura en espiral, contraste cruzado y economía de tokens

**Proyecto:** EdgeLab — https://github.com/Nicodelcampo/EdgeLab
**Fecha:** 2026-10-04
**Estado del documento:** especificación de diseño aprobada por secciones (1–4) y completada (5–7); no describe un sistema construido.
**Referente rector:** `docs/NORTH_STAR.md`, sha256 del cuerpo `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.

---

## Resumen

Se propone un agente de investigación autónomo e indefinido cuyo objetivo es reducir la distancia hacia un edge neto, robusto y operable, tal como lo define el referente de EdgeLab. El agente no es un modelo de lenguaje en control de un proceso: es un **orquestador Python determinista** que invoca modelos de lenguaje (LLM) por rol, con entradas y salidas tipadas, dentro de un embudo falsacionista ya existente en el repositorio (EF0–EF5, particiones D0/D1/D2, Edge Brain con ledger encadenado por SHA-256). La contribución de este diseño frente al estado del arte en *alpha mining* con LLM es triple: (i) el LLM propone **familias** de hipótesis con a lo sumo tres parámetros libres y la expansión a millones de celdas es mecánica y sin LLM; (ii) cada ciclo ejecuta un **contraste cruzado** entre avances y descartados, en ambas direcciones, y contra literatura con identificador verificable, antes de cualquier promoción; (iii) la autonomía es total dentro de un perímetro escrito en código, y lo que el código prohíbe (abrir el holdout dos veces, expandir un grid tras ver resultados, reutilizar artefactos stale) no lo decide ningún prompt. Se incluye una revisión de sistemas análogos (R&D-Agent(Q), AQuA, QuantAgent, Alpha-GPT, TradingAgents, AI Scientist, AlphaEvolve) y una evaluación honesta de ventajas y desventajas. Se especifica además la economía de tokens bajo una membresía con ventanas de uso, no bajo una API con factura, y el plan de verificación con pruebas sintéticas.

---

## 1. Introducción

### 1.1 Problema

EdgeLab acumula, al 2026-10-04, más de cuarenta ramas de investigación y un patrón consistente: las hipótesis entran, se miden y mueren. Entre el 30/09 y el 02/10 de 2026 se registraron al menos nueve familias cerradas sin edge (EMA3 multiactivo 0/24, momentum RTY 0/24, VWAP reclaim 0/3, absorción L1 0/3, opening-range 0/3, IPC-ROB 0/23). La única familia viva, EMA 200×500 sobre MGC con TP 400 ticks, sobrevive a un test de cuatro (MCPT p≈0,026) y falla DSR, BH y SPA. El proceso es correcto. El cuello de botella es la **tasa de generación de hipótesis serias** y la **memoria metodológica** entre campañas: cada sesión de trabajo humano o asistido rehace contexto, pierde negativos y a veces reabre lo ya refutado con umbrales vecinos.

### 1.2 Objetivo

Construir un agente que:

1. obtenga el contexto del proyecto por sí mismo (referente, contratos, Edge Brain, negativos, paridad de indicadores, catálogo de datasets);
2. proponga familias de hipótesis fundadas en literatura y en los resultados previos;
3. las pase por el embudo existente, expandidas a miles o millones de variantes en hardware híbrido CPU/GPU (Kaggle);
4. interprete los resultados y decida promover, descartar o derivar;
5. actualice el Edge Brain con reglas de descarte nuevas;
6. corra indefinidamente, sin consulta humana dentro de su perímetro, con uso de tokens proporcional a la utilidad.

### 1.3 Decisiones ya tomadas por el responsable del proyecto

- El agente reemplaza el "OK explícito de Nico" en los gates G0–G4. Esta delegación se formaliza como enmienda al NORTH_STAR (sección 7.3), no como omisión.
- La infraestructura de ejecución es la máquina local operando como servidor 24/7, con Kaggle como acelerador GPU.
- La paridad de los indicadores pendientes la certifica el responsable, fuera del agente. El agente sólo consume indicadores con `parity_exact`.

---

## 2. Estado del arte

### 2.1 Sistemas de descubrimiento automático con LLM en finanzas cuantitativas

**R&D-Agent(Q)** (Li et al., 2025; Microsoft Research y HKUST; NeurIPS 2025) automatiza el ciclo factor–modelo en tres fases: investigación (prompts alineados al objetivo, hipótesis, tareas), desarrollo (agente de código "Co-STEER") y retroalimentación con un planificador *multi-armed bandit*. Reporta hasta 2× el retorno anualizado de bibliotecas clásicas (Alpha158/Alpha360) con 70 % menos factores. Valida por backtest de mercado real y no discute explícitamente fuga de información ni sobreajuste por selección.

**AQuA** (Guo et al., 2026) propone dos pipelines "recursivamente automejorables": descubrimiento de factores mediado por un agente gestor, y desarrollo de modelos por configuración. Cada pipeline conserva registros experimentales para informar propuestas posteriores. Reporta IC ≈ 0,19 en cripto y Sharpe fuera de muestra hasta +2,50 en acciones de EE. UU. Los autores acotan la generalización a sus splits, features y métricas.

**QuantAgent** y **Alpha-GPT** (Wang et al., 2023–2024) usan un lazo interno escritor/juez con base de conocimiento y un lazo externo de prueba en mercado; Alpha-GPT 2.0 pone al humano en el lazo. **TradingAgents** (Xiao et al., 2024) organiza agentes LLM por roles de una mesa de trading. Una revisión reciente (Agentic Quantitative Trading: A Survey, 2026) y la de Springer sobre *LLM-based alpha mining* catalogan decenas de variantes de esta misma idea.

**Hallazgo crítico.** Gençay (2026), en "What survives honest evaluation?", evalúa estrategias descubiertas por LLM sobre 453 acciones y 39 ETF con costos realistas, herramientas cuyo espacio de features excluye el *look-ahead* por construcción, y registro de **cada** evaluación para corregir por el tamaño total de la búsqueda. Resultado: la evaluación honesta certifica los benchmarks pasivos y **rechaza todas las estrategias descubiertas por LLM**, para todos los modelos y presupuestos de búsqueda. Además muestra que las correcciones estadísticas solas no bastan: un oráculo deliberadamente engañoso con Sharpe 35 sobrevivía a los tests tradicionales.

### 2.2 Sistemas generales de descubrimiento automático

**The AI Scientist** (Lu et al., 2024; Sakana AI, Oxford, UBC) genera ideas, escribe código, experimenta, redacta un paper y lo somete a revisión simulada. Evaluaciones independientes (Beel et al., 2025) encuentran resultados mixtos: la parte de generación funciona; la parte de verificación es débil.

**AlphaEvolve** (Novikov et al., 2025; DeepMind) combina un ensamble de LLM (Flash para amplitud, Pro para profundidad) con **evaluadores automáticos** que verifican respuestas dentro de un marco evolutivo. Su éxito en problemas con verificador exacto (multiplicación de matrices, cotas combinatorias, scheduling) se apoya en que el evaluador no es un LLM.

### 2.3 Base estadística

- Bailey y López de Prado (2014), *Deflated Sharpe Ratio*: umbral que crece con el número de pruebas y su dispersión.
- Bailey, Borwein, López de Prado y Zhu (2017), *Probability of Backtest Overfitting* vía CSCV.
- Harvey, Liu y Zhu (2016), *…and the Cross-Section of Expected Returns*: con cientos de factores publicados, un hallazgo nuevo necesita t > 3,0.
- White (2000), *Reality Check*; Hansen (2005), *Superior Predictive Ability*: inferencia sobre el mejor de muchos modelos.
- Masters (2018), *Monte Carlo Permutation Tests* para sistemas de trading.

### 2.4 Síntesis

Los sistemas de 2.1 comparten tres rasgos: el LLM escribe código de factor libremente; la validación es un backtest sobre el que el propio sistema optimiza; y la multiplicidad de la búsqueda rara vez entra en la inferencia. El resultado de Gençay (2026) es, en la práctica, la refutación empírica de ese patrón. AlphaEvolve muestra la alternativa que sí funciona: creatividad del LLM, verificación fuera del LLM. EdgeLab ya tiene el verificador (EF0–EF5, G0–G5, MCPT/PBO/DSR/SPA). Lo que este diseño agrega es el generador disciplinado y la memoria que evita repetir refutaciones.

---

## 3. Método: arquitectura en espiral

### 3.1 Unidad de trabajo

La unidad es la **familia** de hipótesis (contrato `edgelab_hypothesis_v1`, ≤ 3 parámetros libres, `asserts_edge: false`). El LLM nunca ve, propone ni adjudica una celda individual. Esta decisión no es sólo de costo: es la que hace contable la multiplicidad, porque el número efectivo de hipótesis se declara en el preregistro de la familia y no se infiere después.

### 3.2 Máquina de estados por familia

```
CONJECTURED → PREREGISTERED → ELIGIBLE → SCREENED → CONTRASTED
    → ADJUDICATED_{PROMOTE | KILL | DERIVE}
PROMOTE → D1_RUNNING → MULTIPLICITY → ECON → HOLDOUT_OPENED → PAPER → LIVE_CANDIDATE
KILL    → RETIRED (con regla nueva opcional)
DERIVE  → CONJECTURED (radio + 1, parent_id, presupuesto heredado)
```

Correspondencia con el referente: `ELIGIBLE` ≡ G0, `SCREENED`+`CONTRASTED` ≡ G1, `MULTIPLICITY` ≡ G2, `ECON` ≡ G3, `HOLDOUT_OPENED` ≡ G4, `PAPER` ≡ G5. Cada transición es una fila append-only en el ledger del Edge Brain con hash encadenado, y una transacción en `agent_state.db`.

### 3.3 La espiral

Cada vuelta de una familia tiene más radio: más contrastes acumulados, más literatura indexada, más negativos vecinos. Una familia derivada no es una familia nueva: hereda `parent_id`, cuenta contra el presupuesto de multiplicidad del padre y declara qué predicción fallida motivó la derivación. Así la espiral converge o se cierra; no se convierte en búsqueda continua de parámetros, que el contrato prohíbe explícitamente (`forbidden: continuous_period_search, post_hoc_grid_expansion`).

### 3.4 Contraste cruzado (núcleo metodológico)

Cada hipótesis preregistrada declara dos campos nuevos obligatorios:

- `prediction`: una consecuencia observable adicional si la hipótesis es verdadera ("si el reclaim de VWAP tiene información, la tasa de continuación tras el reclaim debe exceder la del control emparejado en los tres terciles de volatilidad");
- `refutation`: la observación que la mata.

El orquestador ejecuta tres contrastes antes de adjudicar, los tres sin LLM salvo en caso ambiguo:

1. **Avance → descartados.** La `prediction` se compara estructuralmente (por `location`, `regime`, `trigger`, instrumento, ventana) contra el ledger de familias retiradas. Si una familia retirada ya midió la negación de la predicción con potencia suficiente (MDE registrado), el avance cae a `DERIVE` con la contradicción adjunta.
2. **Descarte → avances vivos.** Un `KILL` nuevo dispara la re-evaluación de toda familia viva que comparta primitivas con la muerta. Si una familia promovida dependía de algo recién refutado, vuelve a `CONTRASTED`.
3. **Literatura.** Búsqueda selectiva sobre el índice local del corpus (401 papers, 24.340 pasajes) y, si no hay cobertura para la `family_id`, hasta *K* búsquedas externas por ciclo restringidas a SSRN, arXiv q-fin y revistas con DOI. El resultado agrega `corroborating_refs` o `contradicting_refs` al expediente. **Un paper nunca promueve**: sólo informa al revisor.

Esto es la aplicación operativa del método hipotético-deductivo: conjetura, predicción deducida, intento de refutación, y revisión de las conjeturas previas a la luz del nuevo resultado.

### 3.5 Perímetro de autonomía

El agente decide solo todo lo anterior, incluido cuándo abrir el holdout de un candidato que pasó G3. El código impide, sin excepción ni prompt:

- abrir el holdout dos veces por candidato (`holdout_guard` existente + registro inmutable);
- leer `trade_date ≥ frontera` fuera de G4;
- ejecutar un registro de candidatos cuyo hash no coincide con el preregistro;
- reutilizar artefactos marcados stale;
- mergear cambios a `edge_validation_contract.md`: el agente puede proponer un PR, no fusionarlo.

---

## 4. Roles LLM, cómputo y persistencia

### 4.1 Contratos de rol

| Rol | Modelo | Entrada | Salida | Nota |
|---|---|---|---|---|
| Proponente | Opus | resumen Edge Brain, registro de paridad, catálogo de datasets, fichas de papers, presupuesto restante | lista de hipótesis v1 + `prediction`, `refutation`, `refs` | sólo primitivas del registro; sin código libre |
| Compilador | sin LLM | hipótesis | `candidate_registry.json` con hash | aquí nacen las celdas |
| Lector de corridas | Haiku | `summary.json`, `survivors.parquet` | tabla por familia, 3 líneas | sin juicio |
| Contraste ambiguo | Opus | dos expedientes | `{refuta: sí/no/insuficiente, cita}` | sólo si el matching estructural no decide |
| Revisor | Opus, sesión nueva | expediente completo | `{decision, reason, new_rule?, variant?}` | independiente del proponente |
| Cronista | Haiku | transiciones del ciclo | ledger, manifiesto con hash del referente, handoff, "Aporte al referente" | plantillas |

Validación de salida contra JSON Schema; un reintento; después `LLM_INVALID_OUTPUT` registrado y el ciclo sigue. El LLM nunca recibe rutas de datos, credenciales ni nada posterior a la frontera del holdout.

### 4.2 Registro de primitivas

El proponente compone `location`, `regime` y `trigger` desde un registro versionado de primitivas ya implementadas en el motor compartido (banco EMA, VWAP de sesión, terciles de volatilidad, y los indicadores del bridge con `parity_exact` certificado: hoy aVolClusterPOI y los que el responsable vaya certificando). Una primitiva nueva es un PR con tests de paridad, no un prompt. Esto elimina la clase de fallo que Gençay (2026) y Beel et al. (2025) documentan: código generado que introduce *look-ahead* o reinterpreta la métrica.

### 4.3 Reglas de descarte emergentes

Si el revisor adjunta `new_rule` a un `KILL`, la regla entra al Edge Brain en estado `PROPOSED`. Se activa cuando dos familias **distintas** la confirman de forma independiente. Una regla activa bloquea en EF0 toda hipótesis que la viole, con cita a las dos familias que la fundaron. Las reglas nunca se borran; se superseden con cadena de invalidación.

### 4.4 Cómputo híbrido

- **Local (CPU de referencia):** EF0, compilador, contraste, gates, tick-exact de finalistas, PBO/DSR/MCPT/SPA.
- **Kaggle (GPU):** EF2 cheap-kill masivo. Un job = un kernel privado autocontenido (plantilla + registro embebido + hash de arrays esperado), `datasetDataSources` = versión inmutable de `edgelab-arrays`, sin internet, 1 h máximo. Polling de estado cada 2 min; descarga de `summary.json` + `survivors.parquet`; verificación de `split_hash` y hash de arrays contra el preregistro. Resultado sin hashes correctos = corrida inválida, registrada, no reintentada a ciegas.
- **Paridad CPU/GPU:** `gpu_parity.py` corre una vez por versión del kernel; sin paridad verde, ningún resultado GPU de esa versión se acepta.
- **Degradación:** si Kaggle no responde o la cuota semanal (30 h) se agotó, EF2 corre local con `backend=cpu`. Mismo contrato, más lento, el embudo no se detiene.
- **Credencial:** `kaggle.json` local en la máquina servidor, fuera de Git, permisos de usuario. El Worker de Notion queda para acceso desde chat.

### 4.5 Persistencia y reanudación

`agent_state.db` (SQLite) con tablas `families`, `jobs`, `llm_calls` (rol, modelo, tokens, hash de entrada y salida), `budget`. Toda transición es una transacción. Al arrancar, el daemon lee el estado y retoma: jobs `RUNNING` se consultan, no se relanzan; llamadas LLM sin respuesta se repiten, idempotentes por hash de entrada. Pérdida máxima ante apagón: un paso.

### 4.6 Loop del daemon

Cada 60 s: (1) recoger jobs remotos terminados; (2) avanzar toda familia cuyo próximo paso no requiere LLM; (3) si hay presupuesto, ejecutar la llamada LLM de mayor valor pendiente; (4) ante límite de uso, cerrar la ventana hasta `reset_at` y seguir sólo con lo numérico; (5) cada *N* ciclos, commit y push de ledger y documentos.

---

## 5. Economía de tokens

### 5.1 Restricción real

El presupuesto es una membresía de Claude con ventanas de uso (5 horas y semanal), no una API facturada por token. Consecuencias de diseño: el LLM es un recurso **intermitente**; el embudo numérico debe progresar sin él; y la métrica a optimizar no es "tokens por día" sino **utilidad por llamada**, donde utilidad = reducción esperada de distancia a un edge según la jerarquía del referente.

### 5.2 Función de valor de una llamada

Cola de prioridad con puntaje `V = U / T`, donde `T` es el costo estimado en tokens (por rol y tamaño de entrada) y `U` el valor ordinal:

| Prioridad | Llamada | Por qué |
|---|---|---|
| 1 | Revisor sobre familia con sobrevivientes en EF2/EF3 | destraba la única ruta hacia G2–G4 |
| 2 | Contraste ambiguo que bloquea una adjudicación | sin él no hay decisión |
| 3 | Proponente, sólo si familias en vuelo < *F_min* | evita inanición del embudo, no "llena por llenar" |
| 4 | Revisor sobre familia sin sobrevivientes (para `new_rule`) | valor diferido: mejora EF0 futuro |
| 5 | Cronista | por lotes, al final de ciclo |

Si familias en vuelo ≥ *F_max*, el proponente no se llama aunque haya presupuesto: proponer más de lo que el cómputo puede matar sólo infla la multiplicidad.

### 5.3 Mecanismos de ahorro

- **Idempotencia por hash de entrada:** misma entrada, misma salida cacheada; nunca se paga dos veces la misma pregunta.
- **Haiku para lo mecánico:** lector y cronista consumen un orden de magnitud menos que Opus por token y representan la mayoría de las llamadas.
- **Resúmenes incrementales del Edge Brain:** el proponente recibe un *delta* desde su última llamada más un resumen estable con hash, no el ledger entero.
- **Índice local de literatura antes de búsqueda externa.**
- **Tope diario configurable** por rol (`max_calls_per_day`) como cinturón de seguridad independiente de la ventana de la membresía.

### 5.4 Comportamiento ante límite

Detección por código de salida y mensaje de `claude -p`; se registra `RATE_LIMITED` con `reset_at` (parseado si está disponible, 60 min por defecto). Durante la ventana cerrada el daemon sigue ejecutando pasos sin LLM y acumula la cola. Al reabrir, se drena por `V` descendente. Ninguna llamada se pierde; se posterga.

---

## 6. Ventajas y desventajas frente al estado del arte

### 6.1 Ventajas

1. **Verificador fuera del LLM** (patrón AlphaEvolve). Toda cifra que promueve o mata sale de código determinista con hash; el LLM aporta conjeturas y lectura, nunca evidencia.
2. **Multiplicidad contable por construcción.** El preregistro de familia declara el número efectivo de hipótesis antes de ver datos; Gençay (2026) muestra que sin registrar cada evaluación la corrección es ilusoria. Aquí no hay evaluación fuera del ledger.
3. **Memoria que evita reabrir refutaciones.** Las reglas emergentes y el contraste descarte→avances son lo que ningún sistema de 2.1 implementa: R&D-Agent(Q) y AQuA usan registros para *proponer mejor*, no para *bloquear lo ya refutado*.
4. **Sin código generado en el camino de los datos.** Elimina la fuente principal de fuga de información documentada en la literatura.
5. **Tolerancia a fallos de infraestructura real:** membresía con ventanas, Kaggle no interactivo, apagones. Los tres fallos que mataron corridas previas del repo están en el diseño.
6. **Holdout de apertura única garantizado por código**, no por disciplina.

### 6.2 Desventajas y riesgos

1. **Expresividad acotada.** El registro de primitivas limita lo que el proponente puede formular. Un edge que requiera una primitiva inexistente no se descubre hasta que alguien la implemente con paridad. Es un costo deliberado.
2. **Tasa de descubrimiento esperada baja.** El resultado de Gençay (2026) sugiere que lo más probable es que el agente produzca una biblioteca de negativos bien documentados. Eso es valor metodológico, no rentabilidad. El referente lo admite ("no prometer rentabilidad futura"), pero conviene explicitarlo.
3. **Dependencia de la certificación de datos.** La auditoría del 04/10 dictamina `NOT_CERTIFIED_FOR_NEW_STRATEGY` para el canónico y bloquea el montaje en Kaggle. Hasta que eso se resuelva, EF0 rechaza casi todo. El agente no puede arreglar datos; sólo puede negarse a usarlos.
4. **Calidad del contraste estructural.** El matching `prediction` ↔ descartados depende de que las predicciones estén bien tipadas. Predicciones vagas producen falsos "no contradice". Mitigación: schema estricto y revisor que puede devolver `DERIVE` por predicción mal formulada.
5. **Costo de Opus en el revisor.** Si muchas familias sobreviven EF2 a la vez (p. ej. por un bug en el kernel), la cola de revisión se dispara. Mitigación: tope diario y el gate de paridad GPU por versión.
6. **Delegación de decisiones humanas.** Al reemplazar el OK explícito en G0–G4, el sistema pierde una capa de juicio que el referente original consideraba necesaria. La enmienda (7.3) lo hace explícito y auditable, pero no lo compensa.

---

## 7. Plan de verificación y enmienda

### 7.1 Pruebas sintéticas (sin datos de mercado, sin holdout)

| Prueba | Qué falla si rompe |
|---|---|
| `test_holdout_once` | segundo intento de apertura sobre el mismo candidato lanza y queda registrado |
| `test_prereg_hash_mismatch` | registro expandido distinto al preregistrado se rechaza antes de correr |
| `test_crash_resume` | matar el daemon en cada estado y reanudar reproduce el mismo ledger |
| `test_llm_schema` | salida inválida del LLM simulado se reintenta una vez y luego se registra |
| `test_contrast_structural` | una predicción con negación ya medida produce `DERIVE` con la cita correcta |
| `test_kill_cascades` | un `KILL` nuevo reabre las familias vivas que comparten primitivas |
| `test_rule_activation` | una regla `PROPOSED` se activa sólo con dos familias distintas |
| `test_rate_limit` | ante 429 simulado, los pasos numéricos siguen y la cola se drena al reabrir |
| `test_gpu_parity_gate` | sin `gpu_parity.json` verde para la versión, el resultado GPU se descarta |
| `test_north_star_hash` | ya existe; se mantiene |

Todas corren con un LLM falso (fixtures JSON por rol) para ser deterministas y gratis.

### 7.2 Validación end-to-end sintética

Un dataset sintético con un edge plantado conocido y diez familias ruidosas. Éxito: el agente promueve la plantada hasta G3, retira las diez, genera al menos una regla emergente consistente, y el ledger reconstruye la secuencia completa desde cero. Fracaso en cualquiera de los cuatro bloquea el despliegue.

### 7.3 Enmienda al NORTH_STAR (texto propuesto)

> **Enmienda A-2026-10-04 — Delegación al agente de investigación.** Las decisiones de promoción en G0–G4, incluida la apertura única del holdout, se delegan al agente descrito en `docs/research/AGENTE_ESPIRAL_20261004.md` (versión y hash citados en cada manifiesto), bajo las siguientes condiciones no negociables: (a) el perímetro de 3.5 está implementado en código y cubierto por las pruebas de 7.1; (b) ninguna salida de LLM es evidencia; (c) los cambios a `edge_validation_contract.md` siguen requiriendo decisión explícita del responsable. Esta enmienda no mueve ninguna frontera de holdout.

Tras la enmienda se refresca la autocita y se actualiza `CLAUDE.md`/`AGENTS.md`.

### 7.4 Tarea previa: unificar ramas

El embudo y el Edge Brain viven en `main` (177 archivos); el referente, los contratos G0–G5, `CLAUDE.md` y `AGENTS.md` viven en `claude/focused-fermat-qjt805` (3.425 archivos). Primer commit del proyecto: traer `docs/NORTH_STAR.md`, `docs/edge_validation_contract.md`, `docs/kernel_contract.md`, `tests/test_north_star_hash.py`, `CLAUDE.md` y `AGENTS.md` a `main`, sin tocar el resto.

---

## 8. Discusión

El diseño apuesta a que el valor de un agente de investigación no está en cuántas estrategias produce sino en cuántas **falsas** rechaza antes de arriesgar capital, y en no volver a pagar por refutaciones ya compradas. Esa apuesta está alineada con la evidencia disponible: los sistemas que dejan al LLM escribir código y optimizar sobre su propio backtest no sobreviven a una evaluación honesta, y los que separan creatividad de verificación sí producen resultados reproducibles en dominios con verificador exacto. Las finanzas no tienen verificador exacto; tienen MCPT, PBO, DSR, SPA y un holdout que se abre una vez. Este agente los usa como si lo fueran y acepta la tasa de descubrimiento baja que eso implica.

### 8.1 Trabajo futuro

- Ampliar el registro de primitivas a medida que el responsable certifique paridad (L2/MBP-10 bajo la enmienda L2 del 2026-09-24).
- Bootstrap clusterizado por sesión en EF3 en lugar del `deff` supuesto, con `edgelab/stats/bootstrap_estacionario.py` ya existente.
- Métrica de "distancia al edge" explícita por familia para refinar la función de valor de 5.2.
- Publicación periódica de la biblioteca de negativos como resultado científico en sí mismo.

---

## Referencias

- Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. *Journal of Portfolio Management*, 40(5), 94–107. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The Probability of Backtest Overfitting. *Journal of Computational Finance*, 20(4), 39–70. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Beel, J. et al. (2025). Evaluating Sakana's AI Scientist for Autonomous Research. arXiv:2502.14297. https://arxiv.org/abs/2502.14297
- Gençay, E. (2026). What survives honest evaluation? Leakage-safe, search-aware assessment of LLM-driven trading strategy discovery. arXiv:2608.27734. https://arxiv.org/abs/2608.27734
- Guo, J., Huang, S., Gao, Y., Li, Z., Ge, J., Liang, S., Kuang, X., & Wang, M. (2026). AQuA: Recursively Self-Improving Quantitative Trading Research Agents. arXiv:2608.12841. https://arxiv.org/abs/2608.12841
- Hansen, P. R. (2005). A Test for Superior Predictive Ability. *Journal of Business & Economic Statistics*, 23(4), 365–380.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the Cross-Section of Expected Returns. *Review of Financial Studies*, 29(1), 5–68. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314
- Li, Y., Yang, X., Yang, X., Xu, M., Wang, X., Liu, W., & Bian, J. (2025). R&D-Agent-Quant: A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization. arXiv:2505.15155 (NeurIPS 2025). https://arxiv.org/abs/2505.15155
- Lu, C. et al. (2024). The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery. arXiv:2408.06292. https://arxiv.org/abs/2408.06292
- Masters, T. (2018). *Testing and Tuning Market Trading Systems*. Apress.
- Novikov, A. et al. (2025). AlphaEvolve: A coding agent for scientific and algorithmic discovery. Google DeepMind. https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- Wang, S. et al. (2023). Alpha-GPT: Human-AI Interactive Alpha Mining for Quantitative Investment. arXiv:2308.00016.
- Wang, S. et al. (2024). QuantAgent: Seeking Holy Grail in Trading by Self-Improving Large Language Model. arXiv:2402.03755.
- White, H. (2000). A Reality Check for Data Snooping. *Econometrica*, 68(5), 1097–1126.
- Xiao, Y. et al. (2024). TradingAgents: Multi-Agents LLM Financial Trading Framework. arXiv:2412.20138. https://arxiv.org/abs/2412.20138
- Agentic Quantitative Trading: A Survey of Workflows, Systems, and Evaluation (2026). arXiv:2608.31041.

---

**Aporte al referente:** este documento no reduce por sí mismo la distancia a un edge; fija el mecanismo por el cual cada ciclo futuro deberá demostrar que la redujo, y el que impide volver a pagar por refutaciones ya hechas.
