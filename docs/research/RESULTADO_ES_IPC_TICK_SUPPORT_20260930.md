# ES: familias IPC congeladas y soporte por tick — sin resultados de trades

## Alcance
Kaggle `nicolasbuttaro/edgelab-ticks-es-preholdout` v2 ES03-26 y `edgelab-ticks-gc-preholdout` v2 GC04-26, ventana UTC febrero2026, hashes en evidencia. ES22.835.690 registros; GC2.546.985. Todos los registros observados de ambos son `trade`, contrato/instrumento correspondiente. Ningún tick fuera del mes se utiliza para señales. No hay L2 ES en esta ejecución.

Se construyen913.414 barras ES completas de25 registros. Ancla al primer tick de cada fecha UTC y remanentes parciales contados, sin cruzar fechas. Son barras nuevas, NO se certifica paridad con el bundle original del visor. Los contadores antiguos2705/927 y nuevos2706/937 no se igualan por ajuste: calendario/ancla pueden diferir, queda explícito.

## Dos familias, sin recalibrar
Confirmación por precio2ticks, parámetros originales. PLANAS: w2/gap15/step2/pull5/nmin3/dmax35. EMPINADAS: w2/gap15/step3/pull6/nmin3/dmax35/total_min5/step_min3. Se emite primera confirmación de cadena elegible; ningún dibujo extendido o fin futuro se usa como feature. La confirmación es lógica de barra conocida, NO fill a2ticks ni timestamp intrabar certificado.

| Familia | Eventos | Fechas observadas con ≥4 | Mínimo / máximo por fecha observada |
|---|---:|---:|---:|
| PLANAS |2706|24/24|5 /360|
| EMPINADAS |937|20/24|1 /132|

EMPINADAS por debajo de4: 01/02=3,08/02=2,15/02=2,22/02=1 (fechas UTC, no sesiones CME certificadas). Calendario sin ticks en ambas fuentes:7/14/21/28 febrero, sin convertir falta de datos en señales=0.15 eventos comparten barra/lado/nivel entre familias: NO sumar como observaciones iid. Muchas zonas no garantizan potencia, operabilidad ni rentabilidad.

## ¿Tick más grande ayuda?
Tick nominal ES0,25 frente GC0,10 NO permite comparar ventaja. Comparación pertinente preliminar: spread cotizado relativo al tick. En los registros de trade con bid>0 y ask>bid:

- ES:21.174.154 de22.835.655 con spread1tick =92,7240930904%; spread medio1,1122302382ticks.
- GC:97.852 de2.546.869 =3,8420507690%; spread medio8,5699409746ticks.

Son porcentajes ponderados por registros/operaciones del export, NO porcentaje del tiempo ni snapshots L2 sincronizados. No se presenta el spread como costo ejecutable. Locked: ES35/GC116; crossed y quotes no positivos:0/0. Auditoría independiente de todos los registros por pandas concilia contadores;0 trades fuera de su bid/ask válido. Consistencia interna no certifica edad/publicación/autenticidad operativa de la quote: no metadata raw de publicación.

Lectura: ES es buen candidato para estudiar presión de cola/reposición porque este export muestra cotización de1tick mucho más frecuente y PLANAS tiene suficiente densidad geométrica. NO demuestra que L2 ES prediga mejor que GC ni que el retorno neto mejore. La comprobación requiere libro ES y ticks emparejados en mismas sesiones, guardas de reloj/publicación/frescura y comparación contra baseline de precio. Los climas ES que dieron STOP permanecen STOP.

## QA y firewall
6 tests unitarios;8 comparaciones de prefijos; paridad con detector original documentada en evidencia final. Arrow en batches seleccionados por mes verifica nulos, orden y partición de quotes; profiler genérico no lee parquet binario y no se usa como autoridad. Se retienen timestamps repetidos como prints distintos.

**NO MEDIDO:** futuros de señal, MFE/MAE, dirección posterior, retorno, P&L, fills, comisiones, predicción L2 o potencia independiente. Publicación raw: ABSTAIN_MISSING_RAW_PUBLICATION_METADATA. Holdout intacto. No se modifica visor/C0 ni calibraciones. Código+acta+registro en mismo commit; raw/barras/precios fuera repo.

## Siguiente paso compatible
Libro ES de unas sesiones y export de ticks correspondiente con procedencia, sin empaquetar meses enteros en memoria. Generar25t, validar emparejamiento exacto y añadir las mismas features de presión/defensa, sin rescatar climas. Fase predictiva posterior requiere manifiesto+OK separado antes de resultados.
