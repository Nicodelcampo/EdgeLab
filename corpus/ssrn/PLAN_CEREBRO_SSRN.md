# Cerebro SSRN — Plan maestro y estado del proyecto

> **Referente**: un razonador construido sobre ~400 papers de trading
> cuantitativo (SSRN), cuyo fin NO es teórico sino **mejorar el ecosistema
> real de backtesting del usuario** (`C:\$AVectorBTecosistema`, quantlab +
> VectorBT sobre el ES). No es un buscador de citas: es un crítico
> cuantitativo escéptico con acceso simultáneo a todo el corpus, que propone
> experimentos concretos y audita los propios.

Réplica de la infraestructura del **CerebroJLP** (mismos 5 principios de
diseño: LLM lee el corpus una sola vez; local-first; toda afirmación con
cita; checkpoint/resume; el grafo final ES el contexto). Adaptado del
dominio esotérico al cuantitativo.

## Estado al 2026-07-13 — CEREBRO v1 CONSTRUIDO Y FUNCIONAL

Pipeline completo corrido sobre **168 papers** (de 401 del corpus; la
extracción se detuvo por límite de tokens de sesión — el resto queda para
re-correr, ver "Pendientes"). El cerebro es consultable end-to-end.

- **F0 (PDFs→texto)**: `extract_pdfs.py`. 401 papers → texto normalizado +
  manifest, cruzado con `ssrn_papers_master.csv`. PyMuPDF, 100% local.
  5,25M palabras.
- **F1 (chunking+embeddings)**: `chunk_docs.py` + `embed_chunks.py`. 3.254
  chunks → 24.340 pasajes → `embeddings.npy` (multilingual-e5-small, elegido
  a propósito para recuperación cross-lingual: consultas en español sobre
  corpus en inglés). Bibliografía recortada del índice semántico.
- **F2a (gold set)**: 5 papers representativos → `PROMPT_EXTRACCION.md` v1
  (schema quant: conceptos + hallazgos empíricos con robustez + aplicabilidad
  al ES). Validado: citas verbatim.
- **F2b (extracción masiva)**: Workflow de agentes (Sonnet effort bajo) +
  extracciones manuales con Gemini. 168 destilados válidos en
  `extraccion/completo/`. Checkpoint por archivo.
- **F2.5 (normalización)**: `normalize_extractions.py`. Armoniza las
  variantes de formato de Gemini (BOM, hallazgos-como-strings, sin doc_id).
  20 stubs sin conceptos → `descartadas/` + `pendientes_reextraccion.json`.
- **F3 (consolidación)**: `consolidate_concepts.py` (fuzzy local) +
  `decisiones_jueces.json` (juicio de Opus: 6 fusiones de sinónimos, 16
  mapeos de tipos de relación) → `build_graph.py`. **Grafo idempotente**
  (corrección preventiva del defecto #2 del CerebroJLP: reconstruible desde
  cero, sin parches encadenados). **1.223 nodos, 1.864 aristas.**
- **F4 (comunidades)**: `detect_communities.py` (Louvain ponderado). 254
  comunidades, 28 con ≥5 nodos. Resúmenes narrativos en
  `grafo/comunidades_resumen.md`.
- **F5 (puente al ecosistema)**: `prepare_anchor_context.py` +
  `cerebro/PUENTE_ECOSISTEMA.md`. **La pieza que cierra el circuito**: cruza
  el grafo contra el estado real del ecosistema VectorBT (logger hft_zones,
  strict_touch, el estudio de excursiones del 12-jul) y organiza 5 usos
  concretos para encontrar edge, cada uno con un próximo experimento
  ejecutable sobre quantlab.
- **F6 (runtime)**: `cerebro/CEREBRO_SSRN.md` (reglas de razonamiento con
  escepticismo cuantitativo), `nucleo_grafo.md` (317 nodos centrales, ~24k
  tokens), `indice_cola_larga.md` (906 nodos), `hallazgos_por_mercado.md`
  (429 hallazgos), `consultar.py` (RAG local: corteza + barro empírico +
  hipocampo), `COMO_USAR.md`. **Probado**: recupera correctamente y aplica
  el escepticismo (marca robustez, no confunde Sharpe espectacular con
  evidencia).

## Arquitectura del cerebro (tres memorias)

```
consulta (español)
  → consultar.py [local, cross-lingual]:
      CORTEZA    (grafo_final.json: nodos + relaciones tipadas)
      BARRO      (hallazgos.json: backtests con robustez/condiciones)
      HIPOCAMPO  (24.340 pasajes crudos, e5-small)
  → sesión con CEREBRO_SSRN.md + nucleo_grafo.md cargados:
      razona con escepticismo, ubica en el mapa, cruza el PUENTE,
      propone el próximo experimento sobre el ecosistema ES
```

## Los 5 usos para encontrar edge (detalle en PUENTE_ECOSISTEMA.md)

1. **Auditor anti-overfitting** (prioridad): deflated Sharpe + FDR +
   purged CV sobre las corridas de `brute_excursions`/Optuna. Ataca la duda
   del reporte de zonas del 12-jul (split IS/OOS en el roll).
2. **Fábrica de features de order flow**: OFI, Kyle lambda, Hawkes sobre los
   ticks L1 → ejes nuevos de la grilla de zonas.
3. **Meta-labeling de las zonas HFT** (mayor esfuerzo/retorno): XGBoost
   secundario sobre el evento primario "toque de zona".
4. **Condicionamiento**: hora del día + régimen de vol como filtros.
5. **Realismo de costos**: impacto/slippage en la simulación de outcomes.

## Pendientes (en orden)

1. **Completar la extracción** de los ~233 papers restantes + los 20 stubs
   descartados (`pendientes_reextraccion.json`). Con Gemini o en una sesión
   con tokens. Al terminar: re-correr `normalize_extractions.py` →
   `consolidate_concepts.py` → `build_graph.py` → `detect_communities.py` →
   `build_context_pack.py` (todo local, minutos). El grafo se regenera solo.
2. **Filtrar papers off-topic**: algunos entraron por keyword de SSRN (teoría
   de grafos, etc.). Quedan aislados e inofensivos, pero se podría podar por
   comunidad desconectada del núcleo de trading.
3. **Ejecutar el Uso 1** (auditor) como primer experimento real: agregar el
   ajuste por multiplicidad a `brute_excursions.py`. Es el de mayor valor y
   no necesita datos nuevos.
4. **Re-visar las 34 extracciones de Gemini con citas no-verbatim**: los
   conceptos son buenos, pero las citas están parafraseadas/elididas. Baja
   prioridad (no rompe el grafo).

## Mantenimiento

Ver `cerebro/COMO_USAR.md`. Pipeline reproducible desde cero; idempotente.
Si se corre un análisis nuevo en VectorBT: re-correr `prepare_anchor_context.py`
y actualizar `PUENTE_ECOSISTEMA.md`.
