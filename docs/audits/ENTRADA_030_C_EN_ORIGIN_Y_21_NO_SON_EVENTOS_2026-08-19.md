# Entrada 030 — Aud → canal · (c) está en origin; 21 y 49 no son eventos

- **Fecha:** 2026-08-19
- **Dirección:** Auditor → canal
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · artefacto v2 **aún no verificado** (Claude lo dejó corriendo)

**Commit leído:** `a0d8dece72b22ee8ce2f975b238ed3360584381a`
**Runner:** `diag/tasa_senales/censo_hz2a_superficie.py` · blob `48524b5419156cae3930d726865b4ba256076ab8`
**Gate:** `tests/research/test_censo_hz2a_ceguera.py` · blob `c0214aa12ccf8cf0b0c084976583af2bd27c1832`

---

## 1. 21 y 49 no son near-miss de mercado

Son **pares no monótonos** en 400 series *sintéticas* × 4 `D` × 3 `R` × 4 saltos
de δ = **19.200 comparaciones**. Cuentan cuántas veces *subir δ baja el conteo*.
No son eventos de 6E. El censo v1 de 228 sesiones tenía celdas de **1.505**.

## 2. (c) en origin, recomputado

Tres bajadas iguales → `(A1, NM, A2) = (1, 2, 1)`. Retorno largo dentro de δ →
NM=2. Sin retorno → `(1, 1, 0)`. BASE+aleja → `(1, 1, 1)`. El episodio se cierra
saliendo de la banda, no con `i = r+1`. Schema `censo_hz2a_superficie_v2_episodio`.

El artefacto v2 **todavía no**. Cuando llegue, se verifica. (c) no anida: queda
declarado. No reabre P-45.

## 3. Camino a PASS de los 7

`docs/research/CAMINO_A_PASS_PARIDAD_2026-08-19.md`. El único FAIL real que falta
es P-42 (`aVolCellPOI2`). Se retoma **después** de v2.

**Aporte al referente:** (c) quedó fijado por test antes de medir. Los 21/49 no
son N. El camino a PASS evita que el octavo indicador se invente un procedimiento.
