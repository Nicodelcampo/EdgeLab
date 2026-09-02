# AUDITOR START HERE — EdgeLab

> **Punto de entrada operativo actualizado al 2026-09-02.**  
> Rama de continuidad: `foundation/f0b-compatibility-probe`.  
> Resolver el HEAD remoto al comenzar; no copiar un hash desde un handoff.

## Lectura obligatoria

1. [`PROJECT_INDEX.md`](PROJECT_INDEX.md)
2. [`docs/CURRENT.md`](docs/CURRENT.md)
3. [`docs/OPEN_IDEAS_INDEX_2026-09-02.md`](docs/OPEN_IDEAS_INDEX_2026-09-02.md)
4. [`docs/BRANCH_REGISTRY_2026-09-02.md`](docs/BRANCH_REGISTRY_2026-09-02.md)
5. [`PENDIENTE.md`](PENDIENTE.md)
6. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)

Para la historia completa: `docs/PROJECT_CHRONOLOGY_2026-09-02.md`. Para material local-only: `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`.

No empezar por el árbol completo de `docs/research/`: mezcla evidencia vigente, material sustituido y familias distintas.

## Estado en 90 segundos

```text
REMOTE_BRANCHES                     60
OPEN_PULL_REQUESTS                  17
PROTECTED_BRANCHES                  0
PRIMARY_BRANCH                      foundation/f0b-compatibility-probe
NQ_SCAN_V2_ROWS                     119153201
NQ_MANIFEST_STATUS                  ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED
NQ_CERTIFIED_ROLLS                  0
NQ_PROVISIONAL_ROLLS                4, robustos en sensibilidad P-68
CALENDAR_BLOCKER                    acceso a horas oficiales CME por producto
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