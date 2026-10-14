# EdgeLab

Sistema para encontrar, validar y desplegar edges de trading en futuros CME: **expectativa neta, válida fuera de muestra, robusta y ejecutable**, rechazando los falsos antes de arriesgar capital.

Estado: **0 edges promovidos** (`EDGES_DISCOVERED.md`). Objetivo rector: `docs/NORTH_STAR.md`.

## Empezar (en este orden)
1. **`docs/research/HANDOFF_2026-10-14_DATOS_L2_Y_INTEGRACION.md`** — entrada vigente: datos, L2, integración y prioridades.
2. **`docs/PRODUCT.md`** — qué es EdgeLab, capas, roadmap R0–R6 y quién decide qué.
3. **`docs/MODULES.md`** — cada módulo: función, entradas, salidas, dependencias, documento y tests (generado desde `config/modules.json`).
4. **`docs/DOCUMENTATION_PROTOCOL.md`** — dónde va cada documento, encabezado obligatorio y cómo evitar pérdida de información.
5. **`docs/INDEX.md`** / `docs/INDEX.csv` — catálogo de toda la documentación, por familia y estado.
6. `PENDIENTE.md` (decisiones abiertas) · `docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` (qué está medido).

Primer comando de cada sesión: `python tools/estado.py`. Verificaciones del producto: `python tools/check_modules.py` y `python tools/docs_index.py --check`.

## Reglas que no se negocian
- Sin P&L, retornos ni holdout sin OK explícito de Nico, con manifiesto y número efectivo de hipótesis.
- Lo que decide algo vive en el repo, en Markdown. Chat, Notion y Drive son espejos.
- Los datos crudos, parte de `runs/`, oráculos reales y cuarentenas son local-only: que falten en un clon no prueba que no existan.

**Rama viva:** `foundation/f0b-compatibility-probe`. Ojo: `main` **no** es un baseline; tiene una línea paralela (AVZVOL, funnel, compuerta de datos). Ver `docs/research/INVENTARIO_LINEA_MAIN_20261014.md`.
