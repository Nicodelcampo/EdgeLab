# Papel M1 — el largo con régimen, v2 con el motor corregido (K40) (2026-11-18)

Estado: RESULTADO — reemplaza a `LARGO.md` (v1, DESCARTADA por K40).
- **Pre-registro:** `PREREGISTRO.md` con la enmienda 1: el largo NO da de baja; mapa y encendido por régimen.
- **Datos:** `LARGO_v2.json` y `resultados/OTR930-NQ-CANASTA_*.json`.
- **Código:** el mismo cálculo que la v1 (`edgelab/research/papel_regimen.py`, `cartera.papel.canasta_por_sesion`; variables causales
  del día previo: vol20, tend60, noche y dst).
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Sólo OTR930-NQ.** Es la única que pasa la validación v2 (`VALIDACION.md`, criterio `a5.calibrar_por_sesion`). ASIA-NQ, TORI-NQ y
RANGO0100-NQ no se miden en M1.

## OTR930-NQ (canasta por sesión, puntos netos, M1 USATECH)
| Tramo | Sesiones | Media (ee) |
|---|---|---|
| 2012–2019 | 1.433 | −0,82 (0,11) |
| 2020–2023 | 833 | −1,00 (0,53) |
| 2024 → 2025-07 | 324 | −3,01 (1,11) |
| 2025-08 → 2026-09 (validación) | 243 | +3,86 (2,05) |

- **Trimestres positivos:** 12 de 54.
- **Mapa de régimen:** negativo en todos los estados de las cuatro variables. Ninguna ordena el resultado; la noche alta es la peor
  (−1,43).
- **Encendido walk-forward** (50 trimestres) contra estados al azar: vol20 p 0,93; tend60 p 0,94; noche p 0,41; dst p 0,95. **Sin
  régimen detectable.**
- **Lectura:** igual que la v1. La regla pierde en 12 años y vive sólo en el último. No hay un estado observable antes de operar que la
  separe. Por el principio de edges actuales no se da de baja, pero no tiene respaldo histórico ni filtro: la decide el forward.
- **M1 es optimista frente a ticks en esta regla** (validación: +10,4 contra +6,3 por sesión en el tramo común). Lo histórico negativo
  no es un artefacto pesimista.

## ASIA-NQ: la pista de la «noche movida» pierde su respaldo de 12 años
- **Por qué:** el largo v1 de ASIA (dosis-respuesta por rango nocturno en 4 tramos; encendido p 0,007) se midió con el motor sesgado y,
  además, ASIA no pasa la validación de la fuente en la v2 (M1 duplica a los ticks, 1,28 EE).
- **Qué queda:** sólo lo medido en ticks reales de NQ (ago-2025 → sep-2026: −3,2 / +3,7 / +12,9 puntos por sesión según la noche).
  Es el tramo de desarrollo: genera la hipótesis, no la confirma.
- **Siguiente:** confirmarla en datos no usados. Sirven el forward, o la noche medida en ticks largos cuando existan.
