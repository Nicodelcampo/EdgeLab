# Plan: agente investigador autónomo de EdgeLab corriendo en SV1

Estado: PLAN PROPUESTO (2026-10-15). No hay nada desplegado. Lo que dice "decide Nico" no está decidido.

**Pedido (gonzasib, sala de Chaski):** que en SV1 corran uno o varios agentes que orquesten, lancen, analicen e interpreten corridas, investiguen y lean el cerebro, quizás con varios Haiku por rol. El cómputo se hace en Kaggle, así que SV1 tiene que tener credenciales, permisos y acceso al repo.

**Restricciones de SV1** (`SV1-contexto-para-llm.md`):
- Es una notebook en producción: 2 núcleos, 7,6 GiB de RAM, Python 3.11 en el host.
- `sudo` pide contraseña.
- Contenedores sólo en `127.0.0.1`.
- Entre las 02:00 y las 04:00 corren los backups.

## 1. Qué ya está diseñado o construido

Hay **tres piezas**, en ramas distintas, y ninguna está viva en `foundation`.

| pieza | dónde | qué tiene | estado |
|---|---|---|---|
| **Paper del agente en espiral** | PR #119 (`docs/research/AGENTE_ESPIRAL_20261004.md`) | Plano completo: máquina de estados por familia; roles LLM (Proponente, Lector, Revisor, Cronista); reglas K1–K14; canarios; alpha-wealth; economía de tokens bajo membresía; pruebas §8.1; hitos R0–R12 | Sólo documento |
| **Autopilot** | PR #64, rama `claude/vibrant-clarke-s9z6e2`; archivado en `foundation` bajo `archive/ramas_20261014/b009_…` | **Lo más cercano a lo pedido.** `tick()` con kill switch. Guardas duras: holdout, pre-registro committeado, archivos protegidos por hash. FDR en línea (alpha-investing). Selector Thompson. Generador de candidatas por reglas. Escritura al Brain. `kaggle_launch` con preflight. Optimizador con aceptación por salida idéntica. **Kit Debian** (`install.sh`, unidades systemd con timer de 10 min, `doctor`, credenciales en `/etc/edgelab/*.env`). 11 tests. 18 lanzamientos reales hechos a mano; campañas IDM/OU/SCAN/SLOT/VIO con resultado nulo o informativo | Probado con simuladores; **nunca corrió en un Debian real** |
| **Research Ops** | PR #117 → #118 → #120 (base `main`, 1.798 commits atrás de `foundation`) | Cola SQLite durable con presupuesto reservado. `DispatchLedger`: presupuesto de research entre reinicios. `CheckpointLedger` de unidades. Snapshots y restauración. Planificador knowledge-first (Brain + SSRN). `KaggleRunLedger` de #120: reservar, push, poll y recolectar | Sintético, sin despliegue |

**Solapamiento a resolver:** autopilot (`RunLedger` + `executor` + `kaggle_launch`), Research Ops (`Store`) y #120 (`KaggleRunLedger`) son **tres ledgers de corridas**. Tiene que quedar uno solo. #120 se escribió sin conocer el autopilot. Su valor está en los chequeos fail-closed del metadata del kernel; conviene llevar esos chequeos al executor del autopilot en vez de mantener #120 como módulo aparte.

## 2. Qué falta (ordenado por bloqueo)

1. **Base única y viva.** Nada de esto está en `foundation`. Hay que decidir el lugar, rebasar autopilot y Research Ops sobre `foundation` y deduplicar los ledgers.
2. **Capa de roles LLM: no existe en ningún lado.** Hoy el generador del autopilot usa reglas y las candidatas las promueve un humano. Faltan:
   - un runner `claude -p` headless con salida validada contra JSON Schema;
   - un gobernador de límites de la suscripción (`rate_limit_event`: dormir y seguir con lo numérico);
   - un ledger `llm_calls` con rol, modelo, tokens y hashes;
   - la regla "ningún rol ve credenciales, rutas de datos ni métricas privadas".
3. **Despliegue en SV1.** El kit Debian existe, pero hay que ajustarlo:
   - `MemoryMax=3G` es demasiado para esta máquina;
   - el host tiene Python 3.11 y Research Ops pide 3.12;
   - nunca se probó en un Debian real;
   - necesita root para el usuario, las unidades y `/etc/edgelab`.
4. **Credenciales:**
   - Un token de Kaggle **nuevo**: el actual quedó expuesto en la sala.
   - `CLAUDE_CODE_OAUTH_TOKEN` de `claude setup-token` para el modo headless con la suscripción.
   - Una deploy key de GitHub con escritura sólo en este repo, que pushee el estado a una rama propia y no a `foundation`.
5. **Puente con Chaski:**
   - resumen de cada ciclo a la sala;
   - comandos `pausa`, `estado` y `aprobar <candidata>`;
   - `data_requests` (el agente pide datos a las personas);
   - aviso si el ciclo falla.
6. **Prerrequisitos científicos**, que decide Nico:
   - la enmienda al `NORTH_STAR` que delega G0–G4 al agente (paper §8.3);
   - aprobar el release de datos (hoy `liquid_tick_v1` es `CANDIDATE_NOT_RESEARCH_APPROVED`);
   - cargar K1–K14 como reglas activas;
   - controles canario en cada corrida.
7. **Validación end-to-end sintética** (paper §8.2): un edge plantado, ruido y un oráculo con fuga. Si no la pasa, no hay despliegue.

## 3. Roles y modelos

| rol | qué hace | modelo | por qué |
|---|---|---|---|
| Orquestador | Máquina de estados, guardas, presupuestos, lanzar y recolectar en Kaggle | **Ningún LLM** (Python del autopilot) | El LLM nunca controla el proceso |
| Lector de corridas | Resume `summary.json` y agregados en una tabla por familia | Haiku | Mecánico, sin juicio |
| Bibliotecario | Consulta el Brain y el corpus SSRN (`ssrn_brain_cli papers/recall`) y arma fichas para el proponente | Haiku; Gemini opcional para lecturas grandes del repo | Lectura barata; la literatura nunca es evidencia |
| Cronista | Ledger, handoff, resumen a Chaski y "Aporte al referente" | Haiku | Plantillas; los números salen del ledger |
| Proponente | Familias de hipótesis nuevas, con predicción y refutación | Opus | Juicio; sólo se llama si hay pocas familias en vuelo |
| Revisor | Adjudica sobrevivientes con métricas públicas, en sesión nueva | Opus | Juicio; independiente del proponente |

Esto coincide con lo que dijo Nico: Haiku sirve para leer y lanzar, pero armar e interpretar análisis tiene que hacerlo un modelo fuerte. Gemini (ya instalado en SV1) puede bajar costo en lecturas grandes, nunca en adjudicación.

## 4. Fases

| fase | qué | cierre verificable | quién |
|---|---|---|---|
| **F0** Decisiones | Base única (`foundation`); qué ledger queda; enmienda `NORTH_STAR`; lista de datasets permitidos; rama de estado del agente | Decisiones escritas en `docs/DECISIONES_*.md` | Nico |
| **F1** Consolidar | Rebasar autopilot y Research Ops sobre `foundation`; un solo ledger de corridas; chequeos de #120 dentro del executor; cerrar #120 | Suites `autopilot` y `research_ops` verdes en contenedor Linux con Python 3.12 | agente + revisión de Nico |
| **F2** Roles LLM | Runner `claude -p` con schema; gobernador de límites; `llm_calls`; tests con LLM falso (`test_llm_schema`, `test_rate_limit`, `test_private_metrics_hidden`) | Tests verdes; un ciclo sintético completo con roles falsos | agente |
| **F3** Contenedor para SV1 | Imagen `python:3.12-slim` construida **fuera** de SV1 y traída con `docker save/load`; `compose` con `mem_limit: 1.5g`, `cpus: 1`, volumen de estado, sin puertos; timer cada 10 min fuera de 02:00–04:00; `PAUSE` por defecto | `autopilot_doctor` OK dentro del contenedor | agente arma; Gonza instala |
| **F4** Credenciales y repo | Token de Kaggle nuevo, OAuth de Claude y deploy key, en `/etc/edgelab/*.env` (0600) montados de sólo lectura | `kaggle datasets list` y `claude -p "ok"` desde el contenedor sin imprimir secretos; push a la rama de estado | **Gonza** (necesita root) |
| **F5** Puente Chaski | Reporte por ciclo a la sala; comandos `pausa`, `estado`, `aprobar`; `data_requests` | Un ciclo `propose` aparece resumido en la sala | agente |
| **F6** Validación sintética | Edge plantado, ruido, oráculo con fuga y nulo (paper §8.2) | Los cuatro criterios de éxito | agente |
| **F7** Piloto | Un día en `propose` con Haiku en roles mecánicos; medir tokens por ciclo; un round-trip barato a Kaggle verificado | Informe de consumo; corrida smoke recolectada con hashes | agente + Gonza mira |
| **F8** Primer ciclo real | `execute` sobre una familia, con datos aprobados y OK de Nico | Manifiesto con hash del referente y "Aporte al referente" | Nico autoriza |

## 5. Riesgos

- **Memoria compartida con producción.** El contenedor lleva tope de memoria y CPU, y en SV1 no se carga ningún dato de ticks: todo eso se queda en Kaggle.
- **Cuota de la suscripción.** El gobernador debe dormir los roles LLM y dejar que avance lo numérico. Opus sólo para proponer y revisar.
- **Multiplicidad.** Cada campaña cuenta y apuesta alfa antes de lanzarse. Priorizar no regala significancia.
- **Seguridad.** Los roles LLM no ven credenciales. El agente pushea sólo a su rama de estado, nunca a `foundation`. El modo `execute` lo escribe un humano en la configuración.
- **Tres diseños en paralelo.** Si F1 no consolida, va a pasar lo mismo que en el incidente de ramas del 2026-08-05.
