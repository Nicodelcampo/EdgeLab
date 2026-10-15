# Publicación del L2 de ES en Kaggle privado

Estado: PROPUESTA — herramienta lista; falta ejecutar cuando termine la descarga de ES
Fecha: 2026-10-15
Familia / módulo: liquid-release · datos L2

- **Decisión de Nico (2026-10-15):** subir solo el L2 de ES (parquet comprimido) a Kaggle privado; NQ queda para después. Esto cambia la política anterior de no subir L2 a Kaggle; el L2 sigue sin ir a GitHub.
- **Herramienta:** `tools/build_l2_release.py --instrument ES --out D:/edgelab_release_work/l2_es_release [--create]`. Copia por contrato `l2_depth`, `l1_quotes` y los manifiestos de conversión, más las agregaciones de `tools/l2_fast_book.py`, y escribe `L2_RELEASE_MANIFEST.json` con bytes y SHA-256 por archivo, QA por sesión, sesiones marcadas y políticas. Publica con `kaggle datasets create --dir-mode zip` (privado). Tamaño esperado: ~6,5 GB (límite de Kaggle 20 GB por dataset).
- **Cuándo:** una sola vez, al terminar la descarga de ES (hasta 2026-10-14), para no repetir la subida.
- **Estado de uso:** el manifiesto declara `research_allowed=false` hasta una auditoría propia del L2 (payload, reloj P-84, sesiones marcadas como 2026-08-11 y los 4 de nivel inválido), análoga a la de la release v4 de ticks.
- **Partición:** desarrollo L2 hasta 2026-10-31; noviembre–diciembre es el holdout L2 sellado y no está en el dataset. Un resultado de ticks en jul–oct no se combina con un modelo L2 entrenado ahí.
- **Prueba hecha:** armado de 2 sesiones por contrato (16 archivos, 0,13 GB) sin errores.

*Aporte al referente:* deja listo el camino para entrenar con libro real en Kaggle sin sacar el L2 de ES de un dataset privado con trazabilidad por archivo.
