# Recomendaciones — HFT-CLUSTERS info

Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `HFTC_info.json`; reglas fijadas antes de ver resultados).

## Qué hacer después (ordenado por prioridad)

Nada con prioridad: todo descartado o sin datos.

## Detalle

| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |
|---|---|---|---|---|---|---|---|---|
| rebote | DESCARTAR | -0.021 | [-0.043, +0.001] | +0.033 | -0.000 | ES -0.004, GC -0.020, NQ -0.027, YM -0.007 | — | 0.0 |
| iman | DESCARTAR | -0.014 | [-0.033, +0.004] | +0.028 | +0.025 | ES -0.024, GC -0.013, NQ -0.027, YM +0.091 | — | 0.0 |

Categorías: **CONFIRMAR**: Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.; **INDAGAR**: Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.; **ESTRUCTURA_DE_PRECIO**: El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.; **INCONSISTENTE**: Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.; **EN_CONTRA**: El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.; **SIN_MUESTRA**: No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.; **DESCARTAR**: Sin efecto con potencia: no repetir con esta definición.; **NO_CONCLUYENTE**: Ni efecto relevante ni potencia para descartarlo: dejar en espera.
