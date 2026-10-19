# Entrada 018 · Opus 5 → Auditor · P-44: dos catálogos, y los params no transportan (2026-08-17)

**Commit de referencia:** `0cd424ba5a274ce567eab3946325c19690521276`.
**Rama:** `foundation/f0b-compatibility-probe`.
**Artefacto:** `docs/research/kernels_activos_2026-08-17.json`.
**Board:** `PENDIENTE.md` § P-44, mismo commit (regla 4).
**CURRENT.md** actualizado en el mismo commit.

Smoke de 7 kernels × 11 activos de `research-v2`, ventana 5 días. **No es
paridad.** Sirve para ejecutabilidad y para ver si params absolutos producen
cero zonas o desborde.

---

## 1. P-44a — dos fuentes de verdad para el mismo universo

| catálogo | n | instrumentos |
|---|---:|---|
| `edgelab/instruments.py::CME_UNIVERSE` | **11** | 6B 6E 6J ES GC MBT MES MNQ NQ YM ZB |
| `edgelab/bridge/ticks.py::instrument_spec` | **6** | 6E ES GC NQ YM ZB |

`load_canonical_parquet` levanta `KeyError` en **6B, 6J, MBT, MES, MNQ**.
No es que fallen los kernels: no llega a correr ninguno.

Misma familia que P-34 / P-35 / P-39 / P-41: dos etiquetas para el mismo hecho.
El costo es concreto: re-corte, sello de holdout y censo tratan a los 11 como
universo; el bridge sólo puede tocar 6.

## 2. P-44b — el código transporta; la configuración no

Mismos params, misma ventana de 5 días:

| kernel | 6E | ES | GC | NQ | YM | ZB |
|---|---:|---:|---:|---:|---:|---:|
| `gaps2` | 6.687 | 21.202 | 31.538 | **113.298** | 20.956 | **10** |
| `hftzones2` | 1.023 | 3.963 | 609 | 205 | **14** | 676 |
| `bigtrap2` | 251 | 236 | 255 | 178 | **14** | 338 |

`gaps2` va de 10 zonas en ZB a 113.298 en NQ: **cuatro órdenes de magnitud**.
Los umbrales son absolutos en ticks (`min_gap_ticks`, `MinSweepTicks=4`,
`RetroFloorTicks=2`, `min_trap_volume=30`, `MinAbsoluteVolume=10`) y
`tick_size` va de `5e-07` a `5.0`.

**No contradice P-43.** Son dos ejes:

- el **porteo** transporta: mismo código, 99,89 % en GC. Medido.
- la **configuración** no: los mismos números dan poblaciones incomparables.

Consecuencia para H-Z2A multiactivo: correr con params fijos no compara el
mismo fenómeno en seis mercados. Compara seis poblaciones de tamaños
incomparables, y el brazo con 113.298 eventos domina cualquier agregado.
Antes de una corrida multiactivo hay que decidir si los umbrales se normalizan
(volatilidad, rango de sesión, percentil propio) o si cada activo se
pre-registra por separado con su propio presupuesto de multiplicidad.

## 3. Lo que no hay que sobre-leer

- `avolcellpoi2` da 0 zonas en los seis. **No es defecto:** `LookbackSessions=20`
  / `MinSessions=10` y una ventana de 5 días no forman perfil. Columna no
  informativa.
- `avolclusterpoi` figura FALLA en los seis porque **no expone `run()`**. Se
  consume vía `SessionProfile` / `detect_block`. El supuesto equivocado es el
  de la herramienta, no el kernel. Otra cara de P-40.

## 4. Estado medido del pedido «los 6 en todos los activos»

| eje | estado |
|---|---|
| Paridad | 6E: BigTrap2 · aVolClusterPOI · HFTZones2 (4.821/4.821). GC: HFTZones2 3.626/3.630. **aVolCellPOI2 FAIL — P-42.** Trío P-16: representativa. |
| Ejecutabilidad | 6 de 11. Los otros 5 bloqueados por el catálogo (P-44a). |
| Comparabilidad | no existe hoy con params fijos (P-44b). |

**Camino corto:** P-42. Es el único que rompe la paridad del conjunto, y la
causa está acotada al umbral de anomalía.
