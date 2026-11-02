# Decisión 2026-11-02: el control de ruido del preflight usa el FDR

Estado: VIGENTE. Decidió Nico el 2026-11-02 en la sesión en la nube («opción 1, relanzá las 6»). Es un cambio de un gate de validación,
y por eso es una decisión humana.

## Qué cambia
`edgelab/research/preflight.py`, chequeo «ruido puro».
- **Antes:** error si Romano-Wolf rechazaba alguna celda sobre ruido.
- **Ahora:** error si el FDR q 0,10 nomina alguna celda sobre ruido, que es la misma compuerta que nomina en DESC desde el
  2026-10-24. Un rechazo de Romano-Wolf queda como aviso.

## Por qué
Ver `docs/research/relanzamiento_causal_20261102/RELANZAMIENTO.md`. Con `B_RW = 40` y pagos muy asimétricos, Romano-Wolf rechazó una
celda en 2 de 6 semillas de ruido, cuando lo nominal es alrededor del 5 %. El simulador no tenía sesgo: la auditoría vela a vela dio
0 fallas y todas las ejecuciones son negativas sobre ruido. El FDR no nominó nada en ninguna semilla.

## Qué no cambia
- La nominación en DESC (FDR q 0,10).
- LORD++, las réplicas, el OOS y el holdout.
