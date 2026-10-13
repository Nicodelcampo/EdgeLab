# EMAZ-1 — calibración descriptiva de zonas EMA-estables (NQ 25T, EMA 200)

**No es una prueba de hipótesis ni evidencia de edge.** Describe cuántas zonas marca cada configuración en la historia de NQ de edgelab (sesiones aprobadas 2025-07-01..2026-09-30, 6 contratos, 25 ticks) para elegir presets razonables. Las capturas del usuario son posteriores al holdout: se usaron solo para entender la lógica (escala ≈ 1 px = 1 barra, ajustada con la EMA dibujada; zonas de 165 a 540 barras) y no para ajustar umbrales.

## Qué se encontró
- El detector original (ventana 300, side 0,97, drift 1,2) marca ~6 % de las barras (≈4–7 zonas por sesión): coincide con «marca pocas zonas» en el gráfico.
- La calibración sobre las capturas solas daba 35–70 % de barras marcadas en la historia (demasiado ruidoso), así que se descartó: los umbrales se eligieron con la historia, buscando una cantidad razonable de zonas largas.
- Grilla de 144 configuraciones (M 100–200, K 100–150, drift 0,5–1,2 ATR, side 0,9–0,95, eficiencia 0,5–0,7, CV 0,3–0,5). El factor que más controla la cantidad es la exigencia de **desplazamiento de la EMA (drift)**.

## Presets (en `nt8/EmaStableTrend.cs`)
| Preset | Parámetros | Barras marcadas | Zonas/sesión | Largas (≥150 barras)/sesión | Duración mediana | Recorrido mediano |
|---|---|---:|---:|---:|---:|---:|
| 1 Pocas | M200 K150 f0,95 er0,7 cv0,3 drift0,8 | 6,5 % | 8,8 | 3,1 | 122 barras | 12 pts |
| **2 Normal** | M200 K150 f0,95 er0,7 cv0,5 drift0,8 | 15,9 % | 18,0 | 8,7 | 146 barras | 14 pts |
| 3 Muchas | M150 K100 f0,9 er0,7 cv0,5 drift0,5 | 28,1 % | 34,5 | 14,1 | 130 barras | 13 pts |
| (original) | W300 f0,97 er0,85 drift1,2 | 6,5 % | 6,6 | 3,8 | 162 barras | 15 pts |

(Zonas por sesión cuenta tramos continuos, incluso los cortos; con `MinZoneBars` = 120 solo se confirman los que llegan a esa longitud. Zonas arriba/abajo: aprox. 55 % / 45 %.)

## Longitud de la zona (lo que pidió el usuario)
Nuevo parámetro `MinZoneBars` (por defecto 120): la zona se confirma, y `State` pasa a ±1, recién cuando lleva esas barras; opcional `MinMovePoints`. Con ello la zona útil dura ≥ 120 barras (mediana de las confirmadas ~150–200) y recorre del orden de 12–40 puntos de NQ. Costo: la confirmación llega 120 barras después del inicio; la línea azul se dibuja retroactiva desde el inicio.

## Lo que NO se sabe
- Si operar estas zonas tiene ventaja. Deriva posterior media a favor de la tendencia dentro de las zonas (ticks de 0,25 pt por 100 barras): Normal +0,57, Pocas +0,51, Muchas −0,09, original −1,52; una regla trivial (solo pendiente de la EMA) da −0,4 a −0,5. Diferencias de décimas de tick, barras solapadas, sin costos: es descripción, no una prueba. La pregunta del usuario (¿al darse vuelta el precio atraviesa/continúa más de lo que rebota?) necesita una medición pre-registrada aparte, como VIO-1.
- Que el indicador compile en NT8 (no hay compilador acá; la lógica es la de `edgelab/research/ema_zones.py`, probada en Python con `tests/test_ema_zones.py`).
- El «ATR» del indicador es la media simple de (High−Low) en 100 barras, no el ATR de Wilder de NT8, porque así se calibró.
