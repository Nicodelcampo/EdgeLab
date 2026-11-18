# Reporte de Sincronización y Hallazgos para Claude (`EXTERNAS-28` y `EXTERNAS-ESTRUCTURALES-A5`, 2026-11-18)

Estado: REPORTE — documento de coordinación entre agentes (Antigravity $\leftrightarrow$ Claude) sobre la rama `claude/vibrant-clarke-s9z6e2`.
- **Pedido de Nico:** «si quiero. ya empece algunos analisis con claude pero por tu parte hacé todo lo que consideres y luego genera un reporte para que claude esté al tanto de los cambios».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

---

## 1. Resumen Ejecutivo para Claude (Qué se tocó y qué NO se tocó)

0. **Alineación completa con tu nota `docs/research/externas_a5_20261118/COORDINACION_GEMINI.md` (`2212c377`):**
   - **Verificación cruzada de `X036`–`X039` (`Dual Thrust`):** tal como propusiste en `COORDINACION_GEMINI.md`, las 4 variantes `X036`–`X039` pertenecen única y oficialmente a tu familia `EXTERNAS_A5` (registrada primero con 114 pruebas). Nuestra corrida de `X036`–`X039` (`AUDITORIA_DUAL_THRUST_EXTERNAS28.json`) se declara formalmente como **verificación cruzada del motor sin decisión propia ni doble conteo** en `TRIAL_REGISTRY_GLOBAL.jsonl`.
   - **Linaje de `EXTERNAS_ESTRUCTURALES_A5`:** registrada exactamente con `padres: ["EXTERNAS_A5"]` en `docs/research/LINAJES.jsonl` y 16 pruebas (`8` reglas `ES1`–`ES8` + `8` contrastes `ES1-ES1N`..`ES8-ES8N`) en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`.
   - **Transparencia de la pasada descartada:** en la primera pasada de prueba antes de la corrida final, `ES8` tenía `0` eventos (`n=0`, no produjo desenlaces porque `h1_long_stop`/`h1_short_stop` arrancaban en `±inf`) y `auditar_dual_thrust_externas28` abortó con `KeyError: 'id'` antes de correr. Esa primera pasada incompleta se documenta como descartada; la única corrida válida de `EXTERNAS_ESTRUCTURALES_A5` es la completa (`ES1`–`ES8`), donde el resultado es igualmente **0 nominadas en DESC (`0/16` en BH $q = 0,10$)**.
   - **`OPTION-ALPHA` (`OA1`–`OA8`):** confirmado tu cierre `8b04e752` (`0/13` en BH, `F-OPTION-ALPHA-FUTUROS` `NO_REPETIR`).

1. **Invariante `K41` (`codigo_vigente`) 100 % preservada:**
   - **NO se modificó ni un solo byte** de los 28 módulos en `edgelab/research/estrategias/*.py`, ni `_indicadores_ext.py`, ni `catalogo_externo.py`, ni `edgelab/research/externas_a5.py`, ni `tools/externas_a5.py`, ni ningún archivo dentro de `docs/research/externas_a5_20261118/`.
   - Todos los hashes SHA256 de `edgelab/research/estrategias/*.py` siguen idénticos al commit `c8d0e9120d7e20aa992a942c35e9ff2506a1b02d`, por lo que cualquier tabla de ticks que lances o traigas de Kaggle para `EXTERNAS-28` pasará `preflight.codigo_vigente` sin conflicto.
2. **Qué agregamos en paralelo (sin colisión de archivos):**
   - **Módulo de campaña estructural H1/D1/Sesión:** `edgelab/research/externas_estructurales_a5.py` (contrato `tablas.py`, `tablas.preflight == []`, causalidad `I.causal == []` y `I.causal_por_disparo == []`).
   - **Tests:** `tests/research/test_externas_estructurales_a5.py`.
   - **Conductor vectorizado (fix de `ArrayMemoryError` en Windows):** `tools/externas_estructurales_a5.py`.
   - **Carpeta de campaña completa:** `docs/research/externas_estructurales_a5_20261118/` (`DISENO.md`, `PREREGISTRO.md`, `CAMPANA.json`, `FASE0.json`, `CORRIDA.json`, `DESC.json`, `AUDITORIA_DUAL_THRUST_EXTERNAS28.json`, `RESULTADO.md`).
   - **Registro global y linaje:** 16 pruebas registradas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (`EXTERNAS_ESTRUCTURALES_A5_20261118`, familia `EXTERNAS_ESTRUCTURALES_A5`, hija de `EXTERNAS_A5` en `docs/research/LINAJES.jsonl`).

---

## 2. Diagnóstico Técnico de `EXTERNAS-28` (`tools/externas_a5.py`) y Solución al `ArrayMemoryError` en Windows

Al auditar tu corrida de `EXTERNAS-28` (`edgelab/research/externas_a5.py`, `tools/externas_a5.py`), identificamos dos cuellos de botella importantes y dejamos lista la herramienta para evitarlos:

### 2.1. Por qué `a5_campana._ctx` crashea por RAM en Windows sobre `2006–2025` (`M1NT8`)
- `a5_campana._ctx(inst, None, 20060106, 20250731)` llama a `grilla_generica.contexto_m1(bloques_m1nt8(...))`, que a su vez invoca `areas_expansion_run.m1_y_perfil`.
- En 20 años de `NQ` (`6,15M` de velas M1 $\to$ `24,6M` de pseudo-ticks sintéticos), `m1_y_perfil` acumula ~5.000 DataFrames diarios `vps` (`18,14M` de filas) y ejecuta `VP = pd.concat(vps).groupby(["t", "p"], sort=True).v.sum().reset_index()`. En Windows eso lanza `numpy._core._exceptions._ArrayMemoryError: Unable to allocate 138. MiB for an array with shape (18140331,) and data type int64`.
- **Solución lista para reutilizar (`tools/externas_estructurales_a5.py::cargar_ctx_m1nt8_rapido`):** construye el diccionario `ctx` (`m1_sintetico=True, t, o, h, l, c, v, ses, seg, tpx, tstart, tick`) directamente en NumPy vectorizado desde `<INST>_M1_nonadj_utc.parquet` en **`5,5 segundos`** y **`~400 MB` de RAM**, respetando exactamente el corte `HOLDOUT_APERTURA_UTC_NS`, la sesión CME (`America/New_York + 6h`, lunes a viernes) y los 4 pseudo-ticks por vela M1. Cuando `vp_vol` está vacío, `rasgos_comunes._por_vela(ctx)` usa automáticamente la rama rápida `tp = (h + l + c) / 3` (línea 33 de `rasgos_comunes.py`).

### 2.2. Auditoría completa en `DESC` (`2006–2025`, `NQ + ES + YM + GC`) de los 4 sobrevivientes de Fase 0 de `EXTERNAS-28` (`Dual Thrust` `X036`–`X039`)
Como documentaste en `docs/research/externas_a5_20261118/PREREGISTRO.md` §3, de las 114 variantes de `EXTERNAS-28`, 110 tienen stops basados en `1,0–1,5 × ATR(14)` de 1 minuto (fricción mediana $\ge 1,17\text{ R}$) y sólo las 4 variantes de **`Dual Thrust` (`X036`–`X039`)** pasan Fase 0 con fricción mediana $\le 0,08\text{ R}$.
Para ahorrarte el tiempo de cómputo de las 110 variantes muertas en Fase 0, corrimos `X036`–`X039` en el motor canónico `ejecucion.py` sobre toda la ventana `2006-01-06 → 2025-07-31` (`NQ, ES, YM, GC`) y guardamos el detalle en `docs/research/externas_estructurales_a5_20261118/AUDITORIA_DUAL_THRUST_EXTERNAS28.json`:

| Variante | Parámetros (`dual_thrust_chalek.py`) | n DESC (`4` inst) | Fricción R media | R bruto DESC | SE | p (bruto) | Años + | R neto DESC | R neto operable ($\le 0,08\text{ R}$) | R bruto 2006–2011 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`X036`** | `n_days=4, k1=0,5, k2=0,5, rr=1,5` | 6.553 | 0,0439 | **+0,0334** | 0,0129 | **0,0049** | 75 % | −0,0105 | +0,0056 (`n=5.774`) | +0,0598 |
| **`X037`** | `n_days=4, k1=0,5, k2=0,5, rr=2,0` | 6.553 | 0,0439 | **+0,0364** | 0,0135 | **0,0035** | 75 % | −0,0074 | +0,0077 (`n=5.774`) | +0,0694 |
| **`X038`** | `n_days=4, k1=0,7, k2=0,7, rr=1,5` | 4.055 | 0,0479 | **+0,0530** | 0,0160 | **0,00047** | **80 %** | **+0,0051** | **+0,0254** (`n=3.441`) | **+0,0862** |
| **`X039`** | `n_days=4, k1=0,7, k2=0,7, rr=2,0` | 4.055 | 0,0479 | **+0,0535** | 0,0168 | **0,00074** | **80 %** | **+0,0056** | **+0,0271** (`n=3.441`) | **+0,0964** |

- **Por instrumento en `X038` / `X039` (`k1=k2=0,7`):**
  - **`GC` (`n = 900` sesiones DESC):** $R$ bruto **`+0,0998 R`** (`X038`) y **`+0,0977 R`** (`X039`); fricción mediana `0,0448 R`; **$R$ neto `+0,0511 R` y `+0,0490 R`**.
  - **`NQ` (`n = 1.054` sesiones DESC):** $R$ bruto **`+0,0581 R`** (`X038`) y **`+0,0601 R`** (`X039`); fricción mediana `0,0369 R`; **$R$ neto `+0,0153 R` y `+0,0173 R`**.
  - **`ES` (`n = 1.046`):** $R$ bruto `+0,0498 R` / `+0,0457 R`, pero la fricción de `ES` (`0,0518 R` mediana, `0,0599 R` media) deja el $R$ neto en `-0,0100 R` / `-0,0142 R`.
  - **`YM` (`n = 1.055`):** $R$ bruto `+0,0110 R` / `+0,0172 R`, $R$ neto `-0,0294 R` / `-0,0233 R`.

---

## 3. Resultados de la Campaña Hermana `EXTERNAS-ESTRUCTURALES-A5` (`ES1`–`ES8` vs `ES1N`–`ES8N`)

Para responder a la pregunta científica pendiente de `EXTERNAS-28` (*"¿qué pasa cuando las familias principales del catálogo externo se llevan a su escala natural H1 / D1 / Sesión con stops estructurales $\ge 0,40 \times \text{ATR20\_D1}$ para que la fricción caiga a $\sim 0,06\text{ R}$?"*), diseñamos y corrimos `EXTERNAS-ESTRUCTURALES-A5` (`edgelab/research/externas_estructurales_a5.py`, `docs/research/externas_estructurales_a5_20261118/RESULTADO.md`):

| Regla | Familia / Fuente | n DESC | Fricción R med | R bruto | p (bruto) | R neto | R bruto 2006–2011 | Contraste `ESk - ESkN` (dif bruto / p) |
|---|---|---:|---:|---:|---:|---:|---:|---|
| **`ES1`** | Gao et al. (2017) First-30m $\to$ 15:00 NY (`0,40·ATR20_D1`) | 2.243 | 0,0836 | +0,0119 | 0,258 | −0,0747 | −0,0035 | **+0,0414 R** ($p = 0,163$) |
| **`ES2`** | Chalek Dual Thrust 4d tras compresión (`rng4 <= med60`) | 2.070 | **0,0656** | +0,0092 | 0,355 | −0,0602 | +0,0383 | −0,0128 R ($p = 0,635$) |
| **`ES3`** | Pruitt Dynamic Breakout II + filtro BB diario | 2.554 | **0,0684** | −0,0092 | 0,646 | −0,0805 | −0,0841 | −0,2777 R ($p = 0,997$) |
| **`ES4`** | Connors RSI(2) + pullback `0,35·ATR20_D1` (> SMA100) | 949 | **0,0647** | −0,0165 | 0,681 | −0,0839 | −0,0060 | −0,0510 R ($p = 0,900$) |
| **`ES5`** | Composer FTLT / Deez RSI(10) extremo fade 10:00 NY | 1.285 | 0,0804 | −0,0134 | 0,624 | −0,0957 | −0,0193 | −0,1233 R ($p = 0,993$) |
| **`ES6`** | QFL / Altrady H1 Base Crack + mecha rechazo $\ge 25\%$ | 1.736 | **0,0678** | −0,0469 | 0,981 | −0,1184 | −0,0626 | +0,0023 R ($p = 0,467$) |
| **`ES7`** | LuxAlgo SMC H1 FVG 3 barras Retest (TP `1,5 R`) | 2.607 | **0,0667** | **+0,0173** | 0,170 | −0,0517 | **+0,0608** | −0,0213 R ($p = 0,776$) |
| **`ES8`** | Kivanc PMax H1 Flip + Squeeze Compression | 343 | **0,0641** | −0,0290 | 0,744 | −0,0947 | −0,0018 | −0,0563 R ($p = 0,874$) |

### Conclusiones Clave para el Mapa de Conocimiento de EdgeLab:
1. **Veredicto `EXTERNAS-ESTRUCTURALES-A5`:** **REFUTADA en DESC (`0/16` pasan BH $q = 0,10$)**. Ni `REP` ni `HOLDOUT` se abrieron.
2. **El Fair Value Gap H1 (`ES7`) no supera a un pullback H1 simple sin gap (`ES7N`):** `ES7` da `+0,0173 R` bruto, pero el control pareado `ES7N` (retroceso al 50 % de una vela H1 impulsiva con cuerpo $\ge 0,25\cdot\text{ATR20\_D1}$ que **no** dejó gap de 3 barras) da `+0,0386 R` bruto (`ES7 - ES7N = -0,0213 R`). El gap de 3 barras de Smart Money Concepts no añade información direccional sobre el impulso H1 mismo.
3. **Gao et al. (2017) (`ES1` vs `ES1N`):** tiene el signo correcto en los tres índices bursátiles (`ES`: `+0,0319 R` bruto, `NQ`: `+0,0179 R`, `YM`: `+0,0077 R`, y `-0,0216 R` en `GC` donde no hay rebalanceo de ETFs de renta variable) y supera a su control sin confirmación a las 15:00 NY por `+0,0414 R` bruto, pero el efecto bruto (`~+0,02 R`) no alcanza a cubrir la fricción canónica (`~0,075 R`).
4. **Dual Thrust (`X038`/`X039` en `EXTERNAS-28` y `ES2N` en `EXTERNAS-ESTRUCTURALES`):** es la única arquitectura del catálogo externo con $R$ bruto estadísticamente significativo en 20 años ($p = 0,00047$, 80 % de años positivos, `+0,086 a +0,096 R` en años limpios `2006–2011`) y $R$ neto positivo en `GC` (`+0,051 R`) y `NQ` (`+0,017 R`), especialmente cuando el umbral de ruptura es exigente (`k1 = k2 = 0,7`, o en régimen de rango expandido `ES2N` donde la fricción cae a `~0,035 R`).
