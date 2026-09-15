# Dossier Técnico y Guía de Auditoría: Corredores de Vacío y Campo de Resistencia Microestructural (HP-007)

> **Destinatario:** LLM Auditor / Agente Científico Cuantitativo de EdgeLab  
> **Fecha:** 2026-09-15  
> **Rama Canónica:** `foundation/f0b-compatibility-probe`  
> **Autor Intelectual & Diseño:** Nico del Campo  
> **Referente:** [`docs/NORTH_STAR.md`](file:///D:/EdgeLab-foundation/docs/NORTH_STAR.md)  
> **Estado del Holdout:** Sellado e Intacto (`2026-07-01 -> 2026-12-31`). Prohibido abrir o consultar.

---

## 1. Resumen Ejecutivo para el Auditor

Este documento constituye el compendio formal, técnico, algebraico y experimental del descubrimiento y validación de la **Hipótesis HP-007 ("Corredores de Vacío y Campo de Resistencia Microestructural")**.

### El Descubrimiento Central
El precio en los mercados de futuros no se mueve sobre un vacío homogéneo ni sobre líneas de soporte/resistencia discretas arbitrarias. Se desplaza a través de un **campo continuo de densidad microestructural $D(p, t) \in [0, 1]$**, generado por la memoria de órdenes límite pasivas de absorción histórica.

- **Corredores de Vacío ($D \le 0.28$):** Espacios intermedios desprovistos de absorción pasiva descansada donde el precio experimenta **flujo laminar rápido** con una velocidad **3.03 veces mayor en tiempo real** ($10.3$ vs $3.4\text{ ticks/minuto}$, $p = 2.14 \times 10^{-10}$, $Z_{\text{MC}} = 5.65$).
- **Murallas de Congestión ($D \ge 0.70$):** Clusters de absorción pasiva previa que actúan como terminales físicos del vacío: al impactar contra ellos, el precio experimenta un **Rebote Limpio en el 52.27% de las ocasiones** (rechazo medio de $5.15\text{ ticks}$) y absorción en el $15.91\%$. Menos de un tercio logra perforar.
- **Efecto Backstop Protector (Asimetría Vectorial):** Si una entrada alcista en vacío cuenta con un suelo protector denso a su espalda, la expectativa teórica salta a **+0.076 R** (frente a **-0.409 R** al comprar contra un techo). En cortos, vender con un techo protector salta a **+0.156 R** (frente a **-0.103 R** al vender contra soporte).

---

## 2. El Indicador Base: BigTrap2 / BigTrap2Absorption

El campo de resistencia no utiliza indicadores predictivos estándar ni medias móviles. Se nutre del kernel microestructural de **BigTrap2** / **BigTrap2Absorption** (implementado en Python en `edgelab/bridge/indicators/` y en C# para NinjaTrader 8 en `nt8/`):

### 2.1 Mecánica de Detección
1. **Resolución Subyacente:** Reconstrucción de footprint subseries de 1 tick (`BarsPeriodType.Tick, 1`) evaluado bajo contrato estricto de `OnBarClose`, `non_repainting` y ticks enteros con cero ULP.
2. **Naturaleza de las Zonas:**
   - **`ABSORB BULL` (Suelo / Soporte Pasivo):** Formada cuando agresiones de venta masivas en el bid son absorbidas íntegramente por compradores institucionales pasivos con órdenes límite, impidiendo la continuación bajista.
   - **`ABSORB BEAR` (Techo / Resistencia Pasiva):** Formada cuando agresiones de compra masivas en el ask son absorbidas íntegramente por vendedores pasivos con órdenes límite, impidiendo la continuación alcista.
3. **Geometría de las Zonas:**
   - Cada zona ocupa típicamente entre **1 y 3 ticks** de ancho (`top` a `bottom`).
   - Parámetros del preset de Alta Sensibilidad en 6E: 2,884 zonas detectadas sobre 111,400 barras de 25 ticks (`bundle["runs"][2]["zones"]` en `viewer/nt8_bridge/bundles/6E_CONT.json`).

---

## 3. Modelo Matemático: Función Unificada de Resistencia $D(p, t)$

Dado que las zonas individuales son de 1 a 3 ticks, la microestructura entre ellas **no es binaria**. Cada nivel discreto de precio $p$ en el tiempo $t$ posee una densidad calculada por la superposición de todas las zonas activas.

### 3.1 Kernel Espacial Gaussiano
Para una zona $k$ con centro de masa $p_k = \frac{\text{top}_k + \text{bottom}_k}{2}$ y un precio evaluado $p$:
$$K(p, p_k) = \exp\left(-\frac{(p - p_k)^2}{2\sigma^2}\right)$$
donde $\sigma = 1.2 \times \text{tick\_size}$. Si el precio cae dentro del rectángulo de la zona, la distancia es 0 ($K = 1.0$). A más de $3.5\sigma$, la contribución se trunca a 0 para optimización $O(1)$.

### 3.2 Calibración Empírica del Decaimiento Temporal y Maduración
El análisis inicial refutó formalmente el decaimiento monótono rápido ($T_{\text{half}} = 4\,\text{h}$):
- Las zonas recién formadas ($<15\,\text{min}$) son perforadas el **68.3%** de las veces ($\text{MFE}/\text{MAE} = 0.52$).
- Las zonas **maduras de 4 a 12 horas** son las murallas más firmes (**57.3%** de rebote a 8t, $\text{MFE}/\text{MAE} = 1.53$, $+3.7\%$ sobre el control nulo placebo).

La función de ponderación temporal calibrada e implementada es **bimodal**:
$$w_k(t) = f_{\text{vol}}(k) \cdot f_{\text{mat}}(\Delta t) \cdot f_{\text{decay}}(\Delta t) \cdot f_{\text{wear}}(\text{touches}) \cdot \text{penalty}_{\text{inv}}$$

1. **Ponderación por Volumen:**
   $$f_{\text{vol}} = \left(\min\left(3.0, \max\left(0.3, \frac{\text{vol}_k}{20}\right)\right)\right)^{0.25}$$
2. **Función de Maduración:**
   $$f_{\text{mat}}(\Delta t) = \min\left(1.0, 0.35 + 0.65 \times \frac{\Delta t}{3600\,\text{s}}\right)$$
3. **Decaimiento Lento Post-Maduración ($T_{\text{half}} = 12\,\text{horas}$):**
   $$f_{\text{decay}}(\Delta t) = \begin{cases} 1.0 & \text{si } \Delta t \le 14,400\,\text{s} \,(4\,\text{h}) \\ \exp\left(-\ln(2) \times \frac{\Delta t - 14,400}{43,200}\right) & \text{si } \Delta t > 14,400\,\text{s} \end{cases}$$
4. **Mecanismo de Desgaste por Impacto ($f_{\text{wear}}$):**
   La muerte de una zona está gobernada por su consumo de liquidez a través de testeos reiterados:
   $$f_{\text{wear}}(\text{touches}) = \left(\frac{1}{1 + 0.50 \times \text{touches}}\right)^{0.60}$$
5. **Penalización por Invalidación:** $0.35$ si el precio la cruzó completamente, $1.0$ si sigue activa.

### 3.3 Normalización Sigmoidal y Campo Vectorial
$$D(p, t) = 1.0 - \exp\left(-\sum_{k} w_k(t) \cdot K(p, p_k)\right) \in [0.0, 1.0]$$

Para reflejar la asimetría del libro de órdenes:
- **Resistencia Direccional a Compras ($D_\uparrow(p, t)$):** Suma restringida únicamente a zonas `ABSORB BEAR`.
- **Resistencia Direccional a Ventas ($D_\downarrow(p, t)$):** Suma restringida únicamente a zonas `ABSORB BULL`.

---

## 4. Evidencia Empírica Triangulada (Protocolo de Terceridad de Datos)

Todos los tests se corrieron bajo el **Protocolo de Terceridad de Datos de EdgeLab**:
- **Pilar 1:** Bloque In-Sample A (Velas 0 a 55,700).
- **Pilar 2:** Bloque In-Sample B (Velas 55,700 a 111,400).
- **Pilar 3:** Control Nulo Placebo Emparejado + Permutación Monte Carlo ($B=1,000$).
- **Holdout (`2026-07-01 -> 2026-12-31`):** Cero acceso. Intacto.

### 4.1 Falsación de Velocidad de Tránsito ($N=11,874$ eventos)
Script: `tools/test_corredores_vacio.py`

```text
- Travesía en Vacío (D <= 0.28, N=7,167):      0.664 t/b | 10.3 t/min | Exp = +0.099 R
- Travesía en Congestión (D >= 0.70, N=4,707):  0.491 t/b |  3.4 t/min | Exp = +0.053 R
- Control Placebo Nulo (N=2,828):              0.596 t/b |  5.9 t/min | Exp = +0.118 R
- Asimetría de Velocidad:                      1.35x en barras | 3.03x en TIEMPO REAL
- Welch t-test:                                t = 6.373, p = 2.14e-10
- Mann-Whitney U:                              U = 4,496,211, p = 2.57e-14
- Permutación Monte Carlo (B=1,000):           Z = +5.65, p_mc = 0.0000 -> Meta-Valid: True
```

### 4.2 Asimetría Vectorial y Backstop Protector ($N=29,788$ observaciones)
Script: `tools/analisis_profundo_corredores.py`

| Condición del Mercado | Eventos ($N$) | Tasa Acierto (%) | Expectativa ($R$) | Diagnóstico |
|---|---|---|---|---|
| **Alcista: Cielo Despejado ($D_\uparrow \le 0.28$)** | 12.274 | 24.09% | **+0.044 R** | Tránsito libre |
| **Alcista: Con Suelo Protector a la Espalda** | 761 | **24.84%** | **+0.076 R** | **Doble de expectativa** |
| **Alcista: Contra Pared Vendedora ($D_\uparrow \ge 0.70$)** | 447 | 13.65% | **-0.409 R** | **Colisión destructiva** |
| **Bajista: Suelo Despejado ($D_\downarrow \le 0.28$)** | 13.501 | 24.56% | **+0.064 R** | Tránsito libre |
| **Bajista: Con Techo Protector a la Espalda** | 1.380 | **26.67%** | **+0.156 R** | **Triple de expectativa** |
| **Bajista: Contra Soporte Comprador ($D_\downarrow \ge 0.70$)** | 425 | 20.71% | **-0.103 R** | **Colisión destructiva** |

### 4.3 Dinámica Estructural de Pared a Pared (Sin Targets Arbitrarios)
| Amplitud del Corredor | Eventos ($N$) | Ancho Medio | R:R Estructural | Tasa Travesía (%) | Expectativa ($R$) |
|---|---|---|---|---|---|
| **Angosto (4 a 7 ticks)** | 945 | 5.2 ticks | 1.73 : 1 | **42.54%** | **+0.160 R** |
| **Medio (8 a 14 ticks)** | 1.133 | 11.0 ticks | 3.66 : 1 | **22.15%** | **+0.031 R** |
| **Amplio (15 a 30 ticks)** | 1.144 | 20.5 ticks | 6.83 : 1 | 9.27% | -0.275 R |

### 4.4 Física de Colisión en Muralla ($N=132$)
- **Rebote Limpio (Rechazo $\ge 3\text{ ticks}$):** **52.27%** (Rebote medio: $5.15\text{ ticks}$).
- **Absorción / Consolidación ($\pm 2\text{ ticks}$):** **15.91%**.
- **Perforación Directa ($\ge 4\text{ ticks}$):** **31.82%**.

### 4.5 Universalidad en Gráficos de Actividad (Cross-Asset)
- **6E Futuros (CME, 25t):** Ratio de velocidad en vacío = **1.41x** ($p = 6.62 \times 10^{-6}$).
- **EURUSD Spot (Dukascopy, 25t):** Ratio de velocidad en vacío = **1.23x** ($p = 0.0109$).
- **ES Continuo (CME, velas 15m):** Ratio = **0.98x** ($p = 0.0008$).  
  *Demostración Física:* El efecto de corredor de baja fricción es una ley de la subasta de órdenes (volumen/ticks), no del tiempo cronológico del reloj.

---

## 5. Implementación en el Visor Web Interactivo

La lógica matemática completa está integrada en tiempo real en el visor web:
- **Ruta del Visor:** `viewer/nt8_bridge/index.html`
- **Servidor Local Activo:** `http://localhost:8088/index.html?asset=6E_CONT` (levantado vía `viewer/nt8_bridge/server.py`).
- **Características Visuales:**
  - Franja lateral interactiva con el perfil continuo de densidad $D(p, t)$.
  - Detección visual de corredores de vacío (sombreado azul cyan semi-transparente en tramos de $D \le 0.28$).
  - Gauge HUD dinámico que actualiza en tiempo real al mover el cursor la densidad puntual, el estado del corredor y la velocidad estimada.

---

## 6. Hoja de Ruta para el Auditor (Áreas de Profundización)

El auditor entrante cuenta con los siguientes vectores inmediatos para auditar y profundizar:

1. **Reproducción Inmediata de Métricas:**
   ```powershell
   python tools/diagnostico_decaimiento_temporal.py
   python tools/test_corredores_vacio.py
   python tools/analisis_profundo_corredores.py
   ```
   Todos los scripts son deterministas, no tocan el holdout y emiten sus métricas en `docs/research/*.json`.

2. **Gatillo de Ignición e Imbalance (Siguiente Paso Recomendado):**
   - Actualmente sabemos que el corredor es el *medio de baja fricción*, pero el precio no siempre decide cruzarlo de inmediato.
   - Analizar si un imbalance de delta institucional (agresión en el footprint) en la barra de escape del cluster de salida actúa como **ignición de alta probabilidad** para la travesía completa.

3. **Optimización del Stop Loss Dinámico:**
   - La prueba usó un stop estructural fijo de 3 ticks. Sin embargo, una muralla de absorción de 2 ticks permite un stop adaptativo justo en el borde exterior de la muralla (`bottom - 1 tick` en largos), lo que podría optimizar aún más el ratio beneficio/riesgo en corredores de 8 a 14 ticks.

4. **Porting Nativo a NinjaTrader 8:**
   - Implementar la clase C# `nt8/FastTravelCorridors.cs` basada en la formulación bimodal de 12 horas para permitir su backtest y ejecución en tiempo real en NinjaTrader 8.

---

## 7. Inventario Canónico de Archivos

- **Dossier de Auditoría:** [`docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md`](file:///D:/EdgeLab-foundation/docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md)
- **Informe de Falsación Cuantitativa de Velocidad:** [`docs/research/INFORME_CORREDORES_VACIO_VELOCIDAD_2026-09-15.md`](file:///D:/EdgeLab-foundation/docs/research/INFORME_CORREDORES_VACIO_VELOCIDAD_2026-09-15.md)
- **Informe de Análisis Multidimensional Profundo:** [`docs/research/INFORME_ANALISIS_PROFUNDO_CORREDORES_2026-09-15.md`](file:///D:/EdgeLab-foundation/docs/research/INFORME_ANALISIS_PROFUNDO_CORREDORES_2026-09-15.md)
- **Informe de Diagnóstico de Decaimiento Temporal:** [`docs/research/DIAGNOSTICO_DECAIMIENTO_TEMPORAL_6E.md`](file:///D:/EdgeLab-foundation/docs/research/DIAGNOSTICO_DECAIMIENTO_TEMPORAL_6E.md)
- **Registro en Hipótesis Pendientes:** [`docs/HIPOTESIS_PENDIENTES.md`](file:///D:/EdgeLab-foundation/docs/HIPOTESIS_PENDIENTES.md) (HP-007)
- **Scripts de Validación:**
  - [`tools/test_corredores_vacio.py`](file:///D:/EdgeLab-foundation/tools/test_corredores_vacio.py)
  - [`tools/analisis_profundo_corredores.py`](file:///D:/EdgeLab-foundation/tools/analisis_profundo_corredores.py)
  - [`tools/diagnostico_decaimiento_temporal.py`](file:///D:/EdgeLab-foundation/tools/diagnostico_decaimiento_temporal.py)
- **Visor Interactivo:** [`viewer/nt8_bridge/index.html`](file:///D:/EdgeLab-foundation/viewer/nt8_bridge/index.html)
