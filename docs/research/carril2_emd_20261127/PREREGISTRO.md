# Pre-registro — CARRIL2_EMD: Transferencia Congelada de Carril 2 a E-mini S&P MidCap 400 (`EMD`, M1 NT8 `2006–2026-09`)

Estado: PREREGISTRO — EF3 transferencia congelada en `CARRIL2_EMD`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v5 — §0–§8 (K32, K33 costos estimados en JSON, K40 motor M1 calibrado, K51 conteo previo, K60 sin recorte post hoc, K64 sin cruce sellado).
Antecedentes: «Carril 2 EMD MidCap transferencia reglas congeladas placebo» — familias parecidas: CARRIL2_CONFIANZA, FUNDEDSYNC_TRANSFER, CANASTA_AMPLIA; NO_REPETIR: F-GEX-DIA-TENDENCIA, F-FRECUENCIA-POR-SELECCION, F-A20-NO-TRANSFIERE; código: tools/transferencia_multiactivo.py:1, tools/confianza_sin_forward.py:1, tools/orb_confirmacion_o1.py:1
Cambio respecto a falla previa: `F-A20-NO-TRANSFIERE` refutó las reglas intradía del vendedor en EMD (`t < 0`), mientras `F-FRECUENCIA-POR-SELECCION` midió frecuencias post selección; aquí transferimos exclusivamente las reglas diarias **congeladas** de Carril 2 (`carril2._senales` y `_senales2` sin `C2_ROT`) sobre el instrumento virgen `EMD` (`data/m1nt8/EMD_M1_nonadj_utc.parquet`) que Carril 2 nunca tocó, contrastadas contra su placebo exacto de igual exposición (`Regla − Control N`) tal como pide `PLAN_ESPIRAL_20261127 #3`.
Diagnóstico de mecanismo: no aplica — cero grilla paramétrica (`9` reglas congeladas de `tools/carril2.py` + sus `9` controles `N` y `2` canastas predefinidas).
Potencia previa: `EMD` cubre `2006-01 → 2026-09` (`249` meses calendario `< 2026-10-01`, ~`213` meses `2009–2026-09`); para diferencia mensual pareada `Regla − Control N` con efecto Sharpe `0,45–0,60` (~`t = 2,07–2,76` en `18–20` años), la potencia a alfa `0,05` unilateral está entre `0,65` y `0,85`.

## Justificación económica, costos K33 y diseño congelado
- **Instrumento y datos:** `EMD` (`data/m1nt8/EMD_M1_nonadj_utc.parquet`, barras `D1` vía `sqx_catalogo.barras_desde_m1` + camino `M1` vía `indices_m1`), cortado estrictamente `< 20261001` tanto en fecha de entrada como en `fecha_salida` (`TERMINAL` sellado).
- **K33 costos estimados declarados:** `EMD` figura en `config/costos/costos_canonicos.json` con `spread_estimado: true` (`tick_size=0,1`, `tick_value_usd=10,0`, `spread_ticks=2,0` estimado, comisión Topstep `3,78 USD` estimada). Este pre-registro autoriza explícitamente `costos.estimados_permitidos(PRE)` para calcular `base` (1 tick/lado) y `adverso` (2 ticks/lado), y además reporta **`bruto`** (`0` fricción) y **`2x`** (`2 × fricción base`) por K34.
- **Pruebas primarias (`3` pruebas):**
  1. Canasta equiponderada mensual en R de las `5` reglas núcleo (`C2_IBS, C2_D7, C2_TT, C2_TOM, C2_VBB`) y de las `9` reglas completas (`+ C2_P80, C2_EVRP, C2_VZ, C2_DBO`) en `EMD` (`2006–2026-09`, base neta).
  2. Placebo pareado **`Regla − Control N`** en `EMD` todo `2006–2026-09`.
  3. Placebo pareado **`Regla − Control N`** en `EMD` desde **`2009–2026-09`** (corte pre-registrado de `PLAN_ESPIRAL_20261127 #3`).
- Adicionalmente (descriptivo sin aumentar selección): desglose por bloques A5 (`DESC`, `REP`, `HOLDOUT` en un instrumento que `CARRIL2_A5` nunca usó), por `2019–2026-09` y por regla individual.

## 2. Cómo podría refutarse
- Refutada en lo esencial si **`Regla − Control N <= 0`** en `EMD` desde `2009` (`t <= 0` en el contraste pareado), lo que confirmaría que la caída post-2009 observada fuera de EE. UU. también afecta al MidCap de EE. UU. y obligaría a calibrar aún más a la baja el tamaño esperado en vivo de Carril 2.
