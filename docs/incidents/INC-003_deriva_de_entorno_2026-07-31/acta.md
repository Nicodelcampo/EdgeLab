# INC-003: Deriva Global de Entorno y Vencimiento del Baseline (2026-07-31)

Este incidente documenta la pérdida de paridad entre el estado del repositorio y el entorno de ejecución, descubierta durante la auditoría de paridad del logger NT8.

## Mediciones de Pytest

Salidas finales de pytest verbatim. El baseline original era `510 passed, 3 deselected`.

**Árbol de producción (`E:\EdgeLab`):**
```text
= 24 failed, 472 passed, 1 skipped, 3 deselected, 13 errors in 270.16s (0:04:30) =
```

**Worktree aislado (`E:\EdgeLab_worktrees\nt8-logger-paridad`):**
```text
= 20 failed, 451 passed, 26 skipped, 3 deselected, 13 errors in 228.47s (0:03:48) =
```

## Consecuencias Detectadas

1. **El entorno derivó globalmente:** Ambos árboles fallan masivamente con `ArrowTypeError` (y un fallo explícito en `test_core_versions_satisfy_contract`), usando el mismo intérprete de sistema. El baseline de 510 passed está vencido.
2. **Defecto de testeo en worktrees (descubierto incidentalmente):** Un worktree aislado reporta **25 skipped extras** vs. el árbol de producción, sin fallar esos tests. Esto se debe presumiblemente a dependencias en artefactos no versionados (`runs/`, oráculos) que existen en el árbol principal pero no en un `git worktree add` nuevo. La cláusula SUITE del contrato ha estado comparando salidas asimétricas. Todo turno futuro en worktree debe declarar el delta esperado de skipped.
