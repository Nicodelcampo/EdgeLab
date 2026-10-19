# Viabilidad de las reglas según el mandato

Resultados: `PNL1_RESULTADOS.json`. Challenge de referencia: `mandate.json` (simulación por remuestreo de días, tamaño en múltiplos de 1 contrato que mejor aporta sobre el control de dirección aleatoria). Costos: GC 24,80 / ES 30,00 por contrato y operación.

| regla | muestra (rol) | n | neto medio USD | bruto medio USD | aciertos | trim. positivos | 5 mejores días | tamaño | pase | pase control | nivel | falla |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| GC_ROD_LH_ALL | GC (discovery) | 274 | 135.9 | 160.7 | 0.51 | 0.80 | 0.58 | 0.1 | 0.989 | 0.108 | **C** | no_depende_de_5_dias |
| GC_ROD_LH_ALL | GC_spot_old (oos) | 931 | -12.4 | 12.4 | 0.38 | 0.42 | — | 2.0 | 0.135 | 0.077 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| GC_ROD_LH_ALL | GC_spot_new (descriptive) | 390 | 61.6 | 86.4 | 0.43 | 0.80 | 0.69 | 0.1 | 0.745 | 0.010 | **C** | no_depende_de_5_dias |
| GC_ROD_LH_BIG | GC (discovery) | 90 | 411.0 | 435.8 | 0.54 | 0.75 | 0.57 | 0.5 | 0.961 | 0.263 | **C** | frecuencia, no_depende_de_5_dias |
| GC_ROD_LH_BIG | GC_spot_old (oos) | 313 | -26.5 | -1.7 | 0.46 | 0.25 | — | 1.0 | 0.037 | 0.027 | **C** | neto_positivo, resiste_costos_x1.5, frecuencia, trimestres_positivos |
| GC_ROD_LH_BIG | GC_spot_new (descriptive) | 146 | 148.8 | 173.6 | 0.52 | 0.60 | 0.76 | 0.1 | 0.990 | 0.210 | **C** | trimestres_positivos, no_depende_de_5_dias |
| GC_PREV15_1330_MOM | GC_spot_old (discovery) | 932 | -30.2 | -5.4 | 0.29 | 0.00 | — | 0.1 | 0.000 | 0.000 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| GC_PREV15_1330_MOM | GC (descriptive) | 276 | -5.1 | 19.7 | 0.41 | 0.60 | — | 0.2 | 0.233 | 0.083 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| GC_PREV15_1330_MOM | GC_spot_new (descriptive) | 391 | -17.1 | 7.7 | 0.32 | 0.60 | — | 0.2 | 0.131 | 0.062 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| ES_PREV60_0730_REV | ES_spot (discovery) | 2318 | -19.8 | 10.2 | 0.38 | 0.20 | — | 0.5 | 0.138 | 0.102 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| ES_PREV60_0730_REV | ES (descriptive) | 243 | -39.4 | -9.4 | 0.45 | 0.00 | — | 0.1 | 0.000 | 0.079 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| ES_PREV30_1230_MOM | ES_spot (discovery) | 2318 | -21.0 | 9.0 | 0.35 | 0.20 | — | 2.0 | 0.132 | 0.102 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |
| ES_PREV30_1230_MOM | ES (descriptive) | 243 | -80.7 | -50.7 | 0.38 | 0.00 | — | 0.1 | 0.000 | 0.000 | **C** | neto_positivo, resiste_costos_x1.5, trimestres_positivos, no_depende_de_5_dias |

## Mejor cuenta del catálogo (solo reglas con ventaja bruta positiva; EV y aporte del ciclo completo, cuotas sin verificar)

- **GC_ROD_LH_ALL / GC**: Apex|EOD_50K EV 548 (aporte 822, pase 0.42); Topstep|Combine_NoActivation_50K_Standard EV 697 (aporte 681, pase 0.41)
- **GC_ROD_LH_ALL / GC_spot_old**: Topstep|Combine_NoActivation_50K_Standard EV -44 (aporte 46, pase 0.08); Tradeify|Select_Flex_50K EV -118 (aporte 43, pase 0.08)
- **GC_ROD_LH_ALL / GC_spot_new**: Apex|EOD_50K EV 196 (aporte 438, pase 0.37); Topstep|Combine_NoActivation_50K_Standard EV 374 (aporte 310, pase 0.38)
- **GC_ROD_LH_BIG / GC**: Tradeify|Select_Flex_50K EV 8347 (aporte 8267, pase 0.68); Topstep|Combine_NoActivation_50K_Standard EV 7529 (aporte 7402, pase 0.68)
- **GC_ROD_LH_BIG / GC_spot_new**: Apex|EOD_50K EV 894 (aporte 980, pase 0.45); Topstep|Combine_NoActivation_50K_Standard EV 989 (aporte 860, pase 0.46)
- **GC_PREV15_1330_MOM / GC**: MyFundedFutures|Rapid_50K EV 5 (aporte 56, pase 0.27); Tradeify|Select_Daily_50K EV 48 (aporte 56, pase 0.27)
- **GC_PREV15_1330_MOM / GC_spot_new**: Topstep|Combine_NoActivation_50K_Standard EV 112 (aporte 25, pase 0.25); Apex|EOD_50K EV -220 (aporte 20, pase 0.25)
- **ES_PREV60_0730_REV / ES_spot**: Apex|EOD_50K EV -285 (aporte 27, pase 0.14); Topstep|Combine_NoActivation_50K_Standard EV 25 (aporte 24, pase 0.19)
- **ES_PREV30_1230_MOM / ES_spot**: Topstep|Combine_NoActivation_50K_Standard EV -19 (aporte 34, pase 0.14); Tradeify|Select_Flex_50K EV -91 (aporte 30, pase 0.13)

Nivel: A = válida y útil; B = válida con forma operable pero falla algún criterio; C = información / no confirmada; D = artefacto. Solo la muestra `oos` es confirmatoria.
