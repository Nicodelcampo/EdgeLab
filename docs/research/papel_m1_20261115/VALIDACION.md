# Papel M1: validación de la fuente, v3 (2026-11-18)

Estado: RESULTADO. Reemplaza a la v2 de la misma fecha, que comparaba agregaciones distintas (K47); la v1 está en
`descartada_v1/VALIDACION.md`.
- **Veredicto por código:** `python tools/papel_m1.py validacion [SENSOR]` → `VALIDACION.json` (CFD) y `VALIDACION_FUTM1NT8_NQ.json`
  (futuros M1 de NT8).
- **Criterio único:** `a5.calibrar_por_sesion` (≥ 30 sesiones comunes, mismo signo, diferencia ≤ 1 EE combinado, corr > 0,5).
- **Agregación:** la de la ficha, `cartera.papel.canasta_por_sesion` (suma de las celdas / número de celdas).
- **Tramo:** ago-2025 → sep-2026, contra la serie en ticks reales de NQ de cada ficha (`ops_desarrollo`).

| Regla | Fuente | M1 (pts/sesión) | Ticks NQ | Sesiones comunes | Corr | Veredicto |
|---|---|---|---|---|---|---|
| ASIA-NQ | CFD USATECH (M1DK) | +3,16 | +4,96 | 214 | 0,86 | **CALIBRA** |
| ASIA-NQ | futuros NQ (M1NT8) | +5,32 | +5,20 | 245 | 0,985 | **CALIBRA** |
| OTR930-NQ | CFD USATECH (M1DK) | +3,70 | +6,27 | 214 | 0,88 | **CALIBRA** |
| TORI-NQ | CFD USATECH (M1DK) | −0,62 | +6,04 | 34 | 0,65 | NO (cobertura) |
| RANGO0100-NQ | CFD USATECH (M1DK) | +2,09 | +11,79 | 18 | 0,95 | NO (cobertura) |

## Qué pasó (K47): el motor M1 no estaba mal; la comparación sí
- **El síntoma:** la v1 y la primera v2 dijeron que en ASIA «M1 duplica a los ticks».
- **Lo que se buscó:** para encontrar la causa en el motor se corrió ASIA en ticks reales de NQ (Kaggle) y en futuros M1 de NT8
  (local), y se compararon operación por operación. Coinciden:
  - 1.804 operaciones en común, con la mediana de la diferencia en 0;
  - +14,16 contra +14,27 puntos netos por operación.
- **La causa:** la serie de la ficha agrega con `canasta_por_sesion` (suma / 20 celdas, y las que no operan cuentan 0). La validación
  promediaba sólo las celdas que operan. Con la misma agregación, la serie en ticks reproduce la de la ficha exactamente (corr 1,000)
  y M1 calibra.
- **Guardas:**
  - `papel_m1.validacion` usa `canasta_por_sesion`;
  - `test_validacion_de_papel_usa_la_agregacion_de_la_ficha` lo exige;
  - el criterio es único (K43).

## Consecuencias
- **ASIA-NQ es medible en M1**, en el CFD y sobre todo en futuros NT8 (corr 0,985). Su largo se puede medir. Ver
  `docs/research/asia_noche_20261118/` para la «noche movida», que además tenía una fuga propia (K48).
- **OTR930-NQ** sigue validada; su largo no cambia (`LARGO_V2.md`).
- **TORI-NQ y RANGO0100-NQ** siguen sin medirse en M1. El motivo es cobertura: M1 genera operaciones en otras sesiones. No es la
  agregación.
