# M1 intradía (ORB, pre-rango 08:12, banda del VWAP) — resultado (2026-11-15)
Estado: RESULTADO (EF3). Pre-registro: `PREREGISTRO.md` (+ enmienda 1). Datos: `RESULTADO.json` (Kaggle `edgelab-m1-intradia`, 441
variantes, 8 índices M1 2012 → 2026-09, 30 réplicas del nulo intradía). Umbral p95 del máximo t neto DESC del nulo = **1,40** (bajo: en el
nulo los costos dejan todo negativo).

## Veredicto: ninguna pista por la regla pre-registrada (t neto DESC > 1,40 y R neto > 0 en OOS y RECIENTE)
- **Costos**: en CFD los stops intradía son chicos y el spread pesa 0,1–0,4 R en S&P/Nasdaq/Dow y > 1 R en Euro Stoxx, FTSE, Nikkei y
  Russell (el spread de Russell, 5 puntos ≈ 25 pb, parece mal convertido como los de plata e índice dólar: revisar). Las canastas netas
  quedan entre −0,15 y −1,3 R, dominadas por esos índices caros. Por eso se lee el BRUTO.
- **ORB** (la pista F-ORB-EMA20-NQ): bruto ≈ 0 o negativo en los cuatro tramos (canastas −0,02 a −0,15 R en DESC). OPUESTO −0,031 vs MITAD
  −0,051 en bruto: la diferencia es chica y ambas negativas → la «ventaja del stop opuesto» era fricción/ruido, no señal. Refutada con
  potencia (≈ 20 mil operaciones por variante).
- **Pre-rango 08:12** (H-SWEEP-1): bruto −0,03 / +0,02 / +0,04 / −0,02 (DESC/OOS/RECIENTE/PSEUDO), n 1.800–7.900: ≈ 0. Doble toque
  después del primer extremo ≈ 63 % de las sesiones (información sin ventaja operable en esta forma).
- **Banda 3 del VWAP, reversión** (EL-VWAP-BANDA3): dosis-respuesta en BRUTO frente a la banda 2 en DESC (objetivo VWAP, stop extremo:
  +0,161 vs +0,085; t 4,5) y en PSEUDO (+0,16 a +0,24 vs +0,01 a +0,09), pero **negativa en 2020–2023 (−0,03 a −0,06) y ≈ 0 en
  2024→2025-07**: comportamiento de régimen. Por índice, en PSEUDO neto: Nasdaq +0,13, Dow +0,11, DAX +0,14; S&P −0,05. En DESC neto
  todos negativos (costos). Continuación: ≈ 0.

## Qué queda
- VWAP banda 3 reversión: candidata de RÉGIMEN (no pista): funcionó 2012–2019 y 2025-08 → 2026-09, no en 2020 → 2025-07. Siguiente:
  mapa de régimen por sesión (como ASIA: rango nocturno, vol20, tendencia) — requiere re-correr guardando operaciones por día — y
  medirla en futuros reales (NQ/YM) donde el costo por R es menor.
- ORB y pre-rango 08:12: no repetir en esta forma.
