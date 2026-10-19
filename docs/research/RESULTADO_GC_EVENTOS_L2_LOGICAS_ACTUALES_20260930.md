# GC eventos × L2 — reglas actuales, sin outcomes

**MEDIDO: geometría, causalidad y soporte del libro.**
**NO MEDIDO: predictibilidad, acierto, retornos, costos o ventaja.**

Datos fijados: May31 GC08-26 ticksKaggleV2 y L2 coincidente,556barras25operaciones
completas. No febreroGC04-26, no ticks continuos, no nueva confirmación
independiente. Junio15 queda ABSTAIN por las cinco diferencias de timestamp.

## Escalonadas

Se aplicaron sin ajuste los perfiles resueltos de GC. C0 = mínimo4, lógica
IPC NQ escalada3,51 con primer evento conocido; C1–C4 son exact4 disjuntos
congelados al cuarto. No se prueba crecimiento/fills como nuevas entradas.

| Perfil | Eventos | Libro estructural válido previo | Nivel visible en top-10 |
|---|---:|---:|---:|
| C0 mínimo4 | 8 | 8 | 1 |
| C1 exact4 | 8 | 8 | 1 |
| C2 exact4 densas | 10 | 10 | 1 |
| C3 exact4 separadas | 5 | 5 | 0 |
| C4 exact4 planas | 3 | 3 | 0 |

Parámetros(w/gap/step/pull/conf) iguales a los congelados: C0/C1=1/30/49/25/28;
C2=1/23/49/19/28; C3=1/45/49/38/28; C4=1/30/25/25/28.
Precios en ticks enteros, TICK=1 al llamar cuerpos originales, sin volver
a escalar precios o parámetros. Perfil más frecuente aquí=C2, no más rentable.

Son34 registros entre perfiles pero18 combinaciones distintas(barra,lado,nivel).
Esta deduplicación no equivale a18 episodios/trades independientes. No sumar
perfiles como muestra para potencia. No ranking universal desde una sola captura.
Los34 snapshots tienen ventana OFI completa. UNKNOWN fuera top-10 no es size0.

## Espejos: A/B confirmado y propuesta50%

Se usó sólo `.detect` del kernel EspejoImpulsos, con defaults congelados:
25t,maxbars20,minW17ticks,retr0,3,efimin0,3. NO `.run/_procesar`, porque producen
estados posteriores. Todas las confirmaciones se registraron; no se filtran por
S2, clase ineficiente o espejo completado. Sin percentiles I2 de sesiones previas.

-161 impulsos confirmados A/B;1 adicional sólo por tiempo, no registro operable.
-161 registros con libro estructural previo; A visible en17.
-91 observaciones alcanzan el landmark50% bajo la política de captura,
  pero sólo58 son eventos prospectivos: se observó un precio previo por debajo
  del50% después de confirmar A/B y luego el primer cruce.
-30 ya estaban ≥50% en la primera observación conocida;3 ya habían alcanzado A.
  No se retrotraen como entradas al50%.
-70 se invalidan por nuevo extremoB antes del primer landmark; no se cuentan
  como pérdidas, probabilidad de fracaso o performance de una estrategia.
-Los58 eventos prospectivos tienen libro estructural previo y ventana OFI.
  A está visible sólo en5; en53 es UNKNOWN. Puede medirse presión touch aunque
  A no sea observable; no puede inventarse defensa/ausencia de defensa en A.

Receipts concilian161=58+30+3+70. No se midió cuántos completan luego el espejo.
Horizonte3×duración del primer impulso se conserva para el censo previo al
landmark; no se prolonga para rescatar casos. EOF no crea expiración de sesión.
No se probó el25/75% ni se eligió porcentaje por beneficio.

## Causalidad y calidad

-El cierre lógico se registra conservadoramente en la primera fila raw de
 timestamp posterior; no en bar_B/pico retrospectivo. Ledger exacto por evento.
-El libro usado fue publicado ESTRICTAMENTE ANTES del timestamp del evento.
 Ningún join cercano, interpolación, snapshot de igualtimestamp o posterior.
-C0 se evalúa en cada prefijo; primer evento conocido, sin backdate si el
 detector aparece tarde. Exact4 se procesa barra a barra sin backfill/rescate5º.
-Prefijo200barras: eventos geométricos iguales al prefijo de la corrida completa.
-7 tests nuevos PASS; comprobación independiente de los286 paquetes de eventos:
 fronteras raw, fórmulas QI y orientaciones, visibilidad/UNKNOWN, cuatro miembros
 congelados y receipts de todos los intentos.
-Edad máxima del snapshot: zonas2.880ms, registros A/B3.688ms,
 observaciones50%6.904ms. No se ratificó gate operativo de staleness: PASS
 significa integridad estructural, NO certifica frescura para HFT o entrada.

Code provenance: staging aislado desde31fc624; cuerpos AST literales seleccionados
de fuentes hashadas para evitar importsGUI/numba/grids. No reescritura del
detector. Primera ejecución detenida sin resultados por lectura pandas
innecesariamente costosa; se cambió a iterador de arrays y se corrió v2 nuevo,
añadiendo la conservación explícita del horizonte ya existente. Ningún cambio
de umbral ni consulta a retorno. Datos/eventos/precios permanecen privados.

## Lectura y siguiente paso

La presión del libro cerca del precio (QI/OFI/spread) tiene soporte en los
eventos. “Defensa en A/nivel” es una pregunta distinta, con soporte mucho menor.
No excluir silenciosamente UNKNOWN ni asumir que significa falta de interés.

La captura es corta y ya expuesta.58 cruces no prueban potencia independiente.
Antes de inferencia: más sesiones con correspondencia certificada, manifest
de población/landmark/invalidación/plazo/edad/splits/efecto mínimo y OK.
Después baseline precio frente al MISMO baseline+L2, temporal fuera de muestra.
No se abrieron destinos, entrenamiento, stop/target/fills/costos.

Código: `tools/gc_current_logic_l2_census.py`. Plan:
`PLAN_GC_EVENTOS_L2_LOGICAS_ACTUALES_20260930.md`. Evidencia:
`artifacts/gc_events_l2_20260930/evidence.json`. Registro actualizado en mismo commit.

## Handoff reproducible

Usar la carpeta `frozen_source` del ZIP (sólo código público del repo) como
`--source`; perfiles congelados allí. Requiere herramientas existentes del repo,
parquetKaggleV2, L1/L2 canónicos y barras privadas de la prueba anterior.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/research -p test_gc_current_logic_l2_census.py -v
.\.venv\Scripts\python.exe tools/gc_current_logic_l2_census.py --bars E:\gc_kaggle_l2_may31_private\bars_l2_PRIVATE.jsonl --ticks E:\datos\GC_08-26_ticks.parquet --raw E:\datos\gc_l2_audit_v2 --profiles E:\entrega\frozen_source\gc_resolved_profiles.json --source E:\entrega\frozen_source --book-module edgelab/research/l2_phase0.py --out E:\gc_eventos_l2_private
```

Outputs privados; no versionar. No genera capas nuevas de visor.
No tocaC0/C1–C4 del visor, raw, climas ni holdout.

## Aporte al referente

Las lógicas actuales ya se enlazaron causalmente con L2 real. El soporte permite
preparar una prueba de presión contemporánea incremental; la defensa del nivel
necesita tratar su baja observabilidad, y la ventaja sigue NO MEDIDA.