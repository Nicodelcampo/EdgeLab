# EXP-1: `T` con Tope de Stop Invariante de Escala (`%` Precio / `ATR20` / Sin Tope)

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en `DESC` (`BH q = 0,10`), paso a `REP` congelado sólo con potencia `K49 >= 0,80`; confirmación limpia en holdout terminal (`>= 2026-10-01`) + forward.  
Familia: `FUNDEDSYNC` (`7` pruebas registradas).  
Antecedentes: `T_stop100_BE15R_calFalse` en `FUNDEDSYNC_PROP_OPT_20261122`, `docs/research/fundedsync_multiactivo_oro_20261122/RESULTADO.md` (Etapa B2 en `ES`), `docs/research/candidatas_nt8_20261125/ESTABILIDAD_Y_MATRIZ_ACTIVOS_20261125.md` y `docs/research/candidatas_nt8_20261125/NOTA_HOLDOUT_A5_VISTO_EN_NT8.md`.  
Diferencia respecto a NO_REPETIR: no repite módulos descartados ni transfiere a `GC/YM`; modifica exclusivamente la cota superior en puntos de `T` (`100 pts` → escala relativa al precio o `ATR20`) en `NQ` y `ES` para corregir una distorsión geométrica del stop detectada en `2025–2026` (`51,6%–86,5%` de trades capeados).  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: ~`19` ops/mes por activo (`~1.050` ops `2020–2025 DESC`, `~300` ops `REP`). En contraste pareado `variante - T_FIJO_100` sobre `~450` trades donde difiere el stop (`2022–2025`), MDE (`80%`, `α=0,05`) ≈ `0,11 R`.  
Diagnóstico de mecanismo: reporte obligatorio vía `edgelab.research.diagnostico_grilla` (tasa de cap por año `2019–2025`, `R` neto en subgrupo capeado vs no capeado, `N_eff`, perillas inertes y episodios ±3 meses `K55/K56`).

---

## Justificación económica
En la regla original de `T` (`stop_orb_mult = 1,0`, `stop_max_pts = 100,0`), el techo de `100 pts` se calibró cuando `NQ` cotizaba en ~`7.000 pts` (`~1,4%` del índice). En `NQ` a `20.000–25.000+ pts`, `100 pts` equivale a `~0,40%` y capea el **`51,6%` (`2025`) a `86,5%` (`2026`)** de las entradas, estrangulando el stop por debajo de la volatilidad natural de la apertura (`ORB`) y generando stops prematuros por ruido intradía. Un techo proporcional al precio de cierre previo (`pct * prev_close`) o a `ATR20_D1` mantiene la misma geometría en todas las épocas sin cambiar el mecanismo de ruptura de tendencia. En `ES` (`ETAPA B2`), quitar el techo fijo ya mostró mejora (`+0,019 → +0,055 R`) y requiere prueba controlada específica.

## Cómo podría refutarse
- Ninguna variante supera a `T_FIJO_100` en `R_neto_mini` ni en el contraste pareado `variante - T_FIJO_100` con `BH q = 0,10` en `DESC`.
- En el subconjunto donde los dos stops difieren, ampliar el stop reduce la esperanza neta o aumenta el `MaxDD_R` sin mejorar la estabilidad anual (`2019–2025`).

---

## Variantes congeladas (`7` pruebas: `1` control + `6` variantes, en `NQ` y `ES`)
Todas conservan idéntica señal de entrada de `T`, `be_trigger_r = 1,5` en `NQ` (`0,0` en preset `ES`), calendario completo causal (`calFalse`) y cierre EOD `16:40 NY`, evaluadas con `veto_noticias` activo y fricción canónica (`NQ: 1,5455`, `MNQ: 1,9775`, `ES: 0,8877`, `MES: 1,155`):

| Variante | Regla de tope de stop (`stop_px` causal en barra previa) | Instrumentos | Tipo |
|---|---|---|---|
| `T_FIJO_100` | `min(max(2.0, 1.0 * ORB), 100.0)` (en `ES`: `29.0`) | `NQ` (primario), `ES` (sec.) | Control |
| `T_PCT_060` | `min(max(0.0002 * C_prev, 1.0 * ORB), 0.0060 * C_prev)` | `NQ`, `ES` | Hipótesis |
| `T_PCT_080` | `min(max(0.0002 * C_prev, 1.0 * ORB), 0.0080 * C_prev)` | `NQ`, `ES` | Hipótesis |
| `T_PCT_100` | `min(max(0.0002 * C_prev, 1.0 * ORB), 0.0100 * C_prev)` | `NQ`, `ES` | Hipótesis |
| `T_ATR_050` | `min(max(2.0, 1.0 * ORB), 0.50 * ATR20_D1)` | `NQ`, `ES` | Hipótesis |
| `T_ATR_075` | `min(max(2.0, 1.0 * ORB), 0.75 * ATR20_D1)` | `NQ`, `ES` | Hipótesis |
| `T_SIN_CAP` | `max(2.0, 1.0 * ORB)` (sin tope superior en puntos) | `NQ`, `ES` | Hipótesis |

## Criterio de decisión
1. Se evalúan las `6` comparaciones pareadas `variante - T_FIJO_100` en `DESC` (`2012–2025` y sub-bloque `2020–2025`), además del desglose absoluto `R_neto_mini`, `Sharpe`, `MaxDD_R` y `Calmar`, aplicando `BH q = 0,10` sobre los `7` tests de nivel y estabilidad.
2. Si una variante supera al control con menor `MaxDD` y mantiene consistencia en `2020–2025`, se nomina a `REP` congelado (`K49 >= 0,80`) y recién después se incorpora al runner `EdgeLabCandidataFS` para validación en holdout terminal/forward.
