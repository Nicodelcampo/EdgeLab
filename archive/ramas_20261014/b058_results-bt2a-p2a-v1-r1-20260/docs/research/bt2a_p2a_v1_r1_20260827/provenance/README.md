# Procedencia de ejecución

Esta carpeta conserva los archivos textuales de procedencia de la ejecución P2-A:

- `environment.txt`: runtime, commits, árbol local limpio y lock efectivo.
- `p2a_batch_worker.py`: worker exacto usado para completar checkpoints.
- `run_p2a_parallel.log`: reanudación y cierre agregado.
- `execution_logs/`: logs de ambos workers y de finalización.
- `source-package/SHA256SUMS.txt`: copia exacta de la tabla de hashes ubicada en la raíz del paquete fuente externo.

Las rutas `./...` de `source-package/SHA256SUMS.txt` se resuelven contra la raíz del ZIP fuente, **no** contra este subdirectorio Git. Los hashes allí listados identifican los bytes del paquete externo; no deben atribuirse a snapshots Git-native que hayan cambiado sólo whitespace o finales de línea.

`execution_logs/finalize.err` tiene cero bytes porque la finalización no emitió errores.
