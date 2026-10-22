# Enmienda HOLDOUT-A4 — un solo holdout para todo: la sesión CME del 2026-10-01 (2026-10-22)

Estado: VIGENTE

**Decisión de Nico (chat, 2026-10-22):** «el holdout tiene que ser 2026-10-01 … eliminá las referencias a otras fechas de holdout».
Cambia la semántica de validación: queda firmada por Nico con esa instrucción.

## Qué cambia

| | Antes | Ahora |
|---|---|---|
| ES, NQ (ticks) | holdout desde la sesión del 2026-10-01 (A1–A3) | igual |
| Resto de instrumentos | holdout 2026-07-01 → 2026-12-31 (sello de `holdout_guard.py`) | **desde la sesión del 2026-10-01** |
| L2 (MBP-10) | holdout 2026-11-01 → 2026-12-31 (enmienda del 2026-09-24) | **desde la sesión del 2026-10-01** |
| Autopilot (`guard.py`) | 2026-10-01 para todo, en contradicción con los documentos | sin cambios: ahora coincide |

La sesión CME del 2026-10-01 abre a las 17:00 CT del 2026-09-30, que es 22:00 UTC (`1_790_805_600_000_000_000` ns).

**Fuente única en código: `edgelab/holdout.py`.** `holdout_guard.HOLDOUT_START_ISO`, `L2_HOLDOUT_START_ISO` (alias) y las herramientas de research importan de ahí. Los scripts que corren sueltos en kernels de Kaggle, donde no está el paquete, llevan una copia literal. `tests/test_holdout_unico.py` exige que toda constante de holdout del repo valga lo mismo y que no reaparezcan las fechas viejas como frontera.

## Consecuencias, escritas antes de medir nada con ellas

- **Jul–sep 2026 deja de ser fuera de muestra para todos los instrumentos.** Para ES y NQ sigue la partición de A3: descubrimiento hasta 2026-03-31 y réplica abr–sep una vez por familia. Para el resto todo lo anterior al 1-oct es desarrollo; una familia que quiera réplica la pre-registra antes de mirar.
- **L2 de octubre pasa a ser holdout.** La exploración L2 de NQ (`tools/nq_l2_explore.py`) usaba octubre como confirmación: su rango se recorta al 30-sep. Lo que esa campaña ya miró de octubre queda registrado como consumido; no es una confirmación limpia para esa familia.
- **Lo que el autopilot corrió con jul–sep de YM, GC, ZB, 6E, 6J y MGC** (idm-1, slot-1, idm-2, universe-sigma, scan-1, pnl-1, vio-1, ou-2) queda dentro de desarrollo. Antes de esta enmienda esas corridas contradecían los documentos, no el código.
- **Las aperturas exploratorias ya hechas sobre jul–sep** (enmiendas 5 y 6 de la cesta, `tools/ghost_holdout_cesta*.py`) quedan como historia. Esa ventana ya no es holdout.
- **El sello es un sello (regla 95, INC-006).** Este movimiento no lo hizo un cambio de código: lo hizo una enmienda firmada, la única forma admitida.

## Artefactos que conservan la fecha vieja como CORTE FÍSICO (no es un holdout)

research-v2, los datasets `*-preholdout` y el release v1 terminan físicamente en 2026-06-30 22:00 UTC (`CORTE_FISICO_RESEARCH_V2_UTC_NS`).
- Las herramientas que los generan o verifican nombran esa fecha como corte: `verify_indices`, `verify_tree`, `recut_holdout`, `build_kaggle_bundle`, `migrate_*`, `audit_*`, `generate_kaggle_canonical_manifest`, `rectify_kaggle_manifest`, `build_kaggle_audit_manifest`.
- En los manifiestos ya publicados el nombre de campo `holdout_boundary_ns` no se cambia, porque son inmutables. Su valor es ese corte físico.
- Las herramientas de familias cerradas que llamaban `HOLDOUT_NS` al fin de su descubrimiento (2026-04-01) lo renombran a `FIN_DESCUBRIMIENTO_NS`, sin cambiar el valor.

Dos kernels de Kaggle cortaban en 2026-10-01 00:00 UTC, dos horas tarde: `corridor_pass2`, `grid_support_pilot`. Ahora usan 22:00 UTC del 30-sep.

## Cobertura de datos en Kaggle hasta el holdout (verificada el 2026-10-22)

Fuente: el índice de sesiones del release `nicolasbuttaro/edgelab-liquid-ticks-20261014`, bajado de Kaggle (sin ticks). Ninguna fila es del holdout. Detalle: `docs/infra/COBERTURA_KAGGLE_PREHOLDOUT_20261022.json`, regenerable con `tools/cobertura_release_preholdout.py`. Hay 66 sesiones CME de referencia entre el 1-jul y el 30-sep.

| Activo | Última sesión | Jul–sep | Faltan 28–30 sep |
|---|---|---|---|
| MBT | 30-sep | 66/66 | — |
| GC, MGC | 30-sep | 59/66 | — |
| MNQ | 30-sep | 58/66 | — |
| YM | 30-sep | 58/66 | — |
| ZB | 30-sep | 62/66 | — |
| RTY | 28-sep | 62/66 | 29, 30 |
| MES | 28-sep | 59/66 | 29, 30 |
| MYM | 28-sep | **51/66** | 29, 30 |
| NQ | 25-sep | 61/66 | 28, 29, 30 |
| ES | 25-sep | 57/66 | 28, 29, 30 |
| 6B, 6J | 25-sep | 63/66 | 28, 29, 30 |
| 6E | 25-sep | **54/66** | 28, 29, 30 |

**No todos los activos tienen datos hasta el holdout.**
- **Nueve de 14 terminan antes del 30-sep.** Al 28-sep llegan MES, MYM y RTY; al 25-sep, ES, NQ, 6E, 6B y 6J.
- **Hay huecos internos:** sesiones sin contrato elegible o indeterminadas porque falta un export, en especial MYM (15), 6E (12) y ES (9).
- **El detalle por sesión y contrato** está en `docs/infra/MISSING_EXPORTS_20261014.md`. Se completa con el AddOn `EdgeLabTickHistory`, y es trabajo de Nico en NT8.

**Hallazgo de la misma revisión: el autopilot resuelve contra datasets REEMPLAZADOS.**
- Los 10 datasets a los que apunta `docs/data_catalog/RESOLVER.json` están marcados en Kaggle como `REEMPLAZADO 2026-10-14`:
  - edgelab-nt8-historical-missing-20261001;
  - ticks-nt8-canonical;
  - ticks-nt8-reexport-20261005;
  - ticks-gc / zb / mbt / 6e-preholdout;
  - mgc-nt8-raw-parquet;
  - ticks-es-nq-2026q3-ext;
  - ticks-nq-preholdout, que además está en **CUARENTENA**.
- Ese resolver es el que usan `docs/data_catalog/edgelab_data.py` (protegido) y `tools/kaggle_launch.py --need`, es decir, las corridas del Debian.
- El propio dataset `edgelab-data-catalog` lo describe como «resolver histórico, BLOQUEADO para research».
- Pasar el autopilot al release líquido exige dos cosas, y las dos son decisiones de Nico:
  1. aprobar el release para research: hoy está `CANDIDATE_NOT_RESEARCH_APPROVED` y falta aprobar su política de liquidez;
  2. tocar un archivo protegido.
- No se cambió nada de esto en esta enmienda.

**Aporte al referente:** una sola frontera de holdout, en código y en documentos, elimina la clase de error por la que el autopilot y los documentos decían cosas distintas sobre qué datos podía usar. La cobertura medida dice exactamente qué sesiones faltan antes del holdout.
