# PARIDAD BigTrap2Absorption .cs v1.1.1 <-> Python — 2026-08-22

Medición hecha desde el chat de Notion (auditor) sobre dos archivos provistos por Nico:

- `GC 12-26.Last.txt` — 683.188 ticks, `last;bid;ask;vol`, timestamps en UTC
- `bt2_absorption__TW25_2.csv` — export NT8 v1.1.1, 71.929 líneas: 28.042 `BARRA_PROCESADA`,
  28.042 `ABS_SCORE`, 13.904 `TRAP`, 647 `ZONE_CREATED`, 647 `FILL`, 628 `ZONE_INVALIDATED`,
  18 `ZONE_EXPIRED`

Solo detección y geometría. Sin outcomes, sin P&L. La ventana (17–21 ago) es la del
holdout ya gastado por H-GC-BT2-1: se usó SOLO para comparar implementaciones entre sí,
lo cual es target-free.

## Veredicto por capa (todo medido)

| capa | resultado |
|---|---|
| cobertura de la cinta | **27.328/28.042 cubetas (97,45 %)**. Faltan las 714 iniciales: domingo 19:00 → lunes 00:00 ART = 17.814 ticks que la cinta no incluye |
| identidad de streams | tick por tick idénticos en lo cubierto: **0 desalineos de `t_start`** en 27.328 cubetas; los 4 cortes de sesión (barras 3947, 8287, 15960, 21841; largos 21/15/10/6) cruzan sin perder ni un tick |
| `signed_flow` | **27.328/27.328 exacto** |
| `d_ticks` | **27.328/27.328 exacto** |
| `a_score` | exacto salvo impresión: max diff relativa **4,7e-15** (el CSV imprime 16 dígitos, Python 17; mismo double) |
| umbral causal (p90, lookback 500, warmup 200, residuales fuera del historial) | **`a_pass` 28.042/28.042, `n_hist` 28.042/28.042**; `a_thr` difiere a lo sumo en 1 ULP de impresión. Replay sobre los `a_score` del propio CSV: cubre también las 714 cubetas que la cinta no tiene |
| zonas (rows → runs → `MinStackedRows` → `MinTrapFrac` → `side_match` → `a_pass`) | **635/635 en rango cubierto, 0 campos distintos** (`lo, hi, vol, rows, frac, a_score, a_thr`). Harness siguiendo los bordes del CSV, anillo cebado con los scores de las 714 cubetas previas tomados del propio CSV |
| fills | **634/635 exactos en precio Y timestamp** |

## La única discrepancia: fill de la zona `11537_B`

Mismo nanosegundo (2026-08-19 10:01:27.116000 ART). El CSV registra `fill_px=4498,3`;
la cinta tiene `4497,9` en ese tick. El corte entre las cubetas 11537/11538 cae dentro
de un bloque grande de ticks que comparten el mismo nanosegundo; en el tramo
inspeccionado el 4498,3 no aparece ni en `last` ni en `bid` ni en `ask`.
Hipótesis: NT8 vio un tick que el export Last no trae, o el .cs toma el precio de otra
fuente en ese camino. **ABIERTO.**

Detalle menor adicional, misma zona: `ZONE_CREATED` loguea `a_score=12` y el `FILL`
loguea `a_score=12,5`. Inconsistencia de log, no de detección.

Impacto: 1/635 = 0,16 % de los fills. Alcanza para no firmar 100 %; no alcanza para
declarar la paridad rota.

## Lo que esto dice del registro actual

`tools/visor_server.py` declara
`PARIDAD["BigTrap2Absorption"] = ("EXACT", "GC DEC26 28.042/28.042 EXACT (100%), 0 discrepancias")`.

Medido: **cierto en sustancia sobre el 97,45 % cubierto** (matemática de cubeta, umbral
causal y zonas reproducen exactas); **falso en la forma**:

1. 714 cubetas iniciales no medidas en esta validación (la cinta provista no las tiene).
2. 1 fill de 635 con precio distinto.
3. No hay artefacto de la corrida de Antigravity en el repo: el número viaja como string
   literal. Misma familia que P-34: la etiqueta no se deriva del contenido.

## El kernel Python commiteado NO reproduce esta paridad

`edgelab/bridge/indicators/bigtrap2absorption.py` (331 líneas, commit `1f8a5b6`),
corrido verbatim sobre la cinta: **605 zonas, solo 32 coinciden** con el CSV en
(side, lo, hi, a_score). Dos causas medidas:

1. **No tiene concepto de sesión.** Hace `break` en la primera cubeta corta y pushea
   TODAS las cubetas al anillo. El .cs marca residuales, les fuerza `a_pass=False` y las
   excluye del historial. En el stream completo, el kernel diverge desde la cubeta 3947
   (primer fin de sesión).
2. **La grilla naif exige que la cinta arranque en borde de cubeta.** Esta cinta arranca
   12 ticks adentro de la cubeta 714 y el desfase se arrastra a todo lo posterior.

La semántica del .cs SÍ es reproducible (el harness del auditor cierra 100 % siguiendo
los bordes del CSV), pero hoy vive en un script de auditoría, no en el kernel
versionado.

### Correcciones necesarias del kernel (para que la etiqueta sea medible)

1. Cortar cubeta en fin de sesión (calendario CME, `session_ids` de `bars.py`) con
   marca `residual`.
2. Residuales: `a_pass=False` forzado y no entran al anillo.
3. Resolver el fill 11537 (ordenamiento dentro del mismo ns, o fuente de precio
   alternativa).
4. Recién entonces: correr la paridad con el kernel versionado y **subir el artefacto**
   (JSON con conteos por capa). Ahí la etiqueta `EXACT` tiene respaldo.

## No medido acá

- Campos `TRAP` por cubeta (`run_*`, agregado legacy `vol/centroid/max_ratio`): no
  comparados.
- Las 714 cubetas del domingo: la cinta provista no las incluye.
- Parquets L2 (jun 22–26 y ago 16–20, provistos hoy): el sandbox de Notion no tiene
  pyarrow/duckdb ni red; inspección de contenido NO hecha desde ahí. Los de agosto son
  período de holdout gastado: solo esquema/integridad/relojes cuando se lean.
