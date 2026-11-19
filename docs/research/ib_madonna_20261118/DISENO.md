# IB + «Madonna» (Drysdale): idea principal refinada y 10 variantes de lógica distinta (diseño, 2026-11-18)

Estado: DISEÑO — base del pre-registro `PREREGISTRO.md` (misma carpeta). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Pedido de Nico:** «quedate con la idea principal, pero mejorá/refiná los parámetros (primero leyendo la info disponible en EdgeLab
  para usar los mejores, sin sobreajustar) y diseñá 10 variantes distintas en lógica, no sólo en parámetros, con diferentes filtros,
  usando indicadores y otras herramientas de EdgeLab».
- **Fuentes:** `fuente/` (dos documentos de Meta AI sobre el reel Df2pC5-phBZ de @traderdrysdale).

## 1. Qué se conserva y qué se descarta de las fuentes
**La idea principal (se conserva):** el *Initial Balance* (IB, 9:30–10:30 ET) define el rango de equilibrio del día.
- El primer toque de un borde del IB que deja mecha afuera y cierra adentro («Madonna») es un rechazo.
- Se opera en contra, con objetivo en la mitad del IB y stop detrás del extremo del toque.
- Si el precio sale y se sostiene afuera, no se hace fade.
- Es Market Profile clásico (Steidlmayer, Dalton): no es un invento del autor.

**Se descarta:**
- **La grilla de 62 parámetros «para cubrir al creador».** Elegir entre miles de combinaciones con pocos años produce ganadoras de ruido:
  - el paso 2 de urgencia/evidencia;
  - el «atrás» M1 del 17-nov (las 5 reglas elegidas por el embudo no tenían señal en 2006–2025).
  - Acá cada variante es UNA hipótesis con su lógica, no un barrido.
- **Los filtros en puntos fijos** (IB entre 40 y 120 pts, «10 pts» de distancia, «2 pts» de buffer): K36. 40 pts de NQ en 2010 son
  ~3 IB; en 2025 son medio IB. Todo se expresa en fracciones del IB o del ATR diario causal.
- **La entrada con orden límite en el borde:** paga selección adversa (F-SELECCION-ADVERSA-PASIVA, ≈ −0,07 R en bruto en una caminata).
  La entrada es por confirmación: a mercado al abrir la vela siguiente al cierre de rechazo.
- **«Medir en puntos o en WR».** Se mide en R, con la fricción canónica (`costos.py`), bruto y neto, y la fricción en R por época
  (F-STOP-GRANDE-FRENTE-A-FRICCION).

**Lo que EdgeLab ya sabe y condiciona el diseño:**
- **F-OP1-FADE-NIVEL-LIMPIO (NO_REPETIR):** el fade pasivo del primer regreso a un nivel de la sesión no rebota. La Madonna exige
  rechazo confirmado; si su control (toque sin rechazo) rinde igual, la «Madonna» no agrega nada.
- **F-ORB-EMA20 (NO_REPETIR)** y **ORB0100 (EN_CONTRA):** las rupturas del rango inicial elegidas en datos cortos no sobreviven. T
  (FtmOrb, ORB 15 min + KNN) es pista fuerte en NQ, pero por el clasificador.
- **El régimen de mercado no explica casi nada;** la fricción relativa sí.
- **Señales brutas estables existen en la apertura** (SOM, Franklin). Si la Madonna tiene algo, debería verse en bruto en 20 años y en
  tres índices.

## 2. Regla base refinada (V0)
| Elemento | Regla | Por qué |
|---|---|---|
| IB | máximo y mínimo de las velas M1 de 9:30 a 10:30 ET | definición clásica; los datos M1 de NT8 la reconstruyen exacta |
| Velas de decisión | 5 min alineadas a las 9:30 (construidas desde M1) | las del video; la decisión es al cierre de la vela de 5 min |
| Ventana | toques entre 10:30 y 12:00 ET | la del video (después baja la participación) |
| Madonna | el PRIMER toque de un borde en la ventana: la vela de 5 min llega al borde y CIERRA adentro | primer toque = liquidez no consumida (Dalton) |
| Sin Madonna | si la vela del primer toque de un lado cierra afuera, ese lado queda descartado el día (aceptación) | «si rompe y se sostiene, no fades» |
| Entrada | a mercado en el primer tick de la vela M1 siguiente | sin límite (selección adversa) |
| Stop | extremo de la vela de toque + 0,05·IB | buffer relativo, no 2 pts |
| Objetivo | mitad del IB | la del video |
| Filtro de riesgo | se descarta si objetivo/riesgo < 1 | el código de la fuente también lo hace; no se optimiza |
| Una operación por día | la primera Madonna de cualquiera de los dos lados | sin sobreoperar |
| Salida por tiempo | 240 velas M1 o el fin de la sesión (motor) | — |

**Medición:**
- NQ, ES y YM juntos en M1 de NT8, 2006–2025, con la partición A5. Cada índice se reporta como descriptivo.
- R bruto y neto por instrumento.

## 3. Diez variantes (cada una, una hipótesis con su mecanismo)
| # | Nombre | Lógica (distinta de V0) | Mecanismo / justificación | Cómo podría refutarse | Herramienta de EdgeLab |
|---|---|---|---|---|---|
| V1 | Día de balance | V0 sólo si la apertura de las 9:30 cae DENTRO del rango del día anterior | abrir dentro del rango previo es la señal de Dalton de equilibrio; afuera, de desequilibrio (tendencia) | V1 − V0-fuera ≤ 0 con potencia | rango de la sesión previa (`a5`, M1 NT8) |
| V2 | IB ancho | V0 sólo si IB / ATR20 diario ≥ su mediana causal de 120 sesiones | un IB ancho deja menos extensión de rango: más días de rango | V2 − V0-angosto ≤ 0 | ATR causal (K36) |
| V3 | Aceptación → continuación | dos cierres de 5 min seguidos afuera del IB por ≥ 0,1·IB entre 10:30 y 12:00 → a favor de la ruptura; stop en la mitad del IB; objetivo borde + 1·IB | es la otra mitad de la idea («trend day, opero a favor»), no un fade | bruto ≤ 0 | — |
| V4 | Ruptura fallida | un cierre de 5 min afuera (≥ 0,05·IB) y, dentro de 30 min, un cierre de vuelta adentro → fade a la mitad; stop detrás del extremo de afuera + 0,05·IB | «look above and fail»: los que compraron la ruptura quedan atrapados (Dalton) | bruto ≤ 0 o ≤ V0 | — |
| V5 | Fade hacia el valor | V0 con objetivo en el VWAP de la sesión (desde las 9:30), sólo si el VWAP está entre la entrada y el borde opuesto | el precio vuelve al valor del día; la mitad del IB es un proxy del valor | V5 ≤ V0 | `rasgos_comunes.vwap` |
| V6 | Hacia el cierre anterior | V0 sólo en el lado que apunta al cierre RTH previo (con gap arriba sólo la venta en el máximo del IB) | el relleno del gap es un imán documentado; el fade va a favor del relleno | V6 − V0-contra ≤ 0 | sesión previa (M1) |
| V7 | Clímax de volumen | V0 sólo si el volumen de la vela de toque ≥ 2× el volumen medio de 5 min del IB | agotamiento: el último empuje gasta la liquidez del lado agresor | V7 − V0-sin clímax ≤ 0 | volumen M1 |
| V8 | Impulso LUX-IMB hacia el borde | V0 sólo si en los 15 min previos al toque hubo una marca de impulso LUX-IMB (D3_20, ≥ 1 zona en el 25 % inicial) en dirección al borde | LUXIMB-A5: el fade de un impulso fuerte tiene reversión bruta estable en 17 años; el borde del IB le da ubicación | V8 − V0 ≤ 0 | `luximb_grilla.marcas_segmento`, zonas OG/VI (paridad NT8) |
| V9 | Sin apertura en tendencia | V0 sólo si los primeros 30 min NO son «Open-Drive» (apertura a < 10 % del extremo del rango de 30 min y cierre a < 10 % del otro) | un Open-Drive anuncia tendencia: el fade va contra el flujo iniciador (Dalton) | V9 − V0-drive ≤ 0 | — |
| V10 | Doble prueba | el primer toque cerró AFUERA (no fue Madonna), el precio volvió adentro y una segunda prueba no supera el primer extremo y cierra adentro → fade; stop detrás del primer extremo + 0,05·IB | doble techo en el borde: la segunda prueba sin nuevo extremo confirma el rechazo | bruto ≤ 0 | — |

**Notas:**
- **Contrastes:** V1, V2, V6, V7 y V9 se comparan contra V0 en los días que el filtro DESCARTA (su complemento). Eso mide el filtro, no
  la base.
- **SMT** (divergencia NQ/ES en el toque) queda para una segunda tanda: necesita dos instrumentos en el mismo evento, y la calibración
  por tablas de ticks es de un instrumento.

## 4. Medición, partición y decisión
**Igual que ESCALONADAS-M1:**
- motor único con K40;
- calibración contra ticks en ago-25 → mar-26 (Kaggle);
- desenlaces sólo en DESC/REP;
- BH q 0,10 en DESC, LORD++ en REP;
- apertura A5 única con compuerta económica y potencia ≥ 0,8.

**Pruebas:** 11 absolutas (V0–V10) + 5 contrastes de filtro = 16.

**Estimación sin retornos (a confirmar con el conteo real):**
- ≈ 40 % de los días con Madonna → ≈ 100 por año por índice → ≈ 6.000 en DESC+REP+HOLDOUT con los tres índices;
- el holdout tiene ≈ 1.500 de V0.
