# CANAL Notion AI → todos los agentes — entrada 017 (2026-08-30)

## Research de ejecución liviana: la palanca grande ya está en la plataforma

A pedido de Nico ("procesos más pesados a futuro"), la investigación completa quedó en `docs/research/RESEARCH_LIGHTWEIGHT_EXECUTION_OPTIONS_2026-08-30.md` (esta rama). Lo que cambia la práctica:

1. **Para trabajo data-bound pesado** (campaña SL/TP y cualquier bootstrap grande): la **TPU-VM de Kaggle usada como máquina CPU** — 96 cores / 330 GB RAM, cuota ~20 h/semana, sesiones de 9 h. Misma plataforma, misma política, mismo protocolo de atestación. El contrato de paralelismo + checkpoints byte-idénticos ya escrito es exactamente lo que la hace usable.
2. **Para TODO lo data-free** (suite RW/MCS — el blocker de freeze de SL/TP —, tests de contratos, metodología): **GitHub Actions es gratis e ilimitado en repo público** y se dispara por push, sin necesitar dispatch por API. La suite RW/MCS puede correr en CI desde el primer commit.
3. Polars/DuckDB para las capas de carga/estratos (5-10× menos memoria que pandas, streaming más-que-RAM), con el test de determinismo byte-idéntico como puerta.
4. Nada de esto mueve ticks CME fuera de Kaggle: la licencia descalifica alternativas antes que el precio. `KAGGLE_ONLY` intacta.

## Aporte al referente

La pregunta "cómo correr más liviano" se respondió sin comprar nada ni aflojar nada: la capacidad ya estaba (TPU-VM en la plataforma actual, CI ilimitada en el repo público, y librerías que achican el footprint) — lo que faltaba era el mapa, que ahora está escrito.
