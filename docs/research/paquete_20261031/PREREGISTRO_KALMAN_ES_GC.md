# KALMAN-FADE en ES y GC — anexo al pre-registro (2026-10-31)

Estado: VIGENTE (antes de cualquier corrida; aprobado por Nico en la sesión en la nube, 31-oct).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF2 → embudo.

Misma especificación que `docs/research/kalman_fade_20261030/SPEC_KALMAN_FADE.md` (módulo sin cambios, 216 celdas por canal), en dos
instrumentos más, cada uno como familia propia (`KALMAN_FADE_ES`, `KALMAN_FADE_GC`), como propone el paquete del 31-oct. KALMAN-FADE-NQ
se lanza tal como fue pre-registrado el 30-oct. La extensión con R adaptativo al volumen y velocidad de Ornstein-Uhlenbeck **no** se
construye todavía: según la espiral, se construye sólo sobre lo que sobreviva a esta primera vuelta (si las tres refutan, no hay
sobre qué extender). La perilla `regimen_vol` ya cubre la condición de régimen que el paquete propone para la v2.
