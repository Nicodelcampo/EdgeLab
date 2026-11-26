# EXP-3: Sizing Normalizado, Volatility Targeting Causal y Freno por Drawdown (`Core3` y `MultiEstable`)

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en `DESC`, validación `REP` y simulación realista `LucidFlex 25K/50K` (`EF4`).  
Familia: `CANASTA_CORRELACION` (`5` pruebas registradas).  
Antecedentes: `docs/research/candidatas_nt8_20261125/ESTABILIDAD_Y_MATRIZ_ACTIVOS_20261125.md`, `docs/research/fundedsync_multiactivo_oro_20261122/RESULTADO.md`, `F-FRENO-DIARIO-NO`.  
Diferencia respecto a NO_REPETIR: **no usa freno diario intrasesión (`F-FRENO-DIARIO-NO`, ya probado dañino para el borde);** evalúa exclusivamente dimensionamiento **causal al cierre de sesión (`d - 1`)** sobre contratos enteros de micros (`MNQ/MES`), comparando contratos fijos vs riesgo constante `1R`, targeting por volatilidad realizada de la cartera (`20d`) y escalón lento por drawdown acumulado de cartera (`DD`).  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: ~`1.460` sesiones hábiles en `2020–2025 DESC` (~`960` `DESC` + `310` `REP`). Evalúa mejoras en estabilidad (`Calmar`, `Sharpe`, `MaxDD_R`, `worst_day_R`) y métricas prop `LucidFlex` (`EV_examen`, `Pasa%`, `USD/mes`, `Caja_min_p10`) bajo contracción de media al `60%`.  
Diagnóstico de mecanismo: serie año por año `2020–2025 DESC`, distribución de multiplicador aplicado `[0,5× .. 1,5×]`, truncamiento a contratos enteros en `MNQ` (`R1R=$200`) y episodios ±3 peores meses `K56`.

---

## Justificación económica
En la verificación NT8 quedó demostrado que usar `ContratosFijos = 1` aplasta los años `2020–2023` frente a `2024–2026` por la suba nominal de puntos/ATR del Nasdaq (`103 → 260 pts`). Aun normalizando a `1 R` constante, las rachas de volatilidad extrema (`2020-03`, `2022`) expanden la varianza diaria de la canasta. El *volatility targeting* causal a nivel de cartera (`20` días realizados de retornos `R` de la propia estrategia, estrictamente hasta `d-1`) junto con un escalón suave en drawdown (`DD <= -8 R`) busca comprimir caídas de cola derecha/izquierda y aumentar el `EV` de pase en cuentas prop con trailing drawdown y consistencia `40–50%`.

## Cómo podría refutarse
- En contratos enteros reales de `MNQ` (`$2/pt`), el redondeo discreto destruye el ajuste fino del `VolTarget` y rinde peor Sharpe/Calmar que `S1_R_CONST`.
- Bajar tamaño tras `-8 R` retrasa la recuperación durante rebotes en V (`DD_step` produce menos `USD/mes` y peor `EV` en `LucidFlex`).

---

## Variantes congeladas (`5` esquemas sobre `Core3` y `MultiEstable` con `MNQ/MES`, `2020–2025`)

| Esquema | Regla causal de sizing por operación (conocida antes de abrir la sesión `d`) |
|---|---|
| `S0_FIJO_MICRO` | Control: `1` MNQ por unidad (o contratos fijos equivalentes a riesgo medio `2022`) |
| `S1_R_CONST` | `R_1R = $200` (o `$150` en `25K`) constante, `contratos = round(R_target / (stop_pts * PV))` |
| `S2_VOLTARGET_20D` | `factor = clip(vol_obj / vol_realizada_20d(d-1), 0,50, 1,50)` aplicado sobre `R_target` (`vol_obj` fijada en mediana `2018–2019 DESC` sin mirar retorno) |
| `S3_DD_STEP` | `factor = 0,50` si `DD_acumulado_cerrado(d-1) <= -8,0 R`, recupera `1,00` al superar `-3,0 R` |
| `S4_VOLTARGET_DD` | `min(factor_vol20d, factor_dd_step)` combinado |

## Criterio de decisión
1. Se reportan `DESC` (`2020–2025`), `REP` (`2020–2025`), `Sharpe`, `Calmar`, `MaxDD`, `% meses > 0` y simulador `LucidFlex 25K/50K` (`real_100` y `contr_60`, `B = 10.000` trayectorias bootstrap) con prueba de diferencia pareada (`BH q = 0,10`).
2. Sólo se adopta un esquema dinámico si supera a `S1_R_CONST` en **ambos** criterios: `Calmar` neto en `DESC` (`+15%` relativo o más) y `EV / pasa%` en `LucidFlex` bajo contracción del `60%`.
