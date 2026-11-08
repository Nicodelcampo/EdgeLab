# Pre-registro: TRANSFERENCIA-MULTIACTIVO — reglas congeladas en 10 activos (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar; Nico: «Sí, armala»). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3. Familia TRANSFERENCIA_MULTIACTIVO (linaje: las familias
de origen de cada regla).

**Pregunta:** una regla con motivo económico, congelada en su activo de origen, ¿gana también en activos donde nunca se eligió? Cada
activo nuevo es evidencia independiente de la selección, y correr la regla en varios activos multiplica la frecuencia.

**Justificación económica:** las aperturas, la sesión asiática y los gaps de volatilidad son fenómenos de microestructura comunes a
los futuros líquidos; si la regla captura algo real, no debería depender de un solo contrato. **Cómo podría refutarse:** la canasta
de transferencias no es positiva o p ≥ 0,10.

**Reglas congeladas (celda y cortes de origen, sin reajustar; los cortes son relativos: cocientes y múltiplos):**

| Regla | Experimento | Origen | Celda |
|---|---|---|---|
| PREAPERTURA-ES | `rango_preapertura` | ES | [2, 0, 1, 0, 0, 5] (acta del holdout) |
| PREAPERTURA-NQ | `rango_preapertura` | NQ | [2, 0, 0, 0, 1, 5] (acta del holdout) |
| ASIA-NQ | `asia_bos_gaps` | NQ | [1, 1, 0, 2, 3, 3, 3, 2, 2, 8] (CANASTA-GLOBAL-FRECUENTE) |
| ASIA-GC | `asia_bos_gaps` | GC | [1, 1, 0, 2, 3, 0, 2, 2, 0, 5] (ídem) |
| CVGAP-NQ | `corredor_vol_gaps` | NQ | [0, 0, 0, 2, 2, 3, 3, 2, 0, 2, 8] (ídem) |

Las versiones `-C` (confirmador CFD) quedan afuera: no hay CFD equivalente para todos los activos. U1-ZONAS queda afuera: necesita
almacenes de zonas que sólo existen para NQ, ES e YM.

**Activos destino:** NQ, ES, YM, RTY, GC, ZB, 6E, 6B, 6J, MBT (la release; sin micros duplicados), excepto el de origen de cada regla:
45 pares. Costos canónicos de `edgelab/costos.py` (un activo sin costo medido falla y queda fuera, declarado). Período: 05/08/2025 →
30/09/2026 (DESC + réplica), nunca el holdout. Etapa ANALIZAR_REGLA con operaciones, P&L en R.

**Prueba primaria (una sola):** canasta igual ponderada de los 45 pares por sesión (R del día de cada par, 0 si no opera), t diario y
p de una cola por inversión de signo por sesión (B = 10.000). **Pasa si p < 0,10 y la media > 0.** Secundario (descriptivo): por regla,
cuántos activos dan positivo y su canasta. Si pasa: apertura exploratoria del holdout (pre-registro aparte), con la canasta congelada.
