# Pre-registro — VI coincidentes futuro/índice: reacción a 30 min (2026-10-22)

Estado: VIGENTE (congelado antes de mirar los datos de este período)

- **Origen:** pista exploratoria del 2026-10-22 (`COMPORTAMIENTO_COINCIDENTES_NQ_USATECH.json`, jul–sep 2026). Los VI del futuro NQ que también nacen en el índice USATECH (Dukascopy) reaccionaron +5,2 pts a 30 min, contra +1,1 los que no. La diferencia era +4,0, con IC [−0,6, +8,7] y p de Holm 0,42 sobre 6 pruebas. **Es la mejor de 6: no es evidencia.**
- **OK de Nico:** 2026-10-22 («OK»).
- **Etapa del embudo:** EF2/EF5. Es una sola hipótesis, en un período que esta pregunta no tocó. No es réplica limpia de la familia LUX-IMB, que ya miró estos meses en el visor.
- **Contador global:** `luximb_20261022/vi_coincidentes_reaccion30_rep`, con 1 prueba, registrada antes de correr.
- **Referente:** `docs/NORTH_STAR.md` (sha256 del cuerpo `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`).

## Datos
- **Futuro:** NQ, bundles `NQ_09-25`, `NQ_12-25` y `NQ_03-26` (M1, zonas LUX-IMB con paridad NT8). Cada contrato se usa sólo dentro de su ventana de trade date: 2025-08-05 → 2026-03-16.
- **Índice:** USATECH de Dukascopy, M1 (mid), en el mismo período. Las zonas salen del mismo detector (`build_luximb_spot_m1_bundle.py`).
- **Base futuro − índice:** mediana móvil de 4 h de la diferencia de cierres, estimada por separado para cada contrato.
- Todo el período es anterior al holdout.

## Población
- Todos los VI del futuro creados en el período.
- **Coincidente** = existe un VI del índice con el mismo tipo y dirección, creado a 1 minuto o menos, que se superpone en precio una vez sumada la base. El emparejamiento es uno a uno. Es la misma regla que en jul–sep.

## Medida (única)
`reac30`:
- se mide desde el cierre de la vela M1 del futuro donde el precio toca la zona por primera vez, dentro de su vida de 500 min;
- es el cierre 30 min después menos ese cierre, firmado a favor de la zona (alcista hacia arriba, bajista hacia abajo), en puntos;
- sin toque no hay medida;
- si entre las dos velas hay más de 60 min (hueco de sesión), tampoco se mide.

## Hipótesis y decisión
- **H1:** el coeficiente de «coincidente» es mayor que 0 en la regresión `reac30 ~ coincidente + log(altura de la zona en ticks) + hora UTC de creación (24 dummies) + dirección`. Así se controla que la diferencia no sea de tamaño ni de horario.
- **Inferencia:** bootstrap por días (4.000 repeticiones, semilla 20261022) del coeficiente. p unilateral = fracción ≤ 0. Se informan también el IC 90 % y la diferencia cruda de medias.
- **Confirma** si p ≤ 0,05 **y** el coeficiente es mayor que 1,55 pts, que es la fricción canónica de NQ por viaje.
- **Refuta** si la cota superior del IC 90 % es menor que 1,55 pts.
- **Si no se da ninguna de las dos:** SIN_POTENCIA, y se informa el n que haría falta.
- **Potencia:** se informa el MDE.

## Cómo podría refutarse
Si el coeficiente controlado da ≤ 0 o su cota optimista no supera la fricción, la pista de jul–sep era selección o confusión. Se archiva con este alcance: sólo VI, sólo reacción a 30 min, NQ contra USATECH.

## Justificación económica
Un VI que aparece a la vez en el futuro y en el índice de contado refleja un desbalance de todo el mercado, no ruido propio del futuro (roll, libro, spread). Sería más informativo sobre la dirección de corto plazo. La coincidencia se conoce en el mismo minuto de la creación, así que es causal si se tiene el feed del índice en vivo.

## Qué NO se hace
No se cambia la medida, el horizonte ni la tolerancia después de ver el resultado. No se prueban OG ni otras medidas en esta corrida. Si confirma, recién ahí se arma una regla exacta (entrada, stop, salida y costos) con la escalera del embudo.
