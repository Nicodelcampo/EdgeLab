# Papel M1 — el largo con régimen (2026-11-15)
Estado: DESCARTADA (2026-11-18, K40) — mismo motor sesgado que VALIDACION; se relanza. Antes:  RESULTADO (EF4 + régimen, enmienda 1: el largo NO da de baja). Código: `edgelab/research/papel_regimen.py`. Datos: `resultados/`,
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

## OTR930-NQ (completo)
- Siempre: 2012–2019 −0,82; 2020–2023 −1,80; 2024→2025-07 −3,01; 2025-08→2026-09 +2,53. Ninguna variable de régimen ordena el
  resultado (la noche movida incluso empeora antes de 2025) y ningún encendido supera al azar (p 0,63–0,71). **Sin régimen detectable**:
  vive sólo en el último año. Por el principio de edges actuales no se da de baja, pero queda sin respaldo histórico ni filtro.

## Otros mercados: ASIA-NQ congelada en S&P y Dow (2012 → 2026-09; `LARGO_otros.json`)
| Mercado | 2012–2019 (baja / media / alta noche) | 2020–2023 | 2024→2025-07 | 2025-08→2026-09 | Encendido por noche |
|---|---|---|---|---|---|
| Dow | −3,86 / −1,80 / −1,78 | −6,11 / −5,20 / −1,35 | −6,44 / −4,33 / +0,50 | −8,24 / −3,41 / **+7,63** | **+345 vs −7.145 siempre, −863 azar (p 0,007)** |
| S&P | −0,47 / −0,51 / −0,18 | −0,60 / −0,68 / −0,13 | −0,64 / −1,24 / −0,37 | −1,05 / +0,21 / +0,54 | −71 vs −1.049, −117 azar (p 0,23) |
- **El régimen de noche movida se repite en el Dow** con la misma forma (baja < alta en los 4 tramos, alta positiva en lo reciente) y
  el mismo encendido walk-forward (p 0,007). En el S&P el orden se insinúa pero los valores son chicos: los cortes de la regla están en
  puntos de NQ y el S&P se mueve ~1/4 (las celdas no son equivalentes); no cuenta ni a favor ni en contra.
- Lectura: el mecanismo (rupturas y gaps de la sesión asiática necesitan una noche con recorrido) es de mercado, no del NQ.

## ASIA-NQ congelada sobre ticks REALES de YM (ago-2025 → sep-2026; enmienda 3)
241 sesiones, media +0,65 pts. Por tercil de rango nocturno (Dow CFD, causal): **baja −8,44 (ee 1,75; n 78), media −4,34 (ee 2,17; n 86),
alta +15,44 (ee 4,51; n 77)**. La dosis-respuesta se repite en el futuro real de un segundo índice: con noche alta gana, con noche
baja o media pierde. (Desarrollo, no holdout; el filtro se eligió con NQ, así que YM es un mercado no usado para elegirlo.)

## OTR930-NQ congelada en el Dow M1 (2012 → 2026-09)
Negativa en los cuatro tramos (−2,83 / −4,29 / −0,99 / −5,19 pts por sesión); ningún tercil de noche ordena el resultado; encendido:
tend60 p 0,008 (1 de 4, sin dosis), el resto p 0,16–0,38. OTR930 no se sostiene fuera del Nasdaq ni tiene régimen.
