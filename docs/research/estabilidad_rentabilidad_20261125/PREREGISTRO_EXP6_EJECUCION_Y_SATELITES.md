# EXP-6: Ejecución Límite en Ticks (`-0/-1/-2` Ticks), Costos Faltantes y Satélite Puro `ES/MES`

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en ticks reales (`2025–2026`) + EF3/EF4 en `ES/MES` (`DESC`/`REP`).  
Familia: `EJECUCION_Y_SATELITES` (`7` pruebas con desenlaces: `4` de ejecución en **6B** + `3` de satélite `ES` en **6C**; **6A** es medición target-free de spreads/costos con `0` pruebas de retorno).  
Antecedentes: `docs/HANDOFF_OPERATIVO_20261125_PRODUCCION.md`, `nt8/strategies/EdgeLabExecutionProbe.cs`, `edgelab/costos.py`, `F-DRC-TORI-FRICCION`.  
Diferencia respecto a NO_REPETIR: no re-evalúa `DRC/TORI` ni `PREAPERTURA-NQ Intento 1` (colapsan fuera de `00 s`); mide órdenes pasivas límite con reglas realistas de cola/llenado sobre `T`, `SOM_sin_finde` y `RQ5` (donde ya existe edge) y conforma un satélite puro en `ES` con las estrategias vivas verificadas (`RQ5_ES`, `C2_VZ_ES`, `ES5N_ES`, `T_ES`).  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: en **6B**, ~`220–450` señales en ticks (`2025–2026`), suficiente para estimar tasa de llenado (fill rate), *adverse selection* y ahorro neto por operación (MDE `~0,04 R` en fricción realizada). En **6C**, ~`900` sesiones `DESC` + `~300` `REP` en `ES`.  
Diagnóstico de mecanismo: reporte `diagnostico_grilla`, tasa de órdenes no llenadas en **6B** (separando costo ahorrado en llenadas vs costo de oportunidad en no llenadas) y matriz de correlación diaria contra `NQ_CORE` en **6C**.

---

## Justificación económica
1. **Sub-experimento 6A (`0` pruebas, target-free):** `RTY/M2K`, `6E/M6E`, `CL` y `EMD` siguen bloqueados por `K33` al no tener fricción canónica medida en `config/costos/costos_canonicos.json`. Medir su spread L1 y comisiones desbloquea futuras campañas multi-activo sin suposiciones optimistas.
2. **Sub-experimento 6B (`4` pruebas):** cada entrada `Market` en `NQ/MNQ` paga ~`1,55–1,98 pts` (`~0,02–0,03 R` en `T`/`SOM`/`RQ5`). Entrar con orden límite pasiva (`0`, `-1` o `-2` ticks de mejora, timeout `60 s` / `120 s`, sin persecución al cierre salvo variante explícita) ahorra el half-spread en las llenadas; sólo el test realista en ticks reales dirá si el ahorro supera la *adverse selection* (cuando sólo se llenan las malas).
3. **Sub-experimento 6C (`3` pruebas):** disponer de un satélite autónomo en `ES/MES` (`RQ5_ES + C2_VZ_ES + ES5N_ES` ± `T_ES/R_ES`) permite operar prop firms o cuentas con límites por activo reduciendo concentración en Nasdaq.

## Cómo podría refutarse
- **6B:** cualquier offset pasivo `-1/-2` ticks pierde dinero neto total frente a `Market` por selección adversa (dejar escapar mejores ganadores y llenarse en el 100% de perdedores).
- **6C:** la cartera satélite `ES` es negativa o no aporta `Sharpe` marginal / presenta correlación `> 0,70` con `NQ_CORE`.

---

## Diseño congelado (`7` pruebas totales)

### 6A — Medición Target-Free de Costos Canónicos (`0` pruebas)
- Agregar perfil medido L1/L2 (spread mediana RTH/ETH + comisiones actuales de broker/prop) para **`M2K`, `M6E`, `CL`, `EMD`** en `edgelab/costos.py` y sincronizar `FundedSyncAssets` en NT8.

### 6B — Ejecución Límite vs Market en Ticks Reales (`4` pruebas sobre `T`, `SOM_sin_finde`, `RQ5`, `NQ` `2025–2026`)
| Variante | Tipo de orden al dispararse la señal (`K40`: fill sólo tras cruce estricto o toque en tick realista) | Timeout | Acción tras timeout |
|---|---|---|---|
| `EX0_MKT` (Control) | `Market` a apertura barra `t+1` (slippage `1` tick medido) | — | — |
| `EX1_LMT_0T_60S` | `Limit` en `Close(t)` (bid/ask pasivo `0` ticks) | `60 s` | Cancela (no persigue) |
| `EX2_LMT_1T_120S` | `Limit` a `1` tick mejor que `Close(t)` | `120 s` | Cancela |
| `EX3_LMT_1T_MKT` | `Limit` `1` tick mejor; si no llena en `60 s`, pasa a `Market` | `60 s` | `Market` fallback |

### 6C — Cartera Satélite Pura `ES / MES` (`3` pruebas en `DESC` + `REP`)
| Cartera `ES` | Módulos incluidos |
|---|---|
| `ES_SAT_1` | `RQ5_ES` + `C2_VZ_ES` |
| `ES_SAT_2` | `RQ5_ES` + `C2_VZ_ES` + `ES5N_ES` |
| `ES_SAT_3` | `ES_SAT_2` + `T_ES_scaled` + `R_ES` (`ES_Core_US500`) |

## Criterio de decisión
- **6B:** gana la regla que mejore `PNL_neto_total_USD` (no sólo `PNL/trade`) contra `EX0_MKT` con `p < 0,05` (`BH q = 0,10`) en ticks y se replica en vivo con `EdgeLabExecutionProbe`.
- **6C:** pasa a `REP` y forward en `MES` la combinación `ES_SAT` con mayor `Calmar` neto `DESC`, `p < 0,05` y correlación `< 0,60` frente a `NQ_CORE`.
