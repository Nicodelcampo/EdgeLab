# EXP-5: Ensamble Descorrelacionado `MultiEstable` (`Core3 + SOM_sf + RQ5 + C2_VZ + ES5N + Franklin`)

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en `DESC` (`2020–2025`), validación `REP` congelada y simulador `LucidFlex 25K/50K` (`EF4`).  
Familia: `CANASTA_CORRELACION` (`12` pruebas registradas: `6` composiciones × `2` esquemas de pesos causales).  
Antecedentes: `docs/research/candidatas_nt8_20261125/ESTABILIDAD_Y_MATRIZ_ACTIVOS_20261125.md`, `docs/research/fundedsync_multiactivo_oro_20261122/RESULTADO.md`, `docs/research/validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md`, `F-FS-IL-REMEDICION-V-CANDIDATA`.  
Diferencia respecto a NO_REPETIR: excluye estrictamente todos los módulos refutados (`A1, A20, P, Q, W_tal_cual, PREAPERTURA-NQ, CVGAP-ES-C, DRC, TORI, HobbieCode, X038`) e incluye únicamente módulos intradía + swing (`RQ5 ES/NQ`, `C2_VZ`, `ES5N`, `Franklin NQ` + `VetoPreap`) verificados en NT8 o `CARRIL2/EXTERNAS`; además integra los resultados previos de `EXP-1` y `EXP-2` si ganan.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: ~`1.460` sesiones `2020–2025 DESC` y `~310` `REP`. En `DESC` la canasta `MultiEstable` suma ~`+323,9 R` con `MaxDD -17,4 R` (`Sharpe 1,87`). El contraste pareado `P_k - P0(Core3)` cuenta con `>600` días activos para detectar ganancia en `Sharpe` / `R/mes` bajo `BH q = 0,10`.  
Diagnóstico de mecanismo: matriz de correlación diaria por pares en `DESC`, contribución de cada sleeve en los peores `20%` meses de `Core3`, `MaxOpenR` alcanzado y diagnóstico `K56` de ±3 meses en `DESC` (sin tocar `REP` hasta cierre de selección).

---

## Justificación económica
Ninguna estrategia aislada mantiene pendiente lineal en todos los regímenes macro (`2020–2026`): `SOM_sin_finde` y `T` rinden fuerte en tendencias/expansión (`2020–21`, `2025–26`), mientras que `R`, `Z`, `RQ5_ES` (`8/8` años `+`) y `C2_VZ` (compresión de volatilidad implícita, `+14 R` en `2019`, `+7 R` en `2023`) capturan flujos ortogonales de cobertura institucional y *mean-reversion/vol-compression*. Combinarlos bajo un tope causal estricto de riesgo simultáneo (`MaxOpenR = 3,0`) permite duplicar el ingreso `R/año` en `2020–2023` (`+23,4 → +40,8 R/año` en `DESC`) sin deteriorar la curva `2024–2026` ni aumentar `MaxDD`.

## Cómo podría refutarse
- Agregar `RQ5`, `C2_VZ`, `ES5N` o `Franklin` empeora el `Calmar`, el `MaxDD` o el `EV` en `LucidFlex` respecto a `P0 (Core3)` / `P1 (+SOM_sf)` en `REP` congelado.
- La correlación durante crisis reales (`DD`) converge a `+1` y dispara simultáneamente el tope diario o trailing drawdown de `LucidFlex`.

---

## Composiciones congeladas (`6` composiciones × `2` asignaciones = `12` pruebas)

| Cartera | Módulos incluidos (con selector `T*` y `SOM*` si `EXP-1/2` nominan antes) | Propósito marginal |
|---|---|---|
| `P0_CORE3` (Control) | `T + R + Z` (`NQ/MNQ`) | Núcleo base puro |
| `P1_CORE_SOM` | `P0 + SOM_sin_finde` (`NQ/MNQ`) | Sumar flujo apertura + swing `L-J` |
| `P2_CORE_SOM_RQ5` | `P1 + RQ5(NQ) + RQ5(ES)` | Sumar banda de ruido en `NQ` y `ES` |
| `P3_MULTIESTABLE` | `P2 + C2_VZ(ES+NQ)` | Sumar sleeve swing anticíclico VIX/VXN |
| `P4_MULTI_ES5N` | `P3 + ES5N(ES)` | Sumar continuación `10:00 NY` neutra en `ES` |
| `P5_MULTI_FRANKLIN` | `P4 + Franklin(NQ, VetoPreap=true)` | Evaluar si `Franklin` filtrada agrega margen neto |

*(Nota diagnóstica aparte, no entra en las 12 pruebas primarias: sensibilidad incluyendo `V` con o sin freno tras caída `2025S2`, documentada en anexo del resultado).*

Cada `P0..P5` se corre con **exactamente `2` esquemas de pesos calculados en `DESC`**:
1. `W0_cap3R`: pesos nominales (`1,0 R` por núcleo `T/R/Z/SOM`; `0,5 R` por satélite `RQ5_NQ`, `RQ5_ES`, `C2_VZ`, `ES5N`, `Franklin`), con compuerta FIFO `MaxOpenR = 3,0`.
2. `W5_ERC_cap3R`: *Equal Risk Contribution* inverso a volatilidad + penalización por correlación en `DESC`, con `MaxOpenR = 3,0`.

## Criterio de decisión
1. Evaluación primaria en `DESC` (`BH q = 0,10` sobre diferencias de retorno por sesión y `Sharpe` vs `P0_CORE3`), verificación en `REP` congelado de las nominadas (`K49`) y corrida `LucidFlex 25K/50K`.
2. La ganadora pasa a ser la cartera candidata única para reemplazar/evolucionar `Core4/Core5` en producción (siendo su confirmación definitiva el holdout terminal `>= 2026-10-01` + forward `e-proceso`).
