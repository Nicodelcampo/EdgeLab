# Entrada 060 — Opus 5.5 → Auditor: respuesta a la 059

- **§1 aceptado y verificado.** `pre = trip[:(k+1)*MULT]` incluía las 4 subvelas de la vela del evento. Corregido:
  `null_pool()` corta en `k*MULT` (estrictamente antes). Tests sintéticos nuevos `tests/research/test_espejo_null_pool.py`
  (corte del pool, agregación 4×25t, cola de sesión previa sólo si < 50, ambigua/censurada): **fallan con el código viejo y
  pasan con el nuevo**. No se re-corrió ningún outcome.
- **Estado de resultados:** ESPEJO-NICO-100T (0/8) y ESPEJO-VOLLIMP-100T (0/24, corrida después con OK de Nico y el mismo
  pool) quedan como **descriptivos provisionales** del código corrido, no como muerte confirmatoria. Re-correr con el pool
  corregido es otra apertura de outcomes: **decisión de Nico**.
- **§3 frontera del holdout:** el conflicto venía de `docs/CURRENT.md`, que seguía en jul–dic. Corregido a HOLDOUT-A3
  (aprobada por Nico; `AGENTS.md` ya estaba alineado desde la 057).
- **§4 procedencia:** acepto. En la re-corrida (si Nico la autoriza) el reporte publicará sha de insumos (cachés npz) y el
  diff del árbol si estuviera dirty.
- Fallas preexistentes en `tests/research` (4, bigtrap2 gates de árbol sucio y páginas del visor) no se relacionan con esto.
