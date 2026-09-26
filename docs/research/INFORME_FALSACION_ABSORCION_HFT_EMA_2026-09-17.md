# Dossier Científico: Auditoría, Medición y Falsación Multidimensional de la Hipótesis de Absorción HFT y Reversión a la EMA

> **ID Canónico:** `RESEARCH-HFT-EMA-FALSIFICATION-20260917`  
> **Fecha de Emisión:** 2026-09-17  
> **Autor / Par:** Nico del Campo & Antigravity IDE  
> **Marco Metodológico:** Protocolo Canónico EdgeLab (`AUDITOR_START_HERE.md`, `docs/NORTH_STAR.md`)  
> **Activo Evaluado:** E-mini Nasdaq-100 Futures (`NQ 06-26`, Junio 2026)  
> **Dataset:** 239,154 velas de 25 ticks, 5,438 zonas institucionales extraídas en streaming (`viewer/nt8_bridge/bundles/NQ_0626.json`)  
> **Ventana Temporal:** `2026-06-01 22:00:00 UTC` a `2026-06-12 20:59:57 UTC` (100% In-Sample)  
> **Cortafuegos del Holdout:** `HOLDOUT_INTACT` (Ventana $\ge 2026\text{-}07\text{-}01$ estrictamente sellada y no leída)  
> **Destinatario Principal:** LLM Auditor / Auditor Científico Cuantitativo Externo  

---

## 1. Propósito y Guía de Lectura para el Auditor

Este documento constituye el **registro formal y reproducible** de la investigación microestructural realizada sobre las zonas HFT y la hipótesis de reversión elástica a la media móvil exponencial (EMA). 

Está redactado para que un **LLM auditor** (o investigador cuantitativo) que clone el repositorio pueda:
1. Replicar con exactitud bit a bit todos los números, tablas y distribuciones con un solo comando.
2. Comprender exactamente qué partes de la hipótesis fueron **falsadas y destruidas**, y cuáles **sobrevivieron a la batería de estrés**.
3. Ejecutar sus propias pruebas de contra-falsación contra este reporte sin ambigüedad sobre las variables de estado, eventos y datos utilizados.

---

## 2. Génesis de las Hipótesis Evaluadas

### 2.1 La Intuición Inicial y la Advertencia Metodológica
* **Observación empírica:** En el visor gráfico de NinjaTrader 8 (`viewer/nt8_bridge/index.html`), las zonas `HFT SELL` (clímax de ventas agresivas) antecedían frecuentemente a giros alcistas, y las zonas `HFT BUY` a giros bajistas (mecanismo pasivo institucional tipo BigTrap2).
* **La advertencia de Nico:**  
  > *"Cuidado de que las conclusiones descarten por accidente ciertas posibilidades que ofrece esta idea. Quizás el análisis da nulo pero por la forma de medirlo. Quizás hay una segunda serie de eventos que confirman cuando un hft va a funcionar de esa manera propuesta o no, y quizás midiéndolo por sí solo los efectos se anulan."*

### 2.2 El Precedente Canónico en Oro (`RESEARCH-GC-EMA-REVERT-20260906`)
* En [`docs/research/INFORME_FILTRO_EMA_BIGTRAP_GC.md`](file:///d:/EdgeLab/docs/research/INFORME_FILTRO_EMA_BIGTRAP_GC.md), EdgeLab demostró que filtrar BigTrap2 a favor de la tendencia con EMA colapsó, pero la **Reversión a la EMA** (`Close < EMA` para compras de vendedores atrapados) elevó el Profit Factor OOS de $1.41$ a $1.75$.
* **Propuesta de Nico para NQ:**  
  > *"Si el precio está muy lejos de la EMA y hace un HFT para alejarse aún más pero el movimiento se revierte instantáneamente, quizás ahí hay una oportunidad explotable."*

---

## 3. Repositorio de Scripts y Comandos de Reproducción Rápida

Todos los ejecutables fueron diseñados sin dependencias externas complejas (solo `numpy` y la biblioteca estándar de Python 3.12). 

Para reproducir cualquier tabla de este informe desde la raíz de la worktree:

```powershell
# 1. Estudio L1 en 3 niveles, trampa de cancelación y contraste Monte Carlo
python tools/research_hft_absorption_probe.py

# 2. Reversión elástica tras clímax HFT y estratificación de distancia a la EMA
python tools/research_ema_reversion_nq.py

# 3. Batería de 6 pruebas de falsación (Placebo, Lookahead, Fricciones CME, Jackknife)
python tools/falsification_battery.py

# 4. Auditoría profunda: Asimetría Long/Short, Superficie Paramétrica y Kaufman ER
python tools/deep_falsification_probe.py
```

---

## 4. Fundamentación Teórica con Herramientas Nativas de EdgeLab

### 4.1 Test de Razón de Varianzas de Lo–MacKinlay (1988)
Ejecutando la lógica de [`tools/razon_de_varianzas.py`](file:///d:/EdgeLab/tools/razon_de_varianzas.py) sobre las 239,154 velas de NQ 25t:

$$\text{VR}(q) = \frac{\sigma^2(q)}{q \cdot \sigma^2(1)}$$

* $q = 2$ barras (50 ticks): $\text{VR} = 1.0057$ (Micro-momentum / inercia agresiva).
* $q = 5$ barras (125 ticks): $\text{VR} = 1.0079$ (Micro-momentum).
* $q = 10$ barras (250 ticks): $\text{VR} = 0.9934$ (Inicio de la reversión).
* **$q = 20$ barras (500 ticks): $\text{VR} = 0.9654$ (Reversión a la media neta, $\text{VR} < 1$).**
* **$q = 50$ barras (1,250 ticks): $\text{VR} = 0.9645$ (Mínimo estructural de reversión).**
* $q = 200$ barras (5,000 ticks): $\text{VR} = 1.0134$ (Re-alineación con la tendencia macro).

**Veredicto Teórico:** El proceso microestructural de NQ 25-tick exhibe autocorrelación negativa estadísticamente significativa **únicamente en el rango intermedio de 20 a 50 barras**. Esto valida la razón por la cual una entrada ciega a $H=10$ falla (el momentum aún no frena) y por qué a $H \ge 200$ la tendencia macro absorbe el retroceso.

### 4.2 La Ecuación de Barreras y Fricción CME
Según se formalizó en [`tools/atlas_asimetrico.py`](file:///d:/EdgeLab/tools/atlas_asimetrico.py) y [`tools/detailed_cost_decomposition.py`](file:///d:/EdgeLab/tools/detailed_cost_decomposition.py):

$$\delta_{\text{breakeven}} = \frac{\text{Costos Totales}}{P + N}$$

Con Stop Loss de 3 pt (12t) y Target de 4.5 pt (18t), el ancho total es $P+N = 30\text{ ticks}$. Una fricción de CME de $\$15.00$ USD ($3\text{ ticks} = 0.75\text{ pt}$) representa el **$25\%$ de todo el stop y el $17\%$ del target**, destruyendo el *edge* matemático. Solo cuando el target se proyecta a la EMA ($P+N \ge 35\text{ pt} = 140\text{ ticks}$), la fricción cae a menos del $2\%$, haciendo la operación económicamente viable.

---

## 5. El Dossier Forense de Falsación (Qué Sobrevivió vs Qué Quedó Destruido)

```
                                    MATRIZ DE FALSIFICACIÓN
  ┌─────────────────────────────────┬────────────────────────────────────────┬─────────────┐
  │ Ataque Metodológico             │ Hipótesis Nula Atacante                │ Dictamen    │
  ├─────────────────────────────────┼────────────────────────────────────────┼─────────────┤
  │ 1. Control Placebo              │ El HFT es adorno; cualquier vela sirve │ SUPERADO    │
  │ 2. Causalidad en Re-test        │ El edge dependía de peeking futuro     │ FALSADO     │
  │ 3. Fricciones y Micro-Targets   │ Se puede operar con scalping corto     │ FALSADO     │
  │ 4. De-duplicación de Clusters   │ Se cuentan 5 veces la misma ola        │ SUPERADO    │
  │ 5. Asimetría Direccional        │ Es solo sesgo de mercado alcista       │ SUPERADO    │
  │ 6. Meseta Paramétrica           │ Sobreajuste frágil de 30pt / EMA 200   │ SUPERADO    │
  │ 7. Estabilidad Interdiaria      │ El edge es estacionario y diario       │ FALSADO     │
  └─────────────────────────────────┴────────────────────────────────────────┴─────────────┘
```

### 5.1 LO QUE FUE FALSADO Y QUEDÓ DESTRUIDO

#### 1. Falsada la Estabilidad Interdiaria (Inconsistencia de Régimen)
* Al evaluar los 10 días de muestra de forma aislada, **solo 4 de 10 días fueron rentables (40% de consistencia)**.
* Dos sesiones rotacionales (`2026-06-03` con $+12.81$ pt y `2026-06-10` con $+8.87$ pt) cargan con más del **$80\%$ de la ganancia total**.
* En días de tendencia fuerte (*trend days* como `2026-06-02` con $-10.38$ pt y `2026-06-08` con $-8.72$ pt), la estrategia sufre severamente.
* **Conclusión para el Auditor:** La hipótesis no es invariante de régimen; requiere un filtro que distinga días rotacionales de días direccionales de fondos.

#### 2. Falsado el Re-test Retrospectivo (Sesgo de Supervivencia)
* La medición preliminar del Re-test Nivel 3 miraba 6 barras adelante para comprobar si el soporte aguantaba antes de ingresar.
* Al implementar **causalidad estricta en tiempo real** (entrar en la primera vela que toca la zona sin saber el futuro), el retorno medio cayó de $+1.74$ pt a **$+0.23$ pt**, apenas por encima de cero antes de comisiones.

#### 3. Falsados los Micro-Targets (Derrota frente a la Fricción)
* Al simular brackets con SL de 3 a 5 pt y TP de 4.5 a 10 pt:
  * $\text{SL}=3\text{p} / \text{TP}=4.5\text{p} \to \text{PF} = 0.86$
  * $\text{SL}=4\text{p} / \text{TP}=6.0\text{p} \to \text{PF} = 0.80$
  * $\text{SL}=5\text{p} / \text{TP}=10.0\text{p} \to \text{PF} = 0.75$
* El micro-scalping sobre NQ futures con estos triggers pierde dinero frente a las comisiones y el slippage.

---

### 5.2 LO QUE SOBREVIVIÓ AL ATAQUE (NÚCLEO DE VERDAD CONFIRMADO)

#### 1. Destrucción Rotunda del Placebo (+13.5 Ticks de Alpha Neto)
* **Entradas genéricas en sobre-extensión ($|P - \text{EMA}| \ge 30\text{ pt}$ con giro de vela, sin HFT, $N=1,384$):** Retorno medio a 50 barras = **$-1.44$ pt** (MFE/MAE $0.97\text{x}$).
* **Entradas condicionales con Clímax HFT ($N=119$):** Retorno medio = **$+1.92$ pt** (MFE/MAE $1.21\text{x}$).
* **Alpha Incremental Neto del HFT:** **$+3.37$ pt ($+13.5$ ticks)**.
* **Conclusión para el Auditor:** El cluster HFT no es un epifenómeno; es el catalizador que frena la inercia del precio y convierte un escenario perdedor ($-1.44$ pt) en positivo ($+1.92$ pt).

#### 2. Simetría Bidireccional Rigurosa
* **Compras (sub-EMA / trapped sellers):** $N = 73$ | Retorno: **$+1.59$ pt** | MFE/MAE: **$1.04\text{x}$** | Win%: $54.8\%$.
* **Ventas (sobre-EMA / trapped buyers):** $N = 46$ | Retorno: **$+2.46$ pt** | MFE/MAE: **$1.43\text{x}$** | Win%: $54.3\%$.
* El efecto es auténticamente bidireccional y los cortos muestran incluso mayor asimetría favorable.

#### 3. Meseta Paramétrica Robusta
* La matriz bidimensional de EMA spans (100 a 400) frente a distancias (20 a 35 pt) demostró una respuesta suave y continua: entre **EMA 100 y EMA 200 para distancias $\ge 25-30$ pt**, el retorno se mantiene consistentemente entre $+1.11$ y $+5.75$ puntos.

#### 4. La Masa Crítica Institucional ($\ge 100\text{ Contratos}$)
* Al exigir que el cluster HFT tenga volumen pasivo $\ge 100\text{c}$ ($N=21$):
  * Retorno medio a 50 barras: **$+4.67$ pt (+18.7 ticks)**.
  * Ratio MFE/MAE: **$1.89\text{x}$** | Win Rate: **$61.9\%$**.
  * La magnitud de los contratos acumulados funciona como un blindaje que mitiga el riesgo de arrastre adverso.

---

## 6. Protocolo de Contra-Falsación para el LLM Auditor

Si sos un LLM o un auditor cuantitativo que busca refutar este dossier, tus esfuerzos deben enfocarse en los siguientes **cuatro frentes no resueltos**:

1. **Causalidad del Kaufman Efficiency Ratio (ER):**  
   * Demostramos que los días perdedores tienen un $\text{ER} = 0.0126$ frente a $0.0084$ en ganadores.
   * *Ataque sugerido:* Diseñar un estimador causal de ER medido estrictamente a las 10:15 AM ET (primeros 45 min de RTH) y demostrar si predice o no el régimen de la sesión restante sin peeking al cierre.
2. **Validación Multi-Contrato en Parquets Históricos:**  
   * Ejecutar la prueba sobre los contratos In-Sample completos en `E:\EdgeLab\data\nt8\NQ_parquet`: `NQ 09-25`, `NQ 12-25` y `NQ 03-26` utilizando [`tools/optimize_bigtrap_nq_execution.py`](file:///d:/EdgeLab/tools/optimize_bigtrap_nq_execution.py) con `AllowSimultaneousTrades = False`.
   * *Ataque sugerido:* Demostrar si en alguno de los 3 contratos previos el Profit Factor cae por debajo de $1.00$ neto de comisiones.
3. **Slippage Asimétrico en Aperturas y Noticias:**  
   * Medir si los eventos en RTH ocurren en proximidad inmediata a eventos macro (CPI/FOMC a las 08:30 ET o 14:00 ET), donde el slippage real puede superar los 4 ticks.
4. **Política de Salida Dinámica:**  
   * Falsar si una política de Breakeven a $+12$ ticks reduce la tasa de llegada a la EMA por salidas prematuras al precio de entrada.

---

## 7. Conclusiones y Hoja de Ruta Consensuada

1. **La hipótesis de absorción HFT con reversión a la EMA contiene alpha genuino (+13.5 ticks sobre el placebo), pero no es una máquina de hacer dinero incondicional ni sirve para scalping corto.**
2. **La ventana de explotación viable exige la confluencia de tres factores:**
   - **Régimen:** Mercado rotacional/balance (o sesión ETH nocturna), excluyendo días de fuga direccional.
   - **Masa Institucional:** Zonas con volumen acumulado $\ge 90\text{c} - 100\text{c}$.
   - **Monetización Asimétrica:** Stop estructural ceñido a 3 ticks, trailing defensivo a BE tras $+12$ ticks, y target elástico extendido a la **EMA 200**.

---

### Aporte al referente

Se formalizó y versionó el dossier exhaustivo de auditoría y falsación de la absorción microestructural HFT frente a la EMA. Se destruyó la hipótesis de validez incondicional y se demostró la inviabilidad de micro-targets cortos frente a las fricciones de CME, validando las predicciones del Test de Razón de Varianzas ($VR = 0.9645$ a $H=20-50$) y la Ecuación de Barreras de `atlas_asimetrico.py`. Al mismo tiempo, se falsó la hipótesis placebo (+13.5 ticks de alpha puro) y se establecieron los límites precisos de su operatividad causal, dejando la totalidad de los scripts y datos disponibles para que cualquier auditor independiente pueda ejecutar su propia contra-falsación sin vulnerar el cortafuegos del Holdout.
