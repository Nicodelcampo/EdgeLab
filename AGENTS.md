# EdgeLab — instrucciones permanentes de sesión

> **Punto de entrada obligatorio:** `PROJECT_INDEX.md`.  
> **Arranque del auditor:** `AUDITOR_START_HERE.md`.  
> **Estado vivo:** `docs/CURRENT.md`.  
> **Ramas:** `docs/BRANCH_REGISTRY_2026-09-02.md`.  
> **Rama viva:** `foundation/f0b-compatibility-probe`.

El referente canónico es `docs/NORTH_STAR.md`; sha256 del cuerpo anterior al marcador: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`. Si Notion, memoria del chat y repo divergen, manda el repo. Un spec o manifest congelado manda sobre un resumen general para el objeto que gobierna.

## Objetivo rector

Encontrar edges netos, robustos y ejecutables. Prioridad:

1. expectativa económica neta;
2. validez fuera de muestra;
3. robustez estadística;
4. ejecutabilidad real;
5. control de riesgo;
6. paridad, determinismo, trazabilidad y visor como medios.

Paridad exacta, infraestructura, una zona o un backtest aislado no son un edge.

## Estado obligatorio al 2026-09-02

- Rama primaria: `foundation/f0b-compatibility-probe`; resolver el HEAD remoto al comenzar. No fijarlo por memoria porque avanzó durante la auditoría.
- 60 ramas remotas observadas, 17 PR abiertas, 0 ramas protegidas.
- Línea crítica actual: régimen contractual NQ y paridad/lifecycle de aVolClusterPOI NQ.
- Manifiesto NQ v1: `PROVISIONAL_INVALID_CALENDAR / DO_NOT_USE_FOR_EF0`.
- Scan NQ v2: 119.153.201 filas, `ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED`, 0 rolls certificados.
- Sensibilidad diagnóstica P-68: los cuatro rolls provisionales son idénticos con weekdays y con weekdays menos nueve feriados; ratios idénticos a 6 decimales. Esto no certifica el manifiesto.
- El volumen del scan v2 ya excluye mantenimiento. La normalización NQ 09-26 no era una tarea pendiente.
- Calendario CME: **resuelto 2026-09-02 (`4f365bf`)**. Fuente oficial capturada y hasheada vía el endpoint JSON de cmegroup.com (el WAF sólo bloquea curl/fetch directo). 322 sesiones 2025-08-01..2026-06-18. Pendiente: Juneteenth 2026-06-19 sin adjudicar.
- NQ 09-26: 363.601 ticks en 16:00–17:00 CT sobre 9 días. Dos hipótesis descartadas; plantilla NT8 distinta es dominante pero `root_cause_status=UNRESOLVED`.
- Paridad aVolClusterPOI NQ 06-26: FAIL, con 19 `GEOMETRY_DIFF`, 57 `MISSING_IN_NT8` y 48 `MISSING_IN_PYTHON`; primero alinear el borde de ~3 ticks.
- EF0 sigue bloqueado. Outcomes, P&L y holdout requieren autorización explícita separada.
- `audit/notion-ai-sltp-p2b-provenance-20260830`: `FROZEN_READ_ONLY / DO_NOT_MERGE / DO_NOT_DELETE`.
- `CAMPAIGN_OUTCOMES_OPENED=false` nunca se usa como afirmación global: `PREEXISTING_OUTCOME_EXPOSURE=YES`.

## Primer comando y preflight de cada sesión

```powershell
git remote -v
git fetch --all --prune
git rev-parse --show-toplevel
git rev-parse HEAD
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

El remoto reciente se llamó `github`, no `origin`. Detectarlo. Si falta el entorno, reconstruirlo desde `requirements/core-bridge-dev.lock`; no relajar pins para obtener verde.

Antes de medir:

- confirmar rama, HEAD y root;
- confirmar un solo escritor por worktree;
- inventariar recursivamente cualquier directorio `??`;
- verificar que no haya otro proceso activo sobre los mismos outputs;
- resolver cada dato local por manifest/hash, no por nombre o ruta recordada.

## Reglas de integridad

- Una worktree por campaña que escribe; un solo escritor por directorio.
- Todo artefacto publica `head_start`/`head_end`, dirty/clean, datos, ventana y hashes.
- Un `code_commit` sobre árbol dirty no prueba qué código corrió.
- No usar `git clean` durante forense.
- Cuarentena: inventario → copia → hash origen/copia → recién después retiro.
- No mover ni renombrar paths ya citados sólo por estética.
- No modificar parquets reales ni particiones publicadas.
- Todo WARN/FAIL requiere causa raíz; no ampliar tolerancias después de ver resultados.
- Todo cambio de semántica de validación requiere decisión explícita de Nico.
- Verificar cada commit inmediatamente con su estadística de archivos.
- No borrar, cerrar ni mergear ramas sin verificar `docs/BRANCH_REGISTRY_2026-09-02.md`, ancestry, patches y decisión explícita.

## Firewall de outcomes y holdout

Holdout: `2026-07-01 → 2026-12-31`.

- Prohibido usarlo para elegir dirección, parámetros, contexto, entradas/salidas, costos o candidatos.
- Una validación target-free no autoriza outcomes.
- Antes de cualquier búsqueda sobre retornos/P&L: manifest de campaña, número efectivo de hipótesis, riesgos, datos faltantes y OK explícito de Nico.
- MAE/MFE, TP/SL, WinRate, Net, retornos futuros y cualquier rescate post-hoc son outcomes.
- No trasladar costos ni parámetros entre instrumentos sin justificación y preregistro.

## Camino crítico NQ

1. Obtener y hashear horarios oficiales CME Equity Index aplicables al período.
2. Completar cobertura de fuente por contrato y trade date.
3. Producir evidencia de completitud aprobable; no usar minutos activos como prueba.
4. Reconstruir el manifiesto y verificar que sobrevivan los cuatro rolls diagnósticamente robustos.
5. Reconstruir desde raw cada intervalo contractual con reset total en el roll.
6. Resolver paridad y lifecycle de aVolClusterPOI.
7. Recién después considerar EF0.

No recortar post hoc el trace existente de NQ 06-26 ni reutilizar su estado a través del roll.

## Ramas y módulos

- Primary: `foundation/f0b-compatibility-probe`.
- Auditoría divergente: congelada; sólo auditoría por merge-base, paths y patches.
- GATE: `research/gate-regime-context`; no operativo.
- Crypto/contextos: `work/crypto-context-foundation-20260824`; módulo separado.
- G2: dos contratos rivales (`fix/g2-a1-*`); no adjudicar por check verde.
- `main`, `backup/*` y `preserve/*` divergen deliberadamente.
- Ver las 60 refs en `docs/BRANCH_REGISTRY_2026-09-02.md`.

## Datos y material externo

`/data/`, parte de `runs/`, oráculos reales y cuarentenas son local-only por diseño. Su ausencia de un clon no significa inexistencia. Leer:

- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`;
- `docs/EXTERNAL_ARTIFACTS_MANIFEST_2026-08-24.json`;
- `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`.

Nunca versionar credenciales o secretos para hacerlos visibles. Visibilidad significa manifest, identidad, procedencia y responsable; no necesariamente payload.

## Rituales permanentes

- Todo checkpoint termina con **`Aporte al referente: …`**.
- Toda población enumera antes su event-space y alternativas.
- Separar evento de estado.
- Cadena: geometría/lifecycle → información → P&L bruto → edge neto/replicado.
- Todo nulo publica MDE, canal direccional, canal no direccional y distribución.
- Toda muerte tiene alcance preciso.
- Fuente antes que recuerdo; integridad antes que interpretación.
- Registro MEDIDO/NO MEDIDO se actualiza en el mismo commit que el resultado.

## Punteros

- `PROJECT_INDEX.md`
- `AUDITOR_START_HERE.md`
- `docs/CURRENT.md`
- `docs/PROJECT_CHRONOLOGY_2026-09-02.md`
- `docs/BRANCH_REGISTRY_2026-09-02.md`
- `docs/OPEN_IDEAS_INDEX_2026-09-02.md`
- `docs/NORTH_STAR.md`
- `PENDIENTE.md`
- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`
- `docs/edge_validation_contract.md`
- `docs/nt8_indicator_parity_contract.md`
- `docs/incidents/`

Los documentos del 24 y 28 de agosto preservan historia, pero ya no son el punto de entrada vigente.

## Aporte al referente

Las instrucciones de sesión apuntan al corte real del 2-sep, conservan los firewalls y distinguen robustez diagnóstica de certificación contractual.