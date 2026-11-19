# T-NQ: regla de vigilancia para cortar si el régimen 2021+ se termina (prueba 4 de P-97, 2026-11-19)

Estado: VIGENTE — diseño fijado ANTES de operar o seguir T en papel/forward; se aplica desde la primera operación nueva (desde la sesión
del 2026-10-01, frontera A4). Sustento: `RESULTADO.md` (REGIMEN_ROBUSTO). Herramienta: `edgelab/funnel/secuencial.py::EProceso`.

## Regla (R neto por operación de T de fábrica en NQ, riesgo inicial = clip(ORB15 × 1,25, 2, 100))
1. **Corte por drawdown:** si el R acumulado cae **20 R** desde su máximo, T se suspende (peor caída 2021–2026: −9,1 R).
2. **Futilidad (válida mirando cuando sea):** `EProceso(mu0=0,075, piso=−4, techo=+3,5, lado="menor")`; si el e-valor llega a
   **10** (α 0,10), la media dejó de ser ≥ la mitad de la mediana de la grilla y T se suspende. Cotas estructurales: el stop está a 1 R y el
   objetivo de T a 3 R (`baseline_target_r = 3,0`); en 2008–2026 el R observado estuvo en [−1,34, +2,99]. Un valor fuera de [−4, +3,5] (piso bajado de −2 a −4 por la auditoría de Antigravity: el mínimo real 2008–2026 fue −1,47 R y, en la prueba de futilidad, el piso no entra en la apuesta, así que bajarlo no cuesta potencia)
   detiene el monitor con LIMITE_VIOLADO (no se recorta).
3. Suspender no es refutar: se revisa el mecanismo antes de volver.

## Qué esperar (simulado con remuestreo de los R de T)
| Escenario | Corte por −20 R | Futilidad (e ≥ 10) |
|---|---|---|
| El régimen se corta y la media cae a 0 | ≈ 15 meses (mediana) | ≈ 48 meses |
| La media cae a −0,03 (como 2008–2020) | ≈ 10 meses | ≈ 25 meses |
| Sigue en +0,15 (sin cambio) | 10 % de falsa alarma en 5 años | 0 % en 5 años |
- Aplicado a la historia: recorriendo 2008 → la futilidad habría cortado el 2013-07-19 (362 operaciones); recorriendo 2021 → no corta.
- Consecuencia para el tamaño: detectar el fin del régimen lleva ≈ 1 año; el tamaño se elige para que una caída de 20 R sea tolerable en la
  cuenta (en una LucidFlex 25K con DLL de $600 eso es micro, no mini).
