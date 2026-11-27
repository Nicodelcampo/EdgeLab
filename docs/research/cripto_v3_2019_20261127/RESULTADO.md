# CRIPTO-V3-2019: la canasta v3 en el único tramo de cripto que nadie miró (resultado, 2026-11-27)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (1 prueba, `CRIPTO_BINANCE`). Meses HOLDOUT de 2019–2020
sin leer. Herramienta: `python tools/cripto_v3_2019.py universo|correr` (`RESULTADO.json`, `SERIES_DESC_REP.csv.gz`).

## Resultado
| Medida (20 pb + funding, meses DESC+REP) | Valor |
|---|---|
| Canasta (XSMOM 0,3858 + BetaNeut 0,3568 + BAB 0,2574, pesos congelados) | **+234 USD/mes, t 1,64 (p 0,051), Sharpe 1,89** |
| Meses | 9 (2020-01 a 2020-03 en cero: todavía no había 10 monedas elegibles). Activos: 6, de 2020-05 a 2020-10 |
| Meses activos | +245, +234, +682, −447, +364, +1.030 USD (5 de 6 positivos) |
| Con costos de 10 / 30 / 40 pb | t 1,73 / 1,54 / 1,44 |
| Correlación diaria con BTC | 0,03 |
| Veredicto pre-registrado | **NO_CONCLUYENTE** (media > 0; t justo debajo de 1,645) |

Por regla (20 pb):
- XSMOM: t 2,27.
- BetaNeut: t 1,73.
- ResidMom: t 1,79.
- Basis: t 1,60.
- **BAB: t −0,26.** Es la pata que se sumó a la canasta en v3.

## Lectura
- **Suma algo, sin decidir.** En el único tramo limpio y anterior a su muestra, la canasta gana con la regla congelada, y lo hace el
  momentum transversal. Con potencia previa de ≈ 0,18, un t de 1,64 es más de lo esperable si no hubiera efecto. Sigue siendo el
  equivalente de un semestre.
- **Junto con lo ya medido:**
  - HOLDOUT A5 2021–2026: t 0,60;
  - Sharpe deflactado: 0,07;
  - este tramo: t 1,64.

  Cripto v3 queda en NO_CONCLUYENTE, con más peso del momentum (XSMOM) que de BAB. Esto no se usa para cambiar los pesos: sería elegir
  con datos ya mirados.
- La confirmación sigue siendo el forward.

Diagnóstico de grilla: sin grilla. Reglas, universo (mismo criterio, período anterior), costos y pesos de `cripto_pit_v3.py` sin cambios.
Episodios: en 2020-08 cae −447 USD (el único mes activo negativo); en 2020-01 → 2020-03 no hay posiciones (universo < 10 monedas).

Aporte al referente: agrega el único tramo limpio que quedaba de cripto. La canasta, congelada, es positiva fuera de su muestra (t 1,64),
lo que la sostiene como pista sin confirmarla.
