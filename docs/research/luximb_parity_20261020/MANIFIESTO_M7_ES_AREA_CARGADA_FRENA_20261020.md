# Manifiesto M7 (PROPUESTO, sin OK) — "un area cargada de OG/VI frena el precio": escalonadas en ES, descubrimiento

Estado: PROPUESTO. **No se corre sin OK explicito de Nico** (STOP del proyecto). Fecha 2026-10-20.
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Origen: pista NO pre-registrada de M6 en NQ (H1 -3,6 pp IC [-7,1,-0,2]; recorrido a 60 min menor con zonas). Se prueba en
OTRO instrumento con direccion fijada de antemano.

## Datos (HOLDOUT-A3, ES)
Descubrimiento: ES 09-25 (2025-07-21..09-15), 12-25 (09-16..12-15), 03-26 (12-16..2026-03-16), 06-26 (03-17..03-31).
release v4 `ES_ticks.parquet`, un contrato por tramo, sin back-adjust. Replicacion ES (abr-sep) queda **intacta** para esta
pista: esta familia nunca miro ES. Holdout no se toca. Proceso en numpy por contrato (sin bundles JSON del visor: ES tiene
~2x ticks que NQ; regla de no cargar archivos enteros).

## Poblacion (congelada antes de mirar desenlaces)
Event-space: todas las escalonadas que da `escalonadas_det.detectar_px` (familia IPC-NQ, nmin 5, confirmacion por precio).
- Barras: tick-bars de ES de tamano K elegido **target-free** para que la duracion mediana iguale a la de las velas 150t de
  NQ (calibrado sobre ES descubrimiento, solo tiempos; se publica K antes de medir).
- Umbrales en ticks escalados por precio ES/NQ (factor 1/4,17, el mismo de `escalonadas_det`): escalon <= 10, retroceso >= 3,
  confirmacion 4 ticks.
- Zonas LUX-IMB (OG+VI, M1, vida 500 min) con el detector con paridad en NQ; en ES **sin oraculo NT8** (riesgo abajo).
- **T** = area con >= 3 zonas vivas; **C** = 0-2. Sensibilidad (no inferencial): >= 2 y >= 5.

## Desenlace (igual que M6) e hipotesis — direccion fijada por la pista
Carrera desde el cierre de la barra de deteccion: ruptura del area a favor vs superar el ultimo pico +1 tick; tope 240 min.
Recorrido no direccional = MFE + MAE a 60 min en puntos.
- **H1** P(ruptura) T - C **< 0**.
- **H2** recorrido no direccional (pts) T - C **< 0**.
- **H3** H1 con control **emparejado** por terciles de tamano de area y franja (cash 9:30-11 / resto): descarta que el efecto
  sea solo "areas mas grandes" u "otra hora".
- **H4** P&L neto de operar el rechazo en T > 0 (version economica). Costos ES propios: 1 tick ($12,50) por lado de mercado,
  $4,50 RT (0,09 pts). Sensibilidad 0/1/2 ticks.
Holm sobre 4. Bootstrap por dia NY, 10.000. MDE80 de H1 y H2 publicados. Numero efectivo de hipotesis: 4 (+ sensibilidades
descriptivas sin inferencia).

## Justificacion economica
Zonas OG/VI sin negociar acumulan liquidez pasiva; un precio que escalona sobre ellas deberia absorberse (menos recorrido,
mas rechazo). Si es asi, el valor operable estaria en el rechazo o en evitar entradas de ruptura sobre areas cargadas.

## Como podria refutarse
H1 y H2 sin efecto (IC incluye 0 con MDE <= 5 pp / <= 15 % del recorrido), o efecto solo en el control sin emparejar (H3 nula).
Una muerte aplica a escalonadas IPC sobre area cargada en ES; si muere en ES, la pista de NQ queda como no replicada.

## Riesgos
1. Paridad del detector LUX-IMB y de las barras en ES no medida contra NT8 (la logica es pura OHLC; en NQ dio 100 %).
2. Escalado de parametros NQ -> ES es una eleccion (declarada aca); un mal escalado cambia la poblacion.
3. La pista nacio de un resultado: riesgo de perseguir ruido. Por eso: otro instrumento, direccion fija, Holm, emparejamiento.
4. Clustering por dia y solapamiento de escalonadas consecutivas.
5. Si ES confirma, la replicacion ES (abr-sep) se usa una sola vez sobre esta definicion exacta.

## Datos faltantes
Ninguno para correr. Falta (no bloqueante): oraculo NT8 de LUX-IMB en ES para paridad.
