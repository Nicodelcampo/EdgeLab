# H-CLUSTER-NQ — FUERA DEL PROYECTO

**Decisión de Nico, 2026-09-21:** *«el indicador de clusters HFT queda fuera del proyecto; por ahora solo
usamos el indicador que marca zonas individuales»*.

Esta carpeta conserva, sin borrar nada (historial completo con `git log --follow`), toda la familia
`H-CLUSTER-NQ`: los indicadores NT8 (`HFTClusterZonesNQ.cs`, `HFTClusterZonesNQDx.cs`), su espejo Python
(`hftclusterzones.py`), los módulos de decaimiento y rechazo, los runners, los tests y las actas.

## Estado en que quedó (para que nadie lo reabra sin saberlo)

- Paridad de la capa de **zonas** compartida: EXACT (pero el indicador vigente es `HFTZonesNQPureV4(_V2)`).
- Paridad de la capa de **clusters**: nunca se certificó (faltó el oráculo).
- H1 (atracción): sin efecto detectado, con cota (MDE 0,067).
- **H2 (rechazo en bordes): ANULADA POR ESCALA** — el estimador no medía la hipótesis
  (`docs/research/H2_VOID_POR_ESCALA_2026-09-08.md`). No es un nulo.
- Defecto sin corregir en los runners: entregaban la zona al motor de clusters en la barra de INICIO y no de
  FINAL (look-ahead sobre el 98,2 % de las zonas).
- Las corridas de campaña incluyeron sesiones no operables (un feriado y dos post-roll).

## Qué NO se archivó, y por qué

- `edgelab/stats/cluster_estimand.py` es inferencia *clusterizada por sesión* (otra acepción de «cluster»).
- `edgelab/bridge/indicators/hftzones_nq.py` y `docs/research/CENSO_ZONAS_NQ_2026-09-07.md` son de **zonas individuales**.

## Lo que sí sigue vigente de esta línea

El aprendizaje metodológico **ATJ-18** (`docs/research_funnel_playbook.md`): el estimador también es una
hipótesis; un nulo puede ser del estimador.

## Recuperar

`git mv archive/h_cluster_nq_fuera_del_proyecto/<ruta> <ruta>`. Los `.cs` que corren en la instalación de
NinjaTrader (`Documents\NinjaTrader 8\bin\Custom\Indicators\`) **no fueron tocados**: retirarlos de ahí es
decisión de Nico.
