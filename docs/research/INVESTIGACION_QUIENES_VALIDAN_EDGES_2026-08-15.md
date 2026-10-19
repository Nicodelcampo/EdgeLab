# Investigación — Qué hacen quienes validan edges en una cuenta real

**Fecha:** 2026-08-15
**Estado:** `STRUCTURE_ONLY` — no es la investigación hecha; es el mapa.
**Pregunta general:** ¿qué hacen, de verdad, quienes descubren y validan edges económicamente rentables en el mercado real?
**Restricción:** cada área debe ser implementable en EdgeLab, saldar una debilidad, y acercar a una cuenta. Paridad / store / visor no son capítulos.
**Referente:** `docs/NORTH_STAR.md`. Contrato: `docs/edge_validation_contract.md`. Simulador: `docs/execution_simulator_spec.md`. Plan: `PLAN.md` C→E.
**Firewall:** `holdout_included=False`, `outcomes_accessed=False` hasta manifiesto + OK.

Nada de este documento afirma un edge ni autoriza F4.

---

## Principio

Lo que la evidencia pública permite copiar no es el edge de nadie. Es el **proceso de rechazo**: hipótesis económica primero, N_eff declarado, costos propios, fills que podrían ocurrir, una familia, G2 ejercido, holdout como sello, paper antes de 1 contrato. EdgeLab ya tiene los nombres (G0–G5, F4, simulador, holdout_guard). La debilidad es que casi nada de esa cadena se corrió sobre un objeto vivo.

Fuentes de proceso (no de alpha): Bailey / López de Prado (PBO, DSR, N_eff); Harvey 2017 (tests no reportados); AQR *Trading Costs* (costos de trades vivos); etiquetas/horizonte antes del modelo (López de Prado); filtrado por capacidad / decay / turnover; paper → capital mínimo.

---

## Mapa debilidad → capítulo

| Debilidad | Capítulo | Cierra si… |
|---|---|---|
| Acta ≠ board | 0 Ledgers | el registro no miente |
| Cero neto / F4 nunca corrida | 1 Pregunta económica | información condicional medida, o muerte |
| Siete familias al presupuesto | 2 N_eff | N escrito *antes* |
| Fricción de 6E transportada | 3 Costos | G3 deja de ser un número prestado |
| Sin ejecutable | 4 Fills | P&L neto defendible |
| Sesgo del toque / pack | 5 Un objeto | event-space enumerado |
| G2 ocioso | 6 Robustez real | un candidato pasa o muere en G2 |
| Holdout sano, sin candidato | 7 OOS sello | una apertura, después de G3 |
| Sin paper / kill switch | 8 Sombra | reglas completas *antes* de 1 contrato |

Higiene (`research-v3`, P-33(a), paridad HFT/aVolCell) no es capítulo. Corre en paralelo si no atrasa el 1.

---

## Capítulo 0 · Ledgers honestos

**Entregable:** un commit que alinee `PENDIENTE.md` + `EDGES_DISCOVERED.md` + acta D-1…D-8. Imán = cerrado. P-32 nombrado. P-33 = (a). P-07 = cerrada por alcance (V1 residual).
**Refutación:** si board y acta divergen otra vez en 48 h.

## Capítulo 1 · Pregunta económica (F4)

**Entregable:** manifiesto F4 de `aVolClusterPOI` sola: estimand, población, nulo, MDE, event-space (creación / aproximación / toque / invalidación / estado), cómo se refuta, hash de NORTH_STAR. STOP hasta OK. Resultado admitido: información / sub-fee / muerte.
**Refutación:** población elegida después de ver curvas, o dos familias en la misma corrida.

## Capítulo 2 · Presupuesto de hipótesis

**Entregable:** hoja N_eff de *esta* investigación. Configs de store no listadas no se corren.
**Refutación:** un resultado de una config no listada.

## Capítulo 3 · Costos por instrumento (W7)

**Entregable:** tabla ES / NQ / YM / 6E: tick value, comisión por pata, spread, slippage base/adverso/severo. Fuente: estado de cuenta o spec de broker. Sin esta tabla no hay capítulo 6 con P&L.
**Refutación:** un instrumento usa el número de otro; o no cierra `neto = bruto − spread − slip − comisión`.

## Capítulo 4 · Fills que podrían ocurrir

**Entregable:** simulador = golden G1–G7. Primera corrida diagnóstica; decide el escenario `base`. Prohibido `ts == available_at`.
**Refutación:** golden no reproduce, o fill en el step de la señal.

## Capítulo 5 · Un objeto, event-space escrito

**Entregable:** página de población del capítulo 1. `YMPreRangeSweep` fuera. `tick:N` de VolTicksPOC2 / aVolCellPOI2: cero promoción (P-28).
**Refutación:** una familia no listada aparece en F4 o G1.

## Capítulo 6 · Robustez sobre un objeto real

**Entregable:** (a) hash G2-A1 en la allowlist o por qué sigue vacía; (b) una decisión G2 sobre **un** candidato, escenario base. PASS o FAIL. Sin re-correr con gates relajados.
**Refutación:** promoción con `parity_covered` prestada, o falta un gate.

## Capítulo 7 · Holdout como sello

**Entregable:** no abrir. Borrar o cuarentenar V1 (humano). El capítulo empieza el día que exista G3.
**Refutación:** holdout usado para elegir umbral, `bar_spec` o familia.

## Capítulo 8 · Sombra y 1 contrato

**Entregable:** solo si hay G2+G3. Hoja de reglas (entrada/salida/sizing/límites/kill) hasheada *antes* de la primera sesión sombra.
**Refutación:** cambiar una regla mirando el paper.

---

## Fuera de alcance

Cómo opera un fondo concreto. GEX/L2/cruzado como capítulo 1. `research-v3` como camino crítico. F9. GPU/ML.

## Orden

0 → 3 (paralelo) → 5+2 → 1 (OK) → 4 → 6 → 7/8 si hay G3.

**Éxito de esta investigación:** un objeto en G0→G1, o una muerte F4/G1 registrada. Dejar de medir progreso en P-NN de infraestructura.

Aporte al referente: convierte "acercarse a una cuenta" en ocho capítulos con entregable y refutación, en el orden que el North Star ya exigía y el lab no había corrido.
