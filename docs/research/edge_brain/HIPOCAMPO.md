# Ledger de experimentos — Hipocampo EdgeLab

## DATA-PERF-GEX1-20261005 — PLANNING

**Goal**: Que las corridas de Kaggle sobre datos de ticks sean rápidas: la corrida GEX-1 tardó 25,7 min y falló al final
- ❌ **SLOW_PIPELINE**: load_m1 procesaba cada tick en pandas (root: la fecha de sesión se calculaba como CADENA por tick (tz_convert + strftime sobre decenas de millones de filas), np.isin sobre cadenas, concat y sort de todos los ticks, groupby con columnas de texto; ≈ 10 min por trimestre de MES en Kaggle)
- ❌ **MISSING_INPUT**: El kernel falló a los 1.540 s con FileNotFoundError (root: se lanzó sin adjuntar el dataset edgelab-ticks-nt8-reexport-20261005 que el resolver ya usaba como primera prioridad; el error aparecía recién al llegar al último tramo)
- ✅ load_m1 rápida idéntica a la original
- ✅ Prueba de humo en Kaggle: M1 de MES de 5 trimestres en 36 s (antes ≈ 10 min por trimestre); mismas cantidades de filas que la corrida original
- 📘 **L1** [PROPOSED/LOW/UNRATED] No construyas M1 desde ticks tick por tick en pandas en cada corrida: agregá por grupo de filas con numpy, calculá la fecha de sesión por minuto (no por tick), evitá columnas de texto por tick (usá diccionario) y cacheá el M1 por archivo. Verificá igualdad exacta contra la versión lenta antes de reemplazarla.
- 📘 **L2** [PROPOSED/LOW/UNRATED] Antes de lanzar un kernel largo, resolvé y comprobá todos los inputs: un archivo que falta no debe aparecer tras 25 minutos. Usá required_files/check_inputs y adjuntá los datasets que lista.
- 📘 **L3** [PROPOSED/LOW/UNRATED] Diagnosticá con el log del kernel antes de optimizar: el log trae el tiempo de cada etapa. Imprimí marcas de tiempo por etapa en los scripts largos.
- 📘 **L4** [PROPOSED/LOW/UNRATED] Probá todo script de Kaggle con un recorte chico (un mes, un instrumento) antes de la corrida completa.
- 📘 **L5** [PROPOSED/LOW/UNRATED] Los datos derivados que se reusan (M1 por archivo) conviene publicarlos como dataset propio (edgelab-m1-bars) para que una corrida no recalcule nada. Propuesta, aún no construida.
- 📘 **L6** [PROPOSED/LOW/UNRATED] Lanzá kernels con tools/kaggle_launch.py: comprueba contra la lista VIVA de Kaggle que cada sesión aprobada tenga fuente (primaria o alternativa consistente) y no lanza si falta alguna. Un resolver que apunta a archivos que aún no están subidos hace fallar el kernel tarde.
- 📘 **L7** [PROPOSED/LOW/UNRATED] Un resolver debe guardar, por sesión, fuentes alternativas del mismo contrato y fecha con una marca de consistencia (trades a 1 %), y la lectura debe usarlas con aviso. Una fuente inconsistente no se usa en silencio.
