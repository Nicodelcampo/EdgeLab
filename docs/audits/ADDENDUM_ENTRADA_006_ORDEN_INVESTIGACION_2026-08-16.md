# Addendum del auditor — indicaciones omitidas al revisar la entrada 005

**Fecha:** 2026-08-16  
**Fuentes rectoras:**
- `docs/research/INVESTIGACION_QUIENES_VALIDAN_EDGES_2026-08-15.md`
- `docs/research/DEEP_RESEARCH_EDGES_CUENTA_2026-08-15.md`

**Corrige:** `docs/audits/REVISION_ENTRADA_005_2026-08-16.md`.

## 1. Omisión principal: puse G2 antes del objeto

La revisión anterior terminó diciendo que la próxima acción de mayor valor era el diferencial G2-A1. Eso contradice el orden explícito de la investigación:

```text
0 ledgers -> 3 costos -> 5 población + 2 N_eff -> 1 F4
-> 4 simulador -> 6 G2 -> 7 holdout -> 8 sombra
```

G2-A1 puede sanearse **en paralelo** si no retrasa el capítulo 1, pero no es la ruta crítica del proyecto. Hoy no hay candidato sobreviviente de F4 + simulador base sobre el cual ejercer G2.

**Prioridad corregida:** cerrar W7 hasta donde dependa de datos disponibles; escribir población + N_eff + grafo causal + manifiesto F4 para `aVolClusterPOI` sola; STOP para OK de Nico; recién después correr F4.

## 2. El capítulo 0 no está cerrado según su propio criterio

Su criterio de refutación dice: si board y acta vuelven a divergir dentro de 48 horas, el capítulo 0 no cerró.

La divergencia reapareció de inmediato:
- `ADJUDICACION_G2A1_2026-08-15.md` dice «gana B» sin corrida;
- la revisión 006 corrige a «candidata estructural preferida»;
- P-38 usa «por olvido» donde la causa demostrada es «implementación canónica no adjudicada»;
- la cadena del board/canal pone P-31 como prerequisito de un diferencial que el workflow puede correr sin worktree.

Por el criterio escrito, **capítulo 0 = REABIERTO / NO CERRADO** hasta que board, acta de adjudicación, P-38 y canal expresen el mismo estado.

## 3. Faltó el grafo causal antes de F4

La deep research exige un grafo causal antes de cualquier backtest. El manifiesto F4 debe decir:
- mecanismo económico por el que el estado de `aVolClusterPOI` debería cambiar retornos;
- variables observadas y latentes;
- confusores (hora, volatilidad, sesión, instrumento, régimen);
- qué evidencia refutaría el mecanismo.

No alcanza con estimand, población, nulo y MDE. Sin grafo causal, no se corre F4.

## 4. Faltaron condiciones de adjudicación estadística

El diferencial A/B no debe decidirse por «qué suite queda más verde». Debe probar los requisitos que la investigación nombra:
- 7 configuraciones que fabrican Sharpe 1 bajo Sharpe verdadero 0;
- N_eff incluye intentos abandonados;
- `MIN_DSR_SESSIONS` calibrado como MinTRL, no número ornamental;
- 424 eventos en 201 sesiones cuentan como dependencia por sesión, no n=424 IID;
- DSR e IC usan la misma población;
- purge + embargo cuando haya CV;
- CPCV o al menos múltiples caminos, no un único walk-forward.

El workflow existente compara fallas y ejecuta calibración sintética; hay que verificar que cubra explícitamente esta lista. Si no, el diferencial es de software, no de validez estadística.

## 5. Faltó mantener la barrera IC -> simulador -> G2

La investigación ordena:
1. IC/Spearman por horizonte y estado;
2. sólo si IC != 0, etiquetado/triple barrera y simulador;
3. escenario base como único que cuenta;
4. recién después G2.

No se debe construir una campaña G2 para compensar que F4 todavía no produjo información condicional.

## 6. Costos: W7 sigue primero y sigue incompleto

El spread ya fue medido por instrumento, pero falta la comisión real del broker de Nico. Hasta que exista:
- la tabla W7 queda parcial;
- no hay P&L neto defendible;
- no se transporta 6E a ES/NQ/YM;
- el escenario base debe ser específico por instrumento, especialmente NQ.

## Orden operativo corregido

1. Reabrir capítulo 0 y alinear board/acta/canal sobre G2-A1 y P-38.
2. Completar W7 con el dato de broker cuando Nico lo aporte.
3. Capítulo 5 + 2: población, event-space y hoja N_eff de `aVolClusterPOI` sola.
4. Agregar grafo causal y manifiesto F4 completo.
5. STOP: OK explícito de Nico.
6. F4: IC/Spearman antes de SL/TP.
7. Si hay información: simulador/triple barrera, escenario base.
8. En paralelo, sin bloquear 3–7: diferencial sintético A/B con la lista estadística completa.
9. G2 sólo sobre un candidato que sobrevivió F4 + simulador.
10. Holdout y sombra continúan cerrados.

**Corrección central:** sanear G2 es infraestructura necesaria, pero no distancia recorrida hacia una cuenta mientras no exista un objeto vivo. La ruta crítica vuelve a `aVolClusterPOI` sola, con N_eff y causalidad declarados antes de medir.