# Resultado Exhaustivo y Manual de Referencia: Atlas de Contexto Causal Común y Vetos Estructurales en $R$ (2026-11-04)

Estado: VIGENTE con reservas — sus efectos confirmados resultaron fricción en R (`contexto_bruto_neto/RESULTADO_BRUTO_NETO.md`); vale el módulo, el arreglo de JForex y el método.

- **Pre-registro:** [`docs/research/programa_r_20261103/PREREGISTRO_CONTEXTO_Y_VETOS_R_20261104.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/PREREGISTRO_CONTEXTO_Y_VETOS_R_20261104.md)
- **Módulo causal reutilizable (`L1/L2`):** [`edgelab/research/contexto_comun.py`](file:///e:/EdgeLab-port/edgelab/research/contexto_comun.py)
- **Integración en el embudo de grillas:** [`edgelab/research/grilla_generica.py`](file:///e:/EdgeLab-port/edgelab/research/grilla_generica.py), [`edgelab/research/embudo_runners.py`](file:///e:/EdgeLab-port/edgelab/research/embudo_runners.py), [`tools/kaggle_grilla/embudo_main.py`](file:///e:/EdgeLab-port/tools/kaggle_grilla/embudo_main.py)
- **Paridad de ejecución JForex ↔ Python:** [`nt8_tools/jforex/EdgeLabU1Cruzado.java`](file:///e:/EdgeLab-port/nt8_tools/jforex/EdgeLabU1Cruzado.java) (`maxDuracionMin = 240`, `cierreNY = "16:59"` ET)
- **Suite de tests de truncado, bordes de sesión y paridad:** [`tests/research/test_contexto_comun.py`](file:///e:/EdgeLab-port/tests/research/test_contexto_comun.py) (`7 passed in 5.92s`)
- **Conductor del Atlas (local + Kaggle) y meta-análisis:** [`tools/atlas_contexto_r.py`](file:///e:/EdgeLab-port/tools/atlas_contexto_r.py)
- **Datos crudos completos (`10.871` líneas JSON):** [`docs/research/programa_r_20261103/contexto_marginales/RESULTADO.json`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/contexto_marginales/RESULTADO.json)
- **Linaje y presupuesto global de ensayos:** `ATLAS_CONTEXTO_VETOS_R` en [`docs/research/LINAJES.jsonl`](file:///e:/EdgeLab-port/docs/research/LINAJES.jsonl) y `programa_r/contexto_vetos_r/20261104` en [`docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`](file:///e:/EdgeLab-port/docs/research/TRIAL_REGISTRY_GLOBAL.jsonl)

---

## 1. Resumen Ejecutivo de la Sesión

En esta sesión se diseñó, implementó, certificó causalmente y ejecutó a escala completa (local + Kaggle sobre 135 campañas en $R$) el **Atlas de Contexto Causal Común y Vetos Estructurales en $R$**, con el objetivo de:
1. Estandarizar una capa universal de **contexto causal común** y **vetos estructurales orientados por el lado de la operación** aplicable a cualquier familia de EdgeLab sin modificar su lógica interna ni inflar la multiplicidad de su grilla.
2. Evitar el sobreajuste sobre las 11 estrategias de `Estabilidad_mensual_en_R.html` (que cuentan con sólo 15 meses de datos y fueron seleccionadas mirando la réplica `REP`) **estimando primero cada efecto en el Atlas global de 69 clusters independientes `(familia_base, activo)`** (`DESC` Ago 2025 – Mar 2026 y `REP` Abr 2026 – Sep 2026) mediante meta-análisis de efectos aleatorios DerSimonian-Laird separado por mecanismo (`GLOBAL`, `REVERSION`, `CONTINUACION`).
3. Igualar la ejecución de JForex con el simulador de Python agregando el corte por duración máxima (`240` minutos) y el cierre diario de sesión (`16:59 ET`).

### Hallazgos Principales Confirmados
1. **Ejecución universal (`S3 + T3`) tras colapsar pares `Futuro + CFD` (`K = 13` clusters independientes):**
   - El **stop estructural ancho (`ejecución.stop=S3`)** confirma con el mayor tamaño de efecto del repositorio: **`+0,1235R` en `DESC`** ($z = +6,51$, $p < 10^{-6}$, BH $q \le 0,10$) y **`+0,1057R` en `REP`** ($z = +4,08$, $p = 4,4 \times 10^{-5}$), con **13/13 ($100\,\%$) clusters positivos** tanto en `DESC` como en `REP`.
   - El **objetivo lejano (`ejecución.objetivo=T3`)** es positivo en **13/13 ($100\,\%$) clusters** (`DESC +0,0569R`, `REP +0,0456R`), mientras que acercar el objetivo (**`ejecución.objetivo=T1`**) resta en **13/13 ($100\,\%$) clusters** (`DESC -0,0630R`, `REP -0,0448R`).
2. **Seis efectos de contexto común y vetos confirmados en el Atlas (`BH q <= 0,10` en `DESC` + $p_{\text{uni}} < 0,05$ y mismo signo en `REP`):**
   - **`ctx_atr_rel=bajo` ($\text{ATR}_{14}$ intradía en el tercil inferior $< P_{33}$ de las últimas 20 sesiones):** resta **`-0,0793R` en `DESC`** ($z = -4,29$, $p = 1,8 \times 10^{-5}$, $90,0\,\%$ clusters $-$) y **`-0,0722R` en `REP`** ($z = -3,31$, $p_{\text{uni}} = 0,0005$, $84,3\,\%$ clusters $-$). Perjudica tanto a `REVERSION` (`DESC -0,0874R`, `REP -0,0623R`) como a `CONTINUACION` (`DESC -0,0755R`, `REP -0,0812R`).
   - **`ctx_vol_rel=bajo` (volumen de la vela de decisión $< P_{33}$ de las últimas 20 sesiones):** resta **`-0,0698R` en `DESC`** ($z = -3,71$, $p = 0,00020$, $82,6\,\%$ clusters $-$) y **`-0,0631R` en `REP`** ($z = -2,82$, $p_{\text{uni}} = 0,0024$, $84,4\,\%$ clusters $-$).
   - **`ctx_atr_rel=alto` ($\text{ATR}_{14} > P_{67}$) y `ctx_vol_rel=alto` ($V_k > P_{67}$):** suman **`+0,0380R` / `+0,0278R`** ($p_{\text{uni}} = 0,0269$) y **`+0,0289R` / `+0,0240R`** ($p_{\text{uni}} = 0,0436$) respectivamente.
   - **`ctx_hora_ny=ny_manana_0930_12` (`09:30–12:00 ET` con DST):** suma **`+0,0487R` en `DESC` / `+0,0402R` en `REP`** en `GLOBAL` ($p_{\text{uni}} = 0,0071$) y **`+0,0765R` en `DESC` / `+0,0585R` en `REP`** en `REVERSION` ($p_{\text{uni}} = 0,0078$).
   - **Descubrimiento clave — De «Muro» a «Imán Estructural» en Reversión (`veto_muro=vetado`):** La hipótesis a priori postulaba que tener un nivel estructural de sesión (`VWAP`, `OR30_H/L`, `ONH/ONL`, `PDH/PDL`) entre la entrada $e + 0,25R$ y $0,75\,\text{TP}$ frenaría la operación como un «muro». El Atlas demostró exactamente lo opuesto en `REVERSION` ($K = 31$ clusters): **cuando hay un nivel estructural de sesión delante hacia $T_3$, el rendimiento sube `+0,0883R` en `DESC` ($z = +4,93$, $p = 10^{-6}$, $87,1\,\%$ clusters $+$) y `+0,0732R` en `REP` ($z = +3,21$, $p_{\text{uni}} = 0,0007$, $77,4\,\%$ clusters $+$) focus**, mientras que operar reversión sin ningún nivel de equilibrio delante (`veto_muro=pasa`) resta (`-0,0339R` en `DESC`, `-0,0220R` en `REP`). En reversión a la media, `VWAP`, `OR30` y los extremos previos no son muros sino **imanes de equilibrio hacia los cuales revierte el precio**.
3. **Demostración empírica de la defensa anti-sobreajuste en las 11 reglas:**
   - Evaluado directamente sobre las 11 reglas (`N = 1.161` operaciones), el filtro `veto_vol_diaria_baja` parecía atractivo (`+0,0311R`, `LOMO 14/14`, $p_{\text{nulo}} = 0,0670$). Sin embargo, en el Atlas de 69 clusters su efecto real fue **cero** (`DESC -0,0071R`, $p = 0,71$; `REP +0,0014R`, $p = 0,95$). Sin el filtro previo del Atlas, se habría sobreajustado la cartera a un artefacto muestral de las 11 reglas.
   - El único candidato que pasa simultáneamente el Atlas (`DESC` y `REP`), el $\text{MDE}_{80\%}$ de la cartera ($+0,0699R > +0,0677R$) y las 3 compuertas secundarias sobre las 11 reglas (`8/11` reglas mejoradas, `LOMO 14/14` meses positivos, nulo mensual emparejado `EXP-004b` $p = 0,0195 < 0,05$) es **`atlas_veto_sin_iman_estructural`** (exigir imán estructural hacia $T_3$), que eleva la cartera de **`+0,1235R` a `+0,1934R`** (`+0,0847R` en `DESC`, `+0,0574R` en `REP`, `0` meses rojos). Por tener signo opuesto a la dirección pre-registrada de `veto_muro`, **queda congelado hoy sin tocar las reglas en producción y se valida prospectivamente desde noviembre 2026 (`202611+`)**.

---

## 2. Correcciones de Hecho y Decisiones de Diseño Adoptadas

Antes de escribir código o correr campañas, se auditaron el repositorio, el corpus SSRN (`corpus/ssrn/cerebro/`) y el historial de experimentos (`LEDGER_EXPERIMENTOS.md`, `PATRONES.md`, `ANTIPATRONES.md`), incorporando seis correcciones metodológicas críticas:

1. **Árbol y rama canónicos:** Todo el trabajo se ejecutó sobre `e:\EdgeLab-port` (rama `gemini/filtros-20261104`), donde residen las 135 campañas en $R$ (`docs/research/campanas_r_20261102/`), el módulo `edgelab/research/regimen_sesion.py` y el fix de cola $t$ de Student ya implementado en `edgelab/research/embudo_estadistica.py`.
2. **Prohibición de usar octubre 2026 (`202610`) como confirmación ciega:** La tabla `Estabilidad_mensual_en_R.html` ya expuso los resultados de octubre 2026 (`202610`) para las 11 reglas. Usarlo como «confirmación ciega» constituiría *data snooping* (`AP-001`). En consecuencia:
   - El análisis se restringió estrictamente a `DESC` (`2025-08-05 .. 2026-03-31`) y `REP` (`2026-04-01 .. 2026-09-25`, 14 meses).
   - Toda confirmación prospectiva limpia queda fijada desde **noviembre de 2026 (`202611+`)**.
3. **Secuencia anti-sobreajuste (Atlas de 69 clusters $\to$ 11 reglas):** Como las 11 reglas fueron elegidas tras observar su desempeño en `REP`, evaluar filtros directamente sobre ellas introduce sesgo de selección. Se invirtió el flujo: cada etiqueta se estima primero en el Atlas completo de campañas en $R$ (`STAGE_MARGINALES`) y sólo lo confirmado en `DESC` (con BH $q \le 0,10$) y `REP` ($p_{\text{uni}} < 0,05$, mismo signo) puede promoverse a las 11 reglas.
4. **Independencia de clusters y separación por mecanismo:**
   - Las campañas `Futuro` y `CFD` del mismo activo subyacente y familia base (p. ej. `CVGAP-NQ` y `CVGAP-CFD-NQ`, o variantes `-R` / `-C` de la misma familia sobre el mismo activo) **se colapsan promediando sus efectos dentro del cluster `(familia_base, activo)`** antes del meta-análisis DerSimonian-Laird, evitando inflar artificialmente $\sqrt{K}$.
   - El meta-análisis se reporta estratificado en `GLOBAL` ($K \le 69$), `REVERSION` ($K \le 31$) y `CONTINUACION` ($K \le 29$).
5. **Reemplazo de umbrales mágicos por cuantiles móviles causales de 20 sesiones:** Se eliminaron todos los umbrales fijos arbitrarios (`ER60 > 0,60`, `1,5R`, etc.) y se reemplazaron por **terciles (`P33 / P67`) y decil (`P90`) móviles de las 20 sesiones cerradas previas del propio instrumento** (mínimo 5 sesiones cerradas), con **40 días calendario de calentamiento (`calentamiento_dias=40`)** al inicio de cada ventana (`DESC`, `REP`, `HOLDOUT`).
6. **Descubrimiento de la discrepancia de duración JForex vs Python:** En `edgelab/research/grilla_comun.py` (`MAX_VELAS = 240`), toda operación en Python se cierra a las 4 horas o al borde de sesión (`fin_sesion`), mientras que `nt8_tools/jforex/EdgeLabU1Cruzado.java` sólo tenía `SL` y `TP`. Las pérdidas nocturnas de `> 4h` observadas en JForex provenían de esta falta de paridad y se corrigieron directamente en el ejecutor Java.

---

## 3. Implementación Técnica Realizada

### 3.1. Paridad JForex ↔ Python ([`nt8_tools/jforex/EdgeLabU1Cruzado.java`](file:///e:/EdgeLab-port/nt8_tools/jforex/EdgeLabU1Cruzado.java))
Se agregaron dos parámetros configurables y el control de cierre forzado en cada barra M1 tanto del activo de señal como del activo de ejecución:
- `@Configurable("Duración máxima operación (min, 0=sin tope)") public int maxDuracionMin = 240;`
- `@Configurable("Hora cierre diario NY (HH:MM ET, vacío=sin cierre)") public String cierreNY = "16:59";`
- Método `proximoCierreMs(long fillMs)`: convierte `fillMs` a `ZonedDateTime` en `America/New_York` (respetando horario de verano de EE.UU.) y calcula el instante exacto del próximo `16:59 ET`.
- Método `cierreForzado(long ms)`: verifica si `ms - fillTimeMs >= maxDuracionMin * 60_000L` o `ms >= deadlineCierreMs`, e invoca `ordenViva.close()` registrando el motivo (`TOPE_DURACION` o `CIERRE_SESION_NY`).

### 3.2. Módulo Causal [`edgelab/research/contexto_comun.py`](file:///e:/EdgeLab-port/edgelab/research/contexto_comun.py)
Calcula una sola vez por instrumento y serie M1 los vectores de contexto (`por_vela`) y etiqueta cualquier lote de operaciones simuladas (`etiquetar_operaciones`) según la vela de decisión $k$ y el lado $s \in \{+1, -1\}$:

1. **Indicadores reiniciados por sesión CME (`atr_sesion` y `vwap_sesion`):**
   - En lugar de `ind.atr(h, l, c, 14)` (que contamina las primeras 14 barras de la sesión con el salto entre el cierre de las 17:00 ET y la reapertura de las 18:00 ET o después del fin de semana), `atr_sesion(h, l, c, ses, n=14)` reinicia el True Range (`TR = h - l`) y el suavizado de Wilder exactamente cuando `ses[i] != ses[i - 1]`.
   - `vwap_sesion(h, l, c, v, ses)` reinicia los acumuladores $\sum p_t v_t$ y $\sum v_t$ en cada cambio de sesión.
2. **Niveles causales de sesión sin lookahead (`_niveles_sesion`):**
   - `pdh[i]`, `pdl[i]`, `pdc[i]`, `rango_prev[i]`: máximo, mínimo, cierre y rango de la sesión CME inmediata anterior completamente cerrada.
   - `or30_h[i]`, `or30_l[i]`: máximo y mínimo de `09:30 .. 09:59 ET` de la sesión actual, expuestos como `NaN` hasta las `10:00 ET` inclusive (`min_ny >= 600`) para garantizar cero lookahead durante la formación del rango de apertura.
   - `onh[i]`, `onl[i]`: máximo y mínimo acumulados hasta la barra $i$ durante el tramo nocturno/europeo (`min_ny < 570`, antes de `09:30 ET`), congelados a partir de las `09:30 ET`.
3. **Cuantiles móviles causales de 20 sesiones (`_umbrales_sesiones_previas`):**
   - Para cada sesión $S$, toma los valores observados en las hasta **20 sesiones cerradas anteriores** $[S-20, S-1]$ (exigiendo al menos `MIN_SESIONES_UMBRAL = 5` sesiones previas cerradas) y calcula los terciles $P_{33}, P_{67}$ y el decil $P_{90}$.
4. **Las 7 variables de contexto común orientadas por lado $s$:**
   - `ctx_vol_diaria`: tercil del rango de la sesión previa `rango_prev` (`baja`, `media`, `alta`, `sin_hist`).
   - `ctx_atr_rel`: tercil de `atr14_ses[k]` respecto de las 20 sesiones previas (`bajo`, `medio`, `alto`, `sin_hist`).
   - `ctx_vol_rel`: tercil del volumen `v[k]` respecto de las 20 sesiones previas (`bajo`, `medio`, `alto`, `sin_hist`).
   - `ctx_hora_ny`: franja horaria en `America/New_York` con DST (`overnight_18_03`, `londres_03_0930`, `ny_manana_0930_12`, `ny_tarde_12_16`, `cierre_16_17`, `fuera`).
   - `ctx_tendencia_favor`: pendiente de $\text{EMA}_{48}$ en M5 ($\approx 4\text{h}$) normalizada por `atr14_ses` y multiplicada por el lado $s$ (`favor_fuerte` $> +0,25$, `contra_fuerte` $< -0,25$, `neutra`).
   - `ctx_vwap_favor`: posición del cierre respecto de `vwap_sesion` orientada por el lado $s$ (`favor_vwap`, `contra_vwap`).
   - `ctx_eficiencia_contra`: Efficiency Ratio de Kaufman a 60 minutos ($\text{ER}_{60} = |C_k - C_{k-60}| / \sum_{j=k-59}^k |C_j - C_{j-1}|$) cuando el desplazamiento de 60 minutos va en contra del lado $s$, clasificado por los cuantiles de 20 sesiones (`contra_alta` $> P_{67}$, `contra_media` $\in [P_{33}, P_{67}]$, `favor_o_baja`).
5. **Los 4 vetos estructurales binarios (`pasa` / `vetado`):**
   - `veto_horizonte`: `vetado` si los minutos hábiles restantes hasta el fin de sesión o fin de semana son $< 30\text{ min}$ o el alcance esperado $\text{ATR}_{14}(k)\cdot\sqrt{\min(T_{\text{rest}}, 240)}$ no cubre la distancia al objetivo $|tp - e|$.
   - `veto_muro`: `vetado` si alguno de los niveles estructurales ya conocidos en $k$ (`VWAP`, `OR30_H/L` si `min_ny >= 600`, `ONH/ONL` si `min_ny >= 570`, `PDH/PDL`) se ubica en la dirección de la operación entre $e + 0,25R$ y $e + 0,75\,|tp - e|$.
   - `veto_huida`: `vetado` si el movimiento de 60 minutos va en contra del lado $s$ con $\text{ER}_{60}(k) > P_{90}$ (decil superior de las 20 sesiones previas) **y** el cuerpo de la vela $k$ va en contra del lado $s$ superando $P_{67}$ del $\text{ATR}_{14}$.
   - `veto_liquidez_macro`: `vetado` si la vela $k$ cae en `18:00–02:00 ET` o dentro de $\pm 5\text{ min}$ de las ventanas macro `08:25–08:35 ET` y `09:55–10:05 ET`.

### 3.3. Calentamiento de 40 Días y Etapa `MARGINALES` Acelerada con Numba
- En [`tools/kaggle_grilla/embudo_main.py`](file:///e:/EdgeLab-port/tools/kaggle_grilla/embudo_main.py) se modificó `_cargar_tramo` para cargar siempre `CALENTAMIENTO_DIAS = 40` días calendario antes de `desde` en `ctx["calentamiento"]`. En [`edgelab/research/grilla_generica.py`](file:///e:/EdgeLab-port/edgelab/research/grilla_generica.py), `correr` concatena `calentamiento + tramo` antes de calcular `contexto_comun.por_vela`, garantizando que el primer día de `DESC`, `REP` o `HOLDOUT` ya tenga las 20 sesiones previas completas, y filtra los disparos para conservar exclusivamente aquellos con `t[k] >= t_inicio_tramo`.
- En [`tools/atlas_contexto_r.py`](file:///e:/EdgeLab-port/tools/atlas_contexto_r.py) se implementó `_bloque_m1_nb` (compilado con `@njit(cache=True)`) que reduce en un factor $> 20\times$ el tiempo de agregación de 100 millones de ticks a barras M1 en las campañas que sólo requieren señales M1.

### 3.4. Certificación Causal ([`tests/research/test_contexto_comun.py`](file:///e:/EdgeLab-port/tests/research/test_contexto_comun.py))
Los 7 tests automatizados verifican:
1. **Invarianza al truncado futuro de `por_vela` y `etiquetar_operaciones`:** alterar precios/volúmenes en $t > k$ (multiplicar por $5\times$ o sumar $+500$ puntos) no modifica ni un bit de los indicadores ni de las 11 etiquetas en $\le k$.
2. **Reinicio de `atr_sesion` y `vwap_sesion` en bordes CME:** un gap nocturno de $+1.000$ puntos no contamina el $\text{ATR}_{14}$ de la nueva sesión.
3. **Horario de verano (DST) en `America/New_York`:** `13:30 UTC` es `09:30 ET` en julio (EDT, `min_ny = 570`) y `08:30 ET` en enero (EST, `min_ny = 510`).
4. **Orientación por lado (`s = +1` vs `s = -1`):** en una misma vela $k$, el largo y el corto reciben etiquetas opuestas de `ctx_tendencia_favor`, `ctx_vwap_favor`, `ctx_eficiencia_contra`, `veto_muro` y `veto_huida`.
5. **Ausencia de lookahead en `onh/onl`, `or30_h/l` y `veto_muro`:** un nivel formado a las `11:00 ET` jamás afecta una operación tomada a las `08:00 ET` ni a las `09:40 ET`.
6. **Equivalencia con calentamiento (`ctx["calentamiento"]`):** correr un tramo con 40 días en `ctx["calentamiento"]` produce exactamente las mismas etiquetas y cuantiles que correr la serie histórica continua y recortar al tramo.
7. **Integración con `ET.ejecutar("MARGINALES", ...)` y paridad JForex (`EdgeLabU1Cruzado.java`).**

---

## 4. Resultados Completos del Atlas (`135` Campañas en $R$, `69` Clusters Independientes)

### 4.1. Potencia Pre-Registrada y Efecto Mínimo Detectable ($\text{MDE}_{80\%}$, $\alpha = 0,05$ unilateral)

| Ámbito de evaluación | Muestra efectiva | $\text{SE}(\Delta R)$ | Umbral $\alpha=0,05$ ($1,645 \cdot \text{SE}$) | $\text{MDE}_{80\%}$ ($2,487 \cdot \text{SE}$) |
|---|---:|---:|---:|---:|
| **11 reglas (`DESC + REP`, diferencia directa `pasa` vs `vetado`)** | $N = 1.161$ ops | $0,0790R$ | $+0,1299R$ | **$+0,1963R$** |
| **11 reglas (`DESC + REP`, mejora neta de cartera $\bar{R}_{\text{pasa}} - \bar{R}_{\text{base}}$)** | $N = 1.161$ ops | $0,0272R$ | $+0,0447R$ | **$+0,0677R$** |
| **11 reglas (`REP` sola, mejora neta de cartera)** | $N = 555$ ops | $0,0417R$ | $+0,0686R$ | **$+0,1036R$** |
| **Meta-análisis `GLOBAL` (referencia $K = 20$ clusters)** | $K \ge 20$ clusters | $0,0283R$ | $\pm 0,0465R$ | **$\pm 0,0703R$** |
| **Meta-análisis por mecanismo (`REVERSION` / `CONTINUACION`, ref. $K = 10$)** | $K \ge 10$ clusters | $0,0400R$ | $\pm 0,0658R$ | **$\pm 0,0995R$** |

---

### 4.2. Meta-Análisis de Ejecución tras Colapsar `Futuro + CFD` (`meta_ejecucion_colapsado_por_mecanismo`)

| Estrato | Etiqueta de ejecución | $K$ | Efecto `DESC` ($R$) | $z_{\text{DESC}}$ | $p_{\text{bil}}$ `DESC` | BH `DESC` | Efecto `REP` ($R$) | $z_{\text{REP}}$ | $p_{\text{bil}}$ `REP` | Mismo signo (`DESC`/`REP`) | Confirmada |
|---|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|:---:|
| **`GLOBAL`** | **`ejecución.stop=S3` (stop estructural ancho)** | **13** | **$+0,1235R$** | **$+6,51$** | **$< 10^{-6}$** | **Sí** | **$+0,1057R$** | **$+4,08$** | **$0,000044$** | **$100,0\,\% / 100,0\,\%$** | **Sí** |
| `GLOBAL` | `ejecución.objetivo=T3` (objetivo lejano) | 13 | $+0,0569R$ | $+2,59$ | $0,009541$ | No | $+0,0456R$ | $+1,58$ | $0,114176$ | $100,0\,\% / 100,0\,\%$ | Consistente (13/13) |
| `GLOBAL` | `ejecución.objetivo=T1` (objetivo cercano) | 13 | $-0,0630R$ | $-2,57$ | $0,010196$ | No | $-0,0448R$ | $-1,45$ | $0,147551$ | $100,0\,\% / 100,0\,\%$ | Resta en 13/13 |
| `GLOBAL` | `ejecución.entrada=RET20` (retroceso 20 %) | 13 | $+0,0403R$ | $+1,96$ | $0,050015$ | No | $+0,0323R$ | $+1,14$ | $0,254448$ | $76,9\,\% / 84,6\,\%$ | No |
| `GLOBAL` | `ejecución.entrada=VOL_VUELTA` | 13 | $+0,0425R$ | $+1,96$ | $0,050582$ | No | $+0,0243R$ | $+0,78$ | $0,433285$ | $84,6\,\% / 69,2\,\%$ | No |
| `GLOBAL` | `ejecución.stop=S2` (stop intermedio) | 16 | $-0,0577R$ | $-1,92$ | $0,055221$ | No | $-0,0268R$ | $-0,93$ | $0,354836$ | $81,2\,\% / 81,2\,\%$ | No |
| `GLOBAL` | `ejecución.entrada=E1A` (entrada a mercado) | 13 | $-0,0403R$ | $-1,72$ | $0,085844$ | No | $-0,0194R$ | $-0,68$ | $0,496427$ | $84,6\,\% / 84,6\,\%$ | No |
| **`REVERSION`** | **`ejecución.stop=S3` (stop estructural ancho)** | **12** | **$+0,1077R$** | **$+5,31$** | **$< 10^{-6}$** | **Sí** | **$+0,0920R$** | **$+3,68$** | **$0,000235$** | **$100,0\,\% / 100,0\,\%$** | **Sí** |
| `REVERSION` | `ejecución.objetivo=T1` (objetivo cercano) | 12 | $-0,0539R$ | $-2,05$ | $0,040040$ | No | $-0,0402R$ | $-1,28$ | $0,201327$ | $100,0\,\% / 100,0\,\%$ | Resta en 12/12 |
| `REVERSION` | `ejecución.objetivo=T3` (objetivo lejano) | 12 | $+0,0488R$ | $+2,03$ | $0,042805$ | No | $+0,0386R$ | $+1,29$ | $0,196570$ | $100,0\,\% / 100,0\,\%$ | Consistente (12/12) |
| `CONTINUACION` | `ejecución.objetivo=1.0` | 10 | $-0,0320R$ | $-1,06$ | $0,287332$ | No | $-0,0486R$ | $-1,43$ | $0,153091$ | $90,0\,\% / 80,0\,\%$ | No |

---

### 4.3. Tabla Completa del Meta-Análisis de Contexto y Vetos — Estrato `GLOBAL` ($30$ niveles, $K \le 69$ clusters)

| # | Etiqueta | $K$ | Efecto `DESC` ($R$) | $z_{\text{DESC}}$ | $p_{\text{bil}}$ `DESC` | BH $q \le 0,10$ | Efecto `REP` ($R$) | $z_{\text{REP}}$ | $p_{\text{bil}}$ `REP` | $p_{\text{uni}}$ `REP` | Mismo signo (`DESC`/`REP`) | Confirmada |
|---:|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|:---:|
| 1 | **`veto_muro=vetado` (imán de sesión delante)** | 69 | **$+0,0499R$** | $+4,52$ | $0,000006$ | **Sí** | **$+0,0363R$** | $+2,76$ | $0,005757$ | **$0,0029$** | $73,9\,\% / 73,9\,\%$ | **Sí (imán)** |
| 2 | **`ctx_atr_rel=bajo` ($\text{ATR}_{14} < P_{33}$)** | 50 | **$-0,0793R$** | $-4,29$ | $0,000018$ | **Sí** | **$-0,0722R$** | $-3,31$ | $0,000944$ | **$0,0005$** | $90,0\,\% / 84,3\,\%$ | **Sí** |
| 3 | **`ctx_vol_rel=bajo` ($V_k < P_{33}$)** | 46 | **$-0,0698R$** | $-3,71$ | $0,000205$ | **Sí** | **$-0,0631R$** | $-2,82$ | $0,004807$ | **$0,0024$** | $82,6\,\% / 84,4\,\%$ | **Sí** |
| 4 | **`ctx_hora_ny=ny_manana_0930_12`** | 56 | **$+0,0487R$** | $+3,39$ | $0,000688$ | **Sí** | **$+0,0402R$** | $+2,45$ | $0,014247$ | **$0,0071$** | $76,8\,\% / 66,1\,\%$ | **Sí** |
| 5 | **`ctx_atr_rel=alto` ($\text{ATR}_{14} > P_{67}$)** | 69 | **$+0,0380R$** | $+3,11$ | $0,001846$ | **Sí** | **$+0,0278R$** | $+1,93$ | $0,053836$ | **$0,0269$** | $82,6\,\% / 77,9\,\%$ | **Sí** |
| 6 | **`ctx_vol_rel=alto` ($V_k > P_{67}$)** | 63 | **$+0,0289R$** | $+2,41$ | $0,016110$ | **Sí** | **$+0,0240R$** | $+1,71$ | $0,087272$ | **$0,0436$** | $74,6\,\% / 73,8\,\%$ | **Sí** |
| 7 | `veto_muro=pasa` (sin nivel de sesión delante) | 65 | $-0,0296R$ | $-2,35$ | $0,018876$ | Sí | $-0,0194R$ | $-1,29$ | $0,198567$ | $0,0993$ | $72,3\,\% / 73,8\,\%$ | No |
| 8 | `veto_liquidez_macro=vetado` | 38 | $-0,0366R$ | $-2,01$ | $0,044485$ | No | $-0,0050R$ | $-0,23$ | $0,818533$ | $0,4093$ | $71,1\,\% / 43,6\,\%$ | No |
| 9 | `ctx_hora_ny=overnight_18_03` | 36 | $-0,0335R$ | $-1,86$ | $0,062944$ | No | $-0,0039R$ | $-0,18$ | $0,859212$ | $0,4296$ | $72,2\,\% / 58,3\,\%$ | No |
| 10 | `ctx_eficiencia_contra=contra_media` | 64 | $-0,0274R$ | $-1,80$ | $0,072566$ | No | $-0,0163R$ | $-0,89$ | $0,371909$ | $0,1860$ | $57,8\,\% / 54,7\,\%$ | No |
| 11 | `ctx_eficiencia_contra=contra_alta` | 58 | $-0,0276R$ | $-1,71$ | $0,087183$ | No | $-0,0005R$ | $-0,03$ | $0,979738$ | $0,4899$ | $62,1\,\% / 60,3\,\%$ | No |
| 12 | `ctx_hora_ny=cierre_16_17` | 25 | $-0,0430R$ | $-1,67$ | $0,094252$ | No | $-0,0267R$ | $-0,86$ | $0,391201$ | $0,1956$ | $52,0\,\% / 60,0\,\%$ | No |
| 13 | `veto_huida=vetado` ($\text{ER}_{60} > P_{90}$ en contra) | 45 | $-0,0357R$ | $-1,62$ | $0,104676$ | No | $-0,0155R$ | $-0,53$ | $0,595386$ | $0,2977$ | $64,4\,\% / 50,0\,\%$ | No |
| 14 | `ctx_tendencia_favor=contra_fuerte` | 69 | $+0,0205R$ | $+1,62$ | $0,105217$ | No | $-0,0075R$ | $-0,52$ | $0,600784$ | $0,6996$ | $63,8\,\% / 58,0\,\%$ | No |
| 15 | `ctx_atr_rel=medio` | 65 | $-0,0206R$ | $-1,38$ | $0,168350$ | No | $-0,0057R$ | $-0,33$ | $0,741868$ | $0,3709$ | $60,0\,\% / 48,4\,\%$ | No |
| 16 | `veto_horizonte=vetado` | 25 | $-0,0313R$ | $-1,24$ | $0,213334$ | No | $-0,0143R$ | $-0,46$ | $0,644466$ | $0,3222$ | $52,0\,\% / 52,0\,\%$ | No |
| 17 | `ctx_tendencia_favor=neutra` | 69 | $-0,0186R$ | $-1,18$ | $0,236746$ | No | $-0,0192R$ | $-1,01$ | $0,313695$ | $0,1568$ | $63,8\,\% / 65,7\,\%$ | No |
| 18 | `ctx_eficiencia_contra=favor_o_baja` | 67 | $+0,0120R$ | $+1,08$ | $0,281063$ | No | $+0,0029R$ | $+0,23$ | $0,819860$ | $0,4099$ | $64,2\,\% / 55,2\,\%$ | No |
| 19 | `ctx_vol_diaria=alta` | 69 | $+0,0190R$ | $+1,04$ | $0,297500$ | No | $-0,0210R$ | $-1,06$ | $0,290088$ | $0,8550$ | $72,5\,\% / 39,1\,\%$ | No |
| 20 | `ctx_vol_diaria=media` | 69 | $-0,0181R$ | $-0,90$ | $0,367499$ | No | $+0,0096R$ | $+0,43$ | $0,668006$ | $0,6660$ | $60,9\,\% / 57,4\,\%$ | No |
| 21 | `veto_liquidez_macro=pasa` | 66 | $+0,0097R$ | $+0,86$ | $0,391918$ | No | $+0,0014R$ | $+0,11$ | $0,915705$ | $0,4579$ | $51,5\,\% / 45,5\,\%$ | No |
| 22 | `ctx_hora_ny=ny_tarde_12_16` | 48 | $+0,0098R$ | $+0,69$ | $0,488637$ | No | $+0,0080R$ | $+0,46$ | $0,644712$ | $0,3224$ | $60,4\,\% / 58,1\,\%$ | No |
| 23 | `ctx_tendencia_favor=favor_fuerte` | 69 | $-0,0065R$ | $-0,54$ | $0,589658$ | No | $+0,0169R$ | $+1,18$ | $0,238604$ | $0,8807$ | $53,6\,\% / 69,6\,\%$ | No |
| 24 | `ctx_vol_diaria=baja` | 69 | $-0,0071R$ | $-0,38$ | $0,707900$ | No | $+0,0014R$ | $+0,07$ | $0,947799$ | $0,5261$ | $65,2\,\% / 41,2\,\%$ | No |
| 25 | `ctx_hora_ny=londres_03_0930` | 47 | $+0,0063R$ | $+0,36$ | $0,717141$ | No | $-0,0125R$ | $-0,58$ | $0,560147$ | $0,7199$ | $46,8\,\% / 55,3\,\%$ | No |
| 26 | `veto_huida=pasa` | 69 | $+0,0038R$ | $+0,35$ | $0,729093$ | No | $+0,0019R$ | $+0,15$ | $0,879150$ | $0,4396$ | $62,3\,\% / 59,4\,\%$ | No |
| 27 | `ctx_vwap_favor=favor_vwap` | 67 | $+0,0019R$ | $+0,17$ | $0,866388$ | No | $+0,0011R$ | $+0,09$ | $0,930395$ | $0,4652$ | $56,7\,\% / 55,2\,\%$ | No |
| 28 | `ctx_vol_rel=medio` | 60 | $+0,0019R$ | $+0,12$ | $0,904700$ | No | $+0,0065R$ | $+0,34$ | $0,733206$ | $0,3666$ | $46,7\,\% / 60,0\,\%$ | No |
| 29 | `ctx_vwap_favor=contra_vwap` | 69 | $-0,0013R$ | $-0,11$ | $0,911433$ | No | $-0,0069R$ | $-0,51$ | $0,612379$ | $0,3062$ | $56,5\,\% / 55,1\,\%$ | No |
| 30 | `veto_horizonte=pasa` | 69 | $+0,0001R$ | $+0,01$ | $0,993953$ | No | $-0,0001R$ | $-0,00$ | $0,996684$ | $0,5017$ | $34,8\,\% / 37,7\,\%$ | No |

---

### 4.4. Tabla Completa del Meta-Análisis — Estrato `REVERSION` ($30$ niveles, $K \le 31$ clusters)

| # | Etiqueta | $K$ | Efecto `DESC` ($R$) | $z_{\text{DESC}}$ | $p_{\text{bil}}$ `DESC` | BH $q \le 0,10$ | Efecto `REP` ($R$) | $z_{\text{REP}}$ | $p_{\text{bil}}$ `REP` | $p_{\text{uni}}$ `REP` | Mismo signo (`DESC`/`REP`) | Confirmada |
|---:|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|:---:|
| 1 | **`veto_muro=vetado` (imán de sesión delante)** | 31 | **$+0,0883R$** | $+4,93$ | $0,000001$ | **Sí** | **$+0,0732R$** | $+3,21$ | $0,001322$ | **$0,0007$** | $87,1\,\% / 77,4\,\%$ | **Sí (imán)** |
| 2 | **`ctx_hora_ny=ny_manana_0930_12`** | 31 | **$+0,0765R$** | $+3,69$ | $0,000220$ | **Sí** | **$+0,0585R$** | $+2,42$ | $0,015585$ | **$0,0078$** | $90,3\,\% / 67,7\,\%$ | **Sí** |
| 3 | **`ctx_atr_rel=bajo` ($\text{ATR}_{14} < P_{33}$)** | 27 | **$-0,0874R$** | $-3,66$ | $0,000249$ | **Sí** | **$-0,0623R$** | $-2,13$ | $0,033164$ | **$0,0166$** | $88,9\,\% / 81,5\,\%$ | **Sí** |
| 4 | **`ctx_vol_rel=bajo` ($V_k < P_{33}$)** | 27 | **$-0,0717R$** | $-3,01$ | $0,002630$ | **Sí** | **$-0,0579R$** | $-2,02$ | $0,042887$ | **$0,0214$** | $77,8\,\% / 77,8\,\%$ | **Sí** |
| 5 | **`ctx_atr_rel=alto` ($\text{ATR}_{14} > P_{67}$)** | 31 | **$+0,0483R$** | $+2,53$ | $0,011400$ | **Sí** | **$+0,0414R$** | $+1,78$ | $0,075166$ | **$0,0376$** | $83,9\,\% / 77,4\,\%$ | **Sí** |
| 6 | `ctx_vol_rel=alto` ($V_k > P_{67}$) | 31 | $+0,0439R$ | $+2,30$ | $0,021312$ | No | $+0,0356R$ | $+1,54$ | $0,123145$ | $0,0616$ | $74,2\,\% / 61,3\,\%$ | No |
| 7 | `veto_muro=pasa` (sin imán delante) | 31 | $-0,0339R$ | $-1,85$ | $0,063662$ | No | $-0,0220R$ | $-1,00$ | $0,316368$ | $0,1582$ | $87,1\,\% / 77,4\,\%$ | No |
| 8 | `ctx_hora_ny=overnight_18_03` | 23 | $-0,0401R$ | $-1,74$ | $0,081220$ | No | $+0,0009R$ | $+0,03$ | $0,975198$ | $0,5124$ | $73,9\,\% / 43,5\,\%$ | No |
| 9 | `veto_liquidez_macro=vetado` | 23 | $-0,0394R$ | $-1,69$ | $0,091290$ | No | $-0,0004R$ | $-0,01$ | $0,989769$ | $0,4949$ | $73,9\,\% / 47,8\,\%$ | No |
| 10 | `ctx_eficiencia_contra=contra_alta` | 30 | $-0,0328R$ | $-1,42$ | $0,156228$ | No | $-0,0005R$ | $-0,02$ | $0,985250$ | $0,4926$ | $73,3\,\% / 63,3\,\%$ | No |
| 11 | `veto_huida=vetado` | 26 | $-0,0382R$ | $-1,36$ | $0,174265$ | No | $+0,0317R$ | $+0,94$ | $0,348808$ | $0,8256$ | $73,1\,\% / 53,8\,\%$ | No |
| 12 | `ctx_tendencia_favor=contra_fuerte` | 31 | $+0,0234R$ | $+1,19$ | $0,233543$ | No | $+0,0037R$ | $+0,16$ | $0,875603$ | $0,4378$ | $67,7\,\% / 45,2\,\%$ | No |
| 13 | `ctx_atr_rel=medio` | 30 | $-0,0217R$ | $-1,02$ | $0,305469$ | No | $-0,0216R$ | $-0,86$ | $0,387169$ | $0,1936$ | $63,3\,\% / 51,6\,\%$ | No |
| 14 | `veto_liquidez_macro=pasa` | 31 | $+0,0188R$ | $+1,01$ | $0,310582$ | No | $+0,0055R$ | $+0,24$ | $0,808450$ | $0,4042$ | $61,3\,\% / 41,9\,\%$ | No |
| 15 | `ctx_tendencia_favor=neutra` | 31 | $-0,0201R$ | $-0,94$ | $0,348040$ | No | $-0,0163R$ | $-0,61$ | $0,539876$ | $0,2699$ | $67,7\,\% / 71,0\,\%$ | No |
| 16 | `ctx_hora_ny=londres_03_0930` | 27 | $+0,0147R$ | $+0,69$ | $0,491367$ | No | $-0,0023R$ | $-0,08$ | $0,933117$ | $0,5334$ | $48,1\,\% / 48,1\,\%$ | No |
| 17 | `ctx_vol_diaria=alta` | 31 | $+0,0208R$ | $+0,68$ | $0,497880$ | No | $-0,0100R$ | $-0,28$ | $0,781410$ | $0,6093$ | $77,4\,\% / 25,8\,\%$ | No |
| 18 | `ctx_eficiencia_contra=favor_o_baja` | 29 | $+0,0121R$ | $+0,65$ | $0,515687$ | No | $+0,0097R$ | $+0,43$ | $0,668423$ | $0,3342$ | $65,5\,\% / 69,0\,\%$ | No |
| 19 | `ctx_vol_diaria=media` | 31 | $-0,0155R$ | $-0,46$ | $0,648554$ | No | $+0,0000R$ | $+0,00$ | $0,999168$ | $0,5004$ | $61,3\,\% / 58,1\,\%$ | No |
| 20 | `ctx_vwap_favor=favor_vwap` | 29 | $+0,0083R$ | $+0,44$ | $0,661126$ | No | $-0,0122R$ | $-0,54$ | $0,590461$ | $0,7048$ | $55,2\,\% / 48,3\,\%$ | No |
| 21 | `veto_huida=pasa` | 31 | $+0,0078R$ | $+0,42$ | $0,674509$ | No | $+0,0038R$ | $+0,17$ | $0,864599$ | $0,4323$ | $77,4\,\% / 48,4\,\%$ | No |
| 22 | `ctx_vwap_favor=contra_vwap` | 31 | $-0,0064R$ | $-0,34$ | $0,735279$ | No | $+0,0111R$ | $+0,48$ | $0,633765$ | $0,6831$ | $54,8\,\% / 48,4\,\%$ | No |
| 23 | `ctx_vol_diaria=baja` | 31 | $-0,0108R$ | $-0,33$ | $0,738670$ | No | $+0,0076R$ | $+0,20$ | $0,840197$ | $0,5799$ | $71,0\,\% / 41,9\,\%$ | No |
| 24 | `ctx_hora_ny=cierre_16_17` | 21 | $-0,0074R$ | $-0,25$ | $0,802756$ | No | $+0,0015R$ | $+0,04$ | $0,966580$ | $0,5167$ | $42,9\,\% / 47,6\,\%$ | No |
| 25 | `ctx_vol_rel=medio` | 29 | $+0,0044R$ | $+0,21$ | $0,835803$ | No | $+0,0123R$ | $+0,48$ | $0,632519$ | $0,3163$ | $44,8\,\% / 72,4\,\%$ | No |
| 26 | `ctx_eficiencia_contra=contra_media` | 31 | $-0,0039R$ | $-0,19$ | $0,852647$ | No | $-0,0279R$ | $-1,08$ | $0,279668$ | $0,1398$ | $45,2\,\% / 64,5\,\%$ | No |
| 27 | `ctx_tendencia_favor=favor_fuerte` | 31 | $-0,0031R$ | $-0,15$ | $0,881334$ | No | $+0,0153R$ | $+0,61$ | $0,544657$ | $0,7277$ | $58,1\,\% / 67,7\,\%$ | No |
| 28 | `ctx_hora_ny=ny_tarde_12_16` | 31 | $-0,0019R$ | $-0,09$ | $0,926433$ | No | $-0,0005R$ | $-0,02$ | $0,984781$ | $0,4924$ | $51,6\,\% / 44,8\,\%$ | No |
| 29 | `veto_horizonte=pasa` | 31 | $-0,0003R$ | $-0,01$ | $0,989146$ | No | $-0,0003R$ | $-0,01$ | $0,988018$ | $0,4940$ | $41,9\,\% / 45,2\,\%$ | No |
| 30 | `veto_horizonte=vetado` | 21 | $+0,0003R$ | $+0,01$ | $0,992183$ | No | $+0,0107R$ | $+0,29$ | $0,769558$ | $0,3848$ | $57,1\,\% / 52,4\,\%$ | No |

---

### 4.5. Tabla Completa del Meta-Análisis — Estrato `CONTINUACION` ($28$ niveles, $K \le 29$ clusters)

| # | Etiqueta | $K$ | Efecto `DESC` ($R$) | $z_{\text{DESC}}$ | $p_{\text{bil}}$ `DESC` | BH $q \le 0,10$ | Efecto `REP` ($R$) | $z_{\text{REP}}$ | $p_{\text{bil}}$ `REP` | $p_{\text{uni}}$ `REP` | Mismo signo (`DESC`/`REP`) | Confirmada |
|---:|---|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|:---:|
| 1 | `ctx_eficiencia_contra=contra_media` | 24 | $-0,0650R$ | $-2,41$ | $0,016132$ | No | $+0,0059R$ | $+0,19$ | $0,850926$ | $0,5745$ | $70,8\,\% / 58,3\,\%$ | No |
| 2 | **`ctx_atr_rel=bajo` ($\text{ATR}_{14} < P_{33}$)** | 19 | **$-0,0755R$** | $-2,27$ | $0,023443$ | No | **$-0,0812R$** | $-2,38$ | $0,017553$ | **$0,0088$** | $94,7\,\% / 90,0\,\%$ | Consistente |
| 3 | **`veto_huida=vetado` ($\text{ER}_{60} > P_{90}$ en contra)** | 12 | **$-0,0805R$** | $-1,94$ | $0,051891$ | No | **$-0,1403R$** | $-2,52$ | $0,011567$ | **$0,0058$** | $66,7\,\% / 66,7\,\%$ | Consistente |
| 4 | `ctx_atr_rel=alto` ($\text{ATR}_{14} > P_{67}$) | 29 | $+0,0370R$ | $+1,91$ | $0,055668$ | No | $+0,0259R$ | $+1,14$ | $0,254392$ | $0,1272$ | $82,8\,\% / 78,6\,\%$ | No |
| 5 | **`ctx_vol_rel=bajo` ($V_k < P_{33}$)** | 17 | **$-0,0622R$** | $-1,88$ | $0,060075$ | No | **$-0,0654R$** | $-1,78$ | $0,074537$ | **$0,0373$** | $94,1\,\% / 94,1\,\%$ | Consistente |
| 6 | `ctx_tendencia_favor=contra_fuerte` | 29 | $+0,0314R$ | $+1,47$ | $0,141628$ | No | $-0,0197R$ | $-0,86$ | $0,387200$ | $0,8064$ | $62,1\,\% / 65,5\,\%$ | No |
| 7 | `ctx_eficiencia_contra=contra_alta` | 19 | $-0,0428R$ | $-1,38$ | $0,166913$ | No | $-0,0055R$ | $-0,15$ | $0,879091$ | $0,4395$ | $63,2\,\% / 63,2\,\%$ | No |
| 8 | `ctx_eficiencia_contra=favor_o_baja` | 29 | $+0,0194R$ | $+1,15$ | $0,250261$ | No | $+0,0008R$ | $+0,04$ | $0,965937$ | $0,4830$ | $72,4\,\% / 44,8\,\%$ | No |
| 9 | `ctx_hora_ny=ny_manana_0930_12` | 17 | $+0,0347R$ | $+1,13$ | $0,256970$ | No | $+0,0488R$ | $+1,44$ | $0,150918$ | $0,0755$ | $70,6\,\% / 76,5\,\%$ | No |
| 10 | `ctx_vol_diaria=media` | 29 | $-0,0337R$ | $-1,10$ | $0,270651$ | No | $+0,0211R$ | $+0,67$ | $0,501006$ | $0,7495$ | $72,4\,\% / 64,3\,\%$ | No |
| 11 | `ctx_vol_rel=alto` | 23 | $+0,0209R$ | $+1,10$ | $0,272707$ | No | $+0,0238R$ | $+1,10$ | $0,272356$ | $0,1362$ | $78,3\,\% / 92,0\,\%$ | No |
| 12 | `veto_muro=pasa` | 29 | $-0,0198R$ | $-1,05$ | $0,295000$ | No | $-0,0195R$ | $-0,89$ | $0,373150$ | $0,1866$ | $58,6\,\% / 72,4\,\%$ | No |
| 13 | `ctx_tendencia_favor=neutra` | 29 | $-0,0233R$ | $-0,88$ | $0,379138$ | No | $-0,0264R$ | $-0,88$ | $0,380526$ | $0,1903$ | $65,5\,\% / 70,4\,\%$ | No |
| 14 | `veto_muro=vetado` | 29 | $+0,0148R$ | $+0,84$ | $0,402090$ | No | $+0,0192R$ | $+0,96$ | $0,335208$ | $0,1676$ | $58,6\,\% / 72,4\,\%$ | No |
| 15 | `ctx_hora_ny=ny_tarde_12_16` | 12 | $+0,0160R$ | $+0,75$ | $0,454602$ | No | $+0,0136R$ | $+0,56$ | $0,575107$ | $0,2876$ | $75,0\,\% / 66,7\,\%$ | No |
| 16 | `ctx_vol_diaria=alta` | 29 | $+0,0201R$ | $+0,73$ | $0,465730$ | No | $-0,0383R$ | $-1,42$ | $0,156317$ | $0,9218$ | $72,4\,\% / 51,7\,\%$ | No |
| 17 | `veto_liquidez_macro=vetado` | 14 | $-0,0183R$ | $-0,58$ | $0,561886$ | No | $-0,0052R$ | $-0,14$ | $0,886899$ | $0,4434$ | $64,3\,\% / 33,3\,\%$ | No |
| 18 | `ctx_hora_ny=londres_03_0930` | 19 | $-0,0163R$ | $-0,49$ | $0,625322$ | No | $-0,0405R$ | $-1,09$ | $0,276516$ | $0,1383$ | $57,9\,\% / 68,4\,\%$ | No |
| 19 | `ctx_atr_rel=medio` | 26 | $-0,0115R$ | $-0,47$ | $0,636025$ | No | $+0,0108R$ | $+0,41$ | $0,678871$ | $0,6606$ | $50,0\,\% / 57,7\,\%$ | No |
| 20 | `ctx_vwap_favor=contra_vwap` | 29 | $+0,0084R$ | $+0,42$ | $0,670509$ | No | $-0,0202R$ | $-0,94$ | $0,344972$ | $0,8275$ | $44,8\,\% / 58,6\,\%$ | No |
| 21 | `ctx_hora_ny=overnight_18_03` | 12 | $-0,0129R$ | $-0,41$ | $0,683932$ | No | $-0,0054R$ | $-0,15$ | $0,882718$ | $0,4414$ | $66,7\,\% / 58,3\,\%$ | No |
| 22 | `ctx_vwap_favor=favor_vwap` | 29 | $-0,0054R$ | $-0,33$ | $0,745400$ | No | $+0,0111R$ | $+0,57$ | $0,569220$ | $0,7154$ | $44,8\,\% / 58,6\,\%$ | No |
| 23 | `veto_huida=pasa` | 29 | $+0,0049R$ | $+0,29$ | $0,767675$ | No | $+0,0008R$ | $+0,04$ | $0,967989$ | $0,4840$ | $58,6\,\% / 65,5\,\%$ | No |
| 24 | `ctx_tendencia_favor=favor_fuerte` | 29 | $-0,0054R$ | $-0,29$ | $0,767863$ | No | $+0,0292R$ | $+1,37$ | $0,169563$ | $0,9152$ | $44,8\,\% / 79,3\,\%$ | No |
| 25 | `veto_liquidez_macro=pasa` | 26 | $+0,0036R$ | $+0,20$ | $0,839594$ | No | $-0,0026R$ | $-0,13$ | $0,897899$ | $0,5511$ | $42,3\,\% / 38,5\,\%$ | No |
| 26 | `ctx_vol_diaria=baja` | 29 | $+0,0042R$ | $+0,15$ | $0,880936$ | No | $+0,0089R$ | $+0,26$ | $0,796522$ | $0,3983$ | $41,4\,\% / 42,9\,\%$ | No |
| 27 | `ctx_vol_rel=medio` | 24 | $+0,0031R$ | $+0,11$ | $0,914319$ | No | $-0,0046R$ | $-0,15$ | $0,880650$ | $0,5597$ | $54,2\,\% / 54,2\,\%$ | No |
| 28 | `veto_horizonte=pasa` | 29 | $+0,0002R$ | $+0,01$ | $0,988401$ | No | $+0,0002R$ | $+0,01$ | $0,992346$ | $0,4962$ | $31,0\,\% / 55,2\,\%$ | No |

---

## 5. Evaluación Completa sobre las 11 Estrategias (`DESC + REP`, 14 Meses, $N = 1.161$ Operaciones)

### 5.1. Tabla Completa de los 13 Candidatos Evaluados en las 11 Reglas

| Candidato evaluado | % Vetado | $\bar{R}_{\text{base}}$ | $\bar{R}_{\text{pasa}}$ | $\bar{R}_{\text{vetado}}$ | $\Delta R$ Total | $\Delta R$ `DESC` | $\Delta R$ `REP` | Reglas $+$ | LOMO ($+$/14) | $\min \Delta R_{\text{LOMO}}$ | $p_{\text{nulo}}$ (`EXP-004b`) | $\text{SD}_{\text{mes}}$ (`base` $\to$ `pasa`) | Meses rojos (`base` $\to$ `pasa`) | Pasa 3 compuertas |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|---:|---:|:---:|:---:|:---:|
| `veto_horizonte` (a priori) | $3,4\,\%$ | $+0,1235R$ | $+0,1212R$ | $+0,1897R$ | $-0,0023R$ | $+0,0008R$ | $-0,0053R$ | 2 / 7 | 0 / 14 | $-0,0035R$ | $0,5280$ | $0,0948 \to 0,0958$ | $0 \to 0$ | No |
| `veto_muro` (a priori: vetar si hay nivel delante) | $45,9\,\%$ | $+0,1235R$ | $+0,0641R$ | $+0,1934R$ | $-0,0593R$ | $-0,0676R$ | $-0,0521R$ | 3 / 11 | 0 / 14 | $-0,0654R$ | $0,9895$ | $0,0948 \to 0,0978$ | $0 \to 4$ | No |
| `veto_huida` (a priori: $\text{ER}_{60} > P_{90}$ en contra) | $3,6\,\%$ | $+0,1235R$ | $+0,1248R$ | $+0,0877R$ | $+0,0013R$ | $+0,0044R$ | $-0,0024R$ | 2 / 7 | 12 / 14 | $-0,0011R$ | $0,4795$ | $0,0948 \to 0,1019$ | $0 \to 0$ | No |
| `veto_liquidez_macro` (a priori: `18–02 ET` o Tier-1) | $35,9\,\%$ | $+0,1235R$ | $+0,1058R$ | $+0,1549R$ | $-0,0176R$ | $-0,0307R$ | $-0,0051R$ | 5 / 11 | 0 / 14 | $-0,0267R$ | $0,5795$ | $0,0948 \to 0,1376$ | $0 \to 0$ | No |
| `veto_huida_o_horizonte` (combinado a priori) | $6,9\,\%$ | $+0,1235R$ | $+0,1226R$ | $+0,1349R$ | $-0,0008R$ | $+0,0054R$ | $-0,0076R$ | 4 / 8 | 1 / 14 | $-0,0034R$ | $0,4895$ | $0,0948 \to 0,1030$ | $0 \to 1$ | No |
| `veto_contra_tendencia_fuerte` ($\text{EMA}_{48}$ 4h) | $34,4\,\%$ | $+0,1235R$ | $+0,1046R$ | $+0,1594R$ | $-0,0189R$ | $-0,0378R$ | $+0,0011R$ | 5 / 11 | 0 / 14 | $-0,0263R$ | $0,4535$ | $0,0948 \to 0,0897$ | $0 \to 2$ | No |
| `veto_eficiencia_contra_alta` ($\text{ER}_{60} > P_{67}$) | $11,8\,\%$ | $+0,1235R$ | $+0,1292R$ | $+0,0802R$ | $+0,0058R$ | $+0,0061R$ | $+0,0052R$ | 4 / 9 | 14 / 14 | $+0,0035R$ | $0,3380$ | $0,0948 \to 0,1085$ | $0 \to 1$ | No |
| `veto_vol_diaria_baja` (rango previo $< P_{33}$) | $34,2\,\%$ | $+0,1235R$ | $+0,1546R$ | $+0,0636R$ | $+0,0311R$ | $+0,0417R$ | $+0,0195R$ | 7 / 11 | 14 / 14 | $+0,0222R$ | $0,0670$ | $0,0948 \to 0,1068$ | $0 \to 2$ | No (refutado en Atlas) |
| `atlas_veto_atr_rel_bajo` ($\text{ATR}_{14} < P_{33}$) | $15,9\,\%$ | $+0,1235R$ | $+0,1260R$ | $+0,1098R$ | $+0,0026R$ | $-0,0062R$ | $+0,0111R$ | 6 / 11 | 11 / 14 | $-0,0032R$ | $0,1550$ | $0,0948 \to 0,0920$ | $0 \to 1$ | No ($<\text{MDE}$ en las 11) |
| `atlas_veto_vol_rel_bajo` ($V_k < P_{33}$) | $16,8\,\%$ | $+0,1235R$ | $+0,1271R$ | $+0,1055R$ | $+0,0036R$ | $-0,0053R$ | $+0,0135R$ | 8 / 11 | 12 / 14 | $-0,0002R$ | $0,0740$ | $0,0948 \to 0,0857$ | $0 \to 1$ | No ($<\text{MDE}$ en las 11) |
| `atlas_veto_compresion_intradia` ($\text{ATR}_{14} < P_{33} \land V_k < P_{33}$) | $12,2\,\%$ | $+0,1235R$ | $+0,1235R$ | $+0,1232R$ | $+0,0000R$ | $-0,0105R$ | $+0,0111R$ | 6 / 11 | 8 / 14 | $-0,0056R$ | $0,1930$ | $0,0948 \to 0,0877$ | $0 \to 0$ | No |
| **`atlas_veto_sin_iman_estructural` (exigir nivel hacia $T_3$)** | **$54,1\,\%$** | **$+0,1235R$** | **$+0,1934R$** | **$+0,0641R$** | **$+0,0699R$** | **$+0,0847R$** | **$+0,0574R$** | **8 / 11** | **14 / 14** | **$+0,0628R$** | **$0,0195$** | **$0,0948 \to 0,1203$** | **$0 \to 0$** | **Sí ($>\text{MDE}_{80\%}$)** |
| `atlas_veto_sin_iman_en_compresion` | $14,0\,\%$ | $+0,1235R$ | $+0,1324R$ | $+0,0687R$ | $+0,0089R$ | $+0,0206R$ | $-0,0032R$ | 7 / 10 | 14 / 14 | $+0,0033R$ | $0,1935$ | $0,0948 \to 0,0962$ | $0 \to 1$ | No |

---

### 5.2. Desglose por Regla en las 3 Condiciones Confirmadas en el Atlas

| Regla | $N_{\text{base}}$ | $\bar{R}_{\text{base}}$ | Con imán (`atlas_veto_sin_iman_estructural`) $N$ / $\bar{R}$ / $\Delta R$ | Sin ATR bajo (`atlas_veto_atr_rel_bajo`) $N$ / $\bar{R}$ / $\Delta R$ | Sin Vol bajo (`atlas_veto_vol_rel_bajo`) $N$ / $\bar{R}$ / $\Delta R$ |
|---|---:|---:|---|---|---|
| **`CVGAP-CFD-NQ`** | 221 | $+0,2538R$ | $71 \text{ ops} \mid +0,4172R \mid \mathbf{+0,1634R}$ | $128 \text{ ops} \mid +0,2363R \mid -0,0175R$ | $103 \text{ ops} \mid +0,2923R \mid \mathbf{+0,0386R}$ |
| **`U1-ZONAS-AVCL-NQ`** | 97 | $+0,0400R$ | $14 \text{ ops} \mid +0,2004R \mid \mathbf{+0,1604R}$ | $94 \text{ ops} \mid +0,0475R \mid \mathbf{+0,0075R}$ | $93 \text{ ops} \mid +0,0444R \mid \mathbf{+0,0044R}$ |
| **`U1-ZONAS-AVCL-ES-C`** | 96 | $+0,1172R$ | $43 \text{ ops} \mid +0,2560R \mid \mathbf{+0,1388R}$ | $95 \text{ ops} \mid +0,1097R \mid -0,0075R$ | $95 \text{ ops} \mid +0,1097R \mid -0,0075R$ |
| **`U1-RACIMOS-GRILLA-NQ`** | 64 | $+0,1646R$ | $29 \text{ ops} \mid +0,2484R \mid \mathbf{+0,0838R}$ | $57 \text{ ops} \mid +0,1991R \mid \mathbf{+0,0345R}$ | $60 \text{ ops} \mid +0,1825R \mid \mathbf{+0,0179R}$ |
| **`U1-CRUZADO`** | 173 | $-0,0126R$ | $134 \text{ ops} \mid +0,0365R \mid \mathbf{+0,0491R}$ | $149 \text{ ops} \mid +0,0364R \mid \mathbf{+0,0490R}$ | $149 \text{ ops} \mid +0,0302R \mid \mathbf{+0,0428R}$ |
| **`U1-ZONAS-BT2-NQ`** | 108 | $+0,0873R$ | $26 \text{ ops} \mid +0,1194R \mid \mathbf{+0,0322R}$ | $106 \text{ ops} \mid +0,0975R \mid \mathbf{+0,0102R}$ | $104 \text{ ops} \mid +0,0881R \mid \mathbf{+0,0008R}$ |
| **`CVGAP-ES-C`** | 119 | $+0,3489R$ | $117 \text{ ops} \mid +0,3627R \mid \mathbf{+0,0138R}$ | $111 \text{ ops} \mid +0,3675R \mid \mathbf{+0,0186R}$ | $112 \text{ ops} \mid +0,3688R \mid \mathbf{+0,0199R}$ |
| **`TORI-NQ-R`** | 70 | $+0,0105R$ | $32 \text{ ops} \mid +0,0207R \mid \mathbf{+0,0102R}$ | $50 \text{ ops} \mid +0,0104R \mid -0,0001R$ | $57 \text{ ops} \mid +0,0078R \mid -0,0027R$ |
| `CONF-CVR-CFD-NQ-R` | 72 | $+0,0036R$ | $47 \text{ ops} \mid +0,0029R \mid -0,0007R$ | $67 \text{ ops} \mid +0,0034R \mid -0,0002R$ | $66 \text{ ops} \mid +0,0033R \mid -0,0004R$ |
| `CVGAP-CFD-ES-C` | 76 | $+0,0730R$ | $16 \text{ ops} \mid +0,0638R \mid -0,0092R$ | $62 \text{ ops} \mid +0,0601R \mid -0,0129R$ | $72 \text{ ops} \mid +0,0851R \mid \mathbf{+0,0121R}$ |
| `U1-ZONAS-BT2-ES` | 65 | $+0,0966R$ | $4 \text{ ops} \mid +0,0442R \mid -0,0524R$ | $57 \text{ ops} \mid +0,0968R \mid \mathbf{+0,0002R}$ | $55 \text{ ops} \mid +0,0985R \mid \mathbf{+0,0020R}$ |
| **Total Cartera (11 reglas)** | **1.161** | **$+0,1235R$** | **$533 \text{ ops} \mid +0,1934R \mid \mathbf{+0,0699R}$** | **$976 \text{ ops} \mid +0,1260R \mid +0,0026R$** | **$966 \text{ ops} \mid +0,1271R \mid +0,0036R$** |

> [!NOTE]
> **Por qué `atlas_veto_atr_rel_bajo` y `atlas_veto_vol_rel_bajo` tienen un efecto enorme en el Atlas (`-0,0793R` y `-0,0698R`) pero moderado en el promedio de las 11 reglas (`+0,0026R` y `+0,0036R`):**
> En una familia sin pre-filtro de impulso, el tercil inferior representa por definición el $33,3\,\%$ de las velas. En las 11 reglas seleccionadas, las propias señales de disparo (`lux_imb`, `cvgap` con excursión $\ge 2H$, `racimos`) ya descartan de origen más de la mitad de las velas comprimidas (sólo el $15,9\,\%$ y $16,8\,\%$ de sus disparos caen en el tercil bajo). Aun así, en las reglas que no filtraban compresión intradía como **`U1-CRUZADO`** (`-0,0126R -> +0,0364R`, $\Delta R = +0,0490R$) y **`U1-RACIMOS-GRILLA-NQ`** (`+0,1646R -> +0,1991R`, $\Delta R = +0,0345R$), eliminar el tercil inferior de ATR/volumen pasa la regla de terreno negativo a positivo y reduce la desviación estándar mensual de la cartera de $0,0948R$ a $0,0857R$.

---

## 6. Reglas Operativas y Guía Aplicable a Futuros Análisis en EdgeLab

A partir de esta sesión, quedan incorporadas al estándar de investigación de EdgeLab las siguientes reglas y herramientas reutilizables:

1. **Uso obligatorio de `contexto_comun.py` en toda nueva campaña (`STAGE_MARGINALES`):**
   - Todo módulo que corra por `edgelab/research/grilla_generica.py` ya calcula y reporta automáticamente en `MARGINALES` las 7 variables `ctx_*` y los 4 vetos `veto_*` tanto en `DESC` como en `REP`, con 40 días de calentamiento cargados por `embudo_main.py`.
2. **Estándar de ejecución por defecto para nuevas familias:**
   - Stop estructural ancho (`S3`) + objetivo lejano (`T3`), confirmado en el $100\,\%$ de los clusters independientes (`13/13`) tras colapsar pares `Futuro + CFD`. Prohibido recortar ganancias acercando el objetivo (`T1` resta en `13/13` clusters).
3. **Filtro estructural de compresión intradía (`ctx_atr_rel != "bajo"` y `ctx_vol_rel != "bajo"`):**
   - Toda familia nueva cuyas señales primarias no exijan expansión de rango o volumen en la vela de disparo (por ejemplo, cruces entre activos como `U1-CRUZADO`, toques de línea de tendencia o barridos de nivel fijo) debe excluir el tercil inferior ($< P_{33}$ de las últimas 20 sesiones) de `atr_sesion` y de volumen M1.
4. **Diferenciación estricta por mecanismo (`REVERSION` vs `CONTINUACION`):**
   - En **Reversión (`REVERSION`)**: la presencia de niveles estructurales de sesión (`VWAP`, `OR30`, `ONH/ONL`, `PDH/PDL`) entre la entrada y el objetivo actúa como **imán de reversión (`+0,0883R` en `DESC`, `+0,0732R` en `REP`)**, y la ventana óptima es la mañana de Nueva York (`09:30–12:00 ET`, `+0,0765R` en `DESC`, `+0,0585R` en `REP`).
   - En **Continuación (`CONTINUACION`)**: nunca entrar a contramano de un impulso eficiente de 60 minutos (`veto_huida=vetado` resta `-0,0805R` en `DESC` y `-0,1403R` en `REP`).
5. **Protocolo para evaluar filtros sobre canastas de reglas seleccionadas:**
   - Jamás adoptar un filtro porque mejore una canasta reducida de reglas ya seleccionadas (como demostró el falso positivo de `veto_vol_diaria_baja`). Exigir siempre:
     1. Confirmación previa en el Atlas multi-familia colapsando `Futuro + CFD` en `(familia_base, activo)`.
     2. Superar el $\text{MDE}_{80\%}$ pre-registrado de la canasta.
     3. Superar las 3 compuertas secundarias ($\ge 8/11$ reglas, `LOMO 14/14`, nulo mensual emparejado `EXP-004b` $p < 0,05$).
     4. Si el signo empírico invierte la dirección pre-registrada (caso `atlas_veto_sin_iman_estructural`), congelar la regla descubierta y validarla prospectivamente en datos futuros vírgenes (`202611+`).
