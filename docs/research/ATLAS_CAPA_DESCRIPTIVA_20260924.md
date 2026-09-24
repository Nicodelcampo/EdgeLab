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
