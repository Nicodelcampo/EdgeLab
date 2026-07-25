# BigTrap2 — inventario TARGET-FREE en `time:1` (2026-07-25)

> Insumo para un eventual **CAMP-002**. **No es una campaña** y no habilita
> ninguna: BigTrap2 sigue sin `parity_exact` promovido y sin manifiesto sellado.
> **No se tocó ningún retorno ni P&L.**

Generado con `tools/bigtrap2_inventory.py` sobre los 4 folds de desarrollo de E3
(mismos rangos, mismo firewall del holdout). Artefacto:
`runs/nt8_bridge/bigtrap2_inventory/inventory.json`.

## Frecuencia y ciclo de vida

| Fold | días | barras m1 | zonas | zonas/día | bull | bear | tocadas | vida mediana |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6E 09-25 | 43 | 47.107 | 2.540 | 59,1 | 1.260 | 1.280 | 2.481 | 8 min |
| 6E 12-25 | 76 | 85.781 | 4.701 | 61,9 | 2.347 | 2.354 | 4.610 | 8 min |
| 6E 03-26 | 74 | 84.338 | 5.396 | 72,9 | 2.740 | 2.656 | 5.256 | 7 min |
| 6E 06-26 | 77 | 86.524 | 5.227 | 67,9 | 2.703 | 2.524 | 5.121 | 8 min |
| **total** | | | **17.864** | | | | | |

Tres hechos que sirven para diseñar:

1. **Homogeneidad entre folds.** 59–73 zonas/día, dispersión de 1,23×. Gaps2 iba
   de 253 a 475/día (1,88×). Los folds de BigTrap2 son **más comparables entre
   sí**, lo que reduce el riesgo de que el walk-forward mida cambios de régimen
   en vez de estabilidad de la señal.
2. **Simetría bull/bear casi perfecta** (1.260/1.280, 2.347/2.354, 2.740/2.656,
   2.703/2.524). Ninguna dirección está sobre-representada, así que una familia
   simétrica no arrastra sesgo direccional de origen.
3. **97,7 % de las zonas son tocadas** (2.481 de 2.540 en el fold 1). La
   disponibilidad de señales **no** sería la restricción binding — al revés que
   en el estrato `zmin=5` de CAMP-001.

Cierre: **91 % `close_through`**, 5 % `close_through_gap`, 4 % `max_age`. Las
zonas mueren porque el precio las atraviesa, no por vencimiento.

## Distribución de tamaño — la restricción real

| Fold | ≥1 tick | ≥2 | ≥3 | ≥5 | ≥8 |
|---|---:|---:|---:|---:|---:|
| 6E 09-25 | 2.540 | 464 | 146 | 32 | 11 |
| 6E 12-25 | 4.701 | 494 | 136 | 30 | 12 |
| 6E 03-26 | 5.396 | 742 | 254 | 58 | 13 |
| 6E 06-26 | 5.227 | 689 | 235 | 45 | 23 |
| **total** | **17.864** | **2.389** | **771** | **165** | **59** |

**~82 % de las zonas miden exactamente 1 tick.** Filtrar por tamaño colapsa la
muestra igual de rápido que en Gaps2.

Consecuencia **pre-calculada** para el diseño de CAMP-002, que es justamente lo
que E6 tuvo que corregir a posteriori en CAMP-001:

- `zone_min_size ≥ 1` (sin filtro): ~17.900 zonas → único estrato con muestra
  cómoda en los cuatro folds.
- `≥ 3`: **771 en total**, 136–254 por fold. Antes de aplicar la regla de una
  posición simultánea (que en CAMP-001 rechazó el 65,5 % de las señales) ya
  queda al borde del `n_trades ≥ 100` de G1.
- `≥ 5`: **165 en total**, 30–58 por fold ⇒ **`insufficient_n` garantizado**.
  Incluirlo sería gastar presupuesto de hipótesis en celdas que no pueden
  decidir nada.

## Implicación sobre el `time_stop`

La vida mediana de una zona es de **7–8 minutos**. CAMP-001 usó `time_stop = 240`
barras m1 (4 h), que para BigTrap2 sería **~30× la vida de la zona**: la posición
sobreviviría a la zona que la originó por un margen enorme. Un `time_stop`
plausible acá está en el orden de las **decenas de minutos**, no de las horas —
pero eso es una decisión de diseño de campaña, no un hallazgo, y va al manifiesto
para que Nico lo selle.

## Advertencia — esto calibra el hábitat EQUIVOCADO

Este inventario es de **`time:1`**, y la hipótesis económica de BigTrap2 es de
**microestructura**: agresión atrapada leída del footprint por nivel de precio.
Su hábitat son las velas de tick.

Sirve para: validar el circuito, tener una línea de base, y calibrar un eventual
CAMP-002 **si** se decidiera correrlo en `time:1`. **No sirve** como calibración
de la campaña que realmente importa, que es la de resolución nativa — bloqueada
por TICKBAR-001.

Dicho de otro modo: estos números son buenos, pero miden a BigTrap2 fuera de su
cancha. Presentarlos como calibración del edge real sería el mismo tipo de error
que extrapolar desde un solo día.

## Bloqueos vigentes para cualquier CAMP-002

1. **Decisión de Nico sobre el gate de borde.** BigTrap2 en `time:1` dio
   `PRED-001` exacta pero gate **FAIL** por el `MISSING_IN_NT8` de borde de
   ventana (pre-declarado). Sin `parity_exact`, no hay `parity_covered` que
   propagar (§8.2) y ninguna partición es elegible.
2. **Decisión de Nico sobre el fix de TICKBAR-001**, para la resolución nativa.
3. **Manifiesto sellado**, con N_eff, riesgos y datos faltantes — el STOP de
   `CLAUDE.md` sigue vigente.
