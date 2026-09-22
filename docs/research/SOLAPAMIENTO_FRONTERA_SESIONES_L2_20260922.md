# Solapamiento de reloj en la frontera entre sesiones L2 diarias — causa raíz medida

- **Fecha:** 2026-09-22
- **Alcance:** target-free. Solo integridad estructural del reloj entre archivos consecutivos. Sin outcomes, sin P&L.
- **Dispara desde:** `tools/validate_l2_session_boundaries.py`, corrido contra las 7 sesiones reales de GC 12-26 (`E:\l2_parquet\GC_12-26`) y contra la frontera `20260701→20260702` de GC 08-26 (hallazgo previo, `docs/CURRENT.md`).

## 1. El hallazgo

5 de 6 fronteras lunes-viernes consecutivas en GC 12-26 (13→14, 16→17, 17→18, 18→19, 19→20) miden un **solapamiento negativo** de entre **-4,0 s y -7,6 s** (`last_ts_us(D) > first_ts_us(D+1)`). El mismo patrón, misma magnitud, ya se había medido para GC 08-26 (`20260701→20260702`, -5,68 s) y quedó registrado como `MEASURED_UNEXPLAINED`. Con esta segunda medición sobre un contrato distinto, deja de ser un caso aislado: es un **patrón sistemático del corte de archivo**, no un evento raro de una sesión puntual.

## 2. Causa raíz — inspección fila por fila de la frontera 20260813→20260814

**Últimas filas de `20260813` (L2):** `operation=1` (CHANGE) repetido sobre `side=1 level=5 price_tick=43784` — tamaño oscilando 3↔4↔3↔4. Son eventos genuinos de actividad de fin de sesión, en un nivel que ya existía.

**Primeras filas de `20260814` (L2):** `operation=0` (ADD) construyendo los niveles 0-5 desde cero, en `price_tick=43792..43797` — **precios completamente distintos** a los del final del día anterior. Es la ráfaga de bootstrap que reconstruye el libro al arrancar el archivo nuevo (mismo patrón documentado en `RESOLUCION_RELOJ_GC_L2_20260922.md` para el arranque de sesión).

**Conclusión:** no hay ningún evento duplicado — los precios no coinciden entre las dos colas. Lo que se solapa es el **reloj**, no el dato: la ráfaga de bootstrap de `20260814` queda sellada con el timestamp nominal de arranque de sesión (01:00:00.280 ART, el mismo patrón de microsegundo `.280000` visto en todas las sesiones), mientras que `20260813` sigue capturando actividad real unos segundos más allá de ese instante nominal antes de cerrar el archivo. El bootstrap **no es una secuencia de órdenes nuevas llegando en ese instante** — es una foto del libro que ya existía, estampada con la hora de arranque del archivo, no con una hora de llegada real. Por eso puede aparecer "antes" que la cola genuina del día anterior sin que ningún dato esté mal.

## 3. Consecuencia práctica

- **NO es un error de datos.** No hay filas repetidas, no hay volumen contado dos veces.
- **SÍ es un límite real para cualquier concatenación multi-sesión que asuma orden estrictamente creciente de `ts_us` cruzando la frontera.** Los primeros eventos de bootstrap de un día NO se pueden ordenar de forma confiable contra la cola del día anterior usando solo `ts_us` — están en dominios de reloj ligeramente distintos (snapshot vs. tiempo real).
- Coincide exactamente con la separación que ya recomendó el auditor externo: la clave de orden correcta para series multi-sesión es `(session_id, source_row)`, **nunca** `source_row`/`ts_us` global cruzando archivos.

## 4. Cambio en `validate_l2_session_boundaries.py`

Antes: cualquier `gap_seconds < 0` clasificaba `FAIL_CLOCK_INVERSION` sin distinción de magnitud.

Ahora: un solapamiento negativo pequeño (`-30s <= gap < 0`, margen generoso sobre el rango medido de -4,0 a -7,6 s) en una frontera que de otro modo calificaría como continua (lunes-jueves-domingo → día siguiente) se clasifica `EXPECTED_BOOTSTRAP_OVERLAP` — **no** `PASS` silencioso, sigue quedando marcado explícitamente como solapamiento conocido, pero tampoco `FAIL` — con `continuity_status=REVIEW_MINOR_OVERLAP` para que quede visible sin bloquear el pipeline. Cualquier solapamiento fuera de ese margen, o en una frontera que no calce con el patrón de calendario esperado, sigue fallando duro.

No se tocó el umbral por conveniencia: el margen de -30s es ~4-7x más laxo que el rango medido, calibrado sobre evidencia real de 6 fronteras en dos contratos distintos, no elegido para que pasen los tests.
