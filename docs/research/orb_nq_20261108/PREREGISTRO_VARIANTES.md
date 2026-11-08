# Pre-registro: ORB-VARIANTES — salidas, stops y diversificación entre NQ, ES e YM (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar; pedido de Nico: «variantes, filtros, distintos RR, diversificación»). Referente
`docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2** (DESC) con
réplica congelada en la misma corrida. Familia ORB_VARIANTES, hija de ORB_NQ_FILTROS (que hereda ORB_HORARIOS y ORB0100).

**Pregunta:** ¿la ORB sin filtro (positiva pero no significativa en NQ: +0,11 a +0,20 R/op) mejora con otras salidas o stops, y
diversificada entre índices? **Justificación económica:** la apertura concentra información y órdenes en los tres índices; si la
ruptura tiene continuación, debería verse en los tres, y una canasta reduce la varianza sin elegir. **Cómo podría refutarse:**
ninguna regla ni canasta nomina por FDR en DESC, o lo congelado no es positivo en la réplica.

**Reglas (runner `patches_for_review/orb_nq_20261108/medir_variantes.py`, mismo calendario, noticias, fills y costos que
ORB-NQ-FILTROS):**
- Instrumento NQ / ES / YM (tick y USD por tick de `edgelab/costos.py`; comisión 5,76 USD por viaje; bid/ask + 1 tick por pata,
  2 en el adverso).
- Caja 5 / 15 / 30 min; primera vela M1 que cierra fuera; entrada a mercado en el tick siguiente.
- Stop: extremo opuesto de la caja (O) o mitad de la caja (M), disparado por last.
- Salida: cierre 15:55 ET (C), u objetivo límite a 1R, 2R o 3R (se llena si el last lo atraviesa; si no, cierre 15:55).
- Sin filtros de día, hora ni ATR (no nominaron en ORB-NQ-FILTROS).
- 72 reglas + 24 canastas (cada variante, igual ponderada por sesión entre los tres instrumentos) = **96 pruebas**.

**Decisión:**
- DESC 05/08/2025 → 31/03/2026: p por inversión de signo por sesión; nominación BH q 0,10 con **m = 96 + 1.425 heredadas**.
- Se congelan (se escriben a disco ANTES de leer la réplica) las nominadas **y las 3 ORB base de NQ (O, C)**, pre-registradas acá.
- Réplica 01/04 → 30/09/2026 sólo para lo congelado: una regla congelada CONFIRMA si su media en la réplica es > 0 con p ≤ 0,05
  (una cola); con más de una, Holm sobre las congeladas. Nada se promueve sin holdout a N fijo.
- Sin holdout: el lector corta en la frontera (01/10/2026).

**Riesgos:** pocas operaciones por regla (≈ 130 en DESC, ≈ 100 en réplica): la potencia contra efectos de 0,1 R es baja; el MDE se
reporta. El objetivo límite no modela la cola de la orden (se exige atravesar el precio). Selección retrospectiva por datos completos
de la sesión (heredada, declarada).
