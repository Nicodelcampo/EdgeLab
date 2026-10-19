# EmaCorridorTrendVol — anclas dentro del rectángulo de volumen

Estado: PROPUESTA de diseño implementada en el indicador; la elección de anclas es **por criterio y por evidencia previa del repo, no medida**
Fecha: 2026-10-15
Familia / módulo: nt8-capture · indicadores de usuario · research (hipótesis de «vía de menor fricción»)
Procedencia: `nt8/user_indicators/EmaCorridorTrendVol.cs`, espejo Python `tools/corridor_anchors.py` (5 pruebas).

## Hipótesis (Nico)
Lo que ocurre en el rectángulo de volumen —según de dónde viene el precio y las características de la zona de expansión— condiciona la probabilidad de que el precio se desplace después **a lo largo de la zona**, tratándola como una vía con menos fricción. Se necesitan 1–3 puntos de referencia dentro del rectángulo para observar la interacción del precio con ellos.

## Criterios para elegir anclas
1. **Causales:** definidos con datos ≤ barra de evaluación.
2. **Distintos entre sí:** que no sean el mismo precio con otro nombre.
3. **Definidos sin discreción:** una fórmula, sin parámetros que se afinen mirando resultados.
4. **Con significado de mercado distinto:** aceptación, borde de aceptación y evento puntual.
5. **Compatibles con la evidencia del repo:** los niveles como soporte/resistencia puro están refutados (BigTrap2: ~96 % de ruptura), y las zonas como imán están cerradas. Por eso las anclas se usan como **referencias para observar** el comportamiento, no como predicción de rebote.

## Las 3 anclas elegidas
| # | Ancla | Definición | Por qué |
|---|---|---|---|
| 1 | **POC del sector** | precio con más volumen operado dentro del rectángulo | nivel de máxima aceptación: referencia natural para ver si el precio lo atraviesa, lo respeta o lo usa |
| 2 | **Borde del Área de Valor (70 %) del lado del interior de la zona** | VAL en una suba, VAH en una baja | el borde de aceptación más cercano al camino por el que el precio volvería a lo largo del corredor; marca dónde termina el volumen «aceptado» y empieza el tramo ralo |
| 3 | **Barra de máximo volumen del sector** (vela tipo VolTicksDef) | punto medio de su rango (opción: su cierre) | ancla de un **evento** (absorción o agresión puntual), distinta de la distribución; es lo que tu ejemplo pedía |

## Candidatas descartadas (y por qué)
- **VWAP del sector:** casi colineal con el POC en sectores compactos; no agrega información.
- **Extremos del sector (máx/mín):** son bordes por construcción del rectángulo, no del volumen; ya medidos como S/R.
- **Punto medio del rectángulo:** arbitrario, sin significado de mercado.
- **VAH/VAL del lado opuesto, nodos de bajo volumen (LVN):** interesantes para «menor fricción» (el LVN es el tramo ralo), pero dependen de parámetros de umbral; quedan como candidatas para una segunda ronda **después** de ver las tres primeras.

## Lo que NO está demostrado
- Que estas tres sean «las mejores»: es un diseño razonado, no un ranking medido. Elegir la mejor midiendo cómo reacciona el precio es una **búsqueda sobre retornos**: necesita manifiesto, número efectivo de hipótesis y tu OK.
- Que la hipótesis sea cierta: nada de esto se ha medido.

## Cómo se mediría (propuesta, no ejecutada)
- **Unidad:** zona terminada con sector evaluado; el evento es el primer retorno del precio a cada ancla después de la evaluación (ventana `AnchorLifeBars`).
- **Resultados (dos canales):** dirección del desplazamiento posterior a lo largo de la zona (continuación vs retorno) y magnitud |desplazamiento| a 15/30/60 min, medidos contra **anclas placebo** (precios al azar dentro del sector a la misma distancia del precio) y contra **zonas no marcadas**.
- **Multiplicidad:** 3 anclas × (marcadas / no marcadas) × 2 canales ≈ 12 pruebas; Holm.
- **Potencia (límite real):** la marca es el percentil 90, así que ~10 % de las zonas quedan marcadas por construcción; con unas pocas decenas de zonas por activo en la release, el N de zonas marcadas será de decenas o menos. **Primero hay que contar, sin mirar retornos, cuántas zonas y cuántas marcadas existen** (paso target-free). Dukascopy no sirve (sin volumen real).

## Cómo se ve en el gráfico
Para cada zona marcada (o todas, con `AnchorsOnlyFlagged = false`): línea sólida magenta = POC; línea de trazos naranja = VAL/VAH del lado del interior; línea punteada celeste = barra de máximo volumen. Se dibujan desde el inicio del sector hasta `AnchorLifeBars` (150) barras después de evaluar. Plots expuestos: `AnchorPOC`, `AnchorVAEdge`, `AnchorHVBar` (precio en la barra de evaluación).
