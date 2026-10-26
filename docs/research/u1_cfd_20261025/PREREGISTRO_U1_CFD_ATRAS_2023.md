# Pre-registro — U1-ES-GRILLA y U1-YM-GRILLA «hacia atrás»: las candidatas congeladas sobre 2023

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familias `U1_ES_GRILLA`, `U1_YM_GRILLA`. Etapa EF4. Método 1 de `docs/research/POTENCIA_MISMOS_DATOS_20261026.md` (en el oro dio 197
operaciones contra 41 del DESC y un veredicto con potencia).

## Reglas (congeladas: las 3 candidatas de cada embudo, elegidas en el DESC relanzado con `min_ops_oos`, con sus cortes)
- U1-ES: `[1,1,0,1,2,2,3,3,1,0,20]`, `[1,2,0,1,2,1,3,3,1,0,4]`, `[1,2,1,1,2,2,3,3,3,0,8]` (DESC: +7,8 / +4,3 / +4,5 pts/op).
- U1-YM: `[1,0,1,1,2,1,3,3,3,0,4]`, `[0,2,0,2,2,2,0,3,3,1,16]`, `[1,1,1,1,2,1,3,3,3,0,5]` (DESC: +53 / +41 / +38 pts/op).
Sin tope (el embudo todavía no pasó por TOPES). Señal y ejecución en el CFD con la fricción canónica del futuro (ES 0,8877, YM 5,052).

## Datos
USA500 y USA30 de Dukascopy, 2023-01-02 → 2023-12-29: anteriores al DESC (2024-01-02 → 2026-03-31), nunca usados por estas familias.

## Decisión
Un lote por familia: paso de LORD++ **reservado antes de lanzar** (`<FAMILIA>::<cid>-ATRAS-2023`), Simes + BH dentro del lote.
A FAVOR por celda si BH la confirma y su media adversa > 0; EN CONTRA si media ≤ 0 con MDE menor que la media del DESC; si no,
NO_CONCLUYENTE. No reemplaza el OOS ni el holdout del embudo; si una celda da EN CONTRA, el embudo la sigue igual (nada se cambia),
pero el resultado queda escrito antes de que llegue al acta.

## Cómo podría refutarse
Media neta ≤ 0 con potencia en 2023 en las tres celdas de la familia.

## Riesgos
2023 es otro régimen (canal «reciente» = 2026-T1); la escala mensual compensa la volatilidad pero no el régimen.

## Resultado (2026-10-26; `U1_ES_ATRAS_2023.json`, `U1_YM_ATRAS_2023.json`, kernels `nicobuttaro/embudo-u1-{es,ym}-grilla-atras-rep-20230102`)
| familia | celda | ops 2023 | media neta pts/op | IC90 | DESC (2026-T1) |
|---|---|---:|---:|---|---:|
| ES | `…,0,20` | 160 | −0,15 | [−1,74; +1,33] | +7,8 |
| ES | `…,0,4` | 137 | +0,03 | [−1,04; +1,04] | +4,3 |
| ES | `…,0,8` | 140 | −1,01 | [−2,50; +0,39] | +4,5 |
| YM | `…,0,4` | 48 | +2,47 | [−22,3; +25,8] | +53 |
| YM | `…,1,16` | 135 | +0,55 | [−9,3; +10,0] | +41 |
| YM | `…,0,5` | 53 | −2,56 | [−13,8; +8,2] | +38 |

LORD++: ninguno de los dos lotes rechaza. En las 6 celdas la media es ≈ 0 y el límite superior del IC90 queda por debajo de la media
del DESC: **EN CONTRA** las 6, con potencia (en ES el IC es ±1,5 pts contra +4,3/+7,8). Lo que el DESC nominó en el canal reciente
(3 meses) no se sostiene un año antes. Los embudos siguen su curso (nada pre-registrado se cambia), pero estas candidatas llegan al
OOS con evidencia en contra escrita.
