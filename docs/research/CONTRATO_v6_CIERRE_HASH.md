# CONTRATO v6 — cierre de identidad del hash (2026-08-06)

Complementa `docs/CONTRATO_ANALIZADOR_PRED-004.md` (sección v6).

## Estado: ALINEADO

| | |
|---|---|
| `contrato_sha` canónico | `4ac53dba7fee2022a3873543abbeb3eb204e260f28b6e04dfb750da67949278d` |
| tip política ABSTAIN | `3c7419b` |
| tip strings alineados | `05ad94c` |
| T3a oráculo P5 | `626877f` · sha archivo `7d0f464fd4e1c90301799e2f854d7b5fb5a17d84f4f6600f082f2d4c0e17de27` |

## Valores exactos (acta §3.1 / `aeff855`)

```text
p5_seq_corrido_politica = "ABSTAIN"
p5_comparacion = "identidad_economica_en_orden;seq_absoluto_reportado;seq_corrido_implica_ABSTAIN_politica"
```

El implementador no forzó el hash cuando produjo `13444ebf…` (correcto).
Solo se cambiaron los dos strings del contrato; la lógica ABSTAIN no cambió.

## Batería

55/55 pred004 · suite 706 passed (reportado por implementador).

## Nota sobre el doc narrativo

Si `CONTRATO_ANALIZADOR_PRED-004.md` aún muestra el párrafo «NO coincide y no lo
fuerzo», ese párrafo queda **histórico del momento `3c7419b`**. La identidad
vigente es la de esta nota + el código en tip.
