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

| 2026-07-27T13:34:00Z | target_free_validation | ALLOWED — **apertura NO PLANIFICADA** (ver nota 3) | 2026-07-12T00:00:00 | 2026-07-17T23:59:59 | manual: oráculo `BigTrap2` v2.2 `tick:25` — el chart quedó con el `End date` por defecto en vez del `18/06/2026` pedido, así que la primera corrida cayó en julio |
| 2026-07-27T02:00:00Z | **null_atlas (NO target-free)** | **BREACH — detectado y revertido 2026-07-27T14:05Z** (ver nota 4) | 2026-07-06T00:00:00 | 2026-07-21T23:59:59 | `tools/atlas_excursiones_nulas.py` — el atlas nulo consumió **10 días del holdout** entre sus 163 días efectivos |

> **Nota 4 (BRECHA del atlas nulo, 2026-07-27)**: el atlas mide **MFE/MAE sobre
> horizontes futuros**. Eso es retorno, **no** es `target_free_validation`, y la
> regla sellada dice textualmente *"ningún placebo pisa el holdout"*. La corrida
> de la madrugada del 2026-07-27 (417.661 anclas, 163 días) incluyó **10 días
> del holdout**: 07-06, 07, 08, 09, 13, 14, 15, 16, 20 y 21.
>
> **Causa raíz**: el filtro del holdout existía **sólo en el docstring** del
> atlas. `universe.py` no filtra por fecha (correctamente: el censo debe cubrir
> todo el rango, verificar integridad no gasta nada) y el atlas nunca lo aplicó.
> Ninguna capa era responsable, así que ninguna lo hizo.
>
> **Qué se hizo**: (1) el filtro pasó a ser un candado de **código** dentro de la
> config congelada del atlas (`holdout_desde`), que además **loguea qué días
> descarta**; (2) el atlas contaminado se preservó entero en
> `runs/atlas_CONTAMINADO_holdout_2026-07-27/` como evidencia, **no se borró**;
> (3) el atlas se relanzó desde cero con `config_hash=efeb4a02c5849141`.
>
> **Impacto declarado**: cualquier conclusión sacada del atlas anterior está
> tocada por 10 días de holdout sobre 163 (6,1 %). No se declaró ningún edge a
> partir de él, así que el daño se limita a que **esos 10 días quedaron vistos**
> — el holdout ya no es virgen para el rango 2026-07-06 → 07-21 en lo que hace a
> distribuciones de excursión. Se registra acá para que la próxima apertura
> formal lo tenga en cuenta y no se cuente como primera mirada.

> **Nota 3 (apertura no planificada, 2026-07-27)**: el pedido de paridad estaba
> deliberadamente armado sobre una ventana **pre-holdout** (2026-06-14 → 06-18)
> justamente para no gastar una apertura. Un `End date` que quedó sin cambiar en
> el chart hizo que la primera corrida se ejecutara sobre 2026-07-12 → 07-17.
> **Uso target-free** (paridad de footprint contra el oráculo NT8): no se miró
> P&L ni retornos, no se eligió dirección, threshold ni candidato. Se registra
> igual porque el firewall exige trazar **todo** acceso, y porque una apertura
> por descuido es información sobre el proceso: el error no fue de criterio sino
> de que **el arnés no verifica la ventana del oráculo antes de consumirlo**.
> **Deuda declarada**: que el parser de oráculos falle ruidosamente si el rango
> del CSV no coincide con el rango pre-registrado del pedido.
>
> *(La segunda corrida del mismo CSV, 2026-06-14 → 06-16, es la pre-holdout
> pedida. Las dos quedaron concatenadas en el archivo porque `BigTrap2` v2.2
> appendea; se separan por el reinicio de `seq`.)*

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
| 2026-07-28T00:47:12Z | target_free_validation | ALLOWED | 2026-07-01T00:00:00 | 2026-07-26T23:59:59 | correr_gates:6E_09-26_ticks.parquet |
| 2026-07-29T04:50:11Z | target_free_validation | ALLOWED | 2026-07-12T00:00:00 | 2026-07-13T23:59:59 | manual: lectura **ESTRUCTURAL** del oráculo `BigTrap2` v2.2 `tick:25` (`oracles/BigTrap2_tick25_6E_0926_v22.csv`) — línea `# meta`, histograma de tipos de evento, `seq` y timestamps, para decidir si el oráculo es apto ANTES de correr el matcher. **No se corrió paridad, no se leyeron zonas, geometría, P&L ni outcomes.** Resultado: oráculo **RECHAZADO como insumo** (dos corridas concatenadas — `seq` reinicia 4685→0 — y 4.352 zonas suprimidas por la política de rotura del `.cs` v2.2). La ventana de julio ya estaba registrada en la fila del 2026-07-27 como apertura no planificada; ésta es la lectura posterior de ese mismo archivo |
| 2026-07-31T22:27:06Z | target_free_validation | ALLOWED | 2026-07-01T00:00:00 | 2026-07-26T23:59:59 | correr_gates:6E_09-26_ticks.parquet |
| 2026-07-31T23:46:56Z | target_free_validation | ALLOWED | 2026-07-01T00:00:00 | 2026-07-26T23:59:59 | correr_gates:6E_09-26_ticks.parquet |
| 2026-08-01T00:13:46Z | target_free_validation | ALLOWED | 2026-07-01T00:00:00 | 2026-07-26T23:59:59 | diag |
