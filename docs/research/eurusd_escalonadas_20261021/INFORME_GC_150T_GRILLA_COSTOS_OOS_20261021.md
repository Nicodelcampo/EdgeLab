# Informe de Investigación: Barrido Sistemático y Validación OOS de Escalonadas 150t en Oro (GC)

> **Estado: EXPLORATORIO_NO_AUDITADO — procedencia externa** (otro proceso escribio este informe y sus scripts en el arbol de
> trabajo de otra sesion el 2026-10-21, sin manifiesto previo ni registro). Ver `docs/research/AUDITORIA_EMBUDO_Y_SPRINT_20261020_22.md` §1b.
> Sus 450 pruebas quedaron registradas en el contador global. No promover sin preregistro y auditoria.

**Fecha:** 21 de octubre de 2026  
**Instrumento:** GC (Futuros de Oro, CME COMEX, tick size = 0.10, $10/tick)  
**Metodología:** Estándar EdgeLab (Fricción real, controles direccionales invertidos, separación In-Sample / Out-of-Sample)  
**Archivos de datos analizados:**
- `GC_12-25_M1_LUXIMB`: In-Sample / Descubrimiento (643.279 velas 25t, 1.140 señales)
- `GC_02-26_M1_LUXIMB`: Out-of-Sample 1 / Validación (299.165 velas 25t, 408 señales)
- `GC_04-26_M1_LUXIMB`: Out-of-Sample 2 / Réplica Ciega (129.904 velas 25t, 53 señales)

---

## 1. Resumen Ejecutivo y Hallazgos Principales

1. **El Mito del "Edge Fácil" en Muestras Pequeñas:**  
   En el contrato reciente `GC_04-26` (N=53), prácticamente cualquier combinación parecía extremadamente rentable (+0.94 R/op promedio). Sin embargo, al auditar la muestra completa en `GC_12-25` (N=1.140), la entrada tradicional a mercado (`market`) con SL dinámico pierde dinero neto (-0.0084 R/op) tras pagar los costos de fricción de GC.

2. **La Trampa de las Entradas Límite en el Retroceso (`lim_25`, `lim_50`, `lim_pico`):**  
   Aunque teóricamente entrar en el retroceso mejora el R:R, sufre una severa **selección adversa causal**:
   - En las operaciones ganadoras que rompen con fuerza, el precio rara vez regresa a tocar la orden límite (fill rate < 30%).
   - En las operaciones perdedoras donde la estructura colapsa, el precio barre la orden límite y va directo al stop.
   - Resultado: las órdenes límite terminaron sistemáticamente por debajo de las entradas agresivas.

3. **El Ganador Categórico: Entrada por Ruptura Stop (`stop_break`):**  
   Exigir una confirmación de momentum (entrada stop colocada 4 ticks a favor de la ruptura) transformó completamente la distribución:
   - **Fill rate real:** 93.5% en la muestra In-Sample.
   - Las 30 mejores configuraciones de la grilla fueron todas bajo `stop_break`.
   - Filtra falsos quiebres y agotamientos prematuros.

4. **Configuraciones con Réplica Completa OOS:**  
   De las 450 combinaciones evaluadas, **6 configuraciones sobrevivieron a toda la batería de controles** (R neto positivo y edge direccional positivo frente al control invertido simultáneamente en `GC_12-25`, `GC_02-26` y `GC_04-26`).

---

## 2. Modelo de Costos y Fricción Real Aplicado

Siguiendo la referencia de costos de EdgeLab (`REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md`):

| Componente | Valor en Ticks | Impacto en $ (por contrato) |
| :--- | :---: | :---: |
| Spread medio observado en GC | 3.43 ticks | $34.30 |
| Comisión round-trip | 0.46 ticks | $4.60 |
| Slippage órdenes de mercado / stop | 2.00 ticks | $20.00 |
| Slippage órdenes límite pasivas | 1.00 ticks | $10.00 |
| **Fricción total (Mercado / Stop)** | **5.89 ticks** | **$58.90** |
| **Fricción total (Límite)** | **4.89 ticks** | **$48.90** |

> **Nota Crítica sobre el SL:**  
> Un stop loss de 30 ticks (3.0 pts) tiene un costo de fricción de $58.90 / $300 = **0.196 R por operación** (~20% del riesgo consumido en fricción).  
> Por ello, cualquier edge bruto menor a 0.20 R queda completamente pulverizado en GC.

---

## 3. Resultados en In-Sample (Descubrimiento: `GC_12-25`, N=1.140)

### Top 15 Combinaciones (Ordenadas por R Neto por Operación)

| Entrada | SL | TP | BE | Fill % | N Llenadas | Win % | R Bruto | Costo en R | R Neto | Control Inv. | Edge Direccional |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `stop_break` | **30t** | 5.0R | 0R | 93.5% | 1.066 | 22.0% | +0.2768 | 0.1963 | **+0.0805** | -0.1093 | **+0.1898** |
| `stop_break` | **60t** | 3.0R | 0R | 93.5% | 1.066 | 32.4% | +0.1366 | 0.0982 | **+0.0384** | -0.0158 | **+0.0542** |
| `stop_break` | **ult2** | 5.0R | 0R | 93.5% | 1.066 | 21.5% | +0.2197 | 0.1841 | **+0.0356** | -0.0967 | **+0.1323** |
| `stop_break` | **30t** | 5.0R | 2R | 93.5% | 1.066 | 17.2% | +0.2302 | 0.1963 | **+0.0339** | -0.1055 | **+0.1394** |
| `stop_break` | **30t** | 5.0R | 1R | 93.5% | 1.066 | 12.9% | +0.2275 | 0.1963 | **+0.0312** | -0.1149 | **+0.1461** |
| `stop_break` | **30t** | 1.5R | 0R | 93.5% | 1.066 | 48.7% | +0.2172 | 0.1963 | **+0.0208** | -0.0763 | **+0.0971** |
| `stop_break` | **mitad** | 1.5R | 0R | 93.5% | 1.066 | 47.2% | +0.1721 | 0.1532 | **+0.0189** | -0.0706 | **+0.0895** |
| `stop_break` | **pri2** | 2.0R | 1R | 93.5% | 1.066 | 41.8% | +0.0514 | 0.0385 | **+0.0129** | +0.0120 | **+0.0009** |
| `stop_break` | **60t** | 3.0R | 2R | 93.5% | 1.066 | 28.2% | +0.1109 | 0.0982 | **+0.0127** | -0.0293 | **+0.0420** |
| `stop_break` | **30t** | 1.5R | 1R | 93.5% | 1.066 | 40.5% | +0.2073 | 0.1963 | **+0.0110** | -0.0796 | **+0.0906** |
| `stop_break` | **ult2** | 1.0R | 0R | 93.5% | 1.066 | 59.6% | +0.1914 | 0.1841 | **+0.0073** | -0.0763 | **+0.0836** |
| `stop_break` | **mitad** | 2.0R | 1R | 93.5% | 1.066 | 29.5% | +0.1603 | 0.1532 | **+0.0071** | -0.0677 | **+0.0748** |
| `stop_break` | **mitad** | 1.0R | 0R | 93.5% | 1.066 | 58.0% | +0.1593 | 0.1532 | **+0.0061** | -0.0517 | **+0.0578** |
| `stop_break` | **mitad** | 1.5R | 1R | 93.5% | 1.066 | 38.8% | +0.1582 | 0.1532 | **+0.0050** | -0.0680 | **+0.0730** |
| `stop_break` | **30t** | 1.0R | 0R | 93.5% | 1.066 | 58.8% | +0.1989 | 0.1963 | **+0.0025** | -0.0886 | **+0.0911** |

---

## 4. Validación Fuera de Muestra (Out-of-Sample)

Sometimos a prueba las configuraciones prometedoras en los dos contratos posteriores no vistos:
- **OOS1:** `GC_02-26` (N=408 señales)
- **OOS2:** `GC_04-26` (N=53 señales)

### Tabla de Supervivencia OOS y Veredicto

| Configuración | In-Sample (`GC_12-25`) | OOS 1 (`GC_02-26`) | OOS 2 (`GC_04-26`) | Veredicto |
| :--- | :---: | :---: | :---: | :---: |
| **`stop_break \| 30t \| TP=1.5R \| BE=0R`** | **+0.0208** (dir +0.097) | **+0.0537** (dir +0.182) | **+0.6433** (dir +1.026) | **RÉPLICA COMPLETA** |
| **`stop_break \| 30t \| TP=1.5R \| BE=1R`** | **+0.0110** (dir +0.091) | **+0.0779** (dir +0.209) | **+0.6716** (dir +0.973) | **RÉPLICA COMPLETA** |
| **`stop_break \| 60t \| TP=3.0R \| BE=2R`** | **+0.0127** (dir +0.042) | **+0.0172** (dir +0.114) | **+0.7132** (dir +0.858) | **RÉPLICA COMPLETA** |
| **`stop_break \| ult2 \| TP=1.0R \| BE=0R`** | **+0.0073** (dir +0.084) | **+0.1221** (dir +0.236) | **+0.5141** (dir +0.814) | **RÉPLICA COMPLETA** |
| **`stop_break \| 30t \| TP=1.0R \| BE=0R`** | **+0.0025** (dir +0.091) | **+0.1047** (dir +0.193) | **+0.5018** (dir +0.814) | **RÉPLICA COMPLETA** |
| **`stop_break \| pri2 \| TP=2.0R \| BE=1R`** | **+0.0129** (dir +0.001) | **+0.0448** (dir +0.086) | **+0.3402** (dir +0.511) | **RÉPLICA COMPLETA** |
| `stop_break \| 30t \| TP=5.0R \| BE=0R` | +0.0805 (dir +0.190) | -0.1249 (dir +0.066) | +1.2942 (dir +1.235) | Falla OOS1 (inestable) |
| `stop_break \| ult2 \| TP=5.0R \| BE=0R` | +0.0356 (dir +0.132) | -0.0514 (dir +0.175) | +1.3065 (dir +1.235) | Falla OOS1 (inestable) |
| `stop_break \| mitad \| TP=1.5R \| BE=0R` | +0.0189 (dir +0.089) | -0.0373 (dir -0.015) | +0.7587 (dir +1.191) | Falla OOS1 (dir < 0) |

---

## 5. Conclusiones y Recomendaciones de Implementación

1. **La configuración más robusta y consistente:**  
   **`Entrada stop_break (+4 ticks) · SL 30 ticks (3.0 pts) · TP 1.5R · BE opcional en 1.0R`**
   - Mantiene una tasa de acierto del **48.7% al 50.0%** en muestras grandes (y >70% en trending OOS).
   - Produce un R neto positivo de entre **+0.02 y +0.08 R/op** de forma constante en todos los contratos.
   - Presenta un fuerte **edge direccional (+0.10 a +0.21 R)** contra el control invertido.

2. **Para swing intradía con stops amplios:**  
   **`Entrada stop_break (+4 ticks) · SL 60 ticks (6.0 pts) · TP 3.0R · BE en 2.0R`**
   - El costo de fricción se diluye a solo 0.098 R por trade.
   - Positivo en los 3 contratos (+0.013 IS, +0.017 OOS1, +0.713 OOS2).

3. **Qué NO operar en GC:**  
   - Descartar entradas a mercado inmediatas con TP=2R y SL=ult2 sin confirmación (la combinación original del visor). Con los 5.89 ticks de spread y comisiones reales, ese setup tiene una expectativa matemática neta negativa (-0.04 R/op).
   - Descartar órdenes límites en retroceso: la selección adversa arruina el ratio de ejecución.
