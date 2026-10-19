# GC exact4: auditoría del censo privado y puente de revisión

## Veredicto

**PASS de consistencia del paquete. ABSTAIN de disponibilidad raw y de reproducción sobre las velas originales.** No es un resultado económico ni una aprobación para operar.

Entrada: `GC_EXACT4_CENSO_para_nube.zip`, febrero de 2026, GC 04-26, 25 operaciones por vela. HEAD remoto resuelto al comenzar: `44f2691eb8c1a249fbb247a83fafd43fa5c1fa49`. Trabajo en staging aislado; hashes exactos de fuentes ejecutadas en `artifacts/gc_exact4_censo_audit_20260930/evidence_aggregate.json`. No se presenta el HEAD como prueba de ejecución de un árbol limpio.

## Comprobaciones realizadas

- Hash de captura local: bytes exactos coinciden con el declarado. Configuraciones C0–C4 y hashes canónicos regenerados y coincidentes.
- Código productor, núcleo y resolver: hashes declarados coinciden con los blobs preparados al normalizar a CRLF de Windows. Los archivos originales no se modificaron.
- Eventos de cada perfil recontados, reconciliados por lado y sesión. Cuatro miembros distintos, ordenados; cuarta confirmación = detección; ninguna reutilización de miembros dentro de un perfil y lado.
- Todos los picos elegibles reconcilian con 4 × zonas más picos de bloques incompletos. No hay rechazo de cuatro miembros en este paquete.
- C0 permanece ABSTAIN en el censo: sus 1.459 zonas son reportadas, no reproducidas ni auditadas geométricamente aquí.

| Perfil | Zonas recontadas | Techos / pisos | Sesiones con eventos |
|---|---:|---:|---:|
| C1_EXACT4 | 1605 | 784 / 821 | 20 |
| C2_EXACT4_DENSAS | 1817 | 893 / 924 | 20 |
| C3_EXACT4_SEPARADAS | 1091 | 545 / 546 | 20 |
| C4_EXACT4_PLANAS | 665 | 359 / 306 | 20 |

Hay 21 IDs de sesión listados, uno sin eventos (`20260201`), y 20 con eventos. Eso NO demuestra cobertura completa del dato. En C1, excluyendo el 16/02 con 16 zonas, el rango recontado es 53–137 (no 50–137). No se retira el 16/02 ni la fila cero.

Los 5178 registros entre perfiles no son señales independientes: hay 2918 geometrías distintas por lado/cuatro miembros, con solapamiento entre configuraciones. Ni esa unión ni el total certifican potencia; la muestra tiene dependencia intrasesión y sólo 20 IDs con eventos.

## Qué significa el cero de publicación

En TODOS los eventos `raw_publication_row` y `raw_publication_ts_us` son nulos; `publication_metadata_pass=false`. El resultado correcto es **ABSTAIN_MISSING_RAW_PUBLICATION_METADATA**, no FAIL del detector y tampoco PASS por inferir publicación desde la hora de la vela.

Para certificar disponibilidad hacen falta las barras con `bar_close_row`, `snapshot_asof_row`, `snapshot_ts_us`, `available_row`, `available_ts_us` y `publication_mode=OBSERVED_NEXT_TIMESTAMP_ROW`, reconstruidas desde fuente gobernada. La condición debe verificarse sobre fila y timestamp reales; no se fabrica desde OHLC. Incluso con metadata válida, eso no certifica fills.

## Visor: implementación de la continuación

`tools/gc_exact4_review.py` audita y exporta capas C1–C4 utilizando el bundle privado original. Exige SHA-256 exacto del bundle, serie `tick_25`, ventana y cantidad de velas; verifica extremo/precio/hora/índice de cada miembro y barra de detección. Sin bundle, sólo audita el paquete.

Genera `index_gc_exact4.html` como copia parcheada del `index.html` local. No pisa el visor canónico, C0 ni capas preexistentes. Si cambió cualquier hook relevante, se abstiene antes de escribir. Cambios locales fuera de esos hooks se conservan.

La copia incorpora `gc_exact4_review_guard.js`: bloquea activo/serie/layer incompatibles, congela los cuatro miembros, muestra `RAW PENDIENTE` y `DET lógico p4`, elimina parámetros `sl/tp/be/cand`, deshabilita cómputos de posiciones y no usa el precio de trigger como supuesto fill. La marca azul es el cierre observado de la barra de detección. Juicios quedan separados por `__exact4_c1`…`c4` usando el mecanismo existente del visor.

La cortina de revisión se coloca después de `det_i`, no después de pico4+2. **No es una tanda ciega certificada**: el dataset y la escala del visor pueden contener futuro y el usuario ya vio febrero. No convertir esos juicios en validación causal/OOS.

## Tests y alcance

26 tests originales exact4 + 13 tests nuevos Python + 12 del guard JavaScript pasan. El productor original emite un ResourceWarning por archivo sin cierre explícito; se conserva para no alterar hashes de procedencia. No es una prueba del entorno Windows fijado completo.

QA con fixtures sintéticos en navegador compartido: carga, revisión, ventana de 1280×900 y 390×844, ausencia de tablero de posiciones, eliminación de parámetros de trades. **No se vio la geometría real de febrero**, porque el ZIP no trae las velas.

## Pendiente mínimo local

Seguir `HANDOFF_LOCAL_GC_EXACT4_REVIEW_20260930.md`. Ejecutar el exportador contra el bundle local ya hasheado, abrir las cuatro URL y revisar. Devolver el reporte local y juicios (privados). Si se quiere reproducir el detector aquí, mandar también barras JSONL originales y su procedencia; el bundle solo sirve para paridad de capa, no sustituye el raw.

Sin manifiesto + OK explícito de Nico: NO retornos, MAE/MFE, TP/SL, costos ni fills. Holdout forward octubre+ intacto. Eventos privados/precios/bundle/juicios NO se suben al repo.

## Aporte al referente

El censo tiene consistencia verificable y una vía de revisión local sin tocar C0. La distancia pendiente es disponibilidad y geometría sobre el dato real, no un backtest adicional todavía.
