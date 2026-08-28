# AVOLT — Enmienda de auditoría tras recibir el C# (2026-08-14)

Esta enmienda actualiza `AVOLT_AUDITORIA_DICTAMEN_2026-08-14.md` usando la
fuente primaria que faltaba: `nt8/aVolClusterPOI.cs` v0.5.

## Retiro explícito

**H4 (posible ventana deslizante) queda RETIRADO.** El contrato y el código C#
son inequívocos: `blockBarCount` acumula hasta `WindowBars`, llama
`ProcessBlock()`, limpia `blockCells` y vuelve el contador a cero. Son bloques
disjuntos de 10 barras, reiniciados al comienzo de cada sesión. En ese punto el
runner original coincidía con NT8.

## Hallazgos sustitutos, demostrados por código

- **P2-01 — unidad de lookback incorrecta.** C# guarda `Sample.Session` y poda
  por `minSession`; Python aplanaba scores y limitaba el deque a 20 elementos.
  Con tres bloques por bucket/sesión, Python guardaba ~6–7 sesiones, no 20.
- **P2-02 — primera sesión descartada solo en Python.** `first_roll_done`
  borraba la primera sesión completa; C# la commitea al comenzar la siguiente.
- **P2-03 — bucket off-by-one.** C# usa `barCloseTime.AddSeconds(-1)`; Python no.
- **P2-04 — warmup amputado.** El runner filtró el parquet al inicio de la
  ventana antes de crear el perfil. El oráculo llega a su primera zona en
  `session_index=7`, coherente con historia ya acumulada.
- **P2-05 — asignación de sesión.** Para barras `[start,end)`, usar `end` puede
  mover cierres de frontera a la sesión siguiente; debe usarse `end−1s`.
- **P2-06 — gate incompleto.** No había matching uno-a-uno, no se rechazaban
  zonas Python sobrantes y se usó 99% en vez del 100% preregistrado.
- **P2-07 — orden fail-closed violado.** El runner continuó la carrera formal
  pese a P2 FAIL; esa salida nunca debió producirse.

## Estado de los datos recibidos

Los cuatro 6E entregados son Parquet estructuralmente válidos (`PAR1`) pero
4/4 no coinciden con los hashes preregistrados. No se usan en la formal. Los GC
quedan registrados como candidatos y no se abren hasta pasar schema/P0/P1A.

## Estado resultante

`ABSTAIN_P2` se mantiene. El motivo ahora es más preciso: la prueba ejecutada no
implementó el mismo estado histórico ni el mismo gate que NT8. Se implementó un
replay P2-only v0.1 con tests; falta ejecutarlo en la máquina que conserva el
parquet canónico y PyArrow. Hasta `P2_PASS`, no existe baseline v0.5 medible y
no se prueban filtros v1.0.
