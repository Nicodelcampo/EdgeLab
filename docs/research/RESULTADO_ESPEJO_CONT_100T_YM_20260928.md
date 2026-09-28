# ESPEJO-CONT-100T-FILTROS — YM (Lucid) — resultado (2026-09-28)

Kaggle `edgelab-espejo-cont100t-ym-20260928`, nulo corregido. 158 sesiones; 7.707–8.000 trades por nivel (tope 8.000).
**1.050 celdas; p global 0,001; 7 sobreviven el máximo estadístico (t crítico 3,94).** Todas la misma celda chica:

| Nivel | Filtro (a favor de la entrada) | TP / SL | n | R bruto | Exceso sobre nulo (IC 90 %) |
|---|---|---|---|---|---|
| 4 | VWAP | 0,25 / 0,25 W | 3.973 | −0,024 W | +0,016 [+0,010; +0,021] |
| 4 | EMA 50 / EMA 200 | 0,25 / 0,25 | ~4.040 | −0,025 | +0,013 |
| 5 | VWAP | 0,25 / 0,25 | 3.978 | −0,027 | +0,017 [+0,011; +0,022] |
| 5 | EMA 20 / 50 / 200 | 0,25 / 0,25 | ~4.100 | −0,027 | +0,012–0,013 |

## Lectura
- Por primera vez algo supera al azar en la continuación, y **con sentido**: continuar a favor de la tendencia (precio del
  lado del VWAP o de la EMA en la dirección de la entrada) sale mejor que el paseo sin memoria.
- **Pero es chiquito y no rentable:** el R bruto sigue negativo (−0,024 a −0,028 W); el exceso es +1,2 a +1,7 % de W, con W
  mediano ≈ 30 t ⇒ ≈ 0,4–0,5 t por trade frente a la desventaja de entrada. Lejos de cubrir fricción YM.
- Todo en TP/SL 0,25 W (el más chico), donde la mecánica de la entrada pesa más: puede ser un residuo de esa mecánica
  (el nulo arranca en el cierre pero no modela el orden intravela). Tratar como pista, no como candidato.
- Siguiente paso si se quiere perseguir: confirmación única abr–jun (Lucid) de estas 7 celdas, y ver si se repite en
  los otros instrumentos (ES no: 0/1.035).
