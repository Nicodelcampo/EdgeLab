# Informe externo — Iteración 2: herramientas acopladas y sistema de 3 franjas grilla (copia íntegra)

Estado: PROPUESTA (informe externo de diseño, sin datos; ver `AUDITORIA_ITERACION2_TRES_FRANJAS_20261016.md`)
Fecha: 2026-10-16
Familia / módulo: TRES-FRANJAS (DESDE DÓNDE / POR DÓNDE / A DÓNDE); se solapa con EXP-CORRIDOR y HP-007
Procedencia: archivo `iteracion_2_ingenieria_herramientas_y_tres_franjas_grilla_20261016.md` enviado por Nico por Chaski el 2026-10-16 (llegaron dos copias del mismo texto; ésta es la que no tiene el markdown escapado). Se guarda sin cambios debajo de esta línea (protocolo de documentación §5).

---

# Iteración 2: Ingeniería Detallada de Herramientas Acopladas y su Aplicación Matemática sobre el Sistema de 3 Franjas Grilla (`DESDE DÓNDE`, `POR DÓNDE`, `A DÓNDE`)

- **Documento:** `ITERACION_2_INGENIERIA_HERRAMIENTAS_Y_TRES_FRANJAS_GRILLA_20261016.md`
- **Antecedente Directo:** Evolución e iteración profunda sobre [INVESTIGACION\_USO\_CONJUNTO\_HERRAMIENTAS\_Y\_SISTEMA\_TRES\_FRANJAS\_20261016.md](https://www.google.com/search?q=https%3A%2F%2Fdrive.google.com%2Ffile%2Fd%2F1VWXZeHttI66gshnHl5VnIWaei3FMTuWy%2Fview%3Fusp%3Ddrivesdk) y los hallazgos empíricos de [k32 (PREREGISTERED\_REPLICATION\_AND\_CONTINUAL\_AI\_RESULTS\_20261016.json)](https://www.google.com/search?q=https%3A%2F%2Fdrive.google.com%2Ffile%2Fd%2F18hJ3tRZhhXI-C8xvSkAWWTmxxHYghiHU%2Fview%3Fusp%3Ddrivesdk).
- **Objetivo de esta Iteración:** Pasar del marco conceptual a la **ingeniería matemática, topográfica y algorítmica exacta** de:
  1. Cómo exprimir las capacidades de **segundo orden** de nuestras librerías (`scipy.signal`, `scipy.stats`, `LightGBM`, `scikit-learn`, `PyTorch`, `MAPIE / CQR`, `Venn-Abers`, `PU Learning`) que aún no estaban conectadas entre sí.
  2. Cómo aplicar cada una de esas herramientas sobre la **geometría variable, la física de transporte y las gramáticas de selección** de las **3 Franjas Grilla Extendidas (`DESDE DÓNDE`, `POR DÓNDE`, `A DÓNDE`)**.

## 1. Iteración sobre las Herramientas: Capacidades de Segundo Orden y Sinergia Matemática Exacta

En la primera iteración identificamos *qué* parámetros faltaban (`monotone_constraints`, `interaction_constraints`, `Strip Pooling`, `CQR`). En esta **segunda iteración** resolvemos **cinco problemas técnicos profundos** que aparecen al llevar esas herramientas a un gráfico real de tres franjas horizontales:

### 1.1. Herramienta 1 — Segmentación Topográfica Automática de Franjas sin Cajas Arbitrarias ([scipy.signal.find\_peaks](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.find_peaks.html), [peak\_prominences](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.peak_prominences.html), [peak\_widths](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.peak_widths.html) y [scipy.stats.wasserstein\_distance](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.stats.wasserstein_distance.html))

- **El problema oculto de la Iteración 1:** Si dividimos el eje de precios en bandas fijas de $10$ o $20$ ticks, una banda puede cortar por la mitad un nodo de alto volumen (`HVN`) y por la mitad un vacío de liquidez (`LVN`), mezclando en la misma franja el obstáculo con el camino libre.
- **La herramienta exacta en `SciPy` y cómo se aplica sobre las franjas:**
  1. **Detección Topográfica de Nodos (`HVN`) y Valles (`LVN`) con `scipy.signal`:**
     - Sea $V_{\text{wide}}(p)$ el perfil horizontal de volumen (o tiempo de residencia) acumulado a lo ancho de las últimas $W_{\text{wide}}$ horas para cada nivel de precio $p$ (suavizado con un kernel Gaussiano causal de $\sigma = 2\text{ ticks}$).
     - **Crestas / Imanes (`Candidatos naturales a DESDE DÓNDE y A DÓNDE`):** Llamando a [scipy.signal.find\_peaks(V\_smooth, distance=8, prominence=P\_min)](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.find_peaks.html) seguido de [scipy.signal.peak\_widths(V\_smooth, peaks, rel\_height=0.65)](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.peak_widths.html), obtenemos de forma determinista y sin parámetros arbitrarios los **bordes exactos inferior y superior $[p_{\text{low}}^{(k)}, p_{\text{high}}^{(k)}]$ de cada nodo de valor (`HVN`)**, junto con su prominencia topográfica.
     - **Valles / Canales de Vacío (`Candidatos naturales a POR DÓNDE`):** Aplicando la misma dupla `find_peaks` + `peak_widths` sobre el **perfil invertido $-V_{\text{smooth}}(p)$**, extraemos los **valles topográficos exactos $[p_{\text{low}}^{(v)}, p_{\text{high}}^{(v)}]$ (`Low Volume Nodes / Liquidity Voids`)**, donde la anchura del valle $H_{\text{por}} = p_{\text{high}}^{(v)} - p_{\text{low}}^{(v)}$ mide directamente el recorrido libre disponible en ticks.
  2. **Métrica de Transporte Óptimo 1D con [scipy.stats.wasserstein\_distance](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.stats.wasserstein_distance.html):**
     - Dentro de cada franja, la media o la suma del volumen no distinguen si la liquidez está concentrada en el borde de entrada o en el borde de salida, ni si se movió recientemente.
     - Usando `scipy.stats.wasserstein_distance(u_prices, v_prices, u_weights=vol_macro, v_weights=vol_recent)` medimos dos magnitudes físicas críticas:
       - **En `DESDE DÓNDE`:** La distancia de Wasserstein entre la distribución de volumen histórico lejano ($[-4\text{h}, -30\text{m}]$) y la subasta reciente ($[-5\text{m}, 0\text{s}]$), que cuantifica el **desplazamiento de absorción / defensa institucional** en el borde de lanzamiento.
       - **En `POR DÓNDE`:** La distancia de Wasserstein entre el perfil real de volumen de la franja intermedia y una distribución uniforme plana, detectando si existe **asimetría o taponamiento oculto** hacia uno de los extremos del canal.

### 1.2. Herramienta 2 — Descomposición Aditiva por Coordenada y Regla de No-Compensación con TreeSHAP Nativo (`pred_contrib=True` y `pred_leaf=True` en [LightGBM](https://www.google.com/search?q=https%3A%2F%2Flightgbm.readthedocs.io%2Fen%2Flatest%2Fpythonapi%2Flightgbm.LGBMClassifier.html))

- **El problema oculto de la Iteración 1:** En un modelo tradicional (incluso con `monotone_constraints`), un puntaje total alto puede deberse a que `Desde Dónde` tuvo un clímax enorme ($+3.0$ de contribución en log-odds) mientras que `Por Dónde` tiene un muro intermedio negativo ($-1.2$ de contribución), dando una suma positiva $+1.8$ que termina chocando contra el muro.
- **La herramienta exacta en `LightGBM` y cómo resuelve el problema:**
  1. **Atribución Exacta por Franja en Tiempo Real (`pred_contrib=True`):**
     - Como verificamos en la documentación oficial de [lightgbm.LGBMClassifier.predict(..., pred\_contrib=True)](https://www.google.com/search?q=https%3A%2F%2Flightgbm.readthedocs.io%2Fen%2Flatest%2Fpythonapi%2Flightgbm.LGBMClassifier.html), `LightGBM` calcula en C++ los valores exactos de **TreeSHAP** $\phi_j(X)$ para cada feature $j$, cumpliendo la identidad de eficiencia exacta:
       $$f(X) = \phi_0 + \underbrace{\sum_{j \in \mathcal{I}_{\text{Desde}}} \phi_j(X)}_{\Phi_{\text{Desde}}(X)} + \underbrace{\sum_{j \in \mathcal{I}_{\text{Por}}} \phi_j(X)}_{\Phi_{\text{Por}}(X)} + \underbrace{\sum_{j \in \mathcal{I}_{\text{A}}} \phi_j(X)}_{\Phi_{\text{A}}(X)} + \underbrace{\sum_{j \in \mathcal{I}_{\text{Cross}}} \phi_j(X)}_{\Phi_{\text{Cross}}(X)}$$
     - **Aplicación directa sobre las 3 franjas (`Compuerta de Coherencia Tri-Franja`):** En lugar de mirar sólo el total $f(X)$, exigimos **No-Veto por Coordenada**:
       $$\Phi_{\text{Desde}}(X) > \tau_{\text{desde}} \quad \land \quad \Phi_{\text{Por}}(X) > \tau_{\text{por}} \quad \land \quad \Phi_{\text{A}}(X) \ge \tau_{\text{a}}$$
       Si la franja `Por Dónde` aporta una contribución SHAP negativa ($\Phi_{\text{Por}}(X) < 0$), **la operación queda vetada aunque `Desde Dónde` tenga una señal extrema**.
  2. **Co-Ocurrencia de Hojas (`pred_leaf=True`) para el Meta-Auditor Recursivo:**
     - `predict(X, pred_leaf=True)` devuelve el índice de hoja activa en cada árbol $[n_{\text{samples}}, n_{\text{trees}}]$. Codificar las hojas de los primeros árboles (mediante frecuencia o regresión logística regularizada con penalización $L_1$/$L_2$) captura combinaciones no lineales entre las 3 franjas con varianza mínima.

### 1.3. Herramienta 3 — Tensores de Franja de Altura Variable en `PyTorch`: Re-Muestreo Bilineal + Modulación [FiLM (arXiv:1709.07871)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1709.07871) + [Strip Pooling (arXiv:2003.13328)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2003.13328) + [Axial Cross-Attention (arXiv:1912.12180)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1912.12180)

- **El problema oculto de la Iteración 1:** Las franjas reales en el gráfico tienen **espesores variables en ticks** ($H_{\text{desde}}$ puede medir $10$ ticks, $H_{\text{por}}$ puede medir $45$ ticks en una ocasión y $70$ ticks en otra, y $H_{\text{a}}$ puede medir $16$ ticks). Si re-escalamos todas las franjas `Por Dónde` a una grilla fija de $12 \times 32$, la red convolucional pierde la noción de cuántos ticks físicos mide el canal; y si no las re-escalamos, no pueden apilarse en tensores de lote fijo.
- **La solución arquitectónica acoplada en `PyTorch`:**
  1. **Re-Muestreo Vertical Diferenciable Alineado en Tiempo (`F.interpolate` / `RoIAlign` 1D en Precio):**
     - Las 3 franjas comparten **exactamente las mismas $N_T = 32$ columnas horizontales de tiempo** $[t_1, t_2, \dots, t_{32}]$ (cubriendo hasta $4\text{ horas}$ hacia la izquierda del gráfico).
     - En el eje vertical de precio, `Desde Dónde` se proyecta a $P_d = 6$ filas, `Por Dónde` a $P_p = 12$ filas, y `A Dónde` a $P_a = 6$ filas, formando un tensor apilado $\mathcal{G} \in \mathbb{R}^{B \times C \times 24 \times 32}$ donde las filas $0..5$ son `Desde Dónde`, las filas $6..17$ son `Por Dónde` y las filas $18..23$ son `A Dónde`.
  2. **Modulación Lineal por Escala Física ([FiLM: Feature-wise Linear Modulation, Perez et al. AAAI 2018, arXiv:1709.07871](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1709.07871)):**
     - El vector de escalas físicas adimensionales $\mathbf{s} = \big[\frac{H_{\text{desde}}}{\text{ATR}},\; \frac{H_{\text{por}}}{\text{ATR}},\; \frac{H_{\text{a}}}{\text{ATR}},\; \frac{H_{\text{por}}}{\text{Fricción}}\big] \in \mathbb{R}^4$ pasa por un perceptrón ligero que genera multiplicadores $\gamma(\mathbf{s})$ y desplazamientos $\beta(\mathbf{s})$ para cada canal de cada una de las 3 franjas:
       $$\tilde{\mathcal{F}}_k = \gamma_k(\mathbf{s}) \odot \mathcal{F}_k + \beta_k(\mathbf{s}), \quad k \in \{\text{Desde}, \text{Por}, \text{A}\}$$
     - Así, la red neuronal procesa grillas de tamaño canónico $(6, 12, 6) \times 32$ pero **condiciona cada filtro según el espesor real en ATRs y en múltiplos de fricción**.
  3. **Doble Operador Espacial: [Strip Pooling (Hou et al., CVPR 2020, arXiv:2003.13328)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2003.13328) + [Axial Cross-Attention (Ho et al. 2019, arXiv:1912.12180)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1912.12180):**
     - **Paso A (*Horizontal Strip Pooling $1 \times 32$*):** Promedia y extrae el máximo a lo largo de las $32$ columnas de tiempo para cada una de las $24$ filas de precio, obteniendo la "radiografía horizontal de 4 horas" de cada sub-nivel de `Desde`, `Por` y `A`.
     - **Paso B (*Vertical Profile Pooling $24 \times 1$*):** En cada una de las $32$ columnas de tiempo, resume la interacción vertical instantánea entre las 3 franjas.
     - **Paso C (*Cross-Attention Causal Tri-Franja*):** Sea $E_{\text{desde}}, E_{\text{por}}, E_{\text{a}} \in \mathbb{R}^{32 \times d}$ la secuencia temporal de cada franja. Calculamos atención cruzada donde **la Consulta ($Q$) es el estado actual de `Desde Dónde` + `Por Dónde`**, y **las Claves/Valores ($K, V$) son la historia completa de `Por Dónde` y `A Dónde`**:
       $$\text{Attn}(Q_{\text{desde, por}},\; K_{\text{por, a}},\; V_{\text{por, a}}) = \text{softmax}\!\left(\frac{Q K^\top}{\sqrt{d}}\right) V$$

### 1.4. Herramienta 4 — Calibración Multi-Probabilística [Venn-Abers (arXiv:1211.0025)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1211.0025) + Cuantiles Conformalizados [CQR (arXiv:1905.03222)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1905.03222) + [ACI (arXiv:2106.00170)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2106.00170)

- **El problema oculto de la Iteración 1:** Una sola regresión isotónica (`IsotonicRegression`) sobre un lote pequeño de calibración puede dar saltos bruscos (escalones artificiales) en los extremos.
- **La solución acoplada:**
  1. **Para Probabilidades de Transición entre Franjas ([Inductive Venn-Abers Predictors, Vovk \& Petej 2014, arXiv:1211.0025](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1211.0025)):**
     - Para cualquier candidato nuevo $x$, el calibrador Venn-Abers evalúa dos regresiones isotónicas: $f_0$ (agregando $(s(x), 0)$ al conjunto de calibración) y $f_1$ (agregando $(s(x), 1)$), entregando el par $[p_0(x), p_1(x)]$.
     - Usamos **$p_{\text{conservadora}}(x) = p_0(x)$** como probabilidad conservadora libre de sobreajuste, y penalizamos cualquier candidato cuya incertidumbre epistémica $\Delta p(x) = p_1(x) - p_0(x)$ sea alta.
  2. **Para el Desplazamiento Neto en Ticks ([CQR de Romano, Patterson \& Candès 2019, arXiv:1905.03222](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1905.03222) + [MAPIE](https://www.google.com/search?q=https%3A%2F%2Fmapie.readthedocs.io%2Fen%2Fv0.9.2%2Fexamples_regression%2F4-tutorials%2Fplot_cqr_tutorial.html) + [ACI de Gibbs \& Candès 2021, arXiv:2106.00170](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2106.00170)):**
     - Entrenamos dos modelos [HistGradientBoostingRegressor(loss='quantile')](https://www.google.com/search?q=https%3A%2F%2Fscikit-learn.org%2Fstable%2Fauto_examples%2Fensemble%2Fplot_monotonic_constraints.html) con `monotonic_cst`: uno para el cuantil inferior $\hat{q}_{\alpha_{\text{low}}}(x)$ y otro para el cuantil mediano/superior $\hat{q}_{\alpha_{\text{high}}}(x)$ del retorno neto tick-a-tick.
     - Aplicamos la corrección conformal de Romano et al. (2019) actualizada en línea mediante `ACI`:
       $$\hat{L}_{t}(x) = \hat{q}_{\alpha_{\text{low}}}(x) - Q_{1 - \alpha_t}\!\big(\{E_i\}_{i \in \text{Calib}}\big)$$

## 2. Iteración sobre la Aplicación en las 3 Franjas Grilla (`DESDE DÓNDE`, `POR DÓNDE`, `A DÓNDE`)

### 2.1. Especificación Exacta del Tensor de las 3 Franjas Extendidas (`6 Canales x 24 Filas x 32 Columnas`)

Para capturar tanto la **microestructura instantánea** como la **memoria estructural a lo ancho del gráfico** (hasta $4\text{ horas}$ hacia la izquierda de $t_{\text{dec}}$), las $32$ columnas horizontales de tiempo se distribuyen en **4 Regímenes de Resolución Temporal**:
- **Columnas `0..11` (Historia Macro Lejana, $[-240\text{ min}, -60\text{ min}]$):** $12$ bins de $15\text{ minutos}$ cada uno (captura los grandes nodos de valor `HVN` y vacíos `LVN` de la sesión y apertura).
- **Columnas `12..19` (Historia Estructural Media, $[-60\text{ min}, -12\text{ min}]$):** $8$ bins de $6\text{ minutos}$ cada uno (captura la última subasta intermedia y cómo reaccionó el precio al cruzar `Por Dónde`).
- **Columnas `20..25` (Aproximación Previa, $[-12\text{ min}, -1\text{ min}]$):** $6$ bins de $110\text{ segundos}$ cada uno (captura el impulso de llegada hacia `Desde Dónde`).
- **Columnas `26..31` (Foco Microestructural de Ignición, $[-60\text{ s}, 0\text{ s}]$):** $6$ bins de $10\text{ segundos}$ cada uno (captura el clímax, barrido de stops, absorción y giro de delta en el borde derecho de `Desde Dónde`).

En cada celda $(p, t)$ de las 3 franjas (`Filas 0..5 = Desde Dónde`, `Filas 6..17 = Por Dónde`, `Filas 18..23 = A Dónde`), almacenamos **6 Canales Físicos Invariantes**:

| Canal | Nombre Físico | Definición Matemática Exacta | Rol en `DESDE DÓNDE` | Rol en `POR DÓNDE` | Rol en `A DÓNDE` |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **`C0`** | **Densidad Relativa de Volumen** | $\log\!\left(1 + \frac{V_{p,t}}{\bar{V}_{\text{sesión}} \cdot \Delta p \cdot \Delta t}\right)$ | Mide defensa / absorción institucional acumulada. | **Debe ser BAJA** (identifica el vacío *LVN* / *Liquidity Void*). | **Debe ser ALTA** (identifica el imán *HVN* / POC). |
| **`C1`** | **Velocidad / Inversa de Residencia** | $\frac{|\Delta P_{p,t}| + 1}{\text{Tiempo de Residencia}_{p,t} + 1}$ | Baja en la base de acumulación, alta en el rechazo. | **Debe ser ALTA** (confirma que el precio cruza rápido esta franja sin trabarse). | Baja (indica que el precio suele frenarse y rotar al llegar a `A Dónde`). |
| **`C2`** | **Delta Direccional Orientado** | $\frac{d_{\text{viaje}} \cdot (V_{\text{ask}, p, t} - V_{\text{bid}, p, t})}{V_{p,t} + 1}$ | Giro de negativo a positivo en las columnas `26..31` (*Delta Flip*). | Mide si los cruces previos dejaron desequilibrio comprador/vendedor. | Mide absorción pasiva previa en el nivel objetivo. |
| **`C3`** | **Tamaño Medio de Ejecución (Absorción)** | $\log\!\left(1 + \frac{V_{p,t}}{N_{\text{trades}, p, t} + 1}\right)$ | Detecta presencia de participantes grandes en la punta (`cols 26..31`). | Detecta si algún nivel intermedio oculta un *iceberg* institucional. | Confirma interés institucional real en el destino. |
| **`C4`** | **Estado de Virginidad / No-Mitigación** | $\exp\!\left(-\frac{\text{Volumen posterior al pico}_{p}}{\bar{V}_{\text{fila}}}\right) \in [0, 1]$ | Distingue un nivel fresco recién tocado de un nivel ya gastado. | Indica si el vacío de liquidez (*FVG / Single Print*) sigue abierto o ya fue rellenado. | **Crítico en `A Dónde`:** Un imán virgen no re-testeado tiene mucha mayor atracción que uno ya visitado 5 veces. |
| **`C5`** | **Coordenada Espacial Relativa intra-Franja** | $\eta_p \in [-1, +1]$ dentro de cada franja | Ubica el borde de stop ($\eta \approx -1$) vs. el borde de salida ($\eta \approx +1$). | Ubica el primer tercio, el `50%` central y el último tercio del canal. | Ubica el borde frontal de toma parcial vs. el centro de masa del imán. |

### 2.2. Modelo Matemático de Transporte en 3 Etapas (Cadena de Riesgos Competitivos sobre las 3 Franjas)

En lugar de pedirle a un solo clasificador que adivine el resultado final, descomponemos el viaje del precio a través de las 3 franjas en **tres sub-modelos especializados acoplados** que reflejan exactamente la función de cada coordenada:

1. **Sub-Modelo $\mathcal{M}_{\text{Desde}}$ (`Ignición y Supervivencia al Fill` — Opera sobre `Franja 1: Desde Dónde` + borde inicial de `Por Dónde`):**
   - **Qué predice:** Bajo nuestra máquina de estados tick-a-tick (`k32`), predice:
     - $p_{\text{fill}}(X)$: Probabilidad de que la orden límite sea tomada dentro de $180\text{s}$ sin escaparse antes.
     - $p_{\text{ignición} \mid \text{fill}}(X)$: Probabilidad de que el precio despegue desde `Desde Dónde` y entre al menos un $25\%$ dentro de `Por Dónde` **antes** de tocar el stop detrás de `Desde Dónde` ($-X_{\text{stop}}$).
   - **Restricciones Monótonas (`monotone_constraints`):** $+1$ al giro de delta en `cols 26..31` de `Desde Dónde`, $+1$ al tamaño por trade (`C3`) en `Desde Dónde`, $+1$ al respaldo histórico de pivote en `cols 0..19` de `Desde Dónde`, $-1$ a la aceleración adversa sin absorción.
2. **Sub-Modelo $\mathcal{M}_{\text{Por}}$ (`Conductividad y Supervivencia de Tránsito` — Opera sobre `Franja 2: Por Dónde` condicionada a `Desde` y `A`):**
   - **Qué predice:** Dado que el precio despegó de `Desde Dónde`, predice:
     - $p_{\text{tránsito}}(X)$: Probabilidad de atravesar al menos el $80\%\text{–}100\%$ del espesor $H_{\text{por}}$ de la franja `Por Dónde` hasta tocar el borde frontal de `A Dónde` sin revertir al Break-Even.
     - $\hat{v}_{\text{por}}(X)$: Velocidad esperada de cruce (para ajustar dinámicamente el reloj del modelo intratrade `M3` de salida anticipada).
   - **Restricciones Monótonas (`monotone_constraints`):** $-1$ a la densidad media de volumen `C0` en `Por Dónde` (cuanto más vacía la franja, mayor probabilidad de cruce), $+1$ a la velocidad histórica de cruce `C1` en `Por Dónde`, $-1$ al máximo pico de volumen intermedio dentro de `Por Dónde` (penaliza muros en el 50%), $+1$ a la distancia de Wasserstein de vacío.
3. **Sub-Modelo $\mathcal{M}_{\text{A}}$ (`Atracción, Frenado o Extensión en Destino` — Opera sobre `Franja 3: A Dónde` + región posterior):**
   - **Qué predice:** Dado que el precio cruza `Por Dónde` y llega a `A Dónde`, predice:
     - $p_{\text{frenado\_en\_A}}(X)$: Probabilidad de que `A Dónde` actúe como muro absorbente terminal (indicando cobrar el `100%` de la posición en el borde frontal/medio de `A Dónde`).
     - $p_{\text{ruptura\_mas\_alla}}(X)$: Probabilidad de que el precio atraviese `A Dónde` (cuando `A Dónde` es una piscina de stops sobre un máximo/mínimo previo seguida de otro vacío), indicando usar **Scale-Out 50/50 con Break-Even**.
   - **Restricciones Monótonas (`monotone_constraints`):** $+1$ a la masa gravitatoria (`C0` de `A Dónde` dividido por `C0` de `Por Dónde`), $+1$ al índice de virginidad `C4` de `A Dónde`.

### 2.3. Algoritmo Exacto de las Gramáticas de Selección Aprendidas por Machine Learning (`¿Cómo se Eligen las 3 Franjas en cada Instante?`)

A continuación detallamos cómo opera algorítmicamente el selector de franjas en cada barra de decisión $t_0$, integrando las modalidades que planteaste:

#### Flujo A — Gramática `POR DÓNDE First` (*Descubrimiento Guiado por el Canal de Tránsito*)
1. **Escaneo Topográfico del Perfil Ancho:** En $t_0$, `scipy.signal.find_peaks(-V_smooth)` + `peak_widths` identifica todos los valles horizontales de baja densidad (`LVN`) activos en las últimas $4\text{ horas}$ cuyo espesor cumpla $H_{\text{por}} \ge \max(24\text{ ticks},\; 6 \times \text{ATR})$ (garantizando que la fricción sea $< 10\%$ del canal).
2. **Activación en el Borde del Canal:** Si el precio actual $P(t_0)$ se encuentra en el borde inferior o superior de uno de esos valles `Por Dónde`:
   - La franja de borde donde está $P(t_0)$ (espesor $\sim 0.35 H_{\text{por}}$ hacia atrás) se asigna como candidata **`DESDE DÓNDE`**.
   - El valle central de espesor $H_{\text{por}}$ es **`POR DÓNDE`**.
   - La cresta `HVN` opuesta al otro lado del valle (detectada por `find_peaks(+V_smooth)`) se asigna como **`A DÓNDE`**.
3. **Evaluación Condicional ("¿Hay lugar a seleccionar el resto?"):**
   - Se evalúan los tres sub-modelos $\mathcal{M}_{\text{Desde}}, \mathcal{M}_{\text{Por}}, \mathcal{M}_{\text{A}}$ y sus contribuciones TreeSHAP $\Phi_{\text{Desde}}, \Phi_{\text{Por}}, \Phi_{\text{A}}$.
   - Si el precio tocó el borde del `Por Dónde` con **rechazo y absorción** ($\Phi_{\text{Desde}} > \tau_{\text{reversión}}$), se selecciona el viaje de **reversión a través del `Por Dónde`** hacia el otro borde.
   - Si, por el contrario, el precio viene desde afuera y **rompe con agresión el borde entrando al vacío** ($\Phi_{\text{Desde}}$ de continuación alto), el mismo valle `Por Dónde` actúa como **canal de aceleración (*vacuum breakout*)** hacia el `A Dónde` opuesto.

#### Flujo B — Gramática `DESDE DÓNDE First` (*Selección Secuencial desde el Punto de Partida con Compuerta de Existencia*)
1. **Detección del Punto de Partida (`Desde Dónde`):** Se dispara cuando el precio actual $P(t_0)$ registra un evento de ignición (clímax `REJ_3`, barrido de un pivote histórico de la izquierda o pico de absorción `C3` + giro de delta `C2`). Eso fija la coordenada **`DESDE DÓNDE`** en $[P(t_0) - \delta_{\text{stop}},\; P(t_0) + \delta_{\text{init}}]$.
2. **Búsqueda y Ranking de Candidatos `(Por Dónde_m, A Dónde_m)` con [LGBMRanker (lambdarank)](https://www.google.com/search?q=https%3A%2F%2Flightgbm.readthedocs.io%2Fen%2Flatest%2Fpythonapi%2Flightgbm.LGBMRanker.html):**
   - A partir del borde de salida de `Desde Dónde`, el generador construye $M \in \{1, \dots, 5\}$ pares candidatos `(Por Dónde_m, A Dónde_m)` anclados en los siguientes $M$ nodos `HVN` / piscinas de liquidez detectados por `find_peaks(V_smooth)` en la dirección del movimiento (a distancias $H_1 < H_2 < \dots < H_M$).
   - **`LGBMRanker`** (con `query_id = episodio_actual` y `interaction_constraints = [[Desde, Por, A]]`) ordena los $M$ pares candidatos según su ganancia esperada ajustada por riesgo.
3. **Compuerta de Existencia ("¿Hay lugar a seleccionar al resto o no?"):**
   - Tomamos el mejor triplete $(m^*)$ elegido por `LGBMRanker` y le aplicamos el regresor cuantílico conformalizado **[CQR + ACI](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1905.03222)** junto con el filtro TreeSHAP:
     $$\text{ ¿Existe lugar? } \iff \Big(\Phi_{\text{Por}}(X_{m^*}) > 0\Big) \;\land\; \Big(\Phi_{\text{A}}(X_{m^*}) \ge 0\Big) \;\land\; \Big(\hat{L}_{1-\alpha_t}^{\text{CQR}}(X_{m^*}) > \text{Fricción} + \text{Margen}\Big)$$
   - Si incluso para el mejor candidato $m^*$ el camino `Por Dónde` está obstruido ($\Phi_{\text{Por}} \le 0$) o la cota inferior conformal $\hat{L}_{1-\alpha_t}^{\text{CQR}}$ no supera la fricción, el sistema dictamina formalmente **"NO HAY LUGAR PARA SELECCIONAR `POR DÓNDE` Y `A DÓNDE`"** y se abstiene de operar.

### 2.4. Matriz Exacta de `interaction_constraints` y `monotone_constraints` sobre el Vector Tri-Franja

Para que `LightGBM` y `HistGradientBoosting` aprendan la relación entre las 3 franjas sin memorizar combinaciones espurias, el vector de features de cada triplete candidato se organiza en **4 Bloques de Índices** con restricciones explícitas:

| Bloque de Variables | Variables Clave del Bloque | Signo en `monotone_constraints` | Grupos en `interaction_constraints` |
| :--- | :--- | :---: | :--- |
| **Bloque 1: `Grupo_Desde` (Índices `0..7`)** | Absorción en punta (`C3`), Giro de delta (`C2`), Barrido de stops, Respaldo de pivote a la izquierda (`cols 0..19`), Distancia de Wasserstein de ignición. | `[+1, +1, +1, +1, +1, ...]` | Puede interactuar internamente (`[0..7]`) y en el grupo puente inter-franja. |
| **Bloque 2: `Grupo_Por` (Índices `8..16`)** | Densidad media `C0` en `Por Dónde`, Máximo muro interno en `Por Dónde`, Velocidad histórica de cruce `C1`, Virginidad del vacío `C4`, Ratio $H_{\text{por}} / \text{Fricción}$, Ratio $H_{\text{por}} / \text{ATR}$. | `[-1, -1, +1, +1, +1, +1, ...]` | Puede interactuar internamente (`[8..16]`) y con `Desde` y `A` vía los cocientes de contraste. |
| **Bloque 3: `Grupo_A` (Índices `17..23`)** | Densidad del imán `C0` en `A Dónde`, Prominencia topográfica del `HVN` (`scipy.signal.peak_prominences`), Virginidad del objetivo `C4`, Liquidez detrás de `A Dónde`. | `[+1, +1, +1, 0, ...]` | Puede interactuar internamente (`[17..23]`) y con `Por Dónde` para definir el modo de salida (`Mode 0/1/2`). |
| **Bloque 4: `Grupo_Puente_y_Embeddings` (Índices `24..35`)** | Cociente $\text{Vacío}(\text{Por}) / \text{Masa}(\text{A})$, Cociente $\text{Absorción}(\text{Desde}) / \text{Resistencia}(\text{Por})$, más los embeddings *out-of-fold* del `PyTorch Tri-Strip Axial Encoder` modulated por `FiLM`. | `[+1, +1, 0, ..., 0]` | Grupo transversal autorizado a combinarse con los resúmenes de las 3 franjas. |

## 3. Bucle de Aprendizaje Recursivo e Ingeniería Inversa sobre las 3 Franjas

Con esta arquitectura, el módulo de **Ingeniería Inversa Recursiva** (tanto de operaciones propuestas ganadoras/perdedoras como de operaciones no propuestas que hubieran resultado en beneficio) alcanza una precisión mucho mayor que en `k31`:

1. **Diagnóstico Forense Post-Mortem por Franja (`TreeSHAP Attribution Audit`):**
   - Cuando una operación propuesta **pierde**, ya no preguntamos genéricamente "¿qué falló?", sino que miramos sus tres componentes $\big(\Phi_{\text{Desde}}(x_i),\; \Phi_{\text{Por}}(x_i),\; \Phi_{\text{A}}(x_i)\big)$ y el lugar exacto donde murió la trayectoria en el replay tick-a-tick:
     - **Fallo Tipo F1 (*Fallo de Ignición en `Desde Dónde`*):** El precio nunca salió de `Desde Dónde` y tocó el stop directo $\to$ se incrementa el peso de entrenamiento $w_i$ en el **Sub-Modelo $\mathcal{M}_{\text{Desde}}$**.
     - **Fallo Tipo F2 (*Atasco a Mitad de Camino en `Por Dónde`*):** El precio salió de `Desde Dónde` pero rebotó contra un obstáculo invisible dentro de `Por Dónde` $\to$ se incrementa el peso de entrenamiento $w_i$ en el **Sub-Modelo $\mathcal{M}_{\text{Por}}$** y en el modelo intratrade de salida anticipada.
     - **Fallo Tipo F3 (*Espejismo en `A Dónde`*):** El precio se quedó a pocos ticks de `A Dónde` y se dio vuelta $\to$ el **Sub-Modelo $\mathcal{M}_{\text{A}}$** ajusta el borde frontal de toma de ganancias.
2. **Minería Contrafactual de Movimientos No Propuestos (`PU Learning` sobre el Grafo de Franjas):**
   - En cada sesión cerrada de `Train`, un escáner retrospectivo identifica todos los desplazamientos reales de $\ge 32\text{ ticks}$ que ocurrieron en la sesión y reconstruye las 3 franjas horizontales `(Desde Dónde, Por Dónde, A Dónde)` que existían en el instante exacto previo al inicio de cada uno de esos movimientos.
   - Si nuestro motor no propuso ese movimiento en tiempo real, el módulo **`PU Learning` (`Two-Step Spy + Elkan-Noto`)** compara las 3 franjas de ese movimiento omitido contra las propuestas y aprende qué firma topográfica de `Por Dónde` o de `Desde Dónde` pasó desapercibida, actualizando los árboles mediante `booster.refit(decay_rate=0.90)`.

## 4. Resumen Ejecutivo de la Iteración 2: Lista de Verificación para el Prototipo Experimental

Con esta segunda iteración, cada pieza tiene una responsabilidad matemática única, verificable contra librerías consolidadas y libre de heurísticas arbitrarias:

1. **Descubrimiento Topográfico de Franjas:** [scipy.signal.find\_peaks](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.find_peaks.html) + [peak\_prominences](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.peak_prominences.html) + [peak\_widths](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.signal.peak_widths.html) sobre $V_{\text{smooth}}(p)$ (crestas `HVN` = `Desde`/`A`; valles `LVN` en $-V_{\text{smooth}}(p)$ = `Por Dónde`), más [scipy.stats.wasserstein\_distance](https://www.google.com/search?q=https%3A%2F%2Fdocs.scipy.org%2Fdoc%2Fscipy%2Freference%2Fgenerated%2Fscipy.stats.wasserstein_distance.html).
2. **Codificación Geométrica de las 3 Franjas:** Tensor `6 x 24 x 32` (`4 horas` de ancho multiescala) procesado en `PyTorch` con **[FiLM (arXiv:1709.07871)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1709.07871) + [Strip Pooling (arXiv:2003.13328)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2003.13328) + [Axial Cross-Attention (arXiv:1912.12180)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1912.12180)**.
3. **Selección y Ranking de Tripletes (`G1: Por Dónde First` y `G2: Desde Dónde First`):** [lightgbm.LGBMRanker (lambdarank)](https://www.google.com/search?q=https%3A%2F%2Flightgbm.readthedocs.io%2Fen%2Flatest%2Fpythonapi%2Flightgbm.LGBMRanker.html) + cadena de 3 sub-modelos ($\mathcal{M}_{\text{Desde}}, \mathcal{M}_{\text{Por}}, \mathcal{M}_{\text{A}}$) con `monotone_constraints`, `interaction_constraints`, `path_smooth`, `booster.refit` y veto aditivo por coordenada vía **`pred_contrib=True` (TreeSHAP)**.
4. **Calibración y Compuerta de Ejecución en Ticks Reales:** **[Venn-Abers (arXiv:1211.0025)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1211.0025)** para probabilidades de transición + **[HistGradientBoostingRegressor(loss='quantile')](https://www.google.com/search?q=https%3A%2F%2Fscikit-learn.org%2Fstable%2Fauto_examples%2Fensemble%2Fplot_monotonic_constraints.html) + [CQR (arXiv:1905.03222)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F1905.03222) + [ACI (arXiv:2106.00170)](https://www.google.com/search?q=https%3A%2F%2Farxiv.org%2Fabs%2F2106.00170)** bajo el **Replay Tick-a-Tick de Máquina de Estados** y contabilidad `DSR/PBO`.
