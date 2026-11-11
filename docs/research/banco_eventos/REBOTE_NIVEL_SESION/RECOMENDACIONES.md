# Recomendaciones — banco de eventos: REBOTE_NIVEL_SESION

Estado: RESULTADO (generado por `edgelab/research/recomendador.py` desde `docs/research/banco_eventos/REBOTE_NIVEL_SESION/RESULTADO.json`; reglas fijadas antes de ver resultados).

## Qué hacer después (ordenado por prioridad)

1. previa: dist_zona_3600=2 (EN_CONTRA, prioridad 1.46): Diferencia -0.023 con IC90 [-0.044, -0.002], opuesta a lo esperado. La hipótesis contraria se pre-registra aparte y se prueba en datos no usados; ésta queda NO_REPETIR.
2. previa: dist_zona_1800=2 (EN_CONTRA, prioridad 1.41): Diferencia -0.017 con IC90 [-0.032, -0.001], opuesta a lo esperado. La hipótesis contraria se pre-registra aparte y se prueba en datos no usados; ésta queda NO_REPETIR.

## Detalle

| Ítem | Categoría | Diferencia | IC90 | MDE | Media del grupo | Por activo | Control | Prioridad |
|---|---|---|---|---|---|---|---|---|
| afuera_s=0 ∧ minuto_et=0 | DESCARTAR | -0.001 | [-0.048, +0.046] | +0.071 | -0.001 | — | — | 0.0 |
| ema21_pend=0 ∧ dist_zona_3600=2 | DESCARTAR | -0.032 | [-0.093, +0.028] | +0.092 | -0.032 | — | — | 0.0 |
| salida_s=2 ∧ salida_eficiencia=2 | DESCARTAR | +0.026 | [-0.032, +0.085] | +0.089 | +0.026 | — | — | 0.0 |
| modelo aditivo: tercil alto − tercil bajo | DESCARTAR | -0.000 | [-0.033, +0.032] | +0.049 | -0.005 | — | — | 0.0 |
| previa: dist_zona_1800=2 | EN_CONTRA | -0.017 | [-0.032, -0.001] | +0.024 | -0.017 | — | — | 1.41 |
| previa: dist_zona_3600=2 | EN_CONTRA | -0.023 | [-0.044, -0.002] | +0.032 | -0.023 | — | — | 1.46 |
| previa: dist_cluster=2 | DESCARTAR | -0.005 | [-0.015, +0.005] | +0.015 | -0.005 | — | — | 0.0 |

Categorías: **CONFIRMAR**: Nominada por BH y consistente: va a la réplica congelada que el pre-registro prevé.; **INDAGAR**: Efecto de tamaño relevante sin confirmar: conviene indagarlo con el análisis sugerido antes de cualquier P&L.; **ESTRUCTURA_DE_PRECIO**: El control muestra el mismo efecto: no es el cluster sino lo que pasa alrededor; medir esa variable de precio directamente.; **INCONSISTENTE**: Signo distinto entre activos: indagar por activo (microestructura o umbrales no comparables) antes de combinar.; **EN_CONTRA**: El efecto va en la dirección opuesta a la hipótesis y el IC90 lo separa de 0: la hipótesis contraria puede valer; se pre-registra aparte en datos no usados.; **SIN_MUESTRA**: No hay datos suficientes para decir nada: sumar muestra sólo si la prioridad lo justifica.; **DESCARTAR**: Sin efecto con potencia: no repetir con esta definición.; **NO_CONCLUYENTE**: Ni efecto relevante ni potencia para descartarlo: dejar en espera.
