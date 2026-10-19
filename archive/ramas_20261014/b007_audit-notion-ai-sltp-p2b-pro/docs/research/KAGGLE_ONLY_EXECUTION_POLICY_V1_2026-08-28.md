# Política Kaggle-Only para futuras corridas de EdgeLab V1

**Fecha de decisión:** 2026-08-28  
**Estado:** `ACTIVE_POLICY`  
**Autoridad:** directiva explícita del propietario del proyecto.

## Decisión

Toda corrida o recorrida futura que procese datos de mercado de EdgeLab se ejecutará en **Kaggle**.

```text
EXECUTION_PLATFORM            = KAGGLE_ONLY
LOCAL_HEAVY_EXECUTION_ALLOWED = false
KAGGLE_DATASET_VISIBILITY     = private_only
RESEARCH_HOLDOUT_REQUIRED     = physically_absent
CAMPAIGN_FREEZE_REQUIRED      = true
CAMPAIGN_TOKEN_REQUIRED       = true
```

## Alcance

La política aplica a:

- sweeps y reruns de indicadores;
- builders de Event Store;
- creación de checkpoints de campañas;
- mediciones target-free o de outcomes autorizadas;
- benchmarks que procesen los Parquet canónicos;
- cualquier recorrido integral sobre contratos o sesiones.

## Acciones locales permitidas

La máquina local queda limitada a tareas de custodia y certificación:

1. verificar bytes y SHA-256 de fuentes crudas;
2. construir el recorte físico pre-holdout y su effective input registry;
3. preparar y congelar specs, manifests y notebooks;
4. cargar explícitamente el paquete como dataset privado;
5. descargar `/kaggle/working/output.zip` y verificar su checksum;
6. ejecutar tests contractuales de publicación sobre los artefactos descargados;
7. publicar código, documentación y artefactos pequeños ya certificados.

Estas acciones no cuentan como corrida científica ni habilitan el kernel localmente.

## Contrato obligatorio en Kaggle

Cada campaña debe:

- usar un dataset privado físicamente pre-holdout;
- verificar el package manifest y todos sus archivos antes del kernel;
- hacer checkout detached del commit congelado;
- exigir worktree limpio, spec congelada y token propio;
- ejecutar argv sin shell;
- respetar el paralelismo declarado como semánticamente seguro;
- registrar recursos efectivos y tiempos observados;
- emitir attestation de firewalls, manifest de artefactos, ZIP determinista y SHA-256 externo;
- volver a validarse localmente antes de cualquier commit de publicación.

## Aplicación a PR #23

El rerun BigTrap2 NQ V2 no podrá ejecutarse localmente. Antes de autorizarlo deberá integrarse con el envelope de `PR #24`, consumir el package manifest/effective input registry pre-holdout y producir sus artefactos exclusivamente bajo `/kaggle/working`.

La política de plataforma no corrige ni elimina bloqueadores metodológicos o de runtime del kernel. Tampoco emite por sí sola tokens de freeze, ejecución, selección o Event Store.

## Estado de autorizaciones

```text
BIGTRAP2_SELECTION_FREEZE_TOKEN_ISSUED = false
BIGTRAP2_RERUN_AUTHORIZED              = false
BIGTRAP2_EVENT_STORE_AUTHORIZED        = false
AVOL_ES_SWEEP_RUN                      = HOLD
P2B_RUN                                = false
```

## Aporte al referente

EdgeLab concentra el cómputo pesado en un entorno cloud reproducible y deja la máquina local como frontera de custodia, empaquetado y certificación, sin alterar el sellado del holdout ni los gates científicos.
