# DATA_LICENSE_DECISION — decisión operativa para cómputo cloud privado

**Estado:** `APPROVED` para custodia y cómputo **privado solamente**, por decisión explícita del propietario del proyecto del 2026-08-28.

Esta decisión elimina el bloqueo interno `PENDING` para preparar y subir paquetes privados de research a Kaggle. No afirma derechos de redistribución, no autoriza visibilidad pública y no convierte ticks de terceros en CC0 ni en datos abiertos.

---

## Bloque de decisión legible por máquina

No reformatear: `tools/build_kaggle_bundle.py` lee `clave: valor`, una por línea, dentro del comentario.

<!-- EDGELAB-LICENSE-GATE
schema: 2
status: APPROVED
provider: USER_CONTROLLED_CME_FEED_VIA_NINJATRADER_CONTINUUM
redistribution_allowed: false
kaggle_visibility: private_only
kaggle_license_name: other
approved_by: Nicodelcampo
approved_at_utc: 2026-08-28T17:51:54Z
terms_source_sha256: WAIVED_BY_OWNER_FOR_PRIVATE_COMPUTE_ONLY_2026-08-28
approval_basis: OWNER_DIRECTIVE_PRIVATE_CLOUD_CUSTODY_ONLY
-->

---

## Alcance exacto de la aprobación

Permitido:

- crear o actualizar un Kaggle Dataset privado bajo la cuenta del propietario;
- usar el dataset como input privado de notebooks de EdgeLab;
- ejecutar kernels congelados de EdgeLab sobre paquetes físicamente pre-holdout;
- descargar resultados y manifests para validación contractual local.

No permitido:

- cambiar la visibilidad del dataset a pública;
- compartirlo con terceros o por enlace;
- redistribuir ticks crudos o recortados;
- declarar licencias `CC0`, `PDDL`, `ODbL`, `CC-BY`, `MIT` o equivalentes;
- usar esta aprobación para abrir el holdout, outcomes o una campaña no autorizada;
- interpretar esta decisión operativa como asesoramiento o certificación legal.

## Separación entre licencia y gates científicos

Esta decisión cierra sólo el bloqueo de custodia cloud privada. Siguen siendo independientes y obligatorios:

1. verificación de bytes y SHA-256 de las fuentes;
2. recorte físico pre-holdout del dataset de research;
3. freeze del package manifest;
4. freeze del commit y del spec científico;
5. token único de ejecución de cada campaña;
6. attestation post-run y tests locales de publicación.

El dataset histórico que contiene ticks del holdout permanece `raw_custody` y no es input elegible para research aunque sea privado.

## Estado compacto

```text
PRIVATE_CLOUD_CUSTODY_APPROVED = true
KAGGLE_VISIBILITY               = private_only
REDISTRIBUTION_ALLOWED          = false
PUBLIC_DATASET_ALLOWED          = false
CC0_OR_OPEN_LICENSE_ALLOWED     = false
RESEARCH_HOLDOUT_REQUIRED       = physically_absent
CAMPAIGN_RUN_AUTHORIZED         = false
```

## Aporte al referente

Se elimina un bloqueo operativo para usar cómputo cloud privado, manteniendo separados los permisos de custodia, el sello del holdout y la autorización científica de cada corrida.
