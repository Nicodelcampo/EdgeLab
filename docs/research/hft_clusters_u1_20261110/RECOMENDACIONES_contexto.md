# Recomendaciones — HFT-CLUSTERS contexto

Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `HFTC_contexto.json`; reglas fijadas antes de ver resultados).

## Qué hacer después (ordenado por prioridad)

1. obstaculo (NO_CONCLUYENTE, prioridad 0.38): Sin acción salvo que otro resultado lo vuelva relevante.
2. huella (NO_CONCLUYENTE, prioridad 0.31): Sin acción salvo que otro resultado lo vuelva relevante.
3. mas_nuevo (NO_CONCLUYENTE, prioridad 0.19): Sin acción salvo que otro resultado lo vuelva relevante.
4. respaldo (SIN_MUESTRA, prioridad 0.0): Hoy 0 eventos en el estrato más chico. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
5. densidad (SIN_MUESTRA, prioridad 0.0): Hoy 33 eventos en el estrato más chico. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
6. confluencia (SIN_MUESTRA, prioridad 0.0): Hoy 0 eventos en el estrato más chico. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.

## Detalle

| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |
|---|---|---|---|---|---|---|---|---|
| respaldo | SIN_MUESTRA | — | [—, —] | — | — | — | — | 0.0 |
| obstaculo | NO_CONCLUYENTE | +0.043 | [-0.027, +0.115] | +0.108 | +0.019 | ES +0.417, NQ +0.028 | +0.204 | 0.38 |
| densidad | SIN_MUESTRA | — | [—, —] | — | — | — | — | 0.0 |
| confluencia | SIN_MUESTRA | — | [—, —] | — | — | — | — | 0.0 |
| mas_nuevo | NO_CONCLUYENTE | -0.039 | [-0.140, +0.064] | +0.155 | -0.006 | ES -0.150, NQ -0.033 | +0.103 | 0.19 |
| huella | NO_CONCLUYENTE | -0.057 | [-0.150, +0.034] | +0.139 | -0.020 | ES -0.434, NQ -0.045 | +0.084 | 0.31 |

Categorías: **CONFIRMAR**: Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.; **INDAGAR**: Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.; **ESTRUCTURA_DE_PRECIO**: El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.; **INCONSISTENTE**: Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.; **EN_CONTRA**: El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.; **SIN_MUESTRA**: No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.; **DESCARTAR**: Sin efecto con potencia: no repetir con esta definición.; **NO_CONCLUYENTE**: Ni efecto relevante ni potencia para descartarlo: dejar en espera.
