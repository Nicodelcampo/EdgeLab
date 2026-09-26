# Ejecución Kaggle — EF0 aVolClusterPOI NQ 06-26

**Estado:** `READY_TO_RUN`  
**Costo:** postproceso liviano; no vuelve a leer los 34.203.535 ticks.  
**Salida:** perfil estructural y preguntas para EF1; no ejecuta EF1.

## Identidades fijadas

- launcher: commit `58496ad6d69f9335e684f55a9d5e8672819e5299`;
- código EF0 ejecutado: `4b0e5b3c6cf359447b2b81dcb9a1f4f873fcca97`;
- trace fuente: `eafbc0380253e029acc969e07c17ebb7912ef7ec`.

El launcher también fija los hashes informados del trace:

- `all_blocks.json`: `c4d17510e45dd8492e580c6493478390e852b73174a5509efd853c05ce9fa691`;
- `zones.json`: `9598416abfc4b4dabda3a96cb26fb68078de3abf3663fd3727c492d0e773bff6`;
- `summary.json`: `629905624528af777211eee7c09b3cedddfa09cc7b2067b0a0cefa7b24f1fb57`;
- `sha256_manifest.json`: `e6470f09a9adcac5d5b46ecd5dcc9fe4406ab87eb85211a438ff3e54d7c48dc8`.

Un mismatch detiene la corrida; no existe bypass.

## Input Kaggle

Crear un notebook nuevo y adjuntar como único input el output del kernel:

```text
nicolasbuttaro/avolclusterpoi-tracedump-full-nq0626
```

Puede estar expuesto como carpeta con los JSON o sólo como
`avolclusterpoi_tracedump_full.zip`; el launcher soporta ambas formas. No
adjuntar dos copias del bundle porque la identidad quedaría ambigua.

Internet debe estar habilitado únicamente para clonar el commit fijado. El
runner no descarga ni procesa el parquet original.

## Celda de ejecución

```bash
git clone --filter=blob:none --no-checkout \
  https://github.com/Nicodelcampo/EdgeLab.git \
  /kaggle/working/EdgeLab-launcher

git -C /kaggle/working/EdgeLab-launcher fetch origin \
  58496ad6d69f9335e684f55a9d5e8672819e5299 --depth 200

git -C /kaggle/working/EdgeLab-launcher checkout --detach \
  58496ad6d69f9335e684f55a9d5e8672819e5299

python /kaggle/working/EdgeLab-launcher/notebooks/kaggle/avolclusterpoi_ef0_funnel_runner.py
```

## Preflights obligatorios

```text
n_blocks = 28477
n_create_candidates = 658
n_zones_off_price = 414
n_at_price_candidates = 244

decisions:
  ABSTAIN_BELOW_THRESHOLD = 25002
  ABSTAIN_NO_CLUSTER = 1694
  ABSTAIN_NO_HISTORY = 1123
  CREATE = 658
```

También deben cerrar:

- scope pre-holdout target-free;
- hash de cada archivo fuente;
- manifest interno;
- identidad única de bloque;
- referencias completas de zonas;
- ausencia de campos de outcomes/P&L;
- `history_samples == n_history_scores`.

## Salidas

Directorio:

```text
/kaggle/working/avolclusterpoi_ef0/
```

Archivos:

- `ef0_integrity.json`;
- `ef0_profile.json`;
- `ef0_question_cards.json`;
- `ef0_status.json`;
- `sha256_manifest.json`.

Bundle descargable:

```text
/kaggle/working/avolclusterpoi_ef0_bundle.zip
```

La consola debe terminar con:

```text
next_stage= BLOCKED_PENDING_REVIEWED_EF1_PLAN_AND_AUTHORIZATION
outcomes_accessed= False
```

## Entrega

Devolver:

1. `avolclusterpoi_ef0_bundle.zip`;
2. log completo;
3. SHA-256 del ZIP;
4. estado de cada preflight.

Detenerse ahí. No crear grilla, no correr configuraciones y no abrir outcomes.
Las tarjetas EF0 serán auditadas y recién entonces se redactará el plan EF1.

**Aporte al referente:** obtiene un mapa estructural barato del detector y deja
que la evidencia inicial determine qué eje merece una corrida posterior, sin
pagar todavía un multiverso ni mirar resultados económicos.
