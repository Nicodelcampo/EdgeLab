# H-SWEEP-2: Re-entrada al Rango, Filtro de Régimen GEX y Estanterías de Densidad

- **Estado:** `RESEARCH_IDEA_REGISTERED`
- **Fecha:** 2026-08-14
- **Autor / Origen:** Discusión de diseño cuantitativo y microestructura en EdgeLab.
- **Activos Objetivo:** Futuros de Índices de EE.UU. (YM, NQ, ES) y Divisas (6E).

---

## 1. Motivación y Diagnóstico Previo

La evaluación formal de la familia `YM-PRERANGE` (v0.1) demostró que:
1. El **73.5% de los días** el mercado barre ambos extremos del rango matutino (geometría de volatilidad difusiva en la apertura de Wall Street).
2. Apostar ciegamente a la **reversión en el extremo exacto del segundo barrido** produce un resultado puramente difusivo (**52.1% Reversión vs 47.9% Continuación**, `PRERANGE_NO_EDGE`).
3. **Conclusión de diseño:** El barrido del nivel no es una señal de entrada por sí sola; es el **escenario estructural**. Para extraer un edge transable con asimetría positiva, el modelo debe migrar de la *pesca del extremo* al **reconocimiento de re-entrada de flujo y estructura de liquidez**.

---

## 2. Hipótesis 1: El Modelo de Re-entrada al Rango (*Boarding the Reversal Flow*)

En lugar de intentar comprar/vender en el tick extremo del barrido:

```mermaid
flowchart TD
    A["1. Rango Matutino Establecido [Low, High]"] --> B["2. Barrido del Extremo (ej. Nuevo High)"]
    B --> C{"¿El precio sigue en tendencia o rechaza?"}
    C -->|Tendencia Macro / Sin Rechazo| D["NO OPERAR (Filtra días de ruptura violenta)"]
    C -->|Re-ingreso al Rango (Cierre < High)| E["3. GATILLO DE RE-ENTRADA (Short)"]
    E --> F["Stop: Encima del pico del barrido (High + Delta)"]
    E --> G["Target: Extremo Opuesto (Low) o Midpoint del Rango"]
```

### Mecánica y Ventajas Cuantitativas:
* **Filtro natural contra días tendenciales:** Si el quiebre es real (días de noticias macro CPI/NFP donde el mercado corre 400 puntos en una dirección), el precio **nunca re-ingresa al rango**, por lo que la estrategia no dispara órdenes y evita el *drawdown* sistemático.
* **Confirmación de Compradores Atrapados (*Long/Short Trap*):** El gatillo se activa únicamente cuando los participantes agresivos que compraron la ruptura son absorbidos y el precio vuelve a cotizar dentro del valor previo.
* **Asimetría de Riesgo/Beneficio:** El riesgo queda acotado a la mecha del barrido ($R_{\text{stop}}$), mientras que el recorrido potencial abarca el ancho total del rango matutino ($R_{\text{target}} \approx 2 \times \text{a } 3 \times R_{\text{stop}}$).

---

## 3. Hipótesis 2: Condicionamiento por Régimen GEX (Gamma Exposure)

El comportamiento de los Market Makers de opciones en CME/CBOE actúa como el gobernador de régimen para la probabilidad de reversión:

| Régimen GEX | Posición de Market Makers | Dinámica del Mercado | Comportamiento del Rango |
|---|---|---|---|
| **Gamma Positiva ($+GEX$)** | MMs **Largos de Gamma** (compran caídas, venden subidas para rebalancear delta). | **Amortiguación de Volatilidad (Mean-Reversion).** | Los quiebres tienden a fallar $\rightarrow$ **Alta probabilidad de reversión hacia el centro**. |
| **Gamma Negativa ($-GEX$)** | MMs **Cortos de Gamma** (venden caídas, compran subidas acelerando el movimiento). | **Expansión y Momentum Direccional.** | Los quiebres son reales y explotan $\rightarrow$ **Prohibido buscar reversiones**. |

---

## 4. Hipótesis 3: Estanterías de Densidad y Vacíos de Liquidez (*Imbalance Shelves & Vacuums*)

A partir de la morfología observada en los detectores de ineficiencias (Fair Value Gaps y Opening Gaps):

### A. Fenómeno del Borde Abrupto (*The Shelf Cliff*)
* **Definición:** Bloques de alta densidad vertical de ineficiencias ($\ge 8$ zonas apiladas) que delimitan un área de aceptación institucional y terminan en una frontera nítida.
* **Hipótesis Operable:** Un *poke* (excursión de 5–10 puntos) más allá del borde abrupto que cierra de regreso dentro de la estantería dejando mecha de rechazo presenta una alta probabilidad de snap-back hacia el punto de control/centro del bloque.

### B. Fenómeno del Vacío de Liquidez (*The Vacuum / Highway*)
* **Definición:** Intervalos verticales de precio $[P_1, P_2]$ con 0 zonas/ineficiencias previas.
* **Hipótesis Operable:** Al no existir liquidez pasiva de fricción dentro del vacío, el tiempo de cruce (*bars-to-target*) es significativamente menor y el precio tiende a atravesar el vacío de punta a punta hasta alcanzar la siguiente estantería densa.

---

## 5. Protocolo de Evaluación Pendiente en EdgeLab

1. **Dataset:** 600 días de barras M1 y ticks de YM, NQ y ES.
2. **Estimando:** Carrera de primer pasaje simétrica anclada en la barra de re-ingreso (no en el extremo).
3. **Controles:** Comparación pareada contra barras sintéticas de control intra-sesión bajo la maquinaria formal de EdgeLab.
