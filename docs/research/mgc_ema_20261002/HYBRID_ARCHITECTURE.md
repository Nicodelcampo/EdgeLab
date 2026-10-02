# Arquitectura híbrida CPU/GPU para EdgeLab

## Principio

Asignar trabajo por patrón computacional, no por disponibilidad de hardware. El resultado debe ser idéntico entre backends dentro de tolerancias explícitas y siempre referir al mismo `artifact_id`, `roll_schedule_sha256`, registro de candidatos y versión de kernel.

## CPU

- parsing Parquet, validación de esquema, hashing y manifests;
- calendarización CME/DST y selección causal D-1;
- agrupación por sesión/contrato y resets de estado;
- máquinas de estado path-dependent: pullback, timeout, BE/trailing, prioridad intrabar y fills;
- tick-exact de finalistas;
- bootstrap/CSCV cuando la unidad es sesión y el volumen cabe en RAM.

Backend: NumPy/Arrow para I/O vectorizado y Numba `njit(parallel=True)` para kernels. Nada de `pandas.iloc` en loops calientes.

## GPU

Sólo cuando haya CUDA y el lote amortice transferencias:

- EMA/rolling features masivos sobre arrays contiguos;
- máscaras de señales target-free;
- grids densos e independientes de TP/SL con horizontes acotados;
- remuestreos bootstrap/permutaciones grandes;
- creación de ventanas DeepLOB y entrenamiento.

No enviar a GPU reglas divergentes con while loops largos ni replay tick-exact de pocos candidatos. El backend GPU es una aceleración opcional; CPU sigue siendo referencia.

## Capas

1. **Raw immutable**: Parquet originales + hashes.
2. **Canonical ticks**: integer ticks, contract/trade_date/regime, sin back-adjustment.
3. **Versioned arrays**: `.npy` mmap o Zarr por activo/contrato/sesión; manifest con dtype/shape/hash.
4. **Feature cache**: EMA/VWAP/SMA target-free; reset policy explícita.
5. **Signal ledger**: índice de decisión, dirección, feature version; sin TP/SL.
6. **Screening**: CPU-parallel o GPU; produce matriz candidato × unidad temporal.
7. **Tick exact**: CPU Numba sobre finalistas; bid/ask, trade-through y reglas conservadoras.
8. **Validation**: sintéticos, mirror, prefix, ledger independiente, MCPT, DSR/BH, PBO, SPA, estabilidad.
9. **Sealed holdout**: proceso separado, un solo uso, resultado firmado.

## Dispatch

- `backend=auto`: GPU sólo si está disponible, arrays ya residen/entran en VRAM y el estimador de trabajo supera umbral.
- Todo kernel declara `kernel_id`, versión, backend, precision, determinismo y seed.
- CI compara CPU vs GPU en fixtures sintéticos y muestras reales pequeñas.
- Un mismatch bloquea publicación; jamás se elige el resultado “más favorable”.

## Continuación inmediata

Crear `candidate_registry.json` para las 126 celdas originales, extender el motor compartido con pullback/BE y agregar adapters `cpu_numba`/`gpu_cuda` que devuelvan el mismo schema de ledger. En la máquina actual no había GPU, por lo que la corrida registrada usó el backend CPU de referencia.
