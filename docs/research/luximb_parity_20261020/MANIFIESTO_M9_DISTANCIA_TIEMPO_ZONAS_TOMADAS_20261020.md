# Manifiesto M9 (PROPUESTO, sin OK) — distancia y tiempo tras el impulso + zonas tomadas / restantes -> ¿cruza al otro lado?

Estado: PROPUESTO. **No se corre sin OK de Nico.** Fecha 2026-10-20.
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Origen: pregunta de Nico: "¿hay alguna distancia (mas/menos de x) y algun tiempo (mas/menos de x) a la que el precio se
aleje luego de un impulso, que segun la cantidad de OG/VI que haya y que haya tomado, prediga si va a ir al otro lado del
impulso de forma rentable? ¿depende de que hay del otro lado?". Antecedentes: M4 (penetracion 25-75 % sin tiempo ni zonas:
nulo T vs C) y M8 (desbalance adelante/atras; resultado pendiente al escribir esto).

## Poblacion
Los mismos impulsos de M8 (`desc_m8/imp_*`): NQ descubrimiento = desarrollo (~5.400), ES descubrimiento = prueba externa
(~6.500). Replicacion y holdout no se tocan.

## Evento condicionante (causal)
Desde el cierre de la vela de marca, sobre velas 25t: primer toque de la **distancia d** de vuelta desde el extremo X
(d en fracciones de R: **0,25 y 0,50**), antes de que el precio supere X. Se registra el **tiempo t** desde la marca hasta ese
toque: **rapido (<= 15 min)** / **lento (> 15 min)**; tope 240 min. -> 4 celdas fijas (2 d x 2 t). Sin barrido de valores.
En el toque se miden (zonas OG/VI vivas, vida 500 velas M1, mismas reglas de M8):
- **k = zonas tomadas**: zonas del interior del impulso atravesadas enteras por la vuelta entre la marca y el toque.
- **m = zonas restantes**: zonas entre el precio y A (interior aun no tomado) **+** zonas de la franja de atras [A-R, A)
  ("que hay del otro lado").

## Desenlace
Desde el toque: llegar a **A** (el otro lado) antes de volver a **X**; misma vela -> X; tope 240 min/sesion -> "tiempo".
P&L: entrada limite en el nivel d a favor de la vuelta, objetivo A, stop X (+1 tick), costos propios (NQ $4,50 RT y 1 tick;
ES idem en sus puntos).

## Hipotesis (NQ, Holm sobre 8; bootstrap por dia 10.000; bilaterales)
Por celda (4): **H_k** P(A) con k alto (>= mediana de la celda, > 0) - k bajo; **H_m** P(A) con m bajo (<= p33) - m alto (>= p67)
("del otro lado vacio vs cargado"). Ajustado por estratos de vol_pre (terciles) x terciles de R (lo aprendido en M7b).
- Toda celda/contraste que sobreviva Holm en NQ se prueba **una sola vez** en ES con el signo y cortes de NQ congelados.
- Economico (descriptivo hasta replicar): P&L neto de entrar en d en la celda/estrato que sobreviva, en NQ y en ES.
MDE80 publicado por celda.

## Justificacion economica
Si al volver el precio "consume" desequilibrios (k alto) y del otro lado no queda liquidez que lo frene (m bajo), deberia
completar la vuelta al origen mas seguido; el tiempo distingue un rechazo violento (rapido) de una deriva (lento).

## Como podria refutarse
Ningun contraste sobrevive Holm en NQ con MDE <= 8 pp, o el sobreviviente no replica en ES, o el P&L neto <= 0.

## Riesgos
1. Multiplicidad: 8 pruebas fijas; nada de barrer distancias/tiempos.
2. Celdas chicas (d = 0,50 y lento): MDE grande; se publica.
3. Confusion con volatilidad: estratos de vol_pre; tiempo t esta ligado al regimen.
4. M4 ya dio nulo sin estas condiciones: probabilidad previa baja.
5. Paridad LUX-IMB/barras en ES no medida contra NT8.

## Datos faltantes
Ninguno.

## OK (2026-10-20)
OK de Nico ("si, medi M9"). PRE-REGISTRADO. Codigo `tools/luximb_parity/luximb_m9.py` commiteado antes de correr. Zonas tomadas = interiores vivas en la marca atravesadas enteras por la vuelta; las creadas durante la vuelta no cuentan (conservador).
