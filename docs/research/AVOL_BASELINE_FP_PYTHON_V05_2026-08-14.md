# aVolClusterPOI v0.5 — baseline primer pasaje vs espejo (2026-08-14)

**Estado:** `BASELINE_PYTHON_V05`  
**P2:** sigue `ABSTAIN_P2`. Esto **no** es identidad NT8.  
**Universo (decidido antes de ver el número):** las 53 `OFF_PRICE` de Python, no las 50 matcheadas.

Kernel: first-10-seen, FIFO 20 sesiones, sin clock-trim.  
Parquet: `6E_09-26` `6ffcdf04…`. Ventana de creación: 8-jun → 1-jul CT.  
Horizonte: 2000 barras M1. Ceros adentro cuentan. Toque doble en la misma barra = empate. Sin P&L.

## Resultado

| | n |
|---|---|
| Zonas OFF_PRICE | 53 |
| Zona gana | 27 |
| Espejo gana | 20 |
| Empate | 6 |
| Sin toque | 0 |
| Decididas | 47 |
| p(zona) | **0.574** |

Binomial bilateral vs 1/2: **p ≈ 0.38**. No hay evidencia de imán.

Por lado (dir +1 = precio arriba de la zona / LONG; −1 = SHORT):

- LONG: 14–7 (+3 empates). n=21. No se interpreta.
- SHORT: 13–13 (+3 empates).

Lag a toque de zona: p50 **2** barras (min 1, max 73). 21 de 53 tocan en la misma o la siguiente.

## Qué no autoriza

No P2_PASS. No mejora A/B. No QualityScore. No “el 57% es edge”.  
MDE con n=47 es enorme. Para mejorar el indicador hace falta más n (otros contratos, mismo protocolo) **o** una mejora preregistrada sabiendo que esta ventana casi no ve efectos chicos.
