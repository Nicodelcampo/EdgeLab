# Handoff canónico para auditor — 2026-08-24

> **Audited base:** `foundation/f0b-compatibility-probe@9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
> **Repositorio:** `Nicodelcampo/EdgeLab`  
> **Rol:** punto de entrada operativo y mapa de continuidad. No reemplaza `docs/NORTH_STAR.md`, los specs congelados ni los manifiestos de campaña.

## 1. Lectura mínima, en este orden

1. `AUDITOR_START_HERE.md`
2. este documento
3. `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`
4. `docs/BRANCH_REGISTRY_2026-08-24.md`
5. `docs/research/ESTADO_BT2_ABSORPTION_2026-08-24.md`
6. `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`
7. `PENDIENTE.md` y `docs/NORTH_STAR.md`

No empezar leyendo el directorio completo `docs/research/`: contiene historia válida, documentos sustituidos y resultados de familias distintas.

## 2. Estado ejecutivo al corte

```text
PRIMARY_BRANCH                    foundation/f0b-compatibility-probe
AUDITED_BASE                      9b23c307cb112cdd6392d98673e8ead2e8bc4698
MAIN_BASELINE                     cde6d93a75240f550db1fc3b96ca90605ca967c8
REMOTE_BRANCHES                   26, todas resolubles en GitHub
PROTECTED_BRANCHES                0
OPEN_PULL_REQUESTS                6, todas draft
BT2A_PUERTA_0                     firmada en dos ventanas directas
KERNEL_PARITY_ON_EQUAL_INPUT      ~EXACT
GLOBAL_ACCUMULATED_PARITY         FAIL por índice global
SESSION_RECOVERABLE_PARITY        RECOVERED
TAPE_VS_CHART_COVERAGE            ABIERTO
BT2A_UNIVERSE                     152 sesiones
BT2A_SPLIT                        133 / 19, intercalado i % 8 == 7
BT2A_TARGET_FREE_SWEEP            EN CURSO, parcial GC 02-26
BT2A_PUERTA_1                     NO CORRIDA; runner inexistente
PREEXISTING_OUTCOME_EXPOSURE      YES
CAMPAIGN_OUTCOMES_OPENED          false, sólo para el sweep 2026-08-24
GATE_MODULE                       FOUNDATION_EXECUTABLE / CHECKPOINT_PENDING_REAL_DATA / NOT_YET_OPERATIONAL
CRYPTO_CONTEXT                    rama separada + PR #14, CI roja
```

**Nada del corte declara edge.** El sweep vigente no mira outcomes ni puede elegir un ganador.

## 3. Qué estaba corriendo y cómo retomarlo

La campaña activa es el barrido target-free de BigTrap2Absorption:

- spec: `specs/bt2_absorption_target_free_sweep_v1.json`;
- runner: `tools/bt2_absorption_param_sweep.py`;
- protocolo: `docs/research/BT2_ABSORPTION_SWEEP_OVERNIGHT_2026-08-24.md`;
- 99 configuraciones únicas: 51 OAT + 48 interacciones;
- ejecución actual: sólo `GC 02-26` mediante `--contracts`;
- salida parcial obligatoria: `COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS`;
- la corrida completa de cuatro contratos no se declara por inferencia.

La calibración real dio una dispersión de tiempo de 13× sobre la misma cinta. La población generada por la configuración, no la cantidad de ticks, domina el costo. No relanzar desde cero sin inspeccionar parciales y proceso vivo.

### Secuencia de reanudación

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

En el clon que produjo el incidente, el remoto se llamaba **`github`**, no `origin`. Detectarlo; no asumirlo.

Después:

1. comprobar si existe un proceso del sweep todavía vivo;
2. inspeccionar `run_status`, parciales y `config_id` ya materializados;
3. verificar que HEAD y árbol limpio coincidan con la procedencia de cada parcial;
4. continuar con `--resume`, nunca borrando parciales;
5. al finalizar, publicar manifest, estado parcial, contratos medidos/omitidos y hashes;
6. no abrir Puerta 1 ni outcomes como parte de esa continuidad.

## 4. Incidente que condiciona toda lectura futura

Antes del sweep se detectó un drop de **12 archivos sin seguimiento**: 11 con outcomes y 1 target-free. Se preservaron en cuarentena y se registró un manifest remoto; los bytes no están en GitHub.

Consecuencias confirmadas:

- 11 de las 133 sesiones de Puerta 1 tuvieron exposición a outcomes;
- la sellada `20260608` fue expuesta;
- cuatro contratos del holdout temporal fueron leídos por scripts previos;
- hubo búsqueda de contexto por hora × outcomes;
- hubo barrido cross-asset y exposición de la familia YM.

Regla de lenguaje obligatoria:

```text
CAMPAIGN_OUTCOMES_OPENED = false
PREEXISTING_OUTCOME_EXPOSURE = YES
```

Nunca resumir eso como `OUTCOMES_NOT_OPENED` global.

## 5. Ramas: mapa operativo

El inventario completo, con los 26 tips, URLs, PR y acción siguiente, está en:

- `docs/BRANCH_REGISTRY_2026-08-24.md`;
- `docs/BRANCH_REGISTRY_2026-08-24.json`.

### Ramas que un auditor debe mirar primero

| Rama | Estado | Acción |
|---|---|---|
| `foundation/f0b-compatibility-probe` | primaria | único punto de integración y continuidad |
| `work/crypto-context-foundation-20260824` | PR #14 draft, CI roja | auditar fallas; no mergear |
| `research/gate-regime-context` | módulo separado, sin PR | checkpoint con datos reales; no tratar como operativo |
| `fix/g2-a1-calibration-hardening` | PR #8 verde | bloqueada por adjudicación semántica P-10/P-38 |
| `fix/g2-a1-statistical-semantics` | contrato rival | adjudicar junto con la anterior, no por separado |
| `research/zamr1-zone-atlas` | PR #13 verde | histórica/parqueada; base vieja |
| `research/bigtrap2-distance-matched-null` | PR #11 sin checks | patch-equivalent según inventario 2026-08-15; no duplicar historia |
| `fix/bigtrap2-v252-tick-export` | PR #12 sin checks | línea histórica; revisar contra foundation antes de cualquier merge |
| `prep/indicator-onboarding-registry` | PR #9 verde | F9 aparcada; no prioritaria |

No borrar ni cerrar ramas como parte de este handoff. El registro las hace visibles; la adjudicación sigue siendo separada.

## 6. Pull requests abiertos al corte

| PR | Head → base | CI observada | Lectura |
|---:|---|---|---|
| #14 | `work/crypto-context-foundation-20260824` → foundation | **2 fallas** | activo, bloqueado |
| #13 | `research/zamr1-zone-atlas` → local-displacement | **2 éxitos** | base histórica, draft |
| #12 | `fix/bigtrap2-v252-tick-export` → audit/p0 | sin check-runs | no interpretar como verde |
| #11 | `research/bigtrap2-distance-matched-null` → audit/p0 | sin check-runs | línea pre-rebase/superada según inventario previo |
| #9 | `prep/indicator-onboarding-registry` → foundation | **1 éxito** | aparcado |
| #8 | `fix/g2-a1-calibration-hardening` → foundation | **2 éxitos** | verde técnico, bloqueado semánticamente |

Todos son draft. Un check verde no adjudica semántica ni vigencia; ausencia de check no es verde.

## 7. GATE y crypto/contextos

### GATE

Rama `research/gate-regime-context@c882cf521104f4ab0199dfe4db09118bb72836a9`.

- once defectos auditados;
- look-ahead intrabar retirado;
- join point-in-time endurecido;
- features L1 renombradas honestamente;
- HMM3 entrenable con identidad verificable;
- estado: `FOUNDATION_EXECUTABLE`, `CHECKPOINT_PENDING_REAL_DATA`, `NOT_YET_OPERATIONAL`.

No bloquea el sweep ni Puerta 1. No debe usarse todavía como filtro de trading.

### Crypto/contextos

Rama `work/crypto-context-foundation-20260824@973a06fa8f1240ad064d75e136805ae5072fb721`, PR #14.

- adaptador causal Binance USD-M;
- contrato point-in-time;
- features L1 honestas;
- piloto local BTCUSDT registrado fuera de GitHub;
- CI roja al corte.

Debe auditarse como módulo separado. No transportar conclusiones de GC ni declarar que el piloto probó edge.

## 8. Qué no está en GitHub

GitHub permite afirmar que las 26 referencias remotas existen. **No permite afirmar que una máquina local no tenga más material.** Lo conocido fuera del remoto está declarado en:

- `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md`;
- `docs/EXTERNAL_ARTIFACTS_MANIFEST_2026-08-24.json`.

Incluye: raw data gitignored, runtime outputs, oráculos reales no seleccionados, cuarentena del incidente, bundle del piloto BTC y las entradas 001–005 del canal que sólo sobrevivieron como resumen.

## 9. Señales de STOP para el auditor siguiente

Detenerse y registrar antes de seguir si ocurre cualquiera:

- árbol dirty o untracked inesperado;
- más de un escritor sobre el mismo worktree;
- parcial cuyo `head_start` no coincide con su código;
- intento de abrir outcomes o holdout sin autorización;
- merge de una rama no clasificada;
- ruta local que apunta a otro clon;
- resultado que usa `runs/`, `/data/` u `oracles/` sin manifest/hash resoluble;
- uso de `OUTCOMES_NOT_OPENED` como afirmación global;
- conversión de `TAPE_VS_CHART_COVERAGE = ABIERTO` en paridad exacta global.

## 10. Criterio de traspaso completo

El siguiente auditor puede retomar sin esta conversación si puede:

1. resolver el audited base y el HEAD actual;
2. enumerar las 26 ramas desde el registry;
3. distinguir las dos líneas activas separadas de las históricas;
4. localizar los seis PRs y sus checks;
5. localizar la cuarentena por manifest sin necesitar sus outcomes;
6. continuar el sweep desde parciales, sin relanzar ni abrir outcomes;
7. explicar por qué Puerta 1 todavía no se ejecuta;
8. nombrar qué información es local-only y quién debe proveerla.

## Aporte al referente

El traspaso deja de depender de reconstruir un chat: separa estado científico, ramas, PRs, datos externos e incidentes en registros auditables. Reduce el riesgo de duplicar campañas, usar una rama superada o confundir una corrida target-free con ausencia global de exposición.