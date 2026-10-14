# Aprobación de la release `liquid_tick_v1` v4

Estado: VIGENTE
Fecha: 2026-10-14
Familia / módulo: liquid-release

**Decisión.** Nico delegó la aprobación ("se aprueba la release si es correcta; ante la duda, lo más completo o reciente"). Se verificó que es correcta y **se aprueba como release canónica de ticks** para investigación privada, atada al manifiesto `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`.

## Por qué se considera correcta
- Auditoría independiente de contenido en Kaggle: 14 activos, 3.838 sesiones, 1.394.017.834 filas = footer, 0 fallas, 31 hashes verificados (`docs/infra/liquid_v4_audit_20261014/receipt.json`).
- Descarga desde Kaggle con tamaño y SHA-256 idénticos al manifiesto.
- Reparaciones LRA-01…06 con pruebas de regresión; 53 pruebas del productor pasan en `foundation`.

## Qué aprueba
Política de liquidez v4, calendario derivado y alcance de licencia (uso privado, sin redistribución). Registro máquina-legible: `docs/infra/release_approval/release_approval_db9c42cd.json`.

## Límites que se mantienen (no son defectos ocultos)
701 sesiones-contrato con conflicto de fuente; 309 sesiones P0 sin export; calibración de política in-sample en las primeras 80 sesiones; calendario oficial sólo para índices de renta variable; holdout (≥ 2026-10-01) excluido.

## Cómo se aplica (sin v5)
El manifiesto publicado dice `research_allowed=false` y es inmutable (cambiarlo cambia su SHA y rompe la auditoría y los pines de los kernels). La aprobación vive **fuera** de la release, versionada en git y atada al SHA exacto: `docs/infra/release_approval/release_approval_db9c42cd.json` con `supersedes_manifest_research_allowed=true`. `release_reader` la busca dentro de la release y, si no está, en `docs/infra/release_approval/release_approval_<sha8>.json` (prueba en `tests/data/test_liquid_release_audit_20261014.py`). Verificado contra la release real: `load_manifest(release_v4, purpose='research')` admite los 14 activos. Todo resultado sigue citando el SHA del manifiesto.

## Qué NO cambia
- P&L, manifiestos de campaña y holdout siguen requiriendo el OK explícito de Nico.
- `purpose='research'` exige `verify_hash=True` (sin atajos).
