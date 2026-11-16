# Tanda 3 — resultado (2026-11-16)
Estado: RESULTADO. Pre-registro `PREREGISTRO_TANDA3.md` (commit `6da91ec5`). Datos: `tanda2/T3_V1_TAMANO_VOL.json`, `tanda2/T3_V2_CUBOS_SALIDA.json`.

## V1. Tamaño por volatilidad pronosticada — REFUTADO
12 reglas del universo fuera de la cartera v2 (NQ/ES/YM, desarrollo DESC + REP): el tamaño escalado por el rango pronosticado (rugoso) **empeora
el t diario en 9 de 12** (Δt > 0 sólo en CVGAP-CFD-NQ, CVGAP2-CFD-NQ y PREAPERTURA-ES; prueba de signo p 0,98). U1-RACIMOS-GRILLA-ES baja de t 1,60
a 0,45. Lectura: el stop de cada regla ya sale de la estructura del día, así que medir y dimensionar en R ya normaliza la volatilidad; achicar los
días de volatilidad alta recorta justo donde está la ganancia (las reglas de ruptura viven de los días con movimiento, F-RUPTURA-VIVE-DEL-DIA-DE-
TENDENCIA). La cartera v2 sigue con micros fijos. El pronóstico rugoso sigue siendo un buen pronóstico de volatilidad (tanda 2), pero no mejora el tamaño.

## V2. Salida al cierre en rupturas propias (cubos ya medidos, todas las entradas; descriptivo)
SALIDA (mantener hasta el cierre con el mismo stop) le gana a los objetivos 1R y 2R en, de 4 comparaciones por cubo (stop MID/OPUESTO × DESC/REP):
| Cubo | Rango | SALIDA gana |
|---|---|---|
| PREAPERTURA-NQ | 09:15–09:30 ET (apertura de NY) | **4/4** (p. ej. OPUESTO: +0,23 vs +0,04 en DESC; +0,09 vs −0,05 en REP) |
| PREAPERTURA-ES | ídem | **4/4** |
| PREAPERTURA-YM | ídem | 2/4 (DESC sí, REP no) |
| RANGO0100-NQ | rango nocturno (01:00) | 0/4 |
| RANGO0100-ES | ídem | 0/4 |
| RANGO0100-GC | ídem | 3/4 |
Lectura: **mantener hasta el cierre paga en las rupturas del rango de la apertura de Nueva York** (sesión con información, días de tendencia), igual
que en FundedSync (S, W confirmados en índices no usados), **y no en las rupturas del rango nocturno**. La celda congelada de PREAPERTURA-NQ ya usa
OPUESTO + SALIDA: el diseño «ruptura + stop duro + al cierre» es lo que la hace la mejor de la cartera.
Rediseño propuesto (pre-registro aparte): agregar la ejecución «al cierre» a CVGAP (hoy MID50/MID25/ORIG100) y a las rupturas de la apertura de NY
que no la tienen, con réplica no mirada.
