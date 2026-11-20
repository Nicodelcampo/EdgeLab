# Proxy de gamma desde 2006 y el filtro de exclusión: resultado (2026-11-18)

Estado: RESULTADO — **la lectura de 2006–2011 NO se abrió: la guarda K49 la bloqueó (potencia 0,09; harían falta 15.633 días con la
mitad del efecto, ≈ 3.900 con el efecto completo). El filtro de gamma no es confirmable con datos históricos disponibles, ni con
forward en un plazo útil. Los años 2006–2011 quedan sin gastar para otras hipótesis de la familia.**
- **Pre-registro:** `PREREGISTRO.md` (fases 0–2 diseñadas antes de mirar). **Datos:** `FASE0.json` y `FASE1.json`.
- **Herramienta:** `tools/anclaje_proxy.py`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Fase 0 (sin retornos de estrategia): el VIX reproduce a la gamma
| Candidato (cierre previo) | Spearman con `g_rank250` (2011-11 → 2025-07) |
|---|---|
| **Percentil del VIX (252 días)** | **−0,63** |
| VIX contra su media de 20 días | −0,51 |
| Variance ratio intradía (NQ, 20 sesiones) | −0,21 |
| Autocorrelación de 5 min (NQ, 20 sesiones) | −0,06 |

- **Elegido:** «anclaje alto» = percentil del VIX ≤ 24, corte congelado.
- **Lectura:** la gamma alta de los dealers aparece cuando el VIX está bajo en su historia reciente. Los proxies de precio (reversión
  intradía) casi no la capturan.

## Fase 1 (EF2, DESC 2011+, datos ya mirados): el efecto es el mismo que con GEX
- **Canasta T + Franklin + SOM** (R neto por día): anclaje alto − resto = **−0,48 R/día** (EE 0,22).
- **Potencia de la lectura 2006-01 → 2011-10** (1.474 días, mitad del efecto, nivel LORD 0,0109): **0,09**. Hacen falta 15.633 días.
- **Desvío equivalente del contraste:** 9,5 R/día (la canasta suma tres reglas y tres índices). El efecto, aunque grande en promedio,
  es chico frente al ruido diario.

## Fase 2: no se corre (K49)
`a5.exigir_potencia` la rechaza: «potencia 0,09 < 0,8 en días […] seguir explorando en DESC o juntar más N antes de gastar la lectura».

## Conclusión
- **El filtro de gamma (o de VIX bajo) en las reglas de tendencia es consistente** en DESC, en REP + HOLDOUT (GEX) y en DESC con el
  proxy (VIX), pero **no se puede confirmar con potencia**. El ruido diario de la canasta exige décadas de datos.
- **Decisión:** no se usa como filtro operativo ni se busca confirmarlo en forward (también tardaría décadas). Queda como factor de
  contexto descriptivo.
- **Lo que sí sirve para la investigación:** el percentil del VIX como proxy de la gamma desde 2006 (disponible para otras familias, con
  el cuidado de K49).
- **Para que una hipótesis así sea confirmable:** el efecto tiene que medirse sobre una unidad de menos ruido. Por ejemplo, el R por
  operación de UNA regla con muchas operaciones, o la magnitud del día (Spearman parcial 0,23 con GEX). La potencia se calcula antes,
  en días.
