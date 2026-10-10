# AVZVOL: qué significa «sin zonas» y cuándo se conoce un racimo

**Revisión de código y caracterización sintética; no resultado de mercado.**
No se leyeron nuevos ticks, covariables de mercado ni outcomes. No se modificó el
detector, se midió contaminación real ni se adjudicó sesgo del resultado anterior.
La revisión de publicaciones hasta este lote no encontró un checkpoint nuevo de
originales NT8/censo revisado. La comparación científica sigue bloqueada.

## Identidad de la fuente

Notebook recuperado `nicolasbuttaro/edgelab-avzvol-k1`, versión 1, SHA256
`58e81f5cf440921a88f164ae3e974709f7296d130f22ecb9271c06fb369ad310`, igual al pin
registrado en [procedencia candidata](../../config/research/avzvol_lineage_candidates_20261010.json).
Las funciones `_racimo`, `racimos_de` y `run_contract` son AST-equivalentes a las
fuentes de Git en `4e1e26930f9778f974a4dd4946977ac48b1725d8`:

- [etapa 1, formación y controles](https://github.com/Nicodelcampo/EdgeLab/blob/4e1e26930f9778f974a4dd4946977ac48b1725d8/tools/avzp2_racimo_grid_stage1.py).
- [aVolZonePOI2 y _racimo](https://github.com/Nicodelcampo/EdgeLab/blob/4e1e26930f9778f974a4dd4946977ac48b1725d8/edgelab/bridge/indicators/avolzonepoi2.py).

No se importó/ejecutó el notebook. Sólo se extrajeron las dos funciones puras de
formación para un fixture fijado por SHA, probado con zonas inventadas. La identidad
de fuente recuperada NO prueba qué versión de imports/raw se montó históricamente.
Este código usa `aVolZonePOI2` y `SPEC=25`; no sustituirlo por `AVolZoneSimple` ni
por otra variante de aVolClusterPOI. Un cambio de detector sería otra identidad de método.

## Hallazgos concretos

### Z1. «Pseudo» no acredita un control sin racimo

`run_contract` forma un pool de barras aprobadas del contrato, filtra la franja
`clock`, traslada la banda del real alrededor del close candidato y acepta por
ocupación. No filtra por igual sesión ni por clasificación negativa del detector.
Tampoco demuestra un censo independiente de consolidaciones sin racimo: la
geometría se deriva del real. Eso caracteriza el control histórico, no demuestra
que un pseudo observado esté contaminado ni el tamaño/dirección de un sesgo.
No rebautizar el resultado de control de actividad como efecto incremental limpio
«con zonas vs. sin zonas». [Código L261–279](https://github.com/Nicodelcampo/EdgeLab/blob/4e1e26930f9778f974a4dd4946977ac48b1725d8/tools/avzp2_racimo_grid_stage1.py#L261-L279).

### Z2. Formación del racimo no es nacimiento de su primera zona

Con zonas inventadas en barras 10 y 20 y mínimo 2, el racimo se reconoce en 20,
pero `start0=10`. La zona vieja recibe `racimo_bar=20`, no 10. La pertenencia final
no era observable en el momento de creación de esa primera zona. No usar el
`racimo_id` final para clasificar controles retrospectivamente en anclas anteriores.
Eso sería un riesgo de look-ahead en una NUEVA clasificación; aquí no se afirma
que el runner histórico haya usado esa exclusión. Su pseudo pool no la usa.

### Z3. Extensión final no equivale a banda disponible al formarse

Una tercera zona inventada puede ampliar `high` de 102 a 104; `high0=102` y
`bar/start0/low0` permanecen como snapshot de formación. La etapa 1 usa `low0/high0`
para los reales: no se detecta aquí un uso de la banda final en ese camino.
El futuro censo debe preservar snapshot y tiempo de disponibilidad, no usar la
geometría final para reconstruir el ancla.

### Z4. La formación legacy no exige una sola sesión

`racimos_de` copia bar/low/high y descarta identidad de sesión; `_racimo` limita por
distancia de barras, no por sesión. El ejemplo sintético con dos sesiones declaradas
produce un racimo. En `run` se reinicia el bloque parcial al cambiar de sesión,
pero no se vacía la lista `zones`; eso no impone una frontera al replay de racimos.
No es prueba de frecuencia real ni de fallo no intencional: decidir mantener o
prohibir formación entre sesiones exige política explícita y nueva identidad si
se cambia el método. No corregir retroactivamente evidencia histórica.

### Z5. «Previo» no garantiza ventana completa dentro de una sesión

`occ`, `act`, tendencia/momentum y rango previo recorren índices globales de barras.
`act` sólo comprueba inicio del archivo; quitar el salto temporal entre sesiones
no evita sumar barras de la sesión anterior. El filtro global de pool tampoco
verifica cada prewindow dentro de sesión. Debe definirse si se permite arrastre
de historia y revisarse su completitud/calidad; no marcar `prewindow_complete=true`
sólo porque hay suficientes índices.

## Contrato que debe aprobarse ANTES de un censo real

Estos son requisitos/decisiones pendientes, no parámetros aprobados:

1. **Tratamiento exacto:** distinguir «sin zona detectada» de «sin racimo ya
   formado». Un ejemplo con una sola zona puede no tener racimo: no son sinónimos.
   Declarar celda, ventana de clasificación y universo de consolidaciones candidatas.
2. **As-of:** registrar creación de cada zona, barra/UTC de reconocimiento del
   racimo y disponibilidad de cada snapshot. El ancla no puede preceder a esa
   disponibilidad. El historial futuro no puede alterar la etiqueta ya emitida.
3. **Sesión:** declarar política de formación, sesiones de todas las zonas y
   ventanas previas, más calendario y completitud revisados. No inventar una
   frontera basándose en fechas del archivo ni en el nombre del contrato.
4. **Censo completo:** decisión del detector para TODAS las candidatas, incluidas
   abstenciones por warmup/datos insuficientes. UNKNOWN/abstención no equivale a
   «no hay racimo». No elegir candidatos por salida/rebote/horizonte futuro completo.
5. **Matching:** misma sesión/contrato/celda/franja/signo según protocolo propuesto;
   política externa aprobada para calipers/escalas/soporte/balance. Sin relajación
   retrospectiva. Registrar IDs, rechazos, reutilización y estimando soportado.
6. **Después:** revisar diagnósticos pre-anchor; sólo con fuentes y protocolo
   aprobados abrir O5/censura y endpoints no económicos congelados, con familia y
   presupuesto. Desarrollo expuesto no se convierte en confirmación ciega.

El [spec](../../specs/research/avzvol_incremental_design_v1.json) mantiene `null` en
regla del censo, clasificación negativa as-of, política entre sesiones, pins,
calipers, aceptación y presupuesto. P4 continúa prohibida.

## Pruebas y evidencia

```bash
python -m pytest -q tests/test_avzvol_zone_causal_review.py
```

Caracterización del código legacy, no modificación de producción. Fixture con
funciones puras; sin imports, loader ni outcomes. Prueba reconocimiento posterior,
snapshot de formación, extensión posterior, cruce de sesiones posible, límite por
barras y diferencia entre ausencia de zona y ausencia de racimo.
[Evidencia legible por agentes](../../config/research/avzvol_zone_causal_review_v1.json).
La [herramienta descriptiva](AVZVOL_CONTROL_CENSUS_DIAGNOSTICS_20261010.md) sigue sin
verificar clasificación/completitud ni conceder aceptación o autorización.

Validación local de este lote: **580 tests + 25 subtests**, navegación 18 tests;
PASS de software/fixtures, no certificación ni contraste científico.

## Solicitud de ejecución posterior del usuario

El usuario pidió calcular nuevos efectos **cuando esté listo**. Se registra como
solicitud condicional para efectos NO económicos: racimos frente a controles
comparables y controles frente a su propio censo. No aprueba los parámetros
científicos pendientes ni sustituye evidencia independiente de calidad/pins, censo
causal, revisión de exposición y protocolo congelado. `research_authorized` sigue
falso hasta satisfacer esos requisitos; no se abre holdout ni se habilita P4/P&L.
No lanzar una corrida provisional con defaults sintéticos para cumplir la solicitud.
