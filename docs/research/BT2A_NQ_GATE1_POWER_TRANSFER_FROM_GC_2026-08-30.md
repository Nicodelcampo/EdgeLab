# BT2A NQ Gate 1 - transferencia de potencia medida desde GC (paso 3b)

Fecha: 2026-08-30. Estado: `DRAFT_REVIEW_REQUIRED`. No concede freeze ni ejecucion.

## 1. Que se midio

Se extrajeron los valores **realizados** de la corrida de Gate 1 de GC ya
completada (`BT2_ABSORPTION_GATE1_ALL5_RESULT_2026-08-26.json`, status
`COMPLETE_GATE1_ALL5_POST_OUTCOME_REPLICATION`, `CAMPAIGN_OUTCOMES_OPENED=true`)
y de los cinco CSV por sesion, uno por contrato GC.

| Cantidad | Valor medido |
| --- | --- |
| Sesiones | 234 |
| Media del contraste pareado `K_ABS - N_RAND` | 4.837607 ticks |
| **SD del contraste pareado por sesion** | **11.528529 ticks** |
| SE de la media | 0.753644 ticks |
| rho entre brazos `K_ABS` / `N_RAND` | 0.561700 |
| Reduccion de varianza por el pareo | 48,06 % |

Control de correccion: la reconstruccion reproduce exactamente el contraste
publicado en el artefacto de GC (`point`, `n_sessions`), de modo que no es un
numero nuevo sino el mismo numero recomputado desde las filas por sesion.

## 2. Por que el SD realizado es el parametro correcto, y no el ICC

El ICC solo hacia falta para bajar de una cota a nivel de evento hasta el nivel
de sesion. El SD realizado **ya esta medido a nivel de sesion**, asi que el
agrupamiento intra-sesion esta embebido y no hace falta suponer nada.

Se intento igualmente identificar el ICC, aprovechando que los eventos por
sesion varian mucho en GC, mediante regresion de momentos de la desviacion
cuadratica de sesion contra `1/m_s`:

| Variante | ICC |
| --- | --- |
| Pooled | 0,0679 |
| Efectos fijos por contrato | 0,0878 |
| Leave-one-contract-out | 0,0441 a 0,1337 |
| Bootstrap IC95 | 0,0254 a 0,5317 |

**Veredicto: `NOT_IDENTIFIED_TIGHTLY_ENOUGH_TO_USE`.** El intervalo bootstrap
abarca un orden de magnitud y su cota superior fail-closed (0,5317) es *peor*
que el 0,20 supuesto. La via del ICC queda rechazada como palanca de potencia.

## 3. Consecuencia para la potencia de NQ

| Encoding | SD sesion | Sesiones para MDE 1 | MDE@234 Bonf-16 | MDE@234 1 celda |
| --- | --- | --- | --- | --- |
| Signo tricotomico (preregistrado) | 26.91 | 10443 | 6.68 | 4.93 |
| Magnitud, estimand de GC | **11.53** | 1916 | **2.86** | **2.11** |

El bloqueo de potencia no proviene de tener pocas sesiones: proviene de
**descartar la magnitud del recorrido y quedarse con un signo tricotomico**. Con
las mismas 234 sesiones, el mismo evento y el mismo contraste pareado, el
estimand de magnitud resuelve 2.86 ticks en vez de
6.68.

## 4. Ancla de plausibilidad

GC realizo un efecto de **4.84 ticks, IC95 [3,36 - 6,32]**, con 234
sesiones y **una sola configuracion preregistrada a alpha 0,05**, sin Bonferroni.

Esto refuta el umbral de juicio de ~3 ticks que se habia declarado para la rama 3
del fallo de las 14:05: un efecto de esa magnitud no es extraordinario, es lo que
el instrumento hermano efectivamente mide con la misma maquinaria.

## 5. Justificacion escrita de la transferencia

GC y NQ Gate 1 comparten familia de evento (BigTrap2Absorption), linaje de
runner (`edgelab.research.bt2_gate1_all5`), contraste pareado dentro de sesion
CME `K_ABS - N_RAND`, peso igual por sesion, tamano de muestra de 234 sesiones y
diseno de replicacion (`replications=10000`, `seed=20260821`). Los outcomes de GC
ya estaban abiertos, por lo que leerlos no abre nada nuevo.

Dos margenes independientes hacen la transferencia **conservadora**, no optimista:

1. Las celdas de NQ topean el recorrido en 5-30 ticks sobre horizontes 25-250,
   mucho mas ajustado que el `tick_cap=2000` / `clock_cap_seconds=900` de GC. Un
   tope mas ajustado solo puede reducir la varianza del outcome por evento.
2. NQ tiene 652,5 eventos por sesion contra 72,4 de GC, lo que solo puede reducir
   la componente de muestreo de la varianza a nivel de sesion.

Por eso el SD transferido es una **cota superior** para NQ bajo el mismo
estimand, no una estimacion puntual.

## 6. Lo que sigue abierto y requiere decision escrita de Nico

- `estimand_amendment_authorization`: cambiar el outcome por evento de signo
  tricotomico a magnitud del recorrido dentro de la celda. Es una enmienda al
  estimand preregistrado; no la puede tomar un agente.
- `preregistered_mde_ticks`: fijar el MDE desde la restriccion de diseno.
- `multiplicity_scope_16_cells_vs_single_primary_cell`: GC corrio una sola
  configuracion. Mantener 16 celdas con Bonferroni cuesta pasar de
  2.11 a 2.86 ticks.

Mientras esas tres no se resuelvan por escrito, el gate sigue
`UNDERPOWERED_AT_PREREGISTERED_MDE` y no corresponde freeze ni corrida.

## 7. Firewalls de esta derivacion

`nq_outcomes_accessed=false`, `nq_future_price_path_accessed=false`,
`nq_holdout_touched=false`, `pnl_accessed=false`, `edge_declared=false`.
