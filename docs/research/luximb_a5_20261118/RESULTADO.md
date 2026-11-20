# LUXIMB-A5: resultado (2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (con la enmienda 1). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Primera campaña con la partición HOLDOUT-A5.

**Datos:** `CALIBRACION.json`, `DESC.json`, `REP.json`, `CORRIDA.json`, `EVENTOS.csv.gz` (sin retornos) y `OPS_DESC_REP.csv.gz`.

## Veredicto
**MECANISMO BRUTO REPLICADO, REGLA REFUTADA EN LO ECONÓMICO. Holdout NO abierto** (queda sellado para el linaje).
- **El fade de un impulso fuerte hacia su origen tiene reversión bruta real en NQ 2006–2022:**
  - aparece en todas las celdas, también en el control sin zonas;
  - 71–88 % de los años DESC son positivos;
  - se confirma en los meses REP.
- **Las zonas en el 25 % inicial suman** +0,03 a +0,05 R en DESC (BH 8/9). En REP mantienen el signo pero no llegan al nivel: el
  mecanismo de las zonas sigue como pista, sin confirmar.
- **No es operable.** El bruto (+0,02 a +0,10 R) es menor que la fricción en R de estas operaciones:
  - 0,6–2,2 R antes de 2018;
  - 0,1–0,3 R en 2020–2022;
  - 0,11 R en ticks 2025–26 con stop 0,2·D.

## 1. Calibración (fase 0)
- **v0:** falló 12/12 por el stop de M1 al extremo de la vela (K40, enmienda 1).
- **Después de la corrección:** 11/12 calibran (corr 0,90–0,99). `z0|sl0.35` falla sólo por el signo (ambas ≈ 0) y no se nomina.

## 2. DESC (meses DESC 2006–2022, 21 pruebas, BH q 0,10)
| Celda | n | R bruto | p | años + | neto operable (n) |
|---|---|---|---|---|---|
| z0, stop 0,5·D | 106.151 | +0,017 | 9e-6 | 0,76 | −0,049 (6.742) |
| z2, stop 0,5·D | 10.183 | +0,055 | 9e-5 | 0,82 | −0,059 (521) |
| z0, stop 0,2·D | 106.151 | +0,059 | 8e-20 | 0,82 | −0,034 (403) |
| z1, stop 0,35·D | 21.373 | +0,070 | 4e-9 | 0,88 | −0,149 (658) |
| z2 − z0, stop 0,5·D | — | +0,039 | 3e-3 | — | — |

- Las 21 celdas están en `DESC.json`.
- **Nominadas:** 16 (las de 0,35·D en contraste quedan fuera porque su control no calibra).
- **Sensibilidad 2006–2011** (años que ninguna familia LUX-IMB miró con impulsos): bruto +0,03 a +0,12, mismo signo.

## 3. REP (meses REP, un paso de LORD++, nivel 0,0109)
- **Confirmadas:**
  - `z0|sl0.2`: +0,053 R, p 1,3e-5;
  - `z1|sl0.35`: +0,076 R, p 3,2e-4.
- **Las 16 conservan el signo positivo.**
- **Contrastes zonas − control:** +0,016 a +0,033, p 0,11–0,35. No confirmados.

## 4. Compuerta económica antes de abrir (escalera: «económico con costos canónicos y potencia antes de abrir»)
- **`z1|sl0.35`:** neto operable (fricción ≤ 0,08 R) −0,156 R, IC90 [−0,244; −0,070], n 784. La potencia del holdout sería 0,60 (8.475
  marcas) → **REFUTADA_ECONOMICA**.
- **`z0|sl0.2`** (control):
  - bruto +0,053 R, contra una fricción mediana en R por año de 0,18–0,33 en 2020–2022 y 0,11 en ticks 2025–26;
  - neto operable −0,018 (IC90 −0,18/+0,15, n 437, sólo 2018–2022).
  - La cota bruta no cubre la fricción de hoy, aunque la potencia alcanzaría (0,85 con 42.862 marcas) → **REFUTADA_ECONOMICA**.
- **No se abre el holdout.** Gastarlo en una regla que no puede ser operable quema la única apertura de la familia. Para un hijo
  diseñado para serlo vale más.

## 5. Qué queda y qué cambia
- **Pista (bruto):** «el fade hacia A después de un impulso fuerte revierte» es estable en 17 años, y las zonas lo aumentan (DESC).
- **Para que sea operable:**
  - el stop tiene que ser grande frente a la fricción, o el objetivo más lejano con stop amplio (palanca F-STOP-GRANDE);
  - o se usa como filtro de contexto en otra regla (zonas sí/no);
  - un hijo nuevo hereda este linaje: el holdout A5 de 2006–2022 sigue sin abrir.
- **El resultado del 2026-11-11 queda explicado:** «el visor ≈ 0 neto» era la misma historia (bruto chico, fricción mayor).
- **Herramienta:** la partición A5 funcionó de punta a punta (eventos sin retornos en todo el tramo, desenlaces sólo DESC/REP,
  conteos de holdout sin mirar).
  - Falta integrarla en el embudo, como tarea aparte.
  - K40 (stop de M1) aplica a toda medición en M1 con stops chicos.
