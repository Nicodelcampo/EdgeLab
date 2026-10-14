# EMAZ-D1 — estadística descriptiva de las zonas (NQ 25T, EMA 200, configuración «larga y permisiva» del usuario)

Solo descriptivo; **sin hipótesis ni medidas sobre el precio posterior**. Historia aprobada de NQ 2025-07-01..2026-09-30 (6 contratos), 264 sesiones con al menos una zona. Parámetros: Preset 0 (M150, K100, lado 0,9, eficiencia 0,6, drift 0,5, distancia constante 0,6/0,7, hold 100, extensión 150, ruptura 1,0 ATR, distancia máxima 10 ATR). Tabla por zona privada (no se publica). Resultados completos: `EMAZD1_RESULTADOS.json`.

## Anatomía
| Atributo | p10 | mediana | p90 |
|---|---:|---:|---:|
| Largo (barras de 25 ticks, desde el ancla) | 195 | **247** | 351 |
| Duración real (minutos) | 2,1 | **6** | 47,5 |
| Recorrido de precio (ATR) | 11,5 | 20,6 | 32,9 |
| Recorrido (puntos NQ) | 22,5 | 46,5 | 92,3 |
| Pendiente (ATR por barra) | 0,05 | 0,08 | 0,13 |
| Toques de la línea | 3 | 3 | 4 |
| Distancia media a la EMA (ATR) | 5,2 | 6,8 | 9,4 |
| Razón acercamiento/alejamiento | 0,36 | 0,48 | 0,60 |
| Actividad (barras por minuto) | 5,7 | 43 | 117 |

- **1.571 zonas, 6 por sesión (mediana; 136 de 264 sesiones tienen 6 o más), 53 % alcistas.**
- **Largo en barras ≠ largo en tiempo:** una zona mediana de 247 barras dura ~6 minutos, porque en la apertura de NQ se forman ~43 barras de 25 ticks por minuto. Medidas en ATR (el recorrido) son comparables entre momentos; el largo en barras no.

## Cómo terminan
82 % por ruptura de la línea, 10 % porque el precio se aleja demasiado (> 10 ATR), 8 % porque deja de cumplirse la EMA. Entre el último toque y el final pasan una mediana de 45 barras (p10 13, p90 132).

## Contextos
- **Hora (CT) de inicio:** concentradas en la apertura regular: 275 zonas a las 8h, 273 a las 9h, 176 a las 10h, 165 a las 14h; muy pocas de madrugada. Cuidado: la cantidad por hora sigue la cantidad de barras (más negocio, más barras de 25 ticks); falta normalizar por barras disponibles.
- **Largo y recorrido en ATR casi no cambian con la hora, el día de la semana ni la volatilidad** (terciles de ATR: mediana de largo 249 / 246 / 245; recorrido 20,7 / 21,1 / 19,9 ATR): las medidas en ATR normalizan bien.
- **Estabilidad temporal:** primera mitad vs segunda: largo 248 / 245, recorrido 21,1 / 20,1 ATR.
- **Secuencia:** la zona siguiente en la misma sesión va en la misma dirección el 50,3 % de las veces (azar); solo 1,2 % de pares se superponen; mediana de 1.815 barras entre zonas.

## Relaciones entre atributos (Spearman)
La pendiente se asocia con el recorrido (0,68) y con la distancia a la EMA (0,79); más pendiente → menos largo (−0,23). Toques, volatilidad y actividad son casi independientes del resto.

## Tipología exploratoria (k = 4; proporciones estables entre mitades)
| Tipo | Parte | Largo | Pendiente | Toques | Dist. EMA (ATR) | Recorrido (ATR) | Alcista |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 «suave y corta» | 38 % | 224 | 0,069 | 3 | 6,0 | 14,9 | 53 % |
| 1 «empinada y lejana» | 29 % | 237 | 0,114 | 3 | 8,7 | 27,1 | 59 % |
| 2 «muchos toques» | 9 % | 298 | 0,076 | 5 | 6,5 | 22,4 | 45 % |
| 3 «larga» | 24 % | 313 | 0,067 | 3 | 6,5 | 22,0 | 49 % |
Los cuatro tipos aparecen sobre todo en la apertura (8–10 h CT). La agrupación es exploratoria: sirve para plantear contextos, no para concluir.

## Para las próximas preguntas (antes de cualquier hipótesis sobre el precio)
Normalizar la hora por barras disponibles; medir largo en minutos además de barras; ver si los tipos 1 y 3 (los de mayor recorrido) se concentran en ciertos días/horas; relacionar los toques con volumen/delta; comparar con las zonas de aVolZonePOI2; repetir en ES/YM/GC/MGC.

# EMAZ-D2 — volumen tras el fin de la zona: franja «más allá» vs «adentro» (descriptivo)
Definición: al terminar la zona (cierre de la última barra válida, R), dos franjas de igual altura (fracción de la altura de la zona = rango de precio): «más allá» (desde R, en el sentido de la tendencia) y «adentro» (desde R hacia atrás); volumen a nivel de tick en las N barras siguientes (misma sesión). `share` = más_allá / (más_allá + adentro). Control: la misma medida en una barra al azar fuera de las zonas con igual altura y dirección. 1.571 zonas, 264 sesiones; diferencia apareada con error estándar agrupado por sesión. Datos: `EMAZD2_RESULTADOS.json`.

| Franja (× altura) | N barras | share más allá (zonas) | control | diferencia apareada ± EE | P(llega a más allá / a adentro) | control |
|---|---:|---:|---:|---|---|---|
| 0,5 (la del usuario) | 50 | 0,407 | 0,503 | −0,095 ± 0,015 | 0,02 / 0,05 | 0,08 / 0,08 |
| 0,5 | 100 | 0,436 | 0,503 | −0,066 ± 0,014 | 0,08 / 0,14 | 0,18 / 0,15 |
| 0,5 | 200 | 0,459 | 0,505 | −0,046 ± 0,013 | 0,22 / 0,30 | 0,31 / 0,28 |
| 0,5 | 400 | 0,475 | 0,508 | −0,032 ± 0,012 | 0,39 / 0,45 | 0,42 / 0,41 |
| 0,25 | 100 | 0,431 | 0,500 | −0,068 ± 0,013 | 0,36 / 0,48 | 0,43 / 0,42 |
| 1,0 | 200 | 0,460 | 0,505 | −0,044 ± 0,014 | 0,02 / 0,04 | 0,08 / 0,08 |
- Tras el fin de la zona, **hay menos volumen en la franja «más allá» que en la franja «adentro»** (≈ 41 % a 50 barras, 46–48 % a 200–400 barras, contra 50 % del control). Consistente en las 4 alturas, en las 4 ventanas y en todos los contextos probados (alcistas/bajistas, pendiente, largo, hora de inicio, mitades de la muestra: 44–47 % contra ~50 % del control).
- El precio llega menos a menudo a extenderse una distancia h más allá que a volver una distancia h hacia adentro (0,22 contra 0,30 con franja 0,5 y 200 barras), mientras que el control es simétrico.
- **Advertencia sobre cómo se mide:** el 82 % de las zonas termina porque el precio rompe la línea en contra de la tendencia. Las barras inmediatamente posteriores empiezan con ese movimiento contrario, así que parte de este resultado es **mecánico** (selección por cómo se define el fin), y el control al azar no tiene ese condicionamiento. No debe leerse como una propiedad del mercado todavía.
- Próximo paso para quitar el sesgo: medir desde la barra de ruptura (lo único conocido en tiempo real), separar por motivo de fin (ruptura/alejamiento/EMA) y usar un control condicionado a un movimiento contrario de igual tamaño justo antes.

# EMAZ-D3 — corrección del sesgo de EMAZ-D2 (el efecto desaparece)
Referencia = barra de ruptura (kb = fin + 1, conocida en tiempo real); ventana desde kb+1; control = barra fuera de las zonas **emparejada por el contramovimiento previo** (último cierre y desplazamiento de 20 barras, en ATR, mismo sentido), no al azar. 1.448 zonas (1.282 por ruptura, 161 por alejamiento), 1.447 con control; datos en `EMAZD3_RESULTADOS.json`.

| Franja (× altura) | N barras | share «más allá» zonas | control emparejado | diferencia ± EE (sesiones) | P(llega más allá / adentro) zonas | control |
|---|---:|---:|---:|---|---|---|
| 0,5 | 50 | 0,489 | 0,490 | −0,001 ± 0,015 | 0,04 / 0,03 | 0,09 / 0,08 |
| 0,5 | 100 | 0,500 | 0,497 | +0,003 ± 0,014 | 0,11 / 0,12 | 0,17 / 0,17 |
| 0,5 | 200 | 0,508 | 0,505 | +0,004 ± 0,014 | 0,25 / 0,27 | 0,31 / 0,26 |
| 0,5 | 400 | 0,514 | 0,507 | +0,008 ± 0,013 | 0,43 / 0,42 | 0,44 / 0,40 |
| 0,25 | 100 | 0,496 | 0,496 | −0,000 ± 0,013 | 0,42 / 0,43 | 0,43 / 0,42 |
| 1,0 | 200 | 0,508 | 0,506 | +0,003 ± 0,014 | 0,03 / 0,04 | 0,09 / 0,07 |

- **El efecto de EMAZ-D2 (−5 a −10 puntos) era mecánico**: con el control emparejado la diferencia es ≈ 0 (± 1,4 puntos) en todas las franjas y ventanas, tanto para fines por ruptura como por alejamiento. El volumen tras el fin de la zona se reparte igual que tras cualquier contramovimiento similar: el fin de una zona no agrega información sobre dónde se opera después.
- Por contexto (alcista/bajista, pendiente, largo, hora, mitades) los valores van de 0,49 a 0,53 contra 0,49–0,52 del control; con 12 cortes y 1.400 zonas no hay ninguno que se distinga del ruido (pendiente media 0,526 vs 0,504 es el mayor, sin corrección por comparaciones múltiples).
- Detalle sin resolver: la probabilidad de **llegar** a la franja «más allá» es algo menor en las zonas que en el control (0,25 vs 0,31 con ½ y 200 barras) mientras que «adentro» es igual; no tiene error estándar calculado y puede deberse a un emparejamiento imperfecto.
- **Velocidad:** esta corrida tardó 64 segundos (EMAZ-D2: ~34 minutos) reutilizando las zonas ya calculadas, cargando solo las columnas necesarias y procesando contratos en paralelo (2 procesos; con 4 se agotó la memoria).
