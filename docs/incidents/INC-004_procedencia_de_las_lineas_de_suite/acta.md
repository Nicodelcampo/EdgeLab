# INC-004: Procedencia de las Líneas de Suite

## Origen

Derivado de INC-003 §98. La investigación de entorno cerró la rama de restauración
pero reveló un problema lógico independiente que no se resuelve con un .venv.

## Hechos Establecidos

### El contrato y sus fechas

| Fecha | Evento | Commit |
|---|---|---|
| 2026-07-16 21:12 | Ruptura del intérprete global (streamlit) | — |
| 2026-07-21 18:20 | Se introduce `test_environment_contract.py` | `49289a1` |
| 2026-07-28 | Se reporta `490 passed` (§88) | — |
| 2026-07-31 03:08 | Se reporta `510 passed, 3 deselected` | `ee257bc` |
| 2026-07-31 18:53 | Primera corrida verificada: `510 passed, 3 deselected` en `.venv` canónico | `76b9900` |

### El inventario de intérpretes (§98, exhaustivo)

| Intérprete | pyarrow | ¿Puede pasar `test_environment_contract` (pyarrow >= 25)? |
|---|---|---|
| Global (`C:\Users\Usuario\...\python.exe`) | 20.0.0 | **No** |
| `C:\Freqtrade\...\venv` | 22.0.0 | **No** |
| `C:\NicoEdgeFinder\...\venv` | 18.1.0 | **No** |
| `C:\TradingPlayground\.venv` | 24.0.0 | **No** (por un major) |
| `E:\EdgeLab\sidecar\kronos_env` | no instalado | **No** |
| `E:\EdgeLab\.venv` (creado 2026-07-31 18:5x) | 25.0.0 | **Sí** — primer intérprete capaz |

### La deducción

`test_environment_contract.py` existía y se recolectaba en toda corrida desde el 21 de julio.
Ningún intérprete presente en la máquina antes del 31 de julio a las 18:5x podía pasarlo.
Ergo, las líneas `490 passed` y `510 passed` reportadas entre el 28 y el 31 de julio
**no pudieron producirse ejecutando la suite completa sobre esta máquina**.

Hipótesis descartadas:
- **H1** (intérprete global): pyarrow 20.0.0, refutada.
- **H2** (otro venv de la máquina): inventario exhaustivo, ninguno tiene pyarrow >= 25, refutada.

Hipótesis restante por eliminación:
- **H3**: Las líneas no provienen de una corrida completa de la suite tal como se reportaron.
  Posibles explicaciones (sin implicar mala fe): corrida parcial, subconjunto de tests,
  línea copiada de un entorno efímero, o salida editada.

### Testigo independiente: la duración

| Corrida | Resultado | Duración |
|---|---|---|
| §88 (490 passed) | 490 passed, 3 deselected | 142.31s |
| Intérprete roto (producción) | 472 passed, 24 failed | 270.16s |
| `.venv` verificado (§98) | 510 passed, 3 deselected | 673.95s |

142.31s para 490 passed vs 673.95s para 510 passed con intérprete verificado.
Menos tiempo con más tests verdes no es variación de máquina.

**Dato pendiente:** duración del 510 de `ee257bc` — está en el hilo donde se reportó.

## Línea de Investigación Abierta

### Procedencia de los parquets

`C:\TradingPlayground\.venv` tiene `pandas 3.0.3` — el mismo que aparece en la metadata
`pandas_version` de los parquets de EdgeLab. El campo `created_by` del footer Parquet
registra la versión de Arrow usada para escribir:
- Si dice `pyarrow 24.x` → los parquets se escribieron desde TradingPlayground.
- Si dice `pyarrow 25.x` → se escribieron desde un entorno que ya no existe en la máquina.

**Lectura realizada: 2026-07-31 20:19 (Gemini, desde `.venv` canónico).**

| Parquet | `created_by` | `pandas_version` | `creator` |
|---|---|---|---|
| 6E_03-26_ticks | pyarrow 25.0.0 | 3.0.3 | pyarrow 25.0.0 |
| 6E_06-26_ticks | pyarrow 25.0.0 | 3.0.3 | pyarrow 25.0.0 |
| 6E_09-25_ticks | pyarrow 25.0.0 | 3.0.3 | pyarrow 25.0.0 |
| 6E_09-26_ticks | pyarrow 25.0.0 | 3.0.3 | pyarrow 25.0.0 |
| 6E_12-25_ticks | pyarrow 25.0.0 | 3.0.3 | pyarrow 25.0.0 |
| 6E_all_contracts | pyarrow 25.0.0 | — | — |
| ES_03-26_ticks | pyarrow 25.0.0 | — | — |
| NQ_03-26_ticks | pyarrow 25.0.0 | — | — |
| GC_02-26_ticks | pyarrow 25.0.0 | — | — |
| es_full_ticks (legacy) | pyarrow 22.0.0 | 3.0.3 | pyarrow 22.0.0 |
| nq_m1_clean (legacy) | pyarrow 20.0.0 | 2.2.2 | pyarrow 20.0.0 |

**Interpretación**: Todos los parquets F2 canónicos (`data/nt8/`) dicen `pyarrow 25.0.0`.
TradingPlayground tiene pyarrow 24.0.0 → **no los escribió**. Ningún intérprete presente
en la máquina al momento del inventario (§98) tiene pyarrow 25 excepto `E:\EdgeLab\.venv`,
creado el 2026-07-31 a las 18:5x. Los parquets son anteriores a esa fecha.

Esto corrobora H3 por una vía independiente: el entorno que produjo los parquets F2 **ya no
existe en la máquina**. Los archivos legacy (`es_full_ticks`, `nq_*`) fueron escritos con
versiones anteriores (22.0.0 y 20.0.0), coherentes con los intérpretes que sí existen.

**Estado:** LEÍDO. No se requiere acción adicional sobre esta línea.

## Regla de Operación (a incorporar en el proyecto)

A partir de este incidente, todo turno que reporte una línea de suite debe declarar:
1. `sys.executable` — el intérprete usado.
2. La línea completa de pytest incluyendo `passed`, `failed`, `skipped`, `deselected`.
3. La duración.

Sin estos tres datos, la línea no tiene valor probatorio.

El `.venv` de `E:\EdgeLab\.venv` es **obligatorio** para toda corrida.
El intérprete global no se usa para EdgeLab bajo ninguna circunstancia.
