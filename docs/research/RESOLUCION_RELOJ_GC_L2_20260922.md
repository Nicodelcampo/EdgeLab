# Resolución forense del reloj L2 — GC 08-26 (Market Replay NRD→CSV)

- **Fecha:** 2026-09-22
- **Estado:** `NT8_WALL_CLOCK_RESOLVED_ART_UTC-3`
- **Alcance:** target-free. Solo reloj/timezone de `ts_us`. Sin señales, sin outcomes, sin P&L.
- **Corrige:** `NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED` en `tools/build_l2_viewer_bundle.py` (auditoría 2026-09-21) y en `edgelab/data/l2.py`.
- **Precedente y método:** el mismo procedimiento forense que resolvió el reloj de ES en `docs/research/INTAKE_L2_ES_NRD_2026-08-21.md` §5.1 (evidencia empírica contra el calendario oficial de CME: halt de mantenimiento, apertura dominical, cierre de semana).

## 1. Evidencia

Se corrieron las 30 sesiones GC 08-26 ya convertidas (`E:\DatosNT8\gc_aug26_canonical_parquets`), buscando gaps de actividad > 300 s en la serie combinada `ts_us` (L1+L2, ordenada) e interpretando `ts_us` primero como UTC literal.

**Regla CME (igual que para ES):** el halt diario de mantenimiento de Globex es **16:00–17:00 Central Time (CT)** de lunes a jueves. En verano boreal (DST activo, como todo el rango de fechas de esta captura, 27-may a 30-jun) CT = CDT = UTC-5, así que el halt real es **21:00–22:00 UTC**.

**Resultado — 20 sesiones lunes-jueves, sin excepción:**

| Muestra | Gap principal (`ts_us` leído como UTC) | Duración |
|---|---|---:|
| 20260527 (mié) | 18:00:00 | 2106 s |
| 20260601 (lun) | 18:00:00 | 2199 s |
| 20260610 (mié) | 18:00:00 | 2201 s |
| 20260615 (lun) | 18:00:00 | 2100 s |
| 20260618 (jue) | 18:00:00 | 2199 s |
| 20260630 (mar) | 18:00:00 | 2152 s |
| … (las 20 sesiones lunes-jueves de las 30 disponibles) | **18:00:00, sin excepción** | 2086–2201 s |

`18:00:00` leído como UTC, más 3 horas, da exactamente `21:00:00` UTC real = `16:00` CDT = el halt oficial. La única lectura consistente es que `ts_us` **es hora de pared en ART (UTC-3)**, no UTC.

**Segunda confirmación, independiente — borde de archivo.** Las 20 sesiones lunes-jueves empiezan **exactamente a las `01:00:00`** (mismo patrón que ES: `01:00:00 ART` → `00:59:59 ART` del día siguiente, ver `INTAKE_L2_ES_NRD_2026-08-21.md` §5.2). Si `ts_us` fuera UTC literal, el borde de archivo caería en un huso horario arbitrario sin relación con ningún evento de mercado; en ART cae justo después del cierre de la sesión Globex del día anterior.

**Tercera confirmación — calendario, no artefacto.** Los viernes (20260529, 20260605, 20260612, 20260619, 20260626) **no** muestran el gap de 18:00: dos no tienen ningún gap grande, y los otros tres muestran un patrón distinto (corte más tardío o más largo, coherente con el cierre de semana del viernes a las 17:00 CT en vez de la reapertura del halt diario). Los domingos (20260531, 20260607, 20260614, 20260621, 20260628) arrancan tarde (10:52–12:07) con actividad rala hasta un gap grande seguido de más actividad cerca de las 18:00–18:40 — coherente con el patrón de pre-apertura dominical ya documentado para ES (impresiones preliminares seguidas del arranque real del flujo). Ninguna de las 30 sesiones contradice la hipótesis ART.

## 2. Conclusión

`ts_us` en los parquets `l1_quotes`/`l2_depth` de GC 08-26 (fuente `E:\DatosNT8\replay_gc0826_raw_csv`, mismo `NRDToCSV` que ES) está en **hora de pared ART (America/Argentina/Buenos_Aires, UTC-3, sin horario de verano)**, exactamente como se determinó para ES. No es un hallazgo nuevo de mecanismo — es la misma máquina, mismo NT8, mismo AddOn de conversión — pero **no se puede asumir sin medir por instrumento/sesión**: éste es el registro de esa medición para GC.

## 3. Qué NO cambia

- **`CUTOFF_DATE = 20260630`** (el límite pre-holdout en `tools/build_l2_viewer_bundle.py`) **no se toca**. El margen de ese corte no dependía solo de la incertidumbre del reloj; es un límite de holdout y su modificación requiere decisión explícita de Nico (regla permanente del proyecto). Resolver el reloj no autoriza a estrecharlo.
- **La referencia absoluta UTC↔ART entre L2 y los ticks `.Last.txt`** sigue sin resolverse — eso es un problema distinto (correspondencia entre dos fuentes con conversores distintos, no solo el timezone de una sola). El acople `join L2 ↔ .Last.txt por timestamp cercano: prohibido` (señalado por el auditor) sigue vigente hasta que se resuelva aparte.
- El holdout permanece sellado; esta medición no abrió ni miró outcomes.

## 4. Qué cambia en el código

`tools/build_l2_viewer_bundle.py`, `meta` del bundle:
- `clock`: `NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED` → `NT8_WALL_CLOCK_RESOLVED_ART_UTC-3_20260922`
- `chart_tz`: `"UTC (reloj NT8, referencia sin resolver)"` → `"America/Argentina/Buenos_Aires (ART, UTC-3) — resuelto 2026-09-22, ver docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md"`

Los bundles ya generados (por ejemplo `GC_L2_20260615.json` en el visor) conservan el meta viejo hasta que se regeneren; no hace falta regenerarlos para que esto quede correcto — es metadata descriptiva, no afecta ningún cálculo ya hecho.
