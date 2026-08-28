# Registro de ramas remotas — 2026-08-28

> **Corte:** 2026-08-28 05:04 UTC  
> **Cobertura:** 44/44 ramas devueltas por GitHub.  
> **Protección:** 0/44 protegidas.  
> **Base de integración:** `foundation/f0b-compatibility-probe@8ebda7840bc3f0a7e39f3561db75a2c9090fd55f`.

Este registro hace visibles las refs. **No autoriza merges, cierres ni borrados.** Las clasificaciones que requieren ancestry o patch-equivalence quedan pendientes de verificación mecánica local.

## Clases

- `INTEGRATION_BASE`: base vigente.
- `ACTIVE_RESEARCH`: campaña viva aislada.
- `OPEN_PR`: rama con PR abierta.
- `RESULT`: publicación de resultados; no equivale a promoción.
- `HISTORICAL`: conservar hasta adjudicación mecánica.
- `PARKED`: fuera de foco; requiere nuevo STOP para reactivar.
- `BACKUP`: preservación deliberada.
- `BASELINE`: baseline antiguo, no rama de trabajo.
- `TRACEABILITY`: actualización documental sin autorización científica.

## Inventario

| # | Rama · tip | Clase | PR / acción |
|---:|---|---|---|
| 1 | `audit/p0-bigtrap2-drift` · `1916ffa` | HISTORICAL | conservar evidencia |
| 2 | `backup/foundation-f0b-local` · `a48efcd` | BACKUP | no borrar |
| 3 | `docs/es-apriori-2026-08-25` · `a73f57f` | HISTORICAL | adjudicar diff |
| 4 | `docs/estado-real-2026-08-10` · `16acc7d` | HISTORICAL | estado antiguo |
| 5 | `docs/h-cond-1-lux-imb` · `5530344` | HISTORICAL | protocolo sucedido |
| 6 | `docs/h-sweep-1-ym-prerange` · `2df700f` | HISTORICAL | documentación sucedida |
| 7 | `docs/handoff-2026-08-25` · `4b73df7` | HISTORICAL | preservar handoff |
| 8 | `docs/lecciones-2026-08-24` · `a8ab114` | HISTORICAL | adjudicar integración |
| 9 | `docs/lux-imb-source-correction` · `3383d88` | HISTORICAL | corrección histórica |
| 10 | `docs/mbt-apriori-2026-08-25` · `e2c7bf2` | HISTORICAL | adjudicar diff |
| 11 | `docs/post-merge-sync-2026-08-10` · `be1fcfa` | HISTORICAL | sincronización histórica |
| 12 | `fix/bigtrap2-v252-tick-export` · `6a858fd` | OPEN_PR | #12 |
| 13 | `fix/capture-probe-v2-contract` · `8b85add` | HISTORICAL | diff mecánico pendiente |
| 14 | `fix/g2-a1-calibration-hardening` · `3c06e9c` | OPEN_PR | #8; semántica pendiente |
| 15 | `fix/g2-a1-statistical-semantics` · `f3b8263` | HISTORICAL | contrato rival; no adjudicar por CI |
| 16 | `fix/sweep-finalize-contract-scope` · `ee07c34` | HISTORICAL | verificar contención |
| 17 | `foundation/f0b-compatibility-probe` · `8ebda78` | INTEGRATION_BASE | base vigente |
| 18 | `main` · `cde6d93` | BASELINE | no trabajar aquí |
| 19 | `prep/indicator-onboarding-registry` · `c47a687` | OPEN_PR / PARKED | #9 |
| 20 | `preserve/f0b-local-divergente-2026-08-04` · `a48efcd` | BACKUP | no borrar |
| 21 | `registry/gex-familia` · `f065df2` | PARKED | revalidar antes de activar |
| 22 | `research/avol-bt2-two-stage-v0-20260827` · `cde6d93` | PARKED | ref vacía sobre baseline |
| 23 | `research/avolcluster-compression-v1-20260827` · `e53fcf6` | ACTIVE_RESEARCH / OPEN_PR | #19 |
| 24 | `research/avolcluster-nq-microticks-v1-20260828` · `3961b67` | ACTIVE_RESEARCH | resultado target-free; falta PR/spec Gate 1 |
| 25 | `research/bigtrap2-distance-matched-null` · `2374832` | OPEN_PR / HISTORICAL | #11 |
| 26 | `research/bigtrap2-local-displacement-null` · `29d78eb` | HISTORICAL | base de #13 |
| 27 | `research/bigtrap2-multiframe-ml` · `05d2da7` | PARKED | no reactivar sin manifest/STOP |
| 28 | `research/bigtrap2-soporte-balance-curve` · `a856821` | HISTORICAL | preservar |
| 29 | `research/bt2a-p2a-clock-heterogeneity-v1-20260827` · `56717b0` | ACTIVE_RESEARCH / OPEN_PR | #20; freeze bloqueado |
| 30 | `research/bt2a-p2b-economic-gc-v1-20260827` · `9d71b60` | ACTIVE_RESEARCH / OPEN_PR | #18 |
| 31 | `research/event-store-pit` · `4d6c6b1` | ACTIVE_RESEARCH | recomputación/estado pendiente |
| 32 | `research/gate-regime-context` · `c882cf5` | ACTIVE_RESEARCH | infraestructura, no resultado operativo |
| 33 | `research/ym-prerange-session-window` · `0c44813` | HISTORICAL | conservar referencia |
| 34 | `research/zamr1-zone-atlas` · `b74f7bd` | OPEN_PR / PARKED | #13 |
| 35 | `results/bt2a-p2a-v1-r1-20260827` · `7a9959f` | RESULT / OPEN_PR | #16; no confirmatorio |
| 36 | `work/bt2a-gate1-all5-20260826` · `3e639e1` | HISTORICAL / RESULT | Event Store fuente |
| 37 | `work/bt2a-gate1-runner-20260826` · `f5fd49d` | HISTORICAL | runner antecesor |
| 38 | `work/bt2a-gate2-l2-audit-20260826` · `f4b7e60` | HISTORICAL | auditoría L2 |
| 39 | `work/bt2a-gate2-l2-hardening-20260826` · `761f50b` | ACTIVE_RESEARCH | base de #15 |
| 40 | `work/bt2a-gate2-p2a-freeze-20260826` · `ef7f5c9` | OPEN_PR | #15; base de #18/#20 |
| 41 | `work/crypto-context-foundation-20260824` · `3b52974` | ACTIVE_RESEARCH / OPEN_PR | #14 |
| 42 | `work/futures-l2-context-foundation-20260825` · `0a1283f` | ACTIVE_RESEARCH | sin PR al corte |
| 43 | `work/indicator-coordinate-store-v1-20260827` · `9ad26cf` | ACTIVE_RESEARCH / OPEN_PR | #17 |
| 44 | `work/repository-research-iterations` · `5abf9b6` | HISTORICAL | iteraciones documentales |
| 45 | `work/research-architecture-hardening` · `a2b3527` | HISTORICAL | arquitectura temprana |

## Nota de corte

La consulta inicial devolvió 44 ramas antes de crear esta actualización. Esta rama documental, `docs/traceability-refresh-20260828`, pasa a ser la rama 45 y debe incorporarse al próximo snapshot con el tip resultante.

## Riesgos observados

1. Ninguna rama está protegida.
2. `main` no refleja la base científica vigente.
3. Existen cadenas de PR cuya base no es `foundation`; el orden de integración importa.
4. Hay ramas de resultado y de protocolo simultáneas; no interpretar fecha/tip como autorización.
5. Varias ramas históricas carecen de adjudicación reciente mediante `merge-base` y `git cherry`.
6. Los documentos de estado del 24-ago quedaron superados por nuevas campañas del 26–28 ago.

## Regla de mantenimiento

Actualizar este registro cuando ocurra cualquiera de estos eventos:

- nuevo branch/tip material;
- apertura, cierre o merge de PR;
- freeze o autorización;
- outcome abierto;
- incidente o cuarentena;
- resultado publicado;
- cambio de base de integración.

Cada actualización debe conservar el snapshot anterior y publicar corte, cobertura y limitaciones.

## Aporte al referente

El registro incorpora las ramas nacidas después del handoff del 24-ago, hace visible la cadena BT2A y separa la selección target-free de AVol NQ-120t de cualquier Gate 1.
