# AVCL-RACIMO — zonas agrupadas en tiempo y espacio — resultados MNQ — 2026-10-06

Manifiesto: `AVCL_RACIMO_MANIFIESTO_20261006.md`. JSON: `avcl_racimo_20261006/AVCL_RACIMO_RESULTADOS.json`.
- 50t: 33.794 zonas, 5.140 en racimo (principal), 815 densas, 10.734 aisladas.
- 25t: 67.916 zonas, 14.873 / 2.506 / 15.447.

## Formal (50t, racimo `burst ≥ 3` contra aislada, Holm 8)
| prueba | AT | OFF |
|---|---|---|
| `y_pre` H10 | +0,019 (Holm 0,50) | +0,016 (0,46) |
| `y_pre` H50 | **−0,063** (Holm < 1e-4) | **−0,058** (< 1e-4) |
| cola sin signo H10 | 0,000 (0,99) | +0,015 (0,46) |
| `s` = lado × asim H10 | — | −0,016 (0,60) |
| `s` H50 | — | **−0,039** (Holm **0,054**) |

## Réplica en 25t (descriptivo; paridad no validada en 25t)
- `y_pre` H50: AT −0,061, OFF −0,042 (p ≈ 0).
- **`s` H10 −0,029 (p 0,004), `s` H50 −0,057 (p 5e-9)**.
- Criterio denso: `s` H50 −0,048; `y_pre` H50 −0,12 / −0,13.

## Lectura
1. **Después de un racimo hay MENOS rango que antes de que el racimo empezara** (H50, −0,06; el racimo denso,
   −0,12), robusto en las dos escalas y creciendo con el apilamiento. Esta métrica usa el pasado **anterior** al primer
   miembro, así que no es el artefacto de AVCL-PRE. La lectura natural: **el racimo marca una fase de consolidación que
   continúa**, no una ruptura inminente.
2. **Dirección: en un racimo, el precio tiende a VOLVER sobre la zona** (s < 0: hacia el lado de la zona o a través de
   ella), no a rechazarla.
   - 50t H50: −0,039 (Holm 0,054, borde).
   - 25t: −0,029 / −0,057, con una muestra 3 veces mayor y p muy chicos.
   - Coincide con la asimetría de regreso en alta anomalía (AVCL-CIERRE) y con las capturas de Nico (resistencias
     apiladas que terminan atravesadas).
   - Tamaño: −0,04 a −0,06 de asim ≈ acertar el lado un 52–53 % de las veces.
3. Sin efecto en la expansión a H10 ni en la cola.

## Estado
- `RACIMO → CONSOLIDACIÓN POSTERIOR: establecido (MNQ, 2 escalas)`.
- `RACIMO OFF → REGRESO/RUPTURA: candidato fuerte`: no pasa Holm por poco en 50t, pero replica en 25t.
- Siguiente correcto: **prueba única pre-registrada en otros instrumentos** (ES, YM, RTY, MGC), como VTD-VELA, con el
  signo fijado (s < 0) y H50.
