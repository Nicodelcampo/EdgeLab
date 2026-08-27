# Research — leé estos, no el directorio

Una sesión nueva **no** abre `docs/research/` de forma indiscriminada. Si un documento histórico contradice `AUDITOR_START_HERE.md` o `docs/CURRENT.md`, manda el corte más reciente, salvo que el objeto tenga un spec/manifest congelado propio.

| # | Qué | Path |
|---:|---|---|
| 1 | Punto de entrada del traspaso | `AUDITOR_START_HERE.md` |
| 2 | Estado operativo vigente | `docs/CURRENT.md` |
| 3 | **Resultado final P2-A V1-R1** | `docs/research/bt2a_p2a_v1_r1_20260827/README.md` |
| 4 | Estado/firewall P2-A | `docs/research/bt2a_p2a_v1_r1_20260827/STATUS.json` |
| 5 | Resultado P2-A reconstruible | `docs/research/bt2a_p2a_v1_r1_20260827/result/reconstruct_gate2_p2a_result.py` |
| 6 | Auditoría de publicación P2-A | `docs/research/bt2a_p2a_v1_r1_20260827/REPOSITORY_PUBLICATION_AUDIT.md` |
| 7 | Inventarios completos | `docs/research/bt2a_p2a_v1_r1_20260827/checkpoints/complete/` · `source-package/complete/` |
| 8 | Handoff detallado anterior | `docs/HANDOFF_AUDITOR_2026-08-24.md` |
| 9 | Visibilidad y material local-only | `docs/REPOSITORY_VISIBILITY_AUDIT_2026-08-24.md` |
| 10 | Inventario de ramas | `docs/BRANCH_REGISTRY_2026-08-24.md` |
| 11 | Gate 1 BigTrap2Absorption | `docs/research/BT2_ABSORPTION_GATE1_ALL5_RESULT_2026-08-26.md` |
| 12 | Contrato/hardening Gate 2 y L2 | `docs/research/bt2a_gate2_l2_20260826/` |
| 13 | Incidente de outcomes histórico | `docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md` |
| 14 | Referente y decisiones | `docs/NORTH_STAR.md` · `PENDIENTE.md` |

## Línea primaria vigente

P2-A terminó sobre 234 sesiones con clasificación `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`. La publicación contiene el resultado agregado completo reconstruible, preflight, auditoría, tablas, logs, spec snapshot, manifiesto del Event Store e inventarios SHA-256 completos de 234 checkpoints y 251 archivos.

No leer esa clasificación como P&L, ganador, SL/TP, edge o promoción. P2-B, outcomes L2/HMM y holdout permanecen cerrados.

## Líneas secundarias que siguen accesibles

- GATE/L2: ramas separadas; cimiento técnico, outcomes no abiertos.
- `aVolClusterPOI`: instrumento/contexto target-free separado; no usar para rescatar post-hoc P2-A.
- Crypto/contextos: rama `work/crypto-context-foundation-20260824`; no mezclar con esta publicación.
- H-Z2A, HFTZones, GEX, YM, LUX y ZAMR permanecen como historia o líneas aparcadas.

El resto de `docs/research/` es archivo, evidencia o una línea distinta. No se mueve ni se borra sólo para ordenar visualmente.

## Aporte al referente

El índice apunta primero al resultado P2-A efectivamente ejecutado y a su firewall, evitando que el siguiente auditor arranque desde el estado del sweep del 24-ago o confunda mecanismo con estrategia económica.
