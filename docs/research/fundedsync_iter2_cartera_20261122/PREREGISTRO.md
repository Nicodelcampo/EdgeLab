# Iteración 2 `FUNDEDSYNC`: Variantes de Robustez/Rescate, Batería de Permutaciones y Cartera Ponderada (HOLDOUT-A4 / HOLDOUT-A5)

Estado: PRE-REGISTRO — se commitea antes de contar pruebas y antes de correr.
Fecha: 2026-11-22
Familia / módulo: `FUNDEDSYNC`
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa del embudo:** EF3 (batería de mejora V1, rescate estructural V2 en `DESC` A5 con permutaciones `B=5.000` + `BH-FDR` + `maxT` + `DSR`, transferencia multi-índice `DESC`/`REP` congelado, e ingeniería de cartera ponderada + sizing + LucidFlex).
- **Herramienta:** `tools/fundedsync_iter2_cartera.py` (reutiliza `tools/fundedsync_post_il_cadena.py`, `edgelab.research.fundedsyncstack`, `edgelab.costos`, `edgelab.holdout`, `edgelab.research.diagnostico_grilla`, `tools/lucid_guia.py` y compuerta K51/L1..L4).
- **Presupuesto global (K51):** **`95` pruebas** (`23` V1 robustez núcleo + `22` V2 rescate estructural + `38` Transferencia multi-índice DESC/REP + `12` Cartera/Sizing `DESC → REP`).

Antecedentes: `docs/research/fundedsync_post_il_20261122/RESULTADO.md` (auditoría post-IL: núcleo válido T/R/Z/V_nm30/W_eod25; A20/F/C/N con señal parcial `POST_2020`, A1/P/Q/S refutadas), `docs/research/fundedsyncstack_20261115/RESULTADO_TANDA2.md`, `tools/mejora_ronda2.py`, `tools/lucid_guia.py`, `edgelab/cartera/asignacion.py`, `tools/antecedentes.py`. Factores en `FACTORES.jsonl`: `F-FUNDEDSYNC-SIN-VENTAJA`, `F-FRENO-DIARIO-NO`, `F-AJUSTE-FINO-NO-PAGA`, `F-SALIDA-TECNICA-REGALA-LA-GANANCIA`, `F-RUPTURA-VIVE-DEL-DIA-DE-TENDENCIA`, `F-FRICCION-RELATIVA-REGIMEN`, `F-LUCID-SIN-OVERNIGHT`, `F-Z-TRANSFER-RTY`, `F-R-ATRPHASE-EN-R`, `F-TZR-TAMANO-EN-CARTERA`, `F-LUCID-PLAN`.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27, K28, K32, K33, K40, K48, K51, K55, K56, HOLDOUT-A4/A5).

Cambio respecto a falla previa: respecto de `F-FUNDEDSYNC-SIN-VENTAJA` (fábrica pre-IL sobre CFD Dukascopy en puntos) y de las fallas específicas observadas únicamente en `NQ DESC POST_2020`, esta iteración ataca causas mecánicas concretas antes de elegir variantes:
1. **Robustez y reducción de drawdown en ganadoras actuales (`V1`, 23 variantes en `DESC`):** evalúa sensibilidad del stop de catástrofe MAE en `R` y `Z` (`0,20–0,50 × ATR20`, pues `0,25 ATR` mostró `mae_p90 = 2,58 R`), filtros nativos anti-whipsaw en `W_eod` (`slope`, `conf2`, `dist4` × `0,25–0,50 ATR`), tope MAE escalado a `ATR20` en `V_nm30` (`0,30–0,50 ATR` y SL `$1200`) para hacerlo portable fuera de `NQ`, y multiplicador ORB en `T` (`1,0` y `1,5`).
2. **Rescate estructural sin sobreajuste de módulos débiles/refutados (`V2`, 22 variantes en `DESC`):** ataca exactamente los cuellos de botella diagnosticados en `DESC`:
   - `A1` (`-0,144 R` en largos vs `+0,056 R` en cortos, `med_fric_R = 0,172`): restringe a cortos puros (`allow_longs=False`) y amplía stop (`hard_stop_atr_mult ∈ {3.0, 5.0}`) para comprimir la fricción relativa `< 0,08 R`.
   - `A20` (correlación negativa `-0,15` vs `W_eod25` cuando conserva su lógica short-only): mantiene `exit_on_st_flip=True` en lugar de forzar EOD (que colapsó en `REP`) y prueba alineación SuperTrend + stop `2,5 ATR`.
   - `F` (usa ATR de **5 min**, no diario, por lo que `0,5 ATR` anuló el 100% de señales): prueba `max_initial_risk_atr ∈ {0.0, 5.0, 8.0}`, `disable_delta_filter` y `tp_rr=99` (salida EOD).
   - `P` (RR pobre nativo): exige `minimum_reward_risk ∈ {1.0, 1.5, 2.0}` y mayor `target_swing_length` (`5–20`).
   - `C` (gap longs-only en 150m+): prueba simetría bidireccional y apertura más temprana (`60 min`).
   - `S` y `N`: alineación SuperTrend / solo cortos en `S` y stops MAE más ceñidos (`0,25–0,35 ATR`) en `N` de fábrica (donde `mae_p90 = 0,55 R`).
3. **Batería anti-sobreajuste (`B = 5.000` permutaciones sincronizadas por bloque de 5 días):** en lugar de elegir el máximo marginal en `DESC`, todas las `45` variantes pasan control `BH-FDR`, test global `maxT` (White Reality Check / Westfall-Young) y `DSR` usando `numero_efectivo` de `diagnostico_grilla`.
4. **Ingeniería de cartera y respeto a `F-FRENO-DIARIO-NO`:** en `DESC → REP` congelado se prueban 3 regímenes de sizing (`R_const`, `raiz_riesgo`, `fijo_micro`) y 6 esquemas de ponderación (`equal_1R`, `inv_vol_dia`, `inv_vol_mes`, `ERC_cov_cap`, `HRP`, `freq_dur_concurrency` con tope causal de riesgo concurrente intradía de `3,0 R` por dirección — nunca freno por P&L intradía).

Potencia previa: en `NQ A5 DESC POST_2020` (`46` meses `DESC`, `n ≈ 108–3.400`), el MDE al 80% (`α=0,05`) va de `~0,05 R` en reglas frecuentes (`V`, `T`, `W`, `A20`) a `~0,19–0,25 R` en baja frecuencia (`R`, `Z`, `C`), que se compensa en la evaluación multi-índice (`ES, YM, RTY`) y en la combinación ponderada de cartera (`t_ses > 5` en `DESC`). La confirmación `REP` congelada cuenta con `14` meses `POST_2020` (y `38` meses en `FULL_2008`).

Diagnóstico de mecanismo: todas las grillas de V1/V2 pasarán obligatoriamente por `edgelab.research.diagnostico_grilla.diagnostico()` y `episodios()` pegando las líneas `Diagnóstico de grilla:` y `Episodios:` verbatim en `RESULTADO.md` (K55/K56).

Costos estimados declarados (K33): `NQ/MNQ`, `ES/MES`, `YM/MYM` y `RTY` emplean exclusivamente costos medidos en `config/costos/costos_canonicos.json`. `EMD` emplea spread estimado (`0,4378` pts RT) dentro de `costos.estimados_permitidos("docs/research/fundedsync_iter2_cartera_20261122/PREREGISTRO.md")` y se reporta separado de la cartera operable. `RTY` se mide con costo `RTY` y NO entra a micros simulados sin medición de `M2K`. Las tarifas `LucidFlex` con 40% consistencia heredan la estimación declarada en `tools/lucid_guia.py`.

## Justificación económica
1. **Asimetría de duración, riesgo y frecuencia en la cartera base:** En `NQ DESC POST_2020`, `R` (`+0,592 R`, `2,8/mes`, duración `360m`), `Z` (`+0,327 R`, `2,3/mes`, `60m`), `T` (`+0,146 R`, `18,7/mes`, `168m`), `V_nm30` (`+0,047 R`, `21,8/mes`, `60m`) y `W_eod25` (`+0,123 R`, `11,7/mes`, `389m`) tienen volatilidades mensuales, duraciones y frecuencias muy dispares, llegando a `5` posiciones simultáneas (`4` netas en la misma dirección). Igualar a `1 R` plano subestima a `Z`/`R` y sobreexpone a `W`/`T` en días tendenciales coincidentes. Ajustar pesos por riesgo/frecuencia/covarianza + duración/concurrencia y tamaño por operación busca maximizar `Calmar`, `t_ses` y supervivencia prop firm sin depender de optimización in-sample de retornos.
2. **Coherencia con régimen moderno (`2020+`) y auditoría `FULL_2008`:** Priorizamos la operatividad en `POST_2020/POST_2021` reportando siempre el contraste honesto `FULL_2008` y exigiendo confirmación en `REP` A5 congelado para evitar espejismos de `DESC`.

## Diseño fijo (HOLDOUT-A4 `< 2026-10-01` y HOLDOUT-A5)
- **Etapa 1 (NQ A5 `DESC`):** `45` variantes (`23` V1 + `22` V2) + batería de `5.000` permutaciones en bloque de 5 días + `BH-FDR` + `maxT` + `DSR` + diagnóstico K55/K56.
- **Etapa 2 (Multi-Índice `DESC` y `REP` congelado):** hasta `9` finalistas seleccionados **solo desde `NQ DESC`** (5 núcleo `T, R, Z, V, W` escalados + hasta 4 diversificadores/rescatadas `A20, N` + hasta 2 de `A1/F/P/C/S` si pasan `p_perm < 0,05` y `fric <= 0,12`) evaluados en `NQ, ES, YM, RTY` y `EMD` (K33 separado).
- **Etapa 3–4 (Cartera `DESC → REP` congelado):** ajuste de pesos y sizing solo en `DESC POST_2020`, evaluación congelada en `REP POST_2020` (sin leer `HOLDOUT`, `EMBARGO`, `TERMINAL`), Monte Carlo de cartera (`B=5.000`) y viabilidad **LucidFlex** (`25K/50K/100K/150K`) a deriva `100%` y `60%`.

## Cómo podría refutarse
- Toda variante V1/V2 queda **refutada** si no supera `p_perm < 0,05` y `R_neto > 0` con `med_fric_R <= 0,12` en `NQ DESC POST_2020`, si `q_bh >= 0,10` o `p_maxT >= 0,15` la expone como azar de búsqueda múltiple, si depende de `< 3` meses atípicos (`episodios`), o si invierte signo en `NQ REP` congelado.
- Un esquema de ponderación/sizing avanzado queda **refutado** si no mejora `Calmar` o `t_ses` o no reduce drawdown frente al baseline `W0_equal_1R` cuando se evalúa congelado en `REP POST_2020`.
- La viabilidad prop firm (`LucidFlex`) queda **refutada** si bajo media contraída al `60%` el neto promedio por ciclo de cuentas (`neto_medio` o `neto_12m_medio`) resulta negativo.
