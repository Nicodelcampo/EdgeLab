# Pre-registro: ORB-RR-MENOR — objetivos menores que el riesgo (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar y antes de ver ORB-VARIANTES; pedido de Nico: «probá con RR negativo también»).
Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. EF2 con réplica
congelada. Familia ORB_RR_MENOR, hija de ORB_VARIANTES (hereda 96 + 1.425).

Igual que `PREREGISTRO_VARIANTES.md` (mismo runner, instrumentos, cajas, stops, costos, fills, calendario y ventanas), con dos cambios:
- **Salidas:** objetivo límite a **0,25R, 0,5R o 0,75R** (relación riesgo/beneficio menor que 1: muchas ganadoras chicas), con
  cierre 15:55 si no llega. 54 reglas + 18 canastas = **72 pruebas**; BH q 0,10 con **m = 72 + 96 + 1.425**.
- **Réplica:** sólo las nominadas en DESC (no hay reglas base pre-registradas), con LORD++ reservado (`ORB-RR-MENOR/replica`).

**Justificación económica:** si la ruptura tiene continuación inicial pero no sostenida, capturar un tramo corto podría ganar más
que esperar al cierre. **Cómo podría refutarse:** ninguna nomina, o lo nominado no es positivo en la réplica. Riesgo específico: con
objetivos chicos la fricción pesa más por operación (≈ 0,1 R), y un acierto alto con pérdidas completas suele dar esperanza ≤ 0.
