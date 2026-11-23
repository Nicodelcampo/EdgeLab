# Despliegue Integrado P_OPT_SF_v2 (`FUNDEDSYNC`): LucidFlex, Ticks K30, Holdout Confirmatorio y Multi-Prop Firm

**Pre-registro:** [PREREGISTRO.md](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/PREREGISTRO.md) (`K51`, `39` pruebas declaradas)  
**Orquestador:** [fundedsync_integracion_multiprop.py](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/tools/fundedsync_integracion_multiprop.py)  
**Executor NT8 Unificado:** [EdgeLabFundedSyncPortfolio.cs](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/nt8/strategies/EdgeLabFundedSyncPortfolio.cs)  
**Catalogo Multi-Prop:** [catalogo_multiprop_20261122.json](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/catalogo_multiprop_20261122.json)  

---

## 1. Cierre Estadistico de `P_OPT_SF_v2` (DESC 2020-2026-09)

1. **Paridad exacta de `SOMEOD` desde M1:** la generacion causal barra a barra sobre M1 NT8 produjo **0 diferencia** frente a `SOM_OPS_NQ.csv.gz` (`n_ref = 1733`, `n_nuevo = 1733`, `diff_n = 0`, `R_bruto_ref = 0.06611`, `R_bruto_nuevo = 0.06611`, `diff_R_bruto = 0.0`), permitiendo correr `SOMEOD_ext_NQ` sobre `A5_HOLDOUT` y `TERMINAL` sin brecha de datos.
2. **Prueba 1 de estrategia (`W` trail sobre `noRe`):** `W_slope_allowReFalse_trail_15_50_ATR25` (`R_neto_mini = 0.2174`, `R_por_mes = 1.361`, `t_ses = 2.42`, `dd_R = -9.25`, `calmar = 1.77`) **no promovio** (`promovio_w_trail = false`) frente a `W_slope_allowReFalse_ATR25` (`R_neto_mini = 0.2611`, `R_por_mes = 1.634`, `t_ses = 2.75`, `dd_R = -10.26`, `calmar = 1.91`).
3. **Pesos `W5_freq_dur_conc` aprendidos en `DESC` (`2020-01..2026-09`) y rendimiento base (`MaxOpenR = 3.0`):**
   - Pesos `W5`: `Z = 1.965598`, `R = 1.653354`, `N = 1.252428`, `V = 1.019769`, `W = 0.915674`, `SOMEOD = 0.911410`, `T = 0.768284`.
   - `DESC` (`1162` sesiones): `+8.211 R/mes`, `t_ses = 4.81`, `Sharpe = 2.24`, `dd_R = -19.55`, `Calmar = 5.04`, `78.3%` meses positivos.
   - `REP` (`358` sesiones): `+5.860 R/mes`, `t_ses = 2.08`, `Sharpe = 1.74`, `dd_R = -23.39`, `Calmar = 3.01`, `85.7%` meses positivos.

---

## 2. Etapa A — Colisiones Opuestas en `NQ` y 18 Configuraciones LucidFlex

### Auditoria causal de colisiones Long vs Short
- En `DESC`: `25.88%` de trades (`880 / 3400`) y `41.05%` de sesiones (`477 / 1162`) registraron posiciones opuestas abiertas simultaneamente (`SOMEOD vs T`: `300`, `SOMEOD vs V`: `162`, `SOMEOD vs W`: `103`).
- En `REP`: `25.05%` de trades (`259 / 1034`) y `37.15%` de sesiones (`133 / 358`). Comparativa de politicas sobre serie `$450 / 1R`:
  - `independiente`: neto `+$36,641.2`, `Sharpe = 1.67`, `dd_eod = -$11,674.7`, `worst_lo = -$2,632.7`.
  - `netting` (natural NT8 cuenta unica): neto `+$36,668.9`, `Sharpe = 1.67`, `dd_eod = -$11,668.4`, **`worst_lo = -$2,173.3`** (reduccion de excursion adversa simultanea).
  - `veto_opuesto` (`843` trades): neto `+$37,643.4`, `Sharpe = 1.72`, `dd_eod = -$10,988.5`, `worst_lo = -$2,224.8`.

### Integracion LucidFlex (`18` combinaciones, `N=3000`, `H=504`, `payout_basis="total"`)
Resultados completos en [etapaA_integracion_lucidflex.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/etapaA_integracion_lucidflex.csv):

- **Regimen `cero_0` (control negativo):** la mediana (`neto12_p50_usd`) es estrictamente negativa en las `18/18` configuraciones en `DESC` (`-$3,759.8` a `-$28,066.8`) y `REP` (`-$3,211.5` a `-$18,620.9`). La media es negativa en `17/18` en `REP` y `18/18` en `DESC` (`L17` presenta media positiva residual `+$1,336.6` solo en `REP` por asimetria tipo opcion con `p50 = -$3,211.5`, cayendo a `-$1,064.2` en `DESC` y `-$1,489.1` en `A5_HOLDOUT`).
- **Efecto `netting` / `veto_opuesto` vs `independiente` (`$650/$450 + E8 + stag3` en `REP contraida 60%`):**
  - `L09` (`independiente`): `+$11,487.9`, `p10 = -$25,381.4`, `ratio = 0.453`.
  - `L15` (`netting`): **`+$14,255.9`**, `p10 = -$23,356.4`, **`ratio = 0.610`**.
  - `L16` (`veto_opuesto`): **`+$14,333.2`**, `p10 = -$23,567.5`, **`ratio = 0.608`**.
- **Los `3` planos congelados ANTES de tocar holdout ([planes_congelados.json](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/planes_congelados.json)):**
  1. `CONSERVADOR_50K -> L17_50K_Conserv_R200_E5_s3` (`$200/$200`, E5, stagger `3d`, colchon `$1,250`): en `REP real_100` `+$15,280.0` (`p10 = -$4,229.8`); en `REP 60%` `+$8,538.0` (`p10 = -$6,266.3`, `ratio = 1.363`, `7.66` retiros/12m).
  2. `EQUILIBRADO_150K -> L02_150K_Base_40p_Col2500_E5_s1` (`$450/$450`, E5, stagger `1d`, colchon `$2,500`): en `REP real_100` `+$25,417.7` (`p10 = -$11,569.5`); en `REP 60%` `+$11,529.1` (`p10 = -$16,806.7`, `ratio = 0.686`, `7.45` retiros/12m).
  3. `MAX_FLUJO_150K -> L10_150K_Boost650_E10_s1` (`$650/$450`, E10, stagger `1d`, colchon `$2,500`): en `REP real_100` `+$33,603.1` (`p10 = -$20,360.4`); en `REP 60%` `+$15,915.6` (`p10 = -$33,423.0`, `12.58` retiros/12m).

![Etapa A Integracion LucidFlex y Colisiones](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/deploy_etapaA_integracion_y_colisiones.png)

---

## 3. Etapa B — Calibracion Tick a Tick `K30` y Confirmacion Congelada (`A5_HOLDOUT` + `TERMINAL`)

### Etapa B1: Calibracion en Ticks Reales Kaggle `K30` (`159` sesiones `20250805..20260925`)
Resultados completos en [etapaB_calibracion_ticks_k30.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/etapaB_calibracion_ticks_k30.csv):

- **Cartera `CARTERA_P_OPT_SF_v2` (`564` trades, `159` sesiones):**
  - `R_neto_m1 = +0.1262 R` vs `R_neto_ticks = +0.1577 R`, `corr_sesion = 0.9836`, `m1_ses_media = 0.4816`, `ticks_ses_media = 0.5798` (`ee = 0.2873`) -> **`calibra_k30 = True`** (ticks reales superan a M1).
  - Anti-microscalping: `100.0%` de trades y `100.0%` de ganancias duran `> 5s` y `> 10s`.
  - Sensibilidad de costos en `K30`: `1.0x` (`1.545 pts`) = `+75.86 R` (`+10.02 R/mes`); `1.25x` (`1.932 pts`) = `+74.39 R` (`+9.825 R/mes`); `1.5x` (`2.318 pts`) = `+72.91 R` (`+9.629 R/mes`).
- **Por modulo en `K30`:**
  - `T`, `V`, `W`, `SOMEOD` tuvieron `comunes >= 41` y todos pasaron `calibra_k30 = True` (`corr` entre `0.9262` y `0.9801`).
  - `R` (`comunes = 18`, `corr = 0.9972`), `Z` (`comunes = 19`, `corr = 0.9794`) y `N` (`comunes = 26`, `corr = 0.9938`) marcaron `calibra_k30 = False` exclusivamente por el umbral `comunes >= 30` de `a5.calibrar_por_sesion`, manteniendo exactamente el mismo signo positivo y diferencias M1-ticks dentro de banda de error.

### Etapa B2: Holdout Congelado `A5_HOLDOUT` (`2020-2026-09`) y `TERMINAL` (`2026-10-01..2026-11-17`)
1. **`A5_HOLDOUT` (`450` sesiones, `21` meses nunca tocados en Iters 1–4):**
   - Cartera `P_OPT_SF_v2`: **`+3.209 R/mes`**, `t_ses = 1.43`, **`Sharpe = 1.07`**, `dd_R = -24.95 R`, **`Calmar = 1.54`**, `worst_mes = -10.44 R`, `66.7%` meses positivos.
   - `6/7` modulos fueron netamente positivos (`T = +3.401 R/mes`, `V = +0.469`, `R = +0.459`, `SOMEOD = +0.397`, `Z = +0.296`, `N = +0.230`); solo `W` registro `-0.763 R/mes` (`-0.1261 R/op`).
   - Evaluacion MC de los `3` planos congelados en `A5_HOLDOUT`:
     - En `real_100` (expectativa observada real del holdout): **los 3 planos son rentables**: `CONSERVADOR_50K` (`+$6,217.6`, `p_1ret12 = 64.9%`, `p10 = -$6,344.7`), `EQUILIBRADO_150K` (`+$5,297.9`, `p10 = -$17,140.0`), `MAX_FLUJO_150K` (`+$6,644.3`, `p10 = -$40,493.2`).
     - En estres doble (`contraida_60` aplicado encima de `A5_HOLDOUT`, equivalente a `~1.93 R/mes`): **`CONSERVADOR_50K` (`+$2,145.1`) y `EQUILIBRADO_150K` (`+$187.5`) siguen positivos**, mientras que `MAX_FLUJO_150K` (`-$4,631.0`) se vuelve negativo por el alto costo acumulado de `$214.25` en `E10`.
2. **`TERMINAL` (`34` sesiones `2026-10-01..2026-11-17`):**
   - Cartera M1: **`+10.213 R/mes` (`+16.54 R` totales)**, `Sharpe = 3.29`, `dd_R = -5.12 R`, `Calmar = 23.92`, **`100.0%` meses positivos**.
   - **Ticks sellados `C:\EdgeLab\sellado` (`31` sesiones `20261001..20261113`, sin `20261007`, `101` trades emparejados):** M1 = **`+15.37 R`** vs ticks sellados reales = **`+19.89 R`**, **`corr_diaria = 0.9949`**.
   - **Replay calendario en `TERMINAL` (`34` dias habiles):**
     - `CONSERVADOR_50K`: `5` evals compradas (`-$391.65`), `0` quemadas, `+$9,192.97` balance abierto en evals.
     - `EQUILIBRADO_150K`: `6` evals compradas (`-$1,285.50`), `0` quemadas, **`1` fondeada** (`+$345.55`), `+$33,933.27` en evals activas.
     - `MAX_FLUJO_150K`: `10` evals compradas (`-$2,142.50`), `0` quemadas, `1` aprobada, `+$73,223.19` en evals activas.

![Etapa B Calibracion Ticks K30 y Holdout](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/deploy_etapaB_calibracion_ticks_y_holdout.png)

---

## 4. Etapa C — Multi-Prop Firm (`16` planes aptos + `4` arquitecturas Multi-Firma)

Resultados completos en [etapaC_multiprop_comparativa.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/etapaC_multiprop_comparativa.csv) y [etapaC_arquitecturas_multifirma.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/etapaC_arquitecturas_multifirma.csv).

- **Excluidas por `algo_policy="prohibido"`:** **Apex** y **AlphaFutures** (prohiben bots/algos totalmente automatizados).
- **Top planes individuales bajo `REP contraida_60`:**
  1. `MP_Topstep_NoAct_150K` (`monthly $229`, `$0` act.): `+$16,724.8`, `11.85` retiros/12m, `p10 = -$27,022.0` (`ratio = 0.619`). *(Nota operativa: sin API en Live Account; XFA OK)*
  2. `MP_Tradeify_150K_promo` (`one_time $258.30`, `$0` act.): `+$16,068.7`, `9.46` retiros/12m, `p10 = -$25,909.3` (`ratio = 0.620`), soporta NT8 (`>10s` regla: nuestro portafolio cumple `100% > 10s`).
  3. **`MP_Topstep_NoAct_50K`** (`monthly $95`, `$0` act.): **`+$13,549.5`**, `14.51` retiros/12m, **`p10 = -$9,533.6` (`ratio = 1.421`)** — **unico plan que se mantiene positivo tanto en `real_100` (`+$8,562.4`) como en estres doble `A5_HOLDOUT contraida_60` (`+$2,592.3`)**.
  4. `MP_LucidFlex_150K_promo` (`$214.25`): `+$11,807.2` en `REP 60%` (`+$4,579.2` en `A5_HOLDOUT real_100`).
  5. `MP_LucidFlex_50K_promo` (`$95.20`): `+$6,420.0` en `REP 60%` (`+$3,432.8` en `A5_HOLDOUT real_100`).
- **Impacto de reglas restrictivas reales verificadas en Etapa C:**
  - **Intraday trailing en funded (`TakeProfitTrader PRO 150K`):** en `REP 60%` cae a apenas `+$2,702.6` (`p10 = -$34,134.0`) y en `A5_HOLDOUT real_100` pierde **`-$5,329.5`**, demostrando que pasar de EOD a `intraday_trailing` destruye el margen frente a drawdowns intradia.
  - **Precios retail sin promo (`FundedNext 150K $490`):** pierde dinero incluso en `REP 60%` (`-$4,378.6`), haciendo obligatorio operar solo con promociones/cupones (`~$80–$275`).
  - **Activacion cara + consistency en funded (`Bulenox Opt2 $498 act.` y `MFFU Pro 150K`):** `MFFU Pro` cae a `-$208.6` en `REP 60%` y Bulenox requiere `p10 = -$18,085.1` para `+$5,723.0`.
- **Arquitecturas Multi-Firma Sincronizadas (`N=3000`, mismo `j_seq` de mercado):**
  - En `REP real_100`: `MP1 Duo` `+$66,035.6` (`p10 = -$34,657.6`), `MP2 Trio` `+$80,293.8`, `MP3 Chico 50K` `+$40,161.0` (`p10 = -$21,210.1`), `MP4 Quartet` `+$120,406.4`.
  - En `A5_HOLDOUT real_100`: las `4` arquitecturas permanecen positivas (`MP3 50K +$8,445.3`, `MP1 Duo +$10,092.2`, `MP2 Trio +$9,186.7`, `MP4 Quartet +$14,444.1`), pero en doble estres `A5_HOLDOUT contraida_60` se vuelven negativas (`-$2.5k` a `-$15.7k`) si se combinan cuentas `150K` agresivas en paralelo. **Conclusion operativa:** escalar multi-firma solo con `MP3 (50K)` o `MP1 Duo (LucidFlex + Tradeify Select Flex)` manteniendo el tamano `50K/equilibrado` hasta validar fondeo real.

![Etapa C Comparativa Multi-Prop Firm y Frontera](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsync_deploy_multiprop_20261122/deploy_etapaC_multiprop_frontera.png)
