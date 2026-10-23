# AREAS-EXP-1 (áreas de zonas LUX-IMB) — qué está medido y qué NO (registro vivo, desde 2026-10-22)

Estado: VIGENTE — `SIN EFECTO DETECTADO` en el tamiz v1.3; v1.4 (Romano-Wolf + canal reciente + pistas a réplica) en curso.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia independiente (no transporta resultados, costos ni multiplicidad de BigTrap2, HFTZones, aVolCluster, ESPEJO ni YM-PRERANGE).
Spec: `SPEC_AREAS_EXPANSION_V1.md` (v1.3). Manifiesto y resultados: `MANIFIESTO_DESC_AREAS_EXP_1.md`.

## Medido
| qué | datos | resultado | alcance exacto de la muerte |
|---|---|---|---|
| DESC v1.3: 995.328 celdas (N×W, x, 144 ejecuciones, A/H ≥, comercio ≤, p_vol, v_rel), tamiz FDR q = 0,10 | NQ y USATECH, 2025-08-05 → 2026-03-31 | 0 nominadas en las dos (π0 = 1,0) | ninguna: el tamiz BH no mata la familia (v1.4 audita el filtro) |
| MDE v1.3b (determinista) | mismas | t máx NQ 4,59 · USATECH 4,29 ≈ máximo por azar (4,55); 33.000 / 25.000 celdas detectarían +1 fricción | no es falta de potencia en esas celdas |
| Reacción de VI coincidentes NQ↔USATECH (pre-registro 2026-10-22) | NQ 2026 | REFUTA: coef −0,20, IC90 [−1,79, +1,29] < fricción 1,545 | esa regla de reacción en VI coincidentes, NQ, ese período |

## No medido
- Umbral de máximo t con la correlación real (Romano-Wolf) y canal reciente (v1.4 en curso).
- Réplica de las pistas en 2026-04 → 2026-09 (lo más reciente sin usar) y forward.
- Otros instrumentos (ES, YM), otros timeframes que M1, otras definiciones de área (G, ciclos, ancho W fuera de 5–100).
- Entradas que no estén en las 144 ejecuciones (p. ej. confirmación por estructura, entradas escalonadas).
- Estado continuo (distancia al área en cada barra) en vez de evento (disparo).
- Réplica y holdout: no corresponden mientras no haya nominadas.

## Cómo podría reabrirse sin data snooping
Una grilla nueva (otras perillas o valores) es una prueba nueva: registro en el contador, pre-registro con el bloque `GRILLA` exacto y datos que esta corrida no usó para elegir.
