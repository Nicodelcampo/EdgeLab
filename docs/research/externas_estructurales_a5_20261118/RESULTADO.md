# EXTERNAS-ESTRUCTURALES-A5 en M1 de futuros 2006–2025: resultado en DESC y auditoría de Dual Thrust (2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO.md`, diseño `DISENO.md`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `FASE0.json`, `DESC.json`, `CORRIDA.json`, `AUDITORIA_DUAL_THRUST_EXTERNAS28.json`. Familia `EXTERNAS_ESTRUCTURALES_A5` (16 pruebas registradas en `TRIAL_REGISTRY_GLOBAL.jsonl`), etapa EF3.

## 1. Veredicto de `EXTERNAS-ESTRUCTURALES-A5`: REFUTADA en DESC (`0/16` pasan BH `q = 0,10`)

1. **Fase 0 (fricción en R sin mirar retornos):**
   - Al anclar los stops iniciales a estructura diaria (`rg >= 0,40–0,50 × ATR20_D1` o `0,45 × rng4`), **6 de las 8 reglas estructurales (`ES2`, `ES3`, `ES4`, `ES6`, `ES7`, `ES8`) lograron fricción mediana global $\le 0,08\text{ R}$** (`0,064–0,068 R` en la canasta `ES+NQ+YM+GC`, y `0,052–0,061 R` en `NQ` e `YM`), mientras que `ES1` (`0,40 × ATR20_D1`, mediana `0,0836 R`) y `ES5` (`0,45 × ATR20_D1`, mediana `0,0804 R`) quedaron apenas en el borde por el peso de `ES` en los años de baja volatilidad (`2006–2007`, `2012–2017`) y sí pasan $\le 0,08\text{ R}$ en `NQ` (`0,072 R` y `0,068 R`) e `YM` (`0,071 R` y `0,069 R`).
   - Esto confirma empíricamente que el diseño estructural resuelve por completo el cuello de botella de `EXTERNAS-28` en M1 crudo (donde 110 de 114 variantes tenían fricción mediana $\ge 1,17\text{ R}$).
2. **Evaluación en `DESC` (`2006–2025`, `ES + NQ + YM + GC`, 16 pruebas):**
   - **Ninguna de las 16 hipótesis (8 reglas absolutas + 8 contrastes contra su control pareado) supera `BH q = 0,10` en `DESC`**, y las 8 reglas tienen **$R$ neto medio negativo** (`-0,052 R` a `-0,118 R` en toda la muestra; `-0,013 R` a `-0,127 R` en el subconjunto operable con fricción individual $\le 0,08\text{ R}$).
   - Por `K49` (`a5.plan_lectura`), todas las reglas tienen `potencia = 0,0` para `REP` (`efecto de DESC <= 0`). **`REP` y `HOLDOUT` no se leyeron y permanecen intactos.**

| Regla | Familia / Fuente | n DESC | Sesiones DESC | Fricción R med | R bruto | p (bruto) | Años + | R neto | R neto operable ($\le 0,08\text{ R}$) | R bruto 2006–2011 | Contraste `ESk - ESkN` (dif bruto / p) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **`ES1`** | Gao et al. (2017) First-30m $\to$ 15:00 NY | 2.243 | 1.288 | 0,0836 | +0,0119 | 0,258 | 55 % | −0,0747 | −0,0215 | −0,0035 | **+0,0414 R** ($p = 0,163$) |
| **`ES2`** | Chalek Dual Thrust 4d (régimen comprimido) | 2.070 | 1.161 | **0,0656** | +0,0092 | 0,355 | 55 % | −0,0602 | −0,0128 | +0,0383 | −0,0128 R ($p = 0,635$) |
| **`ES3`** | Pruitt Dynamic Breakout II + filtro BB | 2.554 | 1.413 | **0,0684** | −0,0092 | 0,646 | 40 % | −0,0805 | −0,0448 | −0,0841 | −0,2777 R ($p = 0,997$) |
| **`ES4`** | Connors RSI(2) + ATR Pullback (> SMA100) | 949 | 603 | **0,0647** | −0,0165 | 0,681 | 35 % | −0,0839 | −0,0642 | −0,0060 | −0,0510 R ($p = 0,900$) |
| **`ES5`** | Composer FTLT / Deez RSI(10) extremo 10:00 | 1.285 | 823 | 0,0804 | −0,0134 | 0,624 | 50 % | −0,0957 | −0,0471 | −0,0193 | −0,1233 R ($p = 0,993$) |
| **`ES6`** | QFL / Altrady H1 Base Crack + mecha rechazo | 1.736 | 1.136 | **0,0678** | −0,0469 | 0,981 | 25 % | −0,1184 | −0,1274 | −0,0626 | +0,0023 R ($p = 0,467$) |
| **`ES7`** | LuxAlgo SMC H1 FVG 3 barras Retest | 2.607 | 1.552 | **0,0667** | **+0,0173** | 0,170 | 55 % | −0,0517 | −0,0272 | **+0,0608** | −0,0213 R ($p = 0,776$) |
| **`ES8`** | Kivanc PMax H1 Flip + Squeeze Compression | 343 | 222 | **0,0641** | −0,0290 | 0,744 | 50 % | −0,0947 | −0,1098 | −0,0018 | −0,0563 R ($p = 0,874$) |

### Desglose por instrumento de las reglas con $R$ bruto positivo (`ES1`, `ES2`, `ES7`) y hallazgos de los controles (`ESkN`)

1. **`ES1` (Gao et al. 2017 First-30m $\to$ 15:00 NY):**
   - Tiene $R$ bruto positivo en los tres índices de renta variable (`ES`: `+0,0319 R`, `n=531`; `NQ`: `+0,0179 R`, `n=716`; `YM`: `+0,0077 R`, `n=628`) y negativo en oro (`GC`: `-0,0216 R`, `n=368`), consistente con la tesis de Gao et al. (rebalanceo de ETFs de índices bursátiles en la última hora RTH, ausente en oro).
   - Además, el contraste de doble confirmación (`ES1 - ES1N = +0,0414 R`, $p = 0,163$) tiene el signo predicho por el paper (`ES1N` pierde `-0,0295 R` bruto cuando a las 15:00 NY el signo divergió de la primera media hora). Sin embargo, la magnitud bruta (`+0,018 a +0,032 R`) es insuficiente para pagar la fricción canónica (`~0,073–0,112 R`).
2. **`ES7` vs `ES7N` (LuxAlgo SMC H1 Fair Value Gap vs Pullback H1 sin gap):**
   - `ES7` logra `+0,0173 R` bruto (`+0,0608 R` en años limpios `2006–2011`; `+0,0446 R` en `GC`, `+0,0192 R` en `NQ`, `+0,0099 R` en `YM`), pero su control pareado **`ES7N` (pullback del 50% a una vela H1 impulsiva que NO dejó gap de 3 barras) obtiene `+0,0386 R` bruto** (`ES`: `+0,0882 R`, `NQ`: `+0,0366 R`, `YM`: `+0,0262 R`).
   - **Lección estructural (`ES7 - ES7N = -0,0213 R`):** la condición de que quede un hueco de 3 barras (`Fair Value Gap`) **no agrega ventaja alguna** sobre comprar/vender el retroceso al 50% de cualquier vela H1 impulsiva (`cuerpo >= 0,25 × ATR20_D1`).
3. **Inversión de los filtros de régimen en `ES2`, `ES3`, `ES5` y `ES8`:**
   - En las cuatro familias de ruptura/impulso, **el control sin compresión o en régimen neutro superó en bruto a la variante filtrada**:
     - En **`ES2` (Dual Thrust 4d)**: romper tras expansión (`ES2N`: `+0,0220 R` bruto; `ES`: `+0,0566 R` bruto / **`+0,0116 R` neto**, `GC`: `+0,0590 R` bruto / **`+0,0229 R` neto**, fricción `0,036–0,045 R`) superó a romper tras compresión (`ES2`: `+0,0092 R` bruto), porque cuando `rng4` es grande el stop (`0,45 × rng4`) es más ancho, la fricción cae a `~0,035 R` y el umbral de ruptura evita el ruido matutino.
     - En **`ES5` vs `ES5N`**: el fade de `RSI(10)` diario extremo a las 10:00 NY (`ES5`) dio `-0,0134 R` bruto, mientras que el control `ES5N` (**continuación a las 10:00 NY en dirección del impulso de los primeros 30m cuando el `RSI(10)` diario está neutro `40..60`**) obtuvo **`+0,1099 R` bruto** en la canasta (`ES`: `+0,1744 R` bruto / `+0,0827 R` neto, `n=704`; `NQ`: `+0,1438 R` bruto / `+0,0777 R` neto, `n=765`; `YM`: `+0,0909 R` bruto / `+0,0311 R` neto, `n=765`; `GC`: `+0,0121 R` bruto, `n=582`). Como `ES5N` fue pre-registrado como control y no como hipótesis principal, no se nomina en esta campaña (evitando post-hoc cherry-picking), pero confirma que a las `10:00 NY` tras un `open drive >= 0,12 × ATR20_D1` en días no sobreextendidos domina la **continuación** y no la reversión.

---

## 2. Auditoría completa en `DESC` (`2006–2025`) de los sobrevivientes de Fase 0 de `EXTERNAS-28` (`Dual Thrust` `X036`–`X039`)

Para complementar el trabajo de Claude en `EXTERNAS-28` (`docs/research/externas_a5_20261118/PREREGISTRO.md`, donde `X036`–`X039` fueron las únicas 4 variantes de las 114 que pasaron Fase 0 con fricción mediana $\le 0,08\text{ R}$), corrimos las 4 variantes exactas de `edgelab/research/estrategias/dual_thrust_chalek.py` en el motor canónico `ejecucion.py` sobre `NQ`, `ES`, `YM` y `GC` (`2006-01-06 → 2025-07-31`, bloque `DESC`):

| Variante (`EXTERNAS-28`) | Parámetros (`n_days`, `k1`, `k2`, `rr`) | n DESC (`4` inst) | Fricción R media | R bruto DESC | SE | p (bruto) | Años + | R neto DESC | R neto operable ($\le 0,08\text{ R}$) | R bruto 2006–2011 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`X036`** | `n_days=4, k1=0,5, k2=0,5, rr=1,5` | 6.553 | 0,0439 | **+0,0334** | 0,0129 | **0,0049** | 75 % | −0,0105 | +0,0056 (`n=5.774`) | +0,0598 |
| **`X037`** | `n_days=4, k1=0,5, k2=0,5, rr=2,0` | 6.553 | 0,0439 | **+0,0364** | 0,0135 | **0,0035** | 75 % | −0,0074 | +0,0077 (`n=5.774`) | +0,0694 |
| **`X038`** | `n_days=4, k1=0,7, k2=0,7, rr=1,5` | 4.055 | 0,0479 | **+0,0530** | 0,0160 | **0,00047** | **80 %** | **+0,0051** | **+0,0254** (`n=3.441`) | **+0,0862** |
| **`X039`** | `n_days=4, k1=0,7, k2=0,7, rr=2,0` | 4.055 | 0,0479 | **+0,0535** | 0,0168 | **0,00074** | **80 %** | **+0,0056** | **+0,0271** (`n=3.441`) | **+0,0964** |

### Desglose por instrumento de `X038` y `X039` (`k1 = k2 = 0,7`, umbral alto) en `DESC` (`2006–2025`):
- **`GC` (Oro, `n = 900` sesiones DESC):**
  - `X038` (`rr=1,5`): **$R$ bruto `+0,0998 R`**, fricción mediana `0,0448 R`, **$R$ neto `+0,0511 R`**.
  - `X039` (`rr=2,0`): **$R$ bruto `+0,0977 R`**, fricción mediana `0,0448 R`, **$R$ neto `+0,0490 R`**.
- **`NQ` (Nasdaq 100, `n = 1.054` sesiones DESC):**
  - `X038` (`rr=1,5`): **$R$ bruto `+0,0581 R`**, fricción mediana `0,0369 R`, **$R$ neto `+0,0153 R`**.
  - `X039` (`rr=2,0`): **$R$ bruto `+0,0601 R`**, fricción mediana `0,0369 R`, **$R$ neto `+0,0173 R`**.
- **`ES` (S&P 500, `n = 1.046` sesiones DESC):**
  - `X038`: $R$ bruto `+0,0498 R`, fricción mediana `0,0518 R`, $R$ neto `-0,0100 R`.
  - `X039`: $R$ bruto `+0,0457 R`, fricción mediana `0,0518 R`, $R$ neto `-0,0142 R`.
- **`YM` (Dow Jones, `n = 1.055` sesiones DESC):**
  - `X038`: $R$ bruto `+0,0110 R`, fricción mediana `0,0341 R`, $R$ neto `-0,0294 R`.
  - `X039`: $R$ bruto `+0,0172 R`, fricción mediana `0,0341 R`, $R$ neto `-0,0233 R`.

**Diagnóstico económico de `X038`/`X039` (`Dual Thrust` con `k1 = k2 = 0,7`):**
1. Las 4 variantes pasan `BH q = 0,10` en bruto ($p \in [0,00047, 0,0049]$ contra el corte BH de 4 sobrevivientes de Fase 0) y son positivas en el **75 %–80 % de los 20 años (`2006–2025`)** y en los años limpios `2006–2011` (`+0,086 a +0,096 R` bruto).
2. Sin embargo, el $R$ neto agregado en la canasta de 4 instrumentos es muy pequeño (`+0,0051 R` en `X038` y `+0,0056 R` en `X039`, o `+0,025–0,027 R` filtrando días con fricción $\le 0,08\text{ R}$) porque `ES` e `YM` diluyen la ventaja que sí paga costos en **`GC` (`+0,051 R` neto)** y **`NQ` (`+0,017 R` neto)**.
3. Con un efecto neto agregado de `+0,0056 R` en la canasta de 4 instrumentos, la potencia en días (`K49`) sobre `REP` (`~290` sesiones REP) no alcanza `0,80`, por lo que `X038`/`X039` quedan en **`SIN_POTENCIA_PREVIA`** en la canasta completa sin gastar `REP`.
