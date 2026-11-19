# TAMANO-K52: con pesos sin sesgo de nivel de precio, el tamaño no mejora RQ5, RQ6, SOM ni Franklin (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (2 pruebas en ROBOQUANT_A5, 1 en SOM, 1 en FRANKLIN). Datos: `OPS.csv.gz`, `DESC.json`.
REP no se leyó (sin nominadas).

| Estrategia | S0 riesgo constante | W1 contratos ∝ 1/ATR20 | W2 intermedio | Mejor − S0 (ee; p) |
|---|---|---|---|---|
| RQ5 (ES+NQ) | −0,0101 | −0,0109 | −0,0105 | −0,0004 (0,0005; 0,81) |
| RQ6 (ES+NQ) | −0,0272 | −0,0278 | −0,0275 | −0,0003 (0,0005; 0,74) |
| SOM (NQ+ES+YM) | −0,0105 | −0,0107 | −0,0102 | +0,0003 (0,0027; 0,46) |
| Franklin (NQ+ES) | +0,0024 | +0,0120 | +0,0089 | +0,0096 (0,0185; 0,30) |

- Ninguna mejora en DESC. Las ganancias de «contrato fijo» que aparecieron antes (FRICCION-RQ §3, NETO-PISTAS §B) desaparecen al normalizar por
  la volatilidad del día en lugar de por puntos crudos: eran el sesgo de nivel de precio que señaló la auditoría de Antigravity (K52), no una
  palanca de tamaño. **El tamaño queda cerrado como palanca para estas cuatro reglas.**
