# Enmienda HOLDOUT-A3 — descubrimiento / replicación por familia / holdout a futuro (2026-09-27)

**Decisión de Nico (chat, 27/09):** «dale, formalizá HOLDOUT-A3», sobre la propuesta de Claude de equilibrar potencia y rigor. Reemplaza el esquema de `HOLDOUT-A2` (todo exploración) para **ES y NQ**.

| Partición | Rango (sesiones CME) | ES | NQ | Uso |
|---|---|---|---|---|
| **Descubrimiento** | 18-jul-2025 → 31-mar-2026 | 181 | ~170 | grillas, búsqueda, elección de celdas (como siempre) |
| **Replicación** | 1-abr → 30-sep-2026 | 117 (65 + 52) | ~114 | **una vez por familia**, sólo sobre las celdas que sobrevivieron al descubrimiento, con dirección, estimand y umbral fijados antes |
| **Holdout** | desde la sesión del 1-oct-2026, a futuro | — | — | confirmación final (paper), una apertura por candidato |

## Reglas
1. La replicación **no elige nada**: no se buscan celdas, parámetros ni cortes en abr–sep. Si una familia la mira para diseñar, pierde su replicación.
2. Una sola corrida de replicación por familia; se publica completa (todas las celdas pre-registradas, pasen o no).
3. Si replica, el tamaño del efecto se reporta con descubrimiento + replicación juntos (298 sesiones en ES), y la decisión exige las dos.
4. Una familia que ya usó abr–jun como reserva o para diseñar (ninguna hasta hoy, según los registros) no tiene replicación disponible.
5. Otros instrumentos: siguen con el esquema viejo hasta que se descargue su jul–sep.

## Código
- `tools/tbz_e2.py`: `EXP_END = "20260331"` (descubrimiento, vuelve a su valor), `REP_START = "20260401"`, `REP_END = "20260930"`; `HOLDOUT_NS` = 2026-09-30 22:00 UTC.
- Las herramientas seleccionan la partición explícitamente (`--part rep`); por defecto usan descubrimiento.
