# Pre-registro: atlas de ideas transferibles entre estrategias, medidas en R (2026-11-02)

Estado: VIGENTE, registrado antes de correr. Pedido de Nico: «seguí trabajando en determinar los mejores tipos y prácticas de medición… no
necesariamente su resultado tuvo que haber sido positivo, pero resultados positivos sugieren buenas ideas o lógicas que se pueden aplicar
en otras estrategias». Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF3: exploratorio entre familias, sobre datos de desarrollo ya usados, sin holdout.

## Pregunta
¿Hay **decisiones de diseño** que mejoren el R de forma consistente en familias distintas? Por ejemplo:
- cómo se entra: al cierre, en la apertura siguiente, con retroceso o en un nivel de volumen;
- a qué objetivo se apunta: borde cercano, medio o lejano;
- dónde va el stop;
- si conviene el break-even.

Una idea que mejora R en muchas familias distintas es candidata a aplicarse por defecto en estrategias nuevas.

## Datos
Etapa `MARGINALES` (`etapas.py`), con **`estadistico: "R"`**, para cada campaña del relanzamiento en R
(`relanzamiento_R_20261102/CAMPANAS.json`):
- **Descubrimiento:** su ventana DESC.
- **Confirmación:** su ventana de réplica (OOS o la de pistas). Nunca el holdout.

Cada corrida devuelve, por nivel de cada perilla y por componente de la ejecución (entrada, objetivo, stop, BE), las operaciones, la suma y
la suma de cuadrados de R y la cantidad de sesiones, **sobre todas las operaciones de la grilla**, no sobre una celda elegida.

## Análisis (`tools/atlas_ideas_r.py`)
1. **Efecto de un nivel dentro de una familia:** media de R del nivel menos media de R de toda la familia. Error estándar = desvío /
   √(sesiones del nivel), conservador por la dependencia intradía.
2. **Unidad de comparación:** la etiqueta del componente (por ejemplo `objetivo=T3`, `entrada=E1A`, `stop=S3`, `be=1`), comparable entre
   familias. Las perillas propias de una familia, como los cortes de A/H, se informan dentro de la familia y no entran al meta-análisis.
3. **Meta-análisis de efectos aleatorios** (DerSimonian–Laird) por etiqueta, con las familias como unidades. Se informan efecto, IC90,
   I², fracción de familias con el mismo signo y cantidad de familias.
4. **Descubrimiento (DESC):** BH q 0,10 sobre todas las etiquetas con al menos 4 familias.
5. **Confirmación (réplica), sólo para las descubiertas:** mismo signo y p < 0,05 a una cola en el meta-análisis de la réplica.
6. **Además, por sensor (CFD contra futuro) y por instrumento,** a nivel familia: media de R de la familia.

## Lectura fijada
- **Idea confirmada (descubierta y confirmada):** se recomienda como valor por defecto o como perilla obligatoria en las campañas nuevas.
  Nunca se aplica como filtro a reglas ya elegidas, porque eso sería selección posterior.
- **Idea sólo descubierta:** pista, para probar en campañas nuevas como perilla.
- **Una idea negativa confirmada** (empeora R en muchas familias) es tan útil como una positiva: se deja de explorar.

## Cómo podría refutarse
- Que ninguna etiqueta pase la confirmación.
- Que los efectos sean heterogéneos (I² alto, signos mezclados): las ideas no se transfieren y cada familia es propia.

## Riesgos
- Las familias comparten instrumento y período: no son independientes. La confirmación en réplica es la defensa principal.
- Las grillas tienen tamaños distintos; con efectos aleatorios, una grilla grande no domina.

## Registro
Etiquetas × 2 ventanas en `TRIAL_REGISTRY_GLOBAL.jsonl` (`atlas_ideas_r/20261102`). Se registra una cota de 200 pruebas antes de correr.
