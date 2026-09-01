# Hipótesis Pendientes

Tablero de hipótesis **no concluyentes** (sugerentes pero no demostradas). Cada
entrada tiene: definición, por qué importa, evidencia acumulada, qué la
cerraría, y estado. Se nutre de `DIRECCIONES_INVESTIGACION.md`,
`BITACORA_CONEXIONES.md`, `PREHOLDOUT_ADDENDUMS.md` y las verificaciones de
Gates 1/2.

**Reglas de uso**

- Nada acá se reporta como edge. Es material de investigación en curso.
- Cada hipótesis vive en UNA línea de trabajo a la vez; no bifurcar sin asentar.
- Cuando una se confirma con el protocolo estándar, sale de este archivo y se
  documenta como hallazgo (spec nueva o sección del censo). Cuando se
  falsifica, se cierra con la evidencia que la mató (también vale).
- **Ninguna hipótesis de este tablero se trabaja en holdout (P2).** A partir
  del 2026-08-16, el holdout ES-06-26 y los datos ES aún no ingeridos (ES
  12-25/03-26) son buffer canónico del gate (P-42), no material exploratorio.

## Definición operativa (para no repetir en cada entrada)

Todas las hipótesis siguientes son **operativas y filtrables** bajo este
protocolo: (i) diseño de medición preregistrado antes de mirar resultados del
test; (ii) **control de comparaciones múltiples** acorde al barrido real
(Romano-Wolf stepdown o, si no aplica, Holm; nunca p crudos); (iii) chequeo de
**robustez** sobre los knobs declarados (desplazamientos ±, régimen
alto/bajo, o la partición que corresponda a la línea); (iv) **evaluación
económica neta de costos** en la misma moneda del estudio; (v) **capacidad /
N efectivo = sesiones**, con intervalos por bootstrap de sesiones y etiqueta
ante cada ventana (`full_day` / `RTH` / ventana corta); (vi) **replicación
fuera de muestra** en un segmento que no haya tocado el diseño; (vii)
criterio de falsación escrito de antemano (incluyendo qué cuenta como "no
concluyente" y qué se registra en ese caso).

---

## P-49 — La "firma" de BigTrap2 (régimen + sesión + día + dirección)

- **Definición.** El rendimiento bruto de BigTrap2 (y de cualquier candidato)
  no es una propiedad del patrón solo, sino del patrón **dentro de un régimen
  definido**: sesión/hora del día (EU vs US), día de la semana, dirección del
  movimiento, volatilidad (RV vs VIX implícito), y régimen de alta/baja
  dispersión. Esa firma se mide sobre la muestra de diseño y se congela como
  pre-spec del estudio principal.
- **Por qué importa.** El dolor del G2 multi-asset mostró que parámetros
  elegidos sin firma ("±1/±5" universales) no transportan entre instrumentos.
  La firma es la respuesta estructural: en vez de un set global, se mide
  primero **dónde y cuándo** funciona cada instrumento, y el estudio
  principal corre solo en esas celdas. Además la firma permite comparar
  cohortes entre instrumentos sin mezclar manzanas con naranjas (mismo
  régimen, distinto subyacente) y da la base para atribuir performance a
  régimen y no a suerte (media condicional vs incondicional, con IC).
- **Evidencia acumulada.** (i) La tabla por fecha del estudio 6E (addendum
  002) ya sugiere heterogeneidad diaria enorme (días negativos puros junto a
  días salvadores). (ii) La heterogeneidad por subgrupo está implementada en
  el motor G2 (por hora, por DOW, por dirección, por RV, por régimen) — la
  maquinaria existe; lo que falta es el **protocolo de firma**: cómo se
  decide qué celdas entran a la pre-spec sin hacer cherry-picking con los
  mismos datos que después evalúan. (iii) Collinearidad entre ejes (día de
  la semana ~ evento macro; hora ~ volatilidad) ya documentada: la firma se
  estima con atribución, no con filtros encadenados.
- **Qué la cerraría.** (i) Definir el protocolo de firma (muestra de diseño,
  métricas, regla de inclusión de celdas, control de comparaciones
  múltiples); (ii) producir la firma 6E como caso piloto; (iii) congelar la
  pre-spec del estudio principal 6E a partir de ella; (iv) repetir en ES y
  comparar firmas (¿mismo régimen horario? ¿misma sensibilidad a RV?).
- **Estado:** ABIERTA. El motor mide subgrupos; el protocolo de firma no
  existe todavía. Es el candidato natural a ser el siguiente addendum (007).
- **Nota de composición (2026-08-16).** Con P-52 (cola first-touch) y P-53
  (sesiones, no modelos), la firma deja de ser una curiosidad y pasa a ser
  **condición de interpretación** de cualquier headline futuro: una cola que
  solo aparece en ciertas sesiones y un modelo cuya varianza entre sesiones
  es ancha son la misma advertencia vista desde dos lados — el contexto no
  es ruido alrededor del efecto, es parte del efecto.

---

## P-50 — Barras de tiempo (15m) no se integran al pipeline F2

- **Definición.** La integración de barras de 15 minutos al pipeline canónico
  (F2) está **descartada para la línea actual**.
- **Por qué se registra.** Para que la decisión sea visible y no se reabra
  por inercia: el costo de mantener dos granularidades supera el beneficio
  mientras el libro de señales viva en escala tick/minuto.
- **Qué la reabriría.** Una línea nueva que necesite estructura de 15m (p.
  ej. cruzar zonas POI con contexto de mayor marco temporal) — se decide en
  esa línea, con su propio costo.
- **Estado:** CERRADA (no hacer). Decisión de cierre documentada acá para no
  depender de memoria de chat.

---

## P-51 — Barras de tiempo (5m): prototipo standalone aislado

- **Definición.** Construir un prototipo de barras de 5 minutos sobre
  `TickSeries` como **herramienta aislada** (`bridge.time_bars`), sin tocar
  el pipeline ni las specs existentes. Sirve para medir propiedades de
  régimen (rango, actividad, volatilidad agregada) con granularidad uniforme
  donde las barras de tick distorsionan comparaciones horarias.
- **Por qué importa.** P-49 necesita atributos de régimen en escala de
  minutos (la firma horaria con barras de tick mezcla actividad con tiempo).
  Un prototipo 5m aislado permite experimentar sin comprometer el camino
  canónico.
- **Qué la cerraría.** El prototipo corre y produce la serie 5m con
  timestamps alineados a la sesión (mismas reglas de calendario que
  `bridge.sessions`); se usa en exactamente una medición de P-49. Si la
  medición no aporta, se archiva el prototipo y se cierra.
- **Estado:** ABIERTA — trabajo chico y acotado, puerta de entrada a P-49.

---

## P-52 — Cola first-touch de H4b (post-C1)

- **Definición.** H4b quedó con evidencia de cola en primer toque pero
  **inconclusa** (C1): si la cola no es red bajo costos estándar, no
  constituye hallazgo económico. La pregunta operativa es si existe una
  lectura de la cola que sí lo sea (p. ej. interacción con firma de P-49,
  umbrales más estrictos, o rol como filtro y no como entrada).
- **Por qué importa.** Es la cola más grande medida en el estudio 6E y la
  única que sobrevivió control de comparaciones; si no es monetizable tal
  cual, hay que decidir si se trabaja o se archiva con la etiqueta correcta.
- **Evidencia acumulada.** Addendum 005 (cola first-touch, C1); P-48 cerrada
  (cola horaria = rutina). La cola es bruta; la pregunta neta quedó
  explícitamente abierta.
- **Qué la cerraría.** Medición neta con costos en la celda donde la cola es
  más fuerte, con la firma de P-49 como marco; si la cola neta no supera el
  piso económico, se cierra como "cola bruta sin valor de trading" y queda
  como hecho descriptivo del fenómeno.
- **Estado:** ABIERTA. Depende de P-49 (sin firma no hay celda donde medir).
- **Nota.** P-52 y P-53 son el mismo tipo de advertencia: una cola que solo
  aparece en ciertas sesiones y un modelo cuya varianza entre sesiones es
  ancha. La conexión queda registrada; la integración es trabajo de diseño,
  no de chat.

---

## P-53 — Sesiones, no modelos (granularidad de decisión)

- **Definición.** La unidad de decisión para cualquier claim de borde es la
  **sesión completa** (23h CME), no el subsegmento ni el régimen horario.
  Los modelos/variantes se comparan por su distribución de resultados **por
  sesión**, con N efectivo = sesiones y bootstrap por sesión; la varianza
  entre sesiones es parte del headline, no una nota al pie.
- **Por qué importa.** Las colas medidas (P-52) y las firmas (P-49) viven en
  subsegmentos; si la decisión final se tomara en la misma escala en que se
  descubrió el efecto, se estaría sobre-ajustando a la granularidad del
  descubrimiento. "Sesiones, no modelos" es la regla que impide ese salto:
  el modelo que gana en mediana pero con cola de sesiones malas no es el
  modelo que se opera.
- **Evidencia acumulada.** G2 ya corre con N=sesiones; el addendum 005
  mostró cuánto cambia el resultado entre ventanas; P-46 (bigtrap en NQ) ya
  exigió sesiones completas por el costo de cortar la sesión.
- **Qué la cerraría.** Queda cerrada como **norma** cuando la plantilla de
  informe del G2 incluya por defecto la distribución por sesión con su IC y
  la etiqueta de ventana, y ningún claim se escriba sin esas dos líneas.
- **Estado:** ABIERTA como norma a asentar en la plantilla G2 (trabajo
  chico, de documentación/código de reporte).

---

## P-54 — "Detección separada de ejecución" (frase acuñada)

- **Definición.** Regla de arquitectura: **medir y operar son dos sistemas
  distintos**. Lo que se usa para detectar/descubrir (censo, kernels de
  investigación, parámetros sensibles) no es lo que se usaría para ejecutar
  en producción; y a la inversa, una herramienta de ejecución no se usa
  como fuente de evidencia de investigación sin pasar por el pipeline de
  paridad.
- **Por qué importa.** Mezclar los dos papeles fue la raíz de varios
  errores del proyecto (leer outcomes del mismo indicador que dibuja en
  pantalla; usar el export de NT8 como si fuera medición neutra). La frase
  queda como atajo de comunicación: cuando alguien proponga usar una
  herramienta de un rol en el otro, la respuesta es esta entrada.
- **Estado:** CERRADA como **terminología aprobada** (2026-08-14, queda
  asentada acá para uso permanente). No es una hipótesis a falsar: es una
  convención de diseño.

---

## P-55 — "El contexto es un objeto, no un supuesto" (frase acuñada)

- **Definición.** Regla de modelado: el régimen (sesión, día, dirección,
  volatilidad) no se asume de fondo ni se deja implícito — se **declara como
  objeto medible** (la firma de P-49) y viaja con la hipótesis. Toda
  hipótesis nueva que llegue al tablero tiene que decir en qué contexto vive.
- **Por qué importa.** Es la forma corta de P-49+P-53: las dos veces que el
  proyecto se equivocó de escala fueron por tratar el contexto como ruido
  alrededor del efecto en vez de parte del efecto.
- **Estado:** CERRADA como **terminología aprobada** (2026-08-14), misma
  lógica que P-54. Las hipótesis que lleguen sin contexto declarado se
  devuelven con esta entrada.

---

## P-56 — Ingesta de datos Dukascopy completada (vía NT8, 2026-08-16)

- **Definición (registro de hecho, no hipótesis).** La carga de ticks
  Dukascopy vía NT8 quedó completa en cobertura: **ES** 4/4 contratos
  (2025-09-15 → 2026-09-11), **6E** 4/4 (2025-09-15 → 2026-06-12), **NQ** 6/6
  (2025-09-15 → 2026-09-11), **GC** 4/4 (2025-10-27 → 2026-10-23),
  **+SI 09-25**. Totales: 124,2M ticks / 2,13 GB (ES), 102,4M / 1,54 GB (6E),
  144,1M / 2,29 GB (NQ), 25,0M / 484 MB (GC). Incluye bid/ask. Ventana de
  holdout declarada: ES 06-26 **2026-06-15 → 2026-09-11**. Conteos
  auditables en `data/registry/dukascopy_nt8_counts.json` (generado por
  `tools/audit_nt8_dukascopy.py`); gaps declarados en
  `docs/GAPS_DUKASCOPY_NT8.md`.
- **Estado:** CERRADA (hecho registrado). Esta entrada existe para que la
  cobertura no dependa de memoria de chat.

---

## P-57 — Descarte de datos públicos gratuitos para ticks CME

- **Definición (registro de hecho + research).** Se verificó por web
  (2026-08-16) que **no existe fuente pública gratuita** de datos tick-level
  CME con bid/ask (CME Datamine, Databento, Dukascopy directo: todos pagos o
  sin cobertura real). Dukascopy-vía-NT8 queda como la fuente única
  gratuita viable; el camino pago (Databento ~$0,25/GB) queda registrado
  como opción si se necesita extender cobertura. Documento:
  `docs/research/RESEARCH_PUBLIC_TICK_DATA_SOURCES_2026-08-16.md`.
- **Estado:** CERRADA (hecho registrado).

---

## P-58 — Tres palancas de ejecución liviana (DECIDIDA — integración prioritaria)

**Decidida 2026-08-30 ~23:05 ART por Nico** («anotá de manera prioritaria las
3 palancas para que se integren al proyecto ahora mismo»). Fundamento
completo: `docs/research/RESEARCH_LIGHTWEIGHT_EXECUTION_OPTIONS_2026-08-30.md`.

1. **TPU-VM de Kaggle como máquina CPU** (96 cores / 330 GB RAM, cuota
   ~20 h/semana, sesiones de 9 h) para el trabajo data-bound pesado
   (campaña SL/TP, bootstraps grandes). Misma plataforma, política y
   protocolo de atestación; el contrato de paralelismo + checkpoints
   byte-idénticos la hace usable contra el tope de 9 h.
2. **GitHub Actions para TODO lo data-free** (gratis e ilimitado en repo
   público, runners 4 vCPU, se dispara por push). Primer uso: la suite de
   verdad conocida de Romano-Wolf + MCS — blocker de freeze de la campaña
   SL/TP.
3. **Polars/DuckDB en capas de carga y estratos** (5-10× menos memoria que
   pandas; streaming / out-of-core), con el test de determinismo
   byte-idéntico como puerta de admisión.

**No cambia:** `KAGGLE_ONLY_EXECUTION_POLICY_V1` para lo confirmatorio;
ninguna plataforma externa recibe ticks CME (licencia). Cualquier burst
externo futuro = enmienda de Nico + revisión de licencia primero.

## P-59 — ML que aprende lógicas por sí solo (LightGBM): research hecho, adopción pendiente de Nico

**Registrada 2026-08-30** desde la pregunta de Nico. Research completo:
`docs/research/RESEARCH_ML_LOGIC_DISCOVERY_LIGHTGBM_2026-08-30.md`.

**Respuesta:** sí, con el encuadre publicado «ML como generador de
hipótesis» (Ludwig & Mullainathan, NBER w31017): el modelo descubre
patrones (EF1, pre-holdout, búsqueda logueada para su N_eff), el
humano/auditor traduce lo aprendido a una regla falsable escrita, y la
confirmación es preregistrada sobre datos que el modelo nunca vio. **El
modelo nunca confirma lo que descubrió.** Requisitos no negociables si se
adopta: purged/embargoed CV + walk-forward, DSR/PBO sobre la búsqueda (ya
en repo), evaluación económica neta de costos, N efectivo = sesiones
(P-53).

**Consistente con el board:** P-53 (sesiones, no modelos), P-55 (contexto
como objeto), P-49 (la «firma» es la puerta natural — F4 del addendum 007).
**Orden:** después de la línea actual (D3) y de P-44 (sin parámetros que
transportan entre instrumentos, el modelo aprendería artefactos de escala,
no el mercado).

**Criterio de cierre:** Nico decide si se abre la línea «fábrica de
hipótesis ML» con su manifiesto propio. Mientras tanto: ABIERTA, sin
código.
