# BigTrap2 — la paridad contra el oráculo de 6E no es alcanzable, y no debería serlo

- **Fecha**: 2026-08-21 · **Estado**: `MEASURED_COMMITTED`
- **Alcance**: target-free. Sólo integridad del oráculo y del puerto. Sin outcomes.
- Oráculo auditado: `oracles/BigTrap2_diag_tick25_6E_0926.csv` — 6E 09-26, tick:25,
  2026-07-08 → 2026-07-24, 46.430 eventos.

---

## 1. El hallazgo

**`BigTrap2` no logró alinear el footprint con la barra en el 89 % de las barras.**

| evento | n |
|---|---|
| `FOOTPRINT_MISMATCH` | **26.661** |
| `TRAP` | 7.454 |
| `ZONE_TOUCHED` | 8.349 |
| `ZONE_CREATED` | 1.986 |
| `ZONE_INVALIDATED` | 1.910 |
| `ZONE_EXPIRED` | 69 |

Sobre **29.905 barras**, eso es **`26.661 / 29.905 = 0,892`**.

El error no es marginal: la diferencia mediana entre `fp_vol` y `bar_vol` es del
**11,9 %** del volumen de la barra, y es **simétrica** — el footprint sobra en el 49,9 %
de los casos y falta en el 50,1 %. No es un sesgo corregible; es desalineación.

Y `fp_vol == bar_vol` ocurre en apenas el **9,27 %** de los TRAPs exportados.

## 2. Por qué pasa

El `.cs` dedica ~400 líneas a este problema: `DrenarPorOHLCV`, `Abstener`,
`CoincideOHLCV`, `VerificarOHLC`, más contadores de residuales, mismatch y abstenciones.

Existe porque NT8 entrega **dos series separadas** —la primaria de 25 ticks y una
subserie de 1 tick— y hay que alinearlas sin poder consultar qué ticks formaron qué
barra. El indicador lo intenta por OHLCV y **falla la mayoría de las veces**.

## 3. Por qué eso hace la paridad indeseable

Un puerto que construye las barras **desde los mismos ticks** no tiene el problema:
footprint y barra son el mismo objeto por construcción. No hay nada que alinear.

Resultado de intentar la paridad de todos modos:

| | |
|---|---|
| TRAPs del oráculo | 7.454 en 7.267 barras |
| TRAPs del puerto | 4.479 en 4.397 barras |
| barras coincidentes, mejor alineación | 1.106 (15 %) |
| **con el mismo lado exacto** | **680 = 9,4 %** |

Y **9,4 % es casi exactamente el 9,27 % de barras donde el propio oráculo dice que su
footprint SÍ coincidía con la barra.** Las dos implementaciones concuerdan justo donde
NT8 no estaba desalineado.

**Reproducir el oráculo significaría reproducir su desalineación.** Eso no es paridad:
es copiar un defecto.

## 4. Lo que sí quedó verificado

Los flujos de ticks **son el mismo**, así que la discrepancia no es de datos:

| volumen por barra de 25 ticks | p25 | p50 | p75 | media |
|---|---|---|---|---|
| oráculo | 39 | 46 | 57 | 50,9 |
| puerto | 38 | 46 | 56 | 50,1 |

Y la geometría emitida tiene la misma forma exacta: `centroid`, `zone_lo`/`zone_hi` con
±medio tick, `n_rows`, `max_ratio`.

## 5. Consecuencias

### 5.1 El puerto no se llama BigTrap2

Es un objeto distinto: mismo algoritmo, footprint correcto. Se nombra
**`BigTrap2Exact`** y se declara que **no reproduce** al indicador de NT8, con el motivo.
La regla del proyecto es explícita: no se transportan resultados entre implementaciones
que no son la misma.

### 5.2 Todo resultado histórico de BigTrap2 hereda esta duda

Cualquier medición previa que use TRAPs exportados por el indicador está construida sobre
un footprint desalineado en el 89 % de las barras. **No los invalida automáticamente** —
la desalineación es simétrica y podría promediarse— pero es una fuente de ruido que nunca
estuvo declarada.

Esto **no** reabre las líneas cerradas de BigTrap2 (F2.7–F2.10 sobre 6E): aquéllas
midieron atracción y revisita de zona, y su alcance ya está declarado. Lo agrega como
limitación conocida.

### 5.3 Para GC no hace falta exportar oráculo — pero tampoco sirve para paridad

Un oráculo de GC tendría el mismo defecto. La decisión correcta es usar `BigTrap2Exact`
y declararlo, no perseguir una paridad que replicaría el error.

## 6. Qué queda pendiente

- El puerto implementa **detección de TRAP**. El ciclo de vida de zona
  (`ZONE_CREATED` / `TOUCHED` / `INVALIDATED` / `EXPIRED`) **no** está portado todavía.
- La aritmética entera (`round_away`, medios ticks) está replicada del `.cs`, incluido el
  detalle que allí se documenta como origen de 101 falsos positivos por 1 ULP.
- Falta verificar el comportamiento con `tick_size` de GC (0,10) contra el de 6E
  (0,00005): cuatro órdenes de magnitud de diferencia es donde aparecen los errores de
  redondeo.
