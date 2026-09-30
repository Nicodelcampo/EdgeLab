# GC Kaggle ticks × L2 — identidad y prueba causal de barras

**MEDIDO target-free.** Se usó GC08-26 de Kaggle v2, no el bundle de febrero
GC04-26 ni una serie continua. No predicción, retornos, P&L ni calibración IPC.

## Fuentes y reloj

- `nicolasbuttaro/edgelab-ticks-gc-preholdout`, versión2:
  `GC_08-26_ticks.parquet`, 2.804.464 filas, SHA-256
  `7976fbe9814eff0e234b74f36af09d42938bcdb154067ea736a46a571f688b1d`.
  Bytes coinciden con `files.sha256`. Contrato GC08-26, todas trades,
  sin nulos ni inversión de timestamps/sequence/source_row. Holdout intacto.
- L2 `nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921`, versión2:
  fuente canónica L1/L2 de20260531 y20260615. Hashes, grid, nulos y orden
  revalidados contra manifest. Side2 = ejecuciones según conversor del repo.
- Acta previa `RESOLUCION_RELOJ_GC_L2_20260922.md`: pared L2 ART (UTC-3);
  correspondencia contra Last NO estaba certificada. No bastaba desplazar horas.

Se probaron sólo literal y +3h preespecificados, sin nearest-neighbor, sin
interpolar ni usar correlaciones con resultados futuros. El profiler empaquetado
falló leyendo parquet; Arrow/pandas leen y verifican schema/nulos/orden/hash.

## Hallazgo de correspondencia

**20260531:** los13.913 trades L1 side2 coinciden EXACTAMENTE, en población
completa y orden, con los13.913 ticks Last del intervalo, después de +3h.
Misma timestamp, precio y volumen para cada fila. Hay prints repetidos;
no se certifica su interleaving entre feeds por un join de claves o distancia.
La prueba usa sólo publicaciones de libro con timestamp ESTRICTAMENTE ANTERIOR
al trade: no depende de ordenar ejecuciones repetidas dentro del mismo timestamp.

**20260615:** ambas cintas tienen92.515 trades y la secuencia completa de precio/
volumen coincide; cinco timestamps difieren. Deltas Last menos L1 corregido:
-6,877/-14,877/-22,877/-26,877/-34,877ms. No es un cambio uniforme de huso.
Se mantiene ABSTAIN para el join de este archivo; no se redondea o corrige.
Esto NO significa que el L2 esté corrupto ni invalida su cinta propia.

La correspondencia empírica queda resuelta SÓLO para May31 y SÓLO bajo la
política temporal conservadora. No certifica otras sesiones, latencia, fills,
prioridad MBO o disponibilidad operativa del detector de febrero.

## Prueba sobre ticks reales de Kaggle

Con `tools/gc_kaggle_tick_l2_probe.py`:

- 556 barras completas de25 operaciones del tramo May31;13 trades finales
  se conservan como barra parcial y no se cuentan como completa.
- 546 cierres tienen libro válido previo;10 quedan en bootstrap60s.
- 545 cierres disponen de ventana OFI completa. Ausencia de ventana = null.
- Las80 barras del replay de prefijo2000 trades coinciden exactamente con las
  primeras80 del replay completo.
- Verificación independiente de TODAS las556 barras: OHLC/volumen y filas
  inicial/final de ticks, frontera real as-of/publicación, +3h, publicación
  estrictamente anterior y fórmulas del libro reconstruido para546 cierres.
- Cuatro tests nuevos de identidad PASS;39 tests previos del extractor causal
  permanecen como evidencia anterior, no se cuentan como nuevos tests de esta cinta.

El snapshot se publica al aparecer la primera fila REAL posterior a su grupo;
para unirlo con el tick externo se exige además `available_ts < tick_ts`.
Se excluye incluso el snapshot publicado en el mismo timestamp aunque sea
anterior por source_row del feed L2. EOF no publica un grupo artificial.
Edad se guarda sin certificar un umbral operativo; no hay relleno de missing.

Las barras empiezan en el primer trade del archivo, no hay certificación de
la partición por sesión de otro visor. El libro se observa al CIERRE de la
barra: no describe retroactivamente todo su recorrido ni su extremo.
Ticks y L2 permanecen privados; sólo evidencia agregada y código al repo.

## Alcance y continuación

El código se preparó antes del replay; el plan registra el refinamiento desde
multiset hacia identidad de cinta completa y política estricta previa. Nada se
decidió usando retorno/P&L. Se ejecutó en staging aislado desdea379c23 con hashes.

Esto prueba que podemos medir L2 sobre una cinta real GC de Kaggle de fecha
coincidente. NO se enlazaron zonas IPC ni espejos reales; no es prueba de ventaja.
Hay UNA muestra corta ya expuesta, no tamaño suficiente para potencia.

Para GC escalonadas falta aprobación/congelación del detector; para espejo,
ledger causal A/B y manifest/OK para medir destinos. No trasladar el libro May31
a los ticks de febrero. Jun15 necesita resolver las cinco diferencias antes de
unión cruzada; alternativamente usar su cinta side2 con reloj compartido,
declarando que no es Last.txt.

## Reproducir sin datos al repo

Desde root, con las dependencias del repo:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/research -p test_gc_kaggle_tick_l2_probe.py -v
.\.venv\Scripts\python.exe tools/gc_kaggle_tick_l2_probe.py --ticks E:\datos\GC_08-26_ticks.parquet --raw E:\datos\gc_l2_audit_v2 --book-module edgelab/research/l2_phase0.py --file 20260531 --out E:\gc_kaggle_l2_may31_private
```

No aplicar a otro hash/schema. Junio15 se abstiene antes de replay/output.
Outputs son privados: barras/precios/features NO versionar ni publicar.
Evidencia: `artifacts/gc_tick_l2_join_20260930/evidence.json`.

## Aporte al referente

La unión ya pasó de una posibilidad a una prueba real y causal en May31.
El siguiente trabajo es enlazar eventos definidos; predictibilidad y ventaja
siguen NO MEDIDAS, y Jun15 permanece separado por diferencias de reloj.