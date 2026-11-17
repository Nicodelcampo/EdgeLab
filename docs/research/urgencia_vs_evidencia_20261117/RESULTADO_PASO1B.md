# Paso 1b: vida de una ventaja en M1 intradía de índices — resultado (2026-11-17)

Estado: CERRADO — pre-registro `PREREGISTRO_PASO1B.md`. Datos: `M1_VIDA.json` (kernel `edgelab-m1-vida`, 392 series, 8 índices, 2012 →
2026-09), `POTENCIA_PASO1B.json` (calculada sólo con el conteo, commiteada antes del ajuste), `RESULTADO_PASO1B.json`.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Pruebas que deciden (todas con potencia ≥ 0,52 para τ 0,05)
| Grupo (variantes canónicas) | Ops | R neto: τ, ρ [IC], p | R bruto: τ, p | Régimen en neto (BH) | Régimen de mercado |
|---|---|---|---|---|---|
| ORB 30 min, 8 índices | 24.398 | 0,25, 0,999 [0,98–0,999], 0,003 | 0,10, **0,03** | sí | **sí (lento)** |
| Pre-rango 08:12, 8 índices | 21.248 | 0,30, 0,997 [0,97–0,999], 0,003 | 0, 1,00 | sí | no |
| Banda 3 del VWAP, 8 índices | 9.973 | 0,30, 0,999 [0,97–0,999], 0,003 | 0,10, 0,18 | sí | no |
| **Dominio de la cartera** (NQ, ES, YM) | 22.795 | 0,25, 0,999 [0,993–0,999], 0,003 | 0,07, **0,11** | sí | **no** |
| Conjunto canónico (24 series) | 55.619 | 0,25, 0,998 [0,99–0,999], 0,003 | 0,07, 0,13 | sí | no |
Innovaciones estandarizadas: desvío 0,96–1,04 (el modelo describe las series). Las «todas las variantes» por familia son descriptivas
(comparten operaciones: su evidencia está inflada) y van en el mismo sentido.

## Lectura
1. **En el dominio de la cartera no hay régimen de mercado detectable** con potencia (bruto p 0,11). Lo que se mueve es el R **neto**, con
   una deriva muy lenta (ρ ≥ 0,993: vida media de más de 8 años): es la fricción, fija en puntos, pesando distinto en R según la volatilidad.
2. La única deriva de mercado es la del **ORB** (bruto τ 0,10, p 0,03), también lentísima: la ruptura de la apertura cambió a lo largo de
   años, no de meses.
3. Con el paso 1 (catálogo) la conclusión es la misma en los dos dominios: **las ventajas que medimos no se apagan en meses**. Para el
   equilibrio de la propuesta: confirmar en forward antes de escalar no llega tarde; la urgencia como «vida en el tiempo» no tiene sustento
   en los datos. Lo que sí cambia y se conoce antes de operar es la **fricción en R según la volatilidad del momento**: es la variable que
   debe gobernar P(viva) y el tamaño (paso 3), junto con la evidencia acumulada.
4. Alcance: CFD de Dukascopy con spread de Dukascopy (no costos de futuros); reglas canónicas de tres familias, no las ocho reglas de la cartera.
