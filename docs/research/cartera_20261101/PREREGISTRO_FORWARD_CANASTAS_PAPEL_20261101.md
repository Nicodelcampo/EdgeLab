# Pre-registro: canastas congeladas en PAPEL (cartera viva), forward desde 2026-11-02

Estado: VIGENTE (pre-registro; nada de la ventana se miró). Fecha: 2026-11-01. Aprobado por Nico en la sesión en la nube («Sí, dá de alta»).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa del embudo: EF5 (seguimiento forward). Marco: `docs/CARTERA_VIVA.md`. Fichas: `config/cartera/altas.json`, generadas con
`tools/cartera_diaria.py preparar-altas --plan docs/research/cartera_20261101/altas_plan.json`.

## Qué entra
Las mejores pistas de las corridas recientes. Ninguna está confirmada: son familias vivas, con veredicto `SIN_POTENCIA` o
`SIN_RECHAZO` en la réplica. Curvas IS/OOS: `docs/research/equity_pistas_20261101/`.

| Ficha | Familia | Celdas | IS pts/sesión | Réplica pts/sesión (IC90) | Veredicto de la réplica |
|---|---|---|---|---|---|
| `RANGO0100-NQ-CANASTA` | `RANGO_ASIA0100_NQ` | 1 | +13,51 | +13,73 [−3,7; 30,7], 27 sesiones | SIN_POTENCIA |
| `PRERANGE-ZONAS-NQ-CANASTA` | `PRERANGE_ZONAS_NQ` | 19 | +8,70 | +5,68 [−2,9; 15,0], 100 sesiones | SIN_POTENCIA |
| `OTR930-NQ-CANASTA` | `OTR_930_SWEEP_NQ` | 20 | +8,48 | +5,12 [−1,2; 12,0], 94 sesiones | SIN_RECHAZO |
| `ASIA-NQ-CANASTA` | `ASIA_BOS_GAPS_NQ` | 20 | +6,09 | +4,38 [−0,3; 8,8], 102 sesiones | SIN_RECHAZO |

ASIA-NQ ya tiene su propio pre-registro de confirmación (`docs/research/asia_bos_20261029/PREREGISTRO_FORWARD_CANASTA_ASIA_NQ_20261031.md`,
con nivel LORD++ reservado). Ese documento sigue mandando para **confirmarla**. Este documento sólo agrega su seguimiento operativo
en la cartera. La ficha de ASIA-NQ cita aquel pre-registro.

## Objeto (congelado)
- Celdas: `pistas_replica.celdas` del `estado.json` de cada campaña, en el mismo orden. Cortes del DESC (`cortes`). Código de cada
  experimento al commit de este pre-registro. Fricción canónica de NQ (`edgelab/costos.py`). Sin tope, sin filtros y sin pesos
  elegidos después.
- Observación: la canasta igual-ponderada por sesión. Es la suma del neto de todas las celdas en la sesión dividida por el número de
  celdas, sólo en sesiones con alguna operación. Es el mismo estimador de la réplica y de las curvas de equity
  (`edgelab/cartera/papel.py::canasta_por_sesion`).
- Motor: `ANALIZAR_REGLA` con `operaciones=True`, el mismo que eligió las celdas.
- **No** se usan canastas "ortogonales" ni subconjuntos elegidos mirando el OOS.

## Ventana
- Sesiones CME con fecha **>= 2026-11-02**, hacia adelante. Son datos que no existían al escribir esto.
- **Octubre de 2026 queda afuera.** Es holdout sellado (HOLDOUT-A4) y queda disponible para la apertura formal de cada familia por el
  protocolo de `edgelab/autopilot/holdout_apertura.py`. Esta prueba no lo consume.
- Una ventana por familia en el libro de ventanas (`holdout_ventanas`), registrada al dar el alta, con estadístico `e_proceso`.

## Prueba (la de la cartera, `edgelab/funnel/secuencial.MonitorCandidato`)
Es válida mirando todos los días (Ville).
- **EDGE**, H0 E[x] <= 0. Con e >= 1/0,05 y al menos 30 sesiones forward, la ficha pasa a **REAL**. Las reglas `alfa_real` y
  `min_ops_real` son las de `config/cartera/cartera.json`. REAL **no** habilita dinero: las cuentas reales las habilita una persona.
- **FUTILIDAD**, H0 E[x] >= mu_util. Con e >= 1/0,10 la ficha queda **RETIRADA**. También se retira con un drawdown forward mayor a
  8 × la pérdida máxima declarada.
- **Efecto útil** `mu_util` = min(0,5 × efecto del DESC, 0,5 × media de la réplica), por sesión. Se toma el menor para no retirar
  por exigir más de lo que la réplica mostró.

| Ficha | mu_util |
|---|---|
| RANGO0100 | 3,38 |
| PRERANGE-ZONAS | 2,84 |
| OTR930 | 2,56 |
| ASIA | 2,19 |

- **Cotas declaradas** (ver Limitación): 3 × el peor y 3 × el mejor valor por sesión del desarrollo (hasta 2026-09-30). La tabla
  muestra los valores antes de sumar la fricción canónica de NQ, que el monitor agrega a las dos cotas.

| Ficha | Cota inferior | Cota superior |
|---|---|---|
| RANGO0100 | −273,9 | +365,9 |
| PRERANGE-ZONAS | −463,7 | +714,2 |
| OTR930 | −215,4 | +514,7 |
| ASIA | −220,4 | +435,6 |

  Una sesión fuera de esas cotas detiene la ficha con "cota estructural violada". La ficha se retira, no se recorta el valor.

## Limitación declarada
Estas reglas no tienen pérdida máxima en puntos por construcción. El stop está en el rango, en la mitad o el borde opuesto, en el
pivote o en la zona, y su ancho no tiene techo. El e-proceso necesita cotas, así que se **declaran** antes del forward con un margen
de 3× sobre el desarrollo. Esto no es una cota estructural, y es el riesgo que describe el error 10 de la revisión del 2026-10-23.
La mitigación: la canasta promedia entre 19 y 20 celdas, y salirse de la cota retira la ficha en vez de distorsionar la prueba. Para
operar con dinero, cada regla necesita un tope en puntos, que es otra regla y requiere otro pre-registro.

## Justificación económica y cómo podría refutarse
- **RANGO0100-NQ**: la ruptura del rango 01:00–01:15 ET, con reentrada, libera órdenes acumuladas en los bordes
  (`SPEC_RANGOS.md`). Se refuta con futilidad, o con media forward <= 0 a las 60 sesiones con operación.
- **PRERANGE-ZONAS-NQ**: la cantidad de zonas alrededor del rango 08:12–09:12 ET cambia lo que sigue a un barrido
  (`SPEC_PRERANGE_ZONAS.md`). Se refuta igual.
- **OTR930-NQ**: el barrido del rango pre-market en la apertura de contado vuelve hacia el POC, el 50% o el extremo opuesto
  (`SPEC_OTR_930_SWEEP.md`). Se refuta igual.
- **ASIA-NQ**: la caja asiática y su ruptura o barrido (`SPEC_ASIA_BOS_GAPS.md`). Su refutación formal está en su propio pre-registro.

Las cuatro comparten el riesgo de maldición del ganador: salieron de grillas de 648 a 1,1 M celdas. Si el efecto fuera de selección,
la media forward tiende a 0 y la futilidad las retira.

## Qué NO se afirma
Que sean edges. Que REAL implique operar con dinero. Que el e-proceso de la cartera reemplace la confirmación por el embudo con
LORD++: no reserva α y no es un descubrimiento. Que las cuatro sean independientes: todas son NQ y se solapan en la sesión de NY.
Por eso `peso_max_instrumento` limita su peso conjunto.

## Reglas
- No se cambia nada del objeto después de este commit. Un cambio de código que altere las operaciones invalida el seguimiento: la
  ficha se retira y la regla nueva necesita otro pre-registro.
- Conteo: 4 pruebas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (`cartera_forward/<CID>/20261102`), una por canasta.
- Bloqueo práctico: hacen falta los ticks de NQ del día en el Debian (`docs/CARTERA_VIVA.md` §8.1). Sin ellos, la ficha no suma
  sesiones y queda esperando. No se rellena con otra fuente.
