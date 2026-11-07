# Pre-registro — H-REG-2, amplitud de la sesión previa

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / régimen corto (`regimen_corto_20261106`)
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: series `docs/research/regimen_corto_20261106/series_diarias_regimen_20261106.json`. Amplitud desde los datasets de pre-holdout `nicolasbuttaro/edgelab-ticks-{nq,es,ym,gc}-preholdout`. No se usa `edgelab-holdout-sellado`.

Este archivo se escribe **antes** de unir la amplitud con el R diario. No promueve estrategias. No abre el holdout `>= 2026-10-01`.

## 1. Qué ya se midió

H-REG-1 (`RESULTADO_HREG1_WALKFORWARD_20261107.md`) no pasó: rotar por la racha de 3 meses no supera a la canasta de calidad estática. REGIMEN_ETAPA0 encontró persistencia de amplitud y no de eficiencia, con la salvedad de que la amplitud cruda arrastra la estacionalidad de la hora. Este test no reabre H-REG-1 y no usa el P&L reciente como estado.

## 2. Hipótesis

H-REG-2: un estado S, observable antes de operar la sesión, cambia el R/op de las familias para las que el mecanismo ya dice en qué amplitud deberían operar.

Justificación, fijada por el mecanismo y no por el P&L publicado:

- `RANGO_PREAPERTURA` y `COMPRESION_NR` son rupturas después de una contracción. Se operan sólo si el rango de la sesión previa cae en el tercil bajo.
- `ABSORCION_CLIMAX` es un clímax después de una extensión. Se opera sólo si ese rango cae en el tercil alto.
- `DOBLE_RETROCESO` no entra. No hay un mapeo de amplitud congelado para esa familia, y elegirlo después de ver el R sería otro test.

## 3. Estado

Para el instrumento I y la sesión d:

- Rango de una sesión = máximo − mínimo del precio de los ticks de ese `trade_date`, en el contrato con más ticks ese día. Si el mismo día aparece en dos vencimientos, no se mezclan los precios.
- Si el parquet no trae `trade_date`, la fecha es `edgelab.kaggle.sessions_cme.trade_date_ymd` (la sesión CME abre a las 17:00 CT). Eso se fija antes de mirar el rango contra el R.
- El estado de d usa las 20 sesiones de I estrictamente anteriores a d. El valor que se clasifica es el rango de la sesión inmediata anterior. Los cortes son los cuantiles 1/3 y 2/3 de esas 20. Un empate con el corte cae en el tercil inferior (0 o 1, nunca el superior).
- Las primeras 20 sesiones de cada instrumento no tienen estado y salen de las dos cuentas, la filtrada y la de siempre operar.
- Sesiones `>= 20261001` no entran, aunque un archivo las traiga.

Esto es el rango de la sesión completa ya cerrada, no la amplitud cruda por hora de REGIMEN_ETAPA0. No se residualiza por día de la semana: eso sería otro pre-registro.

## 4. Población y métrica

Población: reglas de `series_cand` cuya `familia`, en mayúsculas, está en el mapa de la sección 2, y cuyo instrumento tiene serie de rango. `series_p4` queda fuera.

Métrica primaria, una sola: R/op de las operaciones cuyo estado es el tercil del mapa, menos el R/op de todas las operaciones con estado, en el mismo conjunto de reglas. R de un día = `m * n`. Se suman R y n entre reglas y después se divide.

Nulo: 200 permutaciones de las etiquetas de tercil dentro de cada instrumento, semilla `20261107`. Las etiquetas se permutan sobre todas las sesiones con estado, no sólo sobre los días que la regla operó. p = (1 + cantidad de nulos con delta ≥ el observado) / 201.

## 5. Decisión

Pasa sólo si se cumplen las cuatro:

- hay rango para el instrumento de la regla;
- n elegible ≥ 90 y n filtrado ≥ 30;
- el delta de R/op es positivo;
- p ≤ 0,05.

Si falta un dataset, la corrida de ese instrumento no se imputa y la decisión primaria no se declara. Los números por regla son descriptivos y no rescatan un primario que no pasa.

## 6. Qué no mide

No recomputa la celda contra ticks. No elige el tercil que más ganó. No abre octubre.
