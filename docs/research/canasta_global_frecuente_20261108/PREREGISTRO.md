# Pre-registro: CANASTA-GLOBAL-FRECUENTE — la misma búsqueda exigiendo frecuencia (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr; Nico: «vamos a tener que buscar estrategias que operen más seguido. Mucho más»).
Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. EF4. Familia
CANASTA_GLOBAL_FRECUENTE, hija de CANASTA_GLOBAL.

Igual que `docs/research/canasta_global_20261108/PREREGISTRO.md` (mismos 106 cubos, ventana, 5 sub-bloques, estabilidad, correlación,
diversificación, nulo de la selección completa con B = 200), con dos exigencias nuevas, aplicadas también en cada réplica del nulo:
- **Cada regla:** al menos **0,5 operaciones por sesión** en la ventana (≈ 169 operaciones en 338 sesiones; antes bastaban 30).
- **La canasta:** al menos **3 operaciones por sesión** sumando sus reglas; si no, queda vacía.

**Por qué:** el holdout de CANASTA-GLOBAL tuvo 30 operaciones en 14 sesiones; con eso nada se confirma. Una canasta frecuente acumula
en semanas la evidencia que la anterior junta en años. **Cómo podría refutarse:** p ≥ 0,10, o ninguna canasta cumple la frecuencia.
Si p < 0,10: apertura exploratoria del holdout (pre-registro aparte), combinación Fisher.
