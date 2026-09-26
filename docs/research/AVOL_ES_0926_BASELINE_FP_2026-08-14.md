# aVolClusterPOI v0.5 — baseline ES 09-26 (2026-08-14)

**Estado:** `BASELINE_PYTHON_V05_ES_0926`  
**P2:** `ABSTAIN_ALIGNMENT`. El CSV NT8 arranca 1-may; este parquet 8-jun. No es identidad NT8.

Universo (antes de ver el número): todas las OFF_PRICE de Python en la cobertura del parquet.  
Kernel: first-10-seen, FIFO 20, sin clock-trim. Horizonte 2000 M1. Ceros adentro. Empate same-bar. Sin P&L.

Parquet SHA-256 `add9bfcd46b3e8a14b26e6fe90295509dc9444309836f186661850af214146ef`.  
30 509 257 ticks, 66 115 barras, `decode_gaps=[]`. Zonas: 17-jun → 27-jul CT.

## Resultado

| | n |
|---|---|
| OFF_PRICE | 111 |
| Zona gana | 35 |
| Espejo gana | 49 |
| Empate | 27 |
| Decididas | 84 |
| p(zona) | **0.417** |

Binomial bilateral vs 1/2: **p ≈ 0.16**. No hay imán. El signo va **al revés** que 6E.

- LONG: 17–25 (+22 empates)
- SHORT: 18–24 (+5 empates)
- Lag zona p50 = 2 barras

## Pool con 6E (exploratorio, no preregistrado)

62–69 en 131 decididas, p=0.473, binomial ≈0.60. Ruido.

## Qué no autoriza

No P2. No “ES confirma 6E”. No A/B. No QualityScore. No Asia/GEX/L2.
