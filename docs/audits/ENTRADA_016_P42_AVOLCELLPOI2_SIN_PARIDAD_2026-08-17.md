# Entrada 016 · Opus 5 → Auditor · P-42: aVolCellPOI2 no tiene paridad (2026-08-17)

**Commit de referencia:** `01d84878cf5f12dbbc3d1be931ebb3cc9ae81cfc`.
**Rama:** `foundation/f0b-compatibility-probe`.
**Artefacto:** `docs/research/paridad_avolcellpoi2_30d_2026-08-17.json`
(sha blob `57b2ef21d2484951bab02aa321863780078af746`).
**Board:** `PENDIENTE.md` § P-42, mismo commit (regla 4).

---

## 1. Medido

Primera paridad formal de `aVolCellPOI2` contra su oráculo
(`avolcellpoi2_v23_6E_0626_time1_100d.csv`, sha256 `5683d2e3…`), 6E 06-26,
`time:1`, 30 días. Gate **FAIL**. No es artefacto de ventana.

```
kernel 671   vs   oraculo 678
MISSING_IN_PYTHON  9
MISSING_IN_NT8     2
GEOMETRY_DIFF      2
FEATURE_DIFF       2    touches py=2/nt8=4 · py=3/nt8=9
TIMESTAMP_DIFF     1    created_ms diff = 60.000 ms = 1 barra
MATURITY_TAIL     22    cola de ventana; no cuenta como divergencia real
```

Los 16 reales cierran contra `summary.counts` del JSON. Los 22 `MATURITY_TAIL`
son frontera, no defecto.

## 2. Warmup descontado

Con 1 sesión de warmup los `MISSING_IN_PYTHON` eran 14; con 12 (por
`MinSessions=10`) bajan a 9. Cinco eran warmup, nueve son reales. El resto de
códigos no se mueve entre las dos corridas.

**Hueco de evidencia:** el JSON commiteado es sólo la corrida w=12. La corrida
w=1 (14 faltantes) no está en el repo. La dirección es verificable; la magnitud
del «5 eran warmup» descansa en una corrida no versionada.

## 3. Pista — zona 118/113

Difiere en geometría, timestamp y touches **a la vez**:

```
py  = (46663, 46661)   →  2 medio-ticks = 1 tick de alto
nt8 = (46665, 46661)   →  4 medio-ticks = 2 ticks de alto
created_ms diff = 60.000
touches py=2 / nt8=4
```

Mismo borde inferior, distinto superior. NT8 fusionó dos celdas; Python, una.

**Descartado:** la fusión es idéntica (`.cs` l.568 vs `.py` l.346),
`MergeGapTicks=0`, `MinZoneCells=1`. No hay margen ahí.

**Causa acotada, no cerrada:** el umbral que marca celdas anómalas
(`is_anomaly`, `.py` l.412). Un umbral marginalmente distinto mete o saca una
celda de borde y explica los tres síntomas juntos.

**Criterio de cierre:** comparar `threshold`, `empirical_pct`, `robust_z`,
`sample_count`, `session_count` por evento `OBS` del oráculo. Directo, sin
instrumentar.

## 4. Notas de registro (auditor)

1. El board cita `runs/paridad_avolcellpoi2_30d_w12.json`. Ese path **no existe**.
   El artefacto real es `docs/research/paridad_avolcellpoi2_30d_2026-08-17.json`.
   Corrección de una línea pendiente.
2. `procedencia.arbol_limpio: false`. `head_commit` del JSON es `4ac00ef`
   (el commit anterior). Medición sobre árbol sucio: no invalida los conteos;
   la identidad del runner no es reproducible byte a byte.
3. No transportar `aVolCellPOI2` a otro activo hasta cerrar P-42.

## 5. Consecuencia para «los 6»

Es el único de los siete kernels con paridad formal **medida y fallada**.
HFTZones2 ya había pasado 4.821/4.821 en 6E (entrada 009 / `7596a78`).
