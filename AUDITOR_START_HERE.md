# AUDITOR START HERE — EdgeLab

> **Punto de entrada único para el traspaso del 2026-08-24.**  
> Audited scientific base: `9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
> Handoff package commit: `7b360bf8f6bc4ac54ca72f771520690046f61789`  
> Rama de continuidad: `foundation/f0b-compatibility-probe`

## Lectura obligatoria

1. [`docs/HANDOFF_AUDITOR_2026-08-24.md`](docs/HANDOFF_AUDITOR_2026-08-24.md)
2. [`docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`](docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md)
3. [`docs/BRANCH_REGISTRY_2026-08-24.md`](docs/BRANCH_REGISTRY_2026-08-24.md)
4. [`docs/research/ESTADO_BT2_ABSORPTION_2026-08-24.md`](docs/research/ESTADO_BT2_ABSORPTION_2026-08-24.md)
5. [`docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`](docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md)
6. [`PENDIENTE.md`](PENDIENTE.md) y [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)

No empezar por el árbol completo de `docs/research/`; mezcla material vigente, sustituido e histórico.

## Estado en 90 segundos

- BigTrap2Absorption: Puerta 0 firmada en dos ventanas directas; paridad sobre insumo igual `~EXACT`.
- El FAIL global de tres contratos era del indexado acumulado; la paridad se recupera por sesión.
- `TAPE_VS_CHART_COVERAGE = ABIERTO`.
- Universo: 152 sesiones; split congelado 133/19, intercalado `i % 8 == 7`.
- Sweep target-free: 99 configuraciones, corriendo parcial sobre GC 02-26; no elige ganador.
- Puerta 1: **no corrida** y sin runner.
- Exposición previa: **sí** — 11/133, una sellada y contratos del holdout fueron tocados por scripts externos a la campaña.
- GATE: ejecutable como cimiento, pendiente de checkpoint real, no operativo.
- Crypto/contextos: PR #14 draft, CI roja.
- Ramas: 26/26 accesibles; ninguna protegida; no borrar ni mergear desde este checklist.

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

En el clon reciente el remoto se llamó `github`, no `origin`. Detectarlo.

## Antes de retomar el sweep

1. confirmar que HEAD sea descendiente del audited base y contenga el handoff package;
2. comprobar si existe un proceso todavía vivo;
3. inventariar recursivamente cualquier `??`;
4. verificar parciales, `run_status`, `config_id`, hashes y `head_start`;
5. continuar con `--resume`; no borrar ni relanzar a ciegas;
6. no abrir outcomes, Puerta 1 ni el holdout.

## Regla de lenguaje crítica

```text
CAMPAIGN_OUTCOMES_OPENED = false
PREEXISTING_OUTCOME_EXPOSURE = YES
```

No escribir `OUTCOMES_NOT_OPENED` como afirmación global.

## Límite de la auditoría de visibilidad

GitHub prueba que todas las refs remotas inventariadas existen. No puede probar que ninguna máquina tenga archivos adicionales. Los artefactos local-only conocidos, la cuarentena, los clones, el bundle BTC y el contenido legacy de Notion están declarados en el visibility audit y en `docs/EXTERNAL_ARTIFACTS_MANIFEST_2026-08-24.json`.

## Aporte al referente

El siguiente auditor tiene un único arranque, un estado científico acotado, las 26 ramas clasificadas y una lista explícita de lo que sólo existe fuera de Git; puede continuar sin reconstruir esta conversación ni abrir outcomes.