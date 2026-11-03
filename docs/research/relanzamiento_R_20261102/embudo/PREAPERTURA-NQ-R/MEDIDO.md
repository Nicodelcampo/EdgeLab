## PREAPERTURA-NQ-R — edgelab.research.rango_preapertura · señal NQ · ejecución NQ
- Justificación: Ruptura del rango 09:15–09:30 ET en NQ con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626427 pruebas de ['OTR_930_SWEEP_NQ']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- **BLOQUEADA** — la etapa DESC falló 3 veces (error (Kaggle no encuentra el kernel después de la gracia): {"code":404,"message":"No runs found for this kernel."}
)
## PREAPERTURA-NQ-R — edgelab.research.rango_preapertura · señal NQ · ejecución NQ
- Justificación: Ruptura del rango 09:15–09:30 ET en NQ con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 6687580 pruebas de ['OTR_930_SWEEP_NQ']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 192 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 138 (m del FDR 138 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.8903064727783203 (diagnóstico), linaje 6687580 como informacion, pistas sin nominación 28, candidatas 0
- PISTAS a réplica (ATJ-25): 4 congeladas de 28 (k 20), ventana [20260401, 20260930], un paso de LORD++ por lote; celdas [[2, 1, 2, 1, 0, 2], [2, 0, 2, 1, 0, 5], [2, 0, 0, 0, 1, 5], [1, 0, 0, 0, 1, 3]]
- AVISO PISTAS: el resultado se calculó con módulos que cambiaron después (['edgelab/research/grilla_generica.py', 'edgelab/research/etapas.py']); revisar si el cambio toca la medición
- PISTAS canasta (una prueba): media -0.010223543003147588 IC90 [-0.17302429542386033, 0.16540030049825802] p 0.5363659085228693 sesiones 71; LORD++ sin rechazo (nivel 0.0018858947159882456)
- PISTAS réplica [20260401, 20260930]: LORD++ t=4 nivel 0.0011901877202097062 p Simes 0.5297001697152555; confirmadas 0 de 4 []
- **PISTAS_VIVAS** — pistas a réplica: 0 de 4 confirmadas una por una (nivel 0.0011901877202097062, p Simes 0.5297001697152555); canasta media -0.010223543003147588 IC90 [-0.17302429542386033, 0.16540030049825802]; con potencia para 0.5 x el efecto del DESC: la canasta no lo alcanza (IC90 [-0.17302429542386033, 0.16540030049825802]) pero no está en contra; un efecto menor sigue posible: la familia sigue viva; potencia de la canasta 0.8644260751202844
