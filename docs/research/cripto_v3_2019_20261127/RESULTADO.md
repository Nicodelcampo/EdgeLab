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

## Addendum de auditoría (2026-11-27, Antigravity)
- **Causa del falso borde (`t = 1,64` vs `t = 1,73`):** `stats_serie(cana[ok])` promedió **9 meses**, incluyendo **`2020-01`, `2020-02` y `2020-03` en `0,0` USD exactos** cuando el universo Binance USDT-M todavía tenía `< 10` contratos elegibles y la estrategia no tomó ninguna posición (inconsistente con `canasta_amplia.py` / `trz_extranjeros.py`, y con el propio [PREREGISTRO.md](PREREGISTRO.md) que fijaba `2020-05 → 2020-10`, ~6 meses).
- **Recálculo sobre los 6 meses activos reales (`python tools/cripto_v3_2019.py auditar` → `RESULTADO.json["auditoria_meses_activos"]`):**
  - **Canasta v3 (20 pb + funding):** **`+351,5 USD/mes`**, `Sharpe = 2,45`, **`t = 1,73` (`p = 0,0414`)**, `5/6` meses positivos (`83 %`) → **`CONFIRMA`**.
  - **Por regla (6 meses activos, 20 pb):** `XSMOM t = 2,67 (Sh 3,78)`, `ResidMom t = 1,94 (Sh 2,74)`, `BetaNeut t = 1,86 (Sh 2,63)`, `Basis t = 1,69 (Sh 2,39)`, **`BAB LowVol t = −0,26 (Sh −0,36, 33 % meses+)`**.
- **Convergencia entre dos tramos vírgenes independientes:** tanto en `2020` como en `HOLDOUT A5 2021–2026` (`CR3_XSMOM Sh = 0,85, t = 1,04` vs `CR3_BAB Sh = 0,00`), el momentum transversal gana y `BAB LowVol` resta o es neutro. Corregido también el doble castigo del `DSR` in-sample sobre el HOLDOUT único (`confianza_sin_forward_20261127/DSR_HAIRCUT.json`), `CRIPTO-V3` no queda en `DSR = 0,07` sino respaldado por `XSMOM`.
