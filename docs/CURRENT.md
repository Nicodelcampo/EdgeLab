# CURRENT — empezar acá

> Estado operativo al 2026-08-24. Para un traspaso nuevo, el primer archivo es `AUDITOR_START_HERE.md`.

**Rama viva:** `foundation/f0b-compatibility-probe`  
**Audited scientific base:** `9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
**Handoff package:** `7b360bf8f6bc4ac54ca72f771520690046f61789`  
**Referente:** `docs/NORTH_STAR.md` · sha256 del cuerpo `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Línea primaria

**BigTrap2Absorption — sweep target-free parcial sobre GC 02-26.**

- 99 configuraciones únicas: 51 OAT + 48 interacciones.
- Estado esperado para un subconjunto: `COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS`.
- El sweep no mira outcomes, no elige ganador y no es Puerta 1.
- Puerta 1 no se corrió y su runner no existe.
- No relanzar: inspeccionar proceso, parciales, `run_status`, `config_id`, hashes y procedencia; continuar con `--resume`.

Acta: `docs/research/ESTADO_BT2_ABSORPTION_2026-08-24.md`.

## Vector de estado BT2Absorption

```text
PUERTA_0_FIRMADA                = SI
KERNEL_PARITY_ON_EQUAL_INPUT    = ~EXACT
GLOBAL_ACCUMULATED_PARITY       = FAIL por indexado acumulado
SESSION_RECOVERABLE_PARITY      = RECOVERED
TAPE_VS_CHART_COVERAGE          = ABIERTO
UNIVERSO                        = 152 sesiones
SPLIT                           = 133 / 19, i % 8 == 7
SWEEP_TARGET_FREE               = EN CURSO, GC 02-26
PUERTA_1                        = NO CORRIDA
CAMPAIGN_OUTCOMES_OPENED        = false
PREEXISTING_OUTCOME_EXPOSURE    = YES
```

No resumir las dos últimas líneas como `OUTCOMES_NOT_OPENED` global.

## Incidente vigente

Doce archivos preexistentes sin seguimiento se movieron a cuarentena con verificación bit a bit: 11 contenían outcomes y 1 era target-free.

- 11/133 sesiones de Puerta 1 expuestas;
- sellada `20260608` expuesta;
- holdout temporal tocado por cuatro contratos;
- búsqueda previa de contexto × outcomes;
- familia YM y barrido cross-asset expuestos.

Autoridad: `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md` y su manifest.

## Líneas separadas

- `research/gate-regime-context`: `FOUNDATION_EXECUTABLE`, `CHECKPOINT_PENDING_REAL_DATA`, `NOT_YET_OPERATIONAL`.
- `work/crypto-context-foundation-20260824`: PR #14 draft; CI roja; no mergear.
- Las restantes 23 ramas no primarias están clasificadas en `docs/BRANCH_REGISTRY_2026-08-24.md`.

## No tocar sin decisión explícita

- outcomes, P&L, MAE/MFE o Puerta 1;
- holdout para diseñar o elegir;
- specs/splits congelados;
- ramas G2 rivales;
- borrado/cierre de ramas;
- parquets o particiones publicadas;
- cuarentena del incidente;
- `TAPE_VS_CHART_COVERAGE` como si estuviera resuelto.

## Primer chequeo

```powershell
git remote -v
git fetch --all --prune
git rev-parse --show-toplevel
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

El remoto reciente se llamó `github`, no `origin`.

## Índices canónicos

- `AUDITOR_START_HERE.md`
- `docs/HANDOFF_AUDITOR_2026-08-24.md`
- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`
- `docs/BRANCH_REGISTRY_2026-08-24.md`
- `docs/research/LEER.md`
- `PENDIENTE.md`

## Aporte al referente

CURRENT vuelve a describir el trabajo realmente vivo y hace explícita la exposición previa. El auditor puede continuar el sweep target-free sin confundirlo con Puerta 1, con un holdout intacto o con evidencia de edge.