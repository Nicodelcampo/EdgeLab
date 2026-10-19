# GC L2 a precio fijo — piloto mecánico P0

**Estado: MEDIDO, factibilidad mecánica; utilidad operativa NO MEDIDA.**
Continúa I-3 de `FAMILIA_ABS_CTX_NQ_20260924.md` y R02 de
`PENDIENTES_L2_APLICACIONES_20260929.md`. No es una estrategia nueva ni un rescate de climas STOP.

## Pregunta y fuente

¿Podemos observar caída y recuperación de tamaño visible en el mismo precio, sin
confundir el movimiento de niveles, una desaparición del top-10 o un trade futuro?

Dos ejemplos disponibles de GC 08-26 de NT8 Market Replay, privados:
`nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921`, versión 2,
archivos `20260531` y `20260615`. Se eligieron por disponibilidad, no por performance.
Se extrajeron sólo cuatro parquet L1/L2 y manifiestos. No se cargaron los bundles del
visor ni se calcularon retornos, MFE/MAE, fills o P&L. No hay derivados de Lucid.

Base consultada: `cf7c4a3266709fc6674e5e11ec0dae0995e891d2`.
Reconstrucción: `edgelab/research/l2_phase0.py`, sin cambiar `apply_event`.
Los cuatro hashes y conteos coinciden con el manifiesto del dataset. Evidencia completa:
`artifacts/gc_l2_fixed_price_p0_20260930/evidence.json`.
El hash autorreferencial listado para el propio manifiesto no se toma como certificación;
la reconciliación afirmada corresponde a los cuatro parquet.

**Reloj:** los manifiestos antiguos dicen referencia NT8 sin resolver. Sólo usamos
orden `source_row` y diferencias de microsegundos. No certificamos UTC, sesión CME,
horario del día ni unión con otro feed.

## Método fijado antes de contar

Plan local escrito antes de ejecutar; copia exacta en
`PLAN_GC_L2_PRECIO_FIJO_P0_20260930.md`.

- Clave `(lado, precio absoluto)`, no número de nivel.
- Snapshots al final de cada grupo de timestamp, nunca estados intermedios del grupo.
- Libro ordenado, no cruzado y con diez niveles visibles por lado; arranque de 60 s.
- Descenso candidato: caída neta entre snapshots con UPDATE al mismo precio.
- Evidencia compatible: LAST al mismo precio en los 2 s previos, no posterior al
  UPDATE según `source_row`. Cada impresión se consume una sola vez como evidencia.
- Recuperación: aumento observado al mismo precio dentro de 5 s y hasta al menos
  70 % del tamaño anterior a la caída. Ventanas heredadas del tracker de referencia,
  no optimizadas aquí.
- DELETE, cambio de precio, desaparición del top-10 o reset cierran el episodio.
  ADD posterior no demuestra reposición de la misma orden. Un nuevo descenso sustituye
  al pendiente. No se fabrica recuperación al terminar el archivo.
- **Disponibilidad causal:** el episodio se publica al observar la recuperación,
  no retroactivamente en la caída. Un filtro en una señal sólo puede usar episodios
  ya conocidos allí; los que se completen después serían look-ahead.

La coincidencia temporal/de precio **no atribuye el trade a esa orden ni identifica
el agresor**, y el volumen impreso no prueba que explique toda la reducción visible.

## Resultado observado

| Archivo de ejemplo | Filas L2 | Impresiones LAST | Caídas netas de tamaño a precio fijo | Caídas con trades compatibles | Recuperaciones observadas |
|---|---:|---:|---:|---:|---:|
| 20260531 (ejemplo corto) | 718.410 | 13.913 | 100.072 | 4.433 | 1.282 |
| 20260615 | 3.921.238 | 92.515 | 762.994 | 34.587 | 12.818 |
| Total de los dos ejemplos | 4.639.648 | 106.428 | 863.066 | 39.020 | 14.100 |

Mediana de demora desde caída hasta recuperación: **132 ms** en el primer archivo y
**100 ms** en el segundo. No se promedian medianas ni se interpreta la diferencia como
tendencia: son dos ejemplos de duración desigual, no una campaña representativa.

El conteo agregado corresponde a **transiciones/episodios**, no a órdenes únicas,
ni a icebergs, operaciones o señales rentables. No presentamos el cociente como una
probabilidad de absorción: el esquema incluye censura por nuevos descensos y salida
del precio de la parte visible del libro.

## QA y pruebas

- Cuatro parquet: sin nulos, precios fuera de grilla 0,1, duplicados de `source_row`,
  inversiones de fila o timestamp. Conteos contrastados con metadata Arrow; sin
  colisiones de filas entre L1 y L2, y orden temporal mixto verificado al reconstruir.
- Primer archivo: 34 grupos inválidos (uno desordenado y 33 cruzados/incompletos).
  El último termina en fila 203; el primer LAST aparece en 207. Son observaciones de
  inicialización, antes del primer trade registrado; se excluyeron y se reinició el
  bootstrap. No se repararon ni se usaron como evidencia de mercado. El otro archivo
  no mostró estos grupos inválidos.
- **12/12 pruebas unitarias del tracker:** trade ausente, futuro por tiempo o fila,
  vencido, no reutilización, desaparición/reaparición, cambio de precio, timeout,
  clave de precio en lugar de profundidad, inmutabilidad de eventos del prefijo y
  ausencia de recuperación inventada al EOF, además del caso normal.
- Recuento independiente de los JSONL privados: **14.100**. Ventanas y tamaño de
  recuperación verificados sobre todos los episodios. Balance de destinos de las
  caídas compatibles reconciliado por archivo, incluidos dos pendientes al EOF.
- Las pruebas unitarias no equivalen a certificación de feed/BBO ni de reconstrucción
  frente a un segundo proveedor.
- El profiler genérico no soportó Parquet en este entorno. Sus perfiles de CSV de las
  primeras 10.000 filas fueron sólo diagnóstico; QA completa hecha sobre arrays y
  metadata. No se atribuye QA de archivo completo a esa muestra.

## Qué aporta el research

CME distingue MBP (tamaño agregado por precio, diez niveles, sin posición individual
de cola) de MBO (órdenes individuales y prioridad). Estos ejemplos son **MBP**:
no permiten reconstruir la cola real ni identificar la misma orden oculta.

La literatura de detección de icebergs en CME aprovecha identificadores de orden y
mensajes de ejecución/refresh; para icebergs sintéticos incluso la inferencia con
MBO carece de ground truth completo. No trasladamos sus etiquetas a este MBP.

Fuentes consultadas:
- CME, *Market by Order*: https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html
- *CME Iceberg Order Detection and Prediction*: https://arxiv.org/html/1909.09495v1

**Conclusión:** hay un observable de recuperación del tamaño visible compatible con
trades, medible causalmente a precio fijo. No hay todavía evidencia de defensa efectiva,
liquidez oculta, atracción del precio, ventaja operativa ni transferencia a ES/MNQ.

## Próximo paso recomendado — NO MEDIDO

1. Fijar un plan de controles negativos emparejados por profundidad visible, magnitud
   de caída y actividad local conocida hasta el evento. Comparar con caídas sin prints
   compatibles; no usar información posterior para construir el control. Presupuesto
   de variantes fijado antes de contar, sin optimizar los umbrales con estos ejemplos.
2. Describir reposición repetida, persistencia y desapariciones en el nivel; distinguir
   salida del top-10 de retirada real. No bautizar los episodios como icebergs.
3. Llevar la capa al visor y luego a niveles/señales congelados, con ventanas pasadas y
   timestamps de disponibilidad explícitos. Validar paridad detector/visor.
4. Antes de evaluar retornos o costos: manifiesto/pre-registro y OK de Nico. GC aquí es
   laboratorio de implementación; para ES/MNQ hacen falta sus L1/L2 propios y señales
   causales alineadas. No transportar el resultado por analogía ni tocar el holdout.

La validación de climas MNQ que corre en la PC no se modificó ni se certificó aquí.

## Reproducción y huellas

Código ejecutado (sin cambios al copiarlo al repo):
`tools/gc_l2_fixed_price_probe.py`, SHA256
`58cff7065bb48cece561553ed3971f299bba36182a200237909122c9626376ea`.
Plan SHA256 `e46d0008edea119fee433901ddb0acf326f0fe01b85040e25ac3363df060d0ce`.
Módulo canónico SHA256 `a65e377ecc7e6b59b92c0c0c6bedd8b1c1aee7c41c142addb0dfeb01b588c891`.
Entorno realmente usado: NumPy 2.5.3, pandas 3.0.6, PyArrow 25.0.0.
No se afirma ejecución en el entorno completo del lock/CI.

```bash
python tools/gc_l2_fixed_price_probe.py --raw /ruta/privada/dataset_v2 \
  --out /ruta/privada/resultados \
  --book-module edgelab/research/l2_phase0.py
python -m unittest discover -s tests/research -p 'test_gc_l2_fixed_price_probe.py' -v
```

El CLI genera conteos básicos y episodios privados; balances independientes y diagnóstico
son evidencia del análisis de esta ejecución, no salidas automáticas del CLI. El hash de
plan se calcula sólo si hay `PLAN.md` junto al script: para reproducirlo, colocar allí la
copia del plan publicado; sin ella el campo queda `null`. No commitear raw ni JSONL
con niveles/precios de los episodios. Se publica sólo evidencia agregada y código.
