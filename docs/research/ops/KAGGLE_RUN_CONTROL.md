# Research Ops — control de corridas en Kaggle (hito 4)

Estado: PROTOTIPO, probado con cliente falso y con una lectura real de estado. No lanza nada por sí solo.

Cubre el paso 4 de `CLAUDE_HANDOFF.md` ("control operacional remoto sobre Kaggle"): identidad del job, versión, consulta acotada, descarga y verificación de salidas, límites de concurrencia y de corridas, y un ledger durable entre reinicios. Usa la misma receta de cadena de hashes que `CheckpointLedger` y `DispatchLedger`.

## Qué hace

`tools/research_ops/kaggle_runs.py`:

- **`KagglePolicy`**: cuenta dueña de los kernels, lista cerrada de datasets montables, presupuesto total de corridas y concurrencia máxima (≤ 5, el límite operacional de Kaggle). Se fija una sola vez por ledger.
- **`kernel_dir_identity`**: antes de reservar, revisa `kernel-metadata.json` y falla cerrado si el kernel:
  - no es privado o tiene internet;
  - pertenece a otra cuenta;
  - monta un dataset fuera de la lista, otra competencia u otro kernel;
  - tiene el código fuera de su directorio.

  Devuelve el sha256 del metadata más el código.
- **`KaggleRunLedger`**: estados `RESERVED → SUBMITTED → RUNNING → COMPLETE_TECHNICAL → COLLECTED_VERIFIED | COLLECTION_INCOMPLETE`, más `FAILED`. Transiciones ilegales, proyecciones alteradas o cadena rota fallan cerrado.
- **`KaggleRunController`**:
  - `submit` reserva primero (cobra presupuesto) y después hace push.
  - `poll` hace una pasada acotada sobre las corridas activas.
  - `collect` baja las salidas a un directorio nuevo y registra sha256 y tamaño de cada salida esperada.
- **`KaggleCli`**: el único lugar con red. Usa argv fijo, sin shell, con timeout.

## Garantías

| regla | cómo se cumple |
|---|---|
| El presupuesto se cobra antes de que algo salga de la máquina, y no se devuelve | `reserve` antes del push; un push fallido queda `FAILED` y cobrado |
| No hay reintentos | Un id usado no se reusa; un reemplazo necesita id nuevo |
| No se pushea sobre una versión viva | Un kernel con corrida activa no admite otra reserva |
| Concurrencia ≤ política ≤ 5 | Se controla en `reserve` |
| Lo que se sube es exactamente lo reservado | El hash del directorio se recalcula justo antes del push |
| Estados desconocidos no mueven el ledger | `poll` informa `UNKNOWN_STATUS_*` y no escribe |
| Salidas nunca sobrescritas | `collect` exige directorio nuevo; una corrida se recolecta una sola vez |
| Verificado ≠ válido | `COLLECTED_VERIFIED` sólo afirma que las salidas esperadas existen y no están vacías; `results_certified` y `retries_allowed` son siempre `False` |

Una caída entre reserva y push deja la corrida en `RESERVED`, y `poll` la reporta como `RESERVED_NOT_PUSHED`. Eso pide revisión humana: no se pushea solo.

## CLI

```bash
S=artifacts/research_ops/kaggle.sqlite
python -m tools.research_ops.cli kaggle-init --kaggle-state $S --owner nicolasbuttaro \
  --dataset nicolasbuttaro/edgelab-data-catalog --dataset nicolasbuttaro/edgelab-code-avcl-fast \
  --max-runs 20 --max-concurrent 3
python -m tools.research_ops.cli kaggle-submit  --kaggle-state $S RUN-0001 path/al/kernel --expect MNQ_09-25_x.parquet
python -m tools.research_ops.cli kaggle-poll    --kaggle-state $S
python -m tools.research_ops.cli kaggle-collect --kaggle-state $S RUN-0001 artifacts/research_ops/outputs
python -m tools.research_ops.cli kaggle-verify  --kaggle-state $S [--expected-tip TIP]
python -m tools.research_ops.cli status --kaggle-state $S      # sólo lectura; no crea nada
```

Las credenciales se leen del entorno del proceso (`KAGGLE_API_TOKEN` o `~/.kaggle`). Nunca pasan por la línea de comandos, el ledger ni la sala.

## Operación desde ccbus (worker en Debian)

La idea es que el agente de gonzasib, conectado a la sala por ccbus, sea el operador:

1. **Solo lectura, sin pedir permiso**: `status`, `kaggle-verify`, `kaggle-poll`. `poll` escribe en el ledger, pero sólo transiciones que Kaggle informó.
2. **Con autorización explícita en la sala**: `kaggle-submit` de un kernel cuyo manifiesto esté commiteado, y `kaggle-collect`.
3. **Nunca**: `kaggle-init` con otra política sobre un ledger existente (lo rechaza), reintentar un id, borrar el ledger para recuperar presupuesto, o lanzar código generado en el momento.

Conviene guardar el `tip` que devuelve cada comando fuera de la máquina (por ejemplo, publicado en la sala). Así un rollback del archivo se detecta con `--expected-tip`. El ledger solo no protege contra quien controla el host.

## Qué falta (no está hecho)

- Enlazar `kaggle-collect` con `CheckpointLedger`, para que una unidad recolectada registre su checkpoint.
- Un scheduler que decida qué lanzar. Este módulo sólo ejecuta lo que se le indica.
- Witness y fencing remotos, y alertas.
- Las pruebas usan un cliente falso. La única llamada real verificada es `status` sobre un kernel terminado (lectura). Push y output reales no se ejercitaron con este módulo.

## Pruebas

`tests/research_ops/test_kaggle_runs.py`: 12 tests, todos verdes.

En Windows, la suite completa de `tests/research_ops` da 67 errores con y sin este cambio (252 → 264 tests). Son de los tests POSIX del worker (`Bad file descriptor`, symlinks). En Linux deberían pasar, pero no lo corrí ahí.
