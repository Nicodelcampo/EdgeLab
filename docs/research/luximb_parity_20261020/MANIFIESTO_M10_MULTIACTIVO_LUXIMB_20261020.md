# Manifiesto M10 — LUX-IMB en otros activos (MYM, GC, 6E, 6B, 6J, MBT), descubrimiento

Estado: PRE-REGISTRADO. **Autorizacion de Nico 2026-10-20**: "probá en otros activos. no solo esto sino cualquier prueba que
consideres. vas a tener que adaptar las configuraciones pero te autorizo". Se congela todo aca antes de mirar desenlaces.
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## Por que estas pruebas (y no otras)
De M1-M9 en NQ/ES quedan tres efectos con signo a favor en desarrollo, ninguno confirmado. Se re-prueban **solo esos tres**,
con sus definiciones congeladas, en 6 activos independientes (sin micros duplicados: MES/MNQ/MGC fuera). Nada nuevo se
inventa aca: es la prueba de transporte de la familia.
- **H1 (M9-H_m)**: tras vuelta rapida (<= 15 min) del 25 % del impulso, P(llegar a A antes que a X) con el otro lado vacio
  (m <= p33) vs cargado (m >= p67). NQ +6,6 pp (Holm 0,045), ES -0,7 pp.
- **H2 (M5)**: impulsos de inicio cargado (>= 3 zonas en el 25 % inicial y >= 50 % de las atravesadas ahi) vs control de igual
  amplitud: P(volver al borde del 25 % inicial antes de +25 %). NQ +2,2 pp (n.s.).
- **H3 (M8-A1, vida 200)**: desbalance adelante vs atras, P(vuelta 50 % antes de +25 %). NQ +2,9 pp, ES 0,0 (n.s.).

## Datos
release v4, un contrato por tramo (front), sin back-adjust; **solo descubrimiento 2025-07-18 .. 2026-03-31** (abr-sep y
holdout intactos para todos). Contratos: MYM 12-25, 03-26; GC 12-25, 02-26, 04-26; 6E/6B/6J 09-25, 12-25, 03-26;
MBT 09-25 .. 03-26 (mensuales). Tick y costos por activo (no se transportan): tick de `release_manifest.json`;
slippage 1 tick; comision RT $4,50 (GC, 6E, 6B, 6J) y $1,20 (MYM, MBT) convertida a puntos con el multiplicador de
`edgelab/instruments.py`.

## Configuraciones (adaptacion congelada)
Todo lo que en NQ estaba en puntos pasa a terminos relativos o en ticks propios del activo:
- Zonas LUX-IMB (OG+VI) en M1 con el detector de paridad (sin oraculo NT8 en estos activos: riesgo declarado).
- Impulsos ESPEJO-IND (umbral 3·ATR, <= 20 velas, eficiencia >= 0,3): ya relativos.
- Poblacion H1/H3: amplitud >= max(p50 causal, 1,3 x mediana causal) — `--modo inicio --p-rango 50 --min-ini 0 --share-ini 0 --rango-min-rel 1.3`.
- Poblacion H2: `--modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-rel 1.3 --ctrl-modo amplitud` (el piso
  fijo de 60 pts de NQ se reemplaza por 1,3 x mediana, la misma equivalencia usada en EURUSD).
- Velas 25t = 25 operaciones del contrato (en todos los activos hay operaciones reales).
- Cortes de H1 (p33/p67 de m) y H3 (p20/p80 de D): los de cada activo, calculados sobre sus eventos sin mirar desenlaces.

## Inferencia
Por activo: diferencia ajustada por estratos (vol_pre x tamano, como en M8/M9) y bootstrap por dia (5.000 replicas).
**Prueba principal por hipotesis = estimacion combinada** de los 6 activos (inverso de la varianza), bilateral. Holm sobre 3.
Una hipotesis "transporta" si: combinada con Holm < 0,05 **y** el signo coincide con NQ en >= 4 de 6 activos.
Se publican todas las celdas, n, dias y MDE por activo. Sin seleccion de activos ni parametros despues de mirar.

## Justificacion economica
Si alguno de estos efectos es una propiedad de las zonas OG/VI y no de NQ, deberia aparecer en mercados distintos (indice,
metal, divisas, cripto) con el mismo signo.

## Como podria refutarse
Las tres combinadas sin efecto (IC incluye 0), o signos sin consistencia entre activos. Con eso la familia LUX-IMB queda
cerrada en su definicion actual.

## Riesgos
1. Sin paridad NT8 en estos activos (logica pura OHLC; en NQ fue 100 %).
2. Activos con pocas operaciones (6B): velas 25t lentas, menos eventos (MDE grande; se publica).
3. MBT mensual: muchos rolls cortos; MYM solo desde oct-2025.
4. Tres hipotesis ya miradas en NQ: esto es transporte, no descubrimiento; un positivo aca seguiria necesitando holdout.

## Enmienda M10b (escrita despues de ver M10, ANTES de correr el control) — 2026-10-20
M10 dio H3 combinado **-4,7 pp** (p 1,5e-7), signo **opuesto** a NQ en 6/6 activos: con mas zonas adelante que atras, la
vuelta del 50 % es MENOS probable. Por la regla escrita H3 **no transporta** (signo != NQ). Antes de cualquier lectura
causal, control de confusion obvio: las zonas adelante pueden ser solo un indicador de que el precio **ya opero** en esa
franja recientemente (impulso que vuelve a un rango previo), sin rol propio de las zonas.
- Covariable causal: **cobertura** de cada franja por el rango [min low, max high] de las 500 velas M1 previas al origen A
  (fraccion de la franja adelante y de la franja atras ya visitada; 0..1).
- **H3b**: mismo contraste H3 (vida 200, cortes de M10) con estratos de vol_pre x R x franja horaria **x terciles de cobertura
  adelante x terciles de cobertura atras**. Combinado por inverso de la varianza en los 6 activos; bilateral.
- Lectura: si H3b ~ 0, el efecto es "precio ya visitado", no de zonas. Si persiste, pasa a candidato direccional nuevo
  (signo negativo) para replicacion abr-jun 2026 en estos activos (pendiente de decision; no se usa aca).
- Se reporta tambien NQ y ES con la misma covariable (descriptivo).
