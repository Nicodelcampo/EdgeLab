# Resultado: ORB-NQ-FILTROS auditado (08/11/2026)

Estado: RESULTADO EXPLORATORIO (manifiesto `docs/research/ORB_NQ_FILTROS_MANIFIESTO_20261108.md` con la enmienda de auditoría). Kernel
`nicolasbuttaro/orb-nq-filtros-auditado-20261108`, DESC 05/08/2025 → 31/03/2026, sin holdout. Datos: `ORB_NQ_RESULTADOS_EXPLORATORIOS.json`.

**Reproducción independiente:** mismos números que la corrida del otro agente (5 min 129 ops +0,197 R; 30 min × ATR bajo 58 ops
+0,278 R, p maxT 0,419). El runner es determinista y las dos corridas coinciden.

| Canal | Operaciones | Evaluables | Nominadas FDR q 0,10 (m = evaluables + 705 heredadas) | Nominadas maxT |
|---|---|---|---|---|
| Total (ago-25 → mar-26) | 409 | 30 | **0** | 0 |
| Reciente (ene → mar-26) | 154 | 8 | **0** | 0 |

Sin filtros (una señal por caja y sesión), R neto por operación, base / adverso, p marginal:

| Caja | Total | Reciente |
|---|---|---|
| 5 min | 129 ops · +0,197 / +0,189 · p 0,11 | 48 · +0,264 · p 0,16 |
| 15 min | 133 · +0,127 / +0,122 · p 0,10 | 50 · +0,260 · p 0,06 |
| 30 min | 147 · +0,114 / +0,110 · p 0,09 | 56 · +0,057 · p 0,30 |

**Lectura:** ningún filtro nomina. Las tres ORB SIN filtro son positivas en las dos ventanas y resisten el escenario de costo adverso,
pero cada una está lejos de la significancia (p ≈ 0,1). Como no salen de elegir entre cientos de celdas, la maldición del ganador las
afecta mucho menos que a las pistas de las grillas.

**Siguiente paso (propuesto, requiere pre-registro):** réplica de las TRES ORB sin filtro (5/15/30, reglas congeladas) en abr–sep 2026,
una prueba con LORD++ y potencia declarada. Nada se promueve desde acá.
