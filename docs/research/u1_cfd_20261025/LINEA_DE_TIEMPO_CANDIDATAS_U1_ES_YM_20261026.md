# U1-ES/YM: ¿edge del régimen actual o ruido de selección? Línea de tiempo trimestral 2023–2025

Estado: RESULTADO (diagnóstico, desarrollo ya usado; holdout intacto)
Fecha: 2026-10-26. Pedido de Nico: profundizar en «las 6 candidatas que dieron en contra sobre 2023 siguen vivas; si el edge existe,
es del régimen actual».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Datos: las 6 candidatas congeladas (celdas y cortes del DESC, sin tocar nada) sobre 2023 (`U1_*_ATRAS_2023.json`) y 2024-01 → 2025-12
(`U1_*_LINEA_2024_2025.json`, kernels `embudo-u1-*-grilla-linea-rep-20240102`). Registradas en el contador global antes de lanzar
(`embudo/U1-*-GRILLA/linea_2024_2025`, 3 pruebas cada una). Etapa EF2 (diagnóstico); no decide nada.

## 1. De dónde salieron las candidatas
Las 6 salieron del **canal «reciente»** del DESC: los últimos 3 meses (ene–mar 2026), 21–30 sesiones, 31–53 operaciones cada una,
elegidas entre 321.943 celdas evaluables. No es que la regla dispare distinto ahora: la frecuencia por trimestre es la misma en
2023–2025 (ES 32–39 operaciones por trimestre, YM 15–39).

## 2. Lo que muestra la historia (P&L neto por operación, por trimestre)
| | ES c0 | ES c1 | ES c2 | YM c0 | YM c1 | YM c2 |
|---|---|---|---|---|---|---|
| ene–mar 2026 (DESC, donde se eligieron) | **+7,80** | **+4,34** | **+4,48** | **+53,1** | **+41,3** | **+38,0** |
| z de ese trimestre | 4,1 | 3,1 | 2,8 | 3,4 | 3,5 | 4,0 |
| z máximo en los 12 trimestres anteriores | 3,0 | 1,7 | 2,4 | 2,2 | 1,9 | 2,3 |
| trimestres anteriores con media > 0 | 6/12 | 6/12 | 4/12 | 7/12 | 5/12 | 4/12 |
| autocorrelación trimestre a trimestre | −0,24 | +0,24 | −0,03 | +0,28 | −0,37 | −0,08 |
| 2024–2025 completo (media, IC90) | +0,22 [−0,91; +1,35] | −0,33 [−1,29; +0,58] | −0,30 [−1,48; +0,81] | +7,7 [−6,5; +21,7] | −3,2 [−10,8; +4,6] | +2,1 [−5,7; +9,4] |

Un episodio parecido ya pasó: en oct–dic 2024 las tres de ES dieron +5,9 / +2,4 / +4,8 y en el trimestre siguiente −2,4 / −2,2 / −1,3.

## 3. Lectura (corrige la frase del 2026-10-26)
La frase «si el edge existe, es del régimen actual» era demasiado generosa. Lo que los datos permiten decir:
- **Las dos explicaciones siguen abiertas**: (a) un régimen que empezó en 2026 y en el que la regla funciona; (b) el mejor trimestre de
  una celda elegida entre ~322.000. Con ese número de celdas, el máximo esperado bajo el nulo ronda z 4,5–5: los z de 2,8–4,1 del
  DESC caben en (b).
- **A favor de (a)**: el trimestre elegido es más fuerte que cualquiera de los 12 anteriores para las mismas celdas (z 2,8–4,1 contra un
  máximo de 1,7–3,0), y pasaron INTEGRIDAD (placebo y latencia) en la versión anterior de ES.
- **En contra de (a)**: en tres años un trimestre bueno no predijo el siguiente (autocorrelación ≈ 0) y el único episodio comparable
  (oct–dic 2024) se dio vuelta enseguida. Si es un régimen, sería nuevo, no la vuelta de algo que ya existió.
- Lo que **no** se puede hacer: declarar ahora que el régimen actual empieza en ene-2026 para que el OOS cuente sólo eso. Sería
  elegir el régimen mirando el resultado. El OOS sigue como está declarado.

## 4. Qué lo decide y con qué potencia
El OOS abr–sep 2026 (no mirado, inmediatamente posterior, el mismo régimen si existe) ya está en el embudo después de INTEGRIDAD.
Con la frecuencia histórica (≈ 70 operaciones en 6 meses en ES) y el desvío medido (8–11 puntos por operación), la potencia para la
mitad del efecto del DESC (`regimen.fraccion_efecto` = 0,5) es ≈ 0,9 (c0), ≈ 0,7 (c1) y ≈ 0,55 (c2). En YM, con 86 puntos de desvío
y 30–75 operaciones, ≈ 0,4–0,6: lo más probable en YM es NO_CONCLUYENTE. Si el OOS va a favor con potencia, (a) gana; si da ≈ 0
con potencia, (b) gana y se refuta en el régimen actual, que es lo que sí mata.

## 5. Cómo podría refutarse esta lectura
Si el OOS de ES da medias cercanas a las del DESC con potencia, la explicación (b) queda descartada para esas celdas y la de régimen
nuevo pasa a ser la de trabajo, a confirmar en el holdout a N fijo.
