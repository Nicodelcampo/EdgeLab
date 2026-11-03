# Familias de Gemini: cuáles valen, qué se corrigió y qué se lanza (03/11/2026)

Estado: VIGENTE — enmienda de diseño ANTES de cualquier desenlace (ninguna de las 40 campañas había corrido). Referente: `docs/NORTH_STAR.md`,
cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Revisión de origen: `docs/research/REVISION_GEMINI_12_FAMILIAS_20261103.md`. Rama integrada: `gemini/familias-20261103`
(`c73bbb60`). Etapa del embudo: **EF2 exploratorio** (DESC → réplica → holdout por el embudo automático).

## Decisión: 6 familias valen, 6 no

| Familia | Decisión | Motivo |
|---|---|---|
| WM-FIXING | **arreglar y lanzar** (6E, 6B, GC) | Mecanismo de flujo documentado (fixing WMR de las 16:00 de Londres) y distinto de todo lo medido. |
| COMEX-CIERRE-ORO | **arreglar y lanzar** (GC) | Liquidación diaria del oro (13:30 ET, hora de NY: no tiene desfase de huso). Mecanismo propio. |
| ABSORCION-CLIMAX | **arreglar y lanzar** (ES, NQ, GC, 6E) | Clímax de volumen con mecha de rechazo: no es caja→ruptura. |
| ESTRUCTURA-HHLL | **arreglar y lanzar** (ES, NQ, YM, GC) | Retroceso a favor de la estructura de pivotes con stop estructural, en línea con el atlas en R. |
| OVERNIGHT-INVENTARIO | **arreglar y lanzar** (ES, NQ, YM, GC) | Inventario overnight contra su punto medio; distinto de GAP-RTH (que mide contra el cierre previo). |
| IMPULSO-POST-MACRO | **arreglar y lanzar** (ES, NQ, GC, 6E) | Sólo si dispara en días con dato a las 08:30 ET (antes corría todos los días). |
| LONDRES-IMPULSO, MEDIODIA-SUBASTA, PRIMERA-HORA-CONT, COMPRESION-NR, APERTURA-EUROPA-ORO, TOKIO-APERTURA-FX | **no se lanzan** | Son caja → ruptura, una gramática ya barrida (RANGO-ASIA, PREAPERTURA, RANGO0100, OTR930, MODELO-ASIA). Sin hipótesis incremental sólo suman multiplicidad. TOKIO además necesita resolver USDJPY → 6J. Quedan en el repo, apagadas. |

Instrumentos que se descartan dentro de las familias que siguen: WM-FIXING-EURUSD (spot → 6E duplica WM-FIXING-6E) y COMEX-CIERRE-XAU (spot → GC duplica GC).
Quedan **20 campañas**.

## Correcciones (código; tests y preflight en verde)

1. **Noticias durante TODA la operación** (Nico 2026-10-25: «las operaciones no pueden ser durante noticias»):
   - entradas bloqueadas a ±5 min de cualquier dato tier1 del calendario canónico (`eventos.TIPOS_TIER1`, 18 tipos; ABSORCION mantiene ±15);
   - **salida forzada antes de cada dato**: `rango_ruptura.lineas_salida_noticias` pone línea ±inf en las velas que cierran en
     [dato − 3 min, dato + 1 min] y la operación sale en la apertura siguiente, ≥ 2 min antes. El calendario se conoce de antemano: es
     causal. No se descartan operaciones por su salida futura.
   - ABSORCION-CLIMAX y ESTRUCTURA-HHLL no tenían salida por hora: ahora salen a las 15:55 ET y antes de cada dato.
2. **Reloj de Londres en WM-FIXING**: `regimen_sesion.minuto_local(t, "Europe/London")`. La ventana es 15:30–16:00 de Londres y la
   salida, 17:30 de Londres. Antes estaba fija en 10:30–11:00 ET, y en las semanas de desfase de horario de verano corría una hora antes del fixing.
3. **IMPULSO-POST-MACRO**: dispara sólo si la sesión tiene un dato programado a las 08:30 ET (cualquier impacto del calendario canónico).
4. Costos: todas las ejecuciones son futuros con fricción canónica medida (6E 4,16; 6B 3,88; GC 6,05; ES 3,55; NQ 6,18; YM 5,05 ticks).
   No queda ninguna ejecución spot → futuro.

## Multiplicidad y linaje

Cada campaña conserva su familia y su linaje sin padres (`LINAJES.jsonl`, registrados por Gemini antes de correr). La corrección cambia
la definición, no agrega celdas: siguen siendo 108 por canal. Fade y continuación (WM, COMEX, OVERNIGHT) son dos reglas de la misma grilla
y se cuentan juntas. Las 6 familias no lanzadas no consumen pruebas.

## Cómo podría refutarse

La misma condición de cada diseño (`DISENO_*.md`): ninguna celda nominada por FDR q 0,10 (con la cola t aprobada hoy) ni pista que
replique en abr–sep. Que la ventaja dependa de operar durante un dato ya no es posible por construcción.
