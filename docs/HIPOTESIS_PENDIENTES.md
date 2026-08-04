# Hipótesis pendientes

Observaciones con forma testeable que todavía no tienen campaña. No son
resultados: son cosas que alguien vio y que vale la pena medir cuando toque.

---

## HP-001 — Burst de zonas HFT al cierre, en **ES**

**Fecha**: 2026-08-04 · **Origen**: observación visual de Nico ·
**Estado**: registrada, sin medir · **Instrumento**: ES (no 6E)

Nico observa que al cierre del mercado aparecen muchas zonas HFT en ES, y
sospecha que de ahí puede salir un edge.

**Pospuesta a propósito**: el foco actual es 6E. No se mide todavía.

### Lo que sí se midió (y no aplica)

Se corrió el kernel `HFTZones2` sobre **6E 09-26**, 4 sesiones
(2026-06-15 → 06-18), 1.775 zonas, contadas por hora CT (cierre 16:00 CT):

| hora CT | 7–10 | 13 | 14 | 15 | 17–23 |
|---|---:|---:|---:|---:|---:|
| zonas | 32,4 % | 16,2 % | 13,4 % | **2,5 %** | **6,0 %** |

En 6E las zonas se concentran en las horas de máxima liquidez, no al cierre —
lo contrario a la observación. **Pero esto no refuta HP-001**: otro instrumento
y, en la observación original, otro indicador (`HFTZonesESPureV2`).

### Cómo medirla cuando se retome

1. Parquet canónico F2 de ES (no existe todavía; hoy solo hay 6E).
2. Correr `HFTZones2` v2.3, contar `created_ms` por hora CT — mismo
   procedimiento que arriba, que ya está probado.
3. Comparar contra la distribución de volumen por hora: si las zonas siguen al
   volumen, no hay nada específico del cierre.

### Precondición que puede invalidarla antes de empezar

En 6E la **mediana del intervalo entre ticks es 0 ms durante toda la sesión**
⇒ `Q(0.50)=0` ⇒ `resolution_limited=1` por el gate P0 del propio indicador: los
buckets de velocidad (PREDATOR/ULTRA/FAST) **no son confiables** porque se
clasifican por `avg_ms` y el feed no tiene esa resolución.

**Hay que verificar esto en ES antes de interpretar cualquier zona HFT.** Si ES
también da `resolution_limited=1`, la clasificación por velocidad no significa
nada y HP-001 habría que replantearla sobre volumen/rango en vez de timing.

*(`HFTZonesESPureV2` no tiene este gate ni ningún otro control de resolución, y
clasificaría todo como PREDATOR sin avisar. Ver la comparación de indicadores en
el reporte del 2026-08-04.)*
