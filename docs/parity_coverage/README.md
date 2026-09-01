# Matrices de cobertura de paridad (F7)

Cada kernel declara sus **ramas** (`branches` en `PARAM_SPEC`) — los caminos de
código que un parámetro activa. Un **oráculo NT8 PASS** cubre las ramas que su
config ejercita. La contabilidad vive en `edgelab/bridge/coverage.py`
(`branches_of`, `config_branches`, `is_covered`).

## Regla de los ejes de paridad

- **`parity_exact`**: esa config exacta tiene un oráculo NT8 propio que pasó P2.
- **`parity_covered`**: esa config NO tiene oráculo propio, pero **TODAS** las
  ramas que activa están cubiertas por oráculos PASS de OTRAS configs del mismo
  kernel. Sirve para fuerza bruta formal, pero **NO** para promover un edge:
  promover exige `parity_exact` propio de la config ganadora (si ganó con
  `parity_covered`, se exporta un oráculo ad-hoc de esa config y se re-verifica).
- **`parity_pending`** / **`parity_failed`**: sin oráculo / con oráculo que falló.

## Estado

Ningún oráculo **PASS** existe todavía (F4C bloqueado esperando el CSV de Gaps2).

> **Corrección 2026-09-01.** La versión previa de este párrafo decía «ningún
> oráculo real existe todavía». Sí existió uno: `aVolCellPOI2_6E_0926.csv`,
> corrido el **2026-07-26**, con gate **FAIL** por desacuerdo de **calendario de
> sesiones** — Python contó 28 sesiones y NT8 25 sobre el mismo tramo (feriado
> del 3 de julio), con lo cual cada lado empezó a detectar en sesiones distintas.
> Ver `aVolCellPOI2.md`. Es el **único oráculo real del proyecto** hasta hoy.
>
> La distinción importa: ese FAIL no fue un desacuerdo sobre **qué es una
> anomalía** — las 2 zonas que ambos lados vieron coincidieron — sino sobre
> **cuándo hay suficiente historia**. El modo de falla está precargado en todo
> kernel que dependa de `LookbackSessions` o de buckets relativos a sesión, y la
> decisión de cuál calendario es la referencia (`edgelab/sessions.py` CME ETH
> contra el `SessionIterator` de NT8) sigue **pendiente desde julio**. Mientras no
> se decida, cualquier gate de esos kernels vuelve a fallar por la misma causa.

Las matrices por kernel listan cada rama y qué oráculo pre-registrado la cubrirá
cuando se genere. El pre-registro EXACTO (contrato, rango, params, bar type,
EventLogPath) está en `../nt8_indicator_parity_contract.md` §6, para generarlos
en tandas en una sola sesión de NT8.

## Campaña mínima de oráculos (pre-registrada)

| Kernel | Oráculos mínimos |
|---|---|
| Gaps2 | default · min_gap denso |
| VolTicksPOC2 | default (CloseThrough) · FirstTouch |
| BigTrap2 | Diagonal/time:1 · SameLevel/tick:25 · wick off |
| HFTZones2 | adaptativo · manual |
| aVolCellPOI2 | SessionRelative/TotalVolume · WallClock/AbsDelta |
| aVolClusterPOI | default SessionRelative / `tick:120` (**ejecutable hoy**) · WallClock · lifecycle FirstTouch (**diferido**) |

Un oráculo default ejercita todas las ramas del kernel con sus caminos por
defecto; los oráculos variante agregan los caminos ALTERNOS de ramas puntuales
(imbalance SameLevel, WallClock, calibración manual, FirstTouch, mecha off).

### Nota de alcance — aVolClusterPOI (2026-09-01)

El kernel Python `edgelab/bridge/indicators/avolclusterpoi.py` v0.5 es **parcial**
(6 KB contra 42 KB del `.cs`): cubre la cadena de detección y la creación de
zonas, y **no** implementa `ProcessLifecycle`, `UpdateOutcome`, `QualityScore`,
filtro predictivo, burst, ni la construcción de las barras — `detect_block`
recibe las celdas ya armadas. Por eso su campaña se parte en dos:

- **Ejecutable hoy:** el oráculo default valida **creación de zonas**
  (`ZONE_CREATED` / `AT_PRICE_CREATED`), que es lo que necesita el embudo de
  medición (`EF0-A` y `EF1` son target-free). Debe exportarse con
  `EnablePredictiveFilter = false`, `MinQualityScore = 0`, `MaxAgeBars = 0` y
  `MaxTouches = 0`: si no, el `.cs` descarta eventos que el kernel no sabe
  descartar y el gate los reporta como `MISSING_IN_NT8` — un FAIL de
  **configuración** disfrazado de FAIL de paridad.
- **Diferido:** los oráculos de lifecycle no son comparables hasta que el kernel
  implemente el ciclo de vida. Quedan registrados como pendientes; no se corren.

Además, el oráculo se exporta **pareado** con una captura de `nt8/TickBarDiag.cs`
a la misma resolución: `FOOTPRINT_MISMATCH` es WARN en el matcher, pero el efecto
indirecto del defecto abierto de `TICKBAR-001` aterriza como `GEOMETRY_DIFF` o
como huérfanas, y ahí el matcher **no puede distinguir** un kernel mal traducido
de un bar builder en desacuerdo consigo mismo.

**Deuda declarada:** este pre-registro todavía **no** tiene su entrada exacta en
`../nt8_indicator_parity_contract.md` §6. Falta escribirla con contrato, rango,
plantilla de Trading Hours, TZ y `EventLogPath` — datos que aún no están
declarados. Pliego completo del oráculo en `aVolClusterPOI.md` §4.
