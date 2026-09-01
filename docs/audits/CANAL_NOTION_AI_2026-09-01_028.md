# Canal 028 — corrección del board y de mi propia verificación

**Fecha:** 2026-09-01

## Corrección

Mi afirmación previa de «PENDIENTE.md restaurado íntegro y verificado» fue falsa. La
verificación confirmó existencia/tamaño/blob del archivo que yo acababa de escribir,
pero no comparó su contenido con el board preexistente. La restauración `bca71898`
(blob `f924a60d`, 15.003 B) era una reescritura condensada; el linaje real era
`e2e0cf40` → `252215c1` (108.777 → 112.595 B).

La corrección no consiste en copiar otra vez 112 KB a esta rama: se elimina la segunda
fuente de verdad. `PENDIENTE.md` queda como puntero al board largo idéntico en
`foundation/f0b-compatibility-probe` y
`research/avolcluster-nq-parity-oracle-20260901` (blob `252215c1`).

## Colisión resuelta

- P-56…P-59 del board largo conservan su número por precedencia temporal.
- Canal 017: «tres palancas» se referencia desde ahora como **P-60**, no P-58.
- Canal 018: «ML/LightGBM» se referencia desde ahora como **P-61**, no P-59.
- Las entradas exclusivas del condensado sin artefactos verificables quedan en
  cuarentena, no promovidas al board.

Acta completa: `docs/audits/PENDIENTE_RECONCILIACION_2026-09-01.md`.

## Regla aprendida

Verificar que un push aterrizó no verifica que el contenido sea el correcto. Para una
restauración hay que cerrar las dos identidades: blob/bytes del destino **y linaje del
contenido de origen**.

**Aporte al referente:** elimina la colisión sin fabricar una tercera copia canónica,
preserva la precedencia histórica P-56…P-59, deja P-60/P-61 trazables y convierte mi
propio error de verificación en una regla mecánica para futuros restores.
