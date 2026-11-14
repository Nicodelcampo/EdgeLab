# Exploración — edgelab.research.luximb_amarilla_ds (NO confirma nada)

Generado por `edgelab/research/analizar_tabla.py`. Una celda por debajo del percentil 95 del nulo de la búsqueda no se distingue
del azar; las de fricción > 0.08 R no son elegibles. Lo que se congele se prueba en datos no mirados (`congelar`).

## todos — 2635 eventos, 300 celdas

Nulo de la búsqueda: mejor t por azar mediana 2.27, p95 3.20.

| definición | ejecución | filtro | n | R bruto | R neto | t | bloques + | p | fricción R | ¿sobre el nulo? |
|---|---|---|---|---|---|---|---|---|---|---|
| sin_filtro|base | P_obj_75_stop_ext | vwapD_lejos_hacia | 34 | +0.198 | +0.183 | +4.95 | 5 | 0.000 | 0.015 | sí |
| amarilla|base | P_obj_50_stop_ext | vwapNY_lejos_hacia | 54 | +0.079 | +0.065 | +4.85 | 5 | 0.000 | 0.013 | sí |
| sin_filtro|base | P_obj_50_stop_ext | vwapD_lejos_hacia | 30 | +0.092 | +0.077 | +4.63 | 5 | 0.000 | 0.015 | sí |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_lejos_hacia | 134 | +0.099 | +0.085 | +3.30 | 5 | 0.001 | 0.013 | sí |
| amarilla|base | P_obj_75_stop_ext | vwap_ambos_hacia | 149 | +0.096 | +0.081 | +3.16 | 4 | 0.001 | 0.013 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwap_ambos_hacia | 248 | +0.077 | +0.062 | +2.97 | 5 | 0.001 | 0.014 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapNY_lejos_hacia | 125 | +0.054 | +0.040 | +2.89 | 4 | 0.000 | 0.014 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_lejos_hacia | 59 | +0.115 | +0.102 | +2.77 | 4 | 0.002 | 0.013 | no |
| amarilla|base | P_obj_75_stop_ext | vwapD_hacia | 240 | +0.066 | +0.053 | +2.46 | 5 | 0.006 | 0.012 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_hacia | 231 | +0.065 | +0.051 | +2.28 | 5 | 0.014 | 0.012 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_hacia | 429 | +0.050 | +0.036 | +2.09 | 4 | 0.013 | 0.013 | no |
| amarilla|base | P_obj_50_stop_ext | vwap_ambos_hacia | 140 | +0.045 | +0.030 | +2.07 | 4 | 0.024 | 0.013 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapD_hacia | 371 | +0.043 | +0.029 | +1.53 | 5 | 0.059 | 0.013 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwap_ambos_hacia | 126 | +0.273 | +0.243 | +1.35 | 3 | 0.075 | 0.018 | no |
| amarilla|V4S_S1|v120 | P_obj_75_stop_ext | vwap_ambos_hacia | 45 | +0.360 | +0.325 | +1.35 | 3 | 0.093 | 0.023 | no |
| amarilla|base | P_obj_50_stop_ext | vwapNY_lejos | 534 | +0.020 | +0.011 | +1.33 | 4 | 0.089 | 0.008 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapNY_hacia | 157 | +0.218 | +0.192 | +1.31 | 4 | 0.098 | 0.016 | no |
| amarilla|V4S_S1|v120 | P_obj_50_stop_ext | vwap_ambos_hacia | 45 | +0.311 | +0.275 | +1.27 | 3 | 0.111 | 0.023 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwap_ambos_hacia | 126 | +0.233 | +0.204 | +1.23 | 2 | 0.104 | 0.018 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwapNY_hacia | 157 | +0.182 | +0.156 | +1.17 | 3 | 0.140 | 0.016 | no |
| amarilla|V4S_S1|v120 | P_obj_75_stop_ext | vwapNY_hacia | 54 | +0.260 | +0.228 | +1.12 | 2 | 0.144 | 0.017 | no |
| amarilla|V4S_S1|v120 | P_obj_50_stop_ext | vwapNY_hacia | 54 | +0.235 | +0.204 | +1.11 | 3 | 0.144 | 0.017 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapD_hacia | 149 | +0.195 | +0.168 | +1.09 | 3 | 0.176 | 0.017 | no |
| amarilla|V4W_S1|v30 | P_obj_50_stop_ext | vwapD_hacia | 43 | +0.167 | +0.140 | +1.05 | 4 | 0.150 | 0.017 | no |
| amarilla|V4W_S1|v30 | P_obj_75_stop_ext | vwap_ambos_hacia | 36 | +0.205 | +0.176 | +1.05 | 4 | 0.142 | 0.018 | no |

Real − control (misma ejecución, R neto): amarilla|V4S_S1|v120 vs amarilla|base P_obj_50_stop_ext: +0.074; amarilla|V2A_S1|v120 vs amarilla|base P_obj_75_stop_ext: +0.050; amarilla|V4S_S1|v120 vs amarilla|base P_obj_75_stop_ext: +0.045; amarilla|V4S_S1|v30 vs amarilla|base P_obj_50_stop_ext: +0.037; amarilla|V2A_S1|v120 vs amarilla|base P_obj_50_stop_ext: +0.025

## NQ/DESC — 1619 eventos, 254 celdas

Nulo de la búsqueda: mejor t por azar mediana 2.13, p95 3.13.

| definición | ejecución | filtro | n | R bruto | R neto | t | bloques + | p | fricción R | ¿sobre el nulo? |
|---|---|---|---|---|---|---|---|---|---|---|
| amarilla|base | P_obj_50_stop_ext | vwapNY_lejos_hacia | 32 | +0.074 | +0.058 | +3.44 | 5 | 0.000 | 0.015 | sí |
| amarilla|base | P_obj_75_stop_ext | vwap_ambos_hacia | 94 | +0.115 | +0.098 | +3.20 | 5 | 0.001 | 0.015 | sí |
| amarilla|base | P_obj_75_stop_ext | vwapD_hacia | 140 | +0.087 | +0.072 | +2.77 | 5 | 0.002 | 0.014 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_lejos_hacia | 36 | +0.127 | +0.111 | +2.59 | 5 | 0.003 | 0.015 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_hacia | 142 | +0.085 | +0.069 | +2.46 | 4 | 0.007 | 0.014 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_lejos_hacia | 72 | +0.096 | +0.080 | +2.13 | 5 | 0.014 | 0.015 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwap_ambos_hacia | 151 | +0.073 | +0.056 | +2.03 | 5 | 0.018 | 0.016 | no |
| amarilla|base | P_obj_50_stop_ext | vwapNY_lejos | 331 | +0.025 | +0.015 | +1.63 | 3 | 0.059 | 0.009 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_hacia | 253 | +0.046 | +0.030 | +1.24 | 3 | 0.122 | 0.015 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapNY_hacia | 96 | +0.285 | +0.257 | +1.17 | 4 | 0.136 | 0.016 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwap_ambos_hacia | 76 | +0.349 | +0.317 | +1.15 | 3 | 0.145 | 0.019 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwapNY_hacia | 96 | +0.255 | +0.227 | +1.13 | 2 | 0.143 | 0.016 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapD_hacia | 219 | +0.043 | +0.027 | +1.12 | 4 | 0.133 | 0.015 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwap_ambos_hacia | 76 | +0.313 | +0.282 | +1.11 | 2 | 0.160 | 0.019 | no |
| amarilla|V4S_S1|v120 | P_obj_50_stop_ext | vwapNY_hacia | 32 | +0.225 | +0.194 | +1.06 | 3 | 0.165 | 0.017 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapNY_lejos_hacia | 66 | +0.040 | +0.023 | +1.00 | 3 | 0.175 | 0.015 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapD_hacia | 88 | +0.262 | +0.233 | +0.97 | 3 | 0.217 | 0.018 | no |
| amarilla|V4S_S1|v120 | P_obj_50_stop_ext | vwapD_hacia | 32 | +0.204 | +0.172 | +0.92 | 2 | 0.206 | 0.020 | no |
| amarilla|base | P_obj_50_stop_ext | vwap_ambos_hacia | 91 | +0.035 | +0.018 | +0.89 | 4 | 0.192 | 0.015 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwapD_hacia | 88 | +0.223 | +0.194 | +0.89 | 2 | 0.270 | 0.018 | no |
| amarilla|V4S_S1|v120 | P_obj_75_stop_ext | vwapNY_hacia | 32 | +0.193 | +0.161 | +0.83 | 3 | 0.220 | 0.017 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwapNY_lejos_hacia | 30 | +0.545 | +0.502 | +0.80 | 3 | 0.304 | 0.023 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapNY_lejos_hacia | 30 | +0.562 | +0.519 | +0.76 | 2 | 0.330 | 0.023 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapNY_lejos | 95 | +0.164 | +0.144 | +0.65 | 2 | 0.378 | 0.010 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapNY_lejos | 539 | +0.016 | +0.005 | +0.63 | 4 | 0.264 | 0.010 | no |

Real − control (misma ejecución, R neto): amarilla|V2A_S1|v120 vs amarilla|base P_obj_75_stop_ext: +0.057; amarilla|V2A_S1|v120 vs amarilla|base P_obj_50_stop_ext: +0.041; amarilla|V4S_S1|v120 vs amarilla|base P_obj_50_stop_ext: +0.039; amarilla|V4S_S1|v30 vs amarilla|base P_obj_50_stop_ext: +0.003; sin_filtro|V2A_S1|v120 vs sin_filtro|base P_obj_50_stop_ext: -0.008

## NQ/REP — 1016 eventos, 196 celdas

Nulo de la búsqueda: mejor t por azar mediana 2.07, p95 2.87.

| definición | ejecución | filtro | n | R bruto | R neto | t | bloques + | p | fricción R | ¿sobre el nulo? |
|---|---|---|---|---|---|---|---|---|---|---|
| sin_filtro|base | P_obj_50_stop_ext | vwapNY_lejos_hacia | 59 | +0.070 | +0.058 | +4.44 | 5 | 0.000 | 0.011 | sí |
| sin_filtro|base | P_obj_50_stop_ext | vwap_ambos_hacia | 88 | +0.071 | +0.059 | +4.43 | 4 | 0.000 | 0.011 | sí |
| amarilla|base | P_obj_50_stop_ext | vwap_ambos_hacia | 49 | +0.064 | +0.053 | +2.81 | 4 | 0.001 | 0.010 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_lejos_hacia | 62 | +0.102 | +0.090 | +2.63 | 5 | 0.004 | 0.011 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwap_ambos_hacia | 97 | +0.082 | +0.071 | +2.28 | 3 | 0.010 | 0.011 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapNY_hacia | 165 | +0.041 | +0.031 | +2.13 | 4 | 0.019 | 0.010 | no |
| sin_filtro|base | P_obj_75_stop_ext | todos | 702 | +0.031 | +0.022 | +1.87 | 4 | 0.036 | 0.008 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapNY_hacia | 176 | +0.057 | +0.046 | +1.87 | 4 | 0.035 | 0.010 | no |
| sin_filtro|base | P_obj_50_stop_ext | todos | 631 | +0.024 | +0.015 | +1.73 | 4 | 0.034 | 0.008 | no |
| amarilla|base | P_obj_75_stop_ext | vwap_ambos_contra | 283 | +0.035 | +0.027 | +1.64 | 3 | 0.051 | 0.007 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapD_hacia | 133 | +0.040 | +0.029 | +1.58 | 3 | 0.068 | 0.011 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwapD_contra | 550 | +0.027 | +0.019 | +1.58 | 4 | 0.055 | 0.008 | no |
| sin_filtro|base | P_obj_75_stop_ext | vwap_ambos_contra | 471 | +0.028 | +0.020 | +1.48 | 4 | 0.059 | 0.008 | no |
| amarilla|V2A_S1|v120 | P_obj_75_stop_ext | vwapNY_lejos | 45 | +0.223 | +0.208 | +1.46 | 4 | 0.078 | 0.010 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwap_ambos_contra | 421 | +0.022 | +0.013 | +1.43 | 3 | 0.073 | 0.008 | no |
| amarilla|base | P_obj_75_stop_ext | todos | 417 | +0.031 | +0.023 | +1.41 | 3 | 0.078 | 0.008 | no |
| amarilla|base | P_obj_50_stop_ext | vwap_ambos_contra | 259 | +0.024 | +0.016 | +1.37 | 3 | 0.072 | 0.007 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_contra | 328 | +0.030 | +0.022 | +1.35 | 3 | 0.090 | 0.007 | no |
| amarilla|base | P_obj_75_stop_ext | vwapD_contra | 317 | +0.029 | +0.021 | +1.30 | 3 | 0.096 | 0.007 | no |
| sin_filtro|base | P_obj_50_stop_ext | vwapD_contra | 498 | +0.020 | +0.011 | +1.26 | 4 | 0.106 | 0.008 | no |
| sin_filtro|V4W_S1|v120 | P_obj_75_stop_ext | vwapD_hacia | 50 | +0.308 | +0.278 | +1.19 | 3 | 0.127 | 0.018 | no |
| amarilla|base | P_obj_75_stop_ext | vwap_ambos_hacia | 55 | +0.064 | +0.053 | +1.15 | 4 | 0.143 | 0.011 | no |
| sin_filtro|V4W_S1|v120 | P_obj_50_stop_ext | vwapD_hacia | 50 | +0.265 | +0.235 | +1.14 | 3 | 0.135 | 0.018 | no |
| amarilla|V2A_S1|v120 | P_obj_50_stop_ext | vwapNY_lejos | 45 | +0.162 | +0.147 | +1.13 | 3 | 0.145 | 0.010 | no |
| amarilla|base | P_obj_75_stop_ext | vwapNY_lejos | 232 | +0.028 | +0.020 | +1.12 | 3 | 0.134 | 0.007 | no |

Real − control (misma ejecución, R neto): sin_filtro|V4S_S1|v30 vs sin_filtro|base P_obj_75_stop_ext: +0.177; amarilla|V4S_S1|v120 vs amarilla|base P_obj_75_stop_ext: +0.164; amarilla|V4S_S1|v120 vs amarilla|base P_obj_50_stop_ext: +0.133; sin_filtro|V4S_S1|v30 vs sin_filtro|base P_obj_50_stop_ext: +0.125; sin_filtro|V4S_S1|v120 vs sin_filtro|base P_obj_75_stop_ext: +0.100

