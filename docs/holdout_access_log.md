# Log de acceso al holdout (append-only)

> Generado y mantenido por `edgelab/research/holdout_guard.py`. **Append-only**:
> nunca se edita ni se borra una fila existente; una corrección se registra
> como una fila NUEVA con una nota, no reescribiendo la vieja. Ver
> `docs/edge_validation_contract.md` §G4 (firewall del holdout) y
> `docs/NORTH_STAR.md`.

| timestamp_utc | purpose | outcome | window_start_utc | window_end_utc | caller |
|---|---|---|---|---|---|
| 2026-07-24T17:01:40Z | target_free_validation | ALLOWED (retroactivo, ver nota) | 2026-07-13T22:00:00 | 2026-07-16T21:00:00 | manual/retroactive: F4C — validación de paridad geométrica Gaps2 (6E 09-26, commit `0555e5d`, gate P2 PASS 1316/1316) |

> **Nota sobre la fila retroactiva**: este guard no existía cuando se corrió
> la validación de paridad de Gaps2 (F4C). Su ventana (2026-07-13→16) cae
> **dentro** del holdout sellado (2026-07-01→2026-12-31), pero fue un uso
> **target-free permitido**: paridad geométrica NT8↔Python, sin mirar P&L ni
> retornos, sin elegir dirección/thresholds/candidatos — exactamente el uso
> que el firewall autoriza (§G4). Se registra acá con timestamp del commit
> real para que quede trazado, tal como exige el firewall para todo acceso
> `target_free_validation`.
