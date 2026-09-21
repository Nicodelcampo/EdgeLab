# BigTrap2Absorption — Provenance y Semantica Temporal M5/tick_25

**Fecha:** `2026-09-20T21:53 UTC-3`
**Documento:** Auditoria de provenance solicitada en sesion 2026-09-20
**Estado:** CERRADO — cadena causal documentada con hashes verificables

---

## 1. Tres versiones identificadas

### Version A — Remoto publicado (`84eea97`)

| Campo | Valor |
|---|---|
| Commit | `84eea9758ca50fd07e07076dd346e0947bffcf3f` |
| Rama | `feat/edge-discovery-brain-foundation-20260919` |
| SHA-256 (git blob, LF) | `7b13f198896b1fe4a89cb154f07c7c95d0a24bc74b6692590e6c47ff4cee56ea` |
| Tamano | 19.643 bytes, 497 lineas |

Contiene: `meta_line()`, `header`, `csv_lines`, `params_line`, campos `indicator/top/bottom/kind/timeline` en `z_entry`.

### Version B — HEAD rama local (`work/bt2a-gate2-p2a-freeze-20260826`, commit `e50bbf3`)

| Campo | Valor |
|---|---|
| Commit | `e50bbf3` (HEAD local) |
| SHA-256 (git blob, LF) | `b36670a140ccf918d6166f3739f33f242ff97d8fab19c9cd31281dc0189069fc` |
| Tamano | 19.022 bytes, 479 lineas |

Diferencias vs A (18 lineas menos):
- Eliminado: `meta_line()`, `header`, `csv_lines`, `params_line` en `return dict()`
- Eliminado: campos `indicator`, `top`, `bottom`, `kind`, `timeline` de `z_entry`
- Algoritmo de deteccion de zonas: **identico**

### Version C — Disco post-modificacion (`available_at_ns`, 2026-09-20)

| Campo | Valor |
|---|---|
| Estado | Modificado en disco, no commitado aun |
| SHA-256 (bytes de disco, CRLF en Windows) | `dbbb3c61c2939d4c872495f78ecde01bda9e2bd55fc159cd6818030baca6846a` |
| Tamano | 19.875 bytes, 484 lineas |

Cambio sobre Version B: agrega campo `available_at_ns = int(blk_ts[-1])` en `z_entry`.

---

## 2. Semantica temporal canonizada

### Cadena causal M5 (bar_key=time_5m)

```
ticks -> flush_block(blk, ...) 
  blk_ts[-1] = ns del ultimo tick del bloque (cierre del bucket M5)
  created_ms = ns_to_ms(blk_ts[-1])  = ms del cierre
  available_at_ns = int(blk_ts[-1])  = ns del cierre  <-- NUEVO (Version C)

viewer_export._zone_json(z, ..., bar_key='time_5m'):
  Prioridad 1: available_ts = available_at_ns // 1_000_000_000  (del kernel)
  Fallback:    available_ts = t0 + _bar_duration_s('time_5m')   (solo time_*)
               = (created_ms // 1000) + 300

Verificacion con zona real (YM_SEP26, zona BT2A #0):
  t0 = 1781271000 = 2026-06-12T13:30:00Z  (apertura barra M5)
  available_ts = 1781271300 = 2026-06-12T13:35:00Z  (cierre barra M5)
  delta = 300 s  (no look-ahead)
```

### Cadena causal tick_25 (bar_key=tick_25)

```
ticks -> flush_block(blk, ...)
  blk_ts[-1] = ns del ultimo tick de la cubeta (tick numero 25)
  available_at_ns = int(blk_ts[-1])  <-- NUEVO (Version C)

viewer_export._zone_json(z, ..., bar_key='tick_25'):
  Prioridad 1: available_ts = available_at_ns // 1_000_000_000
  Fallback:    _bar_duration_s('tick_25') = None  -> available_ts = None
               (tick bars sin available_at_ns: zona omitida en el renderer)
```

### Regla del renderer (index.html, lineas 1832-1849 post-modificacion)

```javascript
if (z.available_ts !== undefined && z.available_ts !== null) {
  tSignal = z.available_ts;              // Prioridad 1: campo canonico
} else {
  var bspec = z.source_barspec || "";
  if (bspec.indexOf("time_") === 0 && barDurationSec > 0) {
    tSignal = z.t0 + barDurationSec;   // Fallback: SOLO barras temporales
  } else {
    return;  // tick bars sin available_ts: zona omitida, no se fabrica timestamp
  }
}
```

---

## 3. Prueba formal de no look-ahead

Para cualquier zona emitida por BigTrap2Absorption:

1. `flush_block(blk, ...)` se ejecuta al completarse el bloque (M5 o tick_25)
2. `blk_ts[-1]` es el ultimo tick procesado = timestamp de cierre real
3. `available_at_ns = blk_ts[-1]` => disponible al cierre, no antes
4. `t0 = created_ms // 1000 = blk_ts[-1] // 1_000_000_000` = apertura de barra (legacy) 
   NOTA: en bundles pre-Version-C, `t0` apunta a la apertura, no al cierre. 
   El viewer compensaba con `t0 + barDurationSec`. Post-Version-C el kernel emite directamente.
5. Invariante verificado: `available_ts >= t0` (ver tests en `test_bigtrap2_available_ts.py`)

---

## 4. Tests cubriendo M5 y tick_25

Archivo: `tests/bridge/test_bigtrap2_available_ts.py`

| Clase | Tests |
|---|---|
| `TestBarDurationS` | 9 (time_5m, time_1m, time_15m, time_1h, time_1d, tick_25, tick_100, empty, vol) |
| `TestZoneJsonAvailableTs` | 10 (kernel priority, t0<avail, delta=300, fallback, tick25+avail, tick25-none, barspec, empty key, kernel>fallback) |
| `TestCausalSemanticsGeneral` | 3 (no holdout, pre-holdout, avail>=t0) |

**Total: 22 tests PASSED en 0.09s** (verificado localmente, Python 3.12.7)

---

## 5. Campos nuevos en el bundle

A partir de Version C, cada zona en el bundle incluye:

| Campo | Tipo | Descripcion |
|---|---|---|
| `available_ts` | int (segundos) o null | Timestamp causal de disponibilidad de la senal |
| `source_barspec` | string o null | Bar key que genero la zona (ej. "time_5m", "tick_25") |

Bundles anteriores (pre-Version-C) no tienen `available_at_ns` en las zonas del kernel,
por lo que el exportador aplica el fallback temporal cuando `source_barspec` empieza con "time_".

---

## 6. Holdout y outcomes

- Ningun fixture ni test cruza el holdout boundary `1782856800000000000`
- No se abrieron outcomes ni datos del holdout durante esta sesion
- `OUTCOMES_NOT_OPENED` = true para esta sesion
