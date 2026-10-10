# Cómo consultar el CerebroSSRN

## Uso simple (Claude Code, recomendado)

Abrí una sesión de Claude Code en `C:\$ACerebroSSRN` y escribí:

> Leé cerebro/CEREBRO_SSRN.md y cargá el contexto que indica. Después
> atendé mi consulta: [tu pregunta o el problema del ecosistema]

Modelo recomendado: **Sonnet** para consultas normales (el grafo completo
en contexto ya hace la mayor parte del trabajo), **Opus** para diseño de
experimentos importantes o auditoría de un hallazgo antes de implementarlo.

## Arquitectura (corteza + hipocampo + puente)

- **Corteza** (`cerebro/nucleo_grafo.md` + reglas de razonamiento): la
  estructura conceptual — qué es cada cosa y cómo se relaciona.
- **Hipocampo** (`pipeline/consultar.py`): búsqueda semántica local sobre
  los pasajes crudos de los ~400 papers — trae el texto exacto, citable.
- **Barro empírico** (`cerebro/hallazgos_por_mercado.md`): los resultados
  de backtests/experimentos reales del corpus, organizados por mercado y
  robustez.
- **Puente** (`cerebro/PUENTE_ECOSISTEMA.md`): el cruce ya hecho entre el
  grafo y el estado real de `C:\$AVectorBTecosistema` — qué conceptos ya
  están implementados, cuáles contradicen resultados propios, cuáles son
  oportunidades sin testear.

El protocolo del Cerebro ya incluye correr la recuperación antes de cada
respuesta. También se puede correr a mano:
`python pipeline/consultar.py "tu pregunta" -k 6`

## Qué esperar

- Consulta teórica ("¿qué es el order flow imbalance?") → definición del
  grafo + relaciones + hallazgos que la miden + citas de papers.
- Consulta sobre el ecosistema ("¿cómo mejoro el filtro de zonas HFT?") →
  respuesta en 4 partes: qué dice el corpus, la evidencia y su peso, la
  brecha con el ecosistema propio, y un próximo experimento concreto.

## Qué NO esperar

- No es asesoramiento financiero ni un generador de señales para operar en
  vivo.
- SSRN no tiene peer review: el Cerebro es deliberadamente escéptico y
  declara la robustez de cada hallazgo — no trata todo el corpus como
  verdad establecida.
- Los PDFs pueden tener OCR degradado; las citas textuales pueden incluir
  errores de reconocimiento de caracteres tal como aparecen en la fuente.

## Mantenimiento

Pipeline completo, en orden, reproducible desde cero:

```
python pipeline/extract_pdfs.py          # PDFs -> texto + manifest
python pipeline/chunk_docs.py            # texto -> chunks.sqlite
python pipeline/embed_chunks.py          # chunks -> embeddings locales
# Fase 2 (extracción): agentes/Workflow sobre extraccion/docs_list.json
#   siguiendo extraccion/PROMPT_EXTRACCION.md -> extraccion/completo/*.json
python pipeline/validate_extraction.py   # audita citas verbatim
python pipeline/consolidate_concepts.py  # extraccion/completo -> nodos_dryrun.json
python pipeline/prepare_judge_package.py # recorta para revisión de jueces LLM
# Jueces (Sonnet/Opus, pocas llamadas): escriben grafo/decisiones_jueces.json
python pipeline/build_graph.py           # nodos_dryrun + decisiones -> grafo_final.json
python pipeline/detect_communities.py    # Louvain -> comunidades.json
python pipeline/build_context_pack.py    # grafo_final -> nucleo/indice/hallazgos .md
python pipeline/prepare_anchor_context.py # arma el paquete para el puente
# Puente (agente): cruza contra C:\$AVectorBTecosistema -> PUENTE_ECOSISTEMA.md
```

Si se agregan PDFs nuevos al downloader: correr todo el pipeline de nuevo.
Es idempotente — `build_graph.py` reconstruye el grafo completo desde
`nodos_dryrun.json` + `decisiones_jueces.json` cada vez, nunca aplica
parches encadenados (lección del CerebroJLP: evita el pipeline
no-reproducible que forzó su Fase 3.5 de rebuild).

Si se corre un análisis nuevo en el ecosistema VectorBT (como
`brute_excursions`): re-correr `prepare_anchor_context.py` + el agente de
puente para que `PUENTE_ECOSISTEMA.md` refleje la evidencia más reciente.
