# Decisiones del 2026-11-08

Estado: VIGENTE — decisiones de Nico del 08/11/2026 (regla global de evidencia, holdout exploratorio).


## Regla global: estabilidad entre días, sub-bloques y canastas diversificadas (Nico, 08/11)

Decisión de Nico: «utilizar la estabilidad entre los días y también usar sub bloques para añadir potencia… reducir y diversificar
el riesgo. Si una estrategia es rentable en varios períodos independientes que reducen la probabilidad de que sea azar a menos de
por ejemplo 10 %, una canasta de estrategias con esas características va a ser rentable estadísticamente».
- La unidad de evidencia es la sesión; la estabilidad se mide en sub-bloques independientes del período de desarrollo.
- Se eligen canastas de reglas poco correlacionadas y de varios activos, no la mejor regla aislada.
- La probabilidad de azar se estima con un nulo que repite TODA la selección (inversión de signo por sesión, la misma para todas
  las reglas), para que elegir entre muchas no la infle; el objetivo es < 10 %.
- La confirmación es en el holdout, con la canasta congelada antes de abrirlo. Primera aplicación: ORB (`docs/research/orb_nq_20261108/PREREGISTRO_CANASTA.md`).

## Holdout exploratorio y más ritmo del agente (Nico, 08/11)

«Que sí lo pueda abrir»: el agente puede abrir el holdout de una familia sin candidato confirmado (modo exploratorio de
`edgelab/autopilot/holdout_apertura.py`), declarando antes la probabilidad de azar de desarrollo y la combinación. Topes diarios de
Opus y Sonnet más altos, sin tope diario de corridas (hace las necesarias) y 8 en paralelo: el agente usa el plan Max.
