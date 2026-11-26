# Barrido de Paridad OOS contra Gráfica del Vendedor (`FUNDEDSYNCSTACK`, 2021-10 -> 2026-04)

- **Estado:** VIGENTE
- **Fecha:** 2026-11-21
- **Familia / módulo:** `fundedsyncstack`
- **North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`

## 1. Objetivo y protocolo científico
Alinear y medir con rigor morfológico la paridad de las **14 curvas publicadas** de `FUNDEDSYNCSTACK` (`A·A1, A·E, A·S, A·T, A·V, A·W, A·Z, B·A20, B·C, B·F, B·O, B·P, B·Q, B·R`) frente a la captura original del vendedor ([vendedor_original.jpg](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/vendedor_original.jpg)), separando estrictamente:

1. **`il_fabrica` (intocable):** Implementación 1:1 extraída de `FUNDEDSYNCSTACK5.dll`.
2. **`vendedor_calibrado` (perfil separado):** Adaptaciones de fricción, serie de contrato o parámetros promovidas **únicamente** cuando cumplen la puerta doble:
   - Mejora `score_pre >= +0.03` en ajuste in-sample (**2022–2024**).
   - Valida fuera de muestra (**2025–2026** OOS) con `r_nivel_25_26 >= 0.80` y sin degradar `r_nivel_25_26` en más de `0.05`.
   - Estricto respeto de HOLDOUT-A4 (`< 2026-10-01`).

## 2. Re-vectorización limpia v2 y desambiguación cromática
La extracción previa mostraba saltos verticales entre pares de color cercano (`B·O`/`B·C`, `B·P`/`B·R`) y omitía `A·T` y `B·R`. El extractor [vectorizar_vendedor.py](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/edgelab/research/fundedsyncstack/vectorizar_vendedor.py) calibrado sobre la imagen original `1024×576` (grilla horizontal `P10` en `y_zero ≈ 384.5 px`, `y_step ≈ 82.25 px`) obtuvo **5.040 puntos limpios en 14 tracks** ([curvas_extraidas_v2_limpias.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/curvas_extraidas_v2_limpias.csv)), con cero saltos internos (`|Δy| <= 0.14` grilla):

- **Desambiguación 2×2 `A·TEAL` (`resolver_identidad_teal`):**
  - `A·T` vs `TEAL_UPPER`: `score_pre = 0.772` (`nonadj`) / `0.796` (`backadj`), `r_nivel_22_24 = 0.968` / `0.981`, `r_nivel_25_26 = 0.909` / `0.917`, `r_total = 0.977` / `0.980`.
  - `A·S` vs `TEAL_LOWER`: `score_pre = 0.523`, `r_nivel_22_24 = 0.617`, `r_delta_22_24 = 0.382`, `r_nivel_25_26 = 0.915`, `r_total = 0.859`.
  - Queda confirmado sin ambigüedad: **`T -> TEAL_UPPER`** y **`S -> TEAL_LOWER`**.

## 3. Resultados del barrido ordenado (Etapas 0 -> 1 -> 2)
Script reproducible: [fundedsync_parity_sweep.py](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/tools/fundedsync_parity_sweep.py)  
Módulo de evaluación y perfiles: [paridad_vendedor.py](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/edgelab/research/fundedsyncstack/paridad_vendedor.py)

| Módulo | Base (`il_fabrica`) | `r_total` Base | Perfil `vendedor_calibrado` | `score_pre` (`Base -> Final`) | `r_nivel 22-24` | `r_delta 22-24` | `r_nivel 25-26` (OOS) | `r_total` Final | Estado OOS |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `P` | `backadj_usd_dll` | `0.990` | `param={}` (`backadj`, `usd_dll`) | `0.8617` | `0.982` | `0.681` | `0.948` | **`0.990`** | Paridad alta fábrica |
| `O` | `nonadj_bruto_1cto` | `0.942` | `use_rth_range_filter=False` (`nonadj`, `bruto_1cto`) | `0.7246 -> 0.8640` | `0.957` | `0.725` | `0.965` | **`0.986`** | **Promovido OOS** (`+0.1394`) |
| `A20` | `nonadj_nt8_1cto` | `0.981` | `param={}` (`nonadj`, `nt8_1cto`) | `0.8441` | `0.968` | `0.658` | `0.913` | **`0.981`** | Paridad alta fábrica |
| `T` | `backadj_edge_1cto` | `0.980` | `param={}` (`backadj`, `edge_1cto`) | `0.7957` | `0.981` | `0.518` | `0.917` | **`0.980`** | Paridad alta fábrica |
| `V` | `nonadj_bruto_1cto` | `0.976` | `param={}` (`nonadj`, `bruto_1cto`) | `0.7295` | `0.971` | `0.367` | `0.955` | **`0.976`** | Paridad alta fábrica |
| `Q` | `backadj_usd_dll` | `0.963` | `param={}` (`backadj`, `usd_dll`) | `0.5513` | `0.878` | `0.062` | `0.933` | **`0.963`** | Paridad alta fábrica |
| `W` | `nonadj_bruto_1cto` | `0.934` | `use_cooldown_filter=False` (`nonadj`, `bruto_1cto`) | `0.3866 -> 0.4352` | `0.938` | `-0.319` | `0.860` | **`0.953`** | **Promovido OOS** (`+0.157` post) |
| `A1` | `nonadj_bruto_1cto` | `0.939` | `param={}` (`nonadj`, `bruto_1cto`) | `0.3926` (`edge=0.4100`) | `0.686` | `-0.047` | `0.843` | **`0.939`** | Paridad alta fábrica |
| `R` | `nonadj_bruto_1cto` | `0.830` | `param={}` (`nonadj`, `bruto_1cto`) | `0.5382` | `0.603` | `0.442` | `0.965` | **`0.830`** | Paridad alta fábrica |
| `S` | `nonadj_bruto_1cto` | `0.859` | `st_mult=3.0, use_eod_close=False` (`nonadj`, `bruto_1cto`) | `0.5230 -> 0.6150` | `0.731` | `0.441` | `0.876` | **`0.824`** | **Promovido OOS** (`+0.092`) |
| `C` | `nonadj_edge_1cto` | `0.525` | `minimum_gap_points=10.0` (`nonadj`, `edge_1cto`) | `0.6582 -> 0.7310` | `0.853` | `0.548` | `0.920` | **`0.694`** | **Promovido OOS** (`+0.169` tot) |
| `E` | `backadj_bruto_1cto` | `0.801` | `param={}` (`backadj`, `bruto_1cto`) | `0.5897` | `0.835` | `0.222` | `0.637` | `0.801` | Rango plano 25-26; rechazo OOS a `sl40_tp60` |
| `Z` | `backadj_edge_1cto` | `0.750` | `param={}` (`backadj`, `edge_1cto`) | `0.3243` | `0.123` | `0.626` | `0.554` | `0.750` | Sin datos limpios pre-2024 (`n_pre=27`) |
| `F` | `nonadj_bruto_1cto` | `0.597` | `param={}` (`nonadj`, `bruto_1cto`) | `0.4804` | `0.540` | `0.390` | `0.754` | `0.597` | Parcial: requiere delta tick real (`0.765` OOS con `risk175`) |

## 4. Hallazgos clave y control anti-sobreajuste (OOS)
1. **Curvas del vendedor = standalone sin bloqueo Lucid50K+news 2026:** La variante `lucid50k_news` derrumbó la correlación (`S: 0.523 -> 0.085`, `V: 0.729 -> 0.414`, `W: 0.387 -> -0.621`), confirmando ejecución independiente por módulo. En **`P` y `Q`** el vendedor muestra sizing dinámico real (`usd_dll`: `P=0.990`, `Q=0.963` vs `Q_usd_dll_nt8=-0.751`).
2. **Descarte explícito de sobreajuste en `W` y `E`:**
   - En `W`, `use_vwap_slope_filter=True` (`0.5` ticks) elevó artificialmente `score_pre` a `0.8054` en 2022–2024 pero colapsó en 2025–2026 a **`r_nivel_25_26 = -0.845`** (`r_total = -0.189`). La puerta OOS lo descartó y promovió **`use_cooldown_filter=False`**, elevando OOS de `0.703 -> 0.860`.
   - En `E`, `stop_points=40, target_points=60` subió `score_pre` a `0.648`, pero colapsó en 2025–2026 (`0.108`), quedando descartado. En `A·E`, el tramo 2025–2026 oscila solo `0.04` unidades de grilla (`~3 px` de meseta plana), amplificando ruido JPEG en Pearson local pese al calce visual (`r_total = 0.801`).
3. **Brecha residual en `F` (`FabioOrb`):** En Etapa 2, `disable_delta_filter=True, max_initial_risk_points=175.0` elevó `score_pre` de `0.480 -> 0.710` y `r_total` a `0.697`, quedando en `r_nivel_25_26 = 0.765` (bajo la cota estricta `0.80`). No se promueve a `VENDOR_PARITY_OVERRIDES`; su brecha 2025–2026 es estructural por ausencia de delta bid/ask tick-level en el parquet M1.

## 5. Entregables gráficos y datos exportados
- Foto 1 (vendedor limpia v2): [foto_1_vendedor_vectorizada_v2.png](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/foto_1_vendedor_vectorizada_v2.png)
- Foto 2 (EdgeLab perfil calibrado OOS): [foto_2_edgelab_paridad_calibrada.png](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/foto_2_edgelab_paridad_calibrada.png)
- Panel comparativo 14 módulos: [comparativa_panel_14_modulos_paridad_20261121.png](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/comparativa_panel_14_modulos_paridad_20261121.png)
- Verificación de vectorización v2: [verificacion_vectorizacion_v2_20261121.png](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/verificacion_vectorizacion_v2_20261121.png)
- CSVs del barrido: [sweep_etapa0_baseline.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/sweep_etapa0_baseline.csv), [sweep_etapa1_ejecucion.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/sweep_etapa1_ejecucion.csv), [sweep_etapa2_parametros.csv](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/sweep_etapa2_parametros.csv), [resumen_paridad_final.json](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-fundedsync/docs/research/fundedsyncstack_20261115/paridad_vendedor/resumen_paridad_final.json)
