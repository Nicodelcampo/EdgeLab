# Papel M1 — el largo con régimen (2026-11-15, parcial: falta OTR930 2020→2025-07)
Estado: RESULTADO (EF4 + régimen, enmienda 1: el largo NO da de baja). Código: `edgelab/research/papel_regimen.py`. Datos: `resultados/`,
`LARGO_parcial.json`. Variables de régimen causales (día previo) fijadas antes: vol20, tend60, noche (rango 18:00→09:30 NY), dst.

## ASIA-NQ (regla congelada, canasta por sesión, pts netos)
- Siempre operando: 2012–2019 −0,84; 2020–2023 −1,53; 2024→2025-07 −0,55; 2025-08→2026-09 **+3,16** (8/43 trimestres positivos):
  en 12 años la regla, sin filtro, pierde; vive en lo reciente (consistente con «edge actual»).
- **Régimen: rango nocturno relativo (tercil contra los 250 días previos), dosis-respuesta en los CUATRO tramos y en ticks reales:**
| Tramo | noche baja | noche media | noche alta |
|---|---|---|---|
| 2012–2019 | −1,79 | −1,21 | −0,05 |
| 2020–2023 | −2,61 | −1,39 | −0,44 |
| 2024→2025-07 | −3,39 | −1,62 | **+2,85** |
| 2025-08→2026-09 (M1) | −3,56 | +3,17 | **+7,83** |
| 2025-08→2026-09 (ticks NQ reales) | −3,20 | +3,73 | **+12,93** |
- **Encendido walk-forward** (operar sólo en los estados con media > 0 en los 12 meses previos), 39 trimestres: noche **+646 pts** contra
  siempre −1.544 y estados al azar −264 (**p 0,007**). tend60 p 0,022; vol20 p 0,22; dst p 0,41. Con 16 pruebas de régimen
  registradas, noche sobrevive Bonferroni a nivel ≈ 0,11 y es la única con dosis-respuesta monótona en todos los tramos.
- Lectura: ASIA-NQ es una regla de **noche movida**: con rango nocturno chico pierde siempre; con rango alto gana, y más en los últimos
  dos años. El estado se conoce antes de la apertura (causal, operable).

## OTR930-NQ (sólo 2012–2019 por ahora)
- 2012–2019 −0,82 por sesión (5/32 trimestres positivos); 2025-08→2026-09 +2,53. Encendido: ninguna variable supera al azar
  (noche p 0,15, vol20 p 0,27). Faltan 2020–2023 y 2024→2025-07 (relanzados).
