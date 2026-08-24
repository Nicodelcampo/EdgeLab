# Registro de ramas remotas — 2026-08-24

> **Corte:** 2026-08-24 17:22 UTC  
> **Audited base:** `foundation/f0b-compatibility-probe@9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
> **Cobertura:** 26/26 ramas devueltas por GitHub; todas con tip resoluble; `protected=false` en las 26.

Este registro hace visibles las ramas. **No autoriza merges, cierres ni borrados.** Las relaciones históricas marcadas como contenidas/superadas provienen del inventario del 2026-08-15 y de documentos posteriores; donde no se reejecutó `git cherry` se declara expresamente.

## Clasificaciones

- `PRIMARY`: única rama de continuidad e integración.
- `ACTIVE_MODULE`: trabajo vigente pero aislado; no operativo todavía.
- `OPEN_PR`: rama con PR draft abierto.
- `BLOCKED_SEMANTICS`: técnicamente auditable, pero requiere decisión humana de semántica.
- `HISTORICAL_CONTAINED`: contenido integrado, patch-equivalent o sucedido; no volver a mergear a ciegas.
- `HISTORICAL_DIVERGENT`: conserva trabajo propio antiguo; comparar archivos/commits antes de borrar.
- `PARKED`: no es prioridad activa.
- `BACKUP`: preservación deliberada.
- `BASELINE`: baseline original, no rama de trabajo.

## Inventario completo

| # | Rama · tip | Clase | PR | Estado / acción siguiente |
|---:|---|---|---:|---|
| 1 | [`audit/p0-bigtrap2-drift`](https://github.com/Nicodelcampo/EdgeLab/tree/audit/p0-bigtrap2-drift) · [`1916ffa`](https://github.com/Nicodelcampo/EdgeLab/commit/1916ffa890a6eba132566826beb9f513663d7b79) | HISTORICAL_CONTAINED | — | ancestro de la línea BT2; conservar como evidencia |
| 2 | [`backup/foundation-f0b-local`](https://github.com/Nicodelcampo/EdgeLab/tree/backup/foundation-f0b-local) · [`a48efcd`](https://github.com/Nicodelcampo/EdgeLab/commit/a48efcd0d004752983680e01f3820e411da0f835) | BACKUP | — | snapshot pre-foundation; mismo tip que `preserve/*` |
| 3 | [`docs/estado-real-2026-08-10`](https://github.com/Nicodelcampo/EdgeLab/tree/docs/estado-real-2026-08-10) · [`16acc7d`](https://github.com/Nicodelcampo/EdgeLab/commit/16acc7d9eb144af48421e90276ef3c61a9b582f6) | HISTORICAL_CONTAINED | cerrado | estado antiguo; no es punto de entrada |
| 4 | [`docs/h-cond-1-lux-imb`](https://github.com/Nicodelcampo/EdgeLab/tree/docs/h-cond-1-lux-imb) · [`5530344`](https://github.com/Nicodelcampo/EdgeLab/commit/5530344c9879668b1102a82e85931ec3252e64f2) | HISTORICAL_CONTAINED | cerrado | protocolo histórico; su premisa fue corregida después |
| 5 | [`docs/h-sweep-1-ym-prerange`](https://github.com/Nicodelcampo/EdgeLab/tree/docs/h-sweep-1-ym-prerange) · [`2df700f`](https://github.com/Nicodelcampo/EdgeLab/commit/2df700f475865cc591fceda09c92288b5bed9e65) | HISTORICAL_CONTAINED | cerrado | documentación integrada/sucedida |
| 6 | [`docs/lux-imb-source-correction`](https://github.com/Nicodelcampo/EdgeLab/tree/docs/lux-imb-source-correction) · [`3383d88`](https://github.com/Nicodelcampo/EdgeLab/commit/3383d8827e304ffd65a580efd5650f1eff88a428) | HISTORICAL_CONTAINED | cerrado | corrección aplicada según PENDIENTE; no duplicar |
| 7 | [`docs/post-merge-sync-2026-08-10`](https://github.com/Nicodelcampo/EdgeLab/tree/docs/post-merge-sync-2026-08-10) · [`be1fcfa`](https://github.com/Nicodelcampo/EdgeLab/commit/be1fcfab9eac39373f6abd088e06b2fcd0dd9eb5) | HISTORICAL_CONTAINED | cerrado | sincronización histórica |
| 8 | [`fix/bigtrap2-v252-tick-export`](https://github.com/Nicodelcampo/EdgeLab/tree/fix/bigtrap2-v252-tick-export) · [`6a858fd`](https://github.com/Nicodelcampo/EdgeLab/commit/6a858fdc31e1a65bb504c18e74be77d1ed1d78c1) | OPEN_PR | #12 | sin check-runs; base histórica `audit/p0`; comparar con foundation antes de integrar |
| 9 | [`fix/capture-probe-v2-contract`](https://github.com/Nicodelcampo/EdgeLab/tree/fix/capture-probe-v2-contract) · [`8b85add`](https://github.com/Nicodelcampo/EdgeLab/commit/8b85add310cc8456531e2e1524cf09419f9f50aa) | HISTORICAL_DIVERGENT | — | línea grande del 6-ago; contenido parcialmente sucedido; requiere diff mecánico antes de archivar |
| 10 | [`fix/g2-a1-calibration-hardening`](https://github.com/Nicodelcampo/EdgeLab/tree/fix/g2-a1-calibration-hardening) · [`3c06e9c`](https://github.com/Nicodelcampo/EdgeLab/commit/3c06e9c0ebebf0f37125c306e8bda02ff2f07e4a) | BLOCKED_SEMANTICS | #8 | dos checks verdes; no mergear hasta adjudicar el contrato rival |
| 11 | [`fix/g2-a1-statistical-semantics`](https://github.com/Nicodelcampo/EdgeLab/tree/fix/g2-a1-statistical-semantics) · [`f3b8263`](https://github.com/Nicodelcampo/EdgeLab/commit/f3b826395336425b698842a481b2ee67f5877940) | BLOCKED_SEMANTICS | — | contrato rival de #8; adjudicar P-10/P-38 en conjunto |
| 12 | [`foundation/f0b-compatibility-probe`](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) · [`9b23c30`](https://github.com/Nicodelcampo/EdgeLab/commit/9b23c307cb112cdd6392d98673e8ead2e8bc4698) | PRIMARY | base de #8/#9/#14 | rama viva y único punto de integración |
| 13 | [`main`](https://github.com/Nicodelcampo/EdgeLab/tree/main) · [`cde6d93`](https://github.com/Nicodelcampo/EdgeLab/commit/cde6d93a75240f550db1fc3b96ca90605ca967c8) | BASELINE | — | baseline original; tag `baseline-pre-foundation`; no trabajar aquí |
| 14 | [`prep/indicator-onboarding-registry`](https://github.com/Nicodelcampo/EdgeLab/tree/prep/indicator-onboarding-registry) · [`c47a687`](https://github.com/Nicodelcampo/EdgeLab/commit/c47a687224ddf6bedff97c07e940d2db44f009d5) | OPEN_PR / PARKED | #9 | check verde; F9 aparcada, no prioridad |
| 15 | [`preserve/f0b-local-divergente-2026-08-04`](https://github.com/Nicodelcampo/EdgeLab/tree/preserve/f0b-local-divergente-2026-08-04) · [`a48efcd`](https://github.com/Nicodelcampo/EdgeLab/commit/a48efcd0d004752983680e01f3820e411da0f835) | BACKUP | — | preservación redundante con `backup/*`; no borrar sin decisión |
| 16 | [`registry/gex-familia`](https://github.com/Nicodelcampo/EdgeLab/tree/registry/gex-familia) · [`f065df2`](https://github.com/Nicodelcampo/EdgeLab/commit/f065df2146c2cc4e51bcd1c28dab81a6f3946394) | PARKED | — | familia observacional; no se revalidó relación por `git cherry`; comparar antes de integrar/archivar |
| 17 | [`research/bigtrap2-distance-matched-null`](https://github.com/Nicodelcampo/EdgeLab/tree/research/bigtrap2-distance-matched-null) · [`2374832`](https://github.com/Nicodelcampo/EdgeLab/commit/2374832466c0436d9ccac708800e7e229552f313) | OPEN_PR / HISTORICAL_CONTAINED | #11 | inventario 15-ago: 100 % patch-equivalent pre-rebase; no mergear de nuevo |
| 18 | [`research/bigtrap2-local-displacement-null`](https://github.com/Nicodelcampo/EdgeLab/tree/research/bigtrap2-local-displacement-null) · [`29d78eb`](https://github.com/Nicodelcampo/EdgeLab/commit/29d78eba662cf6ffbb146b46287a0476b743a8e1) | HISTORICAL_CONTAINED | base de #13 | antigua rama viva; foundation es su sucesora operativa |
| 19 | [`research/bigtrap2-multiframe-ml`](https://github.com/Nicodelcampo/EdgeLab/tree/research/bigtrap2-multiframe-ml) · [`05d2da7`](https://github.com/Nicodelcampo/EdgeLab/commit/05d2da7525f528e26778c53174840e31a038440c) | PARKED | — | contrato ML/multiframe antiguo; contiene la línea v2.5.2; no reactivar sin manifiesto/STOP |
| 20 | [`research/bigtrap2-soporte-balance-curve`](https://github.com/Nicodelcampo/EdgeLab/tree/research/bigtrap2-soporte-balance-curve) · [`a856821`](https://github.com/Nicodelcampo/EdgeLab/commit/a856821c4249ebb26af56f3cc4a129963e406b6e) | HISTORICAL_CONTAINED | — | ancestro de local-displacement |
| 21 | [`research/gate-regime-context`](https://github.com/Nicodelcampo/EdgeLab/tree/research/gate-regime-context) · [`c882cf5`](https://github.com/Nicodelcampo/EdgeLab/commit/c882cf521104f4ab0199dfe4db09118bb72836a9) | ACTIVE_MODULE | — | cimiento ejecutable; checkpoint pendiente con datos reales; no operativo |
| 22 | [`research/ym-prerange-session-window`](https://github.com/Nicodelcampo/EdgeLab/tree/research/ym-prerange-session-window) · [`0c44813`](https://github.com/Nicodelcampo/EdgeLab/commit/0c44813069af54838eca2144c007ede076b94c9b) | HISTORICAL_CONTAINED | cerrado | PENDIENTE registra integración; mantener sólo como referencia |
| 23 | [`research/zamr1-zone-atlas`](https://github.com/Nicodelcampo/EdgeLab/tree/research/zamr1-zone-atlas) · [`b74f7bd`](https://github.com/Nicodelcampo/EdgeLab/commit/b74f7bdc68acca3022ba6dc6f6258eed0cb3093d) | OPEN_PR / PARKED | #13 | dos checks verdes; base histórica; siguiente trabajo redirigido fuera de la rama |
| 24 | [`work/crypto-context-foundation-20260824`](https://github.com/Nicodelcampo/EdgeLab/tree/work/crypto-context-foundation-20260824) · [`973a06f`](https://github.com/Nicodelcampo/EdgeLab/commit/973a06fa8f1240ad064d75e136805ae5072fb721) | ACTIVE_MODULE / OPEN_PR | #14 | dos checks rojos; auditar, no mergear |
| 25 | [`work/repository-research-iterations`](https://github.com/Nicodelcampo/EdgeLab/tree/work/repository-research-iterations) · [`5abf9b6`](https://github.com/Nicodelcampo/EdgeLab/commit/5abf9b68ccc173d74d6315d9273d7b938d748d75) | HISTORICAL_DIVERGENT | — | iteraciones documentales del 4-ago; no implementación vigente |
| 26 | [`work/research-architecture-hardening`](https://github.com/Nicodelcampo/EdgeLab/tree/work/research-architecture-hardening) · [`a2b3527`](https://github.com/Nicodelcampo/EdgeLab/commit/a2b3527bc1d2b359cad45d8577d5fa509bcb2afb) | HISTORICAL_DIVERGENT | — | arquitectura temprana; comparar sólo si una decisión la necesita |

## Reglas para operar con este registro

1. Antes de tocar una rama: `git fetch --all --prune` y verificar su tip contra esta tabla.
2. Si el tip cambió, actualizar el registry antes de interpretar resultados.
3. Para declarar `contenida`, reejecutar `git merge-base --is-ancestor` y `git cherry`; patch-equivalent y ancestro no son lo mismo.
4. No usar el campo inconsistente `merged` del listado de PRs cerrados como única evidencia: varios devolvieron `merged=false` junto a `merged_at` no nulo.
5. Ninguna rama está protegida: la accesibilidad técnica aumenta la necesidad de disciplina; no autoriza push directo.
6. No borrar una rama hasta que su contenido propio, PR, documentación y artefactos externos tengan destino explícito.

## Aporte al referente

Cada línea divergente tiene ahora tip, URL, clase, PR y siguiente acción. Esto reduce el riesgo de repetir el incidente de dos máquinas midiendo ramas distintas o de reintroducir historia patch-equivalent como si fuera trabajo nuevo.