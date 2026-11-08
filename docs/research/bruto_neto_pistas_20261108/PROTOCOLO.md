# Protocolo: ¿las pistas que pierden en réplica tienen señal bruta? (08/11/2026)

Estado: PROTOCOLO (escrito antes de lanzar; pedido de Nico: «dale con todo» al plan del 08/11). Referente `docs/NORTH_STAR.md`,
cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **EXPLORATORIO / diagnóstico:** las celdas ya
se miraron; nada se promueve desde acá. No toca el holdout (período: inicio del DESC → 30/09/2026).

## Pregunta

En 86 campañas en R que llegaron a la réplica de pistas, las canastas dan casi siempre ≤ 0 R por operación. Dos explicaciones
cambian qué hacer después:
- **SIN SEÑAL:** en bruto (sin costos) las pistas también dan ≈ 0 en la réplica. Lo que se eligió en DESC era ruido (maldición del
  ganador). Respuesta: otra clase de idea, no otra variante.
- **FRICCIÓN:** en bruto dan > 0 en la réplica y los costos se lo comen. Hay señal; el problema es de ejecución (recorrido por viaje
  de fricción, entradas límite, menos operaciones más grandes).

## Medición

- Por campaña: etapa ANALIZAR_REGLA (`tools/equity_pistas.py`, el mismo motor que eligió las celdas) sobre las pistas congeladas, con
  operaciones; período DESC + réplica.
- Por operación: R neto y riesgo en puntos. **R bruto = R neto + fricción canónica base en puntos / riesgo** (`embudo_runners.friccion`,
  `edgelab/costos.py`). Costo en R = fricción / riesgo.
- Canasta como la del embudo: media por sesión de las pistas (suma / k), luego media de sesiones; IC90 por bootstrap de sesiones.
- Se reporta para DESC (lo elegido, inflado por selección) y réplica (lo que importa): bruto, neto y costo en R.

## Clasificación (fijada antes de ver los datos), sobre la réplica

- **FRICCIÓN:** cota inferior del IC90 del bruto > 0 y media neta ≤ 0.
- **SEÑAL NETA:** cota inferior del IC90 del neto > 0 (no se espera; se lista aparte, no se promueve desde acá).
- **SIN SEÑAL:** cota superior del IC90 del bruto ≤ costo medio en R (aun sin costos no alcanzaría a cubrirlos) o media bruta ≤ 0.
- **INDETERMINADO:** el resto (IC90 del bruto cruza 0 y su cota superior pasa el costo).

Agregado: proporción de campañas en cada clase y media bruta ponderada por sesiones en réplica. Si FRICCIÓN ≥ 25 % de las
campañas con potencia, la siguiente familia se diseña alrededor de la ejecución; si SIN SEÑAL domina, se cambia de clase de idea.

**Cómo podría refutarse la lectura:** si el bruto de la réplica está sesgado por la propia selección (las pistas se eligieron por
neto en DESC, no en réplica, así que la réplica no está sesgada por selección; sí lo está el DESC, que se reporta sólo como contraste).
