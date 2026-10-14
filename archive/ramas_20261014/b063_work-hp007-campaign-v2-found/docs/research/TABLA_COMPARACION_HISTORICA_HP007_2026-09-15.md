# Tabla de Comparación Histórica vs. Causal Formal — Hipótesis HP-007

**Fecha:** 2026-09-15  
**Campaña:** `HP007-CAMP-001`  
**Referencia:** Contraste metodológico entre la exploración preliminar y la medición causal auditada.

---

## 1. Matriz Comparativa de Arquitectura y Resultados

| Dimensión / Métrica | Fase Exploratoria Histórica (Pre-Causal) | Campaña Formal Causal Auditada (2026-09-15) | Explicación del Desfase y Causa Raíz |
| :--- | :---: | :---: | :--- |
| **Gobernanza y Protocolo** | Scripts ad-hoc sin preregistro formal | `HP007_MEASUREMENT_CONTRACT_V1.md` preregistrado | Eliminación del grado de libertad del investigador. |
| **Causalidad Temporal de Zonas** | Zonas calculadas sobre ventanas agregadas post-facto (*lookahead*) | Zonas `BigTrap2Absorption` deterministas punto-en-el-tiempo ($t_{\text{creación}} \le t_{\text{disponible}} \le t_{\text{decisión}}$) | La causalidad estricta eliminó el conocimiento futuro sobre la formación de absorciones. |
| **Candidatos Headline (`VAR_001`)** | "Cientos de episodios detectados" | **0 candidatos cualificados** ($N_{\text{pairs}} = 0$) | La combinación $Fwd \le 0.28$ y $Bck \ge 0.70$ en anchos 4–7t no ocurre en tiempo real. Era un artefacto de lookahead. |
| **Tratamiento del Control** | Placebo no emparejado o aleatorio (+0.118R vs +0.099R) | **Matching 1:1 determinista exacto** por estrato pre-tratamiento (Contrato, Dirección, Hora, Volatilidad, Impulso) | Aísla exclusivamente el efecto del corredor neutralizando el régimen de mercado. |
| **Unidad de Inferencia Estadística** | Trades individuales agrupados como independientes (IID asumido erróneamente) | **Sesión bursátil completa** mediante bootstrap clusterizado (1,000 resamples) y test de permutación de signos | Corrige la autocorrelación intra-sesión y la inflación artificial de $t$-stats. |
| **Ajuste por Multiplicidad** | Ninguno ($p$-values nominales no corregidos) | **Ajuste FWER de Holm-Bonferroni** sobre grilla formal de 54 variantes ($N_{\text{eff}} = 29$) | Control riguroso de falsos descubrimientos en búsqueda exhaustiva. |
| **Modelado de Fricciones** | 0.0 ticks o costos fijos no documentados | Matriz canónica `edgelab/research/costs.py`: Base 2.768t, Adverso 4.768t, Severo 6.768t | Reflejo fidedigno de slippage y comisiones reales del contrato 6E. |
| **Velocidad de Pasaje / Duración** | "Aceleración 3.03x hacia el target" | Sin significancia incremental en supervivencia de tiempo de primer pasaje | La aparente rapidez era una ilusión de selección post-hoc condicionada a targets alcanzados. |
| **Retorno Neto Incremental ($\Delta_{\text{net\_R}}$)** | $+0.099\text{R}$ a $+0.118\text{R}$ (bruto/placebo) | **$\le 0.000\text{R}$** en Headline; colapso en OOS | En emparejamiento 1:1 exacto, los corredores no baten a los controles pre-tratamiento. |
| **Validación Fuera de Muestra** | Ninguna (evaluación dentro de muestra) | **Walk-Forward Contract Fold 1** (Train `6E 03-26` $\to$ Test `6E 06-26`) | WFE de **$-0.02$**: colapso de $+0.503\text{R}$ en Train a $-0.010\text{R}$ en Test. |
| **Protección de Holdout** | Riesgo de fuga o consultas informales | Cortafuegos criptográfico estricto $\ge \text{2026-07-01}$ (0 ticks / 0 outcomes) | Preservación del holdout institucional intacto. |
| **Veredicto Metodológico** | "Edge prometedor" (ilusorio) | **`FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`** | Dictamen científico auditable y reproducible. |

---

## 2. Diagnóstico Detallado de la Ilusión Exploratoria

### 1. El Fenómeno de las "Zonas Fantasma"
En el análisis exploratorio original, las zonas de resistencia se proyectaban a lo largo de la sesión usando información consolidada al cierre del bar o del cluster. En la implementación causal punto-en-el-tiempo, cada zona sólo adquiere existencia y densidad cuando se produce la última transacción de confirmación institucional. Como consecuencia:
- La densidad forward real que percibe el algoritmo al tomar la decisión es sustancialmente mayor que la proyectada a posteriori.
- El 99.8% de los supuestos "corredores libres" en anchos 4–7 ticks tenían micro-bloqueos o transacciones intermedias que el script original ignoraba.

### 2. El Espejismo del Ratio Target/Stop 3.33:1 (10t vs 3t)
Con un stop de 3 ticks en futuros de divisas (6E), un costo transaccional base de 2.768 ticks representa el **92.3% del stop loss**. Cualquier intento de trade en scalping con stop de 3 ticks sufre una expectativa matemática negativa insalvable ante la mínima fricción de mercado, a menos que la tasa de acierto supere el 85%, lo cual es incompatible con la dinámica de subasta continua.

### 3. La Falsa Ventaja del Placebo
En la exploración histórica se comparaban los corredores contra momentos aleatorios del mercado. En la campaña causal, el control es un trade ejecutado en el **mismo contrato, misma dirección, misma hora del día, misma volatilidad y mismo impulso**, pero que no presenta la condición de corredor libre. El resultado empírico demostró que los controles pareados obtienen retornos prácticamente idénticos a los corredores ($\Delta_{\text{net\_R}} \approx 0$), demostrando que la ganancia no provenía del "vacío", sino de la tendencia de fondo o del impulso pre-existente que compartían ambos.
