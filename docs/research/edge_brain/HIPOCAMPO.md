# Ledger de experimentos — Hipocampo EdgeLab

## AUTOPILOT-idm-1 — PLANNING

**Goal**: IDM/MULTI: Momentum intradía «resto del día → última media hora» y su modulación por gamma bajo
- ✅ 1 rechazos de Holm a nivel 0.0238 sobre 10 pruebas planeadas: idm/GC p=0.0009; idm/GC_spot p=0.1349; idm_gamma_diff/ES_spot p=0.1754

## AUTOPILOT-idm-2 — PLANNING

**Goal**: IDM_JUMP/GC_MULTI: Momentum de la última media hora en GC: ¿lo explican los saltos del día? Prueba en spot 2022-2025 (muestra no usada para esta versión) y en otros activos
- ❌ **NO_FINDING**: ninguna prueba pasa Holm a nivel 0.0351 (root: mejores: idmj/GC p=0.0083; idmj/GC_spot_old p=0.0831; idmj/ES_spot p=0.08555)

## AUTOPILOT-scan-1 — PLANNING

**Goal**: SLOT_SCAN/MULTI: Barrido de franjas (07:00-14:30 CT) en GC, NQ, ES, YM y 6E: momentum y reversión, descubrimiento → réplica
- ❌ **NOT_REPLICATED**: El OK1 registrado antes contaba solo rechazos de descubrimiento (ES spot y GC spot pasaron el nulo de máximo) y ninguna de las 15 réplicas pasó Holm (root: corrección: sin réplica no hay acierto; ES 2018-25 y GC 2022-25 muestran estructura en el spot que no se sostiene en los futuros 2025-26)
- ✅ 2 rechazos de Holm a nivel 0.0189 sobre 20 pruebas planeadas: scan/GC/max_disc p=0.0005; scan/ES/max_disc p=0.0005999; scan/YM/max_disc p=0.011

## AUTOPILOT-slot-1 — PLANNING

**Goal**: SLOT_REVERSAL/MULTI: Reversión de 15 min a las 04:30 CT en otros activos (generalización del hallazgo débil de GC)
- ❌ **NO_FINDING**: ninguna prueba pasa Holm a nivel 0.0238 (root: mejores: slot/ZB/04:30 p=0.0547; slot/ES_spot/04:30 p=0.3997; slot/NQ/04:30 p=0.6622)

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

## KAGGLE-SPEED-AND-DATA-20261012 — PLANNING

**Goal**: Corridas de Kaggle más rápidas y sin sorpresas de datos (AVCL-VOL-1, GEX, OU-1)
- ❌ **SLOW_ANALYSIS**: AVCL-VOL-1: estimación de 1-2 h contaba solo el procesamiento de contratos (root: el análisis posterior (12 pruebas x 20.000 permutaciones con np.lexsort, y emparejamiento de controles con máscaras de texto por estrato) costaba ≈ 44 min por prueba a escala real: ≈ 10 h en total)
- ❌ **SILENT_LAUNCH_FAILURE**: Tres kernels GEX fallaron sin log legible (root: se lanzaron sin --internet y el script bajaba DIX de la web; la API de Kaggle no devuelve el log de un kernel con error; el código se había probado solo en parte)
- ❌ **INVALID_STATISTIC**: GEX-1 daba p = 0,0001 para un estadístico NaN (root: la comparación nulo >= NaN daba verdadero; un estadístico no finito debe ser «no evaluable» y quedar fuera del ranking de Holm)
- 📘 **L8** [PROPOSED/LOW/UNRATED] Perfilá el análisis posterior (permutaciones, matching, bootstrap) a escala real antes de estimar el tiempo de una corrida: el costo puede estar ahí y no en el procesamiento de datos. Usá argsort en vez de lexsort, índices por estrato en vez de máscaras de texto, y verificá que las salidas sean idénticas.
- 📘 **L9** [PROPOSED/LOW/UNRATED] Al lanzar un kernel registrá las versiones de los datasets y los bytes de cada archivo usado, y verificalos al arrancar: si el dataset cambió o falta algo, falla en segundos con el detalle. Nunca elegir un archivo por parecido de nombre dentro de un dataset.
- 📘 **L10** [PROPOSED/LOW/UNRATED] Un estadístico estacionario por construcción (p. ej. precio menos su media móvil) rechaza ADF aunque el precio sea una caminata aleatoria: compará siempre contra un nulo procesado igual (signo aleatorio por retorno) y reportá el exceso, no el valor crudo.
- 📘 **L11** [PROPOSED/LOW/UNRATED] Un estadístico no finito es «no evaluable»: no tiene p ni entra en el ranking de Holm (el denominador sigue siendo el número de pruebas planeadas). Y un kernel de Kaggle con error no devuelve log por la API: probá local con datos parciales y activá --internet si el script descarga algo.
