# Universo de corridas guiado por umbrales

ρ requerido = correlación mínima de una señal con el retorno siguiente para que la mejor cuenta del catálogo deje EV ≥ 0 (cuota incluida), eligiendo tamaño (minis ≤ 4, micros ≤ 40). Plausible si ≲ 0.12. Umbral efectivo = máx(EV ≥ 0 del ciclo, esperanza neta ≥ 0): varias cuentas muestran EV ≥ 0 sin ventaja (valor de opción con cuotas y retiros SIN verificar), y EdgeLab no persigue eso. Muestra: sesiones 2025-07 → 2026-09; costos y cuentas supuestos (THRESHOLDS.md); 2 operaciones por día.

## ES: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 08:30 | 60 min | 97 | 1 MES | 121 | 0.025 | 0.031 | Topstep|Trading_Combine_50K | ok |
| 09:00 | 60 min | 88 | 1 ES | 1095 | 0.027 | 0.034 | Topstep|Trading_Combine_50K | ok |
| 09:30 | 60 min | 79 | 1 ES | 993 | 0.030 | 0.038 | Tradeify|Select_Daily_50K | ok |
| 08:00 | 60 min | 79 | 1 ES | 990 | 0.030 | 0.038 | Tradeify|Select_Daily_50K | ok |
| 08:30 | 30 min | 75 | 1 MES | 94 | 0.032 | 0.040 | Topstep|Trading_Combine_50K | ok |
| 14:00 | 60 min | 66 | 1 MES | 82 | 0.036 | 0.046 | Topstep|Trading_Combine_50K | ok |
| 10:00 | 60 min | 66 | 1 MES | 82 | 0.037 | 0.046 | Topstep|Trading_Combine_50K | ok |
| 09:00 | 30 min | 64 | 1 ES | 805 | 0.037 | 0.047 | Tradeify|Select_Daily_50K | ok |

## NQ: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 08:30 | 60 min | 607 | 1 NQ | 3033 | 0.011 | 0.013 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 08:00 | 60 min | 541 | 1 NQ | 2705 | 0.012 | 0.015 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 08:30 | 30 min | 507 | 1 MNQ | 253 | 0.013 | 0.016 | Tradeify|Select_Daily_50K | ok |
| 09:00 | 60 min | 484 | 1 NQ | 2418 | 0.013 | 0.017 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 09:30 | 60 min | 457 | 1 NQ | 2283 | 0.014 | 0.018 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 10:00 | 60 min | 402 | 1 NQ | 2008 | 0.016 | 0.020 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 09:00 | 30 min | 362 | 1 NQ | 1812 | 0.018 | 0.022 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 08:30 | 15 min | 355 | 1 NQ | 1774 | 0.018 | 0.023 | Topstep|Trading_Combine_50K | σ sobre la grilla |

## YM: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 08:30 | 60 min | 192 | 1 YM | 961 | 0.025 | 0.031 | Topstep|Trading_Combine_50K | ok |
| 09:00 | 60 min | 157 | 2 MYM | 157 | 0.031 | 0.038 | Topstep|Trading_Combine_50K | ok |
| 08:00 | 60 min | 154 | 2 MYM | 154 | 0.031 | 0.039 | Topstep|Trading_Combine_50K | ok |
| 09:30 | 60 min | 150 | 1 YM | 748 | 0.032 | 0.040 | Tradeify|Select_Daily_50K | ok |
| 08:30 | 30 min | 148 | 1 YM | 738 | 0.033 | 0.041 | Tradeify|Select_Daily_50K | ok |
| 10:00 | 60 min | 129 | 1 YM | 646 | 0.037 | 0.046 | Tradeify|Select_Daily_50K | ok |
| 08:30 | 15 min | 128 | 1 YM | 640 | 0.038 | 0.047 | Tradeify|Select_Daily_50K | ok |
| 10:30 | 60 min | 120 | 1 YM | 598 | 0.040 | 0.050 | Tradeify|Select_Daily_50K | ok |

## GC: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 08:30 | 60 min | 312 | 1 GC | 3120 | 0.008 | 0.010 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 09:00 | 60 min | 272 | 1 GC | 2719 | 0.009 | 0.011 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 09:00 | 30 min | 227 | 1 GC | 2269 | 0.011 | 0.014 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 07:00 | 60 min | 215 | 1 GC | 2155 | 0.012 | 0.014 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 08:00 | 60 min | 214 | 1 GC | 2144 | 0.012 | 0.014 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 19:30 | 60 min | 212 | 1 GC | 2117 | 0.012 | 0.015 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 09:30 | 60 min | 203 | 1 GC | 2033 | 0.012 | 0.015 | Topstep|Trading_Combine_50K | σ sobre la grilla |
| 07:30 | 60 min | 193 | 1 GC | 1926 | 0.013 | 0.016 | Topstep|Trading_Combine_50K | σ sobre la grilla |

## 6E: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 07:30 | 60 min | 33 | 1 6E | 209 | 0.083 | 0.103 | Topstep|Trading_Combine_50K | ok |
| 07:00 | 60 min | 33 | 1 6E | 206 | 0.084 | 0.105 | Topstep|Trading_Combine_50K | ok |
| 07:30 | 30 min | 29 | 1 6E | 182 | 0.095 | 0.119 | Topstep|Trading_Combine_50K | ok |
| 09:00 | 60 min | 29 | 1 6E | 178 | 0.097 | 0.121 | Topstep|Trading_Combine_50K | ok |
| 08:30 | 60 min | 28 | 1 6E | 175 | 0.099 | 0.123 | Topstep|Trading_Combine_50K | ok |
| 07:30 | 15 min | 26 | 1 6E | 161 | 0.107 | 0.134 | Topstep|Trading_Combine_50K | ok |
| 09:30 | 60 min | 24 | 1 6E | 148 | 0.117 | 0.146 | Topstep|Trading_Combine_50K | ok |
| 08:00 | 60 min | 23 | 1 6E | 143 | 0.121 | 0.152 | Topstep|Trading_Combine_50K | ok |

## 6J: 8 celdas con menor ρ requerido

| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |
|---|---:|---:|---|---:|---:|---:|---|---|
| 08:30 | 60 min | 24 | 1 6J | 151 | 0.115 | 0.143 | Topstep|Trading_Combine_50K | ok |
| 08:00 | 60 min | 21 | 1 6J | 131 | 0.132 | 0.165 | Topstep|Trading_Combine_50K | ok |

## Resumen por instrumento

| instrumento | ρ requerido mínimo | mediana de las mejores 20 | celdas con ρ ≤ plausible |
|---|---:|---:|---:|
| ES | 0.031 | 0.051 | 81 de 114 |
| NQ | 0.013 | 0.024 | 132 de 132 |
| YM | 0.031 | 0.057 | 66 de 98 |
| GC | 0.010 | 0.017 | 132 de 132 |
| 6E | 0.103 | 0.153 | 3 de 18 |
| 6J | 0.143 | 0.154 | 0 de 2 |
