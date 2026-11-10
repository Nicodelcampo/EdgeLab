# HFT-RUPTURA-OTROS — resultado (banco de eventos en RTY, YM, 6E y 6B)

Estado: RESULTADO (2026-11-10). Pre-registro: `PREREGISTRO_RUPTURA_OTROS.md`. E0-b: `RESULTADO_E0B_OTROS.md`. Banco:
`docs/research/banco_eventos/HFT_RUPTURA_OTROS/` (HIPOTESIS_CONGELADAS.json, RESULTADO.json, RECOMENDACIONES.md). Tabla no mirada
antes del banco (el kernel sólo guardó tabla, conteos y estratos).

## Muestra (mucho menor que la esperada)
524 toques reales: RTY 335, YM 150, 6E 32, 6B 7 (control: 495). En las divisas X = fricción / 0,08 (26 pips en 6E) es muchas veces el
ancho del cluster: el precio rara vez se aleja X/2 y vuelve dentro de la vida del cluster. Mitad A 265, mitad B 259; 104 y 116
sesiones. Calibración del método sobre esta tabla: 8/40 permutaciones con alguna nominada (20 %, en el límite de 2q; no bloquea).

## Hipótesis previas (de NQ/ES), sobre toda la tabla — ninguna nominada
| Previa | n | Estimación (orientada) | se | p | vs resto | Por activo (ruptura media) |
|---|---|---|---|---|---|---|
| retroceso contra la sesión (tendencia, tercil bajo) → ruptura | 176 | +0,011 | 0,067 | 0,43 | −0,035 (se 0,085) | RTY −0,071 (112); YM +0,120 (50); 6E +0,18 (11) |
| un pico dentro → ruptura | 121 | +0,033 | 0,083 | 0,35 | −0,002 | RTY +0,011 (93); YM +0,176 (17) |
| picos sin tomar → rebote | 127 | −0,087 (en contra) | 0,075 | 0,88 | −0,069 | RTY +0,07 (71); YM +0,158 (38) |

MDE (80 %) de las previas ≈ 0,17–0,21: **sin potencia** para el +0,08 de NQ/ES. La pista del retroceso **no se replicó**
(RTY en contra, YM a favor), pero tampoco se puede descartar: su IC90 [−0,10, +0,12] contiene el efecto de NQ/ES.

## Exploración y mitad B
2.167 celdas exploradas en A; **ninguna llegó a n ≥ 100** (la tabla es chica), así que B probó sólo el modelo aditivo: −0,12
(se 0,13), sin efecto. Las «mejores» de A son celdas de 6 a 31 eventos (t 3–4,6): con 2.167 celdas eso es lo esperable por azar.
No son pistas.

## Diagnóstico que sí se ve: el cluster grande no frena (como en NQ)
Real − control (carrera ±X, +1 = atraviesa): **+0,125** (se 0,056, z 2,2; RTY +0,088, YM +0,207). Real +0,034 contra control
−0,091: un nivel cualquiera de la sesión rebota; el cluster grande se atraviesa más. Es el mismo patrón que HFT-REBOTES en NQ
(+0,076). No es una prueba pre-registrada de esta familia (el control es diagnóstico): es una **pista en activos independientes**.

## Lectura (como guía)
1. La pista del retroceso queda **PISTA_VIVA sin réplica con potencia**: hace falta un activo con muchos más toques (o la réplica
   abr–sep de NQ/ES) para decidir.
2. «El cluster grande no defiende el nivel» aparece en NQ y ahora en RTY/YM: el contraste real − control es el candidato más sólido
   de la línea de clusters. Próxima pregunta (directiva 17): ¿por qué el control rebota y el cluster no? (¿el control rebota por
   reversión de corto plazo de la sesión y el cluster queda del lado del flujo?). Se pre-registra como hipótesis previa
   «real − control > 0» en la réplica abr–sep de NQ/ES/RTY/YM.
3. Error de diseño propio (K21): el preflight del banco no chequeaba si alguna celda podía llegar a `min_n` en A ni el MDE de las
   previas; con esta tabla, la mitad B se gastó en una sola prueba sin potencia. Queda como guarda de código.
