# Diagnóstico MNQ frente a NQ y últimas tres semanas (2026-10-04)

Exploratorio, descriptivo. Sin pruebas nuevas ni criterio de éxito. Para las tres semanas se llega hasta la sesión del **2026-09-30**; las sesiones del 1 y 2 de octubre, que son el holdout formal de HOLDOUT-A1, **no se leyeron** (las filas desde 2026-09-30 22:00 UTC se descartaron sin analizar).

## 1. Por qué difieren MNQ y NQ
Mismas reglas, misma ejecución de libro, mismo período. Con comisión alineada (puntos de índice):

| | Sesiones | Operaciones | Puntos brutos por operación |
|---|---:|---:|---:|
| MNQ (copia de Kaggle) | 40 | 390 | +0,95 |
| NQ | 57 | 560 | +4,46 |
| MNQ en sesiones comunes | 39 | 376 | +1,55 |
| NQ en sesiones comunes | 39 | 385 | +2,33 |
| NQ solo en las 18 sesiones que MNQ no tiene | 18 | 175 | **+9,15** |

- **Causa principal: sesiones distintas.** MNQ no tiene (o las tiene truncadas) las 18 sesiones del 1, 2, 7, 8, 15, 16, 17, 21, 29 y 30 de julio, 5, 6, 13, 14, 18, 19, 26 y 27 de agosto. En ellas NQ ganó +9,15 puntos por operación. En las 39 sesiones comunes NQ da +2,33 y MNQ +1,55.
- **Cuando ambos operan lo mismo, coinciden.** 373 operaciones emparejadas (misma regla y sesión): correlación 0,997, mismo signo en el 98,7 %, diferencia media NQ − MNQ de −0,05 puntos. Suma diaria correlacionada 0,989. No hay diferencia atribuible al libro ni a la ejecución. Sin 2 operaciones corruptas (ver abajo) la correlación es 0,9999.
- **Operaciones sin pareja en sesiones comunes.** NQ tiene 12 que MNQ no (+226,5 puntos), casi todas de la tarde o noche en días en que la copia de MNQ está cortada; MNQ tiene 3 que NQ no (−106,8). Explican casi toda la diferencia de la suma diaria (313 puntos).
- **Artefacto de datos.** El 4-sep la copia de MNQ termina a las 20:28 UTC (15:28 CT) mientras NQ sigue; dos operaciones que debían cerrar a las 15:32 se cerraron con el primer tick disponible muchísimo después (diferencia de 46 puntos cada una). Midiendo el retraso entre la hora prevista y el tick usado: solo **2 operaciones de MNQ (0,5 %)** superan los 300 s de retraso de salida; en NQ, ES y MES ninguna; en RTY y YM entre el 1,5 % y el 2,7 % superan 60 s y ninguna supera 300 s. Efecto despreciable; el simulador no tiene una guarda explícita contra ticks tardíos y conviene añadirla.
- **Costo.** USD 1,90 por un MNQ son 0,95 puntos; USD 4,50 por un NQ son 0,225 puntos: 0,7 puntos de diferencia por operación.
- **Lectura.** NQ y MNQ se comportan igual cuando se miran las mismas sesiones. La diferencia de resultados es de **muestra** (cuáles sesiones tiene cada copia), no de instrumento. Sirve además como aviso: en 39 sesiones comunes el NQ da +2,3 puntos y en las otras 18 +9,2, lo que muestra cuánto varía el promedio con el conjunto de sesiones.

## 2. Últimas tres semanas (sesiones del 14 al 30 de septiembre)
Neto en USD por operación tras comisión. MNQ procesado con la exportación de NinjaTrader aportada por el usuario para el contrato 12-26 (ticks completos a partir del 14-sep) y la copia de Kaggle para 09-26; en las 7 sesiones comunes ambas fuentes dan operaciones idénticas (78 pares, correlación 1,0).

| Activo | Sesiones | Operaciones | Neto USD | USD por operación | Puntos por operación | % ganadoras |
|---|---:|---:|---:|---:|---:|---:|
| MNQ (export NT8) | 12 | 123 | −1.593 | −12,95 | −6,47 | 37,4 % |
| NQ | 7 | 77 | −23.696 | −307,75 | −15,39 | 32,5 % |
| ES | 7 | 67 | −7.264 | −108,42 | −2,17 | 28,4 % |
| MES | 7 | 65 | −556 | −8,55 | −1,71 | 27,7 % |
| RTY | 9 | 80 | −75 | −0,94 | −0,02 | 40,0 % |
| YM | 7 | 67 | −2.382 | −35,54 | −7,11 | 34,3 % |

- Todos los activos terminan negativos o planos en las tres semanas; el único prácticamente en cero es RTY.
- **Dos días concentran la pérdida.** 14-sep (NQ −9.142, ES −2.621, MNQ −928) y 24-sep (NQ −10.802, ES −4.350, MNQ −1.100): juntos son el 84 % del neto de NQ.
- Cobertura distinta por activo: NQ y ES no tienen datos más allá del 25-sep y excluyen el 15, 16 y 17-sep (pocos ticks por el roll); MES, RTY e YM terminan el 28-sep. Por eso los activos no cubren las mismas sesiones.
- Caveat: tres semanas son 7 a 12 sesiones y ~70 a 120 operaciones; un tramo así no distingue una mala racha de un cambio de régimen.

## 3. Antes y después de la publicación de la estrategia (observación del usuario, 2026-10-04)
Planteamiento: si las reglas se eligieron con datos hasta su publicación (≈ 2026-09-13), solo lo posterior es fuera de muestra respecto de la selección del proveedor; si cae justo después, es coherente con sobreajuste. Puntos de índice netos por operación (neto de comisión), IC95 por bootstrap de sesiones:

| Activo | 1-jul a 11-sep (antes) | 14 a 30-sep (después) |
|---|---|---|
| MNQ | +3,97 [−2,52, +11,08], 312 op., 33 ses. | −6,47 [−17,17, +5,37], 123 op., 12 ses. |
| NQ | +7,36 [+0,95, +14,57], 483 op., 50 ses. | **−15,39 [−25,74, −2,50]**, 77 op., 7 ses. |
| ES | +0,52 [−0,57, +1,85] | −2,17 [−4,19, +0,20] |
| MES | −0,28 [−1,09, +0,58] | −1,71 [−4,04, +0,23] |
| RTY | +0,15 [−0,34, +0,75] | −0,02 [−1,11, +1,07] |
| YM | +4,45 [−3,10, +13,00] | −7,11 [−14,44, +2,21] |

- Efecto estandarizado medio (en desvíos de cada activo): antes +0,058, después −0,171. En MNQ por sesión, la diferencia después − antes tiene t = −1,40 (no significativa).
- Solo el IC de NQ excluye 0 en las tres semanas, con 7 sesiones. Los seis activos no son seis pruebas independientes: son el mismo episodio de mercado, y dos días (14 y 24-sep) explican el 84 % de la pérdida de NQ.
- Consecuencia para la lectura anterior: si el proveedor eligió con datos hasta la publicación, los tramos que aquí se llamaron «OOS» (junio) y «posterior» (julio a septiembre) tampoco eran fuera de muestra para su selección. La única muestra limpia es la posterior a la publicación (las 3 semanas y, sobre todo, el holdout formal desde el 1 de octubre), y por ahora es negativa pero demasiado corta para concluir.

### 3.1 Corte con la fecha de la publicación (2026-09-10 12:00 CT)
El usuario aportó el enlace de la publicación (Instagram, reel `DdHUqDQBmgc`). No se pudo leer su contenido (requiere sesión iniciada); la fecha se derivó decodificando el código del reel (ID de medio: 2026-09-10 17:00:19 UTC), no se leyó de la página. Con ese corte (antes: sesiones del 1-jul al 10-sep; después: del 11-sep al 30-sep), puntos de índice netos por operación:

| Activo | Antes | Después |
|---|---|---|
| MNQ | +3,77 [−3,11, +11,26], 305 op., 32 ses. | −5,44 [−15,94, +5,44], 130 op., 13 ses. |
| NQ | +7,28 [+0,80, +14,82], 476 op., 49 ses. | −13,00 [−23,79, +0,34], 84 op., 8 ses. |
| ES | +0,53 [−0,57, +1,86] | −1,93 [−3,86, +0,15] |
| MES | −0,28 [−1,07, +0,59] | −1,55 [−3,68, +0,15] |
| RTY | +0,17 [−0,33, +0,81] | −0,11 [−1,12, +0,99] |
| YM | +4,52 [−2,91, +13,54] | −6,07 [−13,10, +2,22] |

Efecto estandarizado medio: antes +0,058, después −0,153. MNQ por sesión: t = −1,27 (después − antes). Con este corte ningún IC posterior excluye 0. El resultado cualitativo no cambia respecto del corte del 14-sep: negativo o plano en los seis activos, con muestra corta (8 a 13 sesiones) y activos correlacionados.
