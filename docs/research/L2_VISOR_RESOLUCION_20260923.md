# L2 en el visor, reloj de 6E y bug de la fracción de segundo (2026-09-23)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Alcance:** integridad de datos y visor (target-free). No se miró ningún retorno.

## S1. Reloj de 6E: ART (UTC-3)

Usé el mismo método que para GC y ES: la pausa diaria de mantenimiento de CME (16:00–17:00 CT, 21:00–22:00 UTC en horario de verano) cae a las **18:00–19:00 si el `ts_us` se lee como UTC**, en 5/5 sesiones de 6E 12-26 (14, 15, 16, 22 y 5 de agosto). El desfase es −3 h, o sea que el reloj es ART. Se agrega `6E` a `WALL_CLOCK_RESOLVED_TZ` en `tools/build_l2_viewer_bundle.py`. Esto **no** resuelve la correspondencia con los ticks `.Last.txt`.

## S2. BUG: la fracción de segundo de NT8 quedaba ×10

- **Qué pasaba:** NT8 (`MarketReplay.DumpMarketDepth`, que es lo que usan tanto NRDToCSV como el Replay Downloader) escribe la fracción en **ticks de 100 ns** (7 dígitos). `edgelab/data/l2.py` la sumaba como microsegundos, así que la fracción salía multiplicada por 10: hasta **+9,99 s** de error y **45.000–70.000 inversiones de reloj por sesión**. Las conversiones viejas daban 0.
- **Medición:** se tomó GC 08-26 20260625, convertido con el conversor viejo y con el actual. Las 7.183.327 filas coinciden en `source_row`. La diferencia va de 0 a 8,964 s, con una media de 4,3 s.
- **Antecedente:** el arreglo ya existía desde el 2026-08-25 (`b3b2a43b`, rama `work/futures-l2-context-foundation-20260825`), pero nunca se integró a esta línea.
- **Arreglo nuevo:** `_detect_subsecond_unit`. Si algún valor de la fracción supera 999.999, la columna no puede estar en microsegundos, así que se trata como ticks de 100 ns y se divide por 10. Un valor fuera de todo rango aborta la conversión. El manifest pasa a v4 y registra `conversion.subsecond_unit` y `clock_inversions_in_source_order`. Hay tests.
- **Afectados:** todos los parquets convertidos del 2026-09-22 al 2026-09-23: GC 12-26, GC 08-26 (desde el 24/06) y 6E 09-26/12-26. Quedaron movidos, sin borrar, a `E:\l2_parquet\_cuarentena_subsegundo_x10_20260923\` con un `LEEME.txt`. **No usar.** Se vuelven a generar reexportando desde NT8.
- **Pérdida:** 6E 09-26 del 08/06 al 16/06 (8 sesiones anteriores al holdout). Sus `.nrd` ya se borraron y NT8 no sirve más de 90 días hacia atrás.
  - Se intentó reparar sin fuente. El método fue acotar cada fila entre el evento anterior y el siguiente, validado contra GC 20260625, donde la verdad es conocida.
  - La verdad cae siempre dentro de los límites, pero **solo el 82,5 % de las filas queda determinado**. El 17,5 % restante es ambiguo.
  - **No se repara.** Quedan en cuarentena como no usables.

### Retractación

`docs/research/SOLAPAMIENTO_FRONTERA_SESIONES_L2_20260922.md` atribuía el solapamiento de −4 a −8 s entre días consecutivos a la "ráfaga de bootstrap sellada con la hora nominal". **Esa explicación era falsa: el solapamiento lo producía este bug.** Con la conversión correcta, las 29 fronteras de GC 08-26 dan PASS sin ninguna tolerancia. Se retira `EXPECTED_BOOTSTRAP_OVERLAP` (el margen de −30 s) de `tools/validate_l2_session_boundaries.py`, y de nuevo todo gap negativo es `FAIL_CLOCK_INVERSION`.

**No queda explicado por este bug:** la superposición del 11/08 → 12/08. Es de unas 13 h en el contrato que vence (GC 08-26, 6E 09-26) y de ~3 min en el siguiente, y el bug aporta como mucho 10 s. Sigue abierta y hay que volver a medirla con los datos reexportados.

## S3. Borrar el nivel 10 cuando el libro tiene menos (abierto, decide Nico)

- **Qué pasa:** en GC 12-26 20260715, NT8 manda `DELETE level=10` sobre un lado que en la reconstrucción tiene 10 niveles (índices 0–9). Al abrir la sesión, el lado vendedor arrancó con 9 niveles y NT8 igual anuncia la salida del undécimo.
- **Frecuencia:** 1 evento en 3.793.870. Con `--exploratory`, el libro coincide con L1 en 99,81 % (bid) y 100 % (ask).
- **Efecto:** el constructor, que falla cerrado, **aborta la sesión entera** por ese único evento.
- **Opción A:** aceptar `op=2` con `lvl == len(lado)` solo si el precio coincide con el último nivel reconstruido, y contarlo aparte.
- **Opción B:** mantener el aborto y construir esas sesiones en modo `--exploratory`, marcadas como tales.
- Es un cambio de cómo se valida: no se toca sin OK.

## S4. Absorción (detector nuevo, PROVISIONAL)

`AbsorptionTracker` en `edgelab/research/l2_manipulation_heuristics.py`:

- **Criterio:** en una ventana de 10 s, el volumen agresivo **atribuido** en un precio supera el p99 de la sesión (hacen falta ≥3 trades) y **el precio no atraviesa ese nivel dentro de la misma ventana**.
- **Qué usa:** solo trades de la ventana. El candidato queda disponible recién cuando la ventana cierra.
- **Estado:** marcado `HEURISTIC_UNVALIDATED`. Hay tests.
- **En el visor:** un segmento verde azulado con tooltip.
- **Medición:** GC 20260615 da 94 candidatos (43 icebergs y 41 spoofs en la misma sesión).

## S5. Visor: arreglos y resolución elegida

- **Bug arreglado:** el cálculo de "dónde está cada marcador" (`_l2MarkerHits`) se hacía pero nadie lo usaba, así que **iceberg y spoof nunca mostraban tooltip**. Ahora lo muestran, igual que la absorción.
- **Bug arreglado:** el tooltip de las burbujas mostraba la hora del feed con `toISOString()` y le agregaba una "Z" que la hacía pasar por UTC. Es reloj de pared ART, y ahora se muestra con esa etiqueta.
- **Etiquetas:** los textos de los marcadores se ocultan con más de 150 velas visibles. Con el día completo a 15 s, se tapaban entre sí y ocultaban las velas.
- **Resolución:**
  - **Velas de 15 s por defecto**, con 5 s, 30 s y 1 min disponibles. En la ventana típica de análisis (1–2 h) dan 240–480 velas: se ven bien de un vistazo y todavía muestran la microestructura. 5 s queda para cuando se hace zoom; 1 min, para ver el día.
  - Se descartan las **barras por ticks**: el eje X del mapa de calor y de las burbujas es tiempo. Con barras de ticks, las velas y el libro dejarían de estar alineados en la misma columna.
  - **Mapa de calor a 1 s** (sin cambios, el estándar tipo Bookmap).
- **Holdout en el visor:** `--holdout-view-only` admite sesiones desde el 01/07 **solo como dato de visor** (target-free, lo permite el NORTH_STAR). Quedan marcadas `holdout_view_only=true` y en un grupo aparte (`--group`).

## Cómo podría refutarse

- **S2:** que una conversión con la fracción dividida por 10 siga teniendo inversiones de reloj dentro de la sesión. Se verifica al reexportar, porque el manifest v4 las cuenta.
- **S4:** que la absorción marcada no se distinga de un control con la misma geometría. Eso requiere un nulo propio; no se promueve sin él.

Aporte al referente: se encontró y cortó un error de reloj que contaminaba todo el L2 convertido esta semana y que ya había producido una conclusión falsa. Ninguna medición de microestructura va a arrancar sobre tiempos corridos hasta 10 s.
