# Fase 0 del ORB (Opening Range Breakout) en ES y NQ — manifiesto PRE-REGISTRADO (BORRADOR)

Estado: **PROPUESTA PARA NICO. No se ejecuta nada hasta su OK explicito.** Fecha: 2026-10-17. Rama `research/k37-prereg-corredor-hft-20261017`.
Referente rector: `docs/NORTH_STAR.md`, cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Familia nueva a registrar: `ORB-FUT` (independiente de corredor x HFT y de EXEC-PASIVA-ES; no hereda resultados ni multiplicidad).

## 0. Lo que ya existe (revision de repo, disco G y Kaggle) — esto cambia el punto de partida
**ORB 5-min en ES y NQ ya se midio y esta refutado.** No se repite.
- `strategies/orb.py` (config unica: rango = primeros 5 min RTH; stop-buy/stop-sell en el extremo; stop en el extremo opuesto; salida EOD; 1 trade/dia; costo 2.5t RT) y su validacion con fills reales
  `strategies/orb_tickfill.py` (fill = ask/bid del primer tick que cruza; +0.5t de fees RT).
- Registro `corpus/ssrn/cerebro/LEDGER_EXPERIMENTOS.md`, **EXP-043 (2026-07-17)**: el "sobreviviente" ORB-NQ (+249t/trade, MCPT p = 0.006) era **un bug de signo** en el stop del short (`(hi-entry)` en vez de `(entry-hi)`);
  lo cazo la replicacion en un segundo simulador independiente (tick vs M1). Corregido: **ORB 5-min NQ, 183 trades, 10.5 meses: -18.7t/trade (M1) / -17.1t (tick), win 33 %, MCPT p = 0.58 -> MUERTA. ES: -13.1t/trade, win 26 % -> MUERTA.**
  Leccion registrada: ningun sobreviviente se asienta sin acuerdo entre dos simuladores independientes.
- Lo adyacente: `docs/SCOPING_ruptura_de_rango.md` (familia "ruptura de rango horario", solo scoping); `MANIFIESTO_IB_VWAP_Y_PMH_PML_NQ_20260929.md` + `RESULTADO_...`: **IB 60 min -> VWAP: 5 trades (inconclusa por muestra); PMH/PML: 36 trades, -0.07R (punto muestral negativo)**; NQ jul-sep 2026, sin comisiones, sin confirmacion.
- Disco G: `DOSSIER_COMPLETO_TRABAJO_AYER_20261013.json` contiene una **propuesta no medida** de Gemini ("Motor 1.B ORB institucional MNQ/MES": caja 09:30-09:45 ET; no operar si `h < 0.6 x ATR14` o `h > 2.5 x ATR14`; ruptura antes de 10:15 en vela de 5 min con volumen `> 1.3 x` media 20; TP = 1.5 h; SL = 50 % de la caja; cierre 15:45). Es una hipotesis, no un resultado.
  `GUIA_TECNICAS_..._EXP_REV_GRID_20261015.md` indica que la posicion respecto del Value Area previo y del rango de apertura RTH separa dias de rotacion de dias de tendencia (contexto para reversion, sin medir ORB).
- Kaggle (privado): `edgelab-liquid-ticks-20261014` (14 activos incl. ES/NQ, 1 contrato por sesion, sin holdout; estado CANDIDATE), `edgelab-ticks-nq-preholdout`, `edgelab-ticks-nt8-canonical` (2025-2026Q3), `edgelab-l2-es-20261015` (cotizaciones L1 continuas jul-sep 2026, `research_allowed` levantada por Nico solo para jul-sep). No hay kernels ORB.
- Datos locales: `data/nq_m1_clean.parquet` (M1, 2025-08-28 a 2026-07-15).

**Correccion a mi mensaje anterior.** Dije que el costo "pesaria mucho menos" en ORB; es cierto en proporcion (costo 2.5t sobre un riesgo de decenas a cientos de ticks), pero **no es el cuello de botella**: EXP-043 mostro perdida bruta, no perdida por costos. El problema del ORB 5-min en futuros indice es la direccion, no la friccion.
El propio `orb.py` registra que el resultado positivo del paper de Zarattini se apoya en el filtro "Stocks in Play", **no portable a un futuro unico**: ese es el hueco que esta fase mira (que, en futuros, hace el papel de "in play").

## 1. Justificacion economica y refutacion
- **Justificacion:** la apertura concentra informacion nueva (noticias, flujo institucional, reaccion a la sesion asiatica/europea). Si el rango inicial es "ancho" para la sesion y el flujo es inusualmente grande, la ruptura podria persistir; si es angosto/apatico, hay mas ruido. Las versiones con filtro de volumen/rango del dia (Stocks in Play) son la forma documentada de seleccionar esos dias.
- **Como podria refutarse (Fase 0):** (a) si la muestra no alcanza (pocos dias con ruptura en los estratos relevantes) la Fase 1 no tiene potencia; (b) si en 0B la extension post-ruptura sin stop, en unidades del rango, es indistinguible de la deriva diaria y su IC excluye cualquier efecto que cubra costos + friccion de apertura, la familia se cierra sin gastar la replicacion; (c) si el costo de ejecucion de un stop de ruptura en la apertura (spread/deslizamiento medidos) es comparable al tamano esperado del efecto.

## 2. Poblacion y espacio de eventos (regla de poblacion)
Espacio considerado: (a) ORB RTH de ES o NQ a las 09:30 ET; (b) ORB sobre otras aperturas (Globex 18:00 ET, Londres 03:00 ET); (c) rango inicial de 5 / 15 / 30 / 60 min; (d) ruptura por toque (stop) o por cierre de barra; (e) una o ambas direcciones; (f) con o sin filtros (relative volume, rango/ATR, gap, direccion de la primera vela, dias de calendario macro).
**Elegida:** ORB sobre la apertura RTH 09:30 ET (America/New_York, con DST), **ventana primaria 15 min** (estandar de practica y la de la propuesta del dossier), grilla descriptiva de 5/15/30/60; ruptura **por toque** (como una orden stop), una direccion por dia (la primera). ES y NQ **por separado**, sin inferencia conjunta.
No se miden aqui: (b), (d) por cierre como primaria, filtros como hipotesis (solo sus distribuciones marginales), dias de calendario macro (no hay calendario verificado en el repo; si se quiere, es un manifiesto aparte con la fuente declarada).
- Datos: ticks de `edgelab-liquid-ticks-20261014` (hora UTC, 1 contrato por sesion). Ventana de **descubrimiento 2025-07-18 a 2026-03-31 (178 sesiones)**. Holdout >= 2026-10-01 intacto.
- **Contaminacion declarada:** EXP-043 uso M1 de ~2025-08-28 a ~2026-07-15, es decir **parte de la ventana de replicacion abr-sep 2026 ya se vio para ORB 5-min**. Para ORB-FUT solo es limpia 2026-07-16 a 2026-09-30 (~55 sesiones por activo) y, si se confirma alguna variante, la unica confirmacion verdaderamente fresca es el holdout forward (>= 2026-10-01). Ademas la captura de NT8 se detuvo (`DECISIONES_20261014` #16): no hay N nuevo hasta restablecerla.

## 3. Fase 0A — sin retornos (target-free)
Mide, por activo, en descubrimiento (y luego en 2026-07-16..09-30 como estabilidad):
1. **Integridad y universo:** sesiones RTH validas por activo, primer print a las 09:30 ET, medias jornadas (feriados de cierre temprano), huecos, roll, contratos; reloj verificado; conteos por definicion de rango.
2. **Geometria del rango inicial** (5/15/30/60 min): ancho en ticks, en ATR diario (14 sesiones previas, causal) y en % del precio; cuantiles; relacion costo/ancho (con 2.5t RT de `orb.py` y con el costo medido abajo).
3. **Ocurrencia de ruptura:** `P(romper maximo)`, `P(romper minimo)`, `P(ambas)`, `P(ninguna)` hasta las 11:30 y hasta las 15:45; distribucion del tiempo a la primera ruptura; fraccion de "latigazo" (ruptura de un lado y del otro antes de las 11:30).
4. **Costo de ejecucion de un stop de ruptura en la ventana 09:45-10:30:** spread efectivo y deslizamiento al cruzar el nivel (ticks con bid/ask del dataset; cotizacion L1 continua de `edgelab-l2-es` solo para ES jul-sep). Es una medicion de mercado, sin direccion.
5. **Distribuciones marginales de los candidatos de filtro** (sin cruzarlas con resultados): volumen del rango inicial relativo a las 20 sesiones previas; rango/ATR; gap de apertura; direccion de la primera vela de 5 min; con el **N por estrato** (terciles) para saber cuantos dias habria en cada celda.
6. **Potencia:** con `N` sesiones con ruptura, `MDE(80 %, 2.5 % unilateral) = 2.8 x SD / sqrt(N)`. La `SD` se toma de 0B; se publica el MDE por activo, por estrato y a que fraccion del rango (R) corresponde.

## 4. Fase 0B — descriptiva, toca precios posteriores a la ruptura (requiere OK aparte dentro de este manifiesto)
Una sola celda primaria, sin estrategia (sin stop ni objetivo): para ORB de **15 min**, en el dia de ruptura, la **extension firmada** `E_t = signo(ruptura) x (P_t - nivel_roto) / ancho_del_rango` medida a 11:30 y al cierre 15:45, con la ruptura por toque (primer tick que cruza). Se publica **la distribucion completa** (cuantiles 5/25/50/75/95), la media y el SE clusterizado por sesion, mas el canal no direccional (extension absoluta). Es el bruto del ORB **antes de cualquier stop**: no se elige nada por su resultado y no hay grilla de decision.
Se compara contra el **nulo de deriva**: el mismo estadistico con `signo` asignado al azar entre los dias (permutacion de 2.000 repeticiones), porque EXP-043 mostro que la deriva del semestre disfraza falsos positivos. La grilla 5/30/60 min se publica descriptiva (landscape), sin inferencia.

## 5. Criterios (definidos antes de mirar)
- **GO_FASE1** (por activo): integridad OK **y** `N >= 150` sesiones con ruptura **y** costo/ancho mediano del rango de 15 min <= 10 % **y** MDE de la media de `E` al cierre <= 0.30 R. No exige un efecto: solo que se pueda medir.
- **NO_GO:** `N < 100` **o** costo/ancho mediano > 25 % **o** la media de `E` al cierre tiene IC 95 % bilateral contenido en [-0.10 R, +0.10 R] y el p del nulo de deriva > 0.10.
- **ABSTENCION:** cualquier otro caso (no se retoma sobre la misma ventana).
Un `GO_FASE1` **no es un edge**: abre un manifiesto de estrategia (una variante, stop/salida causales, ejecucion y costos del modelo de EXEC-PASIVA, confirmacion forward) y su propio STOP.

## 6. Inferencia, multiplicidad y guardas
- SE clusterizado por sesion (linealizacion, un cluster por sesion; leccion de F0). Decisoras: m = 1 por activo (media de `E` al cierre, 15 min). Todo lo demas: descriptivo, marcado exploratorio.
- **Dos simuladores independientes** para cualquier numero que alimente una decision (leccion EXP-043): el calculo de `E` sobre ticks se replica con un segundo camino (barras M1 de `nq_m1_clean.parquet` en NQ; para ES, barras construidas aparte desde ticks por otro codigo); diferencia > 0.5 tick por dia en alguna fila -> aborta.
- Guardas fail-closed: sesion con primer print > 09:35 ET o con huecos > 60 s en la ventana 09:30-10:30 se descartan y se cuentan; relojes monotonos; contrato unico por sesion; ningun timestamp >= 2026-10-01; prueba causal (perturbar ticks posteriores al instante del nivel no cambia el nivel ni el primer cruce).
- Sin optimizar nada: ni ventana, ni hora, ni umbral.

## 7. Fuera de alcance
Estrategia con stops/objetivos, ML/3 franjas/grillas (pendiente separado: `PENDIENTE_ORB_HERRAMIENTAS_EDGELAB_20261017.md`), ejecucion pasiva en ORB, NQ/YM/6E/GC adicionales, calendario macro, cualquier cosa del holdout.

## 8. Decision que se le pide a Nico
1. **(A)** Aprobar 0A + 0B (incluye usar `edgelab-liquid-ticks-20261014`, estado CANDIDATE), o
2. **(B)** Aprobar solo 0A (sin retornos) y decidir 0B despues, o
3. **(C)** Pedir cambios (instrumento, ventana primaria, criterios).
**Mi recomendacion: (B) primero, luego (A):** con 183 operaciones ya muertas en 5-min y un costo que no es el problema, lo mas valioso de la Fase 0 es saber si **hay N y poder** para algo distinto (15 min con filtros) antes de tocar retornos. 0A es barata y deja cerrado, con datos, si la familia merece una Fase 1.

## 9. Ejecucion propuesta
Un kernel Kaggle de una pasada por activo (CPU), salida `EXP_ORB_F0_RESULTS_<activo>.json`, codigo y manifiesto congelados por commit antes de correr; registro MEDIDO/NO MEDIDO de `ORB-FUT` en el mismo commit que el resultado.

## 10. Autorizacion y orden de ejecucion (registro, 2026-10-17)
- Nico, en chat: "opcion B, y despues A". Se ejecuta **0A ahora** (sin retornos, ES y NQ por separado) y **0B despues**, con su propio kernel congelado por commit antes de correr.
- Uso del dataset `edgelab-liquid-ticks-20261014` (CANDIDATE) aprobado para esta fase.
- Como el MDE de la seccion 5 depende de la SD de la extension (que mide 0B), **0A publica banderas preliminares** (N, costo/ancho, integridad) y una **grilla de MDE para SD en {0.5, 1, 1.5, 2} R**; el veredicto GO/NO_GO final se emite despues de 0B.
- Implementacion de 0A (kernel `edgelab-orb-f0a-v1`): descubrimiento 2025-07-18..2026-03-31 y ventana limpia 2026-07-16..2026-09-30; las sesiones intermedias solo alimentan ATR/volumen/gap causales. Segundo camino independiente (barras de 1 minuto por `groupby`) para ancho y minuto del primer cruce; cualquier discrepancia se reporta como `second_path_disagreements`.
- Costo de ejecucion: de los ticks del dataset (bid/ask en la fila del trade, con la cotizacion vieja como limite declarado); la cotizacion L1 continua de `edgelab-l2-es` no se usa en 0A.

## 11. Enmienda A1 (2026-10-17): `outside_regular` no es una bandera RTH utilizable
La primera corrida de 0A (`edgelab-orb-f0a-v1`, version 1) descarto **todas** las sesiones por la guarda de primer print (0 sesiones validas, sin ningun resultado). Un diagnostico (`edgelab-orb-diag-rth-v1`) mostro la causa:
en `edgelab-liquid-ticks-20261014`, `outside_regular` vale 0 en **toda** la sesion Globex (18:00 ET del dia anterior a 17:00 ET), por lo que no marca el RTH. La guarda funciono como corresponde.
Correccion unica: **RTH se define por reloj** (09:30 a 16:00 ET del `trade_date`, con DST); el resto de definiciones y criterios no cambia. No se miro ningun resultado de mercado en la corrida fallida.
**Consecuencia fuera de ORB (registrada en `EXEC_PASIVA_ES_MEDIDO_Y_NO_MEDIDO.md`):** el contraste S3 de F0 ("primera media hora vs resto") uso `outside_regular == 0` y, por lo tanto, midio la primera media hora tras las **18:00 ET (apertura Globex)**, no la apertura de las 09:30. Su resultado (sin efecto, p = 0,47) no habla de la apertura de Nueva York.
