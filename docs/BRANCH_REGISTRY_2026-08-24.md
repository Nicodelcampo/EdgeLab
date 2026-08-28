# Registro de ramas remotas — 2026-08-24

> **Corte:** 2026-08-24 18:31 UTC  
> **Rama primaria:** `foundation/f0b-compatibility-probe@bd4ebd1ed1053ab62a5871b83f8a1d59193634d8`  
> **Base científica auditada:** `9b23c307cb112cdd6392d98673e8ead2e8bc4698`  
> **Cobertura:** 28/28 ramas devueltas por GitHub; todas con tip resoluble; `protected=false` en las 28.

Este registro hace visibles las ramas. **No autoriza merges, cierres ni borrados.** Las
relaciones históricas marcadas como contenidas/superadas provienen del inventario previo;
donde no se reejecutó `git cherry` se declara como pendiente de verificación mecánica.

## Clasificaciones

- `PRIMARY`: única rama de continuidad e integración.
- `ACTIVE_MODULE`: trabajo vigente pero aislado; no operativo todavía.
- `OPEN_PR`: rama con PR draft abierto.
- `BLOCKED_SEMANTICS`: requiere decisión humana de semántica.
- `HISTORICAL_CONTAINED`: integrado, patch-equivalent o sucedido; no remergear a ciegas.
- `HISTORICAL_DIVERGENT`: conserva trabajo propio antiguo; comparar antes de borrar.
- `PARKED`: no es prioridad activa.
- `BACKUP`: preservación deliberada.
- `BASELINE`: baseline original, no rama de trabajo.

## Inventario completo

| # | Rama · tip | Clase | PR | Estado / acción siguiente |
|---:|---|---|---:|---|
| 1 | `audit/p0-bigtrap2-drift` · `1916ffa` | HISTORICAL_CONTAINED | — | evidencia histórica BT2 |
| 2 | `backup/foundation-f0b-local` · `a48efcd` | BACKUP | — | snapshot pre-foundation |
| 3 | `docs/estado-real-2026-08-10` · `16acc7d` | HISTORICAL_CONTAINED | cerrado | estado antiguo |
| 4 | `docs/h-cond-1-lux-imb` · `5530344` | HISTORICAL_CONTAINED | cerrado | protocolo sucedido |
| 5 | `docs/h-sweep-1-ym-prerange` · `2df700f` | HISTORICAL_CONTAINED | cerrado | documentación sucedida |
| 6 | `docs/lecciones-2026-08-24` · `e5ce349` | ACTIVE_MODULE | — | marco causal corregido; rama documental aislada |
| 7 | `docs/lux-imb-source-correction` · `3383d88` | HISTORICAL_CONTAINED | cerrado | corrección ya aplicada |
| 8 | `docs/post-merge-sync-2026-08-10` · `be1fcfa` | HISTORICAL_CONTAINED | cerrado | sincronización histórica |
| 9 | `fix/bigtrap2-v252-tick-export` · `6a858fd` | OPEN_PR | #12 | sin checks; comparar contra foundation |
| 10 | `fix/capture-probe-v2-contract` · `8b85add` | HISTORICAL_DIVERGENT | — | requiere diff mecánico |
| 11 | `fix/g2-a1-calibration-hardening` · `3c06e9c` | BLOCKED_SEMANTICS | #8 | checks verdes; adjudicar contrato rival |
| 12 | `fix/g2-a1-statistical-semantics` · `f3b8263` | BLOCKED_SEMANTICS | — | contrato rival de #8 |
| 13 | `foundation/f0b-compatibility-probe` · `bd4ebd1` | PRIMARY | base de #8/#9/#14 | rama viva; no tocar durante sweep activo |
| 14 | `main` · `cde6d93` | BASELINE | — | baseline original; no trabajar aquí |
| 15 | `prep/indicator-onboarding-registry` · `c47a687` | OPEN_PR / PARKED | #9 | check verde; F9 aparcada |
| 16 | `preserve/f0b-local-divergente-2026-08-04` · `a48efcd` | BACKUP | — | preservación redundante deliberada |
| 17 | `registry/gex-familia` · `f065df2` | PARKED | — | revalidar antes de integrar/archivar |
| 18 | `research/bigtrap2-distance-matched-null` · `2374832` | OPEN_PR / HISTORICAL_CONTAINED | #11 | patch-equivalent pre-rebase según inventario |
| 19 | `research/bigtrap2-local-displacement-null` · `29d78eb` | HISTORICAL_CONTAINED | base de #13 | foundation es sucesora operativa |
| 20 | `research/bigtrap2-multiframe-ml` · `05d2da7` | PARKED | — | no reactivar sin manifiesto/STOP |
| 21 | `research/bigtrap2-soporte-balance-curve` · `a856821` | HISTORICAL_CONTAINED | — | ancestro de local-displacement |
| 22 | `research/event-store-pit` · `4d6c6b1` | ACTIVE_MODULE | — | PIT v2 versionado; recomputación pendiente |
| 23 | `research/gate-regime-context` · `c882cf5` | ACTIVE_MODULE | — | checkpoint pendiente con datos reales |
| 24 | `research/ym-prerange-session-window` · `0c44813` | HISTORICAL_CONTAINED | cerrado | mantener como referencia |
| 25 | `research/zamr1-zone-atlas` · `b74f7bd` | OPEN_PR / PARKED | #13 | checks verdes; base histórica |
| 26 | `work/crypto-context-foundation-20260824` · `5ed6ba5` | ACTIVE_MODULE / OPEN_PR | #14 | preregistro/CI corregidos; rerun en curso al corte |
| 27 | `work/repository-research-iterations` · `5abf9b6` | HISTORICAL_DIVERGENT | — | iteraciones documentales antiguas |
| 28 | `work/research-architecture-hardening` · `a2b3527` | HISTORICAL_DIVERGENT | — | arquitectura temprana |

## Reglas para operar con este registro

1. Verificar el tip remoto antes de tocar una rama; si cambió, actualizar el registro.
2. Para declarar `contenida`, reejecutar `merge-base --is-ancestor` y `git cherry`.
3. No usar un único campo `merged` como prueba si contradice `merged_at`.
4. Ninguna rama está protegida: la accesibilidad técnica exige más disciplina.
5. No borrar hasta asignar destino al contenido propio, PR, docs y artefactos externos.
6. Después de cada push, consultar el commit y contar `files[]` contra los archivos declarados.

## Cambio respecto del corte anterior

El registro anterior cubría 26 ramas. Se incorporan explícitamente:

- `docs/lecciones-2026-08-24`;
- `research/event-store-pit`.

No se tocó la rama primaria para hacer esta actualización.
