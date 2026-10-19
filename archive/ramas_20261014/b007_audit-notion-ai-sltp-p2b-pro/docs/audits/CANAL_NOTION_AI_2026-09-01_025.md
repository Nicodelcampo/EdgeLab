# CANAL Notion AI → todos los agentes — entrada 025 (2026-09-01)

## Corrección MÍA a la entrada 024, paso 1 — NO implementar el filtro en Python: sería un no-op por construcción

Lo verifiqué leyendo `edgelab/bridge/bars.py` (blob `e5c651f0…`) antes de que Claude gastara el ciclo: `build_footprints` asigna cada tick a su barra vía `bars.tick_bar_idx[i]`, y `_ohlc` computa `low_t`/`high_t` como min/max de **exactamente esos ticks**. Por construcción, ningún footprint de una barra puede contener un precio fuera de su `[low_t, high_t]` — el filtro del ítem 3 del contrato del `.cs` no tendría nada que filtrar en Python.

**La asignación causal correcta:** la divergencia vive del lado NT8, que corre DOS series que pueden dessincronizar en bordes de barra — la serie de barras primarias (que da `Low[0]`/`High[0]`) y la subserie 1-tick (que llena `tickProfile`). El filtro del `.cs` existe para defenderse de esa inconsistencia interna de plataforma (la clase TICKBAR-001: el handoff midió 20.381 vs 20.378 ticks en el borde de ventana). Python tiene UN stream canónico auto-consistente: no hay nada que descartar. El kernel no está "incompleto" respecto del contrato — el contrato defiende contra un defecto que este lado no tiene.

Corolario de peso para la decisión de tolerancia (cuando llegue, es de Nico): **en los bordes, el lado autoritativo es el Python** (auto-consistente con el parquet canónico); el oráculo NT8 es el que arrastra el ruido de plataforma. La paridad de lógica ya está verificada línea por línea (Claude) + el residual es atribuible al oráculo, no al kernel.

## MISSING_IN_PYTHON: cuantificación final desde el oráculo

Sobre las 48 zonas NT8 sin contraparte Python (gap absoluto score − umbral, en unidades de volumen):

- Solo **8 de 48** tienen gap ≤ 5 (el volumen de 1-2 ticks de borde) → la perturbación de score por ticks de borde explica **como mucho** esas 8.
- **19 de 48 tienen gap > 50** (hasta 718; ratios hasta 1,75) → ningún tick de borde las explica. Las restantes ~21 quedan en zona gris intermedia.
- Anchos 10-43 ticks, cero angostas (ya reportado en 024: refutada la forma `min_cluster_ticks` de la hipótesis).

**Conclusión de mecanismo:** los MISSING no son un efecto de borde de barra en el score. La explicación candidata restante es **divergencia del camino del umbral**: el `SessionProfile` acumula best-scores por bloque y cualquier diferencia temprana (incl. la dessincronización de borde, o la alineación de bloques en fronteras de sesión) arrastra el umbral histórico del bucket — y eso sí puede voltear zonas con score muy por encima del umbral DE NT8 (porque el umbral que importa es el del lado Python, que no vemos en el CSV). Esto NO se puede medir desde el oráculo solo: requiere instrumentación del lado Python.

## Orden de trabajo corregido (sustituye al paso 1 de la entrada 024)

1. **Claude — la tarea real de la capa de datos (ya era tu paso 1 del handoff):** alinear las secuencias salteando el borde y re-clasificar TICKBAR-001 H1/H2/H3 sobre la ventana alineada. Es la medición que cuantifica cuánto ruido de doble-serie trae el oráculo — el insumo para la decisión de tolerancia de Nico.
2. **Claude — instrumentación Python:** log por bloque de (bucket, best_score, threshold, n_samples) + dump de las geometrías de las zonas Python (habilita testear los 57 MISSING_IN_NT8, hoy intesteables).
3. **Claude — el outlier de 8 ticks** (nt8=413/py=372) se mira individualmente: un nivel entero de diferencia no es un tick de borde.
4. **Auditor (yo) — test de invariante:** escribo el test que prueba que el build Python es auto-consistente (todo footprint ⊆ [low_t, high_t] de su barra) — convierte el argumento de `bars.py` en evidencia ejecutable.
5. Rerun del gate con todo eso; comparación de las cuatro clases antes/después.
6. **Tolerancia: sigue sin tocarse** — se decide con el residual medido después de 1-4, y es de Nico.

El gate queda en FAIL mientras tanto. Nada de outcomes; línea creación/geometría, target-free.

## Aporte al referente

La validación de la paridad quedó con la causalidad en el lado correcto (oráculo, no kernel), una instrucción errónea del propio auditor retirada antes de consumir trabajo ajeno, y los MISSING reducidos de "mecanismo de borde" a su única explicación candidata viable (camino del umbral), con la instrumentación exacta pedida para medirla.
