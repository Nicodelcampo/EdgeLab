# AVZVOL: distinguir negativo del detector, positivo y desconocido

**Pieza propuesta y probada con datos inventados; NO censo de mercado ejecutado.**
Está en `edgelab.kaggle.avzvol_zone_negative.classify_detector_window`.
No sustituye al detector, no modifica históricos ni autoriza matching/outcomes.

## Hallazgo del código original

En el [notebook recuperado y fijado](AVZVOL_ZONE_CAUSAL_REVIEW_20261010.md),
`run` calcula el umbral sólo si el bucket tiene suficientes muestras; de lo
contrario usa `thr = -1.0`. Crea una zona sólo con `thr > 0 and sc >= thr`.
Por tanto, una lista vacía de zonas puede significar falta de calibración,
no una observación negativa válida. Con menos de tres niveles de precio ni
siquiera recorre esa rama: la futura cinta debe declarar ese caso, no inventar
un umbral. El umbral histórico usa sesiones previas por bucket; la calibración
se debe acreditar para CADA bloque, no por contrato agregado.

Referencia exacta: notebook k1 SHA256
`58e81f5cf440921a88f164ae3e974709f7296d130f22ecb9271c06fb369ad310`,
función `run`, líneas 147–245; condiciones de umbral en 210–228.
La función activa se llama `zp2_run`; usa `SPEC = 25`, pese a un comentario
antiguo que dice barras de 50 ticks. La revisión no altera esa definición.

## Contrato del helper propuesto

Entradas: sesión ISO, primera barra declarada de sesión, inicio de ventana y
ancla inclusivos, tamaño de bloque y mínimo de muestras explícitos, fecha
holdout explícita, y una lista de observaciones de detector. No hay defaults
científicos ocultos. No elige ventanas ni calipers mirando O5.

Cada observación tiene exactamente:

| Campo | Significado declarado |
|---|---|
| `session` | Sesión natural del bloque |
| `block_end_bar` | Barra de cierre del bloque del detector |
| `available_bar` | Momento en que esa decisión era observable |
| `threshold` | Umbral positivo de ese bloque, o desconocido |
| `calibration_samples` | Muestras del bucket al decidir |
| `baseline_last_session` | Última sesión de la calibración; debe preceder a la actual |
| `detected_zone_count` | Cantidad de zonas creadas entonces, no su estado final |

No se aceptan campos de outcomes ni `state`/`racimo_id` finales. Los registros
posteriores a la sesión/ancla se ignoran: añadir decisiones futuras válidas no
puede cambiar la clasificación pasada. Duplicados y bloques fuera de la secuencia
esperada causan STOP; no se deduplican ni inventan.

Regla conservadora propuesta, NO aprobada como definición científica:

- **DETECTOR_NEGATIVE:** todos los bloques programados de una ventana alineada y
  de la misma sesión están presentes y disponibles al ancla, con umbral positivo,
  muestras suficientes y baseline de sesiones previas; todos declaran cero zonas.
- **DETECTED_ZONE:** hay al menos una zona en un bloque utilizable; los motivos de
  cobertura desconocida de otros bloques se conservan, no desaparecen.
- **UNKNOWN:** faltan bloques, calibración/as-of/conteos, hay límites parciales o
  la ventana atraviesa el inicio declarado de sesión. Nunca convertirlo a negativo.

**Sin zona detectada aquí ≠ sin racimo al ancla ≠ consolidación comparable.**
`racimo_absence` queda `NOT_ASSESSED`: puede haber zonas anteriores a esta ventana
que formen un racimo. La geometría de consolidación, su enumeración y la ventana
adecuada todavía requieren protocolo. Este helper deliberadamente no declara
`eligible_control` ni alimenta automáticamente el matcher.

Todos los campos de certificación/autenticidad/completitud/aprobación/permisos
se mantienen false. Los inputs son declaraciones: alguien puede mentir sobre
bloques, muestras, origen de sesión o conteos. Pasar el helper no los autentica.
El guard de holdout es sólo trade date; no sustituye pins, footer UTC, calendario
ni el gate de acceso ANTES de construir la cinta con precios.

## Qué se revisó de los artefactos existentes

Los seis exports fijados de la [revisión O5](AVZVOL_EXPOSED_O5_REVIEW_20261010.md)
no conservan este registro por bloque, ni un censo completo de consolidaciones.
Los listados MCP actuales de k1/k2/k3 muestran sus dos exports y `procedencia.json`,
no barras/footprints/cinta del detector. Son listados sin pin de versión: no se
usan como evidencia del contenido histórico ni se sustituyen los seis pins.
El MCP rechazó `versionLabel="1"`; la consulta sin label fue sólo inventario.
No se infiere corrupción ni tamaño real de exports a partir de esos listados.

## Siguiente reconstrucción, sin outcomes

1. Recuperar las fuentes ya existentes con pins exactos y controles de acceso;
   conservar todas las limitaciones de [calidad MNQ](../infra/AVZVOL_MNQ_RAW_QUALITY_20261010.md).
2. Emitir una cinta append-only en CADA cierre de bloque, incluyendo cold-start,
   pocas muestras, ausencia de hot clusters y bloques incompletos. Registrar
   fuente/detector/hash, calendario, origen de sesión, muestras y disponibilidad.
   No reconstruirla con estados finales de zonas ni membresía futura de racimos.
3. Revisar/congelar la regla de enumeración de consolidaciones y sus ventanas.
   Distinguir el registro de una propuesta de su aprobación; los campos científicos
   existentes `negative_classification_asof_rule`, `control_census_selection_rule`
   y `cross_session_cluster_policy` siguen null. Este helper no los llena.
4. Mantener UNKNOWN, no soportados y exclusiones en el censo. Después revisar
   estratos, balance/reutilización y comparar controles contra su propio censo.
   Sólo entonces considerar efectos nuevos no económicos.

No se calcularon prevalencias de zonas, contaminación, contrastes de mercado ni
outcomes en esta pieza. Las pruebas son exclusivamente sintéticas. Sin P&L,
sin holdout y sin reescribir resultados originales. El censo real sigue pendiente.

## Validación de software

622 tests +25 subtests; 35 casos nuevos inventados; 18 checks de navegación.
Guards de fecha reservada y cinta ausente verificados también con Python `-O`.
[Registro de alcance](../../config/research/avzvol_zone_negative_development_v1.json).
Esto acredita pruebas del software, no calidad de fuente ni resultados de mercado.

## Productor de cinta y riesgo de ventana O5

[API, reproducción y auditoría](AVZVOL_DETECTOR_TAPE_AND_O5_BOUNDARY_20261010.md): productor del detector histórico
instrumentado, sin loaders ni estados finales. Censo real pendiente. Desfase
de una barra en el guard O5 documentado; QA acotada de etiquetas existentes no
lo descarta. No outcomes nuevos ni certificación; P4 sigue prohibida.
