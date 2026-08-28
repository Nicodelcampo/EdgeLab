# EdgeLab — instrucciones permanentes de sesión

> **Punto de entrada obligatorio:** `AUDITOR_START_HERE.md`.  
> **Estado vivo:** `docs/CURRENT.md`.  
> **Handoff 2026-08-24:** `docs/HANDOFF_AUDITOR_2026-08-24.md`.  
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

## Estado obligatorio al 2026-08-24

- BigTrap2Absorption es la línea primaria.
- Puerta 0 está firmada en dos ventanas directas.
- `KERNEL_PARITY_ON_EQUAL_INPUT = ~EXACT`.
- `GLOBAL_ACCUMULATED_PARITY = FAIL` por el indexado global; `SESSION_RECOVERABLE_PARITY = RECOVERED`.
- `TAPE_VS_CHART_COVERAGE = ABIERTO`.
- Universo 152; split congelado 133/19 con regla `i % 8 == 7`.
- Sweep target-free de 99 configuraciones en curso, parcial sobre GC 02-26.
- Puerta 1 no se corrió y no existe runner.
- `CAMPAIGN_OUTCOMES_OPENED=false` describe sólo el sweep actual.
- `PREEXISTING_OUTCOME_EXPOSURE=YES`: 11/133, la sellada `20260608`, cuatro contratos del holdout y búsquedas de contexto/cross-asset quedaron expuestos por scripts previos.
- GATE es cimiento ejecutable, pendiente de checkpoint real, no operativo.
- Crypto/contextos vive en una rama separada; PR #14 tiene CI roja.
- Hay 26 ramas remotas accesibles y ninguna protegida; ver el registry antes de tocar una.

**Prohibido escribir `OUTCOMES_NOT_OPENED` como afirmación global.**

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
- No borrar, cerrar ni mergear ramas sin la clasificación de `docs/BRANCH_REGISTRY_2026-08-24.md` y una decisión explícita.

## Firewall de outcomes y holdout

Holdout: `2026-07-01 → 2026-12-31`.

- Prohibido usarlo para elegir dirección, parámetros, contexto, entradas/salidas, costos o candidatos.
- Una validación target-free no autoriza outcomes.
- Antes de cualquier búsqueda sobre retornos/P&L: manifest de campaña, número efectivo de hipótesis, riesgos, datos faltantes y OK explícito de Nico.
- MAE/MFE, TP/SL, WinRate, Net, retornos futuros y cualquier rescate post-hoc son outcomes.
- No trasladar costos ni parámetros entre instrumentos sin justificación y preregistro.

## Reanudación del sweep BT2Absorption

- Leer `docs/research/BT2_ABSORPTION_SWEEP_OVERNIGHT_2026-08-24.md` y el estado consolidado.
- No relanzar a ciegas: inspeccionar proceso, parciales, `run_status`, `config_id`, hashes y procedencia.
- Continuar con `--resume`.
- Un subconjunto de contratos se etiqueta `COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS`.
- No seleccionar un ganador: el sweep sólo mapea sensibilidad estructural.
- No implementar ni ejecutar Puerta 1 como parte de esa continuidad.

## Ramas y módulos

- Primary: `foundation/f0b-compatibility-probe`.
- GATE: `research/gate-regime-context`; no operativo.
- Crypto/contextos: `work/crypto-context-foundation-20260824`; PR #14 roja.
- G2: dos contratos rivales (`fix/g2-a1-*`); no adjudicar por check verde.
- `main`, `backup/*` y `preserve/*` divergen deliberadamente.
- Las 26 ramas, tips y acciones están en `docs/BRANCH_REGISTRY_2026-08-24.md`.

## Datos y material externo

`/data/`, parte de `runs/`, oráculos reales y cuarentenas son local-only por diseño. Su ausencia de un clon no significa inexistencia. Leer:

- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`;
- `docs/EXTERNAL_ARTIFACTS_MANIFEST_2026-08-24.json`;
- `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`.

Nunca versionar credenciales o secretos para hacerlos «visibles». Visibilidad significa manifest, identidad, procedencia y responsable; no necesariamente payload.

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

- `AUDITOR_START_HERE.md`
- `docs/CURRENT.md`
- `docs/HANDOFF_AUDITOR_2026-08-24.md`
- `docs/NORTH_STAR.md`
- `PENDIENTE.md`
- `docs/BRANCH_REGISTRY_2026-08-24.md`
- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`
- `docs/edge_validation_contract.md`
- `docs/nt8_indicator_parity_contract.md`
- `docs/incidents/`

El detalle histórico retirado de este archivo sigue disponible en Git y en los documentos citados. No inferir que una regla histórica desapareció sólo porque su prosa ya no está duplicada acá; verificar la autoridad específica antes de cambiar comportamiento.

## Aporte al referente

Las instrucciones de sesión ya no arrancan desde el 10-ago ni afirman un holdout intacto. El preflight, el incidente, las ramas y la campaña viva quedan alineados con el estado remoto que el siguiente auditor efectivamente encontrará.
