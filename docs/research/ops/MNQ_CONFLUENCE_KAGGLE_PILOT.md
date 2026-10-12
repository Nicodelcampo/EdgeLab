# Piloto técnico de confluencias en Kaggle

## Separación de alcances

El primer notebook nuevo es **SYNTHETIC ONLY**: genera su tape dentro del proceso, no acepta un path/tape de mercado, no usa mounts ni Internet y no abre etiquetas, outcomes, holdout o P&L. Es una prueba de empaquetado, identidades, semántica y presupuesto. No sustituye medir densidad, soporte o rendimiento con MNQ real ni completa el estudio científico.

Se recuperó de los archivos embebidos del focal privado `nicolasbuttaro/edgelab-mnq-09-26-frozen-longevity-focal` la metadata `avzvol_exploratory_authorization_v1`. Su alcance es `EXPLORATORY_ONLY_PER_CONTRACT`, con original no disponible y calidad no certificada. No se importaron ticks ni eventos privados fuera de Kaggle. Esa autorización histórica no se transforma en `SANITIZED_VERIFIED`, no aprueba automáticamente nuevas fuentes/particiones y no equivale a una nueva revisión independiente. El pin recuperado está en el plan técnico, sin URLs firmadas.

Antes de un piloto de mercado se debe vincular explícitamente el alcance nuevo a esos riesgos, fijar fuente/versión/hashes, sesiones target y formación suficiente, otras reservas y presupuesto. Puede usarse la vía exploratoria autorizada y sus controles específicos; no inventar un certificado canónico ni exigir el original como condición imposible. La aproximación de paridad aceptada sigue vigente.

## Runner implementado

- `pilot_runtime.py`: 96 configuraciones completas del roster fijo y 32 triadas alineadas (una config por familia en cada triada). **No es el cruce cartesiano de configs** ni selección de combinaciones prometedoras. Perfil de ramas, no análisis inferencial.
- Fixture fijo: 25 sesiones declaradas, 1.200 ticks/sesión, 30.000 ticks inventados. No reducir `min_samples`, `MinHistoryBuckets`, lookback ni ninguna otra configuración del roster. Ausencia de births aquí no prueba ausencia de mercado ni garantiza warmup suficiente para cada escenario.
- Caches lazy por bar spec: barras compartidas, footprint agresor BT2 y TOTAL NT8 AVZ separados. No reutilizar uno como el otro. Guardar preparación completa por identidad del tape en el proceso.
- Guardar sólo un output nativo temporal por ejecución. Hash incremental tipado y comparación exacta capture/native para cada config. Retener receipts de lifecycle con límite total; no materializar una matriz configuración × tick ni almacenar Frames del replay.
- Replays seriales de las 32 triadas con las cuatro definiciones racimo preparadas. Hash de Frames no vacíos y conteos agregados, sin eventos/zonas exportados. Estos probes no sustituyen los controles espaciales/temporales del estudio.
- Guardar tiempos por etapa/config/triada, preparación/cache y RSS. Son medidas de **ese input y host**, no velocidad MNQ, benchmark estable, ahorro causal o RAM del full atlas.

## Ejecución acotada y empaquetado

`package_synthetic_notebook.py` empaqueta fuentes mediante allowlist explícita y bytes/hash de cada archivo; no incorpora secretos, URLs firmadas ni datos. La fuente de los detectores además se verifica contra pins originales en runtime. El commit declarado y el bundle hash quedan separados.

Notebook privado CPU y offline; el save request es `SaveAndRunAll` y se envía sólo después de persistir código/tests/checkpoint. Bootstrap aislado en directorio temporal, source verify antes de ejecutar, receipts en `confluence-synthetic-pilot/`.

Límites del probe: timeout del padre 900 s, deadline cooperativo 780 s, `RLIMIT_CPU` 840 s, `RLIMIT_AS` 4 GiB, parada por RSS muestreado >2 GiB. El hijo conocido inicia su process group y se mata completo al exceder los límites. Es scope **single child process group, no cgroup**; address space no es RSS. No afirmar aislamiento de árbol arbitrario o presupuesto de todos los procesos del contenedor. Bootstrap aplica los límites antes del exec; fallo no se etiqueta COMPLETE.

Runtime: máximo 100.000 ticks, 200.000 registros lifecycle y 10.000 episodios/pairs/triples por triada. Overflow/deadline rechaza sin truncar. Para mercado grande faltan streaming/checkpoint de calibración detectora, presupuesto conjunto de caches/logs, source reader exploratorio y fuente/sesiones binded antes de acceder a filas. No resolver warmup leyendo un prefijo minúsculo o consultando datos futuros.

## Evidencia local y prueba de paquete

`MNQ_CONFLUENCE_SYNTHETIC_PILOT_LOCAL_RECEIPT.json` guarda el piloto local completo: 96 capturas comparadas exactamente con los kernels nativos y 32 replays terminados sobre el fixture inventado. No representa ejecución Kaggle ni nuevos resultados MNQ.

Las pruebas del paquete ejecutan de verdad el bootstrap aislado con una versión diminuta del fixture. Ese test encontró `edgelab.bridge.sessions` faltante por imports del registry; se añadió a la allowlist y el paquete pasa. Tests de deadline, input budget, roster modificado, hashes tipados y caches separados también pasan.

## Reproducir

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m tools.research_ops.confluence.pilot_runtime \
  --roster docs/research/ops/MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json \
  --out /ruta/nueva/synthetic-receipt.json
python -m tools.research_ops.confluence.package_synthetic_notebook \
  --root . --source-commit FULL_COMMIT_SHA \
  --request-out /ruta/nueva/notebook-request.json \
  --receipt-out /ruta/nueva/package-receipt.json
```

El segundo comando sólo prepara: no lanza ni accede a Kaggle. El CLI del primero no ofrece modo mercado ni bypass de elegibilidad.
