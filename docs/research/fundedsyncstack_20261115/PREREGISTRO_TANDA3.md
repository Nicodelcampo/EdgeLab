# Tanda 3: tamaño por volatilidad pronosticada y salida al cierre en reglas propias (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de correr V1. Pedido de Nico: «dale con los 3» (stops/tamaño por volatilidad pronosticada en datos no
usados; rediseñar rupturas propias con salida al cierre + stop duro; que el forward decida T+Z+R). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Nada mira el holdout. Herramienta `tools/fundedsync_tanda2.py` (subcomandos
`tamano_vol`, `cubos_salida`).

## V1. Tamaño por volatilidad pronosticada (rugosa) contra micros fijos — EF3
- Pronóstico del rango del día (log-rango, modelo rugoso de `PREREGISTRO_TANDA2.md` L4, re-ajuste anual expansivo) del instrumento de ejecución
  (NQ ← M1 Nasdaq, ES ← M1 S&P, YM ← M1 Dow).
- Micros fijos (v2, M3): n = máx(1, round(200 / (riesgo mediano × USD por punto del micro))). Por volatilidad: n_vol = máx(1, round(n ×
  mediana_250(F) / F_día)), con la mediana de los 250 pronósticos previos (causal). Ningún parámetro se ajusta.
- **Datos no usados para esta idea: las reglas del universo de `cartera_20261116/PREREGISTRO.md` que NO están en la cartera v2 y se ejecutan en
  NQ/ES/YM**, desarrollo DESC + REP. (La idea salió del documento de volatilidad rugosa y de FundedSync, no de estas reglas.)
- Estadístico por regla: t de la serie diaria en USD (días con operaciones) con cada tamaño; Δt = t(vol) − t(fijo). **Pasa si Δt > 0 en ≥ 60 % de
  las reglas y la prueba de signo da p < 0,05.** Además: drawdown máximo a igual riesgo medio y USD por día.
- Si pasa: la cartera v2 suma la variante «tamaño por vol» en forward como versión paralela (no reemplaza a la v2 congelada). Contador: 1.
- Stops por volatilidad pronosticada NO se prueban acá: cambiar el stop cambia cada operación y exige re-simular cada regla (queda propuesto).

## V2. Salida al cierre en rupturas propias (descriptivo con los cubos ya medidos; no decide)
- En los cubos de `docs/research/regimen_cubos` (todas las entradas, no la celda elegida): media de R por ejecución, misma entrada y stop,
  objetivo 1R / 2R / SALIDA (cierre), en PREAPERTURA (rango 09:15–09:30 ET) y RANGO0100 (rango nocturno), NQ/ES/YM/GC, DESC y REP.
- Rediseño propuesto con esa evidencia: agregar la ejecución «al cierre» a CVGAP (hoy sólo MID50/MID25/ORIG100) como hipótesis nueva con su
  propio pre-registro y réplica no mirada.

## Justificación económica / cómo podría refutarse
V1: la fricción y el riesgo en USD dependen del rango del día; dimensionar por el rango esperado estabiliza el riesgo y mejora la relación
ganancia/variabilidad. Refutación: Δt ≤ 0 en la mayoría de las reglas no usadas.
