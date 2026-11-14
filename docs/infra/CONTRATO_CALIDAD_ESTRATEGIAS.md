# Contrato de calidad: cuándo una estrategia «vale la pena»

Estado: VIGENTE (2026-11-14, pedido de Nico). Código: `edgelab/research/sqx_calidad.py` (`REQ`, `evaluar`); tests
`tests/research/test_sqx_calidad.py`. Rige para la línea SQX/MT5 y para cualquier estrategia que pretenda pasar a cartera o a una cuenta.
Los umbrales se fijaron antes de ver resultados; cambiarlos es decisión humana registrada.

## Por qué (repaso del proyecto al 2026-11-14)
- 0 edges promovidos. Lo que murió, murió por SELECCIÓN, no por costos (80 pistas: ≈ +0,20 R en bruto donde se eligieron, ≈ 0 en la
  réplica; FRICCIÓN 0 — `docs/research/bruto_neto_pistas_20261108/RESULTADO.md`). Patrones de DeltaSweep (≈ 79.000 celdas) y
  LUXIMB-AMARILLA: el mismo patrón; lo elegido entre miles cae a ≈ 0.
- Efectos de contexto «confirmados» eran fricción (F-ATLAS-CONTEXTO-ES-FRICCION); el stop grande frente a la fricción es una palanca
  de diseño, no una señal.
- Las reglas de alta tasa de acierto con stop lejano (caja amarilla obj 50 %) ganan poco y pierden mucho: su riesgo está en la cola.

## Requisitos (todos; lo que falta deja la estrategia PENDIENTE, nunca aprobada por omisión)
| # | Requisito | Umbral | Por qué |
|---|---|---|---|
| 1 | R neto medio (spread, comisión y swap incluidos) | ≥ +0,10 R | margen para pagar el desafío y el error de estimación |
| 2 | Supera al nulo de la búsqueda | t > p95 del máximo t del mismo Builder sobre la serie sintética (`tools/sqx_nulo.py`) | la selección es lo que mató todo hasta hoy |
| 3 | Potencia | ≥ 200 operaciones | con menos, el error de la media en R es ≥ 0,1 |
| 4 | Frecuencia | 12–400 operaciones por año | macro pero operable; el techo evita scalping disfrazado |
| 5 | Estabilidad | ≥ 4 de 5 bloques cronológicos con R > 0 | regla global de evidencia (DECISIONES_20261108) |
| 6 | Reciente sin usar (2024-01 → 2025-07, una vez) | R > 0 | «edges actuales» |
| 7 | Otros mercados de su clase, sin re-optimizar | ≥ 60 % con R > 0 | el edge es del mecanismo, no de una serie |
| 8 | Drawdown máximo | ≤ 20 R | entra en las reglas de las props con 0,5 % por operación |
| 9 | Racha perdedora | ≤ 12 | supervivencia en la cuenta |
| 10 | Concentración | las 5 mejores ≤ 50 % del resultado | no depende de outliers |
| 11 | Correlación con la cartera (P&L diario) | ≤ 0,3 | diversificación real |
| 12 | Diversificación | ≤ 2 estrategias por (idea, activo) | no repetir la misma apuesta |
| 13 | Diseño (antes de correr, `tools/sqx_corrida.py`) | ≤ 3 condiciones; SL 2–5 ATR, TP 2–8 ATR; generación aleatoria; datos ≤ 2026-09-29 | menos grados de libertad; fricción baja en R |
| 14 | Después: paridad MT5 y demo forward | trades del EA = trades de SQX; forward secuencial sin alarma | ejecutabilidad real |
| 15a | Gaps (domingo, noticias), con llenado realista en SQX (`RealisticGapsHandling`) | peor operación ≥ −3 R; lo perdido más allá de −1 R ≤ 30 % del resultado | que el resultado no dependa de que el gap no te agarre |
| 15 | Cuenta | esperanza del desafío > 0 con sus reglas reales (`edgelab/propfirm/`) | el referente es cobrar |

## Qué NO es evidencia
Profit factor, Sharpe o «Return/DD» del Builder sobre los datos donde se eligió; el OOS interno de SQX que se miró para elegir; un
backtest sin el total generado contado.
