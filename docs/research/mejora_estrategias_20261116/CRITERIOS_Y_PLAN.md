# Cómo mejorar una estrategia sin engañarnos: criterios, método y plan (2026-11-16)

Estado: VIGENTE — pre-registro del programa de mejora. Pedido de Nico: «definí criterios para intentar mejorar la estrategia, iterá la
planificación una vez buscando maximizar rentabilidad, estabilidad y potencia de lo último de Antigravity, y después repetí el proceso con las
otras donde valga». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Qué es «mejor» (criterios, en orden)
| # | Criterio | Medida | Por qué esta y no otra |
|---|---|---|---|
| C1 | **Rentabilidad neta** | R neto por **mes** (no por operación) y su t mensual | Un filtro que sube el R por operación pero corta la mitad de los días puede ganar menos por mes. El t mensual junta media, variabilidad y cantidad. |
| C2 | **Estabilidad** | años positivos; bloques; peor año; vecinas también buenas (meseta) | La lección dura (F-SELECCION-EN-GRILLAS-GRANDES): lo elegido como pico aislado vale ≈ 0 en la réplica. |
| C3 | **Potencia** | operaciones por mes y MDE del R por operación | Más operaciones independientes = el forward decide antes (e-proceso) y la prop se pasa en menos días. |
| C4 | **Ejecutabilidad y riesgo** | fricción en R ≤ 0,08; nada abierto el fin de semana; drawdown máximo y peor racha en R | Regla de Nico y de las props; la fricción se come las reglas de stop corto (F-STOP-CORTO-ES-FRICCION). |
| C5 | **Diversificación** | correlación diaria con la v2, la Cartera B y Franklin | Una mejora que copia lo que ya tenemos suma poco a la cartera. |

**Puntaje para elegir:** t del R mensual (C1). **Restricciones duras:** C4. **Desempate y veto:** C2 (no se elige una variante con menos
años positivos que la base) y C3.

## 2. Método (lo que la historia del proyecto obliga)
- **Variantes por mecanismo, una perilla por vez** (ATJ-26, marginales): cada variante declara su mecanismo y cómo podría refutarse. Nada de
  grillas grandes: tope de ~15 variantes por estrategia (F-SELECCION-EN-GRILLAS-GRANDES, K4).
- **Las palancas que ya probaron servir se prueban primero**: dejar correr la salida (F-SALIDA-TECNICA-REGALA-LA-GANANCIA), stop grande
  frente a la fricción (F-STOP-GRANDE-FRENTE-A-FRICCION), tamaño fijo y piso de fricción (MEJORAS M1/M3), contexto de noche movida
  (F-ASIA-NQ-NOCHE-MOVIDA), acuerdo con otra regla (Franklin como filtro de T).
- **No se repite lo que no sirvió**: filtros de contexto que eran fricción (F-ATLAS-CONTEXTO-ES-FRICCION), rotar por régimen reciente
  (F-REGIMEN-OFFLINE), freno diario (F-FRENO-DIARIO-NO), KNN por voto (F-KNN-VOTO-NO-TRANSFIERE), tamaño por volatilidad pronosticada.
- **Elegir y confirmar en datos distintos**, con la regla de confirmación escrita antes; el holdout ya abierto no se toca para elegir; lo
  que confirma va a **forward como versión paralela** (la base sigue, nunca se reemplaza sin forward).
- Siempre en R neto con costos canónicos; test de causalidad de cada código nuevo; corrida con código corregido = se descarta y se relanza.

## 3. Plan, primera versión (v0)
SOM: barrer EMA rápida {6, 12, 24} × stop {6, 8, 10} × EMA de trailing {60, 120, 240} × arranque {0, 0,5, 1} R × hora {09:35, 09:45, 10:00}
= 243 combinaciones en NQ, ES y YM; elegir la de mayor R por operación en 2012–2019 y confirmar en 2020–2026.

## 4. Crítica de la v0 (contra la historia y las herramientas)
1. **243 × 3 es una grilla de retornos sin E0**: exactamente lo que K4 y F-SELECCION-EN-GRILLAS-GRANDES prohíben; la mejor celda va a ser
   un pico. → marginales alrededor de la base de fábrica, una perilla por vez.
2. **Optimiza R por operación**: premia filtrar operaciones aunque baje la ganancia mensual y la potencia. → puntaje = t del R mensual.
3. **Elegir en 2012–2019 y confirmar en 2020–2026** favorece lo que andaba en el régimen viejo (ATJ-24: queremos lo que anda ahora) y deja la
   confirmación sin datos viejos. → **elegir en años pares, confirmar en años impares**: cada mitad tiene régimen viejo y nuevo y la misma
   cantidad de datos; lo reciente se informa aparte.
4. **Sólo perillas de parámetros**: ignora las palancas que sí mejoraron reglas en el proyecto (frecuencia, salida, contexto, acuerdo con otra
   regla). SOM tiene una restricción cara: **no abre si la anterior sigue abierta** (en el Tester se perdieron 86 de ~250 días por año). →
   agregar la variante **rotar** (a las 09:35 cierra la vieja y toma la señal del día): más operaciones, más potencia.
5. **ES y YM como selección triplica la búsqueda**. → se elige sólo en NQ (donde SOM vive); ES y YM son acuerdo entre fuentes (descriptivo).
6. **Sin regla para combinar**: si dos mejoras de mecanismos distintos sirven, la combinación es otra hipótesis. → se declara ahora: la
   combinación de las dos mejores de **categorías distintas** entra como una finalista más.

## 5. Plan definitivo (v1) — SOM
- **Base:** SOM `sin_finde` (la de fábrica que cierra el viernes 15:55 NY; la del holdout).
- **14 variantes (una perilla por vez):**
  | Categoría | Variante | Mecanismo |
  |---|---|---|
  | Frecuencia | `rotar` | Cada día una señal nueva; más n y menos exposición a una idea vieja |
  | Salida | `trail_desde_0` / `trail_desde_1R` | Proteger antes vs dejar respirar |
  | Salida | `trail_ema60` / `trail_ema240` | Trailing más rápido vs dejar correr (palanca de salida) |
  | Stop | `stop_6atr` / `stop_10atr` | Stop más chico (más R por op, más fricción) vs más grande |
  | Señal | `ema6` / `ema24` | Lectura más rápida vs más lenta del impulso de apertura |
  | Entrada | `entrada_1000` | Esperar a que el primer impulso se confirme (cierre de la vela de las 09:55) |
  | Contexto | `franklin_no_en_contra` | No operar contra el sesgo NY vs Londres y VWAP (funcionó como filtro de T) |
  | Contexto | `noche_no_baja` | Excluir noches quietas (F-ASIA-NQ-NOCHE-MOVIDA) |
  | Contexto | `sin_gap_grande` | Excluir |gap| ≥ 0,5 ATR20 (el impulso puede ser sólo el gap) |
  | Riesgo | `cierre_diario` | Ya medida (`eod`); sirve de referencia de riesgo |
- **Elección (años pares 2012, 2014 … 2026):** elegibles las que tengan fricción ≤ 0,08 R y no menos años positivos que la base; se congelan las
  **3 de mayor t mensual** y, si son de categorías distintas, la combinación de las dos primeras (≤ 4 finalistas).
- **Confirmación (años impares 2013 … 2025):** diferencia mensual variante − base > 0 con p < 0,10 (bootstrap por mes), **BH q 0,10 sobre las
  finalistas**, y R de la variante > 0. Se informan ES/YM y la ventana reciente (ago-25 → sep-26).
- **Salida:** la ganadora (si hay) pasa al forward como **SOM v2** en paralelo; la base sigue. Contador global: 14 + 4.

## 6. Repetición en otras estrategias (después de SOM, con lo aprendido)
Se aplica donde el valor esperado lo justifica: (a) la regla tiene ventaja confirmada o casi, (b) tiene perillas de mecanismo **no exploradas**,
y (c) hay datos para elegir y confirmar por separado. Triage previsto: **T de FundedSync** (la más sólida; sus salidas por objetivo y a las
15:30 son la palanca de salida sin probar), **Franklin** (ya pasó por 32 variantes sin mejora: sólo se le prueba lo nuevo que aprenda SOM),
**Cartera B / v2** (mejoras de cartera ya hechas; sólo si SOM deja una palanca transferible).
