# Adjudicación independiente de paridad HFT V2 — 2026-09-18

## Dictamen

`46d97e8` implementa el comparador de 38 campos, la persistencia NT8 de `termination_reason`, el reset contractual, la monotonía temporal y el uso fail-closed de `available_ts_ns`. Sin embargo, el oracle histórico fue completado con `tools/patch_hft_v2_oracle_termination.py`, que reconstruye `termination_reason` con el detector Python y lo escribe en SQLite. Ese campo no constituye evidencia independiente NT8 ↔ Python.

Estado defendible del artefacto histórico:

```text
PASS_EXACT_37_FIELDS_PLUS_PYTHON_BACKFILLED_TERMINATION_NOT_FULLY_CERTIFIED
```

La aritmética independiente es `5,438 × 37 = 201,206` comparaciones. Las 5,438 razones de terminación son diagnósticas y no se cuentan como paridad independiente.

## Gate para certificación completa

1. Compilar `nt8/HFTZonesNQPureV4_V2.cs` en NinjaTrader 8.
2. Crear un SQLite V2 vacío; no migrar ni parchear el oracle anterior.
3. Ejecutar un replay limpio del mismo ledger de ticks.
4. Preservar SHA-256 del SQLite inmediatamente al cerrar NT8 y antes de ejecutar Python.
5. Ejecutar el preflight y el comparador en modo read-only.
6. Prohibir cualquier backfill Python en el pipeline de certificación.
7. Publicar conteos por `termination_reason`, hashes de inputs y 206,644 comparaciones exactas.

Solo entonces corresponde `PASS_CERTIFIED_FULL_FIELD_PARITY`.

## Playwright

La suite requiere instalar Chromium de Playwright en CI. El workflow incorpora el paso oficial `python -m playwright install --with-deps chromium`; las pruebas del visor no deben declararse reproducibles hasta que ese job termine verde.
