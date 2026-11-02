# Acta de apertura del holdout de la canasta v3 (2026-11-02), registrada antes de correr

Estado: VIGENTE. Canasta v3 firmada por Nico el 2026-11-02 (`PROPUESTA_V3_CAUSAL_20261102.md`). Referente: `docs/NORTH_STAR.md`, cuerpo
sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5.

## Reglas
Las 5 reglas de la v3: CVGAP-NQ, U1-RACIMOS-GRILLA-NQ, CVGAP-CFD-NQ, U1-ZONAS-AVCL-NQ y U1-ZONAS-NQ.
- Cada una con su celda, cortes y tope congelados en su `ACTA_HOLDOUT.json`.
- Código actual, con el certificado de causalidad vigente.

## Datos y ventana
- Dataset sellado `nicolasbuttaro/edgelab-holdout-sellado`, sesiones 2026-10-01 → 2026-10-30.
- Las zonas de las reglas U1 se calientan con el almacén de desarrollo anterior a la frontera.
- Las aperturas de las 5 familias desde 20261001 ya están en `HOLDOUT_VENTANAS.jsonl`. Ninguna miró P&L del holdout antes de esta corrida.

## Prueba principal: primera revisión, a 20 sesiones (v2, sin cambios)
1. **Serie.** Por sesión, la suma de neto / S de cada operación de las 5 reglas, donde S es la escala de `freno.py`:
   - CVGAP-NQ 78,0207;
   - U1-RACIMOS-GRILLA-NQ 33,9181;
   - CVGAP-CFD-NQ 48,7089;
   - U1-ZONAS-AVCL-NQ 17,2718;
   - U1-ZONAS-NQ 74,4533.
2. **Sesiones.** Las primeras 20 sesiones con datos válidos de las dos fuentes (NQ y USATECH), en orden. Una sesión sin
   operaciones vale 0. Esto se declara acá, antes de mirar.
3. **Estadístico.** t = media / (sd / √20). **Aprueba la revisión 1 si t ≥ 2,39** (O'Brien-Fleming, α total 0,10 a una cola).
   Si no, sigue a la revisión de 40 sesiones (t ≥ 1,69) y a la de 60 (t ≥ 1,38).
4. **Informativos:**
   - la misma serie contando sólo las sesiones con operaciones (la convención de `freno.py`);
   - por regla: n, media neta y su estado en `umbrales_estado.json`.

## Registro
1 prueba (la canasta, con sus 3 revisiones) en `TRIAL_REGISTRY_GLOBAL.jsonl`, como `holdout/CANASTA-V3/20261001-`.

## Cómo podría refutarse
Media ≤ 0 en la revisión de 60 sesiones, o una regla que cruce su umbral de colapso.
