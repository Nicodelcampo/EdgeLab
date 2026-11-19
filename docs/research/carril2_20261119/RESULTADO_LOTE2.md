# CARRIL2-LOTE2: pico de VIX, P80, eVRP, z-score de compresión, Dynamic Breakout II y rotación ES/GC — 0/12 en BH; dos pistas sin potencia (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO_LOTE2.md` (12 pruebas en `CARRIL2_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS_LOTE2.csv.gz`, `DESC_LOTE2.json`. Motor `sqx_catalogo.simular`
(K28) con camino M1; operaciones con salida en HOLDOUT/EMBARGO descartadas (assert en la herramienta); ninguna definición sin disparos (K53).
REP no se leyó (sin nominadas).

| Regla | Instrumentos | n DESC | R neto | ee | p | R bruto | fricción R | ops/mes | Contraste con control (p) |
|---|---|---|---|---|---|---|---|---|---|
| Pico de VIX (BB 2σ) | ES, NQ, YM | 360 | **+0,136** | 0,065 | 0,018 | +0,150 | 0,013 | 4,1 | +0,091 (0,10) |
| VIX > P80 de 2 años | ES, NQ, YM | 309 | −0,094 | 0,063 | 0,93 | −0,085 | 0,009 | 5,7 | −0,215 (0,99; P10 rinde más) |
| eVRP > 0 y contango | ES, NQ | 323 | +0,066 | 0,057 | 0,13 | +0,080 | 0,013 | 3,6 | +0,025 (0,38) |
| Z-score de compresión < −1 | ES, NQ | 459 | **+0,089** | 0,042 | 0,016 | +0,111 | 0,019 | 4,5 | **+0,120 (0,029)** |
| Dynamic Breakout II | GC, ES, NQ | 193 | −0,368 | 0,103 | 1,00 | −0,346 | 0,022 | 1,9 | +0,077 (0,22) |
| Rotación ES/GC | ES, GC | 68 | +0,080 | 0,129 | 0,27 | +0,091 | 0,011 | 1,0 | +0,149 (0,21) |

- **Ninguna pasa BH q 0,10 entre las 12** (el menor p, 0,016, necesitaba ≤ 0,008). La fricción en R es mínima (≈ 0,01–0,02): como en el
  lote 1, el límite es el ruido de pocas operaciones de varios días, no el costo.
- **MDE (todo nulo publica su potencia):** con ee 0,04–0,13 R, el efecto mínimo detectable al 80 % es ≈ 0,12–0,36 R por operación. Veredicto
  **SIN_EVIDENCIA** para pico de VIX, eVRP, z-score y rotación (no se puede descartar +0,05–0,10 R).
- **Más cerca de refutadas:** VIX > P80 (negativo y peor que su control P10: en DESC la compra en alta volatilidad persistente no paga a 10 días)
  y Dynamic Breakout II (−0,37 R: 2 de cada 3 operaciones salen por stop de 1,5 ATR20 tras rupturas de 2σ que revierten; los cortos en índices
  pierden ≈ −0,7 a −0,95 R; sólo los largos en NQ dan +0,45 R, lo que es selección después de mirar y no se usa). Revisado que no es un error del
  motor (motivos de salida y lados coherentes).
- **Las dos pistas de volatilidad (pico y compresión) van en la misma dirección mecánica** —comprar índice cuando la volatilidad implícita se
  aleja con fuerza de su media corta— y cada una tiene p ≈ 0,02 por separado. No se combinan después de mirar. **Siguiente legítimo:** una
  hipótesis única «reversión de volatilidad implícita» pre-registrada sobre datos no mirados (RTY/EMD con RVX, o el forward), nunca elegida
  sobre este DESC.
