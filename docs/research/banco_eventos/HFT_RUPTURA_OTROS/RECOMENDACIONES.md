# Recomendaciones — banco de eventos: HFT_RUPTURA_OTROS

Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `docs/research/banco_eventos/HFT_RUPTURA_OTROS/RESULTADO.json`; reglas fijadas antes de ver resultados).

## Qué hacer después (ordenado por prioridad)

1. modelo aditivo: tercil alto − tercil bajo (SIN_MUESTRA, prioridad 0.46): Hoy 83 eventos en el estrato más chico; para MDE 0.1 harían falta ≈ 10.4× más. Opciones: la réplica abr–sep, otro activo con la misma regla, o una definición menos restrictiva declarada antes.
2. previa: picos_sin_tomar=1 (NO_CONCLUYENTE, prioridad 0.35): Sin acción salvo que otro resultado lo vuelva relevante.
3. previa: picos_dentro=1 (NO_CONCLUYENTE, prioridad 0.12): Sin acción salvo que otro resultado lo vuelva relevante.
4. previa: tendencia_alineada=0 (NO_CONCLUYENTE, prioridad 0.05): Sin acción salvo que otro resultado lo vuelva relevante.

## Detalle

| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |
|---|---|---|---|---|---|---|---|---|
| modelo aditivo: tercil alto − tercil bajo | SIN_MUESTRA | -0.120 | [-0.334, +0.093] | +0.323 | +0.048 | — | — | 0.46 |
| previa: tendencia_alineada=0 | NO_CONCLUYENTE | +0.011 | [-0.098, +0.121] | +0.166 | +0.011 | — | +0.154 | 0.05 |
| previa: picos_dentro=1 | NO_CONCLUYENTE | +0.033 | [-0.104, +0.170] | +0.208 | +0.033 | — | +0.128 | 0.12 |
| previa: picos_sin_tomar=1 | NO_CONCLUYENTE | -0.087 | [-0.210, +0.037] | +0.187 | -0.087 | — | -0.073 | 0.35 |

Categorías: **CONFIRMAR**: Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.; **INDAGAR**: Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.; **ESTRUCTURA_DE_PRECIO**: El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.; **INCONSISTENTE**: Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.; **EN_CONTRA**: El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.; **SIN_MUESTRA**: No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.; **DESCARTAR**: Sin efecto con potencia: no repetir con esta definición.; **NO_CONCLUYENTE**: Ni efecto relevante ni potencia para descartarlo: dejar en espera.
