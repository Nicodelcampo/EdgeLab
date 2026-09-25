# Manifiesto: reingreso a la franja TBZX y dirección de los 3 ticks siguientes (TBZX-R3), ES, 2026-09-25

**Estado:** EXPLORACIÓN pedida por Nico en chat (25/09). Escrito y commiteado **antes** de ver cualquier número.
**Partición:** ES, sesiones jul-2025 a mar-2026 (exploración, `P-TBZ-EXP`). Abr–jun (confirmación) y el holdout (>= 2026-07-01) no se leen: el kernel filtra por timestamp al leer.
**Dónde corre:** kernel de Kaggle sobre `nicolasbuttaro/edgelab-ticks-es-preholdout`. Herramienta: `tools/tbzx_reingreso_kaggle.py`.

## 1. Pregunta (palabras de Nico)

Después de que se crea una expansión: ¿hay alguna distancia a la que el precio se aleje de la zona y, al volver, algún
nivel de penetración (tick 1, 2, 3… hasta la zona entera) que, esperando o no un retroceso, prediga la dirección de los
3 ticks siguientes?

**Secuencia (en este orden):** se crea la zona → el precio se aleja `D` → vuelve → se introduce `p` → retrocede `r` → se
dispara la entrada, con TP de 3 ticks.

## 2. Definiciones

- **Zona:** detector TBZX del visor (port exacto, `tools/tbzx_espejo.py::detect`), velas de 25 trades reiniciadas por
  sesión, eficiencia 0,6, retroceso 0,3. Grilla `maxBars` {10, 20, 40} × `minW` {8, 12, 17, 24}. Zona = [min(A,B), max(A,B)],
  ancho W. Disponible al cierre de la vela que decide el fin; todo lo demás se mide con trades posteriores.
- **Se aleja D:** primer trade a >= D ticks más allá de un borde (cualquiera de los dos; se registra si es el lado B, hacia
  donde iba el impulso, o el A). D ∈ {2, 4, 8, 12, 20}. Horizonte: 2 h desde que la zona está disponible, dentro de la sesión.
- **Se introduce p:** primer trade a p ticks adentro desde ese borde (p = 0 es tocar el borde). p ∈ {0, 1, 2, 3, 4, 6, 8, 12}
  ticks (sólo si p < W) y p ∈ {0,25; 0,5; 0,75}·W. Tocar el borde opuesto termina la búsqueda.
- **Retrocede r:** después de tocar p, el precio vuelve r ticks hacia el borde por el que entró, medido desde el punto más
  profundo alcanzado desde el toque. r ∈ {0, 1, 2, 3, 4}; r = 0 es entrar en el toque. **Espera máxima 30 s** desde el toque;
  si llega al **borde opuesto** antes, se cancela (no hay trade).
- **Entrada:** en las dos direcciones, por separado: **sigue** (hacia adentro de la franja) y **rebota** (hacia afuera).
- **Salida:** TP 3 ticks; SL ∈ {2, 3, 4, 6, 8}; salida por tiempo a los 300 s. La celda SL = 3 es la pregunta pura
  («¿para dónde van los próximos 3 ticks?»).

## 3. Ejecución (dos lecturas, Nico)

1. **Perfecta:** entrada exactamente en el nivel del disparo, TP y SL por toque, sin slippage ni comisión.
2. **Realista** (regla EXEC-QI sin QI, porque no hay L2 en Kaggle): latencia 250 ms; límite en el mejor precio propio
   (bid para comprar, ask para vender), llena sólo si un trade la atraviesa; si no llena en 30 s, cruza. TP límite que hay que
   atravesar por 1 tick; SL a mercado al precio contrario del libro en ese trade; comisión 0,2 ticks por lado.
   Como referencia también **agresiva** (a mercado al ask/bid tras la latencia), mismas salidas.

## 4. Nulos (se reportan por separado)

- **N1:** random walk con toque perfecto: acierto esperado SL/(SL+3); para SL = 3, 50 %.
- **Fantasma:** misma geometría (A, B relativos al último trade al estar disponible) puesta en otra sesión de la partición,
  a la misma hora ET (± 15 min), con las mismas reglas. Pregunta si es propio de la zona o lo hace cualquier franja a esa hora.

## 5. Filtro de pocas zonas (Nico, antes de medir; sin mirar resultados)

- Se excluye una configuración (`maxBars`, `minW`) si genera **< 2 zonas por sesión** en promedio.
- Se excluye una celda (config, lado, D, p, r, dirección) si tiene **< 100 disparos**.

## 6. Reporte y multiplicidad

- Por celda: n, acierto, P&L medio (ticks), para real y fantasma; IC por bootstrap por sesión (1.000 réplicas).
- **Familia primaria:** ejecución perfecta, SL = 3: acierto − 50 % y acierto − fantasma. BH-FDR q = 0,10.
- **Familia secundaria:** ejecución realista, todo SL: P&L neto > 0. BH-FDR q = 0,10.
- Sugerencia = pasa FDR, IC inferior > 0 contra N1 **y** contra fantasma, y ≥ 55 % de meses positivos.
- Todo lo que salga es sugerencia a confirmar en abr–jun con spec aparte; se publica el paisaje completo.

## 7. Riesgos

- Miles de celdas sobre los mismos datos: exploración; FDR y reserva de abr–jun.
- Celdas anidadas (p, r, D comparten disparos): no son independientes; el FDR es orientativo.
- El fill realista sin QI es el lado conservador de EXEC-QI (ES: +0,12 vs +0,18 t/lado con QI).

## 8. Enmienda — iteración 2 (25/09, después de ver 46 sesiones jul–sep 2025, corrida local)

**Qué se vio:** con ejecución perfecta al precio de trade, «sigue» con r >= 1 da ~+5,5 pp sobre 50 % y «rebota» con r = 0
~+4,7 pp, pero el **fantasma da lo mismo o más** (+6,5 a +8 pp): es rebote bid/ask de los precios de trade, genérico, no de
la zona (real − fantasma ≈ 0). Realista: todas las celdas negativas (media −1,6 t, mejor −0,63). Una celda pasa todo
(mb40_mw12, B, D 8, p 0,75W, r 1, sigue: 54,8 % vs fantasma 49,5 %, n 1.506), a verificar en la muestra completa.

**Cambios (no eligen celdas; corrigen la medida):**
1. Nueva ejecución **perfecta sobre el precio medio** (bid+ask)/2: entrada en el medio del disparo, TP/SL por toque del medio.
   Pasa a ser la **familia primaria** (SL = 3). La perfecta al precio de trade queda como descriptiva. Verificada: con
   bid/ask simétricos alrededor del trade da idéntico a la de trade en las 30.350 celdas.
2. **3 fantasmas por zona** (antes 1), para bajar el ruido del nulo.
3. Paralelo por sesión (4 núcleos). Semilla por sesión.

La corrida 1 (kernel `edgelab-tbzx-r3`) se conserva como referencia; la 2 corre como `edgelab-tbzx-r3-v2`.
