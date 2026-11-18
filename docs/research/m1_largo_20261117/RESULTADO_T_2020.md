# T (FtmEngine): revisión a fondo y prueba del cambio de 2020 (resultado, 2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO_T_2020.md`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Datos: `RESULTADO_T_2020.json`, `FS_OPS_T2008_{NQ,ES,YM}.csv.gz`, `FS_OPS_{EMD,RTY}.csv.gz`. Pedido de Nico: «pasó de estar en una
cartera a no estar sin tanto motivo».

## 1. Corrección: la conclusión «T frágil, sin señal antes de 2020» estaba mal planteada
- Se midió T en unidades de ATR diario: +0,007 ATR en 2008–2011. T arriesga ≈ 0,3 ATR, así que esa unidad diluye su señal por ≈ 3.
- En su unidad natural, R (neto o bruto / su stop), T tiene en NQ un bruto positivo en 13 de 14 años desde 2012:
  - 2012–2019: +0,02 a +0,10 R por año (+0,036 R en 2008–2019, IC90 apenas sobre 0);
  - 2020–2025: +0,06 a +0,29 R.
- **T no dejó de funcionar antes de 2020: era chica, y la fricción en R de esos años (≈ 0,1 R) se la comía.**

## 2. El tope de 100 puntos del stop no explica la ventaja
- **Cuánto recorta:** nunca antes de 2018 en NQ; entre el 25 % y el 72 % de las operaciones desde 2020; en ES nunca.
- **No cambia el resultado:** en NQ 2020–2025, T rinde igual con y sin tope (bruto +0,175 contra +0,178 R).

## 3. El cambio de 2020: fuerte en los tres grandes índices, no confirmado en MidCap y Russell
| Índice | Bruto por año (R) | Cambio en 2020 |
|---|---|---|
| NQ | 2012–2019: 7 de 8 positivos; 2020–2025: +0,06 → +0,29 | crece |
| ES | ≈ 0 o negativo 2013–2016; 2020–2023: +0,07 → +0,18 | aparece |
| YM | negativo 2012–2016; 2020–2025: positivo todos los años (+0,02 → +0,21) | aparece |
| RTY | positivo todos los años 2018–2025 (+0,02 → +0,11) | no hay salto |
| EMD | mixto; negativo 2022–2025 | no |

**Prueba pre-registrada (EMD + RTY, 2020–2025):**
- Resultado: bruto +0,033 R, IC90 [−0,002, +0,069], 67 % de años positivos, 2.318 operaciones.
- Potencia 0,97 para la mitad del efecto de los grandes índices.
- Veredicto: **NO_CONCLUYENTE**. El efecto fuera de los grandes es chico.

**Lectura:** el salto de 2020 es propio de los tres índices más negociados (NQ, ES, YM). Es coherente, aunque no probado, con flujos que se
concentran ahí: opciones de vencimiento diario sobre SPX y NDX desde 2022 y el flujo minorista de 2020. No es un cambio de todo el mercado.

## 4. Veredicto revisado de T
- **PISTA FUERTE EN NQ**, con señal bruta casi todos los años desde 2012, que creció desde 2020 en NQ, ES y YM.
- **Neto 2020–2025 en NQ:** ≈ +0,15 R por operación.
- **Holdout de oct–nov:** +14 puntos por operación (no significativo).
- **Riesgo:** si el flujo que la potencia desde 2020 se debilita, vuelve a la señal chica de antes, que la fricción de hoy (≈ 0,02 R en
  NQ) todavía no anula.
- **Decisiones:**
  - T vuelve a ser pilar de la cartera B. B (con T) es la principal y B' (sin T) queda sólo como comparación en el forward.
  - T se suma a la canasta de señales estables junto a SOM, Franklin y R (NQ).
  - Su tamaño lo gobierna el forward con el filtro de fricción en R.
