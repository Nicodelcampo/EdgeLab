# Resultado: atlas de contexto en bruto y en neto (04/11/2026)

Estado: VIGENTE — preliminar con 203 de 212 corridas (las 9 restantes no arrancaron en Kaggle por cupo; se actualiza al llegar). Pre-registro:
`PREREGISTRO_BRUTO_NETO.md`. Datos: `RESULTADO.json` (neto), `RESULTADO_BRUTO.json` (bruto, `pnl / riesgo`), `CLASIFICACION.json`.
Mismo meta-análisis DerSimonian-Laird, con grupos (familia, activo) y futuro + CFD juntos.

## La tabla

**Ratio** = efecto bruto / efecto neto, en DESC / réplica. Clase según el pre-registro: CONTEXTO si las dos ratios son ≥ 0,5; FRICCIÓN si
alguna es < 0,25 o cambia de signo; MIXTO en el resto.

| Estrato | Efecto | K | Neto DESC / réplica | Confirmado en neto | Bruto DESC / réplica | Confirmado en bruto | Ratio | **Clase** |
|---|---|---|---|---|---|---|---|---|
| GLOBAL | stop ancho S3 | 13 | +0,121 / +0,105 | sí | +0,020 / +0,018 | no | 0,17 / 0,18 | **FRICCIÓN** |
| GLOBAL | objetivo lejano T3 | 13 | +0,056 / +0,045 | no | +0,010 / +0,012 | no | 0,18 / 0,26 | **FRICCIÓN** |
| GLOBAL | objetivo cercano T1 | 13 | −0,061 / −0,043 | no | −0,012 / −0,010 | no | 0,19 / 0,23 | **FRICCIÓN** |
| GLOBAL | ATR relativo bajo | 63 | −0,105 / −0,068 | sí | −0,013 / −0,008 | no | 0,12 / 0,12 | **FRICCIÓN** |
| GLOBAL | ATR relativo alto | 82 | +0,041 / +0,027 | sí | +0,008 / +0,001 | no | 0,18 / 0,03 | **FRICCIÓN** |
| GLOBAL | volumen relativo bajo | 59 | −0,076 / −0,064 | sí | −0,013 / −0,014 | no | 0,17 / 0,21 | **FRICCIÓN** |
| GLOBAL | volumen relativo alto | 76 | +0,029 / +0,024 | sí | +0,005 / +0,003 | no | 0,16 / 0,14 | **FRICCIÓN** |
| GLOBAL | NY 9:30–12 | 69 | +0,058 / +0,040 | sí | +0,015 / +0,004 | no | 0,26 / 0,10 | **FRICCIÓN** |
| REVERSIÓN | NY 9:30–12 | 45 | +0,082 / +0,050 | sí | +0,026 / +0,006 | no | 0,31 / 0,11 | **FRICCIÓN** |
| REVERSIÓN | **imán** (`veto_muro=vetado`) | 45 | +0,081 / +0,069 | sí | +0,013 / +0,008 | no | 0,16 / 0,11 | **FRICCIÓN** |
| GLOBAL | imán (`veto_muro=vetado`) | 82 | +0,055 / +0,043 | sí | +0,009 / +0,006 | no | 0,16 / 0,15 | **FRICCIÓN** |
| CONTINUACIÓN | huida (`veto_huida=vetado`) | 13 | −0,051 / −0,116 | no | −0,059 / −0,105 | no | 1,14 / 0,90 | **CONTEXTO** |

## Lectura

1. **Todos los efectos «confirmados» del atlas son fricción en R.** En bruto conservan entre el 3 % y el 31 % de su efecto neto y ninguno
   se confirma. ATR y volumen relativos, horario NY, stop ancho, objetivo lejano y el imán: todos marcan, por distintos caminos,
   operaciones con stop grande frente a la fricción fija del instrumento. **No hay contexto de mercado en ellos.**
2. **El imán también es fricción.** Si hay un nivel de sesión entre la entrada y el objetivo, el objetivo y el stop suelen estar lejos, y
   la fricción pesa menos en R. En bruto el efecto se cae a +0,013 / +0,008R. **Se retira como hipótesis de contexto.** La validación desde
   noviembre ya no hace falta como filtro de contexto.
3. **La única que sobrevive en bruto es `veto_huida` en continuación.** Entrar a favor de la tendencia justo después de una huida fuerte en
   contra resta unos −0,05 / −0,11R, igual en bruto que en neto. Tiene K = 13 y no se confirma con BH, así que es una pista viva, no un
   filtro.
4. **La lección que sí vale es económica, no de contexto.** El R neto depende mucho de la relación entre stop y fricción. Pero cortar
   operaciones con stop chico no paga en las 11 reglas (`RESULTADO_PISO_RIESGO_20261104.md`): los stops chicos también traen ganadoras.
   La palanca correcta es **diseñar** reglas con stops naturalmente grandes frente a la fricción, no filtrar después.

## Consecuencias

- **`RESULTADO_CONTEXTO_Y_VETOS_R_20261104.md` (Gemini) pasa a VIGENTE con reservas:** sus efectos confirmados son de costo, no de
  contexto. Lo que sigue en pie de esa entrega es el módulo `contexto_comun.py`, el arreglo de JForex y el método.
- **Desde hoy, todo filtro común se mide también en bruto:** `marginales_globales_bruto` sale gratis en cada corrida. Un filtro que sólo
  mejora en neto es una apuesta sobre la fricción, y ya hay una forma más directa de manejarla.

Aporte al referente: evitamos adoptar 11 «filtros de contexto» que eran fricción disfrazada, el imán incluido, y queda una sola pista de
contexto real (`veto_huida` en continuación).
