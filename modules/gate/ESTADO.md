# GATE — estado operativo verificable

> **Rama:** `research/gate-regime-context`  
> **Estado:** `FOUNDATION_EXECUTABLE / CHECKPOINT_PENDING_REAL_DATA / NOT_YET_OPERATIONAL`  
> **Outcomes:** `NOT_OPENED`  
> **Modelo legacy:** `RETIRED_INVALID_PLACEHOLDER`

GATE sigue siendo un **etiquetador de contexto**, no una señal ni un edge. La rama ya no es
sólo el zip histórico: contiene una ruta limpia, ejecutable y testeable. Sin embargo, todavía
no existe un modelo GC formal porque este repo no contiene el archivo target-free de features
de las 152/151 sesiones. No se fabricó un checkpoint sintético para llenar ese hueco.

## 1. Ruta formal vigente

1. `core/gate_features_l1_v0.py`
   - agrega ticks en minutos `[t, t+1)`;
   - publica la feature en `t+1`, nunca en `t`;
   - usa sólo magnitudes medibles con `last/bid/ask/volume`;
   - no declara OFI ni VPIN.
2. `core/gate_hmm3_forward.py`
   - HMM Gaussiano diagonal de tres estados;
   - normalizador train-only;
   - EM por secuencias, sin transición entre sesiones ni gaps;
   - estados ordenados por RV: `calm`, `normal`, `volatile`;
   - inferencia `forward_filter_only`;
   - checkpoint con pesos, normalizador, hashes y procedencia.
3. `integration/train_label_hmm3.py`
   - `train` exige cutoff, commit real y worktree limpio;
   - `label` verifica el checkpoint y emite manifiesto;
   - no imputa filas no finitas en inferencia.
4. `core/gate_adapter_v2.py`
   - join backward por `instrument/contract/cme_session`;
   - edad máxima de feature: un minuto;
   - exige `model_id` hash-qualified;
   - falla cerrado por evento.
5. `schema/gate_context_schema_v2.json`
   - contrato point-in-time formal;
   - prohíbe estado `toxic`, cruce de identidad y nombres de microestructura no medidos.

## 2. Resolución de los once defectos

| # | defecto auditado | estado | resolución |
|---:|---|---|---|
| 1 | `gate_adapter.py` buscaba el schema en `core/` | **CORREGIDO/RETIRADO** | La ruta legacy ahora resuelve `../schema/`; las corridas formales usan v2. |
| 2 | `model_id` sin checkpoint, pesos ni normalizador | **PARCIAL: CÓDIGO CERRADO, DATO PENDIENTE** | Se retiró el nombre vacío. `fit_hmm3` genera el ID desde el hash del checkpoint; falta ejecutarlo sobre las sesiones GC reales. |
| 3 | look-ahead intrabar por barra etiquetada al inicio | **CORREGIDO** | La barra se publica al final del minuto y el test comprueba `data_window_end < feature_available_at`. |
| 4 | `config_sha256` placeholder | **CORREGIDO POR RETIRO** | El artefacto falso quedó `RETIRED_INVALID_PLACEHOLDER`; config canónica v0: `62aa3ad0058afd5ac25468dac492a57ebf45e43a6d8e313797f702954a0e9edd`. |
| 5 | `ofi` no era OFI | **CORREGIDO** | Nombre formal: `tape_imbalance`; OFI queda prohibido sin eventos/tamaños de libro. |
| 6 | `vpin` no era VPIN y definía `toxic` | **CORREGIDO** | Se eliminaron la magnitud y el cuarto estado; v0 tiene tres estados. |
| 7 | join podía cruzar instrumentos/contratos/sesiones | **CORREGIDO** | Identidad triple obligatoria. |
| 8 | join sin `tolerance` aceptaba contexto viejo | **CORREGIDO** | `max_feature_age=1min`; lo viejo devuelve `STALE_CONTEXT`. |
| 9 | faltando régimen, el pipeline inventaba terciles | **CORREGIDO** | La ruta legacy falla cerrado; no existe proxy implícito. |
| 10 | demos fabricaban eventos y el Transformer se presentaba como modelo | **RETIRADO** | `events_from_bars` aborta; el Transformer viejo queda evidencia histórica, no candidato formal. |
| 11 | no había validación sobre eventos reales ni cierre estadístico | **PENDIENTE DE DATOS/DECISIÓN** | Hace falta checkpoint real, labels point-in-time y auditoría target-free. CTX-3/outcomes siguen cerrados. |

## 3. Identidad de modelo

Familia:

```text
gate_gc_l1_hmm3_forward_v0
```

Un modelo formal sólo existe con este formato:

```text
gate_gc_l1_hmm3_forward_v0:<16 hex del checkpoint_sha256>
```

El checkpoint incluye:

- configuración y `config_sha256`;
- probabilidades iniciales y matriz de transición;
- medias y varianzas de emisiones;
- media/desvío del normalizador train-only;
- hash de la matriz de entrenamiento y cantidad de secuencias;
- commit de código;
- log-likelihood e iteraciones;
- `checkpoint_sha256` que cubre todo lo anterior.

Cambiar un byte de config, pesos, normalizador o procedencia invalida el ID.

## 4. Qué falta para pasar a `OPERATIONAL_TARGET_FREE`

1. Producir el archivo de features de las 152/151 sesiones GC sin outcomes.
2. Fijar el cutoff de train antes de ejecutar el CLI.
3. Ejecutar con worktree limpio:

```bash
python -m modules.gate.integration.train_label_hmm3 train \
  --features <features_target_free.parquet> \
  --train-cutoff <cutoff_UTC> \
  --checkpoint-out <gate_hmm3_checkpoint.json>

python -m modules.gate.integration.train_label_hmm3 label \
  --features <features_target_free.parquet> \
  --checkpoint <gate_hmm3_checkpoint.json> \
  --labels-out <gate_context_labels.parquet>
```

4. Verificar hashes/manifiestos y la invariancia de prefijo.
5. Unir labels con eventos reales por el adapter v2 y reportar cobertura/fallos.
6. Auditar ortogonalidad contra `a_thr`, hora del día y tick rate **sin abrir outcomes**.
7. Sólo luego decidir y congelar CTX-3; no hacer búsqueda post-nulo de subgrupos.

## 5. Tests agregados

- checkpoint determinista e identidad derivada de contenido;
- tampering de config/pesos falla cerrado;
- normalización sólo train;
- secuencias no contiguas rechazadas;
- invariancia de prefijo de la inferencia forward;
- schema cargado desde la ubicación correcta;
- no uso de feature futura;
- no cruce de contrato;
- contexto stale rechazado;
- `model_id` plano y estado `toxic` rechazados;
- minuto publicado al cierre y ausencia de nombres OFI/VPIN.

## 6. Historial y legado

Los commits `bc92a55`, `8d631e6`, `2a9edb5`, `e25e58a` y `9ad3db7` siguen en la historia y
conservan el ingreso, la auditoría y el protocolo original. Las rutas legacy se mantienen sólo
como evidencia y devuelven errores explícitos cuando se intenta usarlas formalmente.

## Aporte al referente

GATE dejó de ser un demo que podía producir una etiqueta plausible sin modelo real. Ahora la
causalidad, la identidad de mercado y la identidad del checkpoint son invariantes ejecutables;
el único bloqueante material restante está declarado sin maquillaje: falta correr el
entrenamiento target-free sobre los datos GC reales y auditar sus labels antes de habilitar
cualquier análisis de outcomes.
