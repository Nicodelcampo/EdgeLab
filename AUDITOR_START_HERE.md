# AUDITOR START HERE — EdgeLab

> **Punto de entrada operativo actualizado al 2026-09-02.**  
> Rama de continuidad: `foundation/f0b-compatibility-probe`.  
> Resolver el HEAD remoto al comenzar; no copiar un hash desde un handoff.

## Lectura obligatoria

1. [`PROJECT_INDEX.md`](PROJECT_INDEX.md)
2. [`docs/CURRENT.md`](docs/CURRENT.md)
3. **[`docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md`](docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md)** — **[NUEVO 2026-09-15]** Dossier de Auditoría Completa de Corredores de Vacío y Campo de Resistencia Microestructural.
4. [`docs/OPEN_IDEAS_INDEX_2026-09-02.md`](docs/OPEN_IDEAS_INDEX_2026-09-02.md)
5. [`docs/BRANCH_REGISTRY_2026-09-02.md`](docs/BRANCH_REGISTRY_2026-09-02.md)
6. [`PENDIENTE.md`](PENDIENTE.md)
7. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)

Para la historia completa: `docs/PROJECT_CHRONOLOGY_2026-09-02.md`. Para material local-only: `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`.

No empezar por el árbol completo de `docs/research/`: mezcla evidencia vigente, material sustituido y familias distintas.

## Estado en 90 segundos

```text
HP-007_VOID_CORRIDORS               CONFIRMADO (Velocidad 3.03x en tiempo real, p < 1e-9, Z_mc = 5.65)
HP-007_VECTORIAL_BACKSTOP           CONFIRMADO (+0.156 R en cortos, +0.076 R en largos vs -0.409 R contra pared)
HP-007_WALL_TO_WALL_4_7T            CONFIRMADO (42.54% hit, +0.160 R con R:R 1.73:1)
HP-007_WALL_COLLISION               CONFIRMADO (52.27% rebote limpio >= 3t, rebote medio 5.15t)
HOLDOUT_INTEGRITY                   INTACTO Y SELLADO (2026-07-01 -> 2026-12-31)
--------------------------------------------------------------------------------
REMOTE_BRANCHES                     60
OPEN_PULL_REQUESTS                  17
PROTECTED_BRANCHES                  0
PRIMARY_BRANCH                      foundation/f0b-compatibility-probe
NQ_SCAN_V2_ROWS                     119153201
NQ_MANIFEST_STATUS                  ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED
NQ_CERTIFIED_ROLLS                  0
NQ_PROVISIONAL_ROLLS                4, robustos en sensibilidad P-68
CALENDAR_STATUS                     RESUELTO 4f365bf -- 322 sesiones con evidencia hasheada; pendiente Juneteenth 2026-06-19
SOURCE_COMPLETENESS                 no aprobada
AVOLCLUSTER_NQ_PARITY               FAIL: 19 / 57 / 48
EF0                                 BLOQUEADO
PREEXISTING_OUTCOME_EXPOSURE        YES
```

Los cuatro rolls sobreviven al diagnóstico con y sin nueve feriados y con ratios idénticos a 6 decimales. Eso reduce el riesgo de que cambien, pero no certifica el calendario, la completitud ni el manifiesto.

## Primeros comandos

```powershell
git remote -v
git fetch --all --prune
git switch foundation/f0b-compatibility-probe
git pull --ff-only <remote-real> foundation/f0b-compatibility-probe
git rev-parse --show-toplevel
git rev-parse HEAD
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

En clones recientes el remoto se llamó `github`, no `origin`. Detectarlo.

## Orden de reanudación

1. Capturar y hashear horarios oficiales CME Equity Index.
2. Construir cobertura de fuente por contrato/trade date.
3. Aprobar evidencia de completitud por vía explícita; no por minutos activos.
4. Reconstruir y verificar el manifiesto NQ.
5. Reconstruir intervalos contractuales con reset en el roll.
6. Alinear el borde de ~3 ticks y resolver paridad/lifecycle aVolClusterPOI.
7. Sólo entonces evaluar autorización de EF0.

## STOP

No abrir outcomes, P&L, holdout, EF0 ni tolerancias. No certificar los cuatro rolls por el análisis de sensibilidad. No mergear la rama de auditoría divergente. No recortar post hoc el trace existente.

## Regla de lenguaje crítica

```text
CAMPAIGN_OUTCOMES_OPENED = false
PREEXISTING_OUTCOME_EXPOSURE = YES
```

No escribir `OUTCOMES_NOT_OPENED` como afirmación global.

## Aporte al referente

El siguiente auditor entra por el estado del 2-sep, ve primero el bloqueo real y no confunde estabilidad diagnóstica de rolls con certificación.