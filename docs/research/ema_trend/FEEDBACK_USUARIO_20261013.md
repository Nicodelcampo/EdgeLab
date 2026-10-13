# Feedback del usuario sobre las líneas del indicador (capturas NQ 12-26, 13/10/2026)

Etiquetas del usuario sobre líneas del indicador v2 (EMA desplazada) en NQ 12-26 25T. Medidas digitalizando las capturas (`tools/ema_feedback_lines.py`, `feedback_lines.json`). ATR = rango medio High-Low por columna de píxeles (aproximado; la escala horizontal puede no ser 1 barra por píxel, por eso se usan medidas verticales en ATR).

| Captura | Etiqueta del usuario | Desplazamiento (ATR) | Pendiente (ATR/barra) | Dist. media (ATR) | Dist. máxima (ATR) |
|---|---|---:|---:|---:|---:|
| 22 | Aceptable | 12,8 | 0,067 | 1,8 | 4,2 |
| 23 (baja) | Aceptable | 16,3 | 0,070 | 2,2 | 5,4 |
| 26 | Bien | 34,4 | 0,070 | 3,0 | 7,3 |
| 27 | Bien | 12,2 | (ATR mal medido) | 1,7 | 4,0 |
| 29 (línea del usuario; el indicador no la marca) | Buena | 27,3 | 0,054 | 3,2 | 7,2 |
| 30/31 línea empinada (la del usuario) | Buena | 25,0 | 0,080 | 3,2 | 6,9 |
| 23 (suba) | **Muy mal** | 7,4 | 0,033 | 5,4 | 10,6 |
| 25 | **Cortísima** | 2,0 | 0,010 | 2,1 | 5,9 |
| 28 (línea plana) | **Cortísima** | 3,4 | 0,023 | 4,0 | 12,2 |
| 30/31 línea plana (del indicador) | Mala | 2,3 | 0,008 | 12,4 | 22,2 |
| 24 | **Muy deforme la tendencia** (aclaración: en momentos el precio está muy alejado de la línea) | 16,5 | 0,080 | 3,4 | **8,9** |
| Última captura (sin etiqueta de texto): línea plana larga del indicador vs. línea empinada del usuario | la plana es la mala | | | | |

## Segundo lote: líneas marcadas por el usuario (capturas 32–35, `feedback_lines_2.json`)
| Captura | Línea | Desplazamiento (ATR) | Dist. media (ATR) | Dist. máxima (ATR) |
|---|---|---:|---:|---:|
| 32 | baja (empinada) | 14,4 | 1,1 | 3,6 |
| 33 | baja «Aceptable» | 16,1 | 2,2 | 5,4 |
| 33 | suba larga (500 barras) | ~15 | ~3,5 | ~8 (medida con una fusión de líneas en la digitalización; aproximado) |
| 34 | baja | 12,6 | 2,1 | 5,4 |
| 34 | suba | 12,1 | 3,2 | **8,1** |
| 35 | baja (= 34 en otro tramo) | 12,6 | 2,1 | 5,4 |
Estas líneas del usuario confirman el piso de desplazamiento (≥ 12) y muestran una buena con distancia máxima 8,1, muy cerca del valor de la «deforme» (8,9): el umbral de distancia máxima se subió a **8,5** (hueco muy angosto; con la incertidumbre de la medición del ATR conviene ajustarlo en NinjaTrader).

## Qué separa buenas de malas
- **Desplazamiento de la línea ≥ ~10 ATR** (buenas ≥ 12; malas ≤ 7,4): descarta las «cortísimas» y las planas.
- **Distancia máxima precio-línea ≤ ~8,5 ATR** (buenas ≤ 8,1; la «deforme» 8,9; la «muy mal» 10,6): descarta las deformes.
- **Distancia media ≤ ~4 ATR** (buenas ≤ 3,4; planas largas ≥ 4,0, hasta 12): descarta líneas flojas que no abrazan el precio.
Valores adoptados como defaults del indicador v3.1: `MinExtentAtr` 10, `MaxMeanDistAtr` 4, `MaxDistAtr` 8,5 (editables). Además, si en la zona viva el precio se aleja más de `MaxDistAtr` de la línea, la zona termina.

## Limitaciones
- Muestra de ~12 líneas etiquetadas a ojo; los umbrales están en el medio del hueco entre buenas y malas, no son óptimos.
- El ATR de las capturas (rango por columna) no es exactamente el ATR del indicador (media de 100 barras de High-Low); si hay diferencia de escala hay que ajustar los tres umbrales.
- Una línea trazada a mano que el indicador no marca (captura 29) necesita saber por qué falla la detección por EMA; no se puede reconstruir con datos de Kaggle (son posteriores al holdout).
