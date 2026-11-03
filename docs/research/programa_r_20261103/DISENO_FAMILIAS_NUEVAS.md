# Diseño de familias nuevas para el programa R (2026-11-03)

Estado: VIGENTE, registrado antes de correr. Pedido de Nico: «diseñá las familias nuevas aprovechando toda la información disponible
(cerebros, papers, corridas anteriores); luego corrélas». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Programa: `PROGRAMA_R.md`. Etapa: EF2 → embudo completo, medido en R.

## Criterios de diseño (lo que dicen las corridas anteriores)
1. **Mecanismo nuevo, no otra grilla de lo mismo.** Las pistas de 44 familias rinden −0,042R fuera de muestra, sin relación con el
   tamaño de la grilla: buscar más sobre las mismas ideas no ayuda.
2. **Independencia de la cartera** (Grinold: IR ≈ IC × √amplitud). La cartera vive de zonas, áreas y corredores, casi todos
   direccionales y en la apertura o en Asia. Se priorizan:
   - una apuesta relativa (neutral al mercado);
   - otro activo con su propio motor (oro, dólar);
   - una franja de muchas operaciones (el mediodía del horario regular).
3. **Pocas perillas:** entre 72 y 216 celdas por canal, contra cientos de miles a millones en las familias anteriores. La potencia se usa en
   la medición, no en la búsqueda.
4. **Todo en R** (`"estadistico": "R"`), con código causal certificado, sesiones válidas, fricción canónica y triple barrera (objetivo,
   stop y tiempo), según López de Prado.
5. **No duplicar lo existente:**
   - gaps de apertura: GAP-RTH;
   - cierre: EOD-MOM;
   - apertura: OTR930;
   - Asia: ASIA-BOS;
   - reversión filtrada sin volumen: KALMAN-FADE.

## Familias
| Familia | Módulo | Mecanismo y fuente | Campañas | Celdas por canal |
|---|---|---|---|---|
| PAR-REL | `par_relativo.py` | Valor relativo intradía entre índices: el spread log(sensor) − β·log(ES) revierte. Gatev, Goetzmann y Rouwenhorst (2006) | PAR-NQES-R (NQ contra ES), PAR-YMES-R (YM contra ES) | 108 |
| LEAD-LAG | `lead_lag.py` | El dólar (EURUSD) lidera al oro: el oro incorpora con rezago un movimiento fuerte del dólar. Hasbrouck (1995); Chordia y Swaminathan (2000) | LEADLAG-GC-EUR-R | 216 (incluye la perilla `rho_fuerte`) |
| VWAP-REV | `vwap_rev.py` | Reversión al VWAP de la sesión regular tras un desvío ≥ 2σ con vela de giro, fuera de noticias. Berkowitz, Logue y Noser (1988); Madhavan (2002) | VWAP-NQ-R, VWAP-ES-R | 72 |

**Ejecución en las tres:** entrada en la vela siguiente (E1A), objetivo y stop en desvíos de la propia señal, y salida forzada por tiempo
(PAR-REL 120 velas, LEAD-LAG 60) o a las 15:59 (VWAP-REV).

**Lección aplicada del punto 3 (no cortar ganancias):** no hay break-even ni trailing. Hay dos objetivos, uno corto y uno largo, y dos
stops.

## Justificación económica y cómo podría refutarse
- **PAR-REL.**
  - *Justificación:* NQ, YM y ES comparten el factor de mercado. Los desvíos intradía del spread vienen de flujos sectoriales
    transitorios.
  - *Refutación:* el spread no revierte dentro de 120 velas; en R no hay celdas nominadas ni pistas que repliquen; o la ganancia
    depende de un solo día.
- **LEAD-LAG.**
  - *Justificación:* el oro se cotiza en dólares y su futuro ajusta más lento que el FX en las horas de poca liquidez.
  - *Refutación:* el seguidor ya incorporó el movimiento (no hay rezago explotable); o `rho_fuerte = 1` no es mejor que `rho_fuerte = 0`.
- **VWAP-REV.**
  - *Justificación:* los ejecutores de VWAP absorben el desvío de flujo transitorio.
  - *Refutación:* los desvíos de 2σ continúan en vez de revertir, o la ventaja vive sólo cerca de noticias, que ya están excluidas.

## Población (regla del repo)
Lo que se mide es el **evento** del cruce del umbral, con un disparo por episodio. Se descartó medir el **estado** continuo (cada vela con
|z| > k), porque está autocorrelado y no da más información por operación. El primer cruce y los n siguientes se separan por el rearmado
(|z| < 1).

## Linaje y multiplicidad
Las tres son familias nuevas, sin padres (`LINAJES.jsonl`). Cada DESC registra sus celdas en el contador global. LORD++ con el libro de
cada familia.

## Después de correr
- **Correlación esperada con la canasta v5:** se calcula con el P&L de las pistas antes de cualquier nominación
  (`tools/correlacion_nominadas.py`).
- **Atlas:** las marginales globales de las tres entran al atlas de ideas.

## Resultado de la primera corrida (03/11/2026, embudo en R, conductor local)
Raíz: `docs/research/programa_r_20261103/embudo/`. Las cinco terminaron en FIN y **ninguna llegó a réplica ni al holdout**.

| Campaña | Evaluables DESC (m FDR) | FDR | Pistas | z de la celda (mín / mediana / máx) | Desenlace |
|---|---|---|---|---|---|
| PAR-NQES-R | 68 de 108 | 0 | 2 | −13,6 / −2,9 / −0,57 | SIN_CANDIDATAS |
| PAR-YMES-R | 68 de 108 | 0 | 2 | −13,7 / −3,3 / +0,44 | SIN_CANDIDATAS |
| LEADLAG-GC-EUR-R | 156 de 216 | 0 | 9 | −7,4 / −1,8 / +1,56 | SIN_CANDIDATAS |
| VWAP-NQ-R | 12 de 72 | 0 | 1 candidata | — | INTEGRIDAD_FALLA (regla −0,017R, latencia 1 vela −0,022R) |
| VWAP-ES-R | 16 de 72 | 0 | 3 | −1,3 / −0,6 / +0,18 | SIN_CANDIDATAS |

Lectura:
- **PAR-REL (fade del spread) queda REFUTADA en R en su forma registrada.** No es un nulo sin potencia. Entre 33 y 35 de 68 celdas
  quedan por debajo de −z del tamiz, y ninguna queda por encima. Con fricción, fadear el spread NQ/ES o YM/ES a 2σ pierde de forma
  sistemática. La lectura inversa (el spread *continúa*) **no se toma de acá**: elegir la dirección después de ver el signo es snooping.
  Si se registra, va como familia hija en `LINAJES.jsonl`, hereda estas 216 pruebas y antes separa bruto de fricción. Con stops cortos
  en R, la fricción puede ser todo el efecto.
- **LEAD-LAG GC/EURUSD:** sin señal positiva (máx z +1,56 de 156 evaluables). Pérdida moderada: el oro ya acompañó al dólar dentro de la
  vela de 1 minuto. Esta es su condición de refutación declarada. Refutada en esta resolución; queda abierta una medición sub-minuto,
  que hoy no está soportada (P-28: `sequence` no es secuencia del exchange).
- **VWAP-REV: SIN POTENCIA, no refutada.** Sólo 12 a 16 de 72 celdas llegan a 30 operaciones: el disparo (|dev| ≥ 2 + vela de giro +
  franja + régimen) es demasiado raro. La única candidata (NQ) murió en integridad: retrasarla una vela la empeora, y el placebo da −2,57.
  Para que sea medible necesita más dato o un disparo menos restrictivo **declarado antes**, no relajado sobre este resultado.
- **Correlación con la canasta v5:** no aplica, porque no hubo pistas con media > 0 para correlacionar. Las marginales quedan para el
  atlas.
