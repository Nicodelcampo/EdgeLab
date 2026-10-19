# MNQ L2 V2 — diagnóstico candidato, una sesión local

**V1 queda congelado; no continuar las 52 con V1.** El primer paquete reprodujo 31 señales, pero 27 máscaras desconocidas y publicación live no certificada. Ver acta primera sesión. V2 cambia semántica de disponibilidad: opt-in explícito, no estrategia aprobada ni filtro financiero nuevo.

Cloud hace diseño/QA/lectura. Local sólo ejecuta UNA sesión, sin returns. Una worktree propia, HEAD remoto actualizado, repo lock/venv, sin otro proceso pesado; no editar visor ni raw. No relajarse pins para verde. Revisar README/AGENTS/PROJECT_INDEX antes.

```powershell
$env:PYTHONPATH="tools"
.venv\Scripts\python.exe -m unittest discover -s tests/research -p "test_mnq_l2_prepare_v2.py" -v
.venv\Scripts\python.exe tools/mnq_l2_prepare_v2.py --root E:\l2_parquet --catalog docs/research/contract_regimes/L2_sessions_catalog_20260927.json --book-module edgelab/research/l2_phase0.py --out E:\mnq_l2_para_nube_v2 --clock ART --sessions 20260629 --max-sessions 1 --ack-diagnostic-v2
```

El último flag es reconocimiento explícito del candidato diagnóstico, no autorización financiera. Si Nico no acepta esta semántica, NO ejecutar. No inferir aprobación de resultados de la aprobación del exporter. Directorio output NUEVO y vacío, no mezclar V1/V2. Pasar `MNQ_targetfree_para_nube.zip` de ese output a nube, no subir JSONL/precios a repo ni público. Si falla: traceback y evidence si existe, sin reparar/tolerar a mano.

## Qué distingue

- `bar_close_row`: último LAST de la vela150.
- `snapshot_asof_row`/`snapshot_ts_us`: datos del grupo viejo.
- `available_row`/`available_ts_us`: primera fila siguiente REAL observada que deja publicar; estrictamente posterior al snapshot.
- `publication_mode`: fila siguiente, EOF sólo diagnóstico o fila después de sesión sólo diagnóstico. En casos no operables, máscara null.
- `book_gate_reason`: PASS, BOOTSTRAP_60S, INCOMPLETE_DEPTH, UNORDERED, CROSSED_OR_MISSING_TOUCH. No todas las ausencias son corrupción.
- `pico_pre_observation`: último snapshot ya publicado, conocido antes/al LAST del extremo; publica edad y filas.
- `pico_observation`: snapshot del grupo del extremo, publicado DESPUÉS; no información disponible antes del trade.
- `pico_association_known_at_row`: momento en que el detector identifica a qué zona pertenece el pico. No backdating.
- `multiple_bars_same_snapshot`: si varias velas se publican juntas, no inventar varios fills anteriores; tratamiento financiero pendiente.

Geometría/confirmación original y filtro en decisión NO cambiados; recoveries compatibles no son iceberg/absorción certificados. Observación en pico es diagnóstico, no filtro elegido por retorno. V1 queda disponible para comparación histórica, no publicación live.

Tras este paquete: medir gates, soporte previo/en pico/en decisión y frecuencia útil. Sin GO automático de 52; freeze/opt-in de semántica y gate target-free primero. Potencia y GC: plan separado. Cualquier outcome requiere manifiesto + OK de Nico.

## Aporte al referente

La PC necesita sólo ejecutar el diagnóstico; la nube se ocupa del resto, separando datos ya conocidos de publicación y asociación causal.
