# aVolClusterPOI parity NQ 06-26 — causa raíz de GEOMETRY_DIFF, 2026-09-01

**Estado: hallazgo con evidencia de código fuente, gate sigue en `FAIL` (no reclasificado).**
Complementa `AVOLCLUSTERPOI_PARITY_NQ0626_HANDOFF_2026-09-01.md` — ese documento
cerraba con el desfase de 3 ticks del classifier TICKBAR-001 sin resolver; esto
va más allá y encuentra el mecanismo exacto detrás de los 19 `GEOMETRY_DIFF`
del gate de paridad (no del classifier de TickBarDiag).

## El patrón, medido, no supuesto

Los 19 `GEOMETRY_DIFF` del gate (`docs/research/avolclusterpoi_nq0626_reports_20260901/paridad_avolclusterpoi_nq0626.json`)
son sistemáticos:

```
py=(199843, 199801) nt8=(199845, 199801) diff=1 ticks
py=(202695, 202659) nt8=(202695, 202655) diff=2 ticks
py=(207323, 207305) nt8=(207321, 207305) diff=1 ticks
py=(209369, 209331) nt8=(209373, 209331) diff=2 ticks
py=(210769, 210737) nt8=(210769, 210735) diff=1 ticks
```

`_geom_ticks()` devuelve `(top, bottom)` en medio-ticks. **El borde inferior
coincide exacto en las 5 muestras; el desvío está siempre en el superior**,
y siempre de 1-2 ticks. Un solo mecanismo, no ruido disperso.

## La lógica de detección se comparó línea por línea — coincide

- Umbral hot: `.cs` `if (kv.Value >= hotThreshold)` == Python `if vol >= med * float(median_multiplier)`.
- Mediana: ambos toman la mediana superior (`n/2` con lista ordenada, empate hacia arriba).
- Fórmula de precio del borde: `.cs` `lowerTick*TickSize - TickSize*0.5` /
  `upperTick*TickSize + TickSize*0.5` == Python `(lo_t - 0.5)*tick_size` /
  `(hi_t + 0.5)*tick_size`. Idénticas.

No hay bug de traducción en el umbral, el agrupamiento ni la conversión de
precio. La causa está antes: en qué ticks entran a `blockCells` para empezar.

## La causa: `nt8/aVolClusterPOI.cs`, líneas 303-315

```csharp
long lowTick = PriceToTick(Low[0]);
long highTick = PriceToTick(High[0]);
if (tickProfile.Count > 0)
{
    foreach (KeyValuePair<long, double> kv in tickProfile)
    {
        if (kv.Key < lowTick || kv.Key > highTick) continue; // defensa de borde
        ...
    }
}
```

Por cada barra primaria que cierra, NT8 filtra el `tickProfile` (subserie de
1 tick reconstruida) contra el rango `[Low[0], High[0]]` de **esa barra
específica**. Si por desfase de cierre llega un tick de la barra siguiente y
su precio cae fuera de ese rango, **se descarta, no se reasigna** — exactamente
la advertencia que ya estaba escrita antes de correr esto (ver handoff previo,
sección de la opinión del auditor sobre este mismo `if`).

El kernel Python (`edgelab/bridge/indicators/avolclusterpoi.py::run()`) no
tiene ese filtro: suma directo `footprints.total[bar]` por barra del bloque.
Si `build_footprints` (Python) y la reconstrucción de `tickProfile` (NT8)
difieren en uno o dos ticks de borde -- exactamente la clase de defecto que
`TICKBAR-001` ya documentó para otros indicadores a otras resoluciones --,
ese puñado de ticks entra en un lado y no en el otro, corriendo el borde
superior del cluster en 1-2 ticks. El inferior no se mueve porque, por
construcción de mercado, el desfase de cierre de barra tiende a agregar
actividad hacia arriba en un mercado con tendencia alcista dentro de la
ventana medida (2026-04-07..06-12) -- una observación, no una explicación
mecánica completa; no se afirma causalidad de esa asimetría específica.

## Lo que esto NO dice

- No dice que el kernel Python esté mal escrito -- la lógica de detección es
  idéntica, verificada línea por línea contra el `.cs`.
- No dice que el `.cs` esté "roto" en un sentido nuevo -- es el mismo defecto
  de borde de barra que TICKBAR-001 ya declaró, ahora con un segundo indicador
  afectado por el mismo mecanismo.
- No reclasifica el gate. `tools/paridad_oraculo.py` es explícito: **"no
  adjudica, no promueve... la etiqueta formal la decide quien lea el informe."**
  El gate corrido dio `FAIL` con `tol_geom_ticks=0`; esta nota da la causa,
  no un nuevo veredicto.

## Para decidir con el auditor

1. ¿Se acepta un `tol_geom_ticks` chico (1-2 ticks) para esta familia,
   documentado y acotado a la clase de defecto ya conocida -- o se exige
   corregir el filtro de borde del `.cs` antes de promover a `parity_covered`?
2. Si se corrige el `.cs`: el fix es acotado (no descartar el tick de borde,
   reasignarlo a la barra que realmente le corresponde por timestamp) -- pero
   es un cambio de comportamiento del indicador en producción, no algo para
   decidir unilateralmente.
3. Los `MISSING_IN_NT8` (57) / `MISSING_IN_PYTHON` (48) todavía no se
   diagnosticaron con el mismo nivel de detalle -- hipótesis de trabajo: el
   mismo mecanismo de borde puede empujar un cluster completo por debajo o
   por encima de `min_cluster_ticks=2`, haciendo que aparezca de un lado y no
   del otro. No verificado todavía, queda declarado como hipótesis, no hecho.

## Archivos de esta entrega

- `data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv` — oráculo real, NQ JUN26, CME US Index Futures ETH, 2026-04-07..06-12.
- `data/nt8_oracles/tickbar_diag_NQ0626__Tick120.csv` — ledger TickBarDiag, NQ JUN26, 120t, 2026-04-02.
- `docs/research/avolclusterpoi_nq0626_reports_20260901/` — reportes crudos del gate y del classifier (ya commiteados).
- `docs/research/AVOLCLUSTERPOI_PARITY_NQ0626_HANDOFF_2026-09-01.md` — handoff previo, contexto completo del proceso.
