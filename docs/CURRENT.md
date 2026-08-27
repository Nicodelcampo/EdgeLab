# CURRENT — empezar acá

> Estado operativo al 2026-08-27. Para un traspaso nuevo, el primer archivo es `AUDITOR_START_HERE.md`.

**Rama viva:** `foundation/f0b-compatibility-probe`  
**Publicación P2-A:** rama `results/bt2a-p2a-v1-r1-20260827`  
**Audited scientific base histórica:** `9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
**Referente:** `docs/NORTH_STAR.md` · sha256 del cuerpo `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Línea primaria — estado vigente

### Gate 1

BigTrap2Absorption cerró Gate 1 sobre los cinco contratos y 234 sesiones pre-holdout:

```text
K_ABS = 16.940
K_BT2 = 5.262
K_ABS − N_RAND  = +4,84; IC95% [+3,36; +6,32]
K_ABS − shuffle = +1,74; IC95% [+0,17; +3,31]
K_ABS − K_BT2   = +0,10; IC95% [−3,93; +4,16]
```

Gate 1 es una replicación post-outcome y no declara edge, confirmación ni promoción.

### P2-A V1-R1

La ejecución autorizada terminó con:

```text
status                      = COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC
classification              = P2_DIAGNOSTIC_MECHANISM_SUPPORTED
sessions/checkpoints        = 234 / 234
primary cells               = 16
secondary clock cells       = 12
validation failures         = 0
result payload sha256       = 296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28
canonical Event Store sha   = feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd
```

Celdas primarias positivas después de Holm:

- `B=9, H=25`: +0,02380852; IC95% `[0,01193237; 0,03546375]`; `p_Holm=0,00159984`.
- `B=30, H=100`: +0,01546812; IC95% `[0,00677754; 0,02387699]`; `p_Holm=0,00699930`.
- `B=30, H=250`: +0,03245809; IC95% `[0,02030684; 0,04464621]`; `p_Holm=0,00159984`.

Interpretación permitida: soporte diagnóstico del mecanismo. No es P&L realizado, no selecciona una combinación ganadora y no convierte automáticamente barreras en SL/TP.

Publicación canónica: `docs/research/bt2a_p2a_v1_r1_20260827/README.md`.

## Firewall posterior a P2-A

```text
P2A_OUTCOMES_OPENED       = true
P2B_RUN                   = false
L2_OUTCOMES_OPENED        = false
HOLDOUT_TOUCHED           = false
WINNER_SELECTED           = false
EDGE_DECLARED             = false
CONFIRMATORY_ELIGIBLE     = false
PROMOTION_ELIGIBLE        = false
```

No ejecutar P2-B, outcomes L2/HMM, abrir holdout, elegir ganador, declarar edge ni promover sin un nuevo contrato y autorización explícita.

## Ramas y PR

- Freeze remoto: `d5edeee36114849585567b768e40c061a4d0ef96`.
- Fix operativo del runner: `bdd326dcf59c0ad4db8e84a9e5de7dd2dd65e568`.
- PR #15 permanece draft/HOLD porque su head incorporó trabajo de Event Store fuera del alcance congelado.
- La publicación de resultados se mantiene en una rama separada y limpia respecto de ese drift.

## Incidente histórico vigente

Doce archivos preexistentes sin seguimiento se movieron a cuarentena con verificación bit a bit: 11 contenían outcomes y 1 era target-free.

- 11/133 sesiones de Puerta 1 expuestas;
- sellada `20260608` expuesta;
- holdout temporal tocado por cuatro contratos en investigación previa;
- búsqueda previa de contexto × outcomes;
- familia YM y barrido cross-asset expuestos.

Esto no contradice `HOLDOUT_TOUCHED=false` de P2-A: esa bandera describe exclusivamente la ejecución P2-A V1-R1, cuya máxima sesión CME fue `20260630`.

Autoridad histórica: `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md` y su manifest.

## Líneas separadas

- `research/gate-regime-context`: cimiento ejecutable, no operativo.
- `work/futures-l2-context-foundation-20260825`: contexto L2 separado; outcomes no abiertos.
- `work/crypto-context-foundation-20260824`: PR #14 draft; no mezclar con P2-A.
- `aVolClusterPOI`: exploración target-free separada; no usar para rescatar post-hoc celdas P2-A.

## No tocar sin decisión explícita

- P2-B o una política económica que convierta cada evento en entrada standalone;
- outcomes L2/HMM;
- holdout `2026-07-01`–`2026-12-31`;
- specs/splits congelados;
- selección de las tres celdas positivas como ganadoras;
- edge, confirmación o promoción;
- merge de PR #15 mientras conserve alcance mezclado;
- parquets o artefactos locales por nombre sin manifest/hash.

## Primer chequeo

```powershell
git remote -v
git fetch --all --prune
git rev-parse --show-toplevel
git rev-parse HEAD
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

El remoto reciente se llamó `github`, no `origin`.

## Índices canónicos

- `AUDITOR_START_HERE.md`
- `docs/research/bt2a_p2a_v1_r1_20260827/README.md`
- `docs/research/bt2a_p2a_v1_r1_20260827/STATUS.json`
- `docs/HANDOFF_AUDITOR_2026-08-24.md`
- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`
- `docs/BRANCH_REGISTRY_2026-08-24.md`
- `docs/research/LEER.md`
- `PENDIENTE.md`

## Aporte al referente

CURRENT incorpora el cierre real de Gate 1 y P2-A, identifica las tres celdas positivas sin seleccionarlas como ganadoras y mantiene separados P2-B, L2/HMM, holdout, edge y promoción.