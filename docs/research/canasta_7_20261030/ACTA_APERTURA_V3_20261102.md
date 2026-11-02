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

## Resultado de la revisión 1 (2026-11-02), en `holdout_v3/RESULTADO.json`
- **Principal, 20 sesiones (10-01 → 10-28):** media −0,62 por sesión (en unidades de S), **t = −1,51** contra un umbral de 2,39.
  **No aprueba.** La canasta sigue hacia la revisión de 40 sesiones; con este arranque, aprobar ahí exige un cambio grande.
- Informativo, sólo las sesiones con operaciones: 18 sesiones, t = −0,73.

| Regla | n | Media neta | Estado contra `umbrales_estado.json` |
|---|---|---|---|
| CVGAP-NQ | 20 | −34,9 | debajo del p5 de n = 20 (−18,3), arriba del colapso (−36,2): **alerta** |
| CVGAP-CFD-NQ | 16 | −22,9 | entre los umbrales de n = 10 y n = 20: **alerta**, sin colapso |
| U1-ZONAS-NQ | 17 | −14,6 | dentro de lo esperable (p5 n = 20: −31,6) |
| U1-ZONAS-AVCL-NQ | 7 | +15,0 | a favor |
| U1-RACIMOS-GRILLA-NQ | 5 | +43,7 | a favor; operaciones recién desde el 10-13 (ver abajo) |

- **Integridad por revisar antes de la revisión 2.** U1-RACIMOS no tiene operaciones del 10-01 al 10-12. Puede ser el mercado o que el
  calentamiento de racimos del sellado no esté entrando (el almacén de racimos de desarrollo puede no llegar a la frontera). Se
  revisa sin mirar P&L de nuevo y queda registrado.
- **Lectura.** El holdout no confirma la canasta: las dos reglas CVGAP, las de más peso en operaciones, van en contra en octubre.
  Nada se ajusta con este resultado.
