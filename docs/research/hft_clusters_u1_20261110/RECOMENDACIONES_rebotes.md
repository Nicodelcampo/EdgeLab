# Recomendaciones — HFT-CLUSTERS rebotes

Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `HFTC_rebotes.json`; reglas fijadas antes de ver resultados).

## Qué hacer después (ordenado por prioridad)

1. D6_PENETRACION_FALLIDA (EN_CONTRA, prioridad 1.78): Diferencia -0.104 con IC90 [-0.180, -0.027], opuesta a lo esperado. La hipótesis contraria se pre-registra aparte y se prueba en datos no usados; ésta queda NO_REPETIR.
2. D0_BASE (EN_CONTRA, prioridad 1.55): Diferencia -0.076 con IC90 [-0.142, -0.013], opuesta a lo esperado. La hipótesis contraria se pre-registra aparte y se prueba en datos no usados; ésta queda NO_REPETIR.
3. D4_MEMORIA (SIN_MUESTRA, prioridad 0.92): Hoy 97 eventos en el estrato más chico; para MDE 0.1 harían falta ≈ 7.9× más. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
4. D5_DERIVA (SIN_MUESTRA, prioridad 0.74): Hoy 108 eventos en el estrato más chico; para MDE 0.1 harían falta ≈ 7.7× más. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
5. D1_FRESCO_LEJANO (NO_CONCLUYENTE, prioridad 0.42): Sin acción salvo que otro resultado lo vuelva relevante.
6. D3_RECHAZADO_AL_NACER (SIN_MUESTRA, prioridad 0.27): Hoy 35 eventos en el estrato más chico; para MDE 0.1 harían falta ≈ 16.1× más. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
7. D2_ACEPTADO_Y_ABANDONADO (NO_CONCLUYENTE, prioridad 0.1): Sin acción salvo que otro resultado lo vuelva relevante.

## Detalle

| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |
|---|---|---|---|---|---|---|---|---|
| D0_BASE | EN_CONTRA | -0.076 | [-0.142, -0.013] | +0.098 | -0.013 | ES +0.046, NQ -0.088 | — | 1.55 |
| D1_FRESCO_LEJANO | NO_CONCLUYENTE | -0.078 | [-0.171, +0.012] | +0.139 | +0.018 | ES -0.373, NQ -0.065 | — | 0.42 |
| D2_ACEPTADO_Y_ABANDONADO | NO_CONCLUYENTE | -0.028 | [-0.161, +0.106] | +0.204 | +0.039 | ES -0.072, NQ -0.020 | — | 0.1 |
| D3_RECHAZADO_AL_NACER | SIN_MUESTRA | -0.086 | [-0.346, +0.184] | +0.401 | +0.028 | NQ -0.093 | — | 0.27 |
| D4_MEMORIA | SIN_MUESTRA | +0.139 | [-0.050, +0.322] | +0.282 | +0.088 | ES -0.667, NQ +0.174 | — | 0.92 |
| D5_DERIVA | SIN_MUESTRA | -0.166 | [-0.349, +0.015] | +0.278 | -0.036 | ES -0.008, NQ -0.260 | — | 0.74 |
| D6_PENETRACION_FALLIDA | EN_CONTRA | -0.104 | [-0.180, -0.027] | +0.116 | -0.042 | ES +0.515, NQ -0.122 | — | 1.78 |

Categorías: **CONFIRMAR**: Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.; **INDAGAR**: Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.; **ESTRUCTURA_DE_PRECIO**: El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.; **INCONSISTENTE**: Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.; **EN_CONTRA**: El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.; **SIN_MUESTRA**: No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.; **DESCARTAR**: Sin efecto con potencia: no repetir con esta definición.; **NO_CONCLUYENTE**: Ni efecto relevante ni potencia para descartarlo: dejar en espera.
