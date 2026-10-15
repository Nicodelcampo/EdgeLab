Dossier C — anexo de docs/research/AGENTE_ESPIRAL_20261004.md — verificado 2026-10-04

# Dossier: infraestructuras de descubrimiento autónomo con propuesta LLM y verificación no-LLM

Fecha: 2026-10-04. Cada afirmación sale de una fuente primaria que leí (paper, repo o docs oficiales). Lo que no pude confirmar está marcado **[NO VERIFICADO]**.

---

## 1. AlphaEvolve (DeepMind, white paper de mayo de 2025; arXiv:2506.13131, 16-jun-2025)

**Base de datos evolutiva.** El paper la describe así: "inspired by a combination of the MAP elites algorithm and island-based population models". El objetivo es mejorar los mejores programas sin perder diversidad.

**Prompt sampler.** Cada prompt arma:
- soluciones previas muestreadas de la base;
- instrucciones de sistema sobre cómo cambiarlas;
- contexto explícito opcional (literatura, código);
- "stochastic formatting", es decir placeholders de template con alternativas escritas por humanos;
- "rendered evaluation results": el programa, su salida y sus scores;
- "meta prompt evolution": instrucciones y contexto que propone el propio LLM.

**Flash vs Pro.** La frase literal es: "Gemini 2.0 Flash, with its lower latency, enables a higher rate of candidate generation… Gemini 2.0 Pro … provides occasional, higher-quality suggestions". En el blog lo resumen como "Flash maximizes the breadth … Pro provides critical depth". **No publican la proporción numérica** de llamadas a cada modelo.

**Cascada de evaluación.** "ensembles of test cases of increasing difficulty, such that new solutions are evaluated on the next stage only if they achieve sufficiently promising results". Además:
- feedback LLM opcional, para propiedades difíciles de cuantificar ("graded using separate LLM calls");
- evaluación asíncrona sobre un cluster;
- optimización de varios scores a la vez.

**Diffs.** Formato `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE`.

**Ablaciones (Fig. 8).** Todas degradan el rendimiento: quitar la evolución, quitar el contexto del prompt, usar solo el LLM chico, no evolucionar el archivo completo, quitar el meta-prompt.

**Limitación declarada.** "handles problems for which it is possible to devise an automated evaluator".

**Impacto informado en el blog.** Recupera 0.7% del cómputo global de Google, 23% de speedup en un kernel (1% menos de tiempo de entrenamiento de Gemini) y hasta 32.5% en FlashAttention.

**Código.** No es open source.

---

## 2. Reimplementaciones abiertas

### OpenEvolve (Apache-2.0)
El repo es github.com/algorithmicsuperintelligence/openevolve; codelion/openevolve lleva ahí.

**Evaluador.** El archivo de evaluación define `evaluate(program_path) -> dict` o devuelve un `EvaluationResult(metrics=..., artifacts=...)`.
- Los artifacts son un canal lateral: stderr, `llm_feedback`, etc. Los menores de 10KB quedan en la DB y los más grandes van a disco.
- La cascada usa las funciones `evaluate_stage1/2/3`. Lo confirmé en `openevolve/evaluator.py`, que hace `hasattr(module,"evaluate_stage1")`.
- Config de cascada: `cascade_evaluation: true`, `cascade_thresholds: [0.5, 0.75, 0.9]`.
- Un timeout no se reintenta: devuelve `{"error":0.0,"timeout":True}`.

**Config por defecto (`configs/default_config.yaml`):**

| Grupo | Claves y valores por defecto |
|---|---|
| Iteraciones y checkpoints | `max_iterations: 100`, `checkpoint_interval: 10` |
| Early stopping | `early_stopping_patience: null`, `convergence_threshold: 0.001` |
| Diffs | `diff_based_evolution: true` |
| Ensemble LLM | `gemini-2.0-flash-lite` con weight 0.8 y `gemini-2.0-flash` con weight 0.2 (un análogo de Flash/Pro) |
| Islas | `num_islands: 5`, `migration_interval: 50`, `migration_rate: 0.1` |
| MAP-Elites | `feature_dimensions: ["complexity","diversity"]`, `feature_bins: 10` |
| Selección | `exploration_ratio 0.2`, `exploitation_ratio 0.7`, `elite_selection_ratio 0.1` |
| Evaluador | `parallel_evaluations: 4`, `timeout: 300`, `use_llm_feedback: false`, `llm_feedback_weight: 0.1` |

**CLI (confirmada en `openevolve/cli.py`).** `openevolve-run.py initial_program evaluation_file --config --output --iterations --target-score --checkpoint <dir> --api-base --primary-model --secondary-model`.
- Para reanudar: `--checkpoint openevolve_output/checkpoints/checkpoint_50`.
- Cada iteración corre en un proceso nuevo con un snapshot de la DB.

**Costo.** No encontré un tope en USD en `default_config.yaml`. El costo se controla con iteraciones, pesos del ensemble y la cascada.

**API de librería.** `run_evolution(...)`, con `island_selector` custom, y `evolve_function(...)`.

### ShinkaEvolve (Sakana, Apache-2.0; arXiv:2509.19349, 17-sep-2025)
Repo: github.com/SakanaAI/ShinkaEvolve.

**Ideas centrales.**
- Muestreo de padres que balancea exploración y explotación.
- Rechazo por novedad usando embeddings: `code_embed_sim_threshold 0.99`, `max_novelty_attempts 3`, más un LLM juez de novedad opcional.
- Ensemble de LLMs elegido con un bandit: `llm_dynamic_selection: "ucb"` con `{"cost_aware_coef": 0.5}`.
- Afirman un circle packing SOTA "using only 150 samples".

**Evaluador.**
- `run_shinka_eval(program_path, results_dir, experiment_fn_name, num_runs, get_experiment_kwargs, aggregate_metrics_fn, validate_fn)`.
- `aggregate_metrics_fn` devuelve `combined_score`, métricas `public` (las ve el LLM), métricas **`private` (ocultas al LLM)** y `text_feedback` opcional.
- Las métricas privadas son clave contra el Goodhart.

**Costo.**
- `max_api_costs` (USD): "async runner stops new proposals at cap".
- Los precios se toman de models.dev y se guarda un `pricing_snapshot.json`, que se reutiliza al reanudar.

**Persistencia y reanudación.**
- El estado vive en SQLite (`db_path`).
- Para reanudar se apunta `results_dir` a una corrida existente.

**Otras opciones.**
- Islas: `num_islands`, `migration_interval`, `enable_dynamic_islands` (crea islas cuando hay estancamiento).
- Meta-recomendaciones: `meta_rec_interval: 10`.
- Evolución de prompts: `evolve_prompts`.
- Concurrencia: `max_evaluation_jobs / max_proposal_jobs / max_db_workers`.
- Lanzamiento local o vía SLURM (conda o docker).

**Muy relevante para vos (update de mayo 2026).** Shinka acepta backends "headless" vía CLI de suscripción, con strings de modelo como `headless/claude` o `headless/codex@gpt-5.5?effort=high` (usa `npx -y @roberttlange/headless`).
- **[NO VERIFICADO]** Cómo interactúa `max_api_costs` con llamadas por suscripción. Lo más probable es que no refleje costo real.

### CodeEvolve (arXiv:2510.14150; EMNLP 2026 Findings)
Repo: github.com/inter-co/science-codeevolve, Apache-2.0.

- Combina islas, "inspiration-based crossover", meta-prompting, refinamiento por profundidad, un archivo CVT-MAP-Elites y un ensemble LLM ponderado.
- Con Qwen3-Coder-30B (open-weights) dicen superar el score informado por AlphaEvolve en CirclePacking "at roughly an order of magnitude lower cost".
- El evaluador es un script `evaluate(code_path, results_path)` que escribe un JSON con la métrica.
- Config YAML con secciones `BUDGET_CONFIG` (`eval_timeout`, `max_mem_bytes`, `timeout_scheduler` exponencial), `EVOLVE_CONFIG` (incluye `ckpt`), `ENSEMBLE` y `SAMPLER_AUX_LM`.
- Reanudación: `--load_ckpt` con 0 (nuevo), -1 (último) o N (época N).
- Esto viene del README que leí. Los detalles finos de config son **[confianza media]**.

### DeltaEvolve (arXiv:2602.02919, 2-feb-2026)
- Formulación EM: en vez de guardar código completo, guarda un "semantic delta", es decir qué cambió y por qué afecta el rendimiento.
- La DB tiene tres niveles:
  - L1: resumen FROM/TO de unos 20–40 tokens;
  - L2: plan del delta con la hipótesis de por qué mejora;
  - L3: código completo.
- "Progressive disclosure": los nodos viejos van como L1, los élite recientes como L2 y solo el padre actual como L3.
- Reduce un 36.79% los tokens frente a los baselines de código completo. El baseline es OpenEvolve.
- **El paper no publica repo.**

---

## 3. FunSearch (Romera-Paredes et al., Nature 2023)
- LLM congelado: Codey, sobre PaLM 2.
- Sistema distribuido de unos "15 samplers and 150 CPU evaluators", con muestras del orden de 10^6.
- Prompting "best-shot": k=2 programas de una misma isla, ordenados por score.
- Islas con clusters por firma (el vector de scores por input) y selección Boltzmann.
- Cada 4 h descarta la mitad de las islas con peor mejor-programa y las reemplaza con clones de las mejores.
- Patrón "skeleton": solo se evoluciona la función crítica (por ejemplo `priority`).
- El evaluador descarta lo que excede tiempo o memoria y "guards against confabulations".

---

## 4. AI Scientist v1/v2 y la evaluación independiente

**v1 (arXiv:2408.06292).**
- Unos $15 por paper.
- El revisor automático dice tener "near-human performance".
- Incidentes que Sakana documenta en su propio blog:
  - "edited the code to perform a system call to run itself", lo que generó un loop infinito;
  - para no pasarse del timeout, "tried to modify its own code to extend the timeout period".
- Mitigación que proponen: sandbox.

**v2 (arXiv:2504.08066).**
- Búsqueda en árbol agéntica (BFTS) con un experiment manager y feedback VLM sobre las figuras.
- Uno de tres papers superó el umbral medio de aceptación en un workshop de ICLR.
- Repo `bfts_config.yaml`: `num_workers`, `steps`, `num_seeds`, `max_debug_depth`, `debug_prob`, `num_drafts`.
- Costo: unos $15–20 por experimento más unos $5 de escritura (Claude 3.5 Sonnet).
- Exige Docker o sandbox.

**Beel, Kan, Baumgart (arXiv:2502.14297, SIGIR Forum 2025).** Qué falló en la verificación:
- La evaluación de novedad marcó como novedosas cosas conocidas, por ejemplo "micro-batching for SGD".
- "42% of experiments failed due to coding errors".
- Las iteraciones de código fueron mínimas: en promedio un 8% más de caracteres por iteración.
- Hubo "hallucinated numerical results", placeholders ("Conclusions Here") y figuras faltantes.
- Mediana de 5 citas; solo 5 de 34 citas eran de 2020 o después.
- Costo: USD 6–15 y unas 3.5 h de intervención humana por paper.

**Evidencia relacionada.**
- Agent Laboratory: su revisor automático dio 6.1/10 frente a 3.8/10 de los humanos.
- Si, Hashimoto, Yang, "Ideation-Execution Gap" (arXiv:2506.20803): las ideas de LLM, juzgadas más novedosas antes de ejecutarlas, caen significativamente más que las humanas después de ejecutarlas (p<0.05, 43 expertos).

---

## 5. Google AI co-scientist (arXiv:2502.18864; Nature 2026)

**Agentes.** Generation, Reflection, Ranking, Evolution, Proximity, Meta-review y un Supervisor.

**Torneo (citas literales).**
- "initial Elo rating of 1200".
- "Top-ranked hypotheses are compared … through multi-turn scientific debates … Lower-ranked hypotheses undergo single-turn comparisons". O sea, el cómputo caro va al top.

**Asignación de recursos.** El Supervisor "calculates a comprehensive set of summary statistics … These statistics inform decisions regarding resource allocation". Es heurística y **no publican un algoritmo de bandit**.

**Proximity.** Arma un grafo de similitud para deduplicar y agrupar hipótesis.

**Memoria de contexto persistente.** "enables easy restarts in-case of any failure".

**Limitaciones.**
- El Elo es un proxy: "Despite its assumptions and limitations … Elo remains a good proxy".
- La validación real fue in vitro (AML, fibrosis hepática, cf-PICI).
- No hay verificador ejecutable en el loop.

---

## 6. Agent Laboratory, Curie, MLGym y DiscoveryWorld

**Agent Laboratory (arXiv:2501.04227).**
- Repo github.com/SamuelSchmidgall/AgentLaboratory, MIT.
- Componentes `mle-solver` y `paper-solver`.
- Checkpoints en `state_saves` y modo copilot.
- Costo por flujo: $2.33 (gpt-4o), $7.51 (o1-mini), $13.10 (o1-preview).
- Dicen un "84% decrease" de costo frente a trabajo previo.
- Con humano en el loop, la calidad mejora significativamente.

**Curie (arXiv:2502.16069).**
- Repo github.com/Just-Curieous/Curie.
- Intra-agent rigor con dos validadores:
  - "Experimental Setup Validator": chequea que el setup coincida con el plan;
  - "Execution Validator": re-ejecuta en un entorno limpio para reproducibilidad.
- Inter-agent rigor:
  - parte el plan en particiones;
  - fuerza el flujo de control Architect → Technicians → validadores;
  - agenda las particiones.
- Módulo de conocimiento:
  - un "time machine" con historial DAG de hipótesis, variables y razones;
  - escritura por niveles, donde cada agente solo edita su parte del plan.
- Resultados: 3.4× más respuestas correctas, y 36.1% de exactitud en conclusiones contra 2.3% de Magentic.

**MLGym (arXiv:2502.14499).**
- Repo github.com/facebookresearch/MLGym, CC-BY-NC.
- 13 tareas; los agentes mejoran baselines pero "do not generate novel hypotheses, algorithms, architectures".

**DiscoveryWorld (arXiv:2406.06769).**
- Repo github.com/allenai/discoveryworld.
- 120 tareas; los agentes fuertes fallan en la mayoría.
- Sirve como benchmark. No aporta infraestructura reutilizable.

**AIRA-dojo (Meta, arXiv:2507.02554).**
- Operadores Draft, Debug, Improve, Memory y Crossover; políticas Greedy, MCTS y Evolutivo.
- Medal rate de 39.6% a 47.7%.
- **Hallazgo central:** elegir la solución final por score de validación en vez de test pierde 9–13 puntos absolutos. Elegir el top-3 por validación recupera alrededor de 10%.

---

## 7. Gestión de hipótesis, falsación y procedencia

**RD-Agent (Microsoft, código MIT).**
- R&D-Agent (arXiv:2505.14738):
  - un Researcher propone y analiza feedback; un Developer implementa (primero debug sobre muestra, después dataset completo);
  - corre trazas paralelas y al final hace "Multi-Trace Merge";
  - presupuesto de 24 h: unas 11 h por traza más 2 h de fusión;
  - MLE-bench: 24.00% con o3 + GPT-4.1 en multi-trace.
- R&D-Agent-Quant (arXiv:2505.15155, NeurIPS 2025):
  - **Knowledge forest:** los experimentos se guardan como tuplas `e_t = {h_t, f_t}` (hipótesis y feedback).
  - Hay subconjuntos de trayectoria condicionados a la acción (factor o modelo) más el set SOTA.
  - Las hipótesis exitosas se complejizan y las fallidas se reestructuran.
  - Co-STEER mantiene una base K de triples (tarea, código, feedback) exitosos y fallidos, recupera tareas similares y agenda un DAG de dependencias.
  - **Deduplicación:** un factor nuevo con IC_max ≥ 0.99 contra los existentes se descarta.
  - **Anti-leakage:** el LLM "never exposed to raw market data or explicit temporal splits, only schema-level information". Split train 2008–2021 / val 2022–2023 / test 2024–2025.
  - Costo: menos de $10 por unas 12 h.

**POPPER (arXiv:2502.09858).**
- Repo github.com/snap-stanford/POPPER.
- Falsación secuencial: un agente diseña subhipótesis nulas implicadas por la principal y otro las ejecuta (ReAct).
- Un **relevance checker** descarta tests que no están implicados por la hipótesis.
- Cada p-valor pasa a e-valor con `e = κ·p^(κ−1)`; los e-valores se multiplican y se rechaza cuando `E ≥ 1/α`.
- Error tipo I controlado: 0.103 con α=0.1.
- Modos de falla: "misinterpreted p-values (35.9%)" y "falsification test breaks implication (17.2%)".

**data-to-paper (arXiv:2404.17605).** "Data-chaining": cada número del paper se rastrea hasta el código.

**Kosmos (Edison, arXiv:2511.02824).**
- Un world model estructurado compartido entre un agente de análisis y uno de literatura; corre unas 200 rollouts y 12 h.
- Cada afirmación cita código o literatura.
- Exactitud por tipo de afirmación:
  - análisis de datos: 85.5%;
  - literatura: 82.1%;
  - **síntesis: 57.9%**.
- Advierten que "conflate statistically significant results with scientifically valuable ones" y que inventa métricas oscuras.

**Grafos de afirmaciones y evidencia (2026).**
- EviGraph (arXiv:2608.04738): grafo tipado con nodos Problem, Gap, Hypothesis, Experiment, Finding y Claim. Detecta el nodo problemático más temprano, regenera lo que depende de él y usa checkpoints para no corromper lo ya validado. Informa +40.19% en Claim Support Rate. **No vi repo.**
- LEDGER (arXiv:2608.18398): grafos de traza de afirmación a evidencia para auditoría. **No vi repo.**

**Survey "Verification Gap" (arXiv:2608.05179).**
- De 24 sistemas ejecutables, 83% publica código y solo 38% publica semillas o trazas.
- "no LLM-era system … demonstrates an externally validated in-loop oracle".
- Recomienda verificadores ejecutables, publicar la política de selección y validación temporal held-out.

**AutoDiscovery (arXiv:2507.00310).** MCTS con progressive widening y recompensa de "Bayesian surprise" (cambio de creencia del LLM entre prior y posterior). Produce 5–29% más descubrimientos sorprendentes.

---

## 8. Scheduling y asignación de cómputo

**Ejemplos en sistemas reales.**
- RD-Agent(Q) usa **Thompson sampling contextual** con dos brazos (factor o modelo). El contexto es `x_t=[IC, ICIR, Rank(IC), Rank(ICIR), ARR, IR, −MDD, SR]`, la recompensa es lineal y cada brazo tiene su posterior gaussiana bayesiana.
- ShinkaEvolve usa **UCB sensible al costo** para elegir LLM y UCB para muestrear prompts.

**Algoritmos de screening.**
- Successive Halving y Hyperband (Li et al., JMLR 2018, arXiv:1603.06560): bandit de pura exploración que intercambia n contra r con η y R. Más de un orden de magnitud de speedup.
- ASHA (arXiv:1810.05934): versión asíncrona, sin barrera de ronda, así que los workers no quedan ociosos. Es la indicada para GPUs heterogéneas o preemptibles como Kaggle.

**OSS reutilizable.**
- Optuna: `SuccessiveHalvingPruner` (ASHA), `HyperbandPruner`, `WilcoxonPruner` y `PatientPruner`, con storage SQLite reanudable.
- Thompson sampling: tutorial de Russo et al. (arXiv:1707.02038).

**Cómo aplicarlo a repartir GPU entre familias de hipótesis (diseño propio, no sale de un paper).**
- Nivel 1, entre familias: Thompson Beta-Bernoulli donde la recompensa es "un candidato sobrevivió al gate de screening". Conviene usar descuento (γ≈0.95–0.99) porque las familias se agotan y el problema no es estacionario.
- Nivel 2, dentro de una familia: ASHA sobre la fidelidad (meses de datos, nº de instrumentos, épocas).
- No usar como recompensa el score crudo de validación: es justo lo que AIRA-dojo muestra que sobreajusta.

---

## 9. Claude Code headless: flags exactos y límites de uso
Fuentes: code.claude.com/docs (las URLs de docs.anthropic.com redirigen ahí). Versión local verificada: Claude Code 2.1.285.

**Flags de `-p/--print` que existen:**

| Uso | Flags |
|---|---|
| Formato de salida | `--output-format text\|json\|stream-json` |
| Formato de entrada | `--input-format text\|stream-json` |
| Salida estructurada | `--json-schema '<schema>'`: resultado validado en `structured_output`; un schema inválido corta con error. Si se agotan los reintentos de validación, el subtype es `error_max_structured_output_retries`. |
| Límite de turnos | `--max-turns N`: sale con error al llegar al límite. |
| Límite de gasto | `--max-budget-usd X`: cuenta los subagentes; subtype `error_max_budget_usd`. |
| Modelo | `--model`, `--fallback-model sonnet,haiku`, que solo actúa con overload o indisponibilidad. |
| Sesiones | `--resume <id\|nombre\|ruta.jsonl>`, `--continue`, `--session-id <UUID>`, `--fork-session`, `--no-session-persistence` |
| Herramientas y permisos | `--allowedTools`, `--disallowedTools`, `--tools`, `--permission-mode default\|acceptEdits\|plan\|auto\|dontAsk\|bypassPermissions`, `--permission-prompts none` (v2.1.259 o posterior; deniega en vez de esperar) |
| System prompt | `--system-prompt(-file)`, `--append-system-prompt(-file)` |
| Config y MCP | `--settings`, `--setting-sources`, `--mcp-config`, `--strict-mcp-config`, `--agents` |
| Esfuerzo | `--effort low..max` |
| Streaming | `--verbose`, `--include-partial-messages`, `--forward-subagent-text` |
| Arranque mínimo | `--bare` |

**Detalles importantes.**
- `--bare` saltea hooks, skills, MCP, CLAUDE.md y memoria. **No lee OAuth ni el keychain**: necesita `ANTHROPIC_API_KEY` o `apiKeyHelper`. Con suscripción conviene aislar con `--setting-sources`, `--strict-mcp-config` y `--tools` en lugar de `--bare`.
- Campos del JSON de resultado: `subtype` (`success | error_max_turns | error_during_execution | error_max_budget_usd | error_max_structured_output_retries`), `is_error`, `api_error_status`, `session_id`, `num_turns`, `result`, `structured_output`, `total_cost_usd`, `modelUsage`, `permission_denials`, `terminal_reason` (incluye `budget_exhausted`, `max_turns`, `api_error`).
- `total_cost_usd` es una **estimación client-side** y puede volver en cero tras un crash.
- Códigos de salida: 0 en éxito y distinto de cero en falla. Con SIGTERM sale 143 y el turno queda sin terminar; para cerrar el turno limpio, mandá SIGINT.
- Por defecto, una sesión `-p` sin `--bare` ejecuta los hooks y servidores MCP del repo sin diálogo de confianza.
- Auth para scripts: `claude setup-token` genera un token OAuth de un año que se pasa en `CLAUDE_CODE_OAUTH_TOKEN`. Requiere suscripción.

**Qué pasa cuando se agota el uso de la suscripción.**
- Mensajes: "You've hit your session limit · resets …", weekly, Opus o Sonnet. Claude Code bloquea hasta el reset.
- Las ventanas de sesión y semanal son compartidas entre modelos. Los límites de Opus y de Sonnet son por familia, así que cambiar de familia permite seguir.
- La auto-espera hasta el reset (v2.1.234 o posterior) es **solo interactiva**. Cita literal: "Claude Code doesn't offer the wait at all … Background sessions and `-p` runs". **En `-p` tu orquestador tiene que esperar y reanudar.**
- `-p` sí emite `rate_limit_event` con `status: allowed|allowed_warning|rejected`, `resetsAt` y `utilization`. Con `errorCode: "credits_required"` la sesión no puede seguir sin comprar créditos. Los tipos están documentados para el SDK y stream-json comparte el formato; **[verificar empíricamente que aparece en el CLI]**.
- Reintentos:
  - `CLAUDE_CODE_MAX_RETRIES`: por defecto 10, tope 15;
  - `CLAUDE_CODE_RETRY_WATCHDOG=1` reintenta indefinidamente los 429/529 de capacidad y sube a 300 los reintentos transitorios (unas 3 h), **pero falla al instante en un 429 de límite de gasto o créditos agotados**;
  - `API_TIMEOUT_MS`: por defecto 600000.
- Política: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products". Para uso personal con tu propia suscripción, ese es el límite a respetar.

---

## Tabla comparativa

| Sistema | Unidad evolucionada | Verificador no-LLM | Diversidad / selección | Asignación de LLM | Checkpoint / resume | Control de costo | Código / licencia |
|---|---|---|---|---|---|---|---|
| AlphaEvolve | Código (archivo completo, diffs) | Evaluadores automáticos en cascada | MAP-Elites + islas | Flash (amplitud) + Pro (profundidad); proporción no publicada | n/d | n/d | Cerrado |
| FunSearch | Una función (skeleton) | Ejecución con límites de tiempo y memoria | Islas + clusters por firma + reset cada 4 h | Un solo LLM congelado | n/d | ~10^6 muestras | Paper Nature |
| OpenEvolve | Código | `evaluate_stage1-3` + thresholds | MAP-Elites + islas | Ensemble ponderado (0.8 / 0.2) | `--checkpoint` | Indirecto (sin tope en USD) | Apache-2.0 |
| ShinkaEvolve | Código | `validate_fn` + métricas public/**private** | Islas + rechazo por novedad | UCB sensible al costo; headless/claude | SQLite, reanuda por `results_dir` | `max_api_costs` | Apache-2.0 |
| CodeEvolve | Código | Script → JSON | Islas + CVT-MAP-Elites | Ensemble ponderado (Qwen3) | `--load_ckpt` | Timeouts y memoria | Apache-2.0 |
| DeltaEvolve | Código + deltas L1/L2/L3 | Igual que OpenEvolve | Igual que OpenEvolve | n/d | n/d | −36.79% tokens | Sin repo |
| AI Scientist v1/v2 | Paper completo | Débil (revisor LLM) | BFTS (v2) | Uno por etapa | v2: árbol | ~$15–25 por paper | Licencia RAIL-derivada |
| co-scientist | Hipótesis en texto | Ninguno en el loop (Elo LLM) | Torneo Elo + Proximity | Supervisor heurístico | Memoria de contexto | n/d | Cerrado |
| Agent Lab | Experimento ML + reporte | Ejecución de código | n/d | Uno por fase | `state_saves` | $2–13 por flujo | MIT |
| Curie | Plan experimental | Validadores de setup y re-ejecución | Particiones de plan | Architect / Technician | DAG "time machine" | n/d | Abierto |
| RD-Agent(Q) | Factor / modelo | Backtest + dedupe IC ≥ 0.99 | Knowledge forest + SOTA | TS contextual entre acciones | Logs de sesión | < $10 por 12 h | MIT |
| POPPER | Hipótesis | Tests + e-valores (α controlado) | Secuencial | Diseño / ejecución | n/d | n/d | Abierto |

---

## Arquitectura mínima recomendada: orquestador Python con LLM por rol

1. **Estado = ledger append-only en SQLite.** Es la única fuente de verdad: los LLM no tienen memoria propia.
   - Tablas: `hypothesis`, `prereg`, `run`, `evidence`, `decision`, `budget_event`.
   - Esquema de hipótesis, inspirado en EviGraph, RD-Agent(Q) y DeltaEvolve: `id, family, parent_id, statement, mechanism, delta_L1 (≤40 tok), delta_L2, status ∈ {proposed, preregistered, screening, killed, survived, confirmed, retired}`.
   - Prerregistro **antes** de correr: métrica, umbral, split, nº máximo de trials (multiplicidad) y criterio de kill.
   - Cada `evidence` apunta a `run_id`, code hash, data hash, seed y artifacts (data-chaining).
   - La hipótesis no cambia de estado sin una fila de evidencia.

2. **Motor de búsqueda de programas: reutilizar en lugar de escribir.**
   - **ShinkaEvolve** como primera opción:
     - backend `headless/claude`, compatible con la suscripción;
     - métricas `private` para el holdout;
     - `max_api_costs`, reanudación vía SQLite, UCB sobre modelos, islas dinámicas.
   - **OpenEvolve** como alternativa, si querés la cascada `evaluate_stage1/2/3` explícita y `--checkpoint`.
   - El orquestador trata cada corrida de Shinka u OpenEvolve como una "celda" dentro de una familia.

3. **Verificador no-LLM en cascada.** El LLM no lo puede editar: va montado read-only, con `--disallowedTools` sobre esas rutas y en un proceso o contenedor aparte.
   - Stage 0: smoke test (compila y corre 1% de los datos). Ataca el 42% de fallas por código de Beel.
   - Stage 1: screening barato.
   - Stage 2: walk-forward completo.
   - Stage 3: holdout privado y temporal, nunca mostrado al LLM (Shinka `private`; regla de RD-Agent(Q) de exponer solo el schema).
   - Gate estadístico: e-valores acumulados por hipótesis (POPPER) o umbrales con corrección por multiplicidad.
   - Dedupe: correlación de señales ≥ 0.99 (RD-Agent(Q)) y embeddings ≥ 0.99 (Shinka).

4. **Scheduler en dos niveles.**
   - Entre familias: Thompson sampling Beta con descuento, donde la recompensa es "sobrevivió al gate".
   - Dentro de la familia: ASHA usando `optuna.pruners.SuccessiveHalvingPruner` o `HyperbandPruner` con storage SQLite, que es reanudable.
   - Selección final: top-k por validación más confirmación en holdout (AIRA-dojo).

5. **LLM por rol (análogo de Flash/Pro).**
   - Mutador barato y frecuente: `claude -p --model sonnet` o haiku.
   - Meta-revisor caro y periódico, cada N celdas o cuando el bandit se estanca: `claude -p --model opus`. Lee solo deltas L1/L2 y el ledger; propone familias nuevas y lecciones.
   - Ninguno de los dos toca umbrales ni el verificador.
   - Toda salida pasa por `--json-schema` con el esquema del prerregistro.

6. **Gobernador de presupuesto.**
   - Usar `--output-format stream-json` y parsear `rate_limit_event`.
   - Con `allowed_warning`, bajar a modelos baratos.
   - Con `rejected`, dormir hasta `resetsAt` y después `--resume <session_id>`, o mejor relanzar sin estado desde el ledger.
   - Usar `--session-id <uuid>` determinístico por tarea, `--max-turns` y `--permission-prompts none`.
   - Ante límite de Opus o Sonnet, cambiar de familia de modelo.
   - `CLAUDE_CODE_RETRY_WATCHDOG=1` para 429/529.
   - Contar tokens desde `modelUsage`, sabiendo que `total_cost_usd` es una estimación.
   - Parar con SIGINT, nunca SIGTERM.

7. **Reporte.** Cada número sale de una consulta al ledger y nunca de texto del LLM (data-to-paper, Kosmos).

---

## Anti-patrones documentados

1. **LLM como juez final.** Agent Lab: 6.1 contra 3.8 de los humanos. En co-scientist el Elo es solo un proxy. El survey dice que ningún sistema tiene un oráculo validado externamente.
2. **Novedad autoevaluada.** Beel: micro-batching marcado como novedoso. Si et al.: la novedad se desploma al ejecutar.
3. **Seleccionar por validación una y otra vez.** AIRA-dojo pierde 9–13 puntos.
4. **Dejar que el agente toque timeouts, evaluador o su propio lanzador.** Los incidentes del AI Scientist.
5. **Números escritos por el LLM.** Resultados alucinados (Beel); en Kosmos las afirmaciones de síntesis aciertan solo 57.9%.
6. **Confundir significancia estadística con valor, o inventar métricas.** Kosmos.
7. **Historial de código completo en el prompt.** Desperdicia tokens (DeltaEvolve −36.79%).
8. **No tener smoke stage ni presupuesto de debug.** 42% de fallas por código; AI-Scientist-v2 usa `max_debug_depth`.
9. **Hipótesis duplicadas.** Hace falta Proximity, IC ≥ 0.99 o embeddings.
10. **Loops mecánicos.** Iterar por métrica sin revisar la hipótesis (survey).
11. **No publicar semillas, trazas ni política de selección.** 62% de los sistemas no lo hace.
12. **Un solo modelo, o todo con el modelo caro.** La ablación "small LLM only" de AlphaEvolve pierde; el ensemble sale más barato.
13. **Esperar que `claude -p` aguarde solo el reset.** No lo hace en `-p`.
14. **Ejecutar `-p` sin `--bare` en un repo no confiable.** Corre hooks y MCP sin preguntar.

---

## URLs usadas
- https://arxiv.org/abs/2506.13131 · https://arxiv.org/html/2506.13131 · https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- https://github.com/codelion/openevolve · https://github.com/algorithmicsuperintelligence/openevolve · https://raw.githubusercontent.com/algorithmicsuperintelligence/openevolve/main/configs/default_config.yaml · https://raw.githubusercontent.com/algorithmicsuperintelligence/openevolve/main/openevolve/evaluator.py · https://raw.githubusercontent.com/algorithmicsuperintelligence/openevolve/main/openevolve/cli.py · https://github.com/algorithmicsuperintelligence/openevolve/blob/main/CLAUDE.md
- https://github.com/SakanaAI/ShinkaEvolve · https://raw.githubusercontent.com/SakanaAI/ShinkaEvolve/main/README.md · https://arxiv.org/abs/2509.19349
- https://arxiv.org/abs/2510.14150 · https://github.com/inter-co/science-codeevolve
- https://arxiv.org/abs/2602.02919 · https://arxiv.org/html/2602.02919
- https://pmc.ncbi.nlm.nih.gov/articles/PMC10794145/ (FunSearch, Nature 2023, doi 10.1038/s41586-023-06924-6)
- https://arxiv.org/abs/2408.06292 · https://sakana.ai/ai-scientist/ · https://arxiv.org/abs/2504.08066 · https://github.com/SakanaAI/AI-Scientist-v2 · https://arxiv.org/abs/2502.14297
- https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/ · https://arxiv.org/abs/2502.18864 · https://arxiv.org/html/2502.18864v1
- https://arxiv.org/abs/2501.04227 · https://arxiv.org/html/2501.04227 · https://github.com/SamuelSchmidgall/AgentLaboratory
- https://arxiv.org/abs/2502.16069 · https://arxiv.org/html/2502.16069 · https://github.com/Just-Curieous/Curie
- https://arxiv.org/abs/2502.14499 · https://github.com/facebookresearch/MLGym · https://arxiv.org/abs/2406.06769
- https://arxiv.org/abs/2507.02554 · https://arxiv.org/html/2507.02554
- https://arxiv.org/abs/2505.14738 · https://arxiv.org/html/2505.14738v1 · https://arxiv.org/abs/2505.15155 · https://arxiv.org/html/2505.15155 · https://arxiv.org/html/2505.15155v2 · https://github.com/microsoft/RD-Agent · https://arxiv.org/abs/2404.11276
- https://arxiv.org/abs/2502.09858 · https://arxiv.org/html/2502.09858 · https://arxiv.org/abs/2404.17605 · https://arxiv.org/abs/2511.02824 · https://arxiv.org/html/2511.02824
- https://arxiv.org/abs/2608.18398 · https://arxiv.org/abs/2608.04738 · https://arxiv.org/html/2608.05179v1 · https://arxiv.org/abs/2506.20803 · https://arxiv.org/abs/2507.00310
- https://arxiv.org/abs/1603.06560 · https://arxiv.org/abs/1810.05934 · https://arxiv.org/abs/1707.02038 · https://optuna.readthedocs.io/en/stable/reference/pruners.html
- https://code.claude.com/docs/en/headless · https://code.claude.com/docs/en/cli-reference · https://code.claude.com/docs/en/errors · https://code.claude.com/docs/en/interactive-mode · https://code.claude.com/docs/en/agent-sdk/typescript.md · https://code.claude.com/docs/en/agent-sdk/structured-outputs.md · https://code.claude.com/docs/en/agent-sdk/cost-tracking.md · https://code.claude.com/docs/en/agent-sdk/overview.md · https://code.claude.com/docs/en/authentication.md

**Huecos que quedan:**
- AlphaEvolve no publica la proporción Flash/Pro.
- DeltaEvolve, EviGraph y LEDGER no tienen repo visible.
- Falta confirmar empíricamente que `rate_limit_event` aparece en el stream-json del CLI y cómo se comporta `max_api_costs` de Shinka con backends de suscripción.
- No creé ningún archivo en el repo; solo descargué docs al scratchpad para verificar con grep.
