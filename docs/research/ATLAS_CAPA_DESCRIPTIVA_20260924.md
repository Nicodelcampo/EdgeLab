# Atlas: capa descriptiva de observaciones (inicio del embudo), 2026-09-24

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué es y qué no es

Hasta hoy, toda medición económica del proyecto era una **prueba**: pre-registro, un estimand, sobrevive o muere. Eso protege contra edges falsos, pero deja un hueco. **Lo que no se preguntó no queda medido**, y "murió la versión X" se lee como "el fenómeno no sirve", cuando solo murió X (la regla "toda muerte tiene alcance preciso").

El atlas es la capa que falta: **observaciones descriptivas** de un fenómeno, que **no promueven ni descartan nada**.
- **Registran:** qué es el fenómeno, cuándo aparece, en qué contexto y cómo se comporta el precio alrededor.
- **Apoyan:** otros análisis las citan como contexto (costos, frecuencia, estado del libro).
- **Sugieren:** qué pruebas vale la pena pre-registrar, y en qué datos tienen que confirmarse.

## El riesgo, y por qué hace falta disciplina

Una capa descriptiva que mira retornos **es** exploración de datos. Si después se "confirma" una idea en los mismos datos donde se la vio, se fabrica un edge falso: es el jardín de los senderos que se bifurcan, como el subgrupo post hoc de HP-008. La literatura de ciencia abierta resuelve esto separando **exploración** de **confirmación** (Wagenmakers et al. 2012; de Groot 1956/2014): se explora libremente en una partición, **se declara lo que se vio**, y se confirma solo en datos que nadie miró.

## Reglas (fijadas antes de medir)

1. **Dos tipos de observación:**
   - **Target-free** (estado, frecuencia, contexto, co-ocurrencias): no miran retornos. Pueden usar toda la historia pre-holdout.
   - **Perfil de respuesta** (qué hace el precio después del evento): **sí** miran retornos. Solo se calculan en una **partición de exploración declarada antes de medir**.
2. **Particiones registradas en el Brain antes de calcular:** `EXPLORATION`, `CONFIRMATION_RESERVED` o `FUTURE`. La reservada no se mira para nada que involucre retornos hasta que una prueba pre-registrada la use.
3. **Sin veredictos.** Una observación publica estimaciones, **distribuciones completas**, intervalos por sesión y **resolución** (qué tamaño de efecto puede distinguir la muestra). No publica p-valores contra un umbral, ni "pasa/no pasa", ni "sirve/no sirve". Estado único: `DESCRIPTIVE`.
4. **Dos canales siempre:** el direccional (movimiento con signo en la dirección de la hipótesis natural) y el no direccional (|movimiento|, MFE/MAE, ruptura del nivel). La regla de los "dos canales" aplica también acá.
5. **Controles emparejados:** cada evento se compara contra momentos al azar de la misma sesión y la misma hora, con la misma dirección y la misma geometría. Un número sin control no dice nada.
6. **Sugerencias deterministas.** Las reglas que convierten observaciones en sugerencias están escritas en el código, no se eligen mirando. Cada sugerencia queda en el Brain como `LessonCandidate` PROPOSED/LOW con `scope=SUGGESTED_ANALYSIS`, y **dice en qué partición se tiene que confirmar**.
7. **El Brain hace cumplir la separación:** una campaña que declara `motivated_by` observaciones **no puede** usar la partición donde se hicieron esas observaciones. `record_campaign` lo rechaza.
8. **Dependencias explícitas:** cada observación depende de la versión del detector y de los datos. Si alguno se invalida, la observación queda `STALE_BY_DEPENDENCY` por cascada (propuesta 5).

## Primer lote: absorción L2 en GC 08-26 (pre-holdout, 30 sesiones)

- **Particiones:** `EXPLORATION` = las primeras 15 sesiones cronológicas; `CONFIRMATION_RESERVED` = las 15 siguientes. Se declaran en el Brain antes de calcular.
- **Target-free, en las 30 sesiones:**
  - frecuencia por sesión y hora, y balance de lado;
  - repetición en el mismo nivel (toque n-ésimo);
  - agrupamiento temporal (CV del tiempo entre eventos: Poisson = 1);
  - estado del libro al momento del evento contra la distribución incondicional: spread, profundidad del lado absorbente, desequilibrio de cola, rango de 60 s.
- **Perfil de respuesta, solo en EXPLORATION:**
  - movimiento en dirección "fade" a 10, 30, 60 y 300 s, con cuantiles;
  - |movimiento|, MFE y MAE a 300 s;
  - probabilidad de ruptura del nivel por horizonte;
  - todo contra controles emparejados, con diferencia por sesión, IC bootstrap por sesión y resolución.
- **Qué NO se hace:** no hay reglas de trading, ni costos, ni combinaciones de stop y target. Eso es trabajo de una spec y una prueba posteriores.

## Cómo se usa después

Una sugerencia del atlas se vuelve una spec (`docs/specs/`), pasa por la **revisión ciega** y se confirma en `CONFIRMATION_RESERVED` o en datos futuros. El Brain registra el vínculo `motivated_by` y bloquea usar la partición explorada.

## Resultados del primer lote (2026-09-24)

Artefacto `artifacts/l2_atlas/absorption_GC_08-26.json` (sha256 `b9a804b733bb…`). Ledger del Brain `artifacts/hippocampus/atlas_l2_20260924.jsonl`, anclado en `ANCHORS.json`. Particiones declaradas antes de medir: `P-GC0826-EXP` (27/05–12/06, 15 sesiones) y `P-GC0826-CONF` (14/06–30/06, 15 sesiones, **reservada**).

### Nulo del detector, re-medido con umbral causal

1,33× [1,27; 1,39], 26/29 sesiones (antes 1,41× con umbral de sesión completa, que usaba información futura). El fenómeno existe más allá del azar. `OBS-ABS-GC0826-NULL-CAUSAL`; la cifra vieja quedó `STALE_BY_DEPENDENCY` por cascada.

### Target-free (30 sesiones, 2.323 eventos)

| Qué | Valor | Lectura |
|---|---|---|
| Lado | 44,8 % en el ask | Casi balanceado |
| Agrupamiento temporal | CV entre eventos 1,55 (Poisson = 1) | Vienen en racimos |
| Siguiente evento dentro de 60 s | 16 % | |
| Mismo nivel repetido dentro de 10 min | 9,5 % | El toque n-ésimo es raro |
| Co-ocurrencia con iceberg | 2,2 % contra 0,04 % del control, lift 51 | **Inflada por construcción** (ver salvedades) |
| Spread (ticks) | p50 4 en eventos y 4 incondicional | Sin diferencia |
| Profundidad del lado que absorbe | p50 1,0 contra 1,5 | **La absorción ocurre con el libro más fino, no más grueso** |
| Desequilibrio de cola | p50 0 contra 0 | Sin diferencia |

### Perfil de respuesta (solo `P-GC0826-EXP`: 1.232 eventos, 6.160 controles emparejados)

Cada celda: media del evento / media del control, y entre corchetes el IC 95 % bootstrap por sesión de la diferencia (en negrita si no cruza cero). Son las **12 celdas**, no solo las que "dispararon":

| Horizonte | Fade con signo, ticks | \|mov\|, ticks | P(ruptura del nivel) |
|---|---|---|---|
| 10 s | 0,13 / 0,03 [−0,54; 0,58] | 6,49 / 5,84 **[0,20; 0,98]** | 0,39 / 0,48 [−0,11; 0,01] |
| 30 s | 0,49 / 0,01 [−0,51; 1,08] | 11,07 / 10,41 [−0,45; 1,18] | 0,57 / 0,69 **[−0,14; −0,02]** |
| 60 s | 0,90 / −0,28 **[0,01; 2,66]** | 16,40 / 15,13 [−0,16; 2,69] | 0,66 / 0,79 **[−0,14; −0,04]** |
| 300 s | 1,87 / −1,57 [−2,96; 6,36] | 35,19 / 34,10 [−1,61; 5,32] | 0,83 / 0,91 **[−0,10; −0,03]** |

MFE p50 25 contra 22,5; MAE −21,5 contra −23,5.

**Lectura honesta.** Lo más firme es no direccional: después de una absorción el nivel **se rompe menos** que un nivel cualquiera (30–300 s) y el precio **se mueve más** en los primeros 10 s. La dirección "fade" tiene signo positivo en todos los horizontes, pero su único IC que no cruza cero (60 s) lo hace por 0,015 ticks. Con 12 IC mirados, ~0,6 disparos son esperables por azar.

### Sugerencias (Brain: `LessonCandidate` PROPOSED/LOW, `scope=SUGGESTED_ANALYSIS`)

| Id | Qué propone | Dónde confirmar |
|---|---|---|
| SUG-ABS-BARRIER-30 | El nivel absorbido como barrera: menor ruptura a 30–300 s | `P-GC0826-CONF` |
| SUG-ABS-VOL-10 | Absorción como marcador de volatilidad inmediata (canal no direccional) | `P-GC0826-CONF` |
| SUG-ABS-FADE-60 | Fade a 60 s. **Candidato a ruido**: lo más débil del lote | `P-GC0826-CONF` |
| SUG-ABS-ICE-CONFLUENCE | Absorción + iceberg en el mismo nivel | Antes, rehacer el control (ver salvedad 1) |
| SUG-ABS-MORE-DATA | 300 s no tiene resolución con 15 sesiones | Más sesiones L2 (P-80) |

### Salvedades (en el ledger: `ATLAS-ABS-GC0826-CAVEATS` y su corrección `-CORR1`)

1. **El lift 51 del iceberg está inflado por construcción:** los dos detectores usan volumen agresivo en un mismo precio, y un momento al azar casi nunca lo tiene. Además, el umbral del iceberg todavía es de sesión completa (no causal).
2. **Miradas múltiples:** 12 IC descriptivos se usaron como disparadores. Por eso cada sugerencia se confirma **solo** en la partición reservada, y el Brain rechaza una campaña motivada por estas observaciones que use `P-GC0826-EXP`.
3. **Costo:** la primera versión de la salvedad citaba "~4,5 ticks RT" sin fuente. Lo verificado es que `H-GC-BT2-1` declara 1,5 ticks, pero **este feed** tiene spread cotizado p50 de 4 ticks, 3–5 en RTH (Fase 0 §2, P-76; re-chequeado hoy en 01/06, 10/06 y 24/06). Ningún número del perfil se compara contra costo hasta resolver P-76. Un fade de ~1 tick no alcanza ni medio spread de este feed.
4. **Falta** el rango de 60 s incondicional en el bloque de contexto (solo está en eventos).
5. Todo el perfil es de un instrumento, un contrato y 15 sesiones. Nada se transporta a 6E ni a otros activos.
