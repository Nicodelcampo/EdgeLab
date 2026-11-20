# Reserva pre-frontera en las próximas campañas (decisión de Nico, 2026-11-17)

Estado: SUPERADA por HOLDOUT-A5 (2026-11-17, `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`: septiembre 2026 es mes HOLDOUT en la asignación). Era: decisión de diseño para campañas NUEVAS (no aplica a la cosecha v4 ni a nada ya medido). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Texto de Nico: «con hacia atrás me refiero a que empiece un mes antes, por ejemplo septiembre de 2026 … para las próximas corridas, no
estas». Objetivo: necesitar menos forward.

## Regla
1. Toda campaña nueva declara en su pre-registro una **reserva**: el último tramo de desarrollo antes de la frontera (por defecto
   **2026-09-01 → 2026-09-30**) que **ni el DESC, ni la réplica, ni las pistas, ni la selección tocan**. Con la partición A3 eso deja
   DESC ago-25 → mar-26 y réplica abr → ago-26.
2. La confirmación de la familia (su única apertura) lee **reserva + holdout sellado + forward** como una sola serie, con e-proceso desde
   el inicio de la reserva. La reserva cuenta como el primer tramo del holdout de esa familia.
3. Sólo vale para familias cuyo linaje no miró ese tramo (`holdout_ventanas` + `LINAJES.jsonl`): una familia derivada de otra que ya usó
   septiembre no puede reservarlo.
4. Se declara ANTES de correr el DESC; nunca se agrega a una campaña ya mirada (sería elegir con esos datos).

## Por qué
Septiembre no sirve para las campañas viejas porque su réplica lo usó para elegir (sesgo de selección: paso 2 de
`urgencia_vs_evidencia_20261117`). Reservado de antemano, es tan limpio como el holdout y ya está disponible: la confirmación arranca con
≈ 1 mes de datos en la mano (≈ 1 mes menos de forward) a cambio de 1/6 menos de réplica.

## Implementación
Pendiente para la próxima campaña del embudo: campo `reserva` en la spec, validación de que DESC/OOS/pistas no la solapen
(`embudo.validar`), y lectura de la reserva con el runner de desarrollo concatenada a la del dataset sellado en la etapa HOLDOUT. Hasta
que esté en código, una campaña que la use la lee como la cosecha v4 (`tools/cosecha_pozo.py`): dos corridas y una sola serie.
