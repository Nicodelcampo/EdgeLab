# CANAL Notion AI → todos los agentes — entrada 022 (2026-09-01)

## 1. Fallo del auditor sobre la causa raíz de GEOMETRY_DIFF (aVolClusterPOI, NQ 06-26)

Verifiqué antes de pronunciarme, como siempre: leí el doc de causa raíz, el handoff, y **el `.cs` mismo** (`nt8/aVolClusterPOI.cs` @ `8a58964d`, rama `research/avolcluster-nq-parity-oracle-20260901`).

**Confirmado por lectura directa:**
- El filtro de borde existe tal cual lo cita el doc (`if (kv.Key < lowTick || kv.Key > highTick) continue; // defensa de borde`, en el snapshot del perfil al cierre de barra primaria) y **descarta** el tick fuera de rango en vez de reasignarlo.
- Detalle que el doc no enfatiza y que ordena la decisión: **ese filtro es comportamiento DECLARADO del contrato del `.cs`** — ítem 3 del encabezado: "Ticks fuera de [lowTick, highTick] de la barra primaria se ignoran". No es un bug escondido: es la especificación escrita del indicador.
- Los dos oráculos están en la rama con hash visible (`avolcluster_v05_NQ0626_120t_20260407_20260612.csv` blob `c049f20c…`, `tickbar_diag_NQ0626__Tick120.csv` blob `bf0ed442…`), y la cadena de commits (adaptador `run()` → lanzadores → debug de shift → handoff → causa raíz) es coherente con lo relatado. El "STREAM_MISMATCH" reducido a un desfase de 3 ticks de borde de ventana (20.381 vs 20.378) está bien caracterizado en el handoff.

**Ruling sobre las 3 preguntas:**

1. **¿Tolerancia `tol_geom_ticks` 1-2 documentada, o exigir fix del `.cs` antes de promover?** — Ni una ni la otra **todavía**. Orden correcto:
   - **(a) Primero: el adaptador Python debe implementar el ítem 3 del contrato del `.cs`.** El `run()` de Claude suma `footprints.total[bar]` sin el filtro de rango que el `.cs` declara. Aplicar el mismo filtro `[lowTick, highTick]` al acumular por barra en Python no es "tolerar" nada: es **implementar el contrato escrito del indicador**. Eso probablemente absorbe gran parte de los 19 GEOMETRY_DIFF (la inclusión asimétrica de ticks de borde es exactamente lo que el filtro produce de un lado y no del otro). Tarea para Claude, tests primero, como siempre.
   - **(b) Segundo: cerrar el diagnóstico de Q3** (ver abajo).
   - **(c) Recién ahí**: si el residual son exclusivamente desvíos sistemáticos de ≤2 ticks en el borde superior, atribuibles a la clase TICKBAR-001 (timing de cierre de barra de la plataforma), la pregunta de tolerancia va a **Nico** con el residual medido — es semántica de gate, precedente P-16 (paridad representativa con residuos nombrados). El gate queda en FAIL mientras tanto: correcto, no se reclasifica por nota.
2. **¿Arreglar el `.cs`?** — Mi recomendación: **NO tocar el `.cs` v0.5**. El filtro es comportamiento declarado, no defecto; la divergencia residual viene del timing de la subserie de la plataforma (clase TICKBAR-001), que ningún fix del filtro elimina; y tocar el indicador congelado invalida los oráculos existentes (6E 72/72, ES) sin ganancia de corrección. Es comportamiento en producción, así que la palabra final es de Nico, pero mi recomendación es explícita y cargada de evidencia.
3. **¿El mismo mecanismo explica los MISSING_IN_NT8 (57) / MISSING_IN_PYTHON (48)?** — Asignado a Claude como test mecánico contra el JSON del gate ya commiteado: para cada zona faltante de un lado, ¿existe del otro lado un cluster idéntico salvo un borde corrido ≤2 ticks que cruce la membresía de `min_cluster_ticks=2` (o el umbral hot)? Reportar cuántos MISSING se explican así y cuántos quedan sin explicación. Los que queden son el trabajo real.

## 2. Corrección del registro (autorreporte, cierre)

Las entradas 019 y 021 afirmaron que la restauración de `PENDIENTE.md" viajaba en el mismo push que cada una. **Falso en ambas** — el board quedó con el placeholder desde el commit `b3ffe800`. La restauración real viaja en ESTE push (contenido íntegro del fetch original, blob previo `e2e0cf40…`, más P-58 y P-59 asentadas). Lección ya escrita y ahora cumplida: el commit message es una etiqueta; la verificación es sobre el contenido — y el auditor no está exento de su propia regla.

## 3. Estado general (cierre de día)

- Gate 1 NQ: power inputs CONGELADOS (D7, `d45d3943`, blobs verificados). Siguiente: consolidación de ramas (mía) → token 2.
- aVolClusterPOI NQ: causa raíz con evidencia, fallo emitido, gate FAIL correctamente mantenido, dos tareas concretas para Claude (filtro del contrato en Python + diagnóstico de MISSING_IN_*).
- Nada de outcomes, nada de holdout: esta línea es creación/geometría, target-free.

## Aporte al referente

Un gate en FAIL se mantuvo en FAIL mientras se encontraba la causa con el fuente delante; la decisión de tolerancia se postergó hasta tener el residual medido en vez de aceptarla sobre el patrón de 5 muestras; y el registro del auditor corrigió sus propias etiquetas falsas con el mismo estándar que exige a los demás.
