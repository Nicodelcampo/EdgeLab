# Log de acceso al holdout (append-only)

> Generado y mantenido por `edgelab/research/holdout_guard.py`. **Append-only**:
> nunca se edita ni se borra una fila existente; una corrección se registra
> como una fila NUEVA con una nota, no reescribiendo la vieja. Ver
> `docs/edge_validation_contract.md` §G4 (firewall del holdout) y
> `docs/NORTH_STAR.md`.

| timestamp_utc | purpose | outcome | window_start_utc | window_end_utc | caller |
|---|---|---|---|---|---|
| 2026-07-24T17:01:40Z | target_free_validation | ALLOWED (retroactivo, ver nota) | 2026-07-13T22:00:00 | 2026-07-16T21:00:00 | manual/retroactive: F4C — validación de paridad geométrica Gaps2 (6E 09-26, commit `0555e5d`, gate P2 PASS 1316/1316) |
| 2026-07-24T22:10:00Z | target_free_validation | ALLOWED (retroactivo, ver nota 2) | 2026-07-13T22:00:00 | 2026-07-16T21:00:00 | manual/retroactive: paridad BigTrap2 **O4** (`tick:25`, 6E 09-26, commit `99b947c`) — gate P2 **FAIL**, causa raíz: footprint de NT8 corrupto en charts de tick (89,12 % de las barras) |
| 2026-07-25T00:30:00Z | target_free_validation | ALLOWED (retroactivo, ver nota 2) | 2026-07-13T22:00:00 | 2026-07-16T21:00:00 | manual/retroactive: paridad BigTrap2 **O1** (`time:1`, 6E 09-26, commit `53ee9ff`) — gate P2 **FAIL**, causa raíz: artefacto de 1 ULP en `BigTrap2.cs` L349 |

> **Nota 2 (BigTrap2, agregada 2026-07-25)**: las dos corridas del matcher de
> BigTrap2 usan la misma ventana pre-registrada en el contrato de paridad §7, que
> cae **dentro** del holdout sellado. Son `target_free_validation`: comparan
> geometría, ciclo de vida y footprint contra el oráculo NT8. **No se miró P&L ni
> retornos, ni se eligió dirección, threshold ni candidato.** Se registran
> retroactivamente porque el guard sólo se invoca automáticamente desde
> `sim.simulate` y `camp001_dryrun`; el matcher de paridad todavía no lo llama.
> **Deuda declarada**: cablear `check_holdout(purpose="target_free_validation")`
> dentro del propio matcher para que el registro deje de ser manual.
>
> **Nota sobre la fila retroactiva**: este guard no existía cuando se corrió
> la validación de paridad de Gaps2 (F4C). Su ventana (2026-07-13→16) cae
> **dentro** del holdout sellado (2026-07-01→2026-12-31), pero fue un uso
> **target-free permitido**: paridad geométrica NT8↔Python, sin mirar P&L ni
> retornos, sin elegir dirección/thresholds/candidatos — exactamente el uso
> que el firewall autoriza (§G4). Se registra acá con timestamp del commit
> real para que quede trazado, tal como exige el firewall para todo acceso
> `target_free_validation`.
