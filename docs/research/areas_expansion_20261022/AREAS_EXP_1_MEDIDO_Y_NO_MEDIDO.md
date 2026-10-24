# AREAS-EXP-1 (áreas de zonas LUX-IMB) — qué está medido y qué NO (registro vivo, desde 2026-10-22)

Estado: VIGENTE — 0 confirmadas. U1-B refutada en NQ; U1-CRUZADO (señal del CFD, operación en NQ) positiva en desarrollo, pendiente de forward.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia independiente (no transporta resultados, costos ni multiplicidad de BigTrap2, HFTZones, aVolCluster, ESPEJO ni YM-PRERANGE).
Spec: `SPEC_AREAS_EXPANSION_V1.md` (v1.3). Manifiesto y resultados: `MANIFIESTO_DESC_AREAS_EXP_1.md`.

## Medido
| qué | datos | resultado | alcance exacto de la muerte |
|---|---|---|---|
| DESC v1.3: 995.328 celdas (N×W, x, 144 ejecuciones, A/H ≥, comercio ≤, p_vol, v_rel), tamiz FDR q = 0,10 | NQ y USATECH, 2025-08-05 → 2026-03-31 | 0 nominadas en las dos (π0 = 1,0) | ninguna: el tamiz BH no mata la familia (v1.4 audita el filtro) |
| MDE v1.3b (determinista) | mismas | t máx NQ 4,59 · USATECH 4,29 ≈ máximo por azar (4,55); 33.000 / 25.000 celdas detectarían +1 fricción | no es falta de potencia en esas celdas |
| v1.4: Romano-Wolf por sesiones + canal reciente | mismas | 0 rechazadas en los 4 canales; umbral medido 5,4–5,6; lo más cercano: USATECH reciente (t 5,45, p RW 0,12, FDR 4) | ninguna: 80 pistas van a réplica 2026-04 → 09 |
| Réplica de 80 pistas, 2026-04 → 09 (LORD++ en orden) | NQ y USATECH | 0 confirman; media +28,8 → +1,6 pts/op; 5 celdas USATECH de una sola idea (U1) con p ≤ 0,0015 | las 75 pistas restantes en su réplica; U1 sigue abierta |
| U1-INDAGA (marginales, 3M celdas por fuente) | USATECH 2025-08 → 2026-09; NQ 2025-08 → 2026-03 | USATECH: A/H ordena monótono (+3 → +18 → +37), VWAP entre área y mitad +28, volumen alto en la ida +25. Por la regla, una sola variante con cota > 0 en ambas: U1-B (x = 0,15; NQ +7,3 [1,2, 12,8]) | ninguna: exploración; la confirmación en NQ abr–sep no tiene potencia (MDE ≈ 13) |
| U1-B, seguimiento secuencial (acta `u1/ACTA_SEGUIMIENTO_U1B.md`) | NQ 2026-04-01 → 09-25 (Fase A, no usada antes) | 91 operaciones, media −0,18 pts/op, IC90 [−10,1, +8,5]; el seguimiento se detuvo con LIMITE_VIOLADO (−241 < piso −221). Holdout (Fase B) no inspeccionado | **REFUTADA**: esa celda, en NQ, con E1A/T1/S3 |
| U1-CRUZADO: señal U1 en USATECH, operación en NQ (`u1/MANIFIESTO_U1_CRUZADO.md`) | 2025-08 → 2026-03 y 2026-04 → 09 | NQ neto T1 +16,8 / +21,1; T3 +21,5 / +28,4 pts/op, IC90 > 0 en los dos períodos; ≈ igual que en USATECH | ninguna: desarrollo (mismos meses de la selección); falta forward |
| U1-CRUZADO integridad (alineación, placebo, latencia) | desarrollo 2025-08 → 2026-09 | pasa: pico 0 s, placebo ≈ 0 o negativo, latencia 5 min sin degradar | ninguna |
| U1 fuera de muestra (paso 3 LORD++) | USATECH 2023-01 → 2025-07 | T1 +0,06 [−9,0, +8,3]; T3 −4,55; por año −2 / −10 / +7; sin rechazo | no se confirma en 2023–2024; no la mata (régimen) |
| U1-CRUZADO holdout exploratorio (acta previa) | NQ 2026-10-01 → 21 (señal USATECH) | 8 ops, T3 +29,4 pts/op (7/8); NO_CONCLUYENTE | ninguna; consume la apertura 01–22 oct |
| Reacción de VI coincidentes NQ↔USATECH (pre-registro 2026-10-22) | NQ 2026 | REFUTA: coef −0,20, IC90 [−1,79, +1,29] < fricción 1,545 | esa regla de reacción en VI coincidentes, NQ, ese período |

## No medido
- Lo aprendido de las marginales de USATECH (A/H, VWAP, volumen en la ida) medido en NQ con potencia; NQ tiene sólo 8 meses de exploración.
- Otros instrumentos (ES, YM), otros timeframes que M1, otras definiciones de área (G, ciclos, ancho W fuera de 5–100).
- Entradas que no estén en las 144 ejecuciones (p. ej. confirmación por estructura, entradas escalonadas).
- Estado continuo (distancia al área en cada barra) en vez de evento (disparo).

## Cómo podría reabrirse sin data snooping
Una grilla nueva (otras perillas o valores) es una prueba nueva: registro en el contador, pre-registro con el bloque `GRILLA` exacto y datos que esta corrida no usó para elegir.
