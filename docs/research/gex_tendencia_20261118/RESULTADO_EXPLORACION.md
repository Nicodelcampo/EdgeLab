# GEX a fondo: exploración en DESC (fase 1, EF2, 2026-11-18)

Estado: RESULTADO EXPLORATORIO — todo en meses DESC de A5, contado en el registro (54 medidas). **No es confirmación.** El hallazgo
principal: **la gamma de los dealers no sirve para tomar una dirección, pero sí para decidir CUÁNDO operar las reglas de tendencia.**
Con gamma alta, T, Franklin, SOM y ORB pierden; con gamma baja, ganan.
- **Pre-registro:** `PREREGISTRO.md`. **Datos:** `TABLA_DESC.csv.gz`, `EXPLORACION.json` y `TABLA_DESC_CONTROL_VOL.csv.gz`.
- **Herramienta:** `tools/gex_tendencia.py`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. La gamma anticipa la MAGNITUD del día, también descontando la volatilidad
NQ/ES/YM/RTY, 1.966 días DESC con GEX. Spearman con el signo económico (menos gamma, más movimiento):

| Variante | Rango/ATR20 | \|cierre − apertura\|/ATR20 | Parcial rango (controla vol) | Parcial \|c−o\| (controla vol) |
|---|---|---|---|---|
| `g_z20` (gamma contra sus 20 días) | **0,35** | 0,19 | **0,23** | **0,11** |
| `g_rank60` | 0,28 | 0,16 | 0,17 | 0,09 |
| `g_rank250` | 0,22 | 0,15 | 0,12 | 0,09 |
| `g_neg`, `g_chg`, DIX | ≤ 0,18 | ≤ 0,10 | — | — |

- **Control de volatilidad:** rango de ayer / ATR20 y ATR5 / ATR20 (sola: 0,31 y 0,19).
- **Lectura:** la gamma relativa a sus últimas semanas agrega información propia sobre cuánto se va a mover el día. El mismo signo
  aparece en los 4 índices (0,25–0,40).
- **La etiqueta binaria** (AUC 0,52–0,54) desperdiciaba esta señal.

## 2. Reglas direccionales con gamma: no pagan
- **Continuación desde las 10:00** en la dirección de 09:30–10:00, sólo con gamma baja: +0,035 ATR bruto, +0,012 neto (desvío
  0,73). Potencia del holdout ≈ 0,04.
- **Momentum del cierre (Baltussen)** de 15:30 a 16:00 con gamma baja: +0,027 ATR bruto, neto ≈ 0.
- **Lectura:** la gamma no dice para dónde. Dice si el día va a moverse.

## 3. La gamma como filtro de las reglas de tendencia (lo importante)
R por operación en meses DESC, por tercil de `g_rank250` del cierre previo:

| Regla | Baja | Media | Alta | Baja − alta (p) |
|---|---|---|---|---|
| T (neto) | +0,035 | −0,011 | **−0,110** | +0,145 (0,001) |
| Franklin (neto) | +0,099 | −0,020 | **−0,106** | +0,205 (0,007) |
| SOM (neto) | +0,006 | +0,040 | −0,052 | +0,058 (0,047) |
| ORB O1 (bruto) | +0,177 | +0,144 | +0,070 | +0,107 (0,15) |

**Canasta T + Franklin + SOM** (NQ/ES/YM, R neto por día):
- por tercil: baja **+0,305**, media +0,033, alta **−0,569**;
- baja − alta: +0,87 R/día (EE 0,24), en 12 de 15 años;
- **«No operar con gamma alta»:** −0,077 → **+0,169 R por día**.

**Lectura:**
- El mecanismo predicho por el E0 (menos gamma, más días de tendencia) aparece como dinero en cuatro reglas distintas, con
  dosis-respuesta monótona.
- Que sean cuatro reglas independientes, con el mismo signo, es una réplica interna del mecanismo. No es selección: las variantes de
  gamma probadas son 2.

## 4. Lo que falta: confirmación
| Fuente | Días | Potencia (efecto ×0,5 / ×0,75 / ×1) | Problema |
|---|---|---|---|
| Holdout A5 (sellado para la familia) | 941 | 0,15 / 0,34 / 0,58 | poca potencia |
| REP + HOLDOUT A5 | 1.596 | 0,25 / 0,56 / 0,83 | el R TOTAL de T/Franklin/SOM en esos meses ya se miró (nunca cruzado con gamma) |
| Forward desde la frontera | creciente | — | hay que mantener GEX diario |

Decidir si los meses REP + HOLDOUT valen para confirmar una condición nueva sobre reglas cuyo agregado ya se miró es una decisión de
semántica de validación: **se consulta con Nico**.
