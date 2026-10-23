# U1-INDAGA — indagar la idea U1 antes de un P&L básico (2026-10-23)

Estado: VIGENTE — registrada antes de correr. Pedido y OK de Nico en el chat (2026-10-23): «antes de correr P&L quiero que corras variantes de esta misma variante… explorarla más, entenderla… armá vos el experimento».

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia: AREAS-EXP-1 (LUX-IMB). Código: `edgelab/research/u1_indaga.py` sobre `edgelab/research/grilla_generica.py`; kernel `tools/kaggle_grilla/kernel_u1_indaga.py`.

## Qué es U1
Sale de la réplica informativa de AREAS-EXP-1 v1.4 en USATECH:
- un área de ≥ 3 zonas LUX-IMB en 40 pts;
- el precio se aleja ≥ 8× la altura del área y vuelve el 75 % del camino;
- se opera HACIA el área, en el tick siguiente.

Replicó con +20 a +28 pts/op (p ≤ 0,0015). En NQ no se probó.

## Justificación económica
Tras un alejamiento grande, la vuelta hacia una concentración de desequilibrios puede seguir hasta el área: órdenes que quedaron sin llenar y reversión hacia el valor justo.
- **Corpus 0238** (Bhatti 2026): agotamiento del impulso y reversión a VWAP.
- **Corpus 0372**: régimen por desvío respecto del VWAP.
- **Corpus 0022:** la entrada en un retroceso con rechazo.
- **Corpus 0065** (Cenesizoglu et al.): sobrerreacción que se revierte.

## Cómo podría refutarse
- **Nada se sostiene en NQ:** si ninguna variante mantiene media neta > 0 en NQ (el futuro operable, período 2025-08 → 2026-03), U1 es propia del CFD (feed y volumen cotizado) y no un edge operable.
- **Las variables no ordenan el retorno:** si las marginales no muestran ninguna variable que lo ordene de forma monótona y en las dos fuentes, el efecto de v1.4 fue suerte de una celda.

## Variables (todas con el pasado de la vela de decisión k)
- **Piernas.**
  - **ida** = desde la última vela que cerró dentro del área hasta el extremo;
  - **vuelta** = del extremo a k.
- **Volumen por pierna:**
  - **cuánto:** `vol_ida_rel`, la tasa por vela de la ida dividida por la de la sesión anterior;
  - **en qué pierna:** `vol_vuelta/ida`, cociente de tasas;
  - **dónde:** la franja de máximo volumen de cada pierna, sobre 5 franjas entre el borde (0) y el extremo (1). Se agrupa en junto al área / medio / junto al extremo.
- **Velocidad de la vuelta frente a la ida** (agotamiento): `vel_vuelta/ida`.
- **VWAP de la sesión hasta k**, relativo al área: pasando el área / entre el área y la mitad / detrás del precio.
- **N** (3 o 5), **x** (0,33 / 0,25 / 0,15) y **A/H** (≥ 4, 8, 16): vecindad de U1 para la meseta.
- Las variables que se cortan por cuantiles toman los cortes de la misma fuente y período (terciles, modo «extremos»).

## Entradas (las propuestas de Nico, como perillas)
| entrada | qué hace |
|---|---|
| `E1A` | tick siguiente a la decisión (U1 tal cual) |
| `RET05/10/20` | espera un retroceso: límite a 5, 10 o 20 % de A más lejos del área |
| `VOL_IDA`, `VOL_VUELTA` | espera volver al volumen: límite en la franja de más volumen de esa pierna, sólo si quedó detrás del precio |
| `HACEV15`, `HACEV25` | espera a que se haga volumen: primera vela con volumen ≥ 1,5 o 2,5× la mediana de la vuelta, antes de tocar el área; entra en el tick siguiente |

- **Límites:** esperan 120 velas y se llenan si el precio los atraviesa por 1 tick.
- **Objetivos:** borde cercano (T1), mitad (T2) o borde lejano (T3).
- **Stops:** más allá del extremo (S3, el de U1) o 1× la distancia al objetivo (S2).
- **BE:** con o sin.
- **Ejecuciones:** 96 en total.
- **Ambigüedad M1:** se resuelve con el orden de los ticks.
- **Fricción:** canónica de NQ, 1,5455 pts. En USATECH es sólo referencia, porque es un CFD.

## Datos (exploración)
| fuente | período | nota |
|---|---|---|
| USATECH | 2025-08-05 → 2026-09-30 | donde nació y replicó U1 |
| NQ | 2025-08-05 → 2026-03-31 | |

**Queda sin tocar para confirmar:** NQ 2026-04-01 → 09-30 y todo lo posterior al 2026-10-01 (forward, e-proceso). USATECH 2023–2025 es sólo informativo.

## Salida
- **Marginales alrededor de U1:** se mueve una perilla por vez y se publican n, media, IC90 y p por sesiones de cada nivel. Responde qué variable ordena el retorno y cuál filtra.
- **Por canal (total y reciente):** tamiz FDR, Romano-Wolf por sesiones y 20 pistas distintas.
- **Anatomía:** distribuciones de las variables.

## Regla de selección para la confirmación (fijada ahora)
1. **Elegibles:** celdas con ≥ 20 sesiones, objetivo ≥ 3× fricción y meseta en USATECH, y con media neta > 0 en NQ (≥ 30 operaciones).
2. **Orden:** por `min(cota inferior IC90 USATECH, cota inferior IC90 NQ)`.
3. **Hasta 3 celdas,** distintas en ≥ 2 perillas, más U1 tal cual como referencia.
4. **Confirmación:** NQ 2026-04 → 09, con un procedimiento por lote (BH dentro del lote al nivel de un paso de LORD++), y después forward. Requiere el OK de Nico: es un P&L básico.

## Pruebas
- **Celdas:** 2.985.984 por fuente y canal.
- **Registro:** `u1_indaga/{total,reciente}_{usatech,nq}`, 4 entradas.
