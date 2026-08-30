# Política de paralelismo para lanzadores de Kaggle v1

**Fecha de decisión:** 2026-08-30
**Estado:** `ACTIVE_POLICY`
**Autoridad:** directiva explícita de Nico.

## Decisión

Todo lanzador de Kaggle nuevo que procese una lista de unidades de trabajo
independientes (una sesión CME, un contrato, una config) debe correrlas con
paralelismo acotado en vez de un bucle secuencial de un subproceso a la vez.

```text
DEFAULT_MAX_WORKERS = 4   # típico de vCPUs en un kernel Kaggle sin GPU
EXECUTION_MODEL      = bounded_thread_pool_of_subprocesses
FAIL_CLOSED           = true  # cualquier falla aborta el resto
```

## Motivación

Todos los lanzadores construidos en la sesión del 2026-08-29/30 (Event Store
de GC, P2-B económico de GC, coordenadas informales de NQ) corrían sus
unidades de trabajo (234 sesiones, o contratos) secuencialmente, un
subproceso Python a la vez, aunque Kaggle asigna típicamente 4 vCPUs a un
kernel sin GPU. Cada unidad es independiente por diseño (lee sus propios
inputs, escribe su propio archivo de checkpoint, no comparte estado
mutable con las demás) — el paralelismo no cambia la semántica de ninguna
herramienta ya probada, sólo cuántas instancias de un mismo subproceso
corren al mismo tiempo.

## Alcance

Aplica al **lanzador** (`run.py` del kernel de Kaggle), no a la
herramienta interna que ejecuta cada unidad. No implica tocar el código
ya congelado/autorizado de una herramienta (por ejemplo, un sweep de una
sola pasada monolítica como `tools/sweep_bigtrap2_nq_tickframes_v2.py` no
se paraleliza por esta política, porque el bucle vive dentro del propio
script ya congelado, no en el lanzador).

## Patrón de referencia

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_parallel(build_args, n, label, max_workers=4):
    """subprocess.run libera el GIL mientras espera al hijo, así que un
    ThreadPoolExecutor alcanza -- no hace falta ProcessPoolExecutor."""
    def _run_one(i):
        return i, subprocess.run(build_args(i), cwd=REPO_DIR, capture_output=True, text=True)
    pool = ThreadPoolExecutor(max_workers=max_workers)
    completed = 0
    try:
        futures = {pool.submit(_run_one, i): i for i in range(n)}
        for future in as_completed(futures):
            i, proc = future.result()
            if proc.returncode != 0:
                print(f"FAILED {label} {i}\n{proc.stdout}\n{proc.stderr}", flush=True)
                pool.shutdown(wait=False, cancel_futures=True)
                raise SystemExit(f"{label} failed at index {i}")
            completed += 1
            if completed % 20 == 0 or completed == n:
                print(f"{label} progress: {completed}/{n}", flush=True)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
```

Aplicado retroactivamente (para si hace falta rehacer una corrida) a los
lanzadores de GC (Event Store + P2-B, `MAX_WORKERS=4`) y al de coordenadas
informales de NQ (`MAX_WORKERS=3`, uno por contrato).

## Lo que esto NO cambia

- No relaja ningún chequeo fail-closed: si una unidad falla, el lanzador
  sigue abortando el resto (antes esperaba a que terminara la unidad que
  fallaba antes de abortar; ahora puede haber unidades adicionales en
  vuelo cuando se detecta la falla, pero ninguna se da por válida sin
  pasar sus propios chequeos).
- No cambia el firewall ni la autorización de ninguna campaña: sigue
  siendo la misma herramienta, con la misma spec congelada, corriendo N
  veces en paralelo en vez de N veces en serie.
- No aplica a herramientas de una sola pasada monolítica ya congeladas.

## Aporte al referente

Reduce el tiempo de pared de las campañas Kaggle de sesión-por-sesión
(Event Store, P2-B, selección de configs) sin tocar la lógica de negocio
de ninguna herramienta ya probada -- el cambio vive enteramente en el
lanzador, es reversible, y no requiere re-autorización de la herramienta
subyacente.
