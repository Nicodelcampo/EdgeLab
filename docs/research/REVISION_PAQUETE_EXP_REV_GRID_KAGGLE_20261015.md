# Revisión del paquete EXP-REV-GRID entregado en Kaggle (otro agente)

Estado: REVISIÓN — lectura de documentos y código; no se ejecutó nada del paquete ni se descargó la release.
Fecha: 2026-10-15 · Revisor: Claude (agente de la línea corredores).
Objeto: notebook `nicolasbuttaro/edgelab-grid-03-documentation-handoff` (salida: `EXP_REV_GRID_COLLABORATION_PACKAGE.zip`, `START_HERE.md`, `documents/*`, `repository/edgelab/research/reversal_grid/{core,models,preflight,smoke}.py`, tests) y notebooks 00/01/02 (privados). Recuperado vía `get_kernel_output` del puente.

## Veredicto
**Buen primer componente, sin hallazgos bloqueantes en lo leído.** Es preparación técnica (sintética), no experimento. El diseño recoge la auditoría externa: primer paso R/C/0 con censura, hazard de riesgos competitivos, tiles multiescala con máscara de cobertura, `available_at` en el ledger, partición restringida a descubrimiento (≤ 2026-03-31) y fail-closed.

## Lo verificado en el código
- `core.tiles`: ventana `(decision−lookback, decision]`, índices enteros (sin sesgo de borde), ticks de igual timestamp no se reordenan, cobertura por bin; escalas con igual tensor. Correcto.
- `first_passage`: usa `t > entry_ns` (estricto), empate de barreras en el mismo ns → `AMBIGUOUS` o `C` por política; sin precio de salida inventado para `TIMEOUT`. Conservador y coherente.
- `discretize_label` + `hazard_nll` + `cumulative_incidence`: consistentes entre sí (evento en bin `(prev, right]`; censura cuenta sólo bins completos; incidencia + supervivencia suman 1).
- `discovery_dates` rechaza fechas fuera de 2025-07-18…2026-03-31: **respeta HOLDOUT-A3** y es más estricto que mi línea de corredores (que perdió su réplica de ES por usar las 299 sesiones).

## Observaciones y sugerencias
1. **Hash de `NORTH_STAR.md`.** El paquete cita `05df5c7c…`, que es el vigente (`tests/test_north_star_hash.py` pasa). Mis documentos de hoy citaban `ed4293b5…`, una versión vieja heredada del texto de sesión; ya está corregido en propuesta, manifiesto y adenda.
2. **Timeouts son la mayoría en mi medición** (55–61 % de los eventos de `HA` en 100T con barrera 1,0H y horizonte de 400 barras). `TIMEOUT` sin precio de salida significa que la economía (E[retorno al vencimiento]) queda sin resolver: antes de elegir X, Y y T conviene medir cuántos eventos quedarían sin resolver y fijar un objetivo que mantenga los timeouts bajos o modelarlos explícitamente.
3. **Datos disponibles no usados:** el parquet de la release v4 trae `aggressor`, `bid_ticks`, `ask_ticks` y `regime_id` además de precio y volumen. Hoy el paquete los excluye (política D13 pendiente); si el agresor se aprueba, es el canal que más cambia el contenido del tile.
4. **Costo de cómputo:** `tiles` usa `np.add.at` por ventana; con ~305 M de ticks de ES conviene un acumulador por sesión (cumsum/bincount o Numba) y ventanas por índice, tal como pide el plan. Sin cambios de semántica.
5. **Coordinación de líneas.** Su paquete lee mis documentos y no transporta mis candidatos, lo cual es correcto: el detector del corredor y mi tabla de eventos (`data/corridor_dev`, 299 sesiones, con ventana de réplica ya inspeccionada) **no** son una población virgen para EXP-REV-GRID. Si la reutilizan como definición de "expansión", deben declarar esa historia de exposición.
6. **Antecedentes relevantes para sus decisiones pendientes** (de `RESULTADOS_ADENDA_D_DESARROLLO_CORREDOR_20261015.md`): el detector con `SMA(Range)` y con EMA del true range dan zonas casi idénticas (8.617 vs 8.604); `HA` no es rentable neta de fricción en ES (neto −2,0 ticks, bruto +1,5 ticks, IC95 del bruto incluye 0); ni T1–T5 ni un baseline continuo de hora/volatilidad/trayectoria mejoran el neto a positivo.
7. **Integración local:** su `config/modules.json` y los registros son propuestas; revisar contra el repo actual antes de mergear. `docs_index --check` reporta dos documentos de corredores sin `Estado:` (de otra línea): corregibles agregando el encabezado, sin tocar contenido.

## Qué no cubre esta revisión
No ejecuté los 34 tests ni los notebooks, no revisé `smoke.py`/tests en detalle ni el bundle git, no abrí ticks ni particiones reservadas. Los recibos de Kaggle son los del otro agente y no los recalculé.

*Aporte al referente:* alinea las dos líneas de trabajo sobre las mismas reglas (partición, hash, timeouts) y deja claro qué evidencia puede pasar de una a otra y cuál no.
